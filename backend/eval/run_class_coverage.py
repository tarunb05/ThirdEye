#!/usr/bin/env python3
"""Per-DASP-10 detection rate, re-scored from existing checkpoints.

WHY. Durieux et al. (ICSE'20, arXiv:1910.10601) ran nine static analysers over
69 annotated contracts carrying 115 tagged vulnerabilities and found that three
DASP-10 categories were detected by *no tool at all*:

    denial of service · bad randomness · short addresses

All nine tools combined reached 48/115 (42%); the best single tool, Mythril,
reached 31/115 (27%); Slither 20/115 (17%).

This project has never reported per-class numbers — only per-provenance-tier —
so we could not say whether an LLM council detects what pattern-based tools
cannot. That is a cheap question to answer: the corpus already carries DASP-10
labels and every contract is checkpointed, so this is a RE-SCORE, not a re-run.
No inference is performed here.

THE RULE. Verdicts are recomputed with the live production functions
(`suppression.suppress` + `council._contract_risk` at `RISK_TAU`), exactly as
`services/stats.py::_shipped_rule` does. The rule is deliberately not
re-implemented: this project has already been burned once by a paper reporting
a threshold the product did not implement, and a third copy of the rule is a
third chance to drift.

WHAT THIS CAN AND CANNOT SAY. Our unit is a CONTRACT carrying a label, and a
detection is any-slice-positive — it does not prove the flag found *that* bug.
Durieux's unit is a tagged vulnerability matched by category. Ours is therefore
an UPPER bound against their lower bound, and the two are reported side by side
without being differenced. Categories with single-digit support are reported
with their intervals and explicitly called underpowered rather than dropped.

    python backend/eval/run_class_coverage.py
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from eval.loaders import thirdeye_bench as tb  # noqa: E402
from eval.schema import REPO_ROOT  # noqa: E402
from eval import taxonomy  # noqa: E402

OUT = REPO_ROOT / "backend" / "eval" / "results"

# Durieux et al. Table: detections of 115 tagged vulnerabilities.
# Quoted for context only — a different unit on a different corpus.
DURIEUX = {
    "reentrancy": "Slither 88% (7/8)",
    "arithmetic": "Mythril 68% (15/22)",
    "unchecked_low_level_calls": "Slither 33% (4/12)",
    "time_manipulation": "Slither 40% (2/5)",
    "front_running": "Mythril/Securify 29% (2/7)",
    "access_control": "best 21% (4/19)",
    "denial_of_service": "ZERO by any of 9 tools",
    "bad_randomness": "ZERO by any of 9 tools",
    "short_addresses": "ZERO by any of 9 tools",
}
ZERO_DETECTION = ("denial_of_service", "bad_randomness", "short_addresses")

# Specialist role -> DASP-10 category. Deliberately CONSERVATIVE: only roles
# with an unambiguous DASP slot are mapped. business_logic,
# oracle_price_manipulation and proxy_upgradeability have no clean DASP-10
# equivalent and are left unmapped rather than stretched into "other", because
# an over-generous map would manufacture type-matched hits.
#
# Note what is absent: the council has EIGHT roles and none of them is
# bad_randomness or short_addresses. Type-matched detection in those classes is
# therefore zero BY CONSTRUCTION, and any contract-level hit there is incidental
# — some other specialist flagged the contract for some other reason. That is a
# coverage gap in our design, not a detection result, and it is reported as one.
ROLE_TO_DASP = {
    "reentrancy": "reentrancy",
    "access_control": "access_control",
    "arithmetic": "arithmetic",
    "dos_gas": "denial_of_service",
    "flashloan_mev": "front_running",
}
NO_SPECIALIST = ("bad_randomness", "short_addresses")


def wilson(k, n, z=1.96):
    if n <= 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (100 * (c - m) / d, 100 * (c + m) / d)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="ollama_noarb")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--rule", choices=["shipped", "or_gate"], default="shipped")
    a = ap.parse_args()

    ckpt = REPO_ROOT / "backend" / "eval" / "checkpoints" / "benchmark" / a.backend / ("seed%d" % a.seed)
    if not ckpt.exists():
        raise SystemExit("no checkpoints at %s" % ckpt)

    rows = []
    for f in ckpt.glob("*.json"):
        try:
            r = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        if r.get("schema", 1) >= 2 and r.get("verdict") in ("GO", "NO-GO"):
            rows.append(r)
    print("checkpoints loaded: %d  (%s/seed%d)" % (len(rows), a.backend, a.seed))

    # corpus join: contract_id -> (categories, source path)
    cats, paths = {}, {}
    for it in tb.load():
        if it.ground_truth_label != "vulnerable":
            continue
        cs = set()
        for vc in (it.vuln_categories or []):
            cs.add(taxonomy.normalize(vc.taxonomy, vc.category))
        cats[it.contract_id] = cs
        paths[it.contract_id] = it.code_paths[0] if it.code_paths else None

    # ── the verdict rule, taken from the live production functions ──
    if a.rule == "shipped":
        from services.council import _contract_risk, RISK_TAU
        from services.suppression import suppress
        from services.llm import preanalyze_code

        def blocked(r):
            p = paths.get(r["contract_id"])
            src = ""
            if p is not None:
                try:
                    src = p.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    src = ""
            kept, _ = suppress(r.get("findings", []), src,
                               preanalyze_code(src) if src else {})
            return _contract_risk(kept) >= RISK_TAU
        print("rule: SHIPPED noisy-OR, tau=%.3f (replayed through live functions)" % RISK_TAU)
    else:
        def blocked(r):
            return len(r.get("findings", [])) > 0
        print("rule: historical OR-gate")

    per = defaultdict(lambda: {"n": 0, "hit": 0, "typed": 0})
    unlabelled = 0
    overall_n = overall_hit = 0
    for r in rows:
        cid = r["contract_id"]
        if cid not in cats:
            continue                      # safe contract, or not in the vuln set
        v = bool(blocked(r))
        overall_n += 1
        overall_hit += v
        cs = cats[cid] or set()
        cs = {c for c in cs if c != taxonomy.UNMAPPED}
        if not cs:
            unlabelled += 1
            continue
        # A contract may carry several categories; it counts toward each, so
        # the column sums exceed the contract count by construction.
        # Which DASP categories did the surviving findings actually name?
        named = set()
        if v:
            for f in (r.get("findings") or []):
                d = ROLE_TO_DASP.get(f.get("type"))
                if d:
                    named.add(d)
        for c in cs:
            per[c]["n"] += 1
            per[c]["hit"] += v
            per[c]["typed"] += (c in named)

    print()
    print("vulnerable contracts scored: %d   detected: %d (%.1f%%)"
          % (overall_n, overall_hit, 100 * overall_hit / max(1, overall_n)))
    print("of those, carrying no mapped DASP-10 label: %d" % unlabelled)
    print()

    hdr = "%-26s %4s  %-20s  %-20s  %s" % (
        "DASP-10 category", "n", "any-slice [95% CI]", "type-matched [95% CI]", "Durieux et al.")
    print(hdr)
    print("-" * len(hdr))
    out_rows = []
    for c in sorted(per, key=lambda k: -per[k]["n"]):
        d = per[c]
        lo, hi = wilson(d["hit"], d["n"])
        tlo, thi = wilson(d["typed"], d["n"])
        mark = " <<<" if c in ZERO_DETECTION else ""
        tcol = ("%5.1f%% [%4.1f, %5.1f]" % (100 * d["typed"] / d["n"], tlo, thi)
                if c in ROLE_TO_DASP.values() else "   no specialist    ")
        print("%-26s %4d  %5.1f%% [%4.1f, %5.1f]  %s  %s%s"
              % (c, d["n"], 100 * d["hit"] / d["n"], lo, hi, tcol,
                 DURIEUX.get(c, "-"), mark))
        out_rows.append({"category": c, "n": d["n"],
                         "detected_any_slice": d["hit"],
                         "rate_any_slice": round(d["hit"] / d["n"], 4),
                         "ci95_any_slice": [round(lo, 1), round(hi, 1)],
                         "detected_type_matched": d["typed"],
                         "rate_type_matched": round(d["typed"] / d["n"], 4),
                         "ci95_type_matched": [round(tlo, 1), round(thi, 1)],
                         "has_specialist": c in ROLE_TO_DASP.values(),
                         "durieux": DURIEUX.get(c),
                         "durieux_zero_detection": c in ZERO_DETECTION})

    print()
    print("<<< marks the three categories Durieux et al. found detected by NONE")
    print("    of nine static analysers.")
    print()
    for c in ZERO_DETECTION:
        d = per.get(c)
        if not d or d["n"] == 0:
            print("  %-20s no labelled contracts in our corpus — NOT REPORTABLE" % c)
            continue
        if c in NO_SPECIALIST:
            lo, hi = wilson(d["hit"], d["n"])
            print("  %-20s NO SPECIALIST EXISTS for this class. Contract-level "
                  "%d/%d is incidental," % (c, d["hit"], d["n"]))
            print("  %-20s not category detection — do NOT claim it." % "")
            continue
        lo, hi = wilson(d["typed"], d["n"])
        note = "  (UNDERPOWERED, n<15)" if d["n"] < 15 else ""
        print("  %-20s type-matched %d/%d = %.1f%% [%.1f, %.1f]%s"
              % (c, d["typed"], d["n"], 100 * d["typed"] / d["n"], lo, hi, note))
        if lo > 0:
            print("  %-20s interval EXCLUDES zero; nine static analysers "
                  "detected none." % "")

    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / ("class_coverage_%s.json" % a.rule)
    json.dump({
        "backend": a.backend, "seed": a.seed, "rule": a.rule,
        "n_vulnerable_scored": overall_n,
        "n_detected": overall_hit,
        "n_without_mapped_label": unlabelled,
        "unit": ("contract carrying the label, any-slice-positive — an UPPER "
                 "bound against Durieux's type-matched lower bound; the two are "
                 "not differenced"),
        "per_category": out_rows,
    }, open(dest, "w", encoding="utf-8"), indent=1)
    print()
    print("wrote %s" % dest)


if __name__ == "__main__":
    main()
