"""Score the shipped rule at current scale, with per-tier confidence intervals.

The per-tier false-alarm gradient is the paper's argument that residual FPs are
label noise rather than tool error. That argument is only as good as the width
of the intervals: at n~40/tier they overlapped almost completely and the claim
could not be made. This reports where it stands now.

Replays checkpoints through the LIVE rule (council._contract_risk + suppress),
exactly as services.stats._shipped_rule does, rather than re-deriving it.
"""
import glob, json, math, sys
sys.path.insert(0, '.')
from services.council import _contract_risk, RISK_TAU
from services.suppression import suppress
from services.llm import preanalyze_code
from eval.loaders import thirdeye_bench as tb

paths, tiers = {}, {}
for it in tb.load():
    paths[it.contract_id] = it.code_paths[0] if it.code_paths else None
    tiers[it.contract_id] = (it.meta or {}).get("tier")

def blocked(r):
    p = paths.get(r["contract_id"]); src = ""
    if p is not None:
        try: src = p.read_text(encoding="utf-8", errors="ignore")
        except Exception: src = ""
    kept, _ = suppress(r.get("findings", []), src, preanalyze_code(src) if src else {})
    return _contract_risk(kept) >= RISK_TAU

rows = []
for f in glob.glob("eval/checkpoints/benchmark/ollama_noarb/seed0/*.json"):
    try: d = json.load(open(f, encoding="utf-8"))
    except Exception: continue
    if d.get("verdict") in ("GO", "NO-GO") and d.get("tier"): rows.append(d)

def ci(k, n):
    """Wilson score interval — the same estimator as run_web3bugs, the context
    ablation, and the exhibit's stats.ts. This was Wald, which is fine at these
    n and p but disagrees at the boundaries, and a paper that quotes one interval
    while its own page draws another has the exact defect this project keeps
    documenting in other people's work."""
    if not n: return (None, None, None)
    z = 1.96
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = (z / d) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return p, max(0.0, c - h), min(1.0, c + h)

SAFE = ["audited_library", "audit_reviewed_clean", "realworld_no_bug_reported"]
print(f"SHIPPED RULE (noisy-OR, tau={RISK_TAU})   n={len(rows)}\n")
print(f"{'safe tier':<32}{'n':>5}{'FPR':>8}   95% CI")
out = {}
for t in SAFE:
    rs = [r for r in rows if tiers.get(r["contract_id"]) == t and r["ground_truth"] != "vulnerable"]
    fp = sum(1 for r in rs if blocked(r))
    p, lo, hi = ci(fp, len(rs))
    out[t] = (len(rs), p, lo, hi)
    print(f"{t:<32}{len(rs):>5}{p*100:>7.1f}%   [{lo*100:.1f}%, {hi*100:.1f}%]")

a = out["audited_library"]; c = out["realworld_no_bug_reported"]
sep = a[3] < c[2]
print(f"\nGRADIENT (audited libs vs real-world): "
      f"{'SEPARATED - claim holds' if sep else 'OVERLAPPING - not yet claimable'}")
print(f"  audited  [{a[2]*100:.1f}, {a[3]*100:.1f}]   real-world [{c[2]*100:.1f}, {c[3]*100:.1f}]")

safe = [r for r in rows if r["ground_truth"] != "vulnerable"]
vuln = [r for r in rows if r["ground_truth"] == "vulnerable"]
fp = sum(1 for r in safe if blocked(r)); tp = sum(1 for r in vuln if blocked(r))
p, lo, hi = ci(fp, len(safe)); rp, rlo, rhi = ci(tp, len(vuln))
prec = tp / (tp + fp) if tp + fp else 0
f1 = 2 * prec * rp / (prec + rp) if prec + rp else 0
print(f"\nOVERALL   FPR {p*100:.1f}% [{lo*100:.1f}, {hi*100:.1f}]  (n_safe={len(safe)})")
print(f"          recall {rp:.3f} [{rlo:.3f}, {rhi:.3f}]  (n_vuln={len(vuln)})")
print(f"          precision {prec:.3f}   F1 {f1:.3f}")
