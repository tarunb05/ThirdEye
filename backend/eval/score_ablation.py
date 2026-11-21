"""Re-score the ablation table with the asymmetric soundness rule applied.

WHY THIS EXISTS. run_ablation's guard admits a row on `ok` alone -- the cell
ran without raising an exception. That is the right gate for "did the pipeline
execute", and the wrong one for "may this cell enter a comparison", because it
ignores council health. It had to ignore it: until 2026-10-23 the ablation rows
did not record health at all.

They do now, and the first contaminated row the field caught shows exactly why
it matters. On sb_smart_billions.sol, 1 of 5 specialists errored in both
council arms:

    council               pred=True   is_ac=False  ->  FP
    council+arbitration   pred=False  is_ac=False  ->  TN

Read naively, arbitration converted a false positive into a true negative --
the single most favourable cell it has in the table. But a dead specialist can
only fail to raise a flag, never invent one, so the two predictions are not
equally trustworthy:

  * pred=True  with an errored specialist is SOUND. The flag was raised despite
    a missing voice; the missing voice cannot have caused it.
  * pred=False with an errored specialist is UNSOUND. The absence of a flag is
    exactly what a dead specialist produces, so arbitration's apparent save is
    indistinguishable from a specialist that never ran.

Scoring that cell as a win for arbitration credits the mechanism with the
outcome of a failure. This script reports the table both ways, so the
difference is visible instead of assumed.

    python -m eval.score_ablation
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

CKPT = Path(__file__).resolve().parent / "checkpoints" / "ablation"


def _sound(row: dict) -> bool:
    """The asymmetric rule at the ablation level.

    A row with no health field is UNKNOWN, not healthy -- the same three-state
    rule eval/audit.py uses. Rows written before health was recorded therefore
    drop out of the strict table rather than silently passing it.
    """
    if not row.get("ok"):
        return False
    if "specialists_errored" not in row:
        return False
    if not row["specialists_errored"]:
        return True
    # Errored: only a POSITIVE prediction survives.
    return bool(row.get("pred"))


def _confusion(rows: list[dict]) -> tuple[int, int, int, int]:
    tp = fp = tn = fn = 0
    for r in rows:
        actual, pred = bool(r.get("is_ac")), bool(r.get("pred"))
        if actual and pred:
            tp += 1
        elif actual and not pred:
            fn += 1
        elif not actual and pred:
            fp += 1
        else:
            tn += 1
    return tp, fp, tn, fn


def _rates(tp: int, fp: int, tn: int, fn: int) -> tuple[float, float, float, float]:
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    fpr = fp / (fp + tn) if fp + tn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return prec * 100, rec * 100, fpr * 100, f1


def main() -> int:
    arms: dict[str, list[dict]] = defaultdict(list)
    for f in sorted(CKPT.glob("*/*/*.json")):
        try:
            row = json.load(open(f, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        row["_cid"] = f.stem
        arms[f.parent.name].append(row)

    if not arms:
        print("no ablation checkpoints found")
        return 1

    print("=" * 92)
    print("ABLATION — scored as-run (ok only) vs with the asymmetric rule applied")
    print("  as-run  : every cell that executed")
    print("  sound   : drops pred=False cells from a council with an errored specialist,")
    print("            because that is precisely what a dead specialist produces")
    print("=" * 92)

    # PAIRED: only contracts present and usable in EVERY arm may be compared.
    names = sorted(arms)
    by_cid: dict[str, dict[str, dict]] = defaultdict(dict)
    for arm, rows in arms.items():
        for r in rows:
            by_cid[r["_cid"]][arm] = r
    complete = [c for c, d in by_cid.items() if len(d) == len(names)]
    sound_cids = [c for c in complete if all(_sound(by_cid[c][a]) for a in names)]

    print(f"\ncontracts: {len(by_cid)} seen, {len(complete)} complete in all "
          f"{len(names)} arms, {len(sound_cids)} sound in all arms")
    dropped = len(complete) - len(sound_cids)
    if dropped:
        print(f"  *** {dropped} complete contract(s) dropped by the soundness rule ***")
        for c in complete:
            if c not in sound_cids:
                detail = "  ".join(
                    f"{a}:pred={by_cid[c][a].get('pred')},err={by_cid[c][a].get('specialists_errored')}"
                    for a in names)
                print(f"      {c[:44]}  {detail}")

    for label, cids in (("as-run (paired, ok only)", complete),
                        ("sound  (paired, asymmetric)", sound_cids)):
        print(f"\n{label}   n={len(cids)}")
        print(f"  {'arm':<24}{'tp':>4}{'fp':>4}{'tn':>4}{'fn':>4}"
              f"{'prec':>9}{'recall':>9}{'FPR':>9}{'F1':>8}")
        for arm in names:
            tp, fp, tn, fn = _confusion([by_cid[c][arm] for c in cids])
            pr, rc, fpr, f1 = _rates(tp, fp, tn, fn)
            print(f"  {arm:<24}{tp:>4}{fp:>4}{tn:>4}{fn:>4}"
                  f"{pr:>8.1f}%{rc:>8.1f}%{fpr:>8.1f}%{f1:>8.3f}")

    print("\nA cell that differs between the two tables is a cell whose value "
          "depends on\ncounting a dead specialist's silence as a judgement.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
