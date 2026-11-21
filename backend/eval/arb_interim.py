"""Interim read on the arbitration sweep: is the judge dropping noise or bugs?

The council verdict is NO-GO iff noisy-OR over CONFIRMED findings >= 0.925
(services/council.py:472/484). Arbitration drops findings judged not_a_bug, so
the post-arbitration verdict is the same rule recomputed over SURVIVORS. That
is the quantity the retracted claim was about.
"""
import json, glob

TAU = 0.925
rows = []
for f in sorted(glob.glob("eval/checkpoints/arb_sweep/*.json")):
    d = json.load(open(f))
    if d.get("error"):
        continue
    rows.append(d)


def noisy_or(confs):
    p = 1.0
    for c in confs:
        if isinstance(c, (int, float)):
            p *= (1.0 - float(c))
    return 1.0 - p


tp = fp = tn = fn = 0
tp2 = fp2 = tn2 = fn2 = 0
flips = []
nf_total = nf_kept = 0
unknown_ok = 0

for d in rows:
    gt = str(d.get("gt", "")).lower().startswith("vuln")
    fs = d.get("findings") or []
    nf_total += len(fs)
    # judge_ok False == the judge did not actually answer. Those findings must
    # NOT be counted as adjudicated; the whole point of the flag.
    kept = [f for f in fs if f.get("judge_ok") and f.get("upheld")]
    unk = [f for f in fs if not f.get("judge_ok")]
    unknown_ok += len(unk)
    nf_kept += len(kept)

    pre = (d.get("council_verdict") or "").upper() == "NO-GO"
    # post: survivors only. A finding whose judge failed is kept (fail-open is
    # correct behaviour for a security tool) but counted separately above.
    post_confs = [f.get("conf") for f in kept] + [f.get("conf") for f in unk]
    post = noisy_or(post_confs) >= TAU

    if gt and pre: tp += 1
    elif gt and not pre: fn += 1
    elif not gt and pre: fp += 1
    else: tn += 1
    if gt and post: tp2 += 1
    elif gt and not post: fn2 += 1
    elif not gt and post: fp2 += 1
    else: tn2 += 1
    if pre != post:
        flips.append((d.get("contract_id", "?")[:44], "vuln" if gt else "safe",
                      "NO-GO->GO" if pre else "GO->NO-GO"))


def rates(tp, fp, tn, fn):
    rec = tp / (tp + fn) if tp + fn else 0
    fpr = fp / (fp + tn) if fp + tn else 0
    pr = tp / (tp + fp) if tp + fp else 0
    return rec * 100, fpr * 100, pr * 100


print("contracts scored: %d   findings: %d total, %d survive arbitration (%.0f%% dropped)"
      % (len(rows), nf_total, nf_kept, 100 * (1 - nf_kept / nf_total) if nf_total else 0))
print("findings whose judge did NOT answer (judge_ok False): %d" % unknown_ok)
print()
print("%-22s %4s%4s%4s%4s  %7s %7s %7s" % ("", "tp", "fp", "tn", "fn", "recall", "FPR", "prec"))
r, f_, p = rates(tp, fp, tn, fn)
print("%-22s %4d%4d%4d%4d  %6.1f%% %6.1f%% %6.1f%%" % ("council (pre-arb)", tp, fp, tn, fn, r, f_, p))
r, f_, p = rates(tp2, fp2, tn2, fn2)
print("%-22s %4d%4d%4d%4d  %6.1f%% %6.1f%% %6.1f%%" % ("post-arbitration", tp2, fp2, tn2, fn2, r, f_, p))
print()
print("verdict flips: %d" % len(flips))
for cid, g, how in flips:
    print("  %-46s gt=%-5s %s" % (cid, g, how))
print()
print("INTERIM ONLY — n=%d contracts. Not a result." % len(rows))
