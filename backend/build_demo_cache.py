# -*- coding: utf-8 -*-
"""Scan every demo sample locally and record what ACTUALLY happened.

Two jobs, one run:

1. Verify the demo profile is stable. The 7B coder model is 4.68 GB against
   4 GB of VRAM and died with "CUDA error: shared object initialization
   failed" on every scan, erroring one specialist each time. This re-runs with
   whatever OLLAMA_CODER_MODEL is set to and reports the error count, so the
   choice is made on measurement rather than hope.

2. Produce a cached result per sample, written to the frontend as JSON. The
   site is static and deploys anywhere, but a live scan needs this backend
   running. With a cache the tool page still shows a real, previously-measured
   verdict when the backend is absent -- clearly labelled as cached, never
   passed off as live.

The cached verdict is whatever the tool really returned, including the cases
where it disagrees with the sample's expected answer. Those disagreements are
the measured 45.9% false-alarm rate showing up in miniature, and hiding them
would make the demo a lie.

    python -u build_demo_cache.py
    OLLAMA_CODER_MODEL=qwen2.5-coder:3b python -u build_demo_cache.py
"""
import argparse
import asyncio
import json
import os
import pathlib
import time

os.environ.setdefault("LLM_BACKEND", "ollama")

OUT = pathlib.Path(__file__).resolve().parents[1] / "frontend" / "src" / "site" / "demo-cache.json"


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None,
                    help="write elsewhere, so two model profiles can be compared "
                         "without one overwriting the other's evidence")
    args = ap.parse_args()
    out_path = pathlib.Path(args.out) if args.out else OUT

    from services.samples import list_samples
    from services.council import run_council, CODER_MODEL, LOGIC_MODEL
    from services.router import select_specialists
    from services.llm import preanalyze_code

    samples = list_samples()
    print(f"coder={CODER_MODEL}  logic={LOGIC_MODEL}")
    print(f"scanning {len(samples)} samples locally\n")

    out = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "models": {"coder": CODER_MODEL, "logic": LOGIC_MODEL, "dos": "gemma3:4b"},
        "results": {},
    }
    matched = 0
    errored_specialists = 0

    for s in samples:
        features = preanalyze_code(s["code"])
        routed = select_specialists(s["code"], features, None)
        t0 = time.time()
        try:
            r = await run_council(s["code"], roles=routed["roles"])
        except Exception as e:  # noqa: BLE001
            print(f"  {s['name']:<40} FAILED {type(e).__name__}: {e}")
            continue
        dt = time.time() - t0
        stats = r.get("stats") or {}
        n_err = int(stats.get("specialists_errored") or 0)
        errored_specialists += n_err
        verdict = r.get("final_verdict")
        hit = verdict == s["expected"]
        matched += bool(hit)

        out["results"][s["id"]] = {
            "verdict": verdict,
            "expected": s["expected"],
            "agrees": hit,
            "latency_s": round(dt, 1),
            "roles_routed": routed["roles"],
            "specialists_errored": n_err,
            "verdict_reason": r.get("verdict_reason") or "",
            "findings": [
                {
                    "type": v.get("type"),
                    "severity": v.get("severity"),
                    "confidence": v.get("confidence"),
                    "evidence_quote": (v.get("evidence_quote") or "")[:300],
                    "description": (v.get("description") or "")[:400],
                }
                for v in (r.get("vulnerabilities") or [])
            ],
        }
        print(f"  {s['name']:<40} {verdict:<13} {'ok ' if hit else 'DIFFERS'} "
              f"{dt:5.0f}s  {len(routed['roles'])} routed, {n_err} errored")

    out["summary"] = {
        "n": len(out["results"]),
        "agreed": matched,
        "specialist_errors": errored_specialists,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")

    print(f"\n{matched}/{len(out['results'])} agreed with the expected verdict")
    print(f"{errored_specialists} specialist error(s) across the run "
          f"({'CLEAN' if errored_specialists == 0 else 'investigate'})")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
