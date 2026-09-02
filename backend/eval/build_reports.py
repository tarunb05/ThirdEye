"""
Builds metrics reports from already-completed checkpoints — no new
analysis runs. Reads whatever's on disk under eval/checkpoints/<baseline>/,
turns "ok" entries into Predictions, and reports every other status as a
skip (no prediction), never a guess.

Usage:
    cd backend
    python -m eval.build_reports
"""

from __future__ import annotations

import json
from pathlib import Path

from eval import metrics
from eval.loaders import etherscan50, smartbugs_curated, web3bugs, access_control_slice
from eval.schema import REPO_ROOT

CHECKPOINT_ROOT = REPO_ROOT / "backend" / "eval" / "checkpoints"
RESULTS_ROOT = REPO_ROOT / "backend" / "eval" / "results"

LOADERS = {
    "smartbugs_curated": smartbugs_curated.load,
    "web3bugs": web3bugs.load,
    "access_control_slice": access_control_slice.load,
    "etherscan50": etherscan50.load,
}


def _load_checkpoints(baseline: str, dataset_name: str) -> dict[str, dict]:
    out = {}
    d = CHECKPOINT_ROOT / baseline / dataset_name
    if not d.exists():
        return out
    for f in d.glob("*.json"):
        with open(f, encoding="utf-8") as fh:
            out[f.stem] = json.load(fh)
    return out


def build_baseline_dataset_report(baseline: str, dataset_name: str, items) -> tuple[dict, dict]:
    """Returns (report, coverage) — coverage summarizes what every
    non-"ok" checkpoint said, so a skip is visible, not silent."""
    checkpoints = _load_checkpoints(baseline, dataset_name)

    preds: dict[str, metrics.Prediction] = {}
    status_counts: dict[str, int] = {}
    skip_reasons: list[dict] = []

    for item in items:
        ckpt = checkpoints.get(item.contract_id)
        status = ckpt.get("status", "missing") if ckpt is not None else "missing"
        status_counts[status] = status_counts.get(status, 0) + 1

        if status == "ok":
            preds[item.contract_id] = metrics.Prediction(
                contract_id=item.contract_id,
                predicted_label=ckpt["predicted_label"],
                predicted_categories=ckpt.get("predicted_categories", []),
                category_taxonomy="thirdeye",
            )
        else:
            skip_reasons.append({
                "contract_id": item.contract_id,
                "status": status,
                "reason": (ckpt or {}).get("reason") or (ckpt or {}).get("slither_message"),
            })

    report = metrics.build_report(items, preds, f"{baseline}/{dataset_name}", normalize_categories=True)
    coverage = {
        "baseline": baseline,
        "dataset": dataset_name,
        "n_total": len(items),
        "n_ok": status_counts.get("ok", 0),
        "status_counts": status_counts,
        "skips": skip_reasons,
    }
    return report, coverage


def _top_categories(report: dict, n: int = 3) -> str:
    """Top categories by true-positive count, excluding the catch-all
    'unmapped' bucket — that's volume, not a finding."""
    cats = [(cat, c["tp"]) for cat, c in report["per_category"].items() if cat != "unmapped" and c["tp"] > 0]
    cats.sort(key=lambda x: -x[1])
    if not cats:
        return "—"
    return ", ".join(f"{cat}({tp})" for cat, tp in cats[:n])


# Which baselines actually have checkpoints for which datasets — Web3Bugs
# only ever ran Slither (the LLM baselines were never run against it: most
# items fail Slither's own import resolution regardless of LLM backend,
# and many would also exceed Groq's per-request token budget — both
# already documented from the prior session, not worth spending time on).
# Backbone benchmarks (etherscan50 dropped as a headline set — heuristic GT).
# Rows are only emitted for (baseline, dataset) pairs that actually have
# checkpoints on this machine (see the all-"missing" skip in main()).
BASELINE_DATASETS = {
    "slither": ["smartbugs_curated", "web3bugs", "access_control_slice"],
    "single_llm": ["smartbugs_curated", "web3bugs", "access_control_slice"],
    "current_thirdeye": ["smartbugs_curated", "access_control_slice"],
    "council": ["smartbugs_curated", "web3bugs", "access_control_slice"],
}

# Static model labels for the non-council baselines — necessary so the
# paper's table can separate model-size effects from architectural effects.
# Council's models are NOT hardcoded here: they're read back from the actual
# checkpoints (council_models_used) so the column reflects what really ran.
STATIC_MODEL_LABELS = {
    "slither": "Slither (static, no LLM)",
    "single_llm": "llama3.2:3b",
    "current_thirdeye": "llama3.2:3b + Slither",
}


def _model_label(baseline: str, dataset_name: str) -> str:
    """The model(s) that produced a row. For council, derived from the
    checkpoints' verifiable council_models_used field (distinct provider:model
    pairs), not asserted — so the column can't claim diversity the run
    didn't actually have."""
    if baseline != "council":
        return STATIC_MODEL_LABELS.get(baseline, "—")
    checkpoints = _load_checkpoints(baseline, dataset_name)
    pairs = set()
    for ckpt in checkpoints.values():
        for m in ckpt.get("council_models_used", []):
            pairs.add(f"{m.get('provider')}:{m.get('model')}")
    return ", ".join(sorted(pairs)) if pairs else "—"


def main() -> None:
    # A dataset whose source isn't present on this machine (e.g. the
    # gitignored web3bugs clone) should be skipped with a warning, not
    # crash the whole report — its rows simply won't appear in the table.
    datasets = {}
    for name, loader in LOADERS.items():
        try:
            datasets[name] = loader()
            print(f"Loaded {name}: {len(datasets[name])} item(s)")
        except FileNotFoundError as e:
            print(f"SKIP {name}: source not present on disk ({e})")

    all_coverage = []
    table_rows: list[tuple[str, str, dict, dict]] = []  # (baseline, dataset, report, coverage)

    for baseline, dataset_names in BASELINE_DATASETS.items():
        for dataset_name in dataset_names:
            if dataset_name not in datasets:
                continue
            items = datasets[dataset_name]
            report, coverage = build_baseline_dataset_report(baseline, dataset_name, items)
            # Don't emit a row we have zero checkpoints for — an all-"missing"
            # (baseline, dataset) pair would otherwise print as a misleading
            # 0.000/0.000/0.000 line that looks like the baseline scored zero,
            # when in fact it was simply never run on this machine. Rows with
            # real non-ok coverage (no_result/too_large) are kept.
            if coverage["status_counts"].get("missing", 0) == coverage["n_total"]:
                print(f"SKIP row {baseline}/{dataset_name}: no checkpoints on this machine")
                continue
            if baseline == "slither":
                metrics.print_report(report)
                metrics.save_report(report, RESULTS_ROOT / f"slither_baseline_{dataset_name}.json")
                all_coverage.append(coverage)
            else:
                metrics.save_report(report, RESULTS_ROOT / f"{baseline}_baseline_{dataset_name}.json")
            table_rows.append((baseline, dataset_name, report, coverage))

    print("\n\n=== Coverage summary (slither) ===")
    header = f"  {'dataset':<20}{'n_ok':>8}{'n_total':>10}{'coverage':>10}"
    print(header)
    for c in all_coverage:
        pct = 100 * c["n_ok"] / c["n_total"] if c["n_total"] else 0.0
        print(f"  {c['dataset']:<20}{c['n_ok']:>8}{c['n_total']:>10}{pct:>9.1f}%")
    for c in all_coverage:
        if c["n_ok"] < c["n_total"]:
            other_statuses = {k: v for k, v in c["status_counts"].items() if k != "ok"}
            print(f"\n  {c['dataset']}: non-ok statuses {other_statuses}")
            reasons_seen = {}
            for s in c["skips"]:
                key = (s["status"], str(s["reason"])[:80])
                reasons_seen[key] = reasons_seen.get(key, 0) + 1
            for (status, reason), count in sorted(reasons_seen.items(), key=lambda x: -x[1])[:5]:
                print(f"    [{status}] x{count}: {reason}")

    # --- Part 3: full ablation table across all 3 baselines ---
    lines = [
        "# Baseline ablation table",
        "",
        "Generated by `eval/build_reports.py` from real checkpointed analysis runs",
        "(Slither: Windows + WSL2 sessions; single_llm/current_thirdeye: local Ollama",
        "via WSL2, `llama3.2:3b`). Web3Bugs only has a Slither row — see coverage notes",
        "above and prior session's documentation for why the LLM baselines were never",
        "run against it.",
        "",
        "Binary precision/recall/F1 are not meaningful pooled across datasets:",
        "SmartBugs-Curated and Web3Bugs have zero negative (likely_safe) examples, so",
        "their precision is mechanically 1.000 whenever recall is nonzero — only",
        "Etherscan-50 has real negative-class signal for a meaningful FP rate.",
        "",
        "| dataset | baseline | model(s) | n_analyzed/n_total | precision | recall | F1 | top categories detected |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for baseline, dataset_name, report, coverage in table_rows:
        b = report["binary"]
        lines.append(
            f"| {dataset_name} | {baseline} | {_model_label(baseline, dataset_name)} | "
            f"{coverage['n_ok']}/{coverage['n_total']} | "
            f"{b['precision']:.3f} | {b['recall']:.3f} | {b['f1']:.3f} | {_top_categories(report)} |"
        )
    table_path = RESULTS_ROOT / "baseline_table.md"
    table_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n\nWrote {table_path}")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
