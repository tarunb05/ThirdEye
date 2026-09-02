"""
Runs the real baselines (Slither, single-LLM, current-ThirdEye) against the
benchmark datasets, with per-item checkpointing so a Groq rate-limit (or any
other interruption) doesn't waste already-spent quota on restart.

Checkpointing: one JSON file per (baseline, dataset, contract_id) under
eval/checkpoints/. If the file exists, the item is skipped entirely (not
even re-checked against the network) — restart-safe by construction, not
by accident.

Retry: a contract's analysis is retried with exponential backoff if
run_full_analysis() reports llm_error_detected=True in its stats (added in
services/llm.py specifically for this — covers 429s, timeouts, and
connection errors, since they all produce the same downstream symptom: a
silently empty result that looks identical to "genuinely no vulnerabilities
found" unless you check for the error marker explicitly).

Usage:
    cd backend
    python -m eval.run_baselines --help
    python -m eval.run_baselines --baselines slither --datasets smartbugs_curated --limit 5
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()  # must run before importing eval.metrics -> services.llm reads LLM_BACKEND/GROQ_API_KEY at module-import time

from eval import metrics
from eval.loaders import etherscan50, smartbugs_curated, web3bugs, access_control_slice
from eval.schema import EvalItem, REPO_ROOT

CHECKPOINT_ROOT = REPO_ROOT / "backend" / "eval" / "checkpoints"

# Statuses worth checkpointing permanently — deterministic given the same
# input, so re-running tomorrow would just reproduce the same outcome.
# "rate_limited_exhausted" and "error" are deliberately excluded: Groq's
# free tier enforces a 100k-token/24h ROLLING window (confirmed via direct
# API test), not a fixed daily reset — an item that exhausts retries today
# because the window is full will very likely succeed tomorrow once it
# drains. Checkpointing those permanently would silently and invisibly
# block every future day's retry, exactly the kind of self-inflicted
# wound a multi-day checkpointed run can't afford.
TERMINAL_STATUSES = {"ok", "no_result", "too_large_for_backend"}

# The benchmark BACKBONE (the restructured set). Etherscan-50 is intentionally
# NOT here: its ground truth is heuristic/scraped ("vulnerabilities not checked
# yet"), it was a pre-existing convenience set, and it carries no research
# weight — it remains loadable for ad-hoc smoke tests via --datasets etherscan50
# but is never part of a default/headline run.
BACKBONE_DATASETS = ["smartbugs_curated", "web3bugs", "access_control_slice"]

LOADERS = {
    "smartbugs_curated": smartbugs_curated.load,
    "web3bugs": web3bugs.load,
    "access_control_slice": access_control_slice.load,
    "etherscan50": etherscan50.load,  # smoke-only, not a backbone benchmark
}

BASELINES = ["slither", "single_llm", "current_thirdeye", "council"]

# Multi-file projects (Web3Bugs) are analyzed slice-by-slice; cap the slices
# per project so one pathological mono-repo can't dominate a run. Truncation
# is logged, never silent (a silent cap reads as "fully analyzed" when it
# wasn't). Single-file datasets are unaffected (they always yield 1 slice).
MAX_SLICES_PER_ITEM = 40

MAX_RETRIES = 5
BASE_DELAY_SECONDS = 8


class DailyQuotaExhausted(Exception):
    """Groq's 100k-tokens/24h window is full. Every subsequent LLM call
    this run will fail identically until the window drains (confirmed via
    direct API test: a ~50min wait was quoted, far past anything our
    retry backoff covers) — so there's no point discovering that one
    item at a time. Raised to stop the whole run early and resume
    tomorrow via the normal checkpoint-skip mechanism."""


def _safe_id(contract_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", contract_id)


def _checkpoint_path(baseline: str, dataset: str, contract_id: str, seed: int | None = None) -> Path:
    # Seeded runs checkpoint into their own namespace so the >=3-seed protocol
    # (mean +/- std over seeds, per the eval plan) doesn't collide seed-0's
    # result with seed-1's. seed=None keeps the original flat layout for
    # deterministic baselines (slither) and single-seed runs.
    base = CHECKPOINT_ROOT / baseline / dataset
    if seed is not None:
        base = base / f"seed{seed}"
    return base / f"{_safe_id(contract_id)}.json"


def _load_checkpoint(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None  # corrupt checkpoint — treat as missing, will be re-run


def _save_checkpoint(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    tmp.replace(path)  # atomic-ish on the same filesystem — avoids half-written checkpoints


async def _run_slither_baseline(item: EvalItem) -> dict:
    from services.slither import run_slither
    from services.llm import _parse_slither

    code = item.read_code()
    slither_out = await asyncio.to_thread(run_slither, code)
    if slither_out.get("status") != "completed":
        return {"status": "no_result", "reason": slither_out.get("status"), "slither_message": slither_out.get("message")}

    slither_vulns = _parse_slither(slither_out)
    predicted_label = "vulnerable" if slither_vulns else "likely_safe"
    predicted_categories = [v.get("type", "") for v in slither_vulns]
    return {
        "status": "ok",
        "predicted_label": predicted_label,
        "predicted_categories": predicted_categories,
        "raw_finding_count": len(slither_vulns),
    }


async def _llm_one_slice(code: str, disable_slither: bool) -> dict:
    from services.llm import run_full_analysis

    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            result = await run_full_analysis(code, disable_slither=disable_slither)
        except Exception as e:
            last_error = f"exception: {e}"
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(BASE_DELAY_SECONDS * (2 ** attempt))
                continue
            return {"status": "error", "reason": last_error}

        if result.get("stats", {}).get("llm_error_detected"):
            last_error = result.get("summary", "")[:200]
            # A 413 ("Request too large") is deterministic given the same input
            # (prompt over the per-request budget), not transient like a 429 —
            # fail fast instead of burning 5 backoff rounds on a guaranteed
            # identical failure, and report it as a distinct coverage gap.
            if "LLM Error 413" in last_error or "too large" in last_error.lower():
                return {"status": "too_large_for_backend", "reason": last_error}
            if "tokens per day" in last_error.lower() or "(tpd)" in last_error.lower():
                raise DailyQuotaExhausted(last_error)
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(BASE_DELAY_SECONDS * (2 ** attempt))
                continue
            return {"status": "rate_limited_exhausted", "reason": last_error}

        return {
            "status": "ok",
            "predicted_label": "vulnerable" if result.get("final_verdict") == "NO-GO" else "likely_safe",
            "predicted_categories": [v.get("type", "") for v in result.get("vulnerabilities", [])],
            "raw_finding_count": len(result.get("vulnerabilities", [])),
            "final_verdict": result.get("final_verdict"),
        }
    return {"status": "error", "reason": last_error or "unknown"}


async def _run_llm_baseline(item: EvalItem, disable_slither: bool) -> dict:
    slices = _item_slices(item)
    slice_results = [await _llm_one_slice(s.code, disable_slither) for s in slices]
    return _aggregate_slice_predictions(slice_results)


def _item_slices(item: EvalItem) -> list:
    """Slices to analyze for an item, capped + logged. One slice for
    single-file items; many for multi-file Web3Bugs projects."""
    slices = item.read_slices()
    if len(slices) > MAX_SLICES_PER_ITEM:
        print(f"    [slice cap] {item.contract_id}: {len(slices)} slices -> analyzing first {MAX_SLICES_PER_ITEM} (rest skipped, logged)")
        slices = slices[:MAX_SLICES_PER_ITEM]
    return slices


def _aggregate_slice_predictions(slice_results: list[dict]) -> dict:
    """Project-level rollup of per-slice results (any-positive rule).

    A project is predicted vulnerable if ANY slice is — matching Web3Bugs's
    project-level ground truth (a contest is vulnerable if it has >=1 bug).
    Categories are the union across slices. If every slice errored, the whole
    item is an error (so coverage stays honest)."""
    ok = [r for r in slice_results if r.get("status") == "ok"]
    if not ok:
        # Surface the most informative non-ok status if nothing succeeded.
        for status in ("too_large_for_backend", "rate_limited_exhausted", "no_result", "error"):
            if any(r.get("status") == status for r in slice_results):
                bad = next(r for r in slice_results if r.get("status") == status)
                return {"status": status, "reason": bad.get("reason", "all slices failed")}
        return {"status": "error", "reason": "no slice results"}

    any_vuln = any(r["predicted_label"] == "vulnerable" for r in ok)
    cats: list[str] = []
    for r in ok:
        cats.extend(r.get("predicted_categories", []))
    models_used = ok[0].get("council_models_used", [])
    return {
        "status": "ok",
        "predicted_label": "vulnerable" if any_vuln else "likely_safe",
        "predicted_categories": sorted(set(c for c in cats if c)),
        "raw_finding_count": sum(r.get("raw_finding_count", 0) for r in ok),
        "final_verdict": "NO-GO" if any_vuln else "GO",
        "n_slices": len(slice_results),
        "n_slices_ok": len(ok),
        "n_slices_flagged": sum(1 for r in ok if r["predicted_label"] == "vulnerable"),
        "council_models_used": models_used,
    }


async def _council_one_slice(code: str, llm_backend: str, seed: int | None) -> dict:
    from services.council import run_council

    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            result = await run_council(code, backend=llm_backend, seed=seed)
        except Exception as e:
            last_error = f"exception: {e}"
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(BASE_DELAY_SECONDS * (2 ** attempt))
                continue
            return {"status": "error", "reason": last_error}

        if result.get("stats", {}).get("llm_error_detected"):
            last_error = result.get("summary", "")[:200]
            if "LLM Error 413" in last_error or "too large" in last_error.lower():
                return {"status": "too_large_for_backend", "reason": last_error}
            if "tokens per day" in last_error.lower() or "(tpd)" in last_error.lower():
                raise DailyQuotaExhausted(last_error)
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(BASE_DELAY_SECONDS * (2 ** attempt))
                continue
            return {"status": "rate_limited_exhausted", "reason": last_error}

        return {
            "status": "ok",
            "predicted_label": "vulnerable" if result.get("final_verdict") == "NO-GO" else "likely_safe",
            "predicted_categories": [v.get("type", "") for v in result.get("vulnerabilities", [])],
            "raw_finding_count": len(result.get("vulnerabilities", [])),
            "final_verdict": result.get("final_verdict"),
            "council_models_used": [
                {"role": r["role"], "provider": r["provider"], "model": r["model"], "found": r["found"]}
                for r in result.get("council_detail", [])
            ],
        }
    return {"status": "error", "reason": last_error or "unknown"}


async def _run_council_baseline(item: EvalItem, llm_backend: str, seed: int | None = None) -> dict:
    slices = _item_slices(item)
    slice_results = [await _council_one_slice(s.code, llm_backend, seed) for s in slices]
    return _aggregate_slice_predictions(slice_results)


async def run_one(baseline: str, item: EvalItem, llm_backend: str = "groq", seed: int | None = None) -> dict:
    if baseline == "slither":
        return await _run_slither_baseline(item)
    if baseline == "single_llm":
        return await _run_llm_baseline(item, disable_slither=True)
    if baseline == "current_thirdeye":
        return await _run_llm_baseline(item, disable_slither=False)
    if baseline == "council":
        return await _run_council_baseline(item, llm_backend, seed=seed)
    raise ValueError(f"unknown baseline: {baseline}")


async def run_dataset_baseline(baseline: str, dataset_name: str, items: list[EvalItem], llm_backend: str = "groq", seed: int | None = None) -> dict:
    """Returns {contract_id: Prediction} for items with a usable result —
    items that errored/rate-limited out are reported but excluded from
    predictions (left as "no prediction" for the metrics module to count
    honestly rather than guessed at). Per-item wall-clock latency is recorded
    into each fresh checkpoint (latency_s) for the cost/latency table."""
    preds: dict[str, metrics.Prediction] = {}
    counts = {"ok": 0, "skipped_checkpoint": 0, "no_result": 0, "error": 0, "rate_limited_exhausted": 0}

    for i, item in enumerate(items):
        ckpt_path = _checkpoint_path(baseline, dataset_name, item.contract_id, seed=seed)
        cached = _load_checkpoint(ckpt_path)
        if cached is not None:
            counts["skipped_checkpoint"] += 1
            result = cached
        else:
            if not item.code_paths or not all(p.exists() for p in item.code_paths):
                result = {"status": "no_result", "reason": "missing source file(s)"}
            else:
                t0 = time.time()
                result = await run_one(baseline, item, llm_backend, seed=seed)
                result["latency_s"] = round(time.time() - t0, 2)
            if result.get("status") in TERMINAL_STATUSES:
                result["_checkpointed_at"] = time.time()
                if seed is not None:
                    result["_seed"] = seed
                _save_checkpoint(ckpt_path, result)

        status = result.get("status", "error")
        counts[status] = counts.get(status, 0) + 1
        lat = f" {result.get('latency_s')}s" if result.get("latency_s") else ""
        print(f"  [{baseline}/{dataset_name}] {i + 1}/{len(items)} {item.contract_id}: {status}{lat}")

        if status == "ok":
            preds[item.contract_id] = metrics.Prediction(
                contract_id=item.contract_id,
                predicted_label=result["predicted_label"],
                predicted_categories=result["predicted_categories"],
                category_taxonomy="thirdeye",
            )

    print(f"  [{baseline}/{dataset_name}] done: {counts}")
    return {"predictions": preds, "counts": counts}


def _check_backend_config(baselines: list[str], llm_backend: str) -> None:
    """Fail loud and immediate, not 30 minutes of wasted retries in: confirm
    LLM_BACKEND is actually what we think it is before spending any quota."""
    llm_dependent = {"single_llm", "current_thirdeye", "council"}
    if not llm_dependent.intersection(baselines):
        return
    backend = os.getenv("LLM_BACKEND", "ollama")
    print(f"LLM_BACKEND={backend!r} (from environment, after load_dotenv())")
    if backend != llm_backend:
        raise SystemExit(
            f"LLM_BACKEND is {backend!r}, not {llm_backend!r} — --llm-backend {llm_backend} requires "
            f"the environment to actually match (cwd must be backend/ when running "
            f"python -m eval.run_baselines)."
        )
    if backend == "groq" and not os.getenv("GROQ_API_KEY"):
        raise SystemExit("LLM_BACKEND=groq but GROQ_API_KEY is empty — check backend/.env.")
    if "council" in baselines and backend == "groq" and not os.getenv("CEREBRAS_API_KEY"):
        raise SystemExit(
            "council baseline with --llm-backend groq needs CEREBRAS_API_KEY (one specialist "
            "runs on Cerebras for genuine provider diversity) — check backend/.env."
        )


async def main(baselines: list[str], dataset_names: list[str], limit: int | None, llm_backend: str, seed: int | None = None) -> None:
    # Must happen before services.llm is ever imported anywhere — it reads
    # LLM_BACKEND once at module-import time into a module-level constant,
    # not per-call. _run_llm_baseline()'s `from services.llm import ...` is
    # a lazy/local import, so as long as this runs first (it does — CLI
    # parsing always precedes the first baseline call), this is safe.
    os.environ["LLM_BACKEND"] = llm_backend
    _check_backend_config(baselines, llm_backend)
    datasets = {}
    for name in dataset_names:
        items = LOADERS[name]()
        if limit:
            items = items[:limit]
        datasets[name] = items
        print(f"Loaded {name}: {len(items)} item(s)")

    for baseline in baselines:
        for dataset_name, items in datasets.items():
            seed_note = f" seed={seed}" if seed is not None else ""
            print(f"\n=== Running {baseline} on {dataset_name} ({len(items)} items){seed_note} ===")
            try:
                await run_dataset_baseline(baseline, dataset_name, items, llm_backend, seed=seed)
            except DailyQuotaExhausted as e:
                # Groq-specific (a 100k-tokens/24h cap) — Ollama has no such
                # wall, and the string-matching that raises this exception
                # only ever fires on Groq's own error text, so this branch
                # is unreachable when llm_backend == "ollama" in practice.
                # Still handled explicitly for clarity rather than relying
                # on that being true forever.
                print(f"\n!!! Groq daily token quota exhausted: {e}")
                print("!!! Stopping this run early (not an error) — already-completed items are")
                print("!!! checkpointed, nothing was lost. Re-run this same command tomorrow (or")
                print("!!! once the 24h rolling window drains) to resume from where this stopped.")
                return


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run real baselines with checkpointing")
    parser.add_argument("--baselines", default=",".join(BASELINES), help="comma-separated subset of: " + ",".join(BASELINES))
    parser.add_argument("--datasets", default=",".join(BACKBONE_DATASETS), help="comma-separated subset of: " + ",".join(LOADERS.keys()) + " (default = backbone: " + ",".join(BACKBONE_DATASETS) + ")")
    parser.add_argument("--limit", type=int, default=None, help="limit items per dataset (for testing)")
    parser.add_argument("--llm-backend", choices=["groq", "ollama"], default="groq", help="which LLM_BACKEND to force for single_llm/current_thirdeye/council baselines")
    parser.add_argument("--seed", type=int, default=None, help="seed for council LLM sampling; checkpoints into seed<N>/ namespace. Run with 0,1,2 for the >=3-seed mean+/-std protocol.")
    args = parser.parse_args()

    asyncio.run(main(
        baselines=args.baselines.split(","),
        dataset_names=args.datasets.split(","),
        limit=args.limit,
        llm_backend=args.llm_backend,
        seed=args.seed,
    ))
