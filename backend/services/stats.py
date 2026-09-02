"""
Benchmark / KPI data for the results dashboard — assembled from REAL on-disk
artifacts, never mocked:
  - eval/results/ablation_ac.json : per-stage ablation (single_llm -> council
    -> council+arbitration) with precision/recall/F1.
  - datasets/smartbugs-curated/vulnerabilities.json + datasets/web3bugs/results/
    bugs.csv : the vulnerability-class distributions ("most common vulns in the
    wild") across the labelled benchmarks.
  - PUBLISHED_BASELINES : the paper numbers we position against (GPTScan ICSE'24
    etc.) — clearly tagged as published, to be reproduced, not claimed as ours.

Every field degrades gracefully: a missing artifact yields an empty/!available
section with a note, so the endpoint never 500s on a fresh checkout.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

from eval.schema import REPO_ROOT, DATASETS_ROOT

RESULTS = REPO_ROOT / "backend" / "eval" / "results"
SMARTBUGS = DATASETS_ROOT / "smartbugs-curated" / "vulnerabilities.json"
WEB3BUGS_BUGS = DATASETS_ROOT / "web3bugs" / "results" / "bugs.csv"

# Published numbers we benchmark against (NOT our results — to be reproduced).
# Sources: GPTScan ICSE'24; ACToolBench ASE'25 (real-world access control).
PUBLISHED_BASELINES = [
    {"tool": "GPTScan (ICSE'24)", "dataset": "Web3Bugs", "recall": 0.833, "f1": 0.678, "cost": "paid GPT", "note": "primary target"},
    {"tool": "GPTScan (ICSE'24)", "dataset": "DefiHacks", "recall": 0.714, "f1": 0.80, "cost": "paid GPT", "note": "no public source — not reproduced"},
    {"tool": "Static tools (Slither/Mythril)", "dataset": "real-world access control", "recall": 0.05, "f1": None, "cost": "free", "note": "3-8% recall (ACToolBench)"},
    {"tool": "GPT-4o-mini", "dataset": "real-world access control", "recall": 0.90, "f1": None, "cost": "paid", "note": "high recall, ~951 false positives"},
]


def _ablation() -> dict:
    p = RESULTS / "ablation_ac.json"
    if not p.exists():
        return {"available": False, "note": "run eval/run_ablation.py"}
    data = json.load(open(p))
    rows = []
    for cfg, m in data.get("configs", {}).items():
        rows.append({"config": cfg, "precision": round(m["precision"], 3),
                     "recall": round(m["recall"], 3), "f1": round(m["f1"], 3),
                     "tp": m["tp"], "fp": m["fp"], "tn": m["tn"], "fn": m["fn"]})
    return {"available": True, "task": "access-control detection",
            "sample": {"n": data.get("sample_size"), "pos": data.get("n_pos"), "neg": data.get("n_neg"), "seed": data.get("seed")},
            "configs": rows}


def _smartbugs_distribution() -> list[dict]:
    if not SMARTBUGS.exists():
        return []
    c = Counter()
    for e in json.load(open(SMARTBUGS)):
        for v in e.get("vulnerabilities", []):
            c[v["category"]] += 1
    total = sum(c.values()) or 1
    return [{"category": k, "count": n, "pct": round(100 * n / total, 1)} for k, n in c.most_common()]


def _web3bugs_distribution() -> list[dict]:
    if not WEB3BUGS_BUGS.exists():
        return []
    c = Counter()
    with open(WEB3BUGS_BUGS, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            # strip keys (columns carry leading spaces, e.g. ' Bug Label'); some
            # short rows map extras to a None key with a list value — coerce.
            row = {}
            for k, v in r.items():
                if k is None:
                    continue
                row[k.strip()] = v.strip() if isinstance(v, str) else ""
            label = row.get("Bug Label", "")
            if label:
                c[label] += 1
    total = sum(c.values()) or 1
    return [{"category": k, "count": n, "pct": round(100 * n / total, 1)} for k, n in c.most_common(15)]


ARB_ABLATION = RESULTS / "arbitration_ablation.json"


def _arbitration_ablation() -> dict:
    """The arbitration precision-gate experiment (eval/arbitration_ablation.py).

    Re-adjudicates every contract the council verdicted NO-GO and reports how
    many flip to GO, split by ground truth. The claim under test: arbitration
    removes FALSE positives (safe contracts) without destroying TRUE ones.
    Reported as raw counts — the sample is small and a percentage alone would
    imply more precision than the n supports.
    """
    # Prefer the per-contract checkpoints: the summary JSON is only written when
    # the whole script finishes, and this run is quota-throttled across hours,
    # so reading checkpoints lets partial progress show up honestly.
    ckpt_dir = REPO_ROOT / "backend" / "eval" / "checkpoints" / "arb_ablation"
    rows: list[dict] = []
    if ckpt_dir.exists():
        for f in sorted(ckpt_dir.glob("*.json")):
            try:
                rows.append(json.load(open(f)))
            except Exception:
                continue
    if not rows:
        if not ARB_ABLATION.exists():
            return {"available": False, "note": "run eval/arbitration_ablation.py"}
        try:
            rows = json.load(open(ARB_ABLATION))
        except Exception:
            return {"available": False, "note": "arbitration_ablation.json unreadable"}
    ok = [r for r in rows if r.get("arbitrated")]
    safe = [r for r in ok if r.get("gt") == "likely_safe"]
    vuln = [r for r in ok if r.get("gt") == "vulnerable"]
    fixed = sum(1 for r in safe if r.get("flipped"))
    lost = sum(1 for r in vuln if r.get("flipped"))
    return {
        "available": bool(ok),
        "n_adjudicated": len(ok),
        "false_positives_seen": len(safe),
        "false_positives_corrected": fixed,
        "true_positives_seen": len(vuln),
        "true_positives_destroyed": lost,
        "judge": "cerebras gpt-oss-120b",
        "note": ("Council NO-GO verdicts re-adjudicated by an adversarial red-team/judge pair. "
                 "Small sample — counts, not rates, are the honest unit here."),
    }


SLITHER_BENCH = RESULTS / "slither_bench.json"
COUNCIL_CKPT = REPO_ROOT / "backend" / "eval" / "checkpoints" / "benchmark" / "ollama_noarb" / "seed0"
SLITHER_CKPT = REPO_ROOT / "backend" / "eval" / "checkpoints" / "slither_bench"


def _head_to_head() -> dict:
    """Council vs Slither on IDENTICAL contracts.

    The published-baseline numbers (GPTScan etc.) are from other papers on other
    datasets — context, not comparison. This is the only genuine head-to-head:
    same contracts, same ground truth, same sample.

    Two things are reported, and the second matters more than the first:
      1. metrics on the subset BOTH tools scored;
      2. COVERAGE — Slither abstains whenever a contract will not compile, and
         those abstentions are not random (modern OZ/Solady safe contracts fail
         far more often than old simple vulnerable ones). Scoring a static
         analyser only on what it compiled silently selects for easy code.
    """
    def _load(d):
        out = {}
        if d.exists():
            for f in sorted(d.glob("*.json")):
                try:
                    r = json.load(open(f)); out[r["contract_id"]] = r
                except Exception:
                    continue
        return out

    council, slither = _load(COUNCIL_CKPT), _load(SLITHER_CKPT)
    if not council or not slither:
        return {"available": False, "note": "run eval/run_slither_bench.py"}

    def score(rows: list[tuple]) -> dict:
        tp = fp = tn = fn = 0
        for gt, verdict in rows:
            v = verdict == "NO-GO"
            if gt == "vulnerable":
                tp += v; fn += not v
            else:
                fp += v; tn += not v
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / (tp + fn) if tp + fn else 0.0
        return {"tp": tp, "fp": fp, "tn": tn, "fn": fn,
                "precision": round(p, 3), "recall": round(r, 3),
                "f1": round(2 * p * r / (p + r), 3) if p + r else 0.0,
                "fpr": round(fp / (fp + tn), 3) if fp + tn else 0.0}

    common = sorted(set(council) & set(slither))
    n_sl_total = len(slither) + sum(1 for r in slither.values() if r.get("verdict") == "INCONCLUSIVE")
    sl_scored = sum(1 for r in slither.values() if r.get("verdict") in ("GO", "NO-GO"))
    return {
        "available": bool(common),
        "n_common": len(common),
        "council": score([(council[c]["ground_truth"], council[c]["verdict"]) for c in common]),
        "slither": score([(slither[c]["ground_truth"], slither[c]["verdict"]) for c in common]),
        "coverage": {"council_scored": len(council), "slither_scored": sl_scored},
        "note": ("Same contracts, same ground truth. Coverage is the bigger story: the council "
                 "scores every contract, while a static analyser abstains on anything that will "
                 "not compile — and those abstentions skew toward modern, complex code."),
    }


WEIGHTED_AGG = RESULTS / "weighted_aggregation.json"
ARB_SWEEP = RESULTS / "arbitration_sweep.json"


def _proposed_methods() -> dict:
    """The two fixes for the council's OR-gate, both validated held-out.

    Motivation (measured): a contract is NO-GO if ANY specialist yields a
    surviving finding — a logical OR over k detectors — so the false-positive
    rate grows with k (50% -> 61% -> 71% -> 73% for k=1..4). Two mechanisms
    were tested against that:

      1. weighted noisy-OR  — reweight the council's OWN findings by per-class
         reliability. Zero extra inference.
      2. calibrated arbitration — keep the adversarial judge but threshold its
         confidence instead of taking its binary verdict. 2 extra LLM calls
         per finding.

    Both report numbers with the threshold/weights fit on a dev split and
    scored on a disjoint test split, averaged over random splits. The
    in-sample optima are deliberately NOT surfaced here.
    """
    out: dict = {"available": False}

    if WEIGHTED_AGG.exists():
        try:
            w = json.load(open(WEIGHTED_AGG))
            # Read the multi-split SUMMARY, never the single-split fields: one
            # random dev/test partition is a coin flip, not a result.
            sm = w.get("summary") or {}
            if sm:
                # The RECOMMENDED rule is threshold-only. A control showed the
                # per-class weights do not earn their place: threshold-alone
                # scored F1 0.787 +/- 0.027 vs weighted 0.771 +/- 0.047, and
                # weighting won only 4/10 splits. Weights fitted from small
                # per-class counts added variance, not signal. Report the
                # simpler rule as the method and keep the weighted variant as
                # the ablation that justifies dropping it.
                out["weighted"] = {
                    "or_gate": sm.get("or_gate"), "or_gate_std": sm.get("or_gate_std"),
                    "tuned": sm.get("threshold_only"), "tuned_std": sm.get("threshold_only_std"),
                    "weighted_variant": sm.get("weighted"),
                    "weighting_wins": sm.get("weighting_beats_threshold_only"),
                    "wins": sm.get("wins"), "n_splits": sm.get("n_splits"),
                    "median_tau": sm.get("median_tau"),
                    "n_rows": w.get("n_rows"), "weights": w.get("weights"),
                    "extra_llm_calls": 0,
                }
                out["available"] = True
        except Exception:
            pass

    if ARB_SWEEP.exists():
        try:
            a = json.load(open(ARB_SWEEP))
            s = a.get("held_out_summary") or {}
            if s:
                out["calibrated_arbitration"] = {
                    "baseline_f1": s.get("baseline_f1"), "tuned_f1": s.get("tuned_f1"),
                    "tuned_f1_std": s.get("tuned_f1_std"),
                    "baseline_fpr": s.get("baseline_fpr"), "tuned_fpr": s.get("tuned_fpr"),
                    "wins": s.get("wins"), "n_splits": s.get("n_splits"),
                    "extra_llm_calls": "2 per finding",
                }
                out["available"] = True
        except Exception:
            pass

    out["note"] = ("Weights/thresholds fit on a dev split and scored on a disjoint test split, "
                   "averaged over random splits. In-sample optima are excluded — selecting a "
                   "threshold on the data you report it on inflates every number.")
    return out


def _story_data() -> dict:
    """Two derived series the narrative needs, computed from the checkpoints.

    1. compounding — false-alarm rate on SAFE contracts as a function of how many
       specialists the router selected. The council verdicts NO-GO if ANY
       specialist fires, so this is an OR over k detectors and the curve should
       rise with k. It is the visual proof of the structural defect.
    2. reliability — per-specialist precision (how often a class's findings sit
       on a genuinely vulnerable contract). Needs schema>=2 rows, which carry
       per-finding detail.
    """
    rows = []
    if COUNCIL_CKPT.exists():
        for f in COUNCIL_CKPT.glob("*.json"):
            try:
                rows.append(json.load(open(f)))
            except Exception:
                continue
    rows = [r for r in rows if r.get("verdict") in ("GO", "NO-GO")]
    if not rows:
        return {"available": False}

    by_k: dict[int, list[bool]] = {}
    for r in rows:
        if r.get("ground_truth") == "vulnerable":
            continue
        k = r.get("n_specialists_run") or 0
        by_k.setdefault(k, []).append(r.get("verdict") == "NO-GO")
    compounding = [
        {"specialists": k, "n": len(v), "fpr": round(sum(v) / len(v), 3)}
        for k, v in sorted(by_k.items()) if k > 0 and len(v) >= 5   # drop cells too small to read
    ]

    tp: dict[str, int] = {}
    fp: dict[str, int] = {}
    for r in rows:
        if r.get("schema", 1) < 2:
            continue
        vuln = r.get("ground_truth") == "vulnerable"
        for f in r.get("findings") or []:
            d = tp if vuln else fp
            d[f.get("type")] = d.get(f.get("type"), 0) + 1
    reliability = []
    for c in sorted(set(tp) | set(fp)):
        t, f_ = tp.get(c, 0), fp.get(c, 0)
        if t + f_ >= 3:
            reliability.append({"cls": c, "tp": t, "fp": f_,
                                "precision": round(t / (t + f_), 3)})
    reliability.sort(key=lambda x: -x["precision"])

    return {"available": bool(compounding or reliability),
            "compounding": compounding, "reliability": reliability,
            "n_rows": len(rows)}


def _headline_kpis(ablation: dict, tier: dict | None = None, arb: dict | None = None,
                   shipped: dict | None = None) -> list[dict]:
    """The KPI cards.

    Sourced from the REAL per-tier benchmark, not the old n=16 access-control
    ablation. The previous version advertised "precision 1.00 / 0 false
    positives" from that 16-contract slice while the actual measured
    false-positive rate on audited safe contracts was far higher — a flattering
    number with no support. Every card below states its own n.
    """
    kpis = [
        {"label": "Vulnerability classes", "value": "8", "sub": "OWASP/DASP specialists"},
        {"label": "Cost per contract", "value": "$0", "sub": "free local + free hosted tiers"},
    ]
    tier = tier or {}
    if tier.get("available"):
        va, sa = tier.get("vuln_aggregate") or {}, tier.get("safe_aggregate") or {}
        n_total = tier.get("n_total")
        kpis.append({"label": "Benchmark contracts", "value": str(n_total or "—"),
                     "sub": f"scored, {tier.get('backend','')} · balanced safe/vulnerable"})
        sh_r = (shipped or {}).get("after") if (shipped or {}).get("available") else None
        if sh_r:
            kpis.append({"label": "Recall (vulnerable)", "value": f"{sh_r['recall']:.2f}",
                         "sub": f"{sh_r['tp']}/{sh_r['tp']+sh_r['fn']} caught · GPTScan 0.83"})
        elif va.get("recall") is not None and va.get("scored"):
            kpis.append({"label": "Recall (vulnerable)", "value": f"{va['recall']:.2f}",
                         "sub": f"{va.get('tp',0)}/{va.get('scored',0)} caught · GPTScan 0.83"})
        # The honest headline: how often audited-safe code gets wrongly blocked.
        # Sourced from the SHIPPED rule when available — the tier aggregate is
        # historical (it was scored under the old OR-gate) and quoting it here
        # would advertise a false-alarm rate the tool no longer has.
        sh = (shipped or {}).get("after") if (shipped or {}).get("available") else None
        if sh:
            kpis.append({"label": "False-positive rate (safe)", "value": f"{sh['fpr']:.0%}",
                         "sub": f"{sh['fp']}/{sh['fp']+sh['tn']} audited-safe wrongly flagged · was "
                                f"{(shipped or {}).get('before',{}).get('fpr',0):.0%} before the fix"})
        elif sa.get("scored"):
            fp, n = sa.get("fp", 0), sa.get("scored", 0)
            kpis.append({"label": "False-positive rate (safe)", "value": f"{fp/n:.0%}" if n else "—",
                         "sub": f"{fp}/{n} audited-safe contracts wrongly flagged"})
    else:
        kpis.append({"label": "Benchmark contracts", "value": "2,250",
                     "sub": "1,125 safe · 1,125 vulnerable (run pending)"})
    arb = arb or {}
    if arb.get("available"):
        kpis.append({"label": "Arbitration: FPs corrected",
                     "value": f"{arb['false_positives_corrected']}/{arb['false_positives_seen']}",
                     "sub": f"true positives lost: {arb['true_positives_destroyed']}/{arb['true_positives_seen']}"})
    return kpis


BENCH_BY_TIER = RESULTS / "benchmark_by_tier.json"


def _tier_benchmark() -> dict:
    """Per-tier results from the full-pipeline benchmark (eval/run_benchmark.py).
    Six trust tiers scored separately so quality is pinpointable, plus the
    safe/vuln/overall roll-ups and the API-call accounting used to size the
    per-user rate limit. Absent until the benchmark has run."""
    if not BENCH_BY_TIER.exists():
        return {"available": False, "note": "run eval/run_benchmark.py"}
    try:
        data = json.load(open(BENCH_BY_TIER))
    except Exception:
        return {"available": False, "note": "benchmark_by_tier.json unreadable"}

    def slim(t: dict) -> dict:
        return {k: t.get(k) for k in (
            "label", "expected", "bucket", "n", "scored", "inconclusive", "errored",
            "tp", "fp", "tn", "fn", "precision", "recall", "f1", "accuracy",
            "correct_go_rate_on_safe", "detection_rate_on_vuln",
        )}

    per_tier = data.get("per_tier", {})
    return {
        "available": True,
        "backend": data.get("backend"),
        "n_total": data.get("n_total"),
        "tiers": [slim(dict(per_tier[k], tier=k)) for k in per_tier],
        "safe_aggregate": data.get("safe_aggregate"),
        "vuln_aggregate": data.get("vuln_aggregate"),
        "overall": data.get("overall"),
        "api_accounting": data.get("api_accounting"),
        "verdict_note": data.get("verdict_note"),
    }


SNAPSHOT = RESULTS / "benchmark_stats.json"


def build_benchmark_stats(use_snapshot: bool = True) -> dict:
    """Assemble the dashboard stats. In production the large datasets are not
    deployed (gitignored), so the vuln-distribution would be empty — we fall
    back to a committed snapshot (benchmark_stats.json) generated where the
    datasets DO exist. Call write_snapshot() after an eval to refresh it."""
    _tier, _arb, _h2h = _tier_benchmark(), _arbitration_ablation(), _head_to_head()
    _prop = _proposed_methods()
    _story = _story_data()
    _shipped = _shipped_rule()
    live = {
        "kpis": _headline_kpis(_ablation(), _tier, _arb, _shipped),
        "ablation": _ablation(),
        "tier_benchmark": _tier,
        "arbitration_ablation": _arb,
        "head_to_head": _h2h,
        "proposed_methods": _prop,
        "story": _story,
        "shipped_rule": _shipped,
        "vuln_distribution": {
            "smartbugs_curated": _smartbugs_distribution(),
            "web3bugs": _web3bugs_distribution(),
        },
        "published_baselines": PUBLISHED_BASELINES,
        "thesis": "Match/beat a paid-GPT ICSE'24 baseline on logic-vuln detection using only free models, "
                  "and add dynamic exploit-confirmation for precision.",
    }
    # Per-section fallback to the committed snapshot. This used to be gated on
    # the vuln_distribution being empty, which coupled two unrelated things: if
    # the datasets happened to be present, NO section could fall back — even the
    # eval sections, which depend on checkpoints rather than datasets and are
    # therefore unavailable in production regardless. That is what left the API
    # serving a 64% false-positive rate after the fix shipped.
    if use_snapshot and SNAPSHOT.exists():
        try:
            snap = json.load(open(SNAPSHOT))
            if not live["ablation"].get("available") and snap.get("ablation", {}).get("available"):
                live["ablation"] = snap["ablation"]
                live["kpis"] = snap.get("kpis", live["kpis"])
            # Fall back for EVERY eval-derived section, not just tier_benchmark.
            # These are computed from checkpoints, which are deliberately not
            # deployed (thousands of files), so in production they are always
            # unavailable and the API served stale KPIs while the committed
            # snapshot held the correct ones. The dashboard hid this because it
            # prefers the snapshot; anything calling the API directly did not.
            for _k in ("tier_benchmark", "shipped_rule", "story",
                       "head_to_head", "proposed_methods", "arbitration_ablation"):
                if not (live.get(_k) or {}).get("available") and (snap.get(_k) or {}).get("available"):
                    live[_k] = snap[_k]
            # KPIs are derived from those sections, so if any of them came from
            # the snapshot the KPIs must too, or the cards contradict the tables.
            if snap.get("kpis"):
                live["kpis"] = snap["kpis"]
            if not live["vuln_distribution"].get("smartbugs_curated"):
                live["vuln_distribution"] = snap.get("vuln_distribution", live["vuln_distribution"])
        except Exception:
            pass
    return live


# Where the frontend reads its baked-in copy from (so the Benchmarks page
# renders instantly on Vercel with no round-trip to the cold backend).
FRONTEND_STATIC = REPO_ROOT / "frontend" / "src" / "data" / "benchmark.ts"


def write_snapshot() -> str:
    """Persist the current live stats (computed where datasets exist) to BOTH:
      1. the committed backend snapshot (benchmark_stats.json) — production
         serves real numbers even though the raw datasets are gitignored;
      2. a frontend TS module (frontend/src/data/benchmark.ts) — the Benchmarks
         page imports this and renders INSTANTLY on Vercel, with zero fetch to
         the cold Render backend. This is the fix for the slow page load.
    """
    RESULTS.mkdir(parents=True, exist_ok=True)
    data = build_benchmark_stats(use_snapshot=False)
    # Merge in any snapshot-only tier data if this environment lacks the raw run
    # (so we never regress a good committed snapshot with an empty live one).
    if not data.get("tier_benchmark", {}).get("available") and SNAPSHOT.exists():
        try:
            prev = json.load(open(SNAPSHOT))
            if prev.get("tier_benchmark", {}).get("available"):
                data["tier_benchmark"] = prev["tier_benchmark"]
        except Exception:
            pass
    json.dump(data, open(SNAPSHOT, "w"), indent=2)

    # Emit the frontend static module.
    FRONTEND_STATIC.parent.mkdir(parents=True, exist_ok=True)
    ts = (
        "// AUTO-GENERATED by backend/services/stats.py write_snapshot().\n"
        "// Do not edit by hand. Regenerate: python -c \"from services.stats import write_snapshot; write_snapshot()\"\n"
        "// Baked into the bundle so the Benchmarks page renders instantly (no backend round-trip).\n"
        "import type { BenchmarkStats } from \"../lib/api\";\n\n"
        "export const BENCHMARK_SNAPSHOT: BenchmarkStats = "
        + json.dumps(data, indent=2)
        + " as BenchmarkStats;\n"
    )
    FRONTEND_STATIC.write_text(ts)
    return f"{SNAPSHOT} + {FRONTEND_STATIC}"


def _shipped_rule() -> dict:
    """What the PRODUCTION verdict rule scores on the benchmark, right now.

    Computed by replaying every scored checkpoint through the live functions
    (council._contract_risk + suppression.suppress) rather than re-deriving the
    rule here. That is deliberate: the whole reason this section exists is that
    the paper once reported a threshold rule the product did not implement, and
    a dashboard that re-implements the rule a third time could drift the same
    way. If the shipped rule changes, this number changes with it.

    No re-run is needed to keep this honest. The shipped change only alters how
    a verdict is computed FROM findings; the findings themselves (which
    specialists ran, what they quoted, their confidences) are unchanged, so
    replaying checkpoints is equivalent to re-running the benchmark.
    """
    try:
        from services.council import _contract_risk, RISK_TAU
        from services.suppression import suppress
        from services.llm import preanalyze_code
        from eval.loaders import thirdeye_bench as tb
    except Exception as e:
        return {"available": False, "note": f"live rule unavailable: {e}"}

    rows = []
    if COUNCIL_CKPT.exists():
        for f in COUNCIL_CKPT.glob("*.json"):
            try:
                r = json.load(open(f))
            except Exception:
                continue
            if r.get("schema", 1) >= 2 and r.get("verdict") in ("GO", "NO-GO"):
                rows.append(r)
    if not rows:
        return {"available": False, "note": "no schema-2 checkpoints"}

    paths, tiers = {}, {}
    try:
        for it in tb.load():
            paths[it.contract_id] = it.code_paths[0] if it.code_paths else None
            tiers[it.contract_id] = (it.meta or {}).get("tier")
    except Exception:
        pass

    def blocked_now(r) -> bool:
        p = paths.get(r["contract_id"])
        src = ""
        if p is not None:
            try:
                src = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                src = ""
        kept, _ = suppress(r.get("findings", []), src, preanalyze_code(src) if src else {})
        return _contract_risk(kept) >= RISK_TAU

    def score(pred) -> dict:
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

    before = score(lambda r: len(r.get("findings", [])) > 0)   # the OR-gate
    after = score(blocked_now)

    per_tier = {}
    for r in rows:
        if r.get("ground_truth") == "vulnerable":
            continue
        t = tiers.get(r["contract_id"]) or "unknown"
        d = per_tier.setdefault(t, {"n": 0, "before": 0, "after": 0})
        d["n"] += 1
        d["before"] += len(r.get("findings", [])) > 0
        d["after"] += blocked_now(r)
    for t, d in per_tier.items():
        d["fpr_before"] = round(d["before"] / d["n"], 3) if d["n"] else 0.0
        d["fpr_after"] = round(d["after"] / d["n"], 3) if d["n"] else 0.0

    return {
        "available": True, "n": len(rows), "tau": RISK_TAU,
        "before": before, "after": after, "per_tier": per_tier,
        "note": ("Replayed through the production verdict functions. The shipped rule pools "
                 "finding confidences as 1 - PROD(1 - conf) and blocks at tau; the previous rule "
                 "blocked on any surviving finding, which is the same rule at tau -> 0."),
    }
