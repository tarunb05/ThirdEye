"""
DASP-10 taxonomy bridge — maps each dataset/source's own native category
vocabulary into the DASP-10 buckets so per-category metrics can (optionally)
be compared across sources. This does NOT replace the native taxonomy
already stored on EvalItem/Prediction — see eval/metrics.py's
`normalize_categories` flag, off by default, which adds normalized buckets
alongside the native ones rather than overwriting them.

Plain dicts on purpose — this is a lookup table, not a system.

DASP10 categories: reentrancy, access_control, arithmetic,
unchecked_low_level_calls, denial_of_service, bad_randomness,
front_running, time_manipulation, short_addresses, other.

UNMAPPED is a separate, explicit bucket from "other": "other" is one of
DASP-10's own 10 categories (a real, in-scope technical bug that just
doesn't have its own slot — SmartBugs-Curated itself has an "other" folder).
UNMAPPED means "this isn't a DASP-10-shaped bug at all" — most commonly
Web3Bugs' S-category business-logic bugs (missing state updates, broken
business-flow assumptions, price-oracle manipulation) and out-of-scope
O-codes. That split is itself a finding, not a gap to paper over: it's
the same observation the ThirdEye plan's own thesis rests on — most real bugs
are logic bugs a pattern taxonomy like DASP-10 was never built to hold.
"""

from __future__ import annotations

DASP10 = {
    "reentrancy", "access_control", "arithmetic", "unchecked_low_level_calls",
    "denial_of_service", "bad_randomness", "front_running", "time_manipulation",
    "short_addresses", "other",
}

UNMAPPED = "unmapped"

# --- Web3Bugs (docs/standard.md) -> DASP-10 -----------------------------
# O-codes are explicitly out-of-scope by the dataset's own definition, not
# technical bug categories — always unmapped.
# S-codes are mostly business-logic/semantic bugs DASP-10 has no slot for;
# only the handful with a genuinely clean conceptual match are mapped.
WEB3BUGS_TO_DASP10 = {
    "O1": UNMAPPED, "O2": UNMAPPED, "O3": UNMAPPED, "O4": UNMAPPED,
    "O5": UNMAPPED, "O6": UNMAPPED, "O7": UNMAPPED,

    "L1": "reentrancy",                    # Reentrancy
    "L2": "arithmetic",                    # Rounding / precision loss
    "L3": "other",                         # Uninitialized variables
    "L4": "denial_of_service",             # Gas-limit bugs
    "L5": "other",                         # Storage collision / proxy confusion
    "L6": "unchecked_low_level_calls",     # Arbitrary external function call
    "L7": "arithmetic",                    # Integer overflow/underflow
    "L8": "unchecked_low_level_calls",     # Revert from low-level calls/libs
    "L9": "other",                         # Memory/storage write confusion
    "LA": "other",                         # Cryptographic issues
    "LB": "access_control",                # tx.origin

    "S1-1": UNMAPPED,                      # AMM price oracle manipulation (no DASP-10 slot)
    "S1-2": "front_running",               # Sandwich attack — genuinely a front-running variant
    "S1-3": UNMAPPED,                      # Non-AMM price oracle manipulation
    "S2-1": UNMAPPED,                      # Arbitrary/unvalidated ID (doc itself flags S2-1 vs S5 ambiguity; kept separate from access_control rather than forced)
    "S2-2": UNMAPPED,                      # Shared resource without locks
    "S2-3": UNMAPPED,                      # ID uniqueness violation
    "S3-1": UNMAPPED,                      # Missing state update — logic bug, not a pattern
    "S3-2": UNMAPPED,                      # Incorrect state update
    "S4-1": UNMAPPED,                      # Business-flow atomicity violation
    "S5-1": "access_control",              # Privilege escalation / access control (category's own name)
    "S5-2": "access_control",
    "S5-3": "access_control",
    "S6-1": "arithmetic",                  # Erroneous accounting — calculation bugs
    "S6-2": "arithmetic",                  # (imperfect fit — "unexpected return value" is as much a logic bug as arithmetic; kept with the rest of S6 rather than over-engineering a one-off bucket)
    "S6-3": "arithmetic",
    "S6-4": "arithmetic",
    "SE-1": UNMAPPED,                      # Broken business model via unexpected operations — semantic bugs, by definition not DASP-10-shaped
    "SE-2": UNMAPPED,
    "SE-3": UNMAPPED,
    "SE-4": UNMAPPED,
    "SC": UNMAPPED,                        # Catch-all the dataset's own authors call "difficult to categorize"
}

# --- Etherscan-50's ad-hoc vuln_types -> DASP-10 ------------------------
ETHERSCAN50_TO_DASP10 = {
    "tx_origin_auth": "access_control",
    "unprotected_withdraw": "access_control",
}

# --- ThirdEye's own observed vocabulary -> DASP-10 ----------------------
# Covers both _parse_vuln_json's keyword-fallback dict keys (services/llm.py)
# and the free-text "type" strings the LLM tends to emit given the
# _scan_vulnerabilities prompt's own hints, plus the Slither detector IDs
# most likely to fire on these datasets — both flow into the same merged
# "type" field in ThirdEye's actual output, so they share one table.
# Exact-match first; normalize() falls back to substring matching against
# this same table's keys for free-text variants this dict doesn't list
# verbatim (e.g. "missing access control on withdraw").
THIRDEYE_TO_DASP10 = {
    # LLM keyword-fallback dict (services/llm.py _parse_vuln_json)
    "reentrancy": "reentrancy",
    "re-entrancy": "reentrancy",
    "reentrant": "reentrancy",
    "selfdestruct": "access_control",      # unprotected selfdestruct = access control failure
    "access control": "access_control",
    "access-control": "access_control",
    "access_control": "access_control",    # services/council.py specialist type field (snake_case, already a DASP10 name)
    "missing access control": "access_control",
    "missing-access-control": "access_control",
    "business logic": "other",             # services/council.py BusinessLogic specialist — no dedicated DASP10 slot, "other" is the honest fit
    "business-logic": "other",
    "business_logic": "other",
    "unchecked": "unchecked_low_level_calls",
    "unchecked return": "unchecked_low_level_calls",
    "unchecked-return": "unchecked_low_level_calls",
    "tx.origin": "access_control",
    "tx-origin": "access_control",
    "delegatecall": "unchecked_low_level_calls",  # delegatecall is itself a low-level call construct
    "front-run": "front_running",
    "front running": "front_running",
    "frontrunning": "front_running",
    "denial of service": "denial_of_service",
    "dos": "denial_of_service",

    # Free-text variants the LLM plausibly emits (prompt-hinted vocabulary)
    "overflow": "arithmetic",
    "underflow": "arithmetic",
    "integer overflow": "arithmetic",
    "integer underflow": "arithmetic",
    "timestamp": "time_manipulation",
    "timestamp dependence": "time_manipulation",
    "block.timestamp": "time_manipulation",
    "randomness": "bad_randomness",
    "bad randomness": "bad_randomness",
    "weak randomness": "bad_randomness",
    "short address": "short_addresses",

    # Slither detector IDs (subset likely to fire on these datasets — full
    # list is 90+; anything not here falls through to UNMAPPED and gets
    # logged, not guessed at)
    "reentrancy-eth": "reentrancy",
    "reentrancy-no-eth": "reentrancy",
    "reentrancy-benign": "reentrancy",
    "reentrancy-events": "reentrancy",
    "reentrancy-unlimited-gas": "reentrancy",
    # ("tx-origin" Slither detector is already covered by the "tx-origin" key above)
    "suicidal": "access_control",
    "unprotected-upgrade": "access_control",
    "arbitrary-send-eth": "access_control",
    "arbitrary-send-erc20": "access_control",
    "arbitrary-send-erc20-permit": "access_control",
    "unchecked-transfer": "unchecked_low_level_calls",
    "unchecked-lowlevel": "unchecked_low_level_calls",
    "unchecked-send": "unchecked_low_level_calls",
    "low-level-calls": "unchecked_low_level_calls",
    "calls-loop": "denial_of_service",
    "costly-loop": "denial_of_service",
    "locked-ether": "denial_of_service",
    "weak-prng": "bad_randomness",
    "divide-before-multiply": "arithmetic",
    "integer-overflow": "arithmetic",
}

_TAXONOMY_TABLES = {
    "web3bugs": WEB3BUGS_TO_DASP10,
    "etherscan50_auto": ETHERSCAN50_TO_DASP10,
    "thirdeye": THIRDEYE_TO_DASP10,
    "thirdeye_llm": THIRDEYE_TO_DASP10,
    "thirdeye_slither": THIRDEYE_TO_DASP10,
    "llm": THIRDEYE_TO_DASP10,
    "slither": THIRDEYE_TO_DASP10,
}

_unmapped_log: list[tuple[str, str]] = []


def normalize(taxonomy: str, category: str) -> str:
    """Map a (taxonomy, native category) pair into a DASP-10 bucket, or
    UNMAPPED. Logs every miss (taxonomy + raw category) for later reporting
    — see get_unmapped_log()."""
    cat_key = category.strip()

    if taxonomy == "dasp10":
        # SmartBugs-Curated passthrough: validate, don't blindly trust.
        if cat_key.lower() in DASP10:
            return cat_key.lower()
        _unmapped_log.append((taxonomy, category))
        return UNMAPPED

    table = _TAXONOMY_TABLES.get(taxonomy)
    if table is None:
        _unmapped_log.append((taxonomy, category))
        return UNMAPPED

    # Web3Bugs codes are case-sensitive (e.g. "S6-4"); ThirdEye/Etherscan-50
    # free text is matched case-insensitively.
    direct = table.get(cat_key) if taxonomy == "web3bugs" else table.get(cat_key.lower())
    if direct is not None:
        result = direct
    else:
        result = None
        if taxonomy != "web3bugs":
            cat_lower = cat_key.lower()
            for keyword, bucket in table.items():
                if keyword in cat_lower:
                    result = bucket
                    break
        if result is None:
            result = UNMAPPED

    # Log every UNMAPPED result, whether it's a deliberate table entry (e.g.
    # Web3Bugs' S3-1) or a code this table doesn't recognize at all — both
    # are "unmapped" from the caller's point of view and the task said log
    # every one, not just the coverage gaps.
    if result == UNMAPPED:
        _unmapped_log.append((taxonomy, category))
    return result


def get_unmapped_log() -> list[tuple[str, str]]:
    return list(_unmapped_log)


def reset_unmapped_log() -> None:
    _unmapped_log.clear()


def summarize_unmapped() -> dict[str, list[str]]:
    """Group the unmapped log by taxonomy for a compact report."""
    out: dict[str, list[str]] = {}
    for taxonomy, category in _unmapped_log:
        out.setdefault(taxonomy, []).append(category)
    return out
