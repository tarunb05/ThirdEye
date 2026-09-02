"""
Validates the metrics module itself before trusting it on new data — per
the Phase 0 task: "run the new metrics module against the existing
50-contract Etherscan set and confirm the numbers it produces are sane...
this is a validation step for the metrics code itself, not a real
evaluation result."

Two checks:
1. test_synthetic() — five hand-crafted items with a hand-computed expected
   answer (worked out on paper, asserted exactly). This is the real proof
   the arithmetic is correct.
2. test_etherscan50_heuristic() — runs the real 50-contract set through a
   deliberately crude, deterministic, ground-truth-independent predictor
   (preanalyze_code()'s existing regex feature flags — no Groq/LLM call,
   no peeking at auto_label) just to exercise the metrics module at real
   scale with real class imbalance (44 likely_safe / 6 vulnerable) and real
   multi-category ground truth. The resulting numbers are NOT a real
   evaluation of ThirdEye — they're what a crude heuristic gets, printed
   only to confirm the module doesn't fall over on real-shaped data.

Run: cd backend && python -m eval.sanity_check
"""

from __future__ import annotations

import math

from eval import metrics
from eval.loaders import etherscan50
from eval.schema import EvalItem, VulnCategory


def _approx(a: float, b: float, tol: float = 1e-6) -> bool:
    return math.isclose(a, b, abs_tol=tol)


def test_synthetic() -> bool:
    items = [
        EvalItem("A", "synthetic", [], "vulnerable", [VulnCategory("t", "reentrancy")]),
        EvalItem("B", "synthetic", [], "vulnerable", [VulnCategory("t", "access_control")]),
        EvalItem("C", "synthetic", [], "likely_safe", []),
        EvalItem("D", "synthetic", [], "vulnerable", [VulnCategory("t", "reentrancy"), VulnCategory("t", "access_control")]),
        EvalItem("E", "synthetic", [], "likely_safe", []),
    ]
    preds = {
        "A": metrics.Prediction("A", "vulnerable", ["reentrancy"]),
        "B": metrics.Prediction("B", "likely_safe", []),
        "C": metrics.Prediction("C", "vulnerable", ["reentrancy"]),
        "D": metrics.Prediction("D", "vulnerable", ["reentrancy"]),
        "E": metrics.Prediction("E", "likely_safe", []),
    }
    # Hand-computed expected answer:
    #   binary: TP=2 (A,D) FP=1 (C) TN=1 (E) FN=1 (B)
    #     precision=2/3 recall=2/3 f1=2/3 accuracy=3/5
    #   reentrancy: TP=2 FP=1 FN=0 -> precision=2/3 recall=1.0 f1=0.8
    #   access_control: TP=0 FP=0 FN=2 -> precision=0 recall=0 f1=0
    #   macro: precision=(2/3+0)/2=1/3 recall=(1+0)/2=0.5 f1=(0.8+0)/2=0.4
    #   micro: tp=2 fp=1 fn=2 -> precision=2/3 recall=0.5 f1=4/7≈0.5714
    report = metrics.build_report(items, preds, "synthetic")
    b = report["binary"]
    checks = [
        ("binary tp", b["tp"], 2), ("binary fp", b["fp"], 1),
        ("binary tn", b["tn"], 1), ("binary fn", b["fn"], 1),
        ("binary precision", b["precision"], 2 / 3), ("binary recall", b["recall"], 2 / 3),
        ("binary f1", b["f1"], 2 / 3), ("binary accuracy", b["accuracy"], 3 / 5),
    ]
    cat = report["per_category"]
    checks += [
        ("reentrancy precision", cat["reentrancy"]["precision"], 2 / 3),
        ("reentrancy recall", cat["reentrancy"]["recall"], 1.0),
        ("reentrancy f1", cat["reentrancy"]["f1"], 0.8),
        ("access_control precision", cat["access_control"]["precision"], 0.0),
        ("access_control recall", cat["access_control"]["recall"], 0.0),
        ("access_control f1", cat["access_control"]["f1"], 0.0),
    ]
    a = report["averages"]
    checks += [
        ("macro precision", a["macro_precision"], 1 / 3),
        ("macro recall", a["macro_recall"], 0.5),
        ("macro f1", a["macro_f1"], 0.4),
        ("micro precision", a["micro_precision"], 2 / 3),
        ("micro recall", a["micro_recall"], 0.5),
        ("micro f1", a["micro_f1"], 4 / 7),
    ]

    ok = True
    for name, actual, expected in checks:
        passed = _approx(actual, expected)
        ok = ok and passed
        status = "OK" if passed else "FAIL"
        print(f"  [{status}] {name}: got {actual:.4f}, expected {expected:.4f}")
    return ok


def _heuristic_predict(code: str) -> tuple[list[str], str]:
    """Deliberately crude, deterministic, ground-truth-independent
    predictor for sanity-check purposes only — reuses the existing
    preanalyze_code() regex feature flags, never touches auto_label."""
    from services.llm import preanalyze_code
    f = preanalyze_code(code)
    cats = []
    if f["has_reentrancy_pattern"]:
        cats.append("reentrancy")
    if f["has_selfdestruct"] and not f["has_onlyowner"]:
        cats.append("access_control")
    if f["has_tx_origin"]:
        cats.append("access_control")
    if f["has_unchecked_return"]:
        cats.append("unchecked_low_level_calls")
    label = "vulnerable" if cats else "likely_safe"
    return cats, label


def test_etherscan50_heuristic() -> dict:
    items = etherscan50.load()
    preds = {}
    for item in items:
        if not item.code_paths or not item.code_paths[0].exists():
            continue
        code = item.read_code()
        cats, label = _heuristic_predict(code)
        preds[item.contract_id] = metrics.Prediction(item.contract_id, label, cats)

    report = metrics.build_report(items, preds, "etherscan50 (SANITY CHECK ONLY — crude heuristic, not ThirdEye's real pipeline)")
    metrics.print_report(report)
    return report


if __name__ == "__main__":
    print("=== 1. Synthetic hand-computed check (proves the arithmetic) ===")
    synthetic_ok = test_synthetic()
    print(f"\nSynthetic check: {'ALL PASSED' if synthetic_ok else 'FAILED — DO NOT TRUST eval/metrics.py'}")

    print("\n=== 2. Real-scale sanity check (etherscan50, crude heuristic) ===")
    report = test_etherscan50_heuristic()

    from eval.schema import REPO_ROOT
    out_path = REPO_ROOT / "backend" / "eval" / "results" / "sanity_check_etherscan50.json"
    metrics.save_report(report, out_path)
    print(f"\nSaved to {out_path}")

    if not synthetic_ok:
        raise SystemExit(1)
