import httpx
import os
import json
import re
import asyncio

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "300"))
LLM_BACKEND = os.getenv("LLM_BACKEND", "ollama").lower()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

PREFERRED_MODELS = [
    "llama3.1:8b", "llama3.2:3b", "llama3.2:1b", "llama3:8b",
    "llama3:latest", "mistral:7b", "mistral:latest", "gemma2:9b",
    "gemma2:2b", "qwen2.5:7b", "phi3:mini", "codellama:7b",
]
_cached_model: str | None = None


async def _detect_model() -> str:
    global _cached_model
    if LLM_BACKEND == "groq":
        return f"groq:{GROQ_MODEL}"
    if _cached_model:
        return _cached_model
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{OLLAMA_URL}/api/tags", timeout=10)
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                for p in PREFERRED_MODELS:
                    if p in models:
                        _cached_model = p
                        print(f"[Raven] Using model: {p}")
                        return p
                if models:
                    _cached_model = models[0]
                    print(f"[Raven] Using: {models[0]}")
                    return models[0]
        except:
            pass
    return "llama3.2:3b"


async def check_ollama() -> dict:
    if LLM_BACKEND == "groq":
        return {
            "status": "connected" if GROQ_API_KEY else "disconnected",
            "models": [GROQ_MODEL],
            "active_model": f"groq:{GROQ_MODEL}",
            "message": None if GROQ_API_KEY else "GROQ_API_KEY not set",
        }
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{OLLAMA_URL}/api/tags", timeout=5)
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                active = await _detect_model()
                return {"status": "connected", "models": models, "active_model": active}
        except httpx.ConnectError:
            return {"status": "disconnected", "message": "Ollama not running"}
        except:
            pass
    return {"status": "error", "message": "Cannot reach Ollama"}


async def _query(prompt: str, timeout: int | None = None) -> str:
    if LLM_BACKEND == "groq":
        return await _query_groq(prompt, timeout)
    return await _query_ollama(prompt, timeout)


async def _query_ollama(prompt: str, timeout: int | None = None) -> str:
    model = await _detect_model()
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
                timeout=timeout or LLM_TIMEOUT,
            )
            if resp.status_code == 200:
                return resp.json().get("response", "")
            return f"[LLM Error {resp.status_code}]"
        except httpx.TimeoutException:
            return "[LLM timeout]"
        except httpx.ConnectError:
            return "[Ollama not running]"
        except Exception as e:
            return f"[Error: {e}]"


async def _query_groq(prompt: str, timeout: int | None = None) -> str:
    if not GROQ_API_KEY:
        return "[Groq API key not configured]"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                json={
                    "model": GROQ_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                },
                timeout=timeout or LLM_TIMEOUT,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            return f"[LLM Error {resp.status_code}: {resp.text[:200]}]"
        except httpx.TimeoutException:
            return "[LLM timeout]"
        except httpx.ConnectError:
            return "[Groq unreachable]"
        except Exception as e:
            return f"[Error: {e}]"


# ─── Code pre-analysis (deterministic, no LLM) ───
def preanalyze_code(code: str) -> dict:
    """Static regex analysis to detect what patterns ACTUALLY exist.
    This prevents the LLM from hallucinating vulns about patterns not in the code."""
    c = code
    cl = code.lower()
    lines = code.split("\n")

    features = {
        "has_external_call": bool(re.search(r'\.(call|send|transfer)\s*[\({]', c)),
        "has_call_value": bool(re.search(r'\.call\{value', c)),
        "has_delegatecall": "delegatecall" in c,
        "has_selfdestruct": "selfdestruct" in c,
        "has_tx_origin": "tx.origin" in c,
        "has_mapping": "mapping" in c,
        "has_balance_update": bool(re.search(r'balance[s]?\[.*\]\s*[-+]?=', c)),
        "has_withdraw": "withdraw" in cl,
        "has_onlyowner": "onlyowner" in cl or "onlyOwner" in c,
        "has_require": "require(" in c,
        "has_modifier": "modifier " in c,
        "has_payable": "payable" in c,
        "has_erc20": "transfer(" in c and ("balanceOf" in c or "IERC20" in c or "ERC20" in c),
        "has_unchecked_return": False,
        "has_loop": bool(re.search(r'\b(for|while)\s*\(', c)),
        "has_block_timestamp": "block.timestamp" in c,
        "has_reentrancy_pattern": False,
        "solidity_version": "",
        "contract_name": "",
    }

    # Check for unchecked return values on external calls
    for i, line in enumerate(lines):
        stripped = line.strip()
        if re.search(r'\w+\.transfer\(', stripped) and "IERC20" not in c and "interface" not in c:
            pass  # .transfer() is safe (reverts on failure)
        if re.search(r'\w+\.\w+\(', stripped) and "require" not in stripped and "bool" not in stripped:
            if "token." in stripped or "IERC20" in c:
                features["has_unchecked_return"] = True

    # Detect reentrancy: external call BEFORE state update
    call_line = None
    state_update_line = None
    for i, line in enumerate(lines):
        if re.search(r'\.(call|send)\s*[\({]', line) and call_line is None:
            call_line = i
        if re.search(r'balance[s]?\[.*\]\s*=\s*0', line) or re.search(r'balance[s]?\[.*\]\s*-=', line):
            if state_update_line is None:
                state_update_line = i

    if call_line is not None and state_update_line is not None:
        features["has_reentrancy_pattern"] = call_line < state_update_line

    # Extract version
    ver_match = re.search(r'pragma solidity\s*[\^>=<]*\s*([\d.]+)', c)
    if ver_match:
        features["solidity_version"] = ver_match.group(1)

    # Extract contract name
    name_match = re.search(r'contract\s+(\w+)', c)
    if name_match:
        features["contract_name"] = name_match.group(1)

    return features


# ─── The actual analysis pipeline ───
async def run_full_analysis(code: str, similar_exploits: list | None = None, disable_slither: bool = False) -> dict:
    """Run the complete ThirdEye analysis with Raven personality.

    disable_slither: eval-only toggle to isolate the single-LLM number as
    its own ablation-table baseline row (per docs/GAP_ANALYSIS.md's Phase 0
    plan). Defaults to False everywhere — the live deployed app and
    dataset_runner.py's normal full_pipeline mode are unaffected unless a
    caller explicitly opts in. When True, Slither simply isn't run; nothing
    in _parse_slither/_merge_vulns/_determine_verdict changes — they already
    handle an empty slither_vulns list as their normal "Slither unavailable"
    path, so no analysis logic needed to change to support this.
    """

    features = preanalyze_code(code)

    # Build context from similar past exploits
    context = ""
    if similar_exploits:
        context = "\n\nSIMILAR PAST EXPLOITS FOUND IN DATABASE:\n"
        for s in similar_exploits[:3]:
            context += f"- {s.get('verdict', '?')}: {s.get('vulns_summary', 'unknown')}\n"

    # Run all analyses concurrently
    summary_task = _raven_summary(code, features)
    vuln_task = _scan_vulnerabilities(code, features, context)
    if disable_slither:
        slither_task = asyncio.sleep(0, result={"status": "skipped", "message": "Slither disabled (single-LLM isolation, eval mode)"})
    else:
        from services.slither import run_slither
        slither_task = asyncio.to_thread(run_slither, code)

    summary, vuln_raw, slither_out = await asyncio.gather(
        summary_task, vuln_task, slither_task
    )

    # Diagnostic only — does not affect verdict/merge/filter logic at all,
    # purely exposes a fact eval/run_baselines.py needs to tell "genuinely
    # clean contract" apart from "the LLM call errored/rate-limited and
    # silently produced an empty result" (see its retry-on-429 logic).
    llm_error_detected = any(
        marker in s for s in (summary, vuln_raw)
        for marker in ("[LLM Error", "[LLM timeout]", "not running]", "unreachable]", "[Error:")
    )

    # Parse LLM vulns
    llm_vulns = _parse_vuln_json(vuln_raw)

    # Post-process: remove false positives based on pre-analysis
    llm_vulns = _filter_false_positives(llm_vulns, features)

    # Parse slither
    slither_vulns = _parse_slither(slither_out)

    # Combine and deduplicate
    all_vulns = _merge_vulns(llm_vulns, slither_vulns)

    # Determine verdict
    verdict = _determine_verdict(all_vulns)

    # Build raven commentary
    raven_note = _raven_verdict_note(verdict, all_vulns, features)

    return {
        "final_verdict": verdict,
        "vulnerabilities": all_vulns,
        "summary": summary,
        "raven_note": raven_note,
        "contract_name": features["contract_name"],
        "features_detected": {k: v for k, v in features.items() if v and k not in ("solidity_version", "contract_name")},
        "stats": {
            "models_run": 1,
            "raw_llm_findings": len(llm_vulns),
            "slither_findings": len(slither_vulns),
            "final_findings": len(all_vulns),
            "similar_in_db": len(similar_exploits) if similar_exploits else 0,
            "llm_error_detected": llm_error_detected,
        },
        "slither": slither_out,
    }


async def _raven_summary(code: str, features: dict) -> str:
    name = features["contract_name"] or "this contract"
    prompt = f"""You are Raven, a witty smart contract security analyst with a sharp eye.
Explain what this Solidity contract does in 3-4 sentences for a non-technical person.
Be specific about THIS contract. Mention what {name} actually does.
Keep it conversational but informative. No bullet points.

```solidity
{code}
```

Raven's explanation:"""
    return await _query(prompt)


async def _scan_vulnerabilities(code: str, features: dict, context: str) -> str:
    """Single comprehensive vulnerability scan with feature-aware prompting."""

    # Build a targeted prompt based on what's actually in the code
    checks = []
    if features["has_external_call"] or features["has_call_value"]:
        checks.append("- CHECK for reentrancy: does an external call (.call, .send) happen BEFORE a state variable update?")
    if features["has_selfdestruct"]:
        checks.append("- CHECK selfdestruct: is it protected by access control (onlyOwner, require(msg.sender == owner))?")
    if features["has_tx_origin"]:
        checks.append("- CHECK tx.origin: is tx.origin used for authentication instead of msg.sender?")
    if features["has_delegatecall"]:
        checks.append("- CHECK delegatecall: is user input passed to delegatecall unsafely?")
    if features["has_unchecked_return"]:
        checks.append("- CHECK unchecked returns: are return values from token transfers or external calls checked?")
    if not features["has_onlyowner"] and (features["has_withdraw"] or features["has_selfdestruct"] or features["has_payable"]):
        checks.append("- CHECK access control: are sensitive functions (withdraw, kill, selfdestruct, mint) protected?")
    if features["has_loop"]:
        checks.append("- CHECK for DoS: could a loop run out of gas with large arrays?")
    if features["has_block_timestamp"]:
        checks.append("- CHECK timestamp dependence: is block.timestamp used for critical logic?")

    if not checks:
        checks.append("- This contract has no obvious dangerous patterns. Look carefully for subtle logic issues.")

    checks_str = "\n".join(checks)

    prompt = f"""You are an expert Solidity security auditor. Analyze this contract.

WHAT TO CHECK:
{checks_str}

CRITICAL RULES TO AVOID FALSE POSITIVES:
1. Solidity >=0.8.0 has BUILT-IN overflow protection. Do NOT flag integer overflow.
2. require() is a SAFETY CHECK, not a vulnerability.
3. If .call() happens AFTER balance update (balance = 0 then .call), that is SAFE (CEI pattern).
4. Only flag reentrancy if .call()/.send() happens BEFORE the balance/state update.
5. Do NOT invent vulnerabilities. If the code is safe, return [].
6. view/pure functions CANNOT be exploited.
7. Simple contracts (counters, storage) are usually safe.
{context}

Return ONLY a JSON array. Nothing else. No markdown. No explanation.
Each vulnerability: {{"type": "name", "line": N, "severity": "critical|high|medium|low", "confidence": 0.0-1.0, "description": "specific explanation"}}
If safe: []

```solidity
{code}
```

JSON:"""
    return await _query(prompt, timeout=240)


def _parse_vuln_json(raw: str) -> list[dict]:
    """Robustly extract JSON array from LLM response."""
    try:
        clean = raw.strip()
        # Find JSON array
        start = clean.find("[")
        end = clean.rfind("]") + 1
        if start != -1 and end > start:
            parsed = json.loads(clean[start:end])
            return [v for v in parsed if isinstance(v, dict) and v.get("type")]
    except:
        pass

    # Fallback: keyword extraction from prose
    vulns = []
    raw_l = raw.lower()
    keywords = {
        "reentrancy": ("critical", "Potential reentrancy pattern detected"),
        "selfdestruct": ("high", "Unprotected selfdestruct detected"),
        "access control": ("high", "Missing access control on sensitive function"),
        "unchecked": ("medium", "Unchecked return value from external call"),
        "tx.origin": ("medium", "tx.origin used instead of msg.sender"),
        "delegatecall": ("critical", "Unsafe delegatecall usage"),
        "front-run": ("medium", "Potential front-running opportunity"),
        "denial of service": ("medium", "Potential DoS vector"),
    }
    for kw, (sev, desc) in keywords.items():
        if kw in raw_l and f"no {kw}" not in raw_l and f"not {kw}" not in raw_l and f"safe from {kw}" not in raw_l:
            vulns.append({"type": kw, "line": None, "severity": sev, "confidence": 0.6, "description": desc, "source": "llm-prose"})
    return vulns


def _filter_false_positives(vulns: list[dict], features: dict) -> list[dict]:
    """Remove hallucinated vulnerabilities that contradict the actual code."""
    filtered = []
    for v in vulns:
        vtype = v.get("type", "").lower()

        # No external calls → no reentrancy possible
        if "reentrancy" in vtype or "reentran" in vtype:
            if not features["has_external_call"] and not features["has_call_value"]:
                continue  # HALLUCINATION: no external calls exist
            if features["has_external_call"] and not features["has_reentrancy_pattern"]:
                # External calls exist but state updates happen before → CEI is fine
                # Lower confidence significantly
                v["confidence"] = min(v.get("confidence", 0.5), 0.35)
                v["description"] = (v.get("description", "") + " [Note: CEI pattern may be followed - verify manually]")

        # No delegatecall → no delegatecall injection
        if "delegatecall" in vtype and not features["has_delegatecall"]:
            continue

        # No selfdestruct → no selfdestruct vuln
        if "selfdestruct" in vtype and not features["has_selfdestruct"]:
            continue

        # No tx.origin → no tx.origin vuln
        if "tx.origin" in vtype and not features["has_tx_origin"]:
            continue

        # Solidity 0.8+ → no overflow
        if "overflow" in vtype or "underflow" in vtype:
            ver = features.get("solidity_version", "")
            if ver and ver >= "0.8":
                continue

        filtered.append(v)
    return filtered


def _parse_slither(out: dict) -> list[dict]:
    if out.get("status") != "completed":
        return []
    try:
        data = json.loads(out.get("output", "{}"))
        detectors = data.get("results", {}).get("detectors", [])
        vulns = []
        sev_map = {"High": "critical", "Medium": "high", "Low": "medium", "Informational": "low"}
        for d in detectors:
            vulns.append({
                "type": d.get("check", "unknown"),
                "line": None,
                "severity": sev_map.get(d.get("impact", ""), "medium"),
                "confidence": {"High": 0.9, "Medium": 0.7, "Low": 0.5}.get(d.get("confidence", ""), 0.6),
                "description": d.get("description", "")[:300],
                "source": "slither",
            })
        return vulns
    except:
        return []


def _merge_vulns(llm_vulns: list, slither_vulns: list) -> list[dict]:
    """Merge LLM + slither findings, boost confidence on overlap."""
    merged = {}

    for v in llm_vulns:
        key = _norm_key(v)
        if key not in merged:
            merged[key] = {**v, "sources": ["llm"], "final_confidence": v.get("confidence", 0.5)}
        else:
            merged[key]["sources"].append("llm")
            merged[key]["final_confidence"] = min(0.95, merged[key]["final_confidence"] + 0.1)

    for v in slither_vulns:
        key = _norm_key(v)
        if key in merged:
            merged[key]["sources"].append("slither")
            merged[key]["final_confidence"] = min(0.98, merged[key]["final_confidence"] + 0.2)
            merged[key]["verified_by_slither"] = True
        else:
            merged[key] = {**v, "sources": ["slither"], "final_confidence": v.get("confidence", 0.7), "verified_by_slither": True}

    result = list(merged.values())
    result.sort(key=lambda x: x.get("final_confidence", 0), reverse=True)

    # Only keep findings above threshold
    return [v for v in result if v.get("final_confidence", 0) > 0.25]


def _norm_key(v: dict) -> str:
    t = v.get("type", "unknown").lower().replace(" ", "-").replace("_", "-")
    aliases = {"re-entrancy": "reentrancy", "reentrant": "reentrancy", "access-control": "access-control",
               "missing-access-control": "access-control", "unchecked-call": "unchecked-return"}
    t = aliases.get(t, t)
    return f"{t}_{v.get('line', '?')}"


def _determine_verdict(vulns: list) -> str:
    if not vulns:
        return "GO"
    for v in vulns:
        sev = v.get("severity", "").lower()
        conf = v.get("final_confidence", 0)
        if sev == "critical" and conf > 0.4:
            return "NO-GO"
        if sev == "high" and conf > 0.5:
            return "NO-GO"
    if any(v.get("severity") in ("critical", "high", "medium") for v in vulns):
        return "NO-GO"
    return "GO"


def _raven_verdict_note(verdict: str, vulns: list, features: dict) -> str:
    """Raven's personality note about the verdict."""
    name = features.get("contract_name", "this contract")
    if verdict == "GO":
        return f"Looks clean to me. {name} follows good practices — no red flags in my scan. Still, I'm an AI, not a replacement for a full manual audit. Ship it, but stay sharp."
    else:
        critical = [v for v in vulns if v.get("severity") in ("critical", "high")]
        if critical:
            types = ", ".join(set(v.get("type", "?") for v in critical[:3]))
            return f"Hold up — {name} has some serious issues. I'm flagging {types}. Do NOT deploy this without fixing these first. Seriously."
        else:
            return f"{name} has some concerns worth looking at. Nothing catastrophic, but I wouldn't ship it as-is. Review the findings below."


def get_raven_greeting() -> str:
    return "Hey, I'm Raven — ThirdEye's security analyst. Paste me a Solidity contract and I'll tear it apart looking for vulnerabilities. I run three parallel analysis models and a consensus engine. Let's see what you've got."
