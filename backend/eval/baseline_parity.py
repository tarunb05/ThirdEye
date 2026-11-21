"""Score the baseline arms on the SAME contracts, and say whether it matters.

THE DEFECT THIS EXISTS FOR. build_reports scores each arm over whatever
checkpoints that arm happens to have (build_reports.py:71), reports per-arm
coverage honestly, and then prints the arms side by side in one ablation table.
Nothing restricts them to a common contract set. So "council 0.78 vs
single_llm 0.71" can be two different benchmarks wearing one table.

WHY IT IS NOT A HYPOTHETICAL. On 2026-10-24 the council arm sat at 278/303
while single_llm had 301. The 25 absent contracts were not a random sample --
they were absent BECAUSE they are the largest, taking ~28 min each against a
corpus median under one minute. Large contracts are plausibly harder, so
dropping them from one arm only is a bias of unknown sign and real size, and
the slither arm on that same box was separately 100% dead. An honest coverage
column does not fix this: the reader sees two coverage numbers and no way to
know what the metric would have been on equal footing.

WHAT THIS REPORTS. Per arm, the metric on its own coverage and on the
intersection of all compared arms, plus the delta. A small delta licenses the
side-by-side table; a large one means the table is not reporting what it
appears to report.

    python -m eval.baseline_parity
    python -m eval.baseline_parity --arms single_llm council --datasets access_control_slice
"""

from __future__ import annotations

import argparse

from eval import metrics
from eval.build_reports import LOADERS, _load_checkpoints, _safe_id

DEFAULT_ARMS = ("slither", "single_llm", "council")
MATERIAL = 2.0  # percentage points of F1/recall worth flagging


def _preds(arm: str, dataset: str, items, restrict: set[str] | None):
    ck = _load_checkpoints(arm, dataset)
    preds, ok = {}, set()
    for item in items:
        c = ck.get(_safe_id(item.contract_id)) or ck.get(item.contract_id)
        if c is None or c.get("status") != "ok":
            continue
        ok.add(item.contract_id)
        if restrict is not None and item.contract_id not in restrict:
            continue
        preds[item.contract_id] = metrics.Prediction(
            contract_id=item.contract_id,
            predicted_label=c["predicted_label"],
            predicted_categories=c.get("predicted_categories", []),
            category_taxonomy="thirdeye",
        )
    return preds, ok


def _b(items, preds, name):
    r = metrics.build_report(items, preds, name, normalize_categories=True)["binary"]
    return {k: 100 * r[k] for k in ("recall", "precision", "f1")} | {"n": len(preds)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", nargs="*", default=list(DEFAULT_ARMS))
    ap.add_argument("--datasets", nargs="*", default=None)
    a = ap.parse_args()

    names = a.datasets or list(LOADERS.keys())
    rc = 0
    for dname in names:
        try:
            items = LOADERS[dname]()
        except (FileNotFoundError, KeyError):
            print(f"SKIP {dname}: source not on this machine")
            continue

        cov = {}
        for arm in a.arms:
            _, ok = _preds(arm, dname, items, None)
            cov[arm] = ok
        live = {k: v for k, v in cov.items() if v}
        if len(live) < 2:
            print(f"SKIP {dname}: fewer than two arms have usable rows "
                  f"({ {k: len(v) for k, v in cov.items()} })")
            continue

        inter = set.intersection(*live.values())
        print(f"\n=== {dname} — {len(items)} items ===")
        for arm, ok in cov.items():
            if not ok:
                print(f"  {arm:<12} 0 usable rows — EXCLUDED from the intersection, and "
                      f"any table showing it alongside the others is comparing nothing")
        print(f"  intersection of {sorted(live)}: {len(inter)} contracts")

        print(f"\n  {'arm':<12}{'own n':>7}{'own F1':>9}{'int F1':>9}{'dF1':>8}"
              f"{'own rec':>9}{'int rec':>9}{'drec':>8}")
        worst = 0.0
        for arm in sorted(live):
            own, _ = _preds(arm, dname, items, None)
            res, _ = _preds(arm, dname, items, inter)
            o, i = _b(items, own, arm), _b(items, res, arm)
            d_f1, d_rec = i["f1"] - o["f1"], i["recall"] - o["recall"]
            worst = max(worst, abs(d_f1), abs(d_rec))
            print(f"  {arm:<12}{o['n']:>7}{o['f1']:>8.1f}%{i['f1']:>8.1f}%{d_f1:>+8.1f}"
                  f"{o['recall']:>8.1f}%{i['recall']:>8.1f}%{d_rec:>+8.1f}")

        missing = {arm: len(ok - inter) for arm, ok in live.items() if ok - inter}
        if missing:
            print(f"\n  rows dropped by the restriction: {missing}")
        if worst >= MATERIAL:
            rc = 1
            print(f"\n  NOT COMPARABLE as printed. Restricting to a common contract set moves")
            print(f"  a headline metric by up to {worst:.1f} points, so the side-by-side table")
            print(f"  is partly reporting coverage differences as tool differences. Report the")
            print(f"  intersection figures, or finish the short arm before publishing.")
        else:
            print(f"\n  COMPARABLE. Max movement {worst:.1f} points (< {MATERIAL}), so the")
            print(f"  side-by-side table is not materially driven by coverage.")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
