"""Arbitration ablation: re-adjudicate the council's NO-GO verdicts.

The paper's core claim is that adversarial arbitration is the precision gate —
it should remove false positives (safe contracts wrongly flagged) without
removing true positives. That claim has never been validly measured: earlier
runs had a drained hosted quota (judge failed open, keeping everything) or hit
the arbiter-config fallback bug (local rubber-stamp judge upholding everything).

This measures it directly and cheaply: take every contract the council-only run
verdicted NO-GO, run ONLY arbitration on it with an explicit backend, and report
how many flips per ground-truth class. Arbitrating just the flagged set costs a
fraction of a full re-run because GO contracts have no findings to arbitrate.

Usage: python -m eval.arbitration_ablation --arb-backend cerebras --limit 30
"""
from __future__ import annotations

import argparse, asyncio, glob, json, time
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

from eval.loaders import thirdeye_bench
from eval.schema import REPO_ROOT

CKPT = REPO_ROOT / "backend" / "eval" / "checkpoints" / "arb_ablation"
SRC = REPO_ROOT / "backend" / "eval" / "checkpoints" / "benchmark" / "ollama_noarb" / "seed0"


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arb-backend", default="cerebras")
    ap.add_argument("--council-backend", default="ollama")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    flagged = []
    for f in glob.glob(str(SRC / "*.json")):
        d = json.load(open(f))
        if d.get("verdict") == "NO-GO":
            flagged.append(d)
    flagged.sort(key=lambda d: d["contract_id"])
    if a.limit:
        flagged = flagged[: a.limit]
    print(f"[arb] {len(flagged)} council NO-GO contracts to re-adjudicate "
          f"(council={a.council_backend}, arbiter={a.arb_backend})")

    by_id = {it.contract_id: it for it in thirdeye_bench.load()}
    CKPT.mkdir(parents=True, exist_ok=True)

    from services.council import run_council
    from services.arbitration import run_arbitration

    rows = []
    for i, d in enumerate(flagged, 1):
        cid = d["contract_id"]
        cp = CKPT / f"{cid.replace('/','_')}.json"
        if cp.exists():
            rows.append(json.load(open(cp))); continue
        item = by_id.get(cid)
        if not item or not item.code_paths[0].exists():
            continue
        code = item.read_code()
        t0 = time.time()
        try:
            council = await run_council(code, backend=a.council_backend, seed=0)
            if council.get("final_verdict") != "NO-GO":
                # Council no longer flags it; nothing for arbitration to do.
                row = {"contract_id": cid, "gt": d["ground_truth"], "council": council.get("final_verdict"),
                       "arbitrated": council.get("final_verdict"), "reviewed": 0, "upheld": 0, "dropped": 0,
                       "flipped": False, "error": None}
            else:
                arb = await run_arbitration(code, council, backend=a.arb_backend, seed=0)
                s = arb.get("arbitration_summary", {})
                row = {"contract_id": cid, "gt": d["ground_truth"], "council": "NO-GO",
                       "arbitrated": arb.get("final_verdict"), "reviewed": s.get("reviewed", 0),
                       "upheld": s.get("upheld", 0), "dropped": s.get("dropped", 0),
                       "flipped": arb.get("final_verdict") == "GO", "error": None}
        except Exception as e:
            row = {"contract_id": cid, "gt": d["ground_truth"], "council": "NO-GO", "arbitrated": None,
                   "reviewed": 0, "upheld": 0, "dropped": 0, "flipped": False, "error": str(e)[:200]}
        row["latency_s"] = round(time.time() - t0, 1)
        # Only checkpoint a real adjudication; an error is transient.
        if not row["error"] and row["arbitrated"]:
            json.dump(row, open(cp, "w"))
        rows.append(row)
        print(f"  [{i}/{len(flagged)}] {cid[:44]:<46} gt={row['gt']:<12} "
              f"NO-GO -> {row['arbitrated']}  reviewed={row['reviewed']} dropped={row['dropped']} "
              f"{row['latency_s']}s" + (f"  ERR:{row['error'][:50]}" if row["error"] else ""))

    ok = [r for r in rows if r.get("arbitrated")]
    safe = [r for r in ok if r["gt"] == "likely_safe"]
    vuln = [r for r in ok if r["gt"] == "vulnerable"]
    fp_fixed = sum(1 for r in safe if r["flipped"])
    tp_lost = sum(1 for r in vuln if r["flipped"])
    print("\n=== ARBITRATION ABLATION ===")
    print(f"adjudicated: {len(ok)}  (safe/FP candidates: {len(safe)}, vulnerable/TP: {len(vuln)})")
    print(f"FALSE POSITIVES corrected : {fp_fixed}/{len(safe)}" + (f"  ({fp_fixed/len(safe)*100:.0f}%)" if safe else ""))
    print(f"TRUE POSITIVES destroyed  : {tp_lost}/{len(vuln)}" + (f"  ({tp_lost/len(vuln)*100:.0f}%)" if vuln else ""))
    print("Verdict: arbitration is a real precision gate only if the first number is high AND the second is low.")
    json.dump(rows, open(REPO_ROOT / "backend" / "eval" / "results" / "arbitration_ablation.json", "w"), indent=2)

asyncio.run(main())
