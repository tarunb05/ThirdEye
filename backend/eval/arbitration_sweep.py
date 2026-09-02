"""Phase B — arbitration threshold sweep.

The binary arbitration gate measured badly: it corrected 9/12 false positives
but destroyed 12/17 true positives, taking F1 from 0.694 to 0.357. That is one
operating point, not a verdict on the whole idea. The judge already emits a
`calibrated_confidence` alongside its ruling, and the previous experiment threw
that score away.

Here we KEEP the score, derive a monotone P(finding is real):

    p_real = conf        if judge said "real"
    p_real = 1 - conf    if judge said "not_a_bug"

and sweep a threshold tau over it. A contract is NO-GO iff any of its findings
has p_real >= tau. That turns one point into a precision-recall curve and
answers the real question: does ANY operating point beat council-only?

Evaluation is over the WHOLE scored benchmark, not just the arbitrated subset —
contracts the council already cleared stay GO at every tau, so scoring only the
flagged subset would silently inflate every number.

The expensive part (LLM calls) happens once; the sweep itself is pure offline
arithmetic over the cached judge scores.

Usage:
    python -m eval.arbitration_sweep --arb-backend cerebras       # collect
    python -m eval.arbitration_sweep --sweep-only                 # re-sweep cache
"""
from __future__ import annotations

import argparse, asyncio, glob, json, time
from itertools import zip_longest
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

from eval.loaders import thirdeye_bench
from eval.schema import REPO_ROOT

CKPT = REPO_ROOT / "backend" / "eval" / "checkpoints" / "arb_sweep"
BENCH = REPO_ROOT / "backend" / "eval" / "checkpoints" / "benchmark" / "ollama_noarb" / "seed0"
RESULTS = REPO_ROOT / "backend" / "eval" / "results"


def _p_real(verdict: str, conf: float) -> float:
    """Judge emits confidence in its own VERDICT, not in the finding. Convert to
    a single monotone 'this finding is real' score so one threshold orders all
    findings consistently."""
    conf = max(0.0, min(1.0, float(conf or 0.0)))
    return conf if (verdict or "").lower() == "real" else 1.0 - conf


def _load_bench() -> list[dict]:
    rows = []
    for f in glob.glob(str(BENCH / "*.json")):
        try:
            rows.append(json.load(open(f)))
        except Exception:
            continue
    return rows


async def collect(arb_backend: str, council_backend: str, limit: int) -> None:
    bench = _load_bench()
    flagged = sorted([r for r in bench if r.get("verdict") == "NO-GO"], key=lambda r: r["contract_id"])
    # INTERLEAVE by ground truth. contract_id order puts every safe contract
    # (01_*) before every vulnerable one (02_*), so a quota-throttled run that
    # creeps forward over days collects only one class for its entire first
    # half — and the threshold sweep needs BOTH classes to say anything at all.
    # Alternating means a partial run is still a usable, balanced sample.
    safe = [r for r in flagged if r.get("ground_truth") != "vulnerable"]
    vuln = [r for r in flagged if r.get("ground_truth") == "vulnerable"]
    flagged = [r for pair in zip_longest(safe, vuln) for r in pair if r is not None]
    if limit:
        flagged = flagged[:limit]
    print(f"[sweep] {len(flagged)} council NO-GO contracts; arbiter={arb_backend}")
    by_id = {it.contract_id: it for it in thirdeye_bench.load()}
    CKPT.mkdir(parents=True, exist_ok=True)

    from services.council import run_council
    from services.arbitration import run_arbitration

    for i, b in enumerate(flagged, 1):
        cid = b["contract_id"]
        cp = CKPT / f"{cid.replace('/', '_')}.json"
        if cp.exists():
            continue
        item = by_id.get(cid)
        if not item or not item.code_paths[0].exists():
            continue
        code = item.read_code()
        t0 = time.time()
        try:
            council = await run_council(code, backend=council_backend, seed=0)
            if council.get("final_verdict") != "NO-GO":
                row = {"contract_id": cid, "gt": b["ground_truth"], "findings": [],
                       "council_verdict": council.get("final_verdict"), "error": None}
            else:
                arb = await run_arbitration(code, council, backend=arb_backend, seed=0)
                findings = []
                for f in (arb.get("vulnerabilities") or []) + (arb.get("dropped_by_arbitration") or []):
                    a = f.get("arbitration") or {}
                    findings.append({
                        "type": f.get("type"),
                        "judge_verdict": a.get("verdict"),
                        "conf": f.get("confidence"),
                        "p_real": _p_real(a.get("verdict", ""), f.get("confidence", 0.0)),
                        "upheld": bool(f.get("upheld")),
                    })
                row = {"contract_id": cid, "gt": b["ground_truth"], "findings": findings,
                       "council_verdict": "NO-GO", "error": None}
        except Exception as e:
            row = {"contract_id": cid, "gt": b["ground_truth"], "findings": [],
                   "council_verdict": "NO-GO", "error": str(e)[:200]}
        row["latency_s"] = round(time.time() - t0, 1)
        if not row["error"]:
            json.dump(row, open(cp, "w"))
        scores = [f"{f['p_real']:.2f}" for f in row["findings"]]
        print(f"  [{i}/{len(flagged)}] {cid[:42]:<44} gt={row['gt']:<12} "
              f"p_real={scores} {row['latency_s']}s" + (f" ERR:{row['error'][:40]}" if row["error"] else ""))


def sweep() -> dict:
    bench = _load_bench()
    cache = {}
    for f in glob.glob(str(CKPT / "*.json")):
        try:
            r = json.load(open(f)); cache[r["contract_id"]] = r
        except Exception:
            continue
    if not cache:
        print("[sweep] no cached judge scores — run collection first"); return {}

    # COVERAGE GUARD. The sweep scores cached judge decisions against the
    # benchmark's current verdicts. If the benchmark set has moved on (contracts
    # re-run under a new schema, or archived) the two no longer describe the
    # same population, and the resulting numbers are silently wrong rather than
    # obviously broken — observed once as 4/10 splits where the aligned data
    # gave 10/10. Refuse to report below a coverage floor.
    bench_ids = {b["contract_id"] for b in bench if b.get("verdict") in ("GO", "NO-GO")}
    covered = len(set(cache) & bench_ids)
    coverage = covered / len(cache) if cache else 0.0
    if coverage < 0.75:
        msg = (f"cached judge scores cover only {covered}/{len(cache)} of the current benchmark "
               f"({coverage:.0%}) — the arbitrated set and the evaluation set have diverged. "
               f"Re-run collection after the benchmark finishes; not reporting.")
        print(f"[sweep] SKIP — {msg}")
        json.dump({"available": False, "note": msg, "coverage": round(coverage, 3)},
                  open(RESULTS / "arbitration_sweep.json", "w"), indent=2)
        return {}

    def metrics(tau: float | None) -> dict:
        tp = fp = tn = fn = 0
        for b in bench:
            gt, cv = b.get("ground_truth"), b.get("verdict")
            if cv not in ("GO", "NO-GO"):
                continue
            if cv == "NO-GO" and tau is not None and b["contract_id"] in cache:
                fs = cache[b["contract_id"]]["findings"]
                pred_vuln = any(f["p_real"] >= tau for f in fs)
            else:
                pred_vuln = cv == "NO-GO"
            if gt == "vulnerable":
                tp += pred_vuln; fn += not pred_vuln
            else:
                fp += pred_vuln; tn += not pred_vuln
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / (tp + fn) if tp + fn else 0.0
        return {"tau": tau, "tp": tp, "fp": fp, "tn": tn, "fn": fn,
                "precision": round(p, 3), "recall": round(r, 3),
                "f1": round(2 * p * r / (p + r), 3) if p + r else 0.0,
                "fpr_safe": round(fp / (fp + tn), 3) if fp + tn else 0.0}

    base = metrics(None)
    rows = [metrics(t / 20) for t in range(0, 21)]
    best = max(rows, key=lambda r: r["f1"])

    # HELD-OUT tau. The curve above is computed over every contract, so its
    # "best" tau is chosen on the same data it is scored on — optimistic by
    # construction and not reportable as a result. Repeat the selection
    # properly: split contracts stratified by ground truth, pick tau on dev,
    # apply it once to test, and average over random splits so the number does
    # not hang on one lucky partition.
    import random as _random
    ids = sorted({b["contract_id"] for b in bench if b.get("verdict") in ("GO", "NO-GO")})
    gt_of = {b["contract_id"]: b.get("ground_truth") for b in bench}

    def metrics_on(subset: set, tau: float | None) -> dict:
        tp = fp = tn = fn = 0
        for b in bench:
            cid, gt, cv = b["contract_id"], b.get("ground_truth"), b.get("verdict")
            if cv not in ("GO", "NO-GO") or cid not in subset:
                continue
            if cv == "NO-GO" and tau is not None and cid in cache:
                pred = any(f["p_real"] >= tau for f in cache[cid]["findings"])
            else:
                pred = cv == "NO-GO"
            if gt == "vulnerable":
                tp += pred; fn += not pred
            else:
                fp += pred; tn += not pred
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / (tp + fn) if tp + fn else 0.0
        return {"precision": round(p, 3), "recall": round(r, 3),
                "f1": round(2 * p * r / (p + r), 3) if p + r else 0.0,
                "fpr_safe": round(fp / (fp + tn), 3) if fp + tn else 0.0}

    held = []
    for s in range(10):
        rng = _random.Random(s)
        dev, test = set(), set()
        for g in ("vulnerable", "likely_safe"):
            grp = [c for c in ids if gt_of.get(c) == g]
            rng.shuffle(grp)
            k = len(grp) // 2
            dev |= set(grp[:k]); test |= set(grp[k:])
        bt, bf = 0.0, -1.0
        for t in [i / 20 for i in range(21)]:
            m = metrics_on(dev, t)
            if m["f1"] > bf:
                bf, bt = m["f1"], t
        held.append({"split": s, "tau": bt,
                     "test": metrics_on(test, bt),
                     "test_baseline": metrics_on(test, None)})

    print(f"\n{'tau':>5}{'FPR(safe)':>11}{'precision':>11}{'recall':>9}{'F1':>8}")
    print(f"{'none':>5}{base['fpr_safe']:>11.3f}{base['precision']:>11.3f}{base['recall']:>9.3f}{base['f1']:>8.3f}   <- council only")
    for r in rows:
        mark = "  <- best F1" if r is best else ""
        print(f"{r['tau']:>5.2f}{r['fpr_safe']:>11.3f}{r['precision']:>11.3f}{r['recall']:>9.3f}{r['f1']:>8.3f}{mark}")

    import statistics as _st
    mean = lambda k: round(_st.mean([h["test"][k] for h in held]), 3)
    sd = lambda k: round(_st.stdev([h["test"][k] for h in held]), 3)
    bmean = lambda k: round(_st.mean([h["test_baseline"][k] for h in held]), 3)
    wins = sum(1 for h in held if h["test"]["f1"] > h["test_baseline"]["f1"])
    print("\n=== HELD-OUT (tau fit on dev, scored on disjoint test, 10 splits) ===")
    print(f"{'council only  [test]':<30}FPR={bmean('fpr_safe'):.3f}  P={bmean('precision'):.3f}  R={bmean('recall'):.3f}  F1={bmean('f1'):.3f}")
    print(f"{'calibrated arb [test]':<30}FPR={mean('fpr_safe'):.3f}  P={mean('precision'):.3f}  R={mean('recall'):.3f}  F1={mean('f1'):.3f} +/- {sd('f1'):.3f}")
    print(f"improves F1 in {wins}/10 splits; median tau={_st.median([h['tau'] for h in held]):.2f}")

    out = {"council_only": base, "sweep": rows, "best_in_sample_NOT_reportable": best,
           "held_out": held,
           "held_out_summary": {"n_splits": len(held), "wins": wins,
                                "baseline_f1": bmean("f1"), "tuned_f1": mean("f1"),
                                "tuned_f1_std": sd("f1"), "baseline_fpr": bmean("fpr_safe"),
                                "tuned_fpr": mean("fpr_safe")},
           "n_arbitrated": len(cache), "n_scored": base["tp"] + base["fp"] + base["tn"] + base["fn"],
           "note": ("p_real = conf if judge said real else 1-conf. A contract is NO-GO iff any "
                    "finding scores >= tau. Scored over the whole benchmark; council-GO contracts "
                    "are unaffected by tau.")}
    RESULTS.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(RESULTS / "arbitration_sweep.json", "w"), indent=2)
    print(f"\n[in-sample best F1 {best['f1']:.3f} at tau={best['tau']} — NOT reportable: tau was "
          f"chosen on the same data it is scored on. Use the held-out block above.]")
    return out


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arb-backend", default="cerebras")
    ap.add_argument("--council-backend", default="ollama")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--sweep-only", action="store_true")
    a = ap.parse_args()
    if not a.sweep_only:
        await collect(a.arb_backend, a.council_backend, a.limit)
    sweep()

asyncio.run(main())
