"""Find the concurrency that actually maximises throughput on this host.

Ten minutes here buys hours on a full-corpus run, and it protects against a
failure that is worse than slowness. Contract concurrency multiplied by eight
specialists is the real request rate at Ollama. If that exceeds
OLLAMA_NUM_PARALLEL, the surplus QUEUES, and queue wait counts against the
client-side deadline. A blown deadline fails closed to INCONCLUSIVE and
quarantines the contract -- and the calls that blow it are the large, complex
ones. The discards are not random, so over-concurrency does not merely slow the
run, it biases the scored sample toward simple code while the tables still look
healthy. That exact mechanism was measured once already: 9 INCONCLUSIVE in 39
contracts, deaths clustered at 303.0 s, 303.4 s and 405.4 s.

So this reports two things per level, and the second one is the veto:

    throughput   contracts/min -- what you are optimising
    p95 latency  against LLM_TIMEOUT -- what you must not approach

The recommendation is the knee of the throughput curve, backed off one level if
p95 is within 60% of the timeout.

Usage:
    python -m eval.calibrate                      # 12 contracts, levels 2..24
    python -m eval.calibrate --n 16 --levels 4,8,16,32
    python -m eval.calibrate --n 8 --levels 4,8 --num-ctx 16384

Nothing is checkpointed: these runs are throwaway measurements, and writing
them would let a calibration row be scored as a result later.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import random
import statistics
import time

from dotenv import load_dotenv
load_dotenv()

from eval.loaders import thirdeye_bench
from eval.provenance import collect as collect_provenance, summarise as provenance_line


async def _one(item, backend: str, seed: int) -> tuple[float, str, int]:
    """One contract, timed. Returns (seconds, verdict, specialists_errored)."""
    from services.pipeline import run_thirdeye
    t0 = time.time()
    verdict, errored = "ERROR", 0
    try:
        r = await run_thirdeye(item.read_code(), backend=backend, seed=seed,
                               use_static_router=True, use_retrieval=False,
                               use_arbitration=False, use_dynamic=False)
        verdict = r.get("final_verdict", "INCONCLUSIVE")
        errored = (r.get("stats") or {}).get("specialists_errored", 0)
    except Exception:  # noqa: BLE001 — a calibration run must not raise
        pass
    return round(time.time() - t0, 1), verdict, errored


async def level(items, conc: int, backend: str, seed: int) -> dict:
    sem = asyncio.Semaphore(conc)

    async def bounded(it):
        async with sem:
            return await _one(it, backend, seed)

    t0 = time.time()
    results = await asyncio.gather(*[bounded(i) for i in items])
    wall = time.time() - t0

    lat = sorted(r[0] for r in results)
    bad = sum(1 for r in results if r[1] in ("INCONCLUSIVE", "ERROR"))
    errored = sum(1 for r in results if r[2])
    return {
        "concurrency": conc,
        "n": len(items),
        "wall_s": round(wall, 1),
        "throughput_per_min": round(60 * len(items) / wall, 2) if wall else None,
        "median_s": statistics.median(lat) if lat else None,
        "p95_s": lat[int(0.95 * (len(lat) - 1))] if lat else None,
        "max_s": lat[-1] if lat else None,
        "inconclusive": bad,
        "with_errored_specialist": errored,
    }


def recommend(rows: list[dict], timeout_s: float) -> tuple[int, str]:
    """Knee of the throughput curve, vetoed by latency and by abstentions.

    A level that abstains is disqualified outright whatever its throughput: an
    abstention at calibration time is a contract the real run would silently
    drop, and dropping the hard ones is exactly the bias this guards against.
    """
    ok = [r for r in rows if not r["inconclusive"]]
    if not ok:
        return rows[0]["concurrency"], ("every level produced an abstention — the backend is "
                                        "unhealthy or OLLAMA_NUM_PARALLEL is far too low. "
                                        "Do not start a long run.")
    best = max(ok, key=lambda r: r["throughput_per_min"] or 0)

    # Knee: the cheapest level within 10% of peak throughput. Buying 5% more
    # throughput with double the queue depth is a bad trade -- the queue is
    # what turns into biased discards when anything goes wrong mid-run.
    peak = best["throughput_per_min"] or 0
    knee = min((r for r in ok if (r["throughput_per_min"] or 0) >= 0.9 * peak),
               key=lambda r: r["concurrency"])

    note = f"knee at {knee['concurrency']} ({knee['throughput_per_min']}/min, {int(100 * (knee['throughput_per_min'] or 0) / peak)}% of peak)"
    if knee["p95_s"] and knee["p95_s"] > 0.6 * timeout_s:
        lower = [r for r in ok if r["concurrency"] < knee["concurrency"]]
        if lower:
            backed = max(lower, key=lambda r: r["concurrency"])
            return backed["concurrency"], (f"{note}, but p95 {knee['p95_s']}s is over 60% of the "
                                           f"{int(timeout_s)}s timeout — backed off to "
                                           f"{backed['concurrency']}")
    return knee["concurrency"], note


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=12, help="contracts per level")
    ap.add_argument("--levels", default="2,4,8,16,24",
                    help="comma-separated contract-concurrency levels to try")
    ap.add_argument("--backend", default="ollama")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--sample-seed", type=int, default=7)
    args = ap.parse_args()

    levels = [int(x) for x in args.levels.split(",") if x.strip()]
    timeout_s = float(os.getenv("LLM_TIMEOUT", "240"))

    from services.council import specialist_assignments
    models = sorted({m for _p, m in specialist_assignments(args.backend).values()})
    prov = collect_provenance(models, extra={"run": "calibrate"})
    print(provenance_line(prov))
    print(f"[calibrate] COUNCIL_MAX_CONCURRENCY={os.getenv('COUNCIL_MAX_CONCURRENCY', 'default')} "
          f"OLLAMA_NUM_PARALLEL={os.getenv('OLLAMA_NUM_PARALLEL', 'unset')} "
          f"OLLAMA_MODELS_RESIDENT={os.getenv('OLLAMA_MODELS_RESIDENT', 'unset')} "
          f"LLM_TIMEOUT={timeout_s:.0f}s")

    # A fixed, mixed sample: both labels, so a level cannot look fast by drawing
    # only short safe contracts.
    items = thirdeye_bench.load()
    rng = random.Random(args.sample_seed)
    safe = [i for i in items if i.ground_truth_label != "vulnerable"]
    vuln = [i for i in items if i.ground_truth_label == "vulnerable"]
    rng.shuffle(safe)
    rng.shuffle(vuln)
    half = max(1, args.n // 2)
    sample = (safe[:half] + vuln[:args.n - half])
    print(f"[calibrate] {len(sample)} contracts ({half} safe, {len(sample) - half} vulnerable), "
          f"same sample at every level\n")

    print(f"  {'conc':>5} {'wall':>8} {'per min':>9} {'median':>8} {'p95':>8} {'max':>8} "
          f"{'incon':>6} {'errspec':>8}")
    print("  " + "-" * 70)

    rows = []
    for c in levels:
        r = await level(sample, c, args.backend, args.seed)
        rows.append(r)
        print(f"  {r['concurrency']:>5} {r['wall_s']:>7.1f}s {r['throughput_per_min']:>9} "
              f"{r['median_s']:>7}s {r['p95_s']:>7}s {r['max_s']:>7}s "
              f"{r['inconclusive']:>6} {r['with_errored_specialist']:>8}")
        # Climbing abstentions mean the backend is already saturated. Going
        # higher only produces more biased discards, so stop.
        if r["inconclusive"] > len(sample) // 4:
            print(f"\n  stopping: {r['inconclusive']}/{len(sample)} abstained at concurrency "
                  f"{c}. Higher levels would only discard more of the hard contracts.")
            break

    best, why = recommend(rows, timeout_s)
    print("\n  " + "-" * 70)
    print(f"  RECOMMENDED  --concurrency {best}")
    print(f"  {why}")
    peak = max((r['throughput_per_min'] or 0) for r in rows)
    if peak:
        print(f"\n  At {best}, a 2,250-contract pass is about "
              f"{2250 / (next(r['throughput_per_min'] for r in rows if r['concurrency'] == best) or 1) / 60:.1f} h; "
              f"web3bugs' 2,733 slices about "
              f"{2733 / (next(r['throughput_per_min'] for r in rows if r['concurrency'] == best) or 1) / 60:.1f} h.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
