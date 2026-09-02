"""
ThirdEye Dataset Runner
Batch-analyzes the etherscan-verified .sol dataset using the full ThirdEye pipeline.
Results are written back to datasets/index.json and datasets/results_summary.csv.

Usage:
    cd backend
    python dataset_runner.py [--limit N] [--static-only]

    --limit N        Only run the first N contracts (default: all)
    --static-only    Skip LLM/Slither; run only preanalyze_code as a smoke test
                      (does it parse without crashing?) — NOT an evaluation.
                      It does not produce an accuracy number: see
                      run_smoke_test()'s docstring for why. For a real
                      accuracy number, use the metrics module in eval/ against
                      a full_pipeline run, or against one of the benchmark
                      datasets in eval/loaders/.
"""

import asyncio
import json
import csv
import hashlib
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent
DATASET_INDEX = BASE_DIR / "datasets" / "index.json"
RESULTS_CSV = BASE_DIR / "datasets" / "results_summary.csv"
SOL_ROOT = BASE_DIR / "datasets" / "etherscan_verified"


def load_index() -> dict:
    with open(DATASET_INDEX) as f:
        return json.load(f)


def save_index(data: dict):
    with open(DATASET_INDEX, "w") as f:
        json.dump(data, f, indent=2)


def resolve_sol_path(entry: dict) -> Path | None:
    p = SOL_ROOT / entry["filename"]
    if p.exists():
        return p
    return None


async def run_smoke_test(code: str, entry: dict) -> dict:
    """Fast, offline check that the pipeline can parse this contract — NOT an
    evaluation. This used to be called run_static_only() and fabricated a
    "prediction" directly from entry["auto_label"]/entry["vuln_types"] — the
    same ground-truth fields compare_verdict() then checked it against. That
    produced a meaningless ~100% "accuracy" number (a label compared to
    itself). This version makes no prediction at all: final_verdict is an
    explicit NOT_EVALUATED sentinel so it can never be scored as a match.
    """
    from services.llm import preanalyze_code
    features = preanalyze_code(code)
    return {
        "final_verdict": "NOT_EVALUATED",
        "vulnerabilities": [],
        "summary": f"Smoke test only for {entry['contract_name']} — preanalyze_code ran without crashing. No prediction was made.",
        "raven_note": None,
        "contract_name": features["contract_name"] or entry["contract_name"],
        "features_detected": {k: v for k, v in features.items() if v and k not in ("solidity_version", "contract_name")},
        "stats": {"models_run": 0, "raw_llm_findings": 0, "slither_findings": 0,
                  "final_findings": 0, "similar_in_db": 0},
        "slither": {"status": "skipped"},
        "mode": "smoke_test",
    }


async def analyze_contract(entry: dict, static_only: bool = False) -> dict | None:
    sol_path = resolve_sol_path(entry)
    if sol_path is None:
        print(f"  [SKIP] {entry['id']}: file not found")
        return None

    with open(sol_path, encoding="utf-8", errors="ignore") as f:
        code = f.read()

    if static_only:
        result = await run_smoke_test(code, entry)
    else:
        from services.llm import run_full_analysis
        from services.vectordb import store_analysis, find_similar
        try:
            similar = find_similar(code)
            result = await run_full_analysis(code, similar)
            code_hash = hashlib.sha256(code.encode()).hexdigest()[:12]
            store_analysis(code_hash, code, result)
            result["mode"] = "full_pipeline"
        except Exception as e:
            print(f"  [WARN] {entry['id']} full analysis failed: {e}. Falling back to smoke test.")
            result = await run_smoke_test(code, entry)

    return result


def compare_verdict(entry: dict, result: dict) -> dict:
    if result.get("mode") == "smoke_test":
        # No prediction was made — nothing to compare. Returning match=None
        # (not True/False) so callers can't silently fold this into an
        # accuracy count, which is exactly the bug this replaces.
        return {
            "match": None,
            "note": "smoke_test mode makes no prediction; not an evaluation result",
            "expected_label": entry.get("auto_label", "unknown"),
            "predicted_label": None,
            "expected_verdict": "NO-GO" if entry.get("auto_label") == "vulnerable" else "GO",
            "predicted_verdict": "NOT_EVALUATED",
            "expected_vuln_types": entry.get("vuln_types", []),
            "predicted_vuln_types": [],
            "type_overlap": [],
        }

    predicted = result.get("final_verdict", "GO")
    expected_label = entry.get("auto_label", "unknown")
    predicted_label = "vulnerable" if predicted == "NO-GO" else "likely_safe"

    predicted_types = {v.get("type", "").lower() for v in result.get("vulnerabilities", [])}
    expected_types = set(entry.get("vuln_types", []))

    match = predicted_label == expected_label
    type_overlap = predicted_types & expected_types

    return {
        "match": match,
        "expected_label": expected_label,
        "predicted_label": predicted_label,
        "expected_verdict": "NO-GO" if expected_label == "vulnerable" else "GO",
        "predicted_verdict": predicted,
        "expected_vuln_types": list(expected_types),
        "predicted_vuln_types": list(predicted_types),
        "type_overlap": list(type_overlap),
    }


def write_csv(entries: list[dict]):
    fieldnames = [
        "id", "contract_name", "source", "auto_label", "vuln_types",
        "predicted_verdict", "predicted_label", "match",
        "predicted_vuln_types", "type_overlap", "expected_severity",
        "final_findings", "mode", "timestamp",
    ]
    with open(RESULTS_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for e in entries:
            cmp = e.get("comparison", {})
            res = e.get("analysis_result") or {}
            w.writerow({
                "id": e["id"],
                "contract_name": e["contract_name"],
                "source": e["source"],
                "auto_label": e["auto_label"],
                "vuln_types": "|".join(e.get("vuln_types", [])),
                "predicted_verdict": cmp.get("predicted_verdict", ""),
                "predicted_label": cmp.get("predicted_label", ""),
                "match": cmp.get("match", ""),
                "predicted_vuln_types": "|".join(cmp.get("predicted_vuln_types", [])),
                "type_overlap": "|".join(cmp.get("type_overlap", [])),
                "expected_severity": e.get("expected_severity", ""),
                "final_findings": res.get("stats", {}).get("final_findings", 0),
                "mode": res.get("mode", ""),
                "timestamp": e.get("analysis_timestamp", ""),
            })


async def main(limit: int | None = None, static_only: bool = False):
    from db import init_db
    await init_db()

    data = load_index()
    contracts = data["contracts"]
    if limit:
        contracts = contracts[:limit]

    total = len(contracts)
    print(f"\n[ThirdEye Dataset Runner]")
    print(f"Mode: {'smoke-test (no prediction, parse-only)' if static_only else 'full pipeline (LLM + Slither)'}")
    print(f"Contracts to process: {total}\n")

    correct = 0
    processed = 0

    for i, entry in enumerate(contracts):
        print(f"[{i+1}/{total}] {entry['id']} — {entry['contract_name']} ({entry['auto_label']})")
        result = await analyze_contract(entry, static_only=static_only)
        if result is None:
            continue

        entry["analysis_result"] = result
        entry["analysis_timestamp"] = datetime.utcnow().isoformat()
        entry["comparison"] = compare_verdict(entry, result)

        cmp = entry["comparison"]
        if cmp["match"] is None:
            status = "SKIPPED (smoke test)"
        else:
            status = "OK" if cmp["match"] else "MISS"
        print(f"  [{status}] expected={cmp['expected_verdict']} predicted={cmp['predicted_verdict']} | vulns={cmp['predicted_vuln_types']}")

        if cmp["match"]:
            correct += 1
        processed += 1

    data["contracts"] = contracts
    data["last_run"] = datetime.utcnow().isoformat()
    if static_only:
        data["run_stats"] = {
            "total_processed": processed,
            "correct_verdicts": None,
            "accuracy": None,
            "mode": "smoke_test",
            "note": "smoke_test mode makes no prediction — it only verifies the pipeline parses every "
                    "contract without crashing. It does not produce an accuracy number. Run without "
                    "--static-only, or use eval/ against a benchmark dataset, for a real evaluation.",
        }
    else:
        data["run_stats"] = {
            "total_processed": processed,
            "correct_verdicts": correct,
            "accuracy": round(correct / processed, 3) if processed else 0,
            "mode": "full_pipeline",
        }
    save_index(data)
    write_csv(contracts)

    print(f"\n[Results]")
    print(f"  Processed: {processed}")
    if static_only:
        print(f"  Mode was smoke_test — no accuracy number was computed (see run_stats.note).")
    else:
        print(f"  Correct verdicts: {correct}/{processed} ({round(correct/processed*100 if processed else 0, 1)}%)")
    print(f"  Results saved to: {DATASET_INDEX}")
    print(f"  CSV saved to: {RESULTS_CSV}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ThirdEye Dataset Runner")
    parser.add_argument("--limit", type=int, default=None, help="Max contracts to analyze")
    parser.add_argument("--static-only", action="store_true", help="Skip LLM, use static analysis only")
    args = parser.parse_args()
    asyncio.run(main(limit=args.limit, static_only=args.static_only))
