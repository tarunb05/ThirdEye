"""Phase C — Slither baseline on the SAME benchmark contracts.

Why this exists: the GPTScan/GPT-4o-mini numbers quoted in the write-up come
from other papers on other datasets. Comparing our recall to theirs is
contextual at best and a reviewer will say so. This runs a real static-analysis
baseline over the identical contracts, identical ground truth, and identical
tier structure, so the comparison is finally apples-to-apples.

Verdict rule (stated because it is a choice, not a law): a contract is
predicted VULNERABLE if Slither reports >=1 finding of High or Medium impact.
Low/Informational/Optimization are ignored — counting them would flag
essentially every contract and produce a meaningless baseline. Contracts that
fail to compile are ABSTENTIONS (excluded from P/R/F1), exactly as an
INCONCLUSIVE scan is for the council; silently scoring them as "safe" would
hand Slither free true-negatives on code it never analyzed.

Usage:
    python -m eval.run_slither_bench --limit-per-tier 25 --sample-seed 0
"""
from __future__ import annotations

import argparse, json, random, time
from collections import defaultdict
from dotenv import load_dotenv
load_dotenv()

from eval.loaders import thirdeye_bench
from eval.schema import REPO_ROOT
from eval.run_benchmark import TIERS, TIER_LABEL, _score_tier

CKPT = REPO_ROOT / "backend" / "eval" / "checkpoints" / "slither_bench"
RESULTS = REPO_ROOT / "backend" / "eval" / "results"

COUNTED_IMPACTS = {"High", "Medium"}


def _predict(code: str) -> tuple[str, int, str | None]:
    """-> (verdict, n_counted_findings, error). Verdict: NO-GO / GO / INCONCLUSIVE."""
    from services.slither import run_slither
    r = run_slither(code)
    if r.get("status") != "completed":
        return "INCONCLUSIVE", 0, (r.get("message") or r.get("status") or "")[:200]
    try:
        data = json.loads(r["output"])
    except Exception as e:
        return "INCONCLUSIVE", 0, f"unparseable slither json: {e}"[:200]
    if not data.get("success", True):
        return "INCONCLUSIVE", 0, "slither reported failure"
    dets = ((data.get("results") or {}).get("detectors") or [])
    n = sum(1 for d in dets if d.get("impact") in COUNTED_IMPACTS)
    return ("NO-GO" if n else "GO"), n, None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit-per-tier", type=int, default=25)
    ap.add_argument("--sample-seed", type=int, default=0)
    a = ap.parse_args()

    CKPT.mkdir(parents=True, exist_ok=True)
    rows_by_tier: dict[tuple, list[dict]] = defaultdict(list)
    total = done = 0

    for bucket, tier, expected in TIERS:
        items = thirdeye_bench.load(buckets={bucket}, tier=tier)
        items = [it for it in items if it.code_paths and it.code_paths[0].exists()]
        if a.limit_per_tier > 0:
            # Identical nested stratified sample as run_benchmark, so this
            # baseline covers exactly the same contracts as the council run.
            rng = random.Random(f"{a.sample_seed}:{bucket}:{tier}")
            items = list(items); rng.shuffle(items); items = items[: a.limit_per_tier]
        total += len(items)

        for it in items:
            cp = CKPT / f"{it.contract_id.replace('/', '_')}.json"
            if cp.exists():
                try:
                    rows_by_tier[(bucket, tier, expected)].append(json.load(open(cp))); done += 1; continue
                except Exception:
                    pass
            t0 = time.time()
            verdict, n, err = _predict(it.read_code())
            row = {
                "contract_id": it.contract_id,
                "ground_truth": it.ground_truth_label,
                "verdict": verdict,
                "predicted": {"NO-GO": "vulnerable", "GO": "likely_safe"}.get(verdict),
                "n_findings": n, "error": err,
                "latency_s": round(time.time() - t0, 1),
                "bucket": bucket, "tier": tier, "expected": expected,
            }
            # Compile failures are transient-ish (wrong solc pick) — don't bake
            # them in as terminal results.
            if verdict in ("GO", "NO-GO"):
                json.dump(row, open(cp, "w"))
            rows_by_tier[(bucket, tier, expected)].append(row)
            done += 1
            print(f"  [{done}/{total}] {tier:<26} {it.contract_id[:38]:<40} "
                  f"gt={it.ground_truth_label:<12} -> {verdict:<12} findings={n} {row['latency_s']}s"
                  + (f" ERR:{err[:40]}" if err else ""))

    per_tier, safe_rows, vuln_rows, all_rows = {}, [], [], []
    for (bucket, tier, expected), rows in rows_by_tier.items():
        t = _score_tier(rows, expected)
        t["label"] = TIER_LABEL.get(tier, tier); t["expected"] = expected; t["bucket"] = bucket
        per_tier[tier] = t
        all_rows += rows
        (safe_rows if expected == "safe" else vuln_rows).append(rows)

    flat = lambda ls: [r for sub in ls for r in sub]
    report = {
        "tool": "slither", "verdict_rule": "NO-GO iff >=1 High/Medium impact detector",
        "n_total": len(all_rows), "per_tier": per_tier,
        "safe_aggregate": _score_tier(flat(safe_rows), "safe"),
        "vuln_aggregate": _score_tier(flat(vuln_rows), "vulnerable"),
        "overall": _score_tier(all_rows, "mixed"),
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    json.dump(report, open(RESULTS / "slither_bench.json", "w"), indent=2)

    print("\n| slice | n | scored | inconcl. | TP | FP | TN | FN | precision | recall | F1 |")
    print("|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|")
    for name, t in (("SAFE", report["safe_aggregate"]), ("VULN", report["vuln_aggregate"]), ("OVERALL", report["overall"])):
        print(f"| {name} | {t.get('n')} | {t.get('scored')} | {t.get('inconclusive')} | {t.get('tp')} | "
              f"{t.get('fp')} | {t.get('tn')} | {t.get('fn')} | {t.get('precision')} | {t.get('recall')} | {t.get('f1')} |")
    print(f"\nwrote {RESULTS / 'slither_bench.json'}")


main()
