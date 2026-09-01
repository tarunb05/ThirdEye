"""
Phase 5: evidence-anchored debate & arbitration — the precision lever for
LLM-only findings.

The council is deliberately high-recall: 8 eager single-class specialists
over-flag, and the evidence-quote gate only removes findings whose quote is
fabricated — it does NOT catch a wrong conclusion drawn about a REAL line of
code (e.g. a dos_gas specialist quoting a real `require` and calling it a DoS).
That residual false-positive class is what arbitration removes.

For each confirmed council finding we run a structured debate:
  - PROPOSER  : the original specialist's claim (already produced; not re-run).
  - RED-TEAM  : a DIFFERENT base model argues the finding is a false positive —
                that the quoted code is actually safe / the attack doesn't work.
  - JUDGE     : a strong reasoning model reads claim + rebuttal + the code and
                renders a verdict with a calibrated confidence, under an
                explicit evidence rubric (dynamic witness > static+precedent >
                LLM-only assertion). It is told to default to "not a real bug"
                when the rebuttal is not clearly defeated — precision-first.

The red-team and judge run on models DIFFERENT from the proposer's, so this is
genuine cross-model adversarial review, not the same weights agreeing with
themselves. A finding survives only if the judge upholds it.

run_full_analysis() and run_council() are untouched; this consumes a council
result and returns a refined one.
"""

import os
import json

from services.council import _query, GROQ_MODEL, CEREBRAS_MODEL, CEREBRAS_API_KEY
from services.llm import LLM_TIMEOUT

# Same fix as council.SPECIALIST_TIMEOUT: 240 was hardcoded here too, so
# LLM_TIMEOUT never governed arbitration either.
ARB_TIMEOUT = int(os.getenv("ARB_TIMEOUT", str(LLM_TIMEOUT)))

# Who plays red-team / judge in each tier. Both must differ from the typical
# proposer model so the review is adversarial across model families.
#   local : proposer is usually qwen2.5-coder:7b or llama3.1:8b -> red-team
#           gemma3:4b (third family), judge llama3.1:8b (strongest local
#           reasoner).
#   hosted: proposer is Llama-3.3-70B (Groq) or gpt-oss-120b (Cerebras) ->
#           red-team and judge on the OTHER family from the proposer.
# Local judge is overridable so the strongest model that FITS can be swapped in
# without a code change. Hardware ceiling on the dev box (4GB VRAM / 15.7GB RAM)
# is the 8B class: a 14B judge (~9GB) does not fit alongside the council's
# working set and pages against disk. qwen3:8b is a newer generation than
# llama3.1:8b at the same footprint, so it replaces rather than adds.
LOCAL_JUDGE_MODEL = os.getenv("LOCAL_JUDGE_MODEL", "qwen3:8b")

_ARBITER_MODELS = {
    "ollama": {"red_team": ("ollama", "gemma3:4b"), "judge": ("ollama", LOCAL_JUDGE_MODEL)},
    "groq": {"red_team": ("cerebras", CEREBRAS_MODEL), "judge": ("groq", GROQ_MODEL)},
    # cerebras: judge AND red-team on the strong hosted reasoner (gpt-oss-120b).
    # Use this even when the COUNCIL ran locally — a measured result here is
    # that an 8B local judge is too weak to adjudicate reliably (it inverted
    # verdicts on eth-046), so the judge needs a strong model regardless of
    # which tier produced the findings. Still cross-family vs local proposers
    # (qwen/llama/gemma), so the review remains genuinely adversarial.
    "cerebras": {"red_team": ("cerebras", CEREBRAS_MODEL), "judge": ("cerebras", CEREBRAS_MODEL)},
}

# The council's backend names ("hosted", "hosted_fast") are NOT arbiter-config
# keys, so a .get() on them silently fell back to the LOCAL arbiters — a hosted
# run was adjudicated by a local 8B judge without anything in the output saying
# so. Map them explicitly.
_ARBITER_MODELS["hosted"] = _ARBITER_MODELS["cerebras"]
_ARBITER_MODELS["hosted_fast"] = _ARBITER_MODELS["cerebras"]


def _pick_arbiters(backend: str, proposer_model: str) -> dict:
    cfg = dict(_ARBITER_MODELS.get(backend, _ARBITER_MODELS["ollama"]))
    # Guarantee the red-team model isn't identical to the proposer's; if it is,
    # swap to the judge's model so the rebuttal is never self-review.
    if cfg["red_team"][1] == proposer_model and cfg["judge"][1] != proposer_model:
        cfg["red_team"] = cfg["judge"]
    return cfg


_RED_TEAM_PROMPT = """You are a skeptical smart-contract auditor on the RED TEAM. Another tool flagged a potential {vuln_type} vulnerability. Your job is to argue, as rigorously as you can, that this is a FALSE POSITIVE — that the quoted code is actually safe or the described attack does not work in this contract.

Flagged finding: {description}
Quoted evidence: {evidence_quote}
Claimed property that would be violated: {proposed_property}

Full contract:
```solidity
{code}
```

Give your strongest rebuttal in 2-4 sentences: why might this NOT be a real, exploitable {vuln_type} bug? Consider guards elsewhere in the contract, modifiers, require checks, the compiler version, and whether the attack is actually reachable. If you genuinely cannot refute it, say so plainly."""

_JUDGE_PROMPT = """You are the JUDGE in an evidence-anchored security debate. Decide whether a flagged vulnerability is REAL and exploitable.

EVIDENCE RUBRIC (weight evidence, not confidence of assertion):
- A dynamic exploit witness (a PoC that runs) = decisive proof it is real.
- Static-tool evidence + a matching known-exploit precedent = strong.
- An LLM specialist's assertion alone = WEAK — it must survive the rebuttal.
Judge on the MERITS: rule REAL only if the quoted code genuinely enables the
described attack given the whole contract (no guard/modifier/version defuses
it); rule NOT-A-BUG if the rebuttal shows the code is actually safe, guarded,
unreachable, or the "bug" is a style/informational nit. Do not rubber-stamp,
but do not reflexively dismiss a well-evidenced finding either — a real bug
with a real quote should be upheld.

VULNERABILITY CLASS: {vuln_type}
PROPOSER's finding: {description}
PROPOSER's quoted evidence: {evidence_quote}
RED-TEAM's rebuttal: {rebuttal}

Contract:
```solidity
{code}
```

Respond with ONLY this JSON (no fences, no prose):
{{"verdict": "real"|"not_a_bug", "calibrated_confidence": 0.0-1.0, "reason": "<one sentence>"}}"""


def _parse_judge(raw: str) -> dict:
    try:
        s, e = raw.find("{"), raw.rfind("}") + 1
        if s != -1 and e > s:
            p = json.loads(raw[s:e])
            return {
                "verdict": str(p.get("verdict", "not_a_bug")).lower(),
                "calibrated_confidence": float(p.get("calibrated_confidence", 0.0)),
                "reason": str(p.get("reason", "")),
            }
    except Exception:
        pass
    # Unparseable judge output -> KEEP the finding, low confidence (fail-safe:
    # a security tool shouldn't silently drop a potential bug because the
    # judge's response didn't parse). It surfaces flagged, not hidden.
    return {"verdict": "real", "calibrated_confidence": 0.4, "reason": "judge output unparseable; finding kept for safety (unvetted)"}


async def _arbitrate_one(finding: dict, code: str, backend: str, seed: int | None) -> dict:
    arbiters = _pick_arbiters(backend, finding.get("model", ""))
    rt_provider, rt_model = arbiters["red_team"]
    j_provider, j_model = arbiters["judge"]

    rebuttal = await _query(rt_provider, rt_model, _RED_TEAM_PROMPT.format(
        vuln_type=finding["type"],
        description=finding.get("description", ""),
        evidence_quote=finding.get("evidence_quote", ""),
        proposed_property=finding.get("proposed_property", ""),
        code=code,
    ), timeout=ARB_TIMEOUT, seed=seed)

    judge_raw = await _query(j_provider, j_model, _JUDGE_PROMPT.format(
        vuln_type=finding["type"],
        description=finding.get("description", ""),
        evidence_quote=finding.get("evidence_quote", ""),
        rebuttal=rebuttal[:1500],
        code=code,
    ), timeout=ARB_TIMEOUT, seed=seed)
    judgment = _parse_judge(judge_raw)

    return {
        **finding,
        "arbitration": {
            "red_team_model": f"{rt_provider}:{rt_model}",
            "judge_model": f"{j_provider}:{j_model}",
            "rebuttal": rebuttal[:600],
            "verdict": judgment["verdict"],
            "reason": judgment["reason"],
        },
        # Judge's calibrated confidence supersedes the proposer's self-reported
        # one — that's the whole point of calibration.
        "confidence": judgment["calibrated_confidence"],
        "upheld": judgment["verdict"] == "real",
    }


async def run_arbitration(code: str, council_result: dict, backend: str | None = None, seed: int | None = None) -> dict:
    """Take a council result, adversarially review every confirmed finding,
    and return a refined result where only judge-upheld findings remain.
    Recomputes final_verdict from the survivors. Adds `arbitration` detail to
    each finding and an `arbitration_summary` block to the result.

    No-op-safe: a GO result (no findings) returns unchanged with an empty
    arbitration summary."""
    backend = backend or os.getenv("LLM_BACKEND", "ollama").lower()
    findings = council_result.get("vulnerabilities", [])
    if not findings:
        out = dict(council_result)
        out["arbitration_summary"] = {"reviewed": 0, "upheld": 0, "dropped": 0}
        out["mode"] = "council+arbitration"
        return out

    import asyncio
    reviewed = await asyncio.gather(*[_arbitrate_one(f, code, backend, seed) for f in findings])
    upheld = [f for f in reviewed if f["upheld"]]
    dropped = [f for f in reviewed if not f["upheld"]]

    out = dict(council_result)
    out["vulnerabilities"] = upheld
    out["dropped_by_arbitration"] = dropped
    out["final_verdict"] = "NO-GO" if upheld else "GO"
    out["arbitration_summary"] = {
        "reviewed": len(reviewed),
        "upheld": len(upheld),
        "dropped": len(dropped),
        "dropped_types": [f["type"] for f in dropped],
    }
    name = council_result.get("contract_name") or "this contract"
    if upheld:
        roles = ", ".join(sorted({f["type"].replace("_", " ") for f in upheld}))
        out["raven_note"] = f"After adversarial cross-model arbitration, {len(upheld)} finding(s) survived on {name}: {roles}. {len(dropped)} were rejected as false positives by the red-team/judge."
    else:
        out["raven_note"] = f"The council raised {len(reviewed)} candidate(s) on {name}, but all were refuted under adversarial arbitration — verdict GO."
    out["mode"] = "council+arbitration"
    return out
