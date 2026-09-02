"""
Precision/recall/F1 + confusion matrix, both binary (vulnerable vs
likely_safe) and per-category (macro/micro-averaged), replacing
dataset_runner.py's old compare_verdict() binary match/no-match.

This module only computes metrics from (ground truth, prediction) pairs —
it does not run any analysis itself. Producing real predictions to feed it
(re-running Slither/Mythril/single-LLM/current-ThirdEye across the full
benchmark datasets) is explicitly the next session's work, not this one.
See eval/sanity_check.py for how this module's own arithmetic was verified
before trusting it on new data.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from eval import taxonomy
from eval.schema import EvalItem


@dataclass
class Prediction:
    contract_id: str
    predicted_label: str  # "vulnerable" | "likely_safe"
    predicted_categories: list[str] = field(default_factory=list)  # lowercase free-text, same convention dataset_runner.py already used
    confidence: float | None = None
    category_taxonomy: str = "thirdeye"  # which table eval/taxonomy.py should use to normalize predicted_categories


def _binary_confusion(items: list[EvalItem], preds: dict[str, Prediction]) -> dict:
    tp = fp = tn = fn = 0
    skipped = 0
    for item in items:
        pred = preds.get(item.contract_id)
        if pred is None:
            skipped += 1
            continue
        actual_positive = item.ground_truth_label == "vulnerable"
        predicted_positive = pred.predicted_label == "vulnerable"
        if actual_positive and predicted_positive:
            tp += 1
        elif actual_positive and not predicted_positive:
            fn += 1
        elif not actual_positive and predicted_positive:
            fp += 1
        else:
            tn += 1

    total = tp + fp + tn + fn
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    accuracy = (tp + tn) / total if total else 0.0

    return {
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "support": total, "skipped_no_prediction": skipped,
        "precision": precision, "recall": recall, "f1": f1, "accuracy": accuracy,
    }


def _category_confusion(items: list[EvalItem], preds: dict[str, Prediction], normalize_categories: bool = False) -> dict[str, dict]:
    """One-vs-rest TP/FP/FN per category (standard multi-label metric
    practice — TN per-category isn't reported since "everything not in this
    category" isn't a meaningful denominator when items can carry zero,
    one, or many categories).

    normalize_categories=False (default) compares each dataset's native
    category strings directly — only meaningful within a single dataset
    whose ground truth and predictions already share a vocabulary.
    normalize_categories=True maps both sides through eval/taxonomy.py into
    DASP-10 buckets first, via each VulnCategory's own taxonomy tag (ground
    truth) and the Prediction's category_taxonomy (predictions) — this is
    what makes cross-dataset/cross-source category comparison meaningful at
    all, at the cost of whatever taxonomy.py can't map cleanly (see
    eval/taxonomy.py's UNMAPPED bucket and get_unmapped_log()).
    """
    per_category: dict[str, dict] = {}

    def bucket(cat: str) -> dict:
        return per_category.setdefault(cat, {"tp": 0, "fp": 0, "fn": 0})

    for item in items:
        pred = preds.get(item.contract_id)
        if pred is None:
            continue
        if normalize_categories:
            actual_cats = {taxonomy.normalize(c.taxonomy, c.category) for c in item.vuln_categories}
            predicted_cats = {taxonomy.normalize(pred.category_taxonomy, c) for c in pred.predicted_categories}
        else:
            actual_cats = {c.category.lower() for c in item.vuln_categories}
            predicted_cats = {c.lower() for c in pred.predicted_categories}

        for cat in actual_cats & predicted_cats:
            bucket(cat)["tp"] += 1
        for cat in predicted_cats - actual_cats:
            bucket(cat)["fp"] += 1
        for cat in actual_cats - predicted_cats:
            bucket(cat)["fn"] += 1

    for cat, c in per_category.items():
        c["support"] = c["tp"] + c["fn"]
        c["precision"] = c["tp"] / (c["tp"] + c["fp"]) if (c["tp"] + c["fp"]) else 0.0
        c["recall"] = c["tp"] / (c["tp"] + c["fn"]) if (c["tp"] + c["fn"]) else 0.0
        c["f1"] = (
            2 * c["precision"] * c["recall"] / (c["precision"] + c["recall"])
            if (c["precision"] + c["recall"]) else 0.0
        )

    return per_category


def _macro_micro(per_category: dict[str, dict]) -> dict:
    if not per_category:
        return {"macro_precision": 0.0, "macro_recall": 0.0, "macro_f1": 0.0,
                "micro_precision": 0.0, "micro_recall": 0.0, "micro_f1": 0.0}

    macro_p = sum(c["precision"] for c in per_category.values()) / len(per_category)
    macro_r = sum(c["recall"] for c in per_category.values()) / len(per_category)
    macro_f1 = sum(c["f1"] for c in per_category.values()) / len(per_category)

    tp = sum(c["tp"] for c in per_category.values())
    fp = sum(c["fp"] for c in per_category.values())
    fn = sum(c["fn"] for c in per_category.values())
    micro_p = tp / (tp + fp) if (tp + fp) else 0.0
    micro_r = tp / (tp + fn) if (tp + fn) else 0.0
    micro_f1 = 2 * micro_p * micro_r / (micro_p + micro_r) if (micro_p + micro_r) else 0.0

    return {
        "macro_precision": macro_p, "macro_recall": macro_r, "macro_f1": macro_f1,
        "micro_precision": micro_p, "micro_recall": micro_r, "micro_f1": micro_f1,
    }


def build_report(items: list[EvalItem], preds: dict[str, Prediction], run_name: str, normalize_categories: bool = False) -> dict:
    binary = _binary_confusion(items, preds)

    if normalize_categories:
        taxonomy.reset_unmapped_log()
    per_category = _category_confusion(items, preds, normalize_categories=normalize_categories)
    averages = _macro_micro(per_category)

    report = {
        "run_name": run_name,
        "n_items": len(items),
        "n_predictions": len(preds),
        "binary": binary,
        "per_category": per_category,
        "averages": averages,
        "categories_normalized_to_dasp10": normalize_categories,
    }
    if normalize_categories:
        report["unmapped_categories"] = taxonomy.summarize_unmapped()
    return report


def print_report(report: dict) -> None:
    b = report["binary"]
    print(f"\n=== {report['run_name']} ===")
    print(f"Items: {report['n_items']}  Predictions: {report['n_predictions']}  "
          f"Skipped (no prediction): {b['skipped_no_prediction']}")
    print("\nBinary verdict (vulnerable vs likely_safe):")
    print(f"  Confusion matrix:  TP={b['tp']}  FP={b['fp']}  TN={b['tn']}  FN={b['fn']}")
    print(f"  Precision={b['precision']:.3f}  Recall={b['recall']:.3f}  "
          f"F1={b['f1']:.3f}  Accuracy={b['accuracy']:.3f}")

    print("\nPer-category (one-vs-rest):")
    header = f"  {'category':<28}{'support':>8}{'tp':>6}{'fp':>6}{'fn':>6}{'prec':>8}{'rec':>8}{'f1':>8}"
    print(header)
    for cat, c in sorted(report["per_category"].items()):
        print(f"  {cat:<28}{c['support']:>8}{c['tp']:>6}{c['fp']:>6}{c['fn']:>6}"
              f"{c['precision']:>8.3f}{c['recall']:>8.3f}{c['f1']:>8.3f}")

    a = report["averages"]
    print(f"\n  macro:  precision={a['macro_precision']:.3f}  recall={a['macro_recall']:.3f}  f1={a['macro_f1']:.3f}")
    print(f"  micro:  precision={a['micro_precision']:.3f}  recall={a['micro_recall']:.3f}  f1={a['micro_f1']:.3f}")

    unmapped = report.get("unmapped_categories")
    if unmapped:
        print("\n  Unmapped categories (fell into DASP-10 'unmapped' bucket, not silently dropped):")
        for tax, cats in unmapped.items():
            from collections import Counter
            counts = Counter(cats)
            detail = ", ".join(f"{c}×{n}" for c, n in sorted(counts.items(), key=lambda kv: -kv[1]))
            print(f"    {tax}: {detail}")


def save_report(report: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
