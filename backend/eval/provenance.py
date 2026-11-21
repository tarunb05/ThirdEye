"""Run provenance — what the result JSON must carry to be reproducible.

RQ4 claims verdict agreement across machines on "byte-identical model digests".
Nothing in any result file currently records a digest, a context window, or the
Ollama serving configuration, so the claim is not checkable from the artefact —
by anyone, including us. This module closes that.

Everything here is best-effort and never raises: a run must not die because
`nvidia-smi` is missing. A field that cannot be read is recorded as None, which
is itself informative — a result with `gpu: None` was produced somewhere we
cannot characterise, and should not be compared across hosts.

Attach the dict to every report under a top-level "provenance" key.
"""

from __future__ import annotations

import os
import platform
import subprocess
import time
from datetime import datetime, timezone

# The serving knobs that are known to change verdicts. OLLAMA_NUM_PARALLEL and
# the context window are not performance settings: num_ctx silently truncates
# oversized prompts (RQ3), and parallelism drives queueing into the client-side
# deadline, whose blown calls are not a random sample of contracts (they skew
# large and complex — measured, 9/39 deaths clustered at 303-405 s).
_ENV_KEYS = (
    "LLM_BACKEND",
    "OLLAMA_HOST",
    "OLLAMA_LOGIC_MODEL",
    "OLLAMA_NUM_PARALLEL",
    "OLLAMA_MAX_LOADED_MODELS",
    "OLLAMA_KEEP_ALIVE",
    "OLLAMA_NUM_CTX",
    "COUNCIL_MAX_CONCURRENCY",
    "LLM_TIMEOUT",
)


def _sh(cmd: list[str], timeout: int = 6) -> str | None:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                             encoding="utf-8", errors="replace")
        return out.stdout.strip() or None
    except Exception:  # noqa: BLE001 — provenance must never break a run
        return None


def _git_sha() -> str | None:
    return _sh(["git", "rev-parse", "HEAD"])


def _git_dirty() -> bool | None:
    """-uno: TRACKED changes only. A plain `git status --porcelain` walks the
    untracked tree, which in this repo means the gitignored dataset corpora --
    minutes, not milliseconds, and it stalled a run during testing. Untracked
    files cannot change a result anyway; modified tracked code can."""
    out = _sh(["git", "status", "--porcelain", "-uno"], timeout=15)
    return None if out is None else bool(out)


def _gpu() -> list[dict] | None:
    """Name and total memory per device. Absent on a CPU-only or unified-memory
    host, which is why system RAM is recorded separately."""
    out = _sh(["nvidia-smi", "--query-gpu=name,memory.total,driver_version",
               "--format=csv,noheader"])
    if not out:
        return None
    gpus = []
    for line in out.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 2:
            gpus.append({"name": parts[0], "memory_total": parts[1],
                         "driver": parts[2] if len(parts) > 2 else None})
    return gpus or None


def _system_ram_gb() -> float | None:
    """On GB10/Spark-class hosts the 120 GB is unified and reports as system
    RAM, not as GPU memory — so a result with no GPU row but 120 GB of RAM is a
    different machine from one with neither."""
    try:
        with open("/proc/meminfo") as fh:
            for line in fh:
                if line.startswith("MemTotal:"):
                    return round(int(line.split()[1]) / 1024 / 1024, 1)
    except Exception:  # noqa: BLE001
        pass
    return None


def model_digests(models: list[str]) -> dict:
    """`ollama show --json <model>` digest per model.

    This is the field RQ4 actually rests on. Two hosts "running llama3.1:8b"
    are only comparable if the digests match; a silent re-pull between sessions
    changes the weights under a run whose name did not change.
    """
    digests: dict[str, str | None] = {}
    for m in sorted(set(models)):
        out = _sh(["ollama", "show", "--json", m], timeout=8)
        digest = None
        if out:
            try:
                import json as _json
                blob = _json.loads(out)
                digest = (blob.get("details") or {}).get("digest") or blob.get("digest")
            except Exception:  # noqa: BLE001
                digest = None
        if digest:
            import re as _re
            m1 = _re.search(r"([0-9a-f]{64})", digest)
            digest = m1.group(1) if m1 else digest
        if digest is None:
            # Older ollama has no --json. Fall back to the modelfile text, whose
            # FROM line carries the layer sha. Normalise to the bare 64-hex so
            # two hosts with different model dirs still compare equal.
            text = _sh(["ollama", "show", "--modelfile", m], timeout=8)
            if text:
                import re as _re
                m2 = _re.search(r"sha256[-:]([0-9a-f]{64})", text)
                digest = m2.group(1) if m2 else None
        digests[m] = digest
    return digests


def collect(models: list[str] | None = None, extra: dict | None = None) -> dict:
    """The provenance block. Call once at the start of a run and attach it to
    the report — not at the end, so a run that dies still names its own setup
    in the log."""
    block = {
        "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "started_monotonic": time.time(),
        "host": platform.node(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "git_sha": _git_sha(),
        "git_dirty": _git_dirty(),
        "gpu": _gpu(),
        "system_ram_gb": _system_ram_gb(),
        "env": {k: os.getenv(k) for k in _ENV_KEYS},
        "model_digests": model_digests(models) if models else None,
    }
    if extra:
        block.update(extra)
    return block


def summarise(block: dict) -> str:
    """One line for the run log, so an outage is diagnosable from the log alone
    without opening the JSON."""
    gpus = block.get("gpu") or []
    gpu = ", ".join(g["name"] for g in gpus) if gpus else f"no GPU (RAM {block.get('system_ram_gb')} GB)"
    env = block.get("env") or {}
    return (f"[provenance] host={block.get('host')} gpu={gpu} "
            f"git={(block.get('git_sha') or '?')[:8]}{'+dirty' if block.get('git_dirty') else ''} "
            f"logic_model={env.get('OLLAMA_LOGIC_MODEL')} "
            f"num_parallel={env.get('OLLAMA_NUM_PARALLEL')} "
            f"keep_alive={env.get('OLLAMA_KEEP_ALIVE')}")
