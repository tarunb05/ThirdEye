"""
Phase 3+ : the model-diverse specialist council.

This is a genuine alternative pipeline to llm.py's run_full_analysis() — not
a wrapper around it. Eight single-purpose specialist agents (the OWASP Smart
Contract Top-10 logic classes), each PINNED to a specific base model so the
council has real architectural diversity, not three prompts against the same
weights (the "echo chamber" failure the plan explicitly rejects). A pure-Python
aggregation judge (no LLM call) decides which findings are CONFIRMED via
cross-specialist agreement or a single high-confidence, quote-backed finding.

Two model tiers, both genuinely diverse (see SPECIALISTS / *_ASSIGNMENTS):
  - hosted  : Groq (Llama-3.3-70B) + Cerebras (gpt-oss-120b) — 2 model families
  - local   : Ollama qwen2.5-coder:7b + llama3.1:8b + gemma3:4b — 3 families

Each specialist also proposes a testable PROPERTY/invariant — the seed the
dynamic-confirmation layer (services/dynamic.py) turns into a fuzz harness.

llm.py's run_full_analysis() is untouched; this module's entry point is
run_council().
"""

import httpx
import os
import json
import re
import asyncio

from services.llm import OLLAMA_URL, GROQ_API_KEY, GROQ_URL, LLM_TIMEOUT, preanalyze_code
import sys

CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY", "")
CEREBRAS_MODEL = os.getenv("CEREBRAS_MODEL", "gpt-oss-120b")
# Second Cerebras model family (GLM vs gpt-oss) — gives the hosted tier genuine
# two-family diversity WITHOUT Groq. Used when a Groq key is absent/invalid.
CEREBRAS_MODEL_B = os.getenv("CEREBRAS_MODEL_B", "zai-glm-4.7")
CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Whether a usable Groq key is configured. If not, the hosted tier runs fully
# on Cerebras's two model families instead of Groq+Cerebras (see
# specialist_assignments). gsk_ keys that are present but invalid still set
# this True — we can't validate without a call — so a dead key surfaces as
# per-specialist llm_error, not a silent all-Cerebras swap.
_HAS_GROQ = bool(GROQ_API_KEY)


# ─── Specialist definitions ───
# Each specialist is one OWASP/DASP logic class with a tight definition and a
# vulnerable + safe few-shot pair (so the model pattern-matches rather than
# free-associates). `property_hint` is the natural-language invariant the
# dynamic layer will try to falsify with a fuzzer.

SPECIALISTS = [
    {
        "role": "reentrancy",
        "definition": "an external call (.call/.send/low-level call / interaction with an untrusted address) happens BEFORE a state variable is updated, letting the callee re-enter and exploit stale state (violates Checks-Effects-Interactions).",
        "vulnerable": "(bool ok,) = msg.sender.call{value: amount}(\"\");\nrequire(ok);\nbalances[msg.sender] -= amount;  // state update AFTER external call",
        "safe": "balances[msg.sender] -= amount;  // state update FIRST\n(bool ok,) = msg.sender.call{value: amount}(\"\");\nrequire(ok);",
        "property_hint": "no function allows a caller's balance to be withdrawn more than once per deposit (sum of withdrawals <= deposits per account).",
    },
    {
        "role": "access_control",
        "definition": "a sensitive function (withdraw/mint/burn/selfdestruct/setOwner/pause/upgrade) has NO restriction on who may call it, or uses a broken check (e.g. tx.origin instead of msg.sender).",
        "vulnerable": "function withdrawAll() public {\n    payable(msg.sender).transfer(address(this).balance);  // anyone can drain\n}",
        "safe": "function withdrawAll() public onlyOwner {\n    payable(msg.sender).transfer(address(this).balance);\n}",
        "property_hint": "only the designated owner/role can invoke privileged state-changing functions.",
    },
    {
        "role": "arithmetic",
        "definition": "integer overflow/underflow (pre-0.8 without SafeMath, or unchecked{} blocks), precision loss, or incorrect rounding/scaling in fee/interest/share math that lets a user extract value.",
        "vulnerable": "function transfer(address to, uint v) public {\n    balances[msg.sender] -= v;  // underflows below zero pre-0.8\n    balances[to] += v;\n}",
        "safe": "require(balances[msg.sender] >= v, \"insufficient\");\nbalances[msg.sender] -= v;\nbalances[to] += v;",
        "property_hint": "token/share accounting never lets total balances exceed total supply, and no balance underflows.",
    },
    {
        "role": "business_logic",
        "definition": "a flaw in the contract's intended rules: missing validation that lets a user bypass an intended constraint (e.g. accepting a bid below the highest), an invariant the contract assumes but never enforces, or a mis-ordered state machine.",
        "vulnerable": "function bid() public payable {\n    highestBidder = msg.sender;   // no check msg.value > highestBid\n    highestBid = msg.value;\n}",
        "safe": "require(msg.value > highestBid, \"bid too low\");\nhighestBidder = msg.sender;\nhighestBid = msg.value;",
        "property_hint": "the contract's core invariant (e.g. highestBid is monotonically non-decreasing) always holds after every state transition.",
    },
    {
        "role": "oracle_price_manipulation",
        "definition": "the contract reads a price/exchange rate from a manipulable source — spot reserves of an AMM pool (getReserves/balanceOf of a pair), a single-block TWAP, or an unvalidated oracle — that a flash-loan can move within one transaction.",
        "vulnerable": "uint price = token.balanceOf(pair) / weth.balanceOf(pair);  // spot reserves, flash-loanable",
        "safe": "uint price = chainlinkFeed.latestAnswer();  // external, manipulation-resistant feed with staleness checks",
        "property_hint": "no price used for valuation can be moved by a single attacker transaction (flash-loan resistant).",
    },
    {
        "role": "flashloan_mev",
        "definition": "logic that is exploitable when an attacker has unlimited capital for one transaction (flash loan) or can reorder/sandwich txs (MEV): governance by spot token balance, single-tx deposit+borrow+withdraw loops, missing slippage bounds.",
        "vulnerable": "uint votes = token.balanceOf(msg.sender);  // governance weight = spot balance, flash-loanable\nrequire(votes > quorum);",
        "safe": "uint votes = token.getPastVotes(msg.sender, proposalSnapshotBlock);  // snapshot, not spot",
        "property_hint": "no privileged outcome (governance, reward, liquidation) can be obtained within a single flash-loaned transaction.",
    },
    {
        "role": "dos_gas",
        "definition": "denial of service: unbounded loops over user-controlled arrays, a push-payment pattern where one reverting recipient blocks everyone, or a critical path that can be made to always revert / exceed the block gas limit.",
        "vulnerable": "for (uint i = 0; i < investors.length; i++) {\n    payable(investors[i]).transfer(amount);  // one revert blocks all\n}",
        "safe": "// pull-payment: each investor withdraws their own balance\npayments[msg.sender] = 0;\npayable(msg.sender).transfer(amount);",
        "property_hint": "no single external account can permanently block a critical function for all other users.",
    },
    {
        "role": "proxy_upgradeability",
        "definition": "upgradeable-proxy hazards: unprotected initializer (can be re-called to seize ownership), uninitialized implementation, storage-layout collision between proxy and logic, or delegatecall to an attacker-controlled address.",
        "vulnerable": "function initialize(address owner_) public {\n    owner = owner_;  // no initializer guard — re-callable to hijack\n}",
        "safe": "function initialize(address owner_) public initializer {\n    owner = owner_;\n}",
        "property_hint": "the initializer can be executed at most once and only by the deployer; no delegatecall target is attacker-controlled.",
    },
]

SPECIALIST_ROLES = [s["role"] for s in SPECIALISTS]
_SPECIALIST_BY_ROLE = {s["role"]: s for s in SPECIALISTS}


# ─── Model assignments: distribute the 8 roles across genuinely different
# base models within each tier. Code-pattern-heavy classes go to the
# code-specialized / strongest model; semantic/holistic classes go to the
# general reasoner — diversity by design, not arbitrary. ───

# Local tier: 3 distinct model families on Ollama.
# The llama-family slot is env-overridable because model SIZE, not quality, is
# the binding constraint on a 4GB GPU. llama3.1:8b (4.9GB) does not fit in VRAM:
# measured ~190s per call for a 3-word prompt, and under run-time memory
# pressure the load fails outright — it sat on business_logic, which the router
# ALWAYS runs, so every contract paid it and 33% of them abstained. llama3.2:3b
# (2.0GB) fits entirely in VRAM. Three distinct families (qwen/llama/gemma) are
# preserved either way, so the model-diversity claim is unaffected.
# Set OLLAMA_LOGIC_MODEL=llama3.1:8b on a bigger GPU to restore the 8B.
LOGIC_MODEL = os.getenv("OLLAMA_LOGIC_MODEL", "llama3.2:3b")

OLLAMA_ASSIGNMENTS = {
    "reentrancy": "qwen2.5-coder:7b",
    "access_control": "qwen2.5-coder:7b",
    "arithmetic": "qwen2.5-coder:7b",
    "proxy_upgradeability": "qwen2.5-coder:7b",
    "business_logic": LOGIC_MODEL,
    "oracle_price_manipulation": LOGIC_MODEL,
    "flashloan_mev": LOGIC_MODEL,
    "dos_gas": "gemma3:4b",
}

# Hosted tier, Groq+Cerebras variant: 2 families (Llama-3.3-70B via Groq,
# gpt-oss-120b via Cerebras). Used only when a valid Groq key is present.
GROQ_CEREBRAS_ASSIGNMENTS = {
    "reentrancy": ("groq", GROQ_MODEL),
    "access_control": ("cerebras", CEREBRAS_MODEL),
    "arithmetic": ("groq", GROQ_MODEL),
    "proxy_upgradeability": ("cerebras", CEREBRAS_MODEL),
    "business_logic": ("cerebras", CEREBRAS_MODEL),
    "oracle_price_manipulation": ("groq", GROQ_MODEL),
    "flashloan_mev": ("cerebras", CEREBRAS_MODEL),
    "dos_gas": ("groq", GROQ_MODEL),
}

# Hosted tier, Cerebras-only variant: 2 families on one provider
# (gpt-oss-120b vs zai-glm-4.7). This is the DEFAULT hosted tier when no Groq
# key — genuine architectural diversity without a second provider. Split so
# neither model sees all of one "kind" of bug.
CEREBRAS_DUAL_ASSIGNMENTS = {
    "reentrancy": ("cerebras", CEREBRAS_MODEL),
    "access_control": ("cerebras", CEREBRAS_MODEL_B),
    "arithmetic": ("cerebras", CEREBRAS_MODEL),
    "proxy_upgradeability": ("cerebras", CEREBRAS_MODEL_B),
    "business_logic": ("cerebras", CEREBRAS_MODEL_B),
    "oracle_price_manipulation": ("cerebras", CEREBRAS_MODEL),
    "flashloan_mev": ("cerebras", CEREBRAS_MODEL_B),
    "dos_gas": ("cerebras", CEREBRAS_MODEL),
}


def specialist_assignments(backend: str) -> dict:
    """Returns {role: (provider, model)} for all 8 specialists. backend is
    "ollama" (local tier) or "groq"/"hosted" (hosted tier). The hosted tier
    uses Groq+Cerebras when a Groq key is configured, else Cerebras's two
    model families (gpt-oss-120b + zai-glm-4.7) — still genuine diversity."""
    if backend == "hosted_fast":
        # Scale tier: all specialists on the fast model (gpt-oss-120b), ~5-10s
        # per contract for large batches. Trades the second model family for
        # throughput — use for thousands-scale runs, not for the headline
        # diversity claim.
        return {s["role"]: ("cerebras", CEREBRAS_MODEL) for s in SPECIALISTS}
    if backend in ("groq", "hosted"):
        return dict(GROQ_CEREBRAS_ASSIGNMENTS if _HAS_GROQ else CEREBRAS_DUAL_ASSIGNMENTS)
    return {role: ("ollama", model) for role, model in OLLAMA_ASSIGNMENTS.items()}


# ─── Provider-level query functions (parameterized on an explicit model and
# optional seed — llm.py's helpers always use the single globally-detected
# model, which is exactly what a diverse council must NOT do). ───

# Specialist errors were previously swallowed into a return string with no trace,
# so a run could quarantine contracts all day without revealing WHY. A GO verdict
# with an errored specialist is unsound and gets quarantined, which means these
# failures cost whole contracts -- and they are not random, so they bias the
# scored sample. If they are happening, they must be visible.
def _warn(model: str, kind: str, detail: str = "") -> None:
    print(f"[council] {model} {kind}: {detail}", file=sys.stderr, flush=True)


# The context window, as an EXPLICIT per-request option rather than an invisible
# server setting.
#
# It was governed only by OLLAMA_CONTEXT_LENGTH on the server, which meant the
# single most consequential knob in the whole pipeline was not recorded in any
# run config, could not be varied without restarting Ollama, and truncated
# silently when exceeded. Measured on the benchmark corpus: 24% of contracts
# (540/2250) build a prompt longer than 4096 tokens, and Ollama's own
# prompt_eval_count confirms the overflow is simply cut -- 2050 tokens evaluated
# out of a ~11.8k-token prompt. The specialist then judges a fraction of the
# contract and reports a verdict as if it had seen all of it.
#
# The truncation is NOT class-balanced: 350 of those 540 are vulnerable against
# 190 safe, because buggy real-world contracts are bigger. So it suppresses
# recall specifically, which is the direction that flatters a false-alarm paper.
# 0 keeps Ollama's server default.
NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "0"))


async def _query_ollama_model(model: str, prompt: str, timeout: int | None = None, seed: int | None = None) -> str:
    options = {}
    if seed is not None:
        options["seed"] = seed  # Ollama honours options.seed for reproducible sampling
    if NUM_CTX:
        options["num_ctx"] = NUM_CTX
    async with httpx.AsyncClient() as client:
        try:
            body = {"model": model, "prompt": prompt, "stream": False}
            if options:
                body["options"] = options
            resp = await client.post(f"{OLLAMA_URL}/api/generate", json=body, timeout=timeout or LLM_TIMEOUT)
            if resp.status_code == 200:
                return resp.json().get("response", "")
            _warn(model, f"HTTP {resp.status_code}", resp.text[:200])
            return f"[LLM Error {resp.status_code}]"
        except httpx.TimeoutException:
            _warn(model, "timeout", f"after {timeout or LLM_TIMEOUT}s")
            return "[LLM timeout]"
        except httpx.ConnectError:
            _warn(model, "connect", OLLAMA_URL)
            return "[Ollama not running]"
        except Exception as e:
            _warn(model, type(e).__name__, str(e)[:200])
            return f"[Error: {e}]"


async def _query_openai_compatible(url: str, api_key: str, model: str, prompt: str, provider_label: str, timeout: int | None = None, seed: int | None = None) -> str:
    if not api_key:
        return f"[{provider_label} API key not configured]"
    body = {"model": model, "messages": [{"role": "user", "content": prompt}], "stream": False}
    if seed is not None:
        body["seed"] = seed  # OpenAI-compatible best-effort determinism (Groq supports it; Cerebras may ignore)
    # Free hosted tiers rate-limit bursts (a parallel fan-out of 8 specialists
    # easily trips a 429). Retry 429/5xx with backoff, honouring Retry-After.
    delays = [1, 2, 4, 8, 16]
    async with httpx.AsyncClient() as client:
        for attempt, delay in enumerate([0] + delays):
            if delay:
                await asyncio.sleep(delay)
            try:
                resp = await client.post(url, headers={"Authorization": f"Bearer {api_key}"}, json=body, timeout=timeout or LLM_TIMEOUT)
                if resp.status_code == 200:
                    return resp.json()["choices"][0]["message"]["content"]
                if resp.status_code == 429 or resp.status_code >= 500:
                    ra = resp.headers.get("retry-after")
                    if ra:
                        try:
                            await asyncio.sleep(min(float(ra), 30))
                        except ValueError:
                            pass
                    if attempt < len(delays):
                        continue
                return f"[LLM Error {resp.status_code}: {resp.text[:200]}]"
            except httpx.TimeoutException:
                if attempt < len(delays):
                    continue
                return "[LLM timeout]"
            except httpx.ConnectError:
                return f"[{provider_label} unreachable]"
            except Exception as e:
                return f"[Error: {e}]"
    return f"[{provider_label} retries exhausted]"


# ─── API-call accounting ──────────────────────────────────────────────
# Every LLM request in the whole pipeline (council specialists, red-team,
# judge) flows through _query(), so this is the one honest choke point to
# count calls. The counter feeds two things: the benchmark's calls-per-
# contract stat (which sizes a sensible per-user rate limit) and any future
# per-request budgeting. Zero overhead when unused.
_API_CALL_COUNT = {"total": 0, "by_provider": {}}


def reset_api_call_count() -> None:
    _API_CALL_COUNT["total"] = 0
    _API_CALL_COUNT["by_provider"] = {}


def get_api_call_count() -> dict:
    return {"total": _API_CALL_COUNT["total"], "by_provider": dict(_API_CALL_COUNT["by_provider"])}


async def _query(provider: str, model: str, prompt: str, timeout: int | None = None, seed: int | None = None) -> str:
    _API_CALL_COUNT["total"] += 1
    _API_CALL_COUNT["by_provider"][provider] = _API_CALL_COUNT["by_provider"].get(provider, 0) + 1
    if provider == "ollama":
        return await _query_ollama_model(model, prompt, timeout, seed)
    if provider == "groq":
        return await _query_openai_compatible(GROQ_URL, GROQ_API_KEY, model, prompt, "Groq", timeout, seed)
    if provider == "cerebras":
        return await _query_openai_compatible(CEREBRAS_URL, CEREBRAS_API_KEY, model, prompt, "Cerebras", timeout, seed)
    raise ValueError(f"unknown provider: {provider}")


_ERROR_MARKERS = ("[LLM Error", "[LLM timeout]", "not running]", "unreachable]", "[Error:", "not configured]")


def _is_error_response(raw: str) -> bool:
    return any(marker in raw for marker in _ERROR_MARKERS)


# ─── Prompt template (one parameterized template, not 8 copies) ───

_PROMPT_TEMPLATE = """You are a smart-contract security specialist with EXACTLY ONE job: detect {role_title} vulnerabilities in the Solidity contract below. Ignore every other vulnerability class — other specialists cover those.

DEFINITION: A {role_title} vulnerability is when {definition}

VULNERABLE EXAMPLE:
```solidity
{vulnerable}
```

SAFE COUNTER-EXAMPLE:
```solidity
{safe}
```

Respond with ONLY a JSON object — no markdown fences, no prose:
{{"type": "{role}", "severity": "critical|high|medium|low", "confidence": 0.0-1.0, "evidence_quote": "<verbatim line(s) copied EXACTLY from the contract that prove the finding, or empty string>", "property": "<one-sentence testable invariant that, if violated, confirms this bug>", "found": true|false}}

evidence_quote MUST be copied verbatim from the contract below (not paraphrased). If you cannot quote a specific vulnerable line, set found=false and evidence_quote="".

```solidity
{code}
```

JSON:"""


def _build_prompt(spec: dict, code: str) -> str:
    return _PROMPT_TEMPLATE.format(
        role=spec["role"],
        role_title=spec["role"].replace("_", " "),
        definition=spec["definition"],
        vulnerable=spec["vulnerable"],
        safe=spec["safe"],
        code=code,
    )


def _parse_specialist_json(raw: str, role: str) -> dict:
    """Extract the specialist's JSON. Any parse failure or error marker is
    treated as found=False — a specialist that can't produce valid output
    contributes nothing rather than a hallucinated finding.

    A response that yields NO parseable JSON object is treated as a call
    FAILURE (`_error` set), not a clean found=False. This is critical for the
    fail-closed verdict: a degraded-but-alive backend (e.g. Ollama returning
    HTTP 200 with an empty/garbage body under load) does NOT emit an error
    marker, so without this it would silently read as "specialist ran, found
    nothing" and drive a false GO. An empty/unparseable body means the
    specialist effectively didn't run."""
    default = {"type": role, "severity": "low", "confidence": 0.0, "evidence_quote": "", "property": "", "found": False}
    if _is_error_response(raw):
        return {**default, "_error": raw}
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end > start:
            parsed = json.loads(raw[start:end])
            return {
                "type": str(parsed.get("type", role)),
                "severity": str(parsed.get("severity", "low")).lower(),
                "confidence": float(parsed.get("confidence", 0.0)),
                "evidence_quote": str(parsed.get("evidence_quote", "") or ""),
                "property": str(parsed.get("property", "") or ""),
                "found": bool(parsed.get("found", False)),
            }
    except Exception:
        pass
    # No usable JSON came back — this is a failed call, not a clean negative.
    return {**default, "_error": f"[unparseable specialist output: {raw[:80]!r}]"}


def _normalize_for_quote_check(s: str) -> str:
    """Whitespace-insensitive normalization for the substring check — models
    reliably reproduce a quoted line's tokens but not always its exact
    indentation. Collapsing whitespace is the minimum that doesn't let a
    fabricated quote pass; it does not fuzzy-match different code."""
    return re.sub(r"\s+", " ", s).strip()


def quote_appears_in_code(quote: str, code: str) -> bool:
    if not quote or not quote.strip():
        return False
    return _normalize_for_quote_check(quote) in _normalize_for_quote_check(code)


# The per-specialist wait. This was hardcoded to 240 while _query does
# "timeout or LLM_TIMEOUT", so passing 240 explicitly meant LLM_TIMEOUT was
# DEAD: setting LLM_TIMEOUT=600 for a big-GPU run changed nothing, and every
# call was still capped at 240s on every machine.
#
# That is not merely a throughput bug. With N contracts in flight x 8
# specialists against OLLAMA_NUM_PARALLEL, requests QUEUE, and queue wait counts
# against this client-side deadline. A timeout returns an error marker, which
# fails closed to INCONCLUSIVE and quarantines the contract -- and the calls that
# blow the deadline are the LARGE, COMPLEX contracts. Dropping those biases the
# scored sample toward simpler code, which is a threat to validity, not a
# slowdown. On the campus GB10 it was discarding 23% of contracts.
SPECIALIST_TIMEOUT = int(os.getenv("SPECIALIST_TIMEOUT", str(LLM_TIMEOUT)))


async def _run_specialist(spec: dict, provider: str, model: str, code: str, seed: int | None) -> dict:
    raw = await _query(provider, model, _build_prompt(spec, code), timeout=SPECIALIST_TIMEOUT, seed=seed)
    result = _parse_specialist_json(raw, spec["role"])
    # If the specialist found something but proposed no property, fall back to
    # the curated property_hint so the dynamic layer always has a target.
    if result["found"] and not result["property"]:
        result["property"] = spec.get("property_hint", "")
    result["role"] = spec["role"]
    result["provider"] = provider
    result["model"] = model
    # A call is failed if it returned an error MARKER or produced no usable
    # JSON (`_error` set by _parse_specialist_json). Both must count toward the
    # fail-closed threshold, else a degraded backend reads as a clean GO.
    result["llm_error"] = _is_error_response(raw) or ("_error" in result)
    return result


# Per-finding confidence floor for the pre-arbitration gate. Precision is
# enforced downstream by the strong-judge arbitration; this just drops
# low-confidence noise and fabricated-evidence findings.
CONF_MIN = float(os.getenv("COUNCIL_CONF_MIN", "0.6"))


def _aggregate(specialist_results: list[dict], code: str) -> list[dict]:
    """Pure-Python evidence gate — PER FINDING, no cross-class quorum.

    Each of the 8 specialists hunts a DIFFERENT bug class, so "two specialists
    flagged something" is two unrelated findings, NOT corroboration of one
    claim. The old >=2-agreement rule dressed that up as consensus; it's
    removed. Instead every finding stands on its OWN evidence:
      keep a finding iff  found=True  AND  its evidence_quote actually appears
      in the submitted source  AND  confidence >= CONF_MIN.
    Genuine precision is then applied by the adversarial arbitration stage
    (services/arbitration.py), which vets each surviving finding with a strong
    independent judge — real per-finding review, not a vote count."""
    return [
        r for r in specialist_results
        if r["found"]
        and r["confidence"] >= CONF_MIN
        and quote_appears_in_code(r["evidence_quote"], code)
    ]


# Contract-level risk threshold. THIS is the rule the paper's headline result
# measures, and until now it lived only in eval/weighted_aggregation.py while
# the live tool shipped the OR-gate (= this rule at tau -> 0).
#
#   risk = 1 - PROD_i (1 - conf_i)        NO-GO iff risk >= RISK_TAU
#
# tau=0.925 was tuned on dev splits and re-picked identically in 8 of 10 random
# splits (the other two chose 0.975), so it is a stable operating point rather
# than one lucky partition. Measured on n=233, held out:
#
#   OR-gate (any survivor blocks)  FPR 0.648  recall 0.938  F1 0.703
#   risk >= 0.925                  FPR 0.268  recall 0.851  F1 0.790
#
# Per-class weights are deliberately NOT applied: the control in
# weighted_aggregation.py showed they lose to the plain threshold (4/10 splits)
# and roughly double its variance.
RISK_TAU = float(os.getenv("COUNCIL_RISK_TAU", "0.925"))


def _contract_risk(confirmed: list[dict]) -> float:
    """Noisy-OR over the confidences of findings that cleared the evidence gate.

    Pooling matters: one medium-confidence finding no longer blocks a contract
    on its own, but several do, and one near-certain finding still does. That is
    the whole difference between this and the OR-gate.

    Mirrors eval/weighted_aggregation.py::risk with all weights = 1, including
    its treatment of a missing confidence as 1.0, so the live verdict and the
    offline measurement cannot drift apart.
    """
    p = 1.0
    for r in confirmed:
        conf = r.get("confidence")
        conf = 1.0 if conf is None else max(0.0, min(1.0, float(conf)))
        p *= 1.0 - conf
    return 1.0 - p


def _filter_assignments(assignments: dict, roles: list[str] | None) -> dict:
    """Restrict the specialist set to `roles` (from services/router.py). None =
    run all. Empty selection falls back to all (never analyze nothing)."""
    if not roles:
        return assignments
    picked = {r: assignments[r] for r in roles if r in assignments}
    return picked or assignments


async def run_council_stream(code: str, backend: str | None = None, seed: int | None = None, roles: list[str] | None = None):
    """Async generator yielding live progress events for the UI, so the user
    sees each specialist resolve instead of staring at a spinner. Event shapes:
      {"event":"start", "specialists":[{role,model,provider}...], "tier":...}
      {"event":"specialist_done", "role":.., "model":.., "found":.., "confidence":.., "severity":.., "evidence_quote":..}
      {"event":"final", "result": <full run_council-shaped dict>}
    Runs the same specialists as run_council and assembles an identical final
    result, so the streaming and non-streaming paths never diverge."""
    backend = backend or os.getenv("LLM_BACKEND", "ollama").lower()
    assignments = _filter_assignments(specialist_assignments(backend), roles)
    features = preanalyze_code(code)

    yield {"event": "start", "tier": backend,
           "specialists": [{"role": r, "provider": p, "model": m} for r, (p, m) in assignments.items()]}

    max_conc = int(os.getenv("COUNCIL_MAX_CONCURRENCY", "3" if backend != "ollama" else "8"))
    sem = asyncio.Semaphore(max_conc)

    async def _bounded(role, provider, model):
        async with sem:
            return await _run_specialist(_SPECIALIST_BY_ROLE[role], provider, model, code, seed)

    # Same model-grouped scheduling as run_council, so the streaming and
    # non-streaming paths never diverge (see _schedule_groups).
    specialist_results = []
    for group in _schedule_groups(assignments, backend):
        tasks = [asyncio.create_task(_bounded(role, p, m)) for role, p, m in group]
        for coro in asyncio.as_completed(tasks):
            r = await coro
            specialist_results.append(r)
            yield {"event": "specialist_done", "role": r["role"], "model": r["model"],
                   "provider": r["provider"], "found": r["found"], "confidence": r["confidence"],
                   "severity": r["severity"], "evidence_quote": r["evidence_quote"][:200],
                   "llm_error": r["llm_error"]}

    final = _assemble_result(code, features, specialist_results, backend, None)
    yield {"event": "final", "result": final}


def _assemble_result(code: str, features: dict, specialist_results: list[dict], backend: str, similar_exploits: list | None) -> dict:
    """Shared result assembly for run_council and run_council_stream."""
    llm_error_detected = any(r["llm_error"] for r in specialist_results)
    confirmed = _aggregate(specialist_results, code)
    # Context-aware suppression (services/suppression.py) runs BETWEEN the
    # evidence gate and the risk pooling, so a structurally-impossible finding
    # cannot inflate the noisy-OR product. Suppressed findings are still
    # reported — they are only barred from driving the block decision.
    from services.suppression import suppress as _suppress
    confirmed, suppressed = _suppress(confirmed, code, features)
    vulnerabilities = [
        {
            "type": r["type"], "line": None, "severity": r["severity"], "confidence": r["confidence"],
            "description": f"Confirmed by {r['role']} specialist ({r['model']}). Evidence: {r['evidence_quote'][:200]}",
            "evidence_quote": r["evidence_quote"], "proposed_property": r.get("property", ""),
            "source": f"council:{r['role']}", "model": r["model"], "provider": r["provider"],
            "dynamic_status": "SUSPECTED",
        }
        for r in confirmed
    ]
    name = features.get("contract_name") or "this contract"
    n_found = sum(1 for r in specialist_results if r["found"])
    n_run = len(specialist_results)
    n_err = sum(1 for r in specialist_results if r["llm_error"])
    models = sorted({r["model"] for r in specialist_results})

    # FAIL-CLOSED verdict (critique #8): a scan where too many specialists
    # errored (missing key, rate-limited, provider down) must NOT read as a
    # clean GO — that's the worst failure mode for a security tool. Distinguish
    # "analyzed and clean" (GO) from "couldn't analyze" (INCONCLUSIVE).
    if n_run == 0 or (n_run > 0 and n_err / n_run >= 0.5):
        verdict = "INCONCLUSIVE"
        verdict_reason = f"{n_err}/{n_run} specialists failed to run — result is not trustworthy."
        raven_note = f"Raven couldn't complete the review of {name}: {n_err} of {n_run} specialists errored (likely a provider/key issue). This is NOT a clean bill of health — re-run once the engine is healthy."
    elif confirmed and _contract_risk(confirmed) >= RISK_TAU:
        verdict = "NO-GO"
        flagged = ", ".join(sorted({r["type"].replace('_', ' ') for r in confirmed}))
        verdict_reason = (f"{len(confirmed)} finding(s) cleared the evidence gate and their combined "
                          f"risk {_contract_risk(confirmed):.3f} is at or above the {RISK_TAU:.3f} bar: {flagged}.")
        raven_note = f"Raven flagged {name} on: {flagged}. Each finding quotes real code from the contract, and together they clear the confidence bar."
    elif confirmed:
        # Findings exist and are quote-backed, but pooled they do not reach the
        # bar. Under the old OR-gate this was an automatic NO-GO, and it is
        # where most false alarms came from. They are still reported — the
        # contract is not silently cleared — the verdict just is not a block.
        verdict = "GO"
        flagged = ", ".join(sorted({r["type"].replace('_', ' ') for r in confirmed}))
        verdict_reason = (f"{len(confirmed)} finding(s) quoted real code but their combined risk "
                          f"{_contract_risk(confirmed):.3f} is below the {RISK_TAU:.3f} bar: {flagged}. "
                          f"Reported for review, not blocking.")
        raven_note = (f"Raven noted {len(confirmed)} low-confidence observation(s) on {name} ({flagged}) "
                      f"that did not meet the bar to block. Worth a human read, not a stop-ship.")
    else:
        verdict = "GO"
        verdict_reason = f"All {n_run} specialists that ran found nothing quote-backed above the confidence bar."
        raven_note = f"Raven reviewed {name} across {n_run} relevant vulnerability classes and it came back clean — no finding cleared the evidence bar."

    summary = (f"Analysis of {name}: {n_run} model-diverse specialists "
               f"({', '.join(models)}) ran, {n_found} raised a finding, "
               f"{len(confirmed)} cleared the evidence gate. Verdict: {verdict}.")
    return {
        "final_verdict": verdict, "verdict_reason": verdict_reason,
        "vulnerabilities": vulnerabilities, "summary": summary,
        "raven_note": raven_note, "contract_name": features.get("contract_name", ""),
        "features_detected": {k: v for k, v in features.items() if v and k not in ("solidity_version", "contract_name")},
        "stats": {
            "models_run": len(models), "specialists_run": n_run,
            "specialists_found": n_found, "specialists_confirmed": len(confirmed),
            "specialists_errored": n_err,
            "contract_risk": round(_contract_risk(confirmed), 4),
            "risk_tau": RISK_TAU,
            "findings_suppressed": len(suppressed),
            "similar_in_db": len(similar_exploits) if similar_exploits else 0,
            "llm_error_detected": llm_error_detected, "tier": backend, "models_used": models,
        },
        "council_detail": specialist_results, "similar_exploits": similar_exploits or [], "mode": "council",
    }


def _schedule_groups(assignments: dict, backend: str) -> list[list[tuple]]:
    """Order specialist execution into groups that run concurrently.

    Hosted backends: one group — the providers are remote, models cost nothing
    to "switch", and full fan-out is fastest.

    Local Ollama: ONE GROUP PER MODEL, run in sequence. On a 4GB GPU only one
    of these models is resident at a time, so an interleaved fan-out pays a
    model evict+reload on nearly every call. Measured on the RTX 3050 laptop:
    warm same-model call 13-53s, switch to another model 72-229s. Grouping
    drops a contract from N reloads to exactly one per distinct model.

    This is a SCHEDULING change only — identical models, prompts, seeds and
    aggregation, so verdicts are unaffected. Order of specialist_results does
    change; _assemble_result is order-independent (it counts and filters, never
    positionally indexes), so that is safe.
    """
    items = [(role, provider, model) for role, (provider, model) in assignments.items()]
    if backend == "ollama":
        by_model: dict[str, list[tuple]] = {}
        for role, provider, model in items:
            by_model.setdefault(model, []).append((role, provider, model))
        return list(by_model.values())
    return [items]


async def run_council(code: str, similar_exploits: list | None = None, backend: str | None = None, seed: int | None = None, roles: list[str] | None = None) -> dict:
    """Council entry point. Returns the same top-level schema as
    run_full_analysis() (final_verdict, vulnerabilities, summary, raven_note,
    contract_name, features_detected, stats) so the eval harness and frontend
    work unchanged.

    backend: "ollama" (local tier) | "groq" (hosted tier). Defaults to
    LLM_BACKEND from the environment (read fresh per call).
    seed: optional sampling seed (threaded to each specialist) for the
    multi-seed eval protocol.
    similar_exploits: optional retrieved precedents (services/retrieval.py);
    surfaced in the output, not yet fed into specialist prompts."""
    backend = backend or os.getenv("LLM_BACKEND", "ollama").lower()
    assignments = _filter_assignments(specialist_assignments(backend), roles)
    features = preanalyze_code(code)

    # Bound concurrency so a hosted free tier isn't hit with 8 simultaneous
    # requests (the cause of burst 429s). Local Ollama serialises model loads
    # anyway, so a small cap costs nothing there. Configurable via env.
    max_conc = int(os.getenv("COUNCIL_MAX_CONCURRENCY", "3" if backend != "ollama" else "8"))
    sem = asyncio.Semaphore(max_conc)

    async def _bounded(role, provider, model):
        async with sem:
            return await _run_specialist(_SPECIALIST_BY_ROLE[role], provider, model, code, seed)

    specialist_results: list[dict] = []
    for group in _schedule_groups(assignments, backend):
        specialist_results.extend(await asyncio.gather(*[
            _bounded(role, provider, model) for role, provider, model in group
        ]))

    return _assemble_result(code, features, specialist_results, backend, similar_exploits)
