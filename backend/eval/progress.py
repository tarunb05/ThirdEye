"""One number for "status": percent complete and an ETA, measured.

Runs ON the box. Counts terminal checkpoints against each stage's known
denominator, derives throughput from checkpoint mtimes over a recent window,
and projects a finish time. Prints one compact line per active stage plus a
session roll-up.

    python3 ~/thirdeye/backend/eval/progress.py
    python3 ~/thirdeye/backend/eval/progress.py --json     # machine-readable

Why mtimes rather than parsing the log: a log line is written when a contract
FINISHES, and a crashed or rotated log loses the history. Checkpoints are the
work product, they are timestamped, and they survive everything. Rate is taken
over a trailing window rather than since-start, because a run that has been
resumed has a meaningless lifetime average.

Quarantined rows are reported beside the sound count and never inside it. A
rising quarantine count is the one signal that means stop -- it is how the
2026-09-25 session produced a clean-looking, entirely invalid result -- so it
is on the status line rather than buried.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent            # .../backend/eval
CKPT = ROOT / "checkpoints"

# Denominators. A1's is overridden by --a1-n when calibrate forces a smaller
# corpus, because reporting 62% of 2,250 when the run was deliberately sized to
# 1,400 would be wrong in the direction that matters.
# Order matches scripts/run_all.sh, which is value order, so reading top to
# bottom is reading the pipeline in the order it matters.
STAGES = [
    # key,            label,                       dir glob,                 default n
    ("ctx4k_safe",    "A2 safe ctx  4k",           "ctx_ctx4k_safe",         120),
    ("ctx16k_safe",   "A2 safe ctx 16k",           "ctx_ctx16k_safe",        120),
    ("benchmark",     "A1 full corpus",            "benchmark/{backend}/seed0", 2250),
    ("ctx4k_vuln",    "A3 vuln ctx  4k",           "ctx_ctx4k",               90),
    ("ctx16k_vuln",   "A3 vuln ctx 16k",           "ctx_ctx16k",              90),
    # Contest-level, not slice-level: 102 projects, each capped at 40 slices.
    # Counting slices would report 2,733 and never reach it, since most
    # projects have far fewer than the cap.
    ("web3bugs",      "web3bugs contests",         "web3bugs",               102),
    ("baselines",     "baselines",                 "*/smartbugs_curated/seed0", 429),
    ("ablation",      "AC ablation",               "ablation/seed0/*",        72),
    ("arb",           "arbitration sweep",         "arb_sweep",              455),
    ("seed1",         "A1 seed 1",                 "benchmark/{backend}/seed1", 2250),
    ("seed2",         "A1 seed 2",                 "benchmark/{backend}/seed2", 2250),
]

WINDOW_MIN = 15.0


def _counts(pattern: str) -> tuple[int, int, list[float]]:
    """(sound, quarantined, mtimes of sound rows) across every dir matching."""
    sound, quar, mtimes = 0, 0, []
    for d in sorted(CKPT.glob(pattern)):
        if not d.is_dir():
            continue
        for f in d.glob("*.json"):
            sound += 1
            try:
                mtimes.append(f.stat().st_mtime)
            except OSError:
                pass
        t = d / "_transient"
        if t.is_dir():
            quar += len(list(t.glob("*.json")))
    return sound, quar, mtimes


def _rate_per_min(mtimes: list[float], now: float) -> float | None:
    """Throughput over the trailing window. None when too little has landed to
    say anything -- an ETA from two data points is a guess wearing a number."""
    recent = [m for m in mtimes if now - m <= WINDOW_MIN * 60]
    if len(recent) < 3:
        return None
    span_min = max((now - min(recent)) / 60.0, 0.5)
    return len(recent) / span_min


def _hms(minutes: float) -> str:
    if minutes < 1:
        return "under a minute"
    h, m = divmod(int(round(minutes)), 60)
    return f"{h}h {m:02d}m" if h else f"{m}m"


def stage_status(key: str, label: str, pattern: str, n: int, now: float) -> dict:
    sound, quar, mtimes = _counts(pattern)
    done = min(sound, n)
    pct = 100.0 * done / n if n else 0.0
    rate = _rate_per_min(mtimes, now)
    remaining = max(n - done, 0)
    eta_min = (remaining / rate) if (rate and remaining) else None
    active = bool(mtimes) and (now - max(mtimes)) < 300 if mtimes else False
    return {"key": key, "label": label, "n": n, "done": done, "pct": round(pct, 1),
            "quarantined": quar, "rate_per_min": round(rate, 2) if rate else None,
            "eta_min": round(eta_min, 1) if eta_min else None,
            "active": active,
            "idle_s": int(now - max(mtimes)) if mtimes else None}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a1-n", type=int, default=None,
                    help="A1's real denominator when calibrate sized it below the full 2,250")
    ap.add_argument("--backend", default="ollama_noarb",
                    help="which benchmark backend directory counts as A1. The glob used to "
                         "be benchmark/*/seed0, which SUMMED three different backends and "
                         "reported A1 at 68%% when the real run was at 51%% -- an overstated "
                         "progress bar is worse than none.")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--health", action="store_true",
                    help="also print the per-stage health log (sound/quarantined/aborted)")
    args = ap.parse_args()

    now = time.time()
    rows = []
    for key, label, pattern, n in STAGES:
        if key == "benchmark" and args.a1_n:
            n = args.a1_n
        rows.append(stage_status(key, label, pattern.format(backend=args.backend), n, now))

    if args.json:
        print(json.dumps({"now": now, "stages": rows}, indent=1))
        return 0

    # Session roll-up weights each stage by its own denominator, so the headline
    # percentage tracks work rather than stage count.
    started = [r for r in rows if r["done"] or r["active"]]
    tot_n = sum(r["n"] for r in started) or 1
    tot_done = sum(r["done"] for r in started)
    overall = 100.0 * tot_done / tot_n
    live_eta = max((r["eta_min"] for r in rows if r["active"] and r["eta_min"]), default=None)

    print(f"OVERALL  {overall:.0f}%   {tot_done}/{tot_n}"
          + (f"   ETA {_hms(live_eta)}" if live_eta else "   ETA —"))
    print()
    for r in rows:
        if not r["done"] and not r["active"]:
            print(f"  {r['label']:<18} not started")
            continue
        mark = "RUNNING" if r["active"] else f"idle {r['idle_s']}s"
        eta = _hms(r["eta_min"]) if r["eta_min"] else ("done" if r["done"] >= r["n"] else "—")
        q = f"  QUARANTINED {r['quarantined']}" if r["quarantined"] else ""
        print(f"  {r['label']:<18} {r['pct']:>5.1f}%  {r['done']:>5}/{r['n']:<5} "
              f"{(str(r['rate_per_min']) + '/min') if r['rate_per_min'] else '—':>10}  "
              f"ETA {eta:<10} {mark}{q}")

    # The health log is the only record of a stage that ABORTED. A stage that
    # died at row 400 of 2,250 shows here as 18% and "idle", which is
    # indistinguishable from a stage still waiting its turn -- so when nothing
    # is running, say which it was.
    if args.health or not any(r["active"] for r in rows):
        try:
            from eval.guard import STAGE_LOG
            if STAGE_LOG.exists():
                print()
                print("stage health:")
                for raw in open(STAGE_LOG):
                    raw = raw.strip()
                    if not raw:
                        continue
                    h = json.loads(raw)
                    flag = f"  ABORTED: {h['aborted']}" if h.get("aborted") else ""
                    print(f"  {h.get('label','?'):<28} sound={h.get('sound')} "
                          f"quarantined={h.get('quarantined')} "
                          f"({100 * (h.get('quarantine_rate') or 0):.0f}%){flag}")
        except Exception:  # noqa: BLE001 -- status must never be the thing that crashes
            pass

    worst = max((r["quarantined"] for r in rows), default=0)
    if worst:
        print(f"\n  Quarantine total {worst}. If this climbs between checks, the backend is")
        print("  dying and the run is worthless — kill it, restart ollama, purge, relaunch.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
