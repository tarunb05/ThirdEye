"""Decide, OUT OF SAMPLE, whether excluding `business_logic` is a real win.

THE HYPOTHESIS, and why it needs this script. On seed 0 we observed that
`business_logic` -- a specialist the static router fires on every contract --
places 52% of its findings on safe contracts, accounts for roughly a third of
all false findings, and that excluding it from aggregation improves the
recall/FPR trade by more than any threshold change (+8.3 points of recall at
matched false-alarm rate).

That hypothesis was SELECTED BY INSPECTING SEED 0. Scoring it on seed 0 would
measure how well we fitted seed 0. A paper whose thesis is that evaluation
setup determines the answer cannot ship a configuration tuned on its own test
set, so the claim is only reportable if it reproduces on seeds the hypothesis
never saw.

WHAT COUNTS AS CONFIRMATION. Three things, and the script reports each
separately rather than collapsing them into one verdict:

  1. The FP rate of `business_logic` findings replicates (~52% on seed 0). This
     is the mechanism.
  2. Excluding the class improves Youden's J at matched τ. This is the effect.
  3. The improvement is directionally consistent on BOTH held-out seeds. Two
     seeds agreeing is weak evidence; two seeds disagreeing is a refutation,
     and that outcome must be reportable too.

A smaller effect out of sample is the expected result, not a failure -- the
seed-0 figure is an upper bound because the class was chosen there. What would
refute the claim is the sign flipping, or the mechanism (1) not replicating.

    python -m eval.validate_droplogic              # all seeds found
    python -m eval.validate_droplogic --seeds 1 2  # held-out only
"""

from __future__ import annotations

import argparse
import glob
import json
import math
import os
from collections import defaultdict

from eval import guard

CKPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "checkpoints")
DROP = "business_logic"
TAUS = (0.925, 0.99)


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if not n:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - m) / d * 100, (c + m) / d * 100)


def load(seed: int) -> list[dict]:
    rows = []
    for f in glob.glob(os.path.join(CKPT, "benchmark", "*", f"seed{seed}", "*.json")):
        try:
            rows.append(json.load(open(f, encoding="utf-8")))
        except Exception:  # noqa: BLE001
            pass
    # Same soundness rule as everywhere else: a GO must prove an intact
    # council. Mixing in rows whose health is unknown would reintroduce exactly
    # the bias this project spent a day removing.
    return [r for r in rows if guard.default_terminal(r)]


def noisy_or(row: dict, drop: tuple[str, ...] = ()) -> float:
    p = 1.0
    for f in (row.get("findings") or []):
        if f.get("type") in drop:
            continue
        c = f.get("confidence")
        if isinstance(c, (int, float)):
            p *= (1.0 - float(c))
    return 1.0 - p


def score(rows: list[dict], tau: float, drop: tuple[str, ...]) -> dict:
    tp = fp = tn = fn = 0
    for r in rows:
        gt = r.get("ground_truth") == "vulnerable"
        pred = noisy_or(r, drop) >= tau
        if gt and pred:
            tp += 1
        elif gt and not pred:
            fn += 1
        elif not gt and pred:
            fp += 1
        else:
            tn += 1
    rec = 100 * tp / (tp + fn) if tp + fn else 0.0
    fpr = 100 * fp / (fp + tn) if fp + tn else 0.0
    prec = 100 * tp / (tp + fp) if tp + fp else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn, "recall": rec,
            "fpr": fpr, "prec": prec, "f1": f1, "J": rec - fpr}


def mechanism(rows: list[dict]) -> dict:
    """Does business_logic still place ~half its findings on safe contracts?"""
    per = defaultdict(lambda: [0, 0])  # type -> [on_safe, on_vuln]
    for r in rows:
        safe = r.get("ground_truth") != "vulnerable"
        for f in (r.get("findings") or []):
            per[f.get("type")][0 if safe else 1] += 1
    out = {}
    for t, (s, v) in per.items():
        tot = s + v
        lo, hi = wilson(s, tot)
        out[t] = {"on_safe": s, "on_vuln": v, "fp_rate": 100 * s / tot if tot else 0.0,
                  "ci": (lo, hi)}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="*", default=None,
                    help="default: every seed with checkpoints; 0 is reported "
                         "separately as IN-SAMPLE and never pooled with the rest")
    a = ap.parse_args()

    seeds = a.seeds
    if seeds is None:
        seeds = sorted({int(os.path.basename(d)[4:])
                        for d in glob.glob(os.path.join(CKPT, "benchmark", "*", "seed*"))
                        if os.path.basename(d)[4:].isdigit()})
    data = {s: load(s) for s in seeds}
    data = {s: r for s, r in data.items() if r}
    if not data:
        print("no sound rows found for seeds", seeds)
        return 1

    print("=" * 88)
    print("OUT-OF-SAMPLE VALIDATION — excluding `business_logic` from aggregation")
    print("  seed 0 selected this hypothesis, so seed 0 is IN-SAMPLE and proves nothing.")
    print("=" * 88)

    print("\n### 1. MECHANISM — does business_logic still misfire on safe contracts?\n")
    print(f"  {'seed':<6}{'scope':<12}{'on safe':>9}{'on vuln':>9}{'FP rate':>10}   95% CI")
    for s, rows in data.items():
        m = mechanism(rows).get(DROP)
        scope = "IN-SAMPLE" if s == 0 else "held-out"
        if not m:
            print(f"  {s:<6}{scope:<12}{'—':>9}{'—':>9}{'no findings':>10}")
            continue
        print(f"  {s:<6}{scope:<12}{m['on_safe']:>9}{m['on_vuln']:>9}"
              f"{m['fp_rate']:>9.1f}%   [{m['ci'][0]:.1f}, {m['ci'][1]:.1f}]")

    print("\n### 2. EFFECT — shipped vs business_logic excluded, per seed\n")
    for s, rows in data.items():
        scope = "IN-SAMPLE (proves nothing)" if s == 0 else "HELD-OUT"
        print(f"  seed {s}  n={len(rows)}  [{scope}]")
        print(f"    {'config':<34}{'recall':>9}{'FPR':>9}{'prec':>8}{'F1':>8}{'J':>7}{'dJ':>7}")
        for tau in TAUS:
            base = score(rows, tau, ())
            dropped = score(rows, tau, (DROP,))
            print(f"    {'shipped  tau=' + str(tau):<34}{base['recall']:>8.1f}%"
                  f"{base['fpr']:>8.1f}%{base['prec']:>7.1f}%{base['f1'] / 100:>8.3f}{base['J']:>7.1f}")
            print(f"    {'drop ' + DROP + '  tau=' + str(tau):<34}{dropped['recall']:>8.1f}%"
                  f"{dropped['fpr']:>8.1f}%{dropped['prec']:>7.1f}%{dropped['f1'] / 100:>8.3f}"
                  f"{dropped['J']:>7.1f}{dropped['J'] - base['J']:>+7.1f}")
        print()

    print("### 3. VERDICT\n")
    held = [s for s in data if s != 0]
    if not held:
        print("  NO HELD-OUT SEEDS YET. Nothing is validated; C3 stays a HYPOTHESIS.")
        return 0

    # A VERDICT FUNCTION MUST CHECK THAT IT HAS ENOUGH DATA TO HAVE A VERDICT.
    # The first version of this script printed "REFUTED -- the seed-0 gain was
    # fitted noise" off 23 rows containing 4 business_logic findings, while
    # seed 1 was still running. That is the defect this whole project is about,
    # committed by the script written to guard against it: a conclusion that
    # does not check its own premise. Thresholds below are deliberately blunt;
    # the point is that a partial run reports INSUFFICIENT, never a finding.
    MIN_ROWS = 200           # per held-out seed, sound rows
    MIN_CLASS = 60           # per class, so neither rate rests on a handful
    MIN_MECH_FINDINGS = 30   # business_logic findings, for the FP-rate estimate
    ready, blocked = [], []
    for s in held:
        rows = data[s]
        nv = sum(1 for r in rows if r.get("ground_truth") == "vulnerable")
        ns = len(rows) - nv
        m = mechanism(rows).get(DROP) or {"on_safe": 0, "on_vuln": 0}
        nm = m["on_safe"] + m["on_vuln"]
        why = []
        if len(rows) < MIN_ROWS:
            why.append(f"{len(rows)} sound rows < {MIN_ROWS}")
        if min(nv, ns) < MIN_CLASS:
            why.append(f"smallest class {min(nv, ns)} < {MIN_CLASS}")
        if nm < MIN_MECH_FINDINGS:
            why.append(f"{nm} {DROP} findings < {MIN_MECH_FINDINGS}")
        (blocked if why else ready).append((s, why))

    for s, why in blocked:
        print(f"  seed {s}: INSUFFICIENT DATA — {'; '.join(why)}")
    if not ready:
        print()
        print("  NO VERDICT. Every held-out seed is still too small to distinguish a")
        print("  real effect from sampling noise, so nothing below is reported. C3")
        print("  stays a HYPOTHESIS. Re-run when the seeds finish.")
        return 0
    if blocked:
        print(f"\n  Verdict uses only the seeds with enough data: {[s for s, _ in ready]}")
        print()
    held = [s for s, _ in ready]
    deltas = {s: {t: score(data[s], t, (DROP,))["J"] - score(data[s], t, ())["J"]
                  for t in TAUS} for s in held}
    all_pos = all(d > 0 for s in held for d in deltas[s].values())
    all_neg = all(d < 0 for s in held for d in deltas[s].values())
    for s in held:
        print(f"  seed {s}: dJ " + ", ".join(f"tau={t} {deltas[s][t]:+.1f}" for t in TAUS))
    print()
    if all_pos:
        print("  CONFIRMED in direction on every held-out seed and τ. A smaller effect")
        print("  than seed 0 is expected -- seed 0 is an upper bound because the class")
        print("  was chosen there. C3 may be promoted to SOUND, reporting the")
        print("  HELD-OUT effect size, not seed 0's.")
    elif all_neg:
        print("  REFUTED. The sign flips out of sample: the seed-0 gain was fitted")
        print("  noise. Report C3 as refuted and keep the shipped configuration.")
    else:
        # Two DIFFERENT disagreements both land here, and saying "seeds disagree"
        # when the seeds agree and the thresholds do not is a wrong diagnosis
        # printed with the authority of a verdict. Name which one happened.
        per_seed_sign = {s: {d > 0 for d in deltas[s].values()} for s in held}
        split_within = [s for s in held if len(per_seed_sign[s]) > 1]
        seed_means = {s: sum(deltas[s].values()) / len(deltas[s]) for s in held}
        split_across = len({m > 0 for m in seed_means.values()}) > 1
        print("  INCONCLUSIVE. Do not promote C3.")
        if split_within:
            print(f"  The sign is THRESHOLD-DEPENDENT within seed(s) {split_within}: the")
            print("  exclusion helps at one tau and hurts at another, so there is no single")
            print("  'excluding business_logic is better'. The effect is inside noise.")
        if split_across:
            print("  The sign also differs BETWEEN held-out seeds, which is the stronger")
            print("  form of the same problem.")
        print("  Report the disagreement; it is itself a finding for this paper.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
