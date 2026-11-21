"""Move unsound checkpoints out of the way, using the guard's own rules.

WHY THIS IS NEEDED EXACTLY ONCE. Quarantining (guard.py) stops a backend
failure from ever being written as a result -- but only from now on. Rows
written BEFORE quarantining existed are already sitting in the arm
directories, and every runner resumes with `if cp.exists(): return it`. So a
re-run reuses the poisoned rows verbatim and completes almost instantly,
reporting a clean-looking result built from a backend outage. That is not a
hypothetical: on the campus box as of 2026-10-09,

    ctx_ctx4k_safe    176 rows, 145 INCONCLUSIVE, 173 with errored specialists
    ctx_ctx16k_safe   176 rows, 108 INCONCLUSIVE, 112 with errored specialists

which is the 2026-09-25 incident, preserved on disk and ready to be mistaken
for a finished stage.

NOTHING IS DELETED. Rows move to `_poisoned/` beside the arm, so the incident
stays auditable and nobody has to take this script's word for the counts. The
runners glob only `*.json` in the arm directory itself, so a moved row is
invisible to scoring and WILL be recomputed on the next run.

The soundness test is imported from guard, not re-implemented here. Two
definitions of "is this row a result" is how they drift apart.

    python -m eval.purge --dry-run            # show what would move
    python -m eval.purge --apply              # move it
    python -m eval.purge --apply --only ctx   # just the ctx arms
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from eval import guard

CKPT = Path(__file__).resolve().parent / "checkpoints"

# Which rule applies to which tree. The ctx arms use the STRICTER paired rule
# for the reason given in run_ctx_ablation: a row from six specialists is not
# comparable to its partner from eight, so the asymmetric rule that is correct
# for "is this contract vulnerable" is wrong here.
PAIRED = lambda r: (not r.get("specialists_errored")                       # noqa: E731
                    and (r.get("verdict") or "").upper() in guard.TERMINAL_VERDICTS)
AGGREGATE = guard.aggregate_terminal("detected", "slices_errored")

TREES = [
    ("ctx",       "ctx_*",                       PAIRED),
    ("benchmark", "benchmark/*/seed*",           guard.default_terminal),
    ("parity",    "parity_*",                    guard.default_terminal),
    ("web3bugs",  "web3bugs",                    AGGREGATE),
    ("arb",       "arb_sweep",                   lambda r: not r.get("error")),
]


def sweep(pattern: str, is_sound, apply: bool) -> tuple[int, int, list[str]]:
    kept = moved = 0
    notes: list[str] = []
    for d in sorted(CKPT.glob(pattern)):
        if not d.is_dir():
            continue
        dk = dm = 0
        for f in sorted(d.glob("*.json")):
            try:
                row = json.load(open(f, encoding="utf-8"))
            except Exception:  # noqa: BLE001 — a corrupt row is itself unsound
                row = {}
            if is_sound(row):
                dk += 1
                continue
            dm += 1
            if apply:
                dest = d / "_poisoned" / f.name
                dest.parent.mkdir(parents=True, exist_ok=True)
                f.replace(dest)
        kept += dk
        moved += dm
        if dm:
            notes.append(f"    {d.relative_to(CKPT)}: {dk} sound, {dm} moved")
    return kept, moved, notes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="actually move (default is a dry run)")
    ap.add_argument("--only", default=None, help="limit to one tree: ctx, benchmark, parity, web3bugs, arb")
    a = ap.parse_args()

    if not a.apply:
        print("DRY RUN — nothing will move. Re-run with --apply.\n")

    total_k = total_m = 0
    for name, pattern, rule in TREES:
        if a.only and a.only != name:
            continue
        k, m, notes = sweep(pattern, rule, a.apply)
        if k or m:
            verb = "moved" if a.apply else "would move"
            print(f"{name:<10} {k} sound, {m} {verb}")
            for n in notes:
                print(n)
        total_k += k
        total_m += m

    print(f"\ntotal: {total_k} sound, {total_m} {'moved to _poisoned/' if a.apply else 'would move'}")
    if a.apply and total_m:
        print("Those contracts have no checkpoint now and will be recomputed on the")
        print("next run. The rows themselves are kept under _poisoned/ for the record.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
