"""
Full-pipeline benchmark over the ThirdEye scored dataset (smartcontract-datasets/).

Runs the REAL redesigned pipeline (services.pipeline.run_thirdeye:
static router -> council -> per-finding gate -> arbitration -> GO/NO-GO/INCONCLUSIVE)
across the 2,250 scored contracts, and scores each of the SIX trust sub-benchmarks
SEPARATELY so quality is pinpointable per tier, not averaged into one blurry number:

  SAFE tiers (a "safe" contract SHOULD verdict GO — false positive if NO-GO):
    01_safe / audited_library          — OpenZeppelin/Solady (283)
    01_safe / audit_reviewed_clean     — audit-reviewed, no bug reported (625)
    01_safe / realworld_no_bug_reported— real deployed, clean (217)
  VULN tiers (a "vulnerable" contract SHOULD verdict NO-GO — miss if GO):
    02_vuln_labelled / curated         — SmartBugs-style curated (224)
    02_vuln_labelled / injected        — synthetically injected bug (343)
    02_vuln_labelled / audit_report    — real audit-report findings (558)

Prediction mapping (the honest one):
  final_verdict NO-GO       -> predicted "vulnerable"
  final_verdict GO          -> predicted "likely_safe"
  final_verdict INCONCLUSIVE-> NOT scored as either. Counted separately. A broken
                               scan is an abstention, not a wrong answer — folding
                               it into TP/FP would flatter or punish the tool for
                               the wrong reason.

API-CALL ACCOUNTING: council._query is the one choke point for every LLM call
(specialists + red-team + judge). We snapshot the counter before/after each
contract, so the report gives calls-per-contract min/median/max/avg — the number
you size a per-user rate limit against.

Checkpointed per contract (eval/checkpoints/benchmark/<backend>/<seed>/<id>.json)
so a long run resumes exactly where it stopped. Idempotent: re-running skips
done contracts and only fills gaps.

Usage:
    python -m eval.run_benchmark --backend ollama --limit-per-tier 0   # 0 = all
    python -m eval.run_benchmark --backend ollama --limit-per-tier 40  # fast sample
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import statistics
import time
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from eval.loaders import thirdeye_bench
from eval.schema import REPO_ROOT

CKPT = REPO_ROOT / "backend" / "eval" / "checkpoints" / "benchmark"
RESULTS = REPO_ROOT / "backend" / "eval" / "results"

# The six sub-benchmarks, in report order, with the expected verdict for each.
TIERS = [
    ("01_safe", "audited_library", "safe"),
    ("01_safe", "audit_reviewed_clean", "safe"),
    ("01_safe", "realworld_no_bug_reported", "safe"),
    ("02_vuln_labelled", "curated", "vulnerable"),
    ("02_vuln_labelled", "injected", "vulnerable"),
    ("02_vuln_labelled", "audit_report", "vulnerable"),
]

TIER_LABEL = {
    "audited_library": "Audited libraries (OZ/Solady)",
    "audit_reviewed_clean": "Audit-reviewed, clean",
    "realworld_no_bug_reported": "Real-world, no bug reported",
    "curated": "Curated vulnerable (SmartBugs-style)",
    "injected": "Injected vulnerability",
    "audit_report": "Real audit-report findings",
}


def _ckpt_path(backend: str, seed: int, cid: str) -> Path:
    safe = cid.replace("/", "_").replace(":", "_")
    return CKPT / backend / f"seed{seed}" / f"{safe}.json"


def _verdict_to_pred(verdict: str) -> str | None:
    """NO-GO -> vulnerable, GO -> likely_safe, INCONCLUSIVE -> None (abstain)."""
    v = (verdict or "").upper()
    if v == "NO-GO":
        return "vulnerable"
    if v == "GO":
        return "likely_safe"
    return None  # INCONCLUSIVE / unknown


async def _backend_healthy(backend: str) -> tuple[bool, str]:
    """Pre-flight: confirm the backend can actually GENERATE, not just answer a
    ping. The full run's vuln tiers were once silently invalidated by an Ollama
    that was up (HTTP 200) but returning empty bodies under load — every scan
    defaulted to GO. A real generation probe catches that."""
    from services.council import _query
    try:
        out = await _query("ollama" if backend == "ollama" else "cerebras",
                           "qwen2.5-coder:7b" if backend == "ollama" else os.getenv("CEREBRAS_MODEL", "gpt-oss-120b"),
                           # A local cold model load measured 90-230s on a 4GB
                           # GPU, so a 60s probe timeout fails a HEALTHY backend
                           # and aborts the run before it starts.
                           "Reply with exactly: OK",
                           timeout=int(os.getenv("LLM_TIMEOUT", "300")) if backend == "ollama" else 60)
        if out and "OK" in out and "[" not in out[:6]:
            return True, out.strip()[:40]
        return False, f"probe returned {out[:80]!r}"
    except Exception as e:
        return False, str(e)[:120]


# How many consecutive contracts may come back INCONCLUSIVE before we assume
# the backend has died mid-run and abort (so we stop writing garbage rather
# than plough through 1,000 bad GO/INCONCLUSIVE checkpoints).
_MAX_CONSECUTIVE_INCONCLUSIVE = 15


async def _run_one(item, backend: str, seed: int, use_arbitration: bool = True) -> dict:
    """Run the full pipeline on one contract, capturing verdict, per-contract
    API-call count, latency, and finding count. Never raises — a crash is
    recorded as an errored abstention."""
    from services.pipeline import run_thirdeye
    from services import council

    code = item.read_code()
    before = council.get_api_call_count()["total"]
    t0 = time.time()
    err = None
    try:
        # Local tier: dynamic off (no Foundry in a batch), retrieval off (not
        # wired into prompts yet — would just burn calls), arbitration on
        # (it's the precision gate the whole redesign turns on).
        result = await run_thirdeye(
            code, backend=backend, seed=seed,
            use_static_router=True, use_retrieval=False,
            use_arbitration=use_arbitration, use_dynamic=False,
        )
        verdict = result.get("final_verdict", "INCONCLUSIVE")
        n_findings = len(result.get("vulnerabilities") or [])
        routing = result.get("routing") or {}
        roles = routing.get("roles") or []
        arb = result.get("arbitration_summary") or {}
        reason = result.get("verdict_reason") or ""
        n_errored = (result.get("stats") or {}).get("specialists_errored", 0)
        # Per-finding detail. Without this a checkpoint records only
        # n_findings, so ANY question about aggregation ("what if we weighted
        # classes by reliability?", "what threshold?") needs a full re-run at
        # ~200s/contract. Storing class+confidence once makes every future
        # aggregation experiment pure offline arithmetic over cached data —
        # which is the only kind of iteration that fits a quota-bound budget.
        findings = [
            {"type": v.get("type"), "severity": v.get("severity"),
             "confidence": v.get("confidence"), "source": v.get("source"),
             "model": v.get("model")}
            for v in (result.get("vulnerabilities") or [])
        ]
    except Exception as e:  # noqa: BLE001 — a batch must not die on one contract
        verdict, n_findings, roles, arb = "INCONCLUSIVE", 0, [], {}
        reason, n_errored, findings = "", 0, []
        err = str(e)[:300]
    dt = round(time.time() - t0, 1)
    calls = council.get_api_call_count()["total"] - before

    return {
        "contract_id": item.contract_id,
        "ground_truth": item.ground_truth_label,   # "vulnerable" | "likely_safe"
        "verdict": verdict,
        "predicted": _verdict_to_pred(verdict),
        "n_findings": n_findings,
        "n_specialists_run": len(roles),
        "roles": roles,
        "arbitration": {"reviewed": arb.get("reviewed", 0), "upheld": arb.get("upheld", 0), "dropped": arb.get("dropped", 0)},
        "api_calls": calls,
        "latency_s": dt,
        "error": err,
        # Kept so an INCONCLUSIVE is diagnosable after the fact (provider
        # rate-limit vs. genuinely broken contract) without a re-run.
        "verdict_reason": reason,
        "specialists_errored": n_errored,
        "findings": findings,
        "schema": 2,
    }


def _score_tier(rows: list[dict], expected: str) -> dict:
    """Confusion + P/R/F1 for one tier. positive class = "vulnerable".
    INCONCLUSIVE rows are abstentions: excluded from P/R/F1, reported alongside."""
    tp = fp = tn = fn = inconclusive = errored = 0
    for r in rows:
        if r.get("error"):
            errored += 1
        pred = r["predicted"]
        if pred is None:
            inconclusive += 1
            continue
        actual_pos = r["ground_truth"] == "vulnerable"
        pred_pos = pred == "vulnerable"
        if actual_pos and pred_pos:
            tp += 1
        elif actual_pos and not pred_pos:
            fn += 1
        elif not actual_pos and pred_pos:
            fp += 1
        else:
            tn += 1

    scored = tp + fp + tn + fn
    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    f1 = (2 * precision * recall / (precision + recall)
          if precision and recall else (0.0 if scored else None))
    accuracy = (tp + tn) / scored if scored else None

    # For an all-safe tier the interesting number is specificity / FP-rate:
    # how often the tool correctly says GO on a clean contract.
    correct_go_rate = tn / (tn + fp) if (tn + fp) else None       # = specificity
    # For an all-vuln tier: detection rate = recall (catches the bug -> NO-GO).

    return {
        "n": len(rows), "scored": scored, "inconclusive": inconclusive, "errored": errored,
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "precision": precision, "recall": recall, "f1": f1, "accuracy": accuracy,
        "correct_go_rate_on_safe": correct_go_rate if expected == "safe" else None,
        "detection_rate_on_vuln": recall if expected == "vulnerable" else None,
    }


def _api_stats(all_rows: list[dict]) -> dict:
    calls = [r["api_calls"] for r in all_rows if r["api_calls"] is not None]
    lat = [r["latency_s"] for r in all_rows if r.get("latency_s") is not None]
    if not calls:
        return {"available": False}
    calls_sorted = sorted(calls)
    return {
        "available": True,
        "contracts": len(calls),
        "total_api_calls": sum(calls),
        "calls_per_contract": {
            "min": min(calls), "max": max(calls),
            "mean": round(statistics.mean(calls), 2),
            "median": statistics.median(calls),
            "p95": calls_sorted[min(len(calls_sorted) - 1, int(0.95 * len(calls_sorted)))],
        },
        "latency_s_per_contract": {
            "min": min(lat), "max": max(lat),
            "mean": round(statistics.mean(lat), 1),
            "median": statistics.median(lat),
        } if lat else None,
        "rate_limit_note": (
            "A single scan makes up to this many LLM calls. Size a per-user "
            "limit as (acceptable concurrent scans) x (p95 calls/contract). "
            "e.g. p95={} calls/scan -> allowing 2 scans/user/min ~= {} calls/user/min."
        ).format(
            calls_sorted[min(len(calls_sorted) - 1, int(0.95 * len(calls_sorted)))],
            2 * calls_sorted[min(len(calls_sorted) - 1, int(0.95 * len(calls_sorted)))],
        ),
    }


async def run(backend: str, seed: int, limit_per_tier: int, concurrency: int, sample_seed: int = 0, use_arbitration: bool = True, max_minutes: int = 0, retry_quarantined: bool = False) -> dict:
    from services import council

    # ── Pre-flight: the backend must be able to GENERATE, or every scan
    # silently defaults to GO. Abort loudly rather than write garbage. ──
    ok, detail = await _backend_healthy(backend)
    if not ok:
        raise SystemExit(f"[benchmark] ABORT — backend '{backend}' failed generation probe: {detail}. "
                         f"Start/repair it and re-run (checkpoints resume).")
    print(f"[benchmark] backend health OK — probe returned {detail!r}")

    # Council-only results must never share a checkpoint namespace with
    # arbitrated ones — they are different systems and mixing them into one
    # table would silently blend two ablation rows.
    ckpt_tag = backend if use_arbitration else f"{backend}_noarb"

    # Gather items per tier (limit applied per tier for a balanced fast mode).
    tier_items: dict[tuple, list] = {}
    for bucket, tier, expected in TIERS:
        items = thirdeye_bench.load(buckets={bucket}, tier=tier)
        items = [it for it in items if it.code_paths and it.code_paths[0].exists()]
        # ALWAYS shuffle, even when taking every contract. limit_per_tier=0
        # used to skip this, which left items in filename order; a run stopped
        # early (time budget, crash, Ctrl-C) then covered an alphabetical prefix
        # that clusters by source project, and no CI computed from it is valid.
        # Shuffling unconditionally makes ANY prefix of the run a valid sample.
        rng = random.Random(f"{sample_seed}:{bucket}:{tier}")
        items = list(items)
        rng.shuffle(items)
        if limit_per_tier > 0:
            # Stratified RANDOM sample, not the first N. Filename order clusters
            # by source project (all the OZ-upgradeable files land together), so
            # a first-N slice is systematically non-representative and no CI
            # computed from it is valid.
            #
            # NESTED by construction: shuffle once under the seed, then take a
            # prefix. So N=10 is a strict subset of N=25 is a strict subset of
            # N=50. That makes "run a small N now, extend it overnight" free —
            # every checkpoint the small run produced is reused by the larger
            # one. (rng.sample(items, k) does NOT have this property: different
            # k draws a different set, so extending would discard the earlier
            # work and silently change which contracts the table covers.)
            items = items[:limit_per_tier]
        tier_items[(bucket, tier, expected)] = items

    total = sum(len(v) for v in tier_items.values())
    print(f"[benchmark] backend={backend} seed={seed}  {total} contracts across {len(TIERS)} tiers")
    for (b, t, e), items in tier_items.items():
        print(f"    {t:<28} {len(items):>4} contracts  (expected {e})")

    sem = asyncio.Semaphore(concurrency)
    done = 0
    lock = asyncio.Lock()
    consecutive_inconclusive = 0
    aborted = {"flag": False}
    # Wall-clock budget. A campus session is a hard time box; being killed
    # mid-run loses the report (though not the checkpoints). Past the budget we
    # stop STARTING work and let in-flight contracts finish, so the run always
    # exits through its own scoring path.
    _deadline = (time.time() + max_minutes * 60) if max_minutes else None
    budget_hit = {"flag": False}

    async def process(item, bucket, tier, expected) -> dict:
        nonlocal done, consecutive_inconclusive
        cp = _ckpt_path(ckpt_tag, seed, item.contract_id)
        if cp.exists():
            try:
                row = json.load(open(cp))
                async with lock:
                    done += 1
                return row
            except Exception:
                pass  # corrupt checkpoint -> re-run
        # A quarantined contract (GO with errored specialists, or INCONCLUSIVE)
        # sits in _transient with no terminal checkpoint, so an ordinary resume
        # retries it FIRST -- and the ones that fail tend to fail repeatedly for
        # the same reason (oversized input, a model that will not fit). Left
        # alone the run spends the night re-failing the same set and never
        # reaches fresh contracts. Skip them unless explicitly asked, so a resume
        # makes forward progress; retry_quarantined=True revisits them later.
        if not retry_quarantined and (cp.parent / "_transient" / cp.name).exists():
            return None
        if _deadline is not None and time.time() > _deadline and not cp.exists():
            if not budget_hit["flag"]:
                budget_hit["flag"] = True
                print(f"[benchmark] wall-clock budget of {max_minutes} min reached — "
                      f"letting in-flight contracts finish, then scoring what is done.")
            return None
        if aborted["flag"]:
            return {"contract_id": item.contract_id, "bucket": bucket, "tier": tier,
                    "expected": expected, "verdict": "SKIPPED", "predicted": None,
                    "api_calls": 0, "latency_s": 0, "n_findings": 0, "n_specialists_run": 0,
                    "roles": [], "arbitration": {}, "error": "skipped after backend-death circuit breaker"}
        async with sem:
            row = await _run_one(item, backend, seed, use_arbitration)
        # Circuit breaker: a long unbroken run of INCONCLUSIVE means the backend
        # died mid-run. Stop writing so we don't invalidate the rest.
        async with lock:
            if row["verdict"] == "INCONCLUSIVE":
                consecutive_inconclusive += 1
            else:
                consecutive_inconclusive = 0
            if consecutive_inconclusive >= _MAX_CONSECUTIVE_INCONCLUSIVE and not aborted["flag"]:
                aborted["flag"] = True
                print(f"\n[benchmark] CIRCUIT BREAKER — {consecutive_inconclusive} consecutive "
                      f"INCONCLUSIVE. Backend likely died. Halting new work; "
                      f"completed checkpoints are kept and will resume on re-run.\n")
        row["bucket"], row["tier"], row["expected"] = bucket, tier, expected
        # Only GO/NO-GO are terminal. An INCONCLUSIVE is almost always a
        # transient provider failure (429/timeout -> >50% specialists errored),
        # NOT a deterministic property of the contract — checkpointing it would
        # make the resume skip it forever and permanently bake a provider
        # outage into the benchmark's recall number. Park it in _transient/ for
        # diagnosis instead, so a re-run genuinely retries it.
        # A verdict only counts as terminal if the WHOLE council ran. Any
        # errored specialist can only fail to raise a flag, never raise a
        # false one, so a partial council biases exclusively toward GO —
        # measured at 32/198 rows, 100% of them GO. That is under the >50%
        # fail-closed bar, so it passes as a clean result while quietly
        # inflating safe-tier accuracy and deflating recall.
        # Terminal rule, matched to the ASYMMETRY of the failure mode. An
        # errored specialist can only fail to raise a flag, never invent one:
        #   NO-GO + errors -> still sound. The finding was raised by a
        #     specialist that DID run; the missing ones could only have added
        #     more findings, never removed this one.
        #   GO + errors    -> unsound. A specialist that never ran might have
        #     been the one to find something, so the clean bill of health is
        #     unearned. This is the exact direction that silently inflated
        #     safe-tier accuracy earlier (32/198 rows, 100% of them GO).
        # Requiring a fully intact council for BOTH discarded ~46% of completed
        # work for no bias reduction on the NO-GO side.
        _terminal = row["verdict"] == "NO-GO" or (
            row["verdict"] == "GO" and not row.get("specialists_errored"))
        if _terminal:
            cp.parent.mkdir(parents=True, exist_ok=True)
            json.dump(row, open(cp, "w"))
        else:
            tp = cp.parent / "_transient" / cp.name
            tp.parent.mkdir(parents=True, exist_ok=True)
            json.dump(row, open(tp, "w"))
        async with lock:
            done += 1
            n = done
        print(f"  [{n}/{total}] {tier:<24} {item.contract_id[:40]:<40} "
              f"gt={item.ground_truth_label:<11} -> {row['verdict']:<12} "
              f"calls={row['api_calls']} {row['latency_s']}s"
              + (f"  ERR:{row['error'][:60]}" if row.get('error') else ""))
        return row

    # One flat task list; the semaphore bounds real concurrency.
    #
    # INTERLEAVED round-robin across tiers, not tier-by-tier. gather() acquires
    # the semaphore in submission order, so a tier-major list means a run that
    # stops early (time budget, crash) completes the safe tiers and starves the
    # vulnerable ones — yielding an FPR with no recall to pair it with. Taking
    # one contract from each tier in turn keeps every tier growing together, so
    # a partial run is still a balanced, scorable benchmark.
    tasks = []
    _queues = [[(it, b, t, e) for it in items]
               for (b, t, e), items in tier_items.items()]
    for i in range(max((len(q) for q in _queues), default=0)):
        for q in _queues:
            if i < len(q):
                tasks.append(process(*q[i]))
    all_rows = await asyncio.gather(*tasks)
    # Contracts skipped by the wall-clock budget return None; they were never
    # started, so they are absent from the sample rather than an abstention.
    _skipped = sum(1 for r in all_rows if r is None)
    all_rows = [r for r in all_rows if r is not None]
    if _skipped:
        print(f"[benchmark] {_skipped} contracts not started (time budget); "
              f"scoring the {len(all_rows)} that ran. Re-run to resume — the "
              f"seeded order is stable, so this extends rather than reshuffles.")

    # ── Score each tier separately, then roll up safe / vuln / overall. ──
    per_tier = {}
    rows_by_tier: dict[str, list] = defaultdict(list)
    for r in all_rows:
        rows_by_tier[r["tier"]].append(r)

    for bucket, tier, expected in TIERS:
        per_tier[tier] = {
            "bucket": bucket, "label": TIER_LABEL[tier], "expected": expected,
            **_score_tier(rows_by_tier.get(tier, []), expected),
        }

    safe_rows = [r for r in all_rows if r["expected"] == "safe"]
    vuln_rows = [r for r in all_rows if r["expected"] == "vulnerable"]
    overall = _score_tier(all_rows, "mixed")
    safe_only = _score_tier(safe_rows, "safe")
    vuln_only = _score_tier(vuln_rows, "vulnerable")

    report = {
        "backend": backend, "seed": seed, "limit_per_tier": limit_per_tier,
        "arbitration": use_arbitration,
        "sample": "stratified random per tier" if limit_per_tier else "full",
        "sample_seed": sample_seed if limit_per_tier else None,
        "n_total": total,
        "overall": overall,
        "safe_aggregate": safe_only,
        "vuln_aggregate": vuln_only,
        "per_tier": per_tier,
        "api_accounting": _api_stats(all_rows),
        "verdict_note": "INCONCLUSIVE verdicts are abstentions, excluded from P/R/F1 and reported separately.",
    }
    return report


def _fmt(x, pct=False):
    if x is None:
        return "—"
    return f"{x*100:.1f}%" if pct else (f"{x:.3f}" if isinstance(x, float) else str(x))


def _write_reports(report: dict) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    tag = f"{report['backend']}{'' if report.get('arbitration', True) else '_noarb'}_seed{report['seed']}"
    json.dump(report, open(RESULTS / f"benchmark_by_tier_{tag}.json", "w"), indent=2)
    # Also a stable filename the snapshot builder can pick up.
    json.dump(report, open(RESULTS / "benchmark_by_tier.json", "w"), indent=2)

    lines = [
        f"# ThirdEye benchmark by tier — backend={report['backend']}, seed={report['seed']}",
        "",
        f"{report['n_total']} scored contracts. Prediction: NO-GO=vulnerable, GO=safe, "
        "INCONCLUSIVE=abstain (excluded from P/R/F1).",
        "",
        "## Per-tier",
        "",
        "| tier | expected | n | scored | inconcl. | TP | FP | TN | FN | precision | recall | F1 | accuracy |",
        "|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|",
    ]
    for _, tier, _e in TIERS:
        t = report["per_tier"][tier]
        lines.append(
            f"| {t['label']} | {t['expected']} | {t['n']} | {t['scored']} | {t['inconclusive']} | "
            f"{t['tp']} | {t['fp']} | {t['tn']} | {t['fn']} | {_fmt(t['precision'])} | "
            f"{_fmt(t['recall'])} | {_fmt(t['f1'])} | {_fmt(t['accuracy'])} |"
        )
    o, s, v = report["overall"], report["safe_aggregate"], report["vuln_aggregate"]
    lines += [
        "",
        "## Aggregates",
        "",
        "| slice | n | scored | inconcl. | TP | FP | TN | FN | precision | recall | F1 | accuracy |",
        "|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|",
        f"| SAFE (all safe tiers) | {s['n']} | {s['scored']} | {s['inconclusive']} | {s['tp']} | {s['fp']} | {s['tn']} | {s['fn']} | {_fmt(s['precision'])} | {_fmt(s['recall'])} | {_fmt(s['f1'])} | {_fmt(s['accuracy'])} |",
        f"| VULN (all vuln tiers) | {v['n']} | {v['scored']} | {v['inconclusive']} | {v['tp']} | {v['fp']} | {v['tn']} | {v['fn']} | {_fmt(v['precision'])} | {_fmt(v['recall'])} | {_fmt(v['f1'])} | {_fmt(v['accuracy'])} |",
        f"| OVERALL | {o['n']} | {o['scored']} | {o['inconclusive']} | {o['tp']} | {o['fp']} | {o['tn']} | {o['fn']} | {_fmt(o['precision'])} | {_fmt(o['recall'])} | {_fmt(o['f1'])} | {_fmt(o['accuracy'])} |",
    ]
    api = report["api_accounting"]
    if api.get("available"):
        c = api["calls_per_contract"]
        lines += [
            "",
            "## API-call accounting (per-user rate-limit sizing)",
            "",
            f"- Total LLM calls across the run: **{api['total_api_calls']}** over {api['contracts']} contracts.",
            f"- Calls per contract: min={c['min']}, median={c['median']}, mean={c['mean']}, p95={c['p95']}, max={c['max']}.",
            f"- {api['rate_limit_note']}",
        ]
    (RESULTS / f"benchmark_by_tier_{tag}.md").write_text("\n".join(lines) + "\n")
    print("\n" + "\n".join(lines))
    print(f"\n[benchmark] wrote results/benchmark_by_tier_{tag}.json + .md")


def report_from_checkpoints(backend: str, seed: int) -> dict:
    """Score whatever checkpoints exist WITHOUT running anything — used to
    refresh the (partial) report while the long batch is still in flight, and
    to regenerate reports after a completed run."""
    base = CKPT / backend / f"seed{seed}"
    rows = []
    for f in sorted(base.glob("*.json")):
        try:
            rows.append(json.load(open(f)))
        except Exception:
            pass
    per_tier, rows_by_tier = {}, defaultdict(list)
    for r in rows:
        if r.get("tier"):
            rows_by_tier[r["tier"]].append(r)
    for bucket, tier, expected in TIERS:
        per_tier[tier] = {"bucket": bucket, "label": TIER_LABEL[tier], "expected": expected,
                          **_score_tier(rows_by_tier.get(tier, []), expected)}
    safe_rows = [r for r in rows if r.get("expected") == "safe"]
    vuln_rows = [r for r in rows if r.get("expected") == "vulnerable"]
    return {
        "backend": backend, "seed": seed, "limit_per_tier": None,
        "n_total": len(rows),
        "partial": True,
        "overall": _score_tier(rows, "mixed"),
        "safe_aggregate": _score_tier(safe_rows, "safe"),
        "vuln_aggregate": _score_tier(vuln_rows, "vulnerable"),
        "per_tier": per_tier,
        "api_accounting": _api_stats(rows),
        "verdict_note": "INCONCLUSIVE verdicts are abstentions, excluded from P/R/F1 and reported separately.",
    }


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="ollama", help="ollama | hosted | hosted_fast")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--limit-per-tier", type=int, default=0, help="0 = all (full 2,250); N = stratified RANDOM sample of N per tier")
    ap.add_argument("--sample-seed", type=int, default=0, help="seed for the per-tier random sample (reproducibility)")
    ap.add_argument("--no-arbitration", action="store_true", help="council-only ablation row (skip the arbitration precision gate)")
    ap.add_argument("--concurrency", type=int, default=2, help="contracts in flight at once")
    ap.add_argument("--report-only", action="store_true", help="score existing checkpoints; run nothing")
    ap.add_argument("--retry-quarantined", action="store_true", help="revisit contracts previously quarantined to _transient; off by default so a resume makes forward progress")
    ap.add_argument("--max-minutes", type=int, default=0, help="wall-clock budget; 0 = unlimited. Past it, stop starting new contracts and score what finished.")
    args = ap.parse_args()
    if args.report_only:
        # Honour --no-arbitration here too. It used to be ignored, so
        # "--backend ollama --no-arbitration --report-only" silently scored the
        # ARBITRATED checkpoint tree and overwrote the arbitrated report -- two
        # different systems, one filename. The tag must be derived identically
        # in both branches.
        tag = args.backend if not args.no_arbitration else (
            args.backend if args.backend.endswith("_noarb") else f"{args.backend}_noarb")
        report = report_from_checkpoints(tag, args.seed)
    else:
        report = await run(args.backend, args.seed, args.limit_per_tier, args.concurrency, args.sample_seed, not args.no_arbitration, args.max_minutes, args.retry_quarantined)
    _write_reports(report)


if __name__ == "__main__":
    asyncio.run(main())
