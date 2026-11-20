# -*- coding: utf-8 -*-
"""Is this machine actually able to run a live scan, right now?

WHY THIS EXISTS, concretely. On 2026-10-24, setting up the demo, Ollama was
restarted from a shell that happened to export OLLAMA_MODELS pointing at a
SECOND model store on another drive. The server came up healthy, answered
/api/tags with five models, and served requests -- but they were the wrong five.
Every qwen2.5-coder:7b call 404'd, three of four specialists errored, and both
sample contracts returned INCONCLUSIVE.

Nothing about that looked like a configuration error from the outside. "Ollama
is running" was true. "Models are installed" was true. "Five models are
available" was true. The only false statement was the one nobody checked: that
the models THIS COUNCIL NEEDS, by name, were among them.

That is the same defect the evaluation harness was bitten by earlier in the
project (FINDINGS.md E5: the preflight gate counted models and passed on a day
the judge model was absent). So this checks names, not counts, and reports what
is missing with the command that fixes it.
"""
from __future__ import annotations

import os
import shutil

import httpx

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")


def required_models() -> list[str]:
    """The distinct models the shipped local council actually dispatches to."""
    from services.council import OLLAMA_ASSIGNMENTS

    return sorted(set(OLLAMA_ASSIGNMENTS.values()))


async def preflight() -> dict:
    """Everything the UI needs to tell a user why a live scan will or will not work."""
    from services.council import ALLOW_CLOUD

    need = required_models()
    out: dict = {
        "mode": "cloud-enabled" if ALLOW_CLOUD else "local-only",
        "ollama_url": OLLAMA_URL,
        "required_models": need,
        "present": [],
        "missing": [],
        "ollama_running": False,
        "ready": False,
        "problems": [],
        "fixes": [],
        # Not required -- arbitration ships off -- but reported so the page can
        # say why the judge is unavailable instead of staying silent about it.
        "judge_model": os.getenv("LOCAL_JUDGE_MODEL", "qwen3:8b"),
        "judge_present": False,
        "slither": bool(shutil.which("slither")),
    }

    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            r = await client.get(f"{OLLAMA_URL}/api/tags")
            r.raise_for_status()
            have = {m.get("name", "") for m in (r.json().get("models") or [])}
        out["ollama_running"] = True
    except Exception as e:  # noqa: BLE001
        out["problems"].append(
            f"Ollama is not reachable at {OLLAMA_URL} ({type(e).__name__}). "
            f"Live scanning is unavailable; cached sample results still render."
        )
        out["fixes"].append("ollama serve")
        return out

    out["present"] = sorted(m for m in need if m in have)
    out["missing"] = sorted(m for m in need if m not in have)
    out["judge_present"] = out["judge_model"] in have
    out["models_visible"] = sorted(have)

    if out["missing"]:
        out["problems"].append(
            f"Ollama is running but {len(out['missing'])} of {len(need)} council "
            f"models are not in the store it is serving: {', '.join(out['missing'])}. "
            f"A scan will not fail loudly -- those specialists error, and the "
            f"verdict degrades to INCONCLUSIVE."
        )
        for m in out["missing"]:
            out["fixes"].append(f"ollama pull {m}")
        if os.getenv("OLLAMA_MODELS"):
            out["problems"].append(
                f"OLLAMA_MODELS is set to {os.getenv('OLLAMA_MODELS')!r}. If the "
                f"models are installed elsewhere, the server is serving the wrong "
                f"store -- restart Ollama with that variable unset."
            )

    out["ready"] = out["ollama_running"] and not out["missing"]
    return out
