"""Per-class calibrated aggregation — replacing the council's OR-gate.

MOTIVATION (measured, see docs/DECISION_LOG.md Phase 6):
  1. The council verdicts NO-GO if ANY specialist yields a surviving finding —
     a logical OR over k detectors. Contract-level FP therefore grows with k:
     measured 50% -> 61% -> 71% -> 73% as the router selects 1..4 specialists.
  2. Specialists differ wildly in reliability but are weighted equally:
     business_logic 0/18 (precision 0.00), dos_gas 2/20 (0.10),
     reentrancy 2/4 (0.50). Two of eight produce 65% of false-positive findings.

METHOD:
    risk(contract) = 1 - PROD_i ( 1 - w_class(i) * conf_i )
    verdict        = NO-GO iff risk >= tau

  w_class is a per-class reliability weight (a noisy-OR leak parameter) and
  conf_i the finding's confidence. Setting every w = 1 and tau -> 0 recovers the
  current OR-gate exactly, so the existing behaviour is a special case and the
  comparison is apples-to-apples.

THE TWO THINGS THAT MAKE THIS HONEST:

  * TRAIN/TEST SPLIT. Weights and tau are fit ONLY on a dev split and reported
    ONLY on a disjoint test split. Fitting w_class on the full benchmark and
    then reporting improved precision on that same benchmark is fitting to the
    test set — the result would be meaningless and a reviewer would say so. We
    also print the (inflated) fit-on-everything number precisely so the gap
    between it and the honest number is visible.

  * LAPLACE SMOOTHING. w_c = (tp_c + a) / (tp_c + fp_c + 2a). A raw 0/18 gives
    weight exactly 0, which is an overconfident conclusion from 18 samples;
    smoothing sends it to ~0.05 — heavily down-weighted but able to recover if
    it earns it on more data.

Usage:
    python -m eval.weighted_aggregation --alpha 1.0 --dev-frac 0.5
"""
from __future__ import annotations

import argparse, glob, json, random
from collections import defaultdict

from eval.schema import REPO_ROOT

BENCH = REPO_ROOT / "backend" / "eval" / "checkpoints" / "benchmark" / "ollama_noarb" / "seed0"
RESULTS = REPO_ROOT / "backend" / "eval" / "results"


def _load() -> list[dict]:
    """Only schema>=2 rows carry per-finding detail; older rows recorded just a
    count and cannot support any aggregation experiment."""
    rows = []
    for f in glob.glob(str(BENCH / "*.json")):
        try:
            r = json.load(open(f))
        except Exception:
            continue
        if r.get("schema", 1) >= 2 and r.get("verdict") in ("GO", "NO-GO"):
            rows.append(r)
    return rows


def fit_weights(dev: list[dict], alpha: float) -> dict[str, float]:
    """Per-class reliability = smoothed precision of that class's findings,
    measured by whether the contract carrying them was actually vulnerable."""
    tp = defaultdict(int); fp = defaultdict(int)
    for r in dev:
        vulnerable = r.get("ground_truth") == "vulnerable"
        for f in r.get("findings", []):
            (tp if vulnerable else fp)[f.get("type")] += 1
    return {c: (tp[c] + alpha) / (tp[c] + fp[c] + 2 * alpha) for c in set(tp) | set(fp)}


def risk(row: dict, w: dict[str, float], default_w: float) -> float:
    """Noisy-OR over weighted per-finding confidences."""
    p = 1.0
    for f in row.get("findings", []):
        conf = f.get("confidence")
        conf = 1.0 if conf is None else max(0.0, min(1.0, float(conf)))
        p *= 1.0 - w.get(f.get("type"), default_w) * conf
    return 1.0 - p


def score(rows: list[dict], pred) -> dict:
    tp = fp = tn = fn = 0
    for r in rows:
        v = pred(r)
        if r.get("ground_truth") == "vulnerable":
            tp += v; fn += not v
        else:
            fp += v; tn += not v
    p = tp / (tp + fp) if tp + fp else 0.0
    rc = tp / (tp + fn) if tp + fn else 0.0
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn,
            "precision": round(p, 3), "recall": round(rc, 3),
            "f1": round(2 * p * rc / (p + rc), 3) if p + rc else 0.0,
            "fpr": round(fp / (fp + tn), 3) if fp + tn else 0.0}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--alpha", type=float, default=1.0, help="Laplace smoothing")
    ap.add_argument("--dev-frac", type=float, default=0.5)
    ap.add_argument("--split-seed", type=int, default=0)
    ap.add_argument("--n-splits", type=int, default=10,
                    help="repeat over N random dev/test splits and report mean+/-std")
    a = ap.parse_args()

    rows = _load()
    if len(rows) < 20:
        print(f"[agg] only {len(rows)} schema-2 rows — need the enriched run to "
              f"progress before weights mean anything. Re-run later.")
        return

    # Stratified dev/test split so both halves keep the safe:vulnerable balance.
    rng = random.Random(a.split_seed)
    dev, test = [], []
    for gt in ("vulnerable", "likely_safe"):
        grp = [r for r in rows if r.get("ground_truth") == gt]
        rng.shuffle(grp)
        k = int(len(grp) * a.dev_frac)
        dev += grp[:k]; test += grp[k:]

    w = fit_weights(dev, a.alpha)
    default_w = sum(w.values()) / len(w) if w else 0.5

    print(f"[agg] {len(rows)} scored rows -> dev {len(dev)} / test {len(test)}")
    print("\nfitted per-class reliability (dev only, Laplace a=%.1f):" % a.alpha)
    for c, v in sorted(w.items(), key=lambda x: -x[1]):
        print(f"   {str(c):<28} {v:.3f}")

    # Baseline: the CURRENT rule — NO-GO iff any finding at all.
    base = score(test, lambda r: len(r.get("findings", [])) > 0)

    # Sweep tau on DEV, then apply the winner once to TEST.
    taus = [i / 40 for i in range(41)]
    best_tau, best_dev_f1 = 0.0, -1.0
    for t in taus:
        m = score(dev, lambda r, t=t: risk(r, w, default_w) >= t)
        if m["f1"] > best_dev_f1:
            best_dev_f1, best_tau = m["f1"], t
    tuned = score(test, lambda r: risk(r, w, default_w) >= best_tau)

    # Deliberately-inflated reference: fit AND report on everything. Printed so
    # the gap against the honest number is visible rather than imagined.
    w_all = fit_weights(rows, a.alpha)
    dflt_all = sum(w_all.values()) / len(w_all) if w_all else 0.5
    cheat_tau, cheat_f1 = 0.0, -1.0
    for t in taus:
        m = score(rows, lambda r, t=t: risk(r, w_all, dflt_all) >= t)
        if m["f1"] > cheat_f1:
            cheat_f1, cheat_tau = m["f1"], t
    cheat = score(rows, lambda r: risk(r, w_all, dflt_all) >= cheat_tau)

    print(f"\n{'config':<34}{'prec':>7}{'recall':>8}{'F1':>7}{'FPR':>7}")
    print(f"{'OR-gate (current) [test]':<34}{base['precision']:>7.3f}{base['recall']:>8.3f}{base['f1']:>7.3f}{base['fpr']:>7.3f}")
    print(f"{'weighted noisy-OR [test]':<34}{tuned['precision']:>7.3f}{tuned['recall']:>8.3f}{tuned['f1']:>7.3f}{tuned['fpr']:>7.3f}   tau={best_tau:.3f} (fit on dev)")
    print(f"{'  (fit+report on ALL - inflated)':<34}{cheat['precision']:>7.3f}{cheat['recall']:>8.3f}{cheat['f1']:>7.3f}{cheat['fpr']:>7.3f}   <- NOT reportable")
    verdict = "IMPROVES" if tuned["f1"] > base["f1"] else "does NOT improve"
    print(f"\nHonest (held-out) F1: {base['f1']:.3f} -> {tuned['f1']:.3f}  [{verdict}]")

    # Repeat over N random splits. A single split is a coin flip — the earlier
    # version wrote whichever split was run last, which is not a result.
    import statistics
    runs = []
    for sp in range(a.n_splits):
        r2 = random.Random(sp)
        d2, t2 = [], []
        for gt in ("vulnerable", "likely_safe"):
            grp = [r for r in rows if r.get("ground_truth") == gt]
            r2.shuffle(grp)
            k = int(len(grp) * a.dev_frac)
            d2 += grp[:k]; t2 += grp[k:]
        w2 = fit_weights(d2, a.alpha)
        dw2 = sum(w2.values()) / len(w2) if w2 else 0.5
        bt, bf = 0.0, -1.0
        for t in taus:
            m = score(d2, lambda r, t=t, w2=w2, dw2=dw2: risk(r, w2, dw2) >= t)
            if m["f1"] > bf:
                bf, bt = m["f1"], t

        # CONTROL: threshold WITHOUT per-class weights (every weight = 1).
        # The weighted rule changes two things at once versus the OR-gate — it
        # adds per-class reliability AND a threshold. If a plain threshold on
        # unweighted confidences captures the same gain, the weighting
        # contributes nothing and the paper's claim collapses to "we tuned a
        # threshold". This is the first control a reviewer asks for, so it is
        # measured rather than assumed.
        flat = {c: 1.0 for c in w2}
        ft, ff = 0.0, -1.0
        for t in taus:
            m = score(d2, lambda r, t=t: risk(r, flat, 1.0) >= t)
            if m["f1"] > ff:
                ff, ft = m["f1"], t

        runs.append({"split": sp, "tau": bt, "tau_flat": ft,
                     "or_gate": score(t2, lambda r: len(r.get("findings", [])) > 0),
                     "weighted": score(t2, lambda r, w2=w2, dw2=dw2, bt=bt: risk(r, w2, dw2) >= bt),
                     "threshold_only": score(t2, lambda r, ft=ft: risk(r, flat, 1.0) >= ft)})

    agg = lambda which, k: (round(statistics.mean([r[which][k] for r in runs]), 3),
                            round(statistics.stdev([r[which][k] for r in runs]), 3) if len(runs) > 1 else 0.0)
    wins = sum(1 for r in runs if r["weighted"]["f1"] > r["or_gate"]["f1"])
    summary = {
        "n_splits": len(runs), "wins": wins,
        "or_gate": {k: agg("or_gate", k)[0] for k in ("precision", "recall", "f1", "fpr")},
        "or_gate_std": {k: agg("or_gate", k)[1] for k in ("precision", "recall", "f1", "fpr")},
        "weighted": {k: agg("weighted", k)[0] for k in ("precision", "recall", "f1", "fpr")},
        "weighted_std": {k: agg("weighted", k)[1] for k in ("precision", "recall", "f1", "fpr")},
        "median_tau": round(statistics.median([r["tau"] for r in runs]), 3),
        "threshold_only": {k: agg("threshold_only", k)[0] for k in ("precision", "recall", "f1", "fpr")},
        "threshold_only_std": {k: agg("threshold_only", k)[1] for k in ("precision", "recall", "f1", "fpr")},
        "weighting_beats_threshold_only": sum(
            1 for r in runs if r["weighted"]["f1"] > r["threshold_only"]["f1"]),
    }
    print(f"\n=== MEAN OVER {len(runs)} RANDOM DEV/TEST SPLITS ===")
    for nm, key in (("OR-gate (current)", "or_gate"),
                    ("threshold only (no weights)", "threshold_only"),
                    ("weighted noisy-OR", "weighted")):
        m, s = summary[key], summary[key + "_std"]
        print(f"{nm:<22}" + "  ".join(f"{k}={m[k]:.3f}±{s[k]:.3f}" for k in ("precision", "recall", "f1", "fpr")))
    print(f"weighted beats OR-gate: {wins}/{len(runs)} splits; median tau={summary['median_tau']}")
    print(f"weighting beats threshold-alone: {summary['weighting_beats_threshold_only']}/{len(runs)} "
          f"<- does the per-class weighting earn its place?")

    out = {"n_rows": len(rows), "n_dev": len(dev), "n_test": len(test),
           "alpha": a.alpha, "weights": w, "tau": best_tau,
           "or_gate_test": base, "weighted_test": tuned,
           "fit_on_all_inflated": cheat,
           "summary": summary, "runs": runs,
           "note": ("Weights and tau fit on dev ONLY, reported on a disjoint test split, "
                    "averaged over N random splits. The fit-on-all row is included solely to "
                    "show how much fitting to the evaluation set would have inflated it.")}
    RESULTS.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(RESULTS / "weighted_aggregation.json", "w"), indent=2)
    print(f"wrote {RESULTS / 'weighted_aggregation.json'}")


main()
