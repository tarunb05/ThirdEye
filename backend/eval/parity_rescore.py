"""Re-score the parity comparison under ONE verdict rule.

Why this exists: the laptop checkpoints store the verdict that was current when
they ran -- the OR-gate ("any confirmed finding blocks"). The shipped rule is
noisy-OR against RISK_TAU, and stats._shipped_rule already reports the benchmark
by REPLAYING checkpoints through the live rule rather than trusting the stored
field. The DGX run, being live, used the shipped rule.

Comparing stored-laptop against live-DGX therefore measures the RULE CHANGE, not
the hardware -- which is what a first pass here accidentally did. This replays
the laptop findings through the identical live functions, so the only thing left
varying between the two columns is the findings themselves: same prompts, same
models, same seed, different silicon and a different Ollama build.
"""
from __future__ import annotations
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.council import _contract_risk, RISK_TAU
from services.suppression import suppress
from services.llm import preanalyze_code
from eval.loaders import thirdeye_bench as tb
from eval.schema import REPO_ROOT

DGX = REPO_ROOT / "backend" / "eval" / "results" / "dgx_parity_3b.json"
LAP = REPO_ROOT / "backend" / "eval" / "checkpoints" / "benchmark" / "ollama_noarb" / "seed0"

paths = {}
for it in tb.load():
    paths[it.contract_id] = it.code_paths[0] if it.code_paths else None


def blocked_now(r) -> bool:
    """The shipped rule, imported not reimplemented."""
    p = paths.get(r["contract_id"])
    src = ""
    if p is not None:
        try:
            src = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            src = ""
    kept, _ = suppress(r.get("findings", []), src, preanalyze_code(src) if src else {})
    return _contract_risk(kept) >= RISK_TAU


d = json.load(open(DGX, encoding="utf-8"))
dgx = {r["contract_id"]: r for r in d["rows"]}
lap = {}
for f in LAP.glob("*.json"):
    x = json.load(open(f, encoding="utf-8"))
    if x["contract_id"] in dgx:
        lap[x["contract_id"]] = x

agree = flips = 0
rows_out = []
print(f"{'contract':<40} {'laptop':<8} {'dgx':<8} {'truth':<11}")
print("-" * 72)
for cid, r in sorted(dgx.items()):
    l = lap[cid]
    lv = "NO-GO" if blocked_now(l) else "GO"
    dv = r["verdict"]
    ok = lv == dv
    agree += ok
    flips += not ok
    truth = "vulnerable" if l.get("ground_truth") == "vulnerable" else "safe"
    rows_out.append({"contract_id": cid, "laptop_shipped_rule": lv, "dgx": dv,
                     "truth": truth, "agrees": ok,
                     "stored_or_gate_verdict": l.get("verdict"),
                     "laptop_confs": [v.get("confidence") for v in l.get("findings", [])],
                     "dgx_confs": [v.get("confidence") for v in r.get("findings", [])]})
    if not ok:
        print(f"{cid[:40]:<40} {lv:<8} {dv:<8} {truth:<11}  FLIP")
n = len(dgx)


def acc(key):
    ok = sum(1 for x in rows_out if (x[key] == "NO-GO") == (x["truth"] == "vulnerable"))
    return round(ok / len(rows_out), 3)


print("-" * 72)
print(f"agreement under the SHIPPED rule : {agree}/{n} = {agree/n:.3f}")
print(f"accuracy  laptop / dgx           : {acc('laptop_shipped_rule')} / {acc('dgx')}")
print(f"(for contrast, stored OR-gate verdicts agreed {sum(1 for x in rows_out if x['stored_or_gate_verdict']==x['dgx'])}/{n})")

json.dump({"rule": f"noisy-OR, RISK_TAU={RISK_TAU}", "n": n,
           "agreement": round(agree / n, 3),
           "accuracy_laptop": acc("laptop_shipped_rule"), "accuracy_dgx": acc("dgx"),
           "rows": rows_out},
          open(REPO_ROOT / "backend" / "eval" / "results" / "dgx_parity_rescored.json", "w"), indent=1)
