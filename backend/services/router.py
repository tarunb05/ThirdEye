"""
Specialist router — the architecture change: instead of firing all 8 council
specialists at every contract (expensive, and 8 eager models over-flag safe
code -> everything becomes NO-GO), we PRE-SELECT which specialists are relevant
using cheap signals first:

  1. Static analysis (Slither) when available — high-confidence signal for the
     pattern-based classes it can actually detect.
  2. Lightweight code features (preanalyze_code + a few regexes) — always
     available, and the ONLY signal for the semantic/logic classes.

Design nuance that matters: static tools CANNOT see logic bugs (business logic,
oracle/price manipulation, flash-loan/MEV) — that's the whole reason this
project exists. So a router that only ran specialists Slither hinted at would
structurally miss the project's headline bug class. Therefore:
  - Pattern classes (reentrancy, access_control, arithmetic, proxy) are gated
    on static/feature signals — skip them when there's clearly no surface.
  - Logic classes (business_logic, oracle, flashloan_mev, dos_gas) are gated on
    cheap content heuristics, and business_logic is ALWAYS run (the catch-all).
  - If a contract has essentially no dangerous surface (an audited library with
    no external calls / privileged fns / loops), few or zero specialists run ->
    it can reach GO cheaply and precisely, which is the point.

Returns the selected roles plus a per-role trace (why included/skipped), so the
routing decision is auditable, not a black box.
"""

from __future__ import annotations

import re

# All 8 council roles (must match services/council.py SPECIALISTS).
ALL_ROLES = [
    "reentrancy", "access_control", "arithmetic", "business_logic",
    "oracle_price_manipulation", "flashloan_mev", "dos_gas", "proxy_upgradeability",
]

# Content heuristics for the classes with no static-tool signal.
_ORACLE_RE = re.compile(r"getReserves|\.balanceOf\(\s*(?:pair|pool|address\(this\))|latestAnswer|getPrice|price0|price1|slot0|consult\(", re.I)
_FLASHLOAN_RE = re.compile(r"flashLoan|flashloan|getPastVotes|balanceOf\([^)]*\)\s*[><]=?|snapshot|delegatee?s?\b", re.I)
_DOS_RE = re.compile(r"for\s*\(|while\s*\(|\.push\(|\.transfer\(", re.I)
_PROXY_RE = re.compile(r"delegatecall|initializer|__init|upgradeTo|implementation|proxy", re.I)
_ARITH_RE = re.compile(r"unchecked\s*\{|[-+*]\s*=|SafeMath|\*\s*\w+\s*/", re.I)

# Slither detector-name substrings -> which specialist they justify.
_SLITHER_TO_ROLE = {
    "reentrancy": "reentrancy",
    "arbitrary-send": "access_control",
    "suicidal": "access_control",
    "unprotected": "access_control",
    "tx-origin": "access_control",
    "access": "access_control",
    "integer": "arithmetic",
    "overflow": "arithmetic",
    "divide": "arithmetic",
    "delegatecall": "proxy_upgradeability",
    "uninitialized": "proxy_upgradeability",
    "controlled-delegatecall": "proxy_upgradeability",
    "calls-loop": "dos_gas",
    "costly-loop": "dos_gas",
    "timestamp": "business_logic",
    "weak-prng": "business_logic",
}


def _roles_from_slither(slither_findings: list[dict]) -> set[str]:
    roles: set[str] = set()
    for f in slither_findings or []:
        check = str(f.get("check", "") or f.get("type", "")).lower()
        for key, role in _SLITHER_TO_ROLE.items():
            if key in check:
                roles.add(role)
    return roles


def select_specialists(code: str, features: dict, slither_findings: list[dict] | None = None) -> dict:
    """Decide which specialists to run. Returns
    {roles: [...], trace: {role: reason}, static_used: bool}."""
    f = features or {}
    static_roles = _roles_from_slither(slither_findings)
    static_used = slither_findings is not None

    trace: dict[str, str] = {}
    selected: set[str] = set()

    def pick(role: str, cond: bool, why: str):
        if role in static_roles:
            selected.add(role); trace[role] = "slither: detector hit"
        elif cond:
            selected.add(role); trace[role] = why
        else:
            trace[role] = "skipped: no relevant surface"

    has_ext = f.get("has_external_call") or f.get("has_call_value")
    privileged = f.get("has_withdraw") or f.get("has_selfdestruct") or f.get("has_payable") or "mint" in code.lower() or "owner" in code.lower()

    pick("reentrancy", bool(has_ext), "external call / value transfer present")
    pick("access_control", bool(privileged), "privileged / fund-moving surface present")
    # Arithmetic: pre-0.8 (no built-in overflow checks) or explicit unchecked/mul-div.
    ver = str(f.get("solidity_version", ""))
    pre08 = bool(re.match(r"0\.[0-7]\b", ver)) or ver == ""
    pick("arithmetic", pre08 or bool(_ARITH_RE.search(code)), "pre-0.8 or unchecked/scaled arithmetic")
    pick("oracle_price_manipulation", bool(_ORACLE_RE.search(code)), "price/oracle/AMM read pattern")
    pick("flashloan_mev", bool(_FLASHLOAN_RE.search(code)), "flash-loan / balance-based governance pattern")
    pick("dos_gas", bool(_DOS_RE.search(code)), "loop / push-payment pattern")
    pick("proxy_upgradeability", bool(f.get("has_delegatecall")) or bool(_PROXY_RE.search(code)), "delegatecall / proxy / initializer pattern")

    # business_logic is the catch-all — static tools can't gate it, so it
    # always runs (unless the contract is trivially tiny).
    if len(code.strip()) > 60:
        selected.add("business_logic"); trace["business_logic"] = "always-on catch-all (no static signal for logic bugs)"
    else:
        trace["business_logic"] = "skipped: contract too small"

    # Floor: if nothing selected but there IS a contract, run business_logic so
    # we never return a verdict on zero analysis.
    roles = [r for r in ALL_ROLES if r in selected]
    if not roles and len(code.strip()) > 60:
        roles = ["business_logic"]
        trace["business_logic"] = "floor: minimal analysis"

    return {"roles": roles, "trace": trace, "static_used": static_used}
