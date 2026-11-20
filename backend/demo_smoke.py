# -*- coding: utf-8 -*-
"""End-to-end local smoke test: does a real scan work on THIS laptop?

Runs the shipped pipeline (router -> council -> evidence gate -> verdict) over
the demo samples with no API key and no network, and prints the verdict, the
latency and whether it matched the expected answer. This is the check that
decides whether the live demo is safe to attempt in a room.

    python -u demo_smoke.py            # two contrasting samples
    python -u demo_smoke.py --all      # the whole demo set
"""
import argparse
import asyncio
import os
import sys
import time

os.environ.setdefault("LLM_BACKEND", "ollama")

from services.samples import list_samples  # noqa: E402


async def scan(code: str):
    from services.council import run_council
    from services.router import select_specialists
    from services.llm import preanalyze_code

    # Same two calls main.py makes, so this measures the shipped path and not
    # a convenience approximation of it.
    features = preanalyze_code(code)
    routed = select_specialists(code, features, None)
    roles = routed["roles"]

    t0 = time.time()
    result = await run_council(code, roles=roles)
    return result, time.time() - t0, roles


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()

    samples = list_samples()
    if not a.all:
        # One that must come back clean, one that must not.
        pick = {"safe-guarded-withdraw", "reentrancy-bank"}
        samples = [s for s in samples if s["id"] in pick]

    print(f"LOCAL-ONLY smoke test — {len(samples)} sample(s), no API key, no network\n")
    ok = 0
    for s in samples:
        print(f"-> {s['name']}  (expect {s['expected']})")
        try:
            result, dt, roles = await scan(s["code"])
        except Exception as e:  # noqa: BLE001
            print(f"   FAILED: {type(e).__name__}: {e}\n")
            continue
        verdict = result.get("final_verdict")
        vulns = result.get("vulnerabilities") or []
        stats = result.get("stats") or {}
        match = "MATCH" if verdict == s["expected"] else "MISMATCH"
        if verdict == s["expected"]:
            ok += 1
        print(f"   verdict {verdict}  [{match}]   {dt:.0f}s   "
              f"{len(roles or [])} specialists routed, "
              f"{stats.get('specialists_run', '?')} ran, "
              f"{stats.get('specialists_errored', '?')} errored")
        for v in vulns[:3]:
            q = (v.get("evidence_quote") or "").strip().replace("\n", " ")[:60]
            print(f"      - {v.get('type')} conf={v.get('confidence')}  {q!r}")
        print()

    print(f"{ok}/{len(samples)} matched the expected verdict")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
