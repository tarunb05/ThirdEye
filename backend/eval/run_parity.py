"""Hardware-parity check + the 8B ablation, on one fixed contract set.

TWO questions, one script, one sample:

  1. PARITY. Does the same contract get the same verdict on different
     hardware? The shipped n=233 was measured on a 4GB laptop GPU. If a
     GB10 with 119GB flips verdicts, every number in the paper is a
     property of that laptop rather than of the method. Nobody has checked.

  2. THE 8B ABLATION. council.py pins business_logic /
     oracle_price_manipulation / flashloan_mev to llama3.2:3b purely
     because llama3.1:8b does not fit in 4GB of VRAM. Those are the three
     SEMANTIC roles. Restoring the 8B is a one-variable change, and the
     capacity that makes it possible is the only thing this box adds.

Both arms run the SAME contract ids, the SAME seed, and the SAME
_run_one() imported from run_benchmark — so the only difference between
arm A and arm B is OLLAMA_LOGIC_MODEL. Results are written under a
dgx_ prefix and are NEVER merged into the laptop's checkpoint tree.
"""
from __future__ import annotations
import argparse, asyncio, json, os, statistics, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from eval.loaders import thirdeye_bench
from eval.schema import REPO_ROOT

DEFAULT_MANIFEST = REPO_ROOT / "backend" / "eval" / "parity_manifest.json"
OUT = REPO_ROOT / "backend" / "eval" / "results"


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, help="label for this arm, e.g. 3b or 8b")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--manifest", default=None, help="baseline manifest; default is the 24-contract set")
    a = ap.parse_args()

    from eval.run_benchmark import _run_one
    from services import council

    man = json.load(open(a.manifest or DEFAULT_MANIFEST, encoding="utf-8"))
    base = {b["contract_id"]: b for b in man["baseline"]}

    # Resolve ids -> items via the same loader the benchmark uses.
    want = set(base)
    items = []
    seen = set()
    for bucket in sorted({b["bucket"] for b in man["baseline"]}):
        for tier in sorted({b["tier"] for b in man["baseline"] if b["bucket"] == bucket}):
            for it in thirdeye_bench.load(buckets={bucket}, tier=tier):
                if it.contract_id in want and it.contract_id not in seen:
                    seen.add(it.contract_id)
                    items.append(it)
    missing = want - seen
    if missing:
        print(f"[parity] WARNING {len(missing)} ids not resolvable: {sorted(missing)[:3]}")

    logic = os.getenv("OLLAMA_LOGIC_MODEL", "(default llama3.2:3b)")
    print(f"[parity] arm={a.arm}  logic_model={logic}  n={len(items)}  conc={a.concurrency}")

    ckpt = REPO_ROOT / "backend" / "eval" / "checkpoints" / f"parity_{a.arm}"
    ckpt.mkdir(parents=True, exist_ok=True)

    sem = asyncio.Semaphore(a.concurrency)
    rows: list[dict] = []
    t_wall = time.time()

    async def one(it):
        cp = ckpt / f"{it.contract_id}.json"
        if cp.exists():
            return json.load(open(cp, encoding="utf-8"))
        async with sem:
            r = await _run_one(it, "ollama", a.seed, use_arbitration=False)
        b = base[it.contract_id]
        r["baseline_verdict"] = b["verdict"]
        r["baseline_latency_s"] = b.get("latency_s")
        r["bucket"], r["tier"], r["expected"] = b["bucket"], b["tier"], b["expected"]
        r["agrees"] = r["verdict"] == b["verdict"]
        json.dump(r, open(cp, "w"), indent=1)
        mark = "=" if r["agrees"] else "!"
        print(f"  [{mark}] {r['verdict']:<12} was {b['verdict']:<12} "
              f"{r.get('latency_s')}s (laptop {b.get('latency_s')}s)  {it.contract_id[:44]}")
        return r

    rows = await asyncio.gather(*[one(it) for it in items])

    scored = [r for r in rows if r["verdict"] in ("GO", "NO-GO")]
    agree = [r for r in scored if r["agrees"]]
    lat = [r["latency_s"] for r in rows if r.get("latency_s")]
    blat = [r["baseline_latency_s"] for r in rows if r.get("baseline_latency_s")]

    def tier_break():
        out = {}
        for r in scored:
            k = f"{r['bucket']}/{r['tier']}"
            d = out.setdefault(k, {"n": 0, "agree": 0, "flips": []})
            d["n"] += 1
            if r["agrees"]:
                d["agree"] += 1
            else:
                d["flips"].append({"id": r["contract_id"],
                                   "laptop": r["baseline_verdict"], "dgx": r["verdict"],
                                   "expected": r["expected"]})
        return out

    # Correctness of each arm against ground truth, not just agreement.
    def acc(rs, key):
        ok = sum(1 for r in rs
                 if (r[key] == "NO-GO") == (r["expected"] == "vulnerable"))
        return round(ok / len(rs), 3) if rs else None

    rep = {
        "arm": a.arm,
        "logic_model": logic,
        "host": "NVIDIA GB10 (DGX Spark), 119GB unified",
        "n_requested": len(items),
        "n_scored": len(scored),
        "n_inconclusive": len(rows) - len(scored),
        "verdict_agreement_with_laptop": round(len(agree) / len(scored), 3) if scored else None,
        "accuracy_dgx": acc(scored, "verdict"),
        "accuracy_laptop": acc(scored, "baseline_verdict"),
        "median_latency_s": round(statistics.median(lat), 1) if lat else None,
        "median_latency_laptop_s": round(statistics.median(blat), 1) if blat else None,
        "wall_clock_min": round((time.time() - t_wall) / 60, 1),
        "total_api_calls": sum(r.get("api_calls", 0) for r in rows),
        "by_tier": tier_break(),
        "note": ("Separate from the shipped n=233, which was measured on a 4GB "
                 "laptop GPU. Not merged into it. Agreement is verdict-level on "
                 "the identical contract ids and seed."),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    json.dump({"summary": rep, "rows": rows}, open(OUT / f"dgx_parity_{a.arm}.json", "w"), indent=1)

    print(f"\n=== PARITY arm={a.arm} ({logic}) ===")
    print(f"scored                {rep['n_scored']}/{rep['n_requested']}  (inconclusive {rep['n_inconclusive']})")
    print(f"agreement w/ laptop   {rep['verdict_agreement_with_laptop']}")
    print(f"accuracy  DGX/laptop  {rep['accuracy_dgx']} / {rep['accuracy_laptop']}")
    print(f"median latency        {rep['median_latency_s']}s  (laptop {rep['median_latency_laptop_s']}s)")
    print(f"wall clock            {rep['wall_clock_min']} min")
    for k, v in sorted(rep["by_tier"].items()):
        print(f"  {k:<42} {v['agree']}/{v['n']}")
        for fl in v["flips"]:
            print(f"      FLIP {fl['laptop']} -> {fl['dgx']}  (truth {fl['expected']})  {fl['id'][:40]}")


asyncio.run(main())
