"""
ThirdEye orchestrator — the redesigned pipeline.

    static analysis (Slither)            ─┐
    + lightweight code features           │ ── ROUTER ── selects the RELEVANT
                                          ─┘              specialists (not all 8)
        -> model-diverse council (only the selected specialists)
        -> per-finding evidence gate (council._aggregate)
        -> adversarial arbitration (strong judge)  ── the precision gate
        -> dynamic exploit confirmation (optional)
        -> verdict: GO / NO-GO / INCONCLUSIVE

Two architectural changes vs the old "fire all 8, gate by quorum" design:
  1. STATIC-DRIVEN ROUTING (services/router.py): static + feature signals pick
     which specialists run. Pattern classes are skipped when there's no
     surface; logic classes run on heuristics (static tools can't see them).
     Fewer eager specialists on safe code -> fewer false positives -> a
     well-audited safe contract can actually reach GO.
  2. PRECISION VIA ARBITRATION, NOT QUORUM: each surviving finding is vetted by
     an independent strong judge; the verdict is recomputed from what survives.

run_full_analysis() / run_council() are composed, not modified.
"""

import os
from services.council import run_council, _assemble_result  # noqa: F401 (kept for parity)
from services.router import select_specialists
from services.llm import preanalyze_code


async def _static_findings(code: str) -> list[dict] | None:
    """Best-effort Slither run for routing. Returns a list of detector hits, or
    None if Slither isn't available / can't compile (router then relies on
    feature heuristics alone). Never raises."""
    try:
        from services.slither import run_slither
        from services.llm import _parse_slither
        import asyncio
        out = await asyncio.to_thread(run_slither, code)
        if out.get("status") == "completed":
            return _parse_slither(out)
    except Exception:
        pass
    return None


async def run_thirdeye(
    code: str,
    backend: str | None = None,
    seed: int | None = None,
    use_static_router: bool = True,
    use_retrieval: bool = True,
    use_arbitration: bool = True,
    use_dynamic: bool = False,
    arbitration_backend: str | None = None,
) -> dict:
    """Full ThirdEye pipeline with per-stage toggles (also the ablation knobs).
    Returns the council schema augmented with routing/static/arbitration/dynamic
    detail and a `pipeline` block recording which stages ran."""
    backend = backend or os.getenv("LLM_BACKEND", "ollama").lower()
    stages = {"static_router": False, "retrieval": False, "council": True, "arbitration": False, "dynamic": False}

    # 1. Static analysis + features -> router
    features = preanalyze_code(code)
    static = await _static_findings(code) if use_static_router else None
    routed = select_specialists(code, features, static)
    roles = routed["roles"] if use_static_router else None
    stages["static_router"] = use_static_router
    stages["static_used"] = routed.get("static_used", False)

    # 2. Retrieval (precedents surfaced; see retrieval.py)
    similar = []
    if use_retrieval:
        try:
            from services.retrieval import find_similar
            similar = await find_similar(code, k=3)
            stages["retrieval"] = True
        except Exception as e:
            stages["retrieval_error"] = str(e)[:200]

    # 3. Council over the SELECTED specialists only
    result = await run_council(code, similar_exploits=similar, backend=backend, seed=seed, roles=roles)
    result["routing"] = routed
    result["static_findings"] = static or []

    # 4. Arbitration — skip if the scan was inconclusive (don't vet a broken run)
    if use_arbitration and result.get("vulnerabilities") and result.get("final_verdict") != "INCONCLUSIVE":
        from services.arbitration import run_arbitration
        # Arbitration follows the RUN's backend unless explicitly overridden.
        # It used to default to Cerebras whenever a key existed, which meant a
        # run invoked as backend="ollama" silently made hosted 120B calls for
        # its precision gate — the "local tier" was not local, an unreportable
        # confound. It also meant a drained hosted quota cost ~125s/contract
        # sleeping in retry backoff while the judge failed open anyway.
        # Pass arbitration_backend="cerebras" explicitly to get the strong
        # hosted judge back.
        ab = arbitration_backend or backend
        result = await run_arbitration(code, result, backend=ab, seed=seed)
        stages["arbitration"] = True
        stages["arbitration_backend"] = ab
        # Recompute verdict from survivors (arbitration already sets final_verdict,
        # but keep INCONCLUSIVE sticky if it somehow got set). Also refresh the
        # verdict_reason so it reflects the POST-arbitration state, not the stale
        # pre-arbitration council reason.
        if result.get("final_verdict") != "INCONCLUSIVE":
            survivors = result.get("vulnerabilities") or []
            dropped = (result.get("arbitration_summary") or {}).get("dropped", 0)
            result["final_verdict"] = "NO-GO" if survivors else "GO"
            if survivors:
                classes = ", ".join(sorted({v["type"].replace("_", " ") for v in survivors}))
                result["verdict_reason"] = f"{len(survivors)} finding(s) upheld by independent arbitration: {classes}."
            else:
                result["verdict_reason"] = (
                    f"Arbitration rejected all {dropped} candidate finding(s) as false positives — contract is clean."
                    if dropped else "No findings — contract is clean."
                )

    # 5. Dynamic confirmation (optional; off by default — Foundry rarely present in prod)
    if use_dynamic:
        from services.dynamic import confirm_findings
        result = await confirm_findings(code, result)
        stages["dynamic"] = True

    result["pipeline"] = stages
    result["mode"] = "thirdeye"
    return result


# Backwards-compatible alias — the old endpoint/name still works.
async def run_argus(code: str, **kw) -> dict:
    return await run_thirdeye(code, **kw)
