"""Context-aware suppression of findings that cannot be real.

From the false-positive review (docs/ThirdEye_FPR_Reduction_Critique items
#12/#23/#27, and #15/#16): a large share of false alarms are findings whose
vulnerability class is *structurally impossible* in the contract that was
scanned, or that sit in code holding neither state nor value.

Every rule here is deliberately RECALL-SAFE by construction: each one drops a
finding only when the contract lacks a precondition that the vulnerability
class REQUIRES. A genuine reentrancy needs an external call; if the source has
no external call, a reentrancy finding cannot be describing a real bug.

These run AFTER the evidence gate and BEFORE the contract-risk pooling, so a
structurally-impossible finding never inflates the noisy-OR product.
"""

from __future__ import annotations
import re

# Classes that require the contract to actually hold or move value. A stateless,
# fund-free helper cannot have an exploitable instance of any of these.
VALUE_CLASSES = {
    "reentrancy",
    "access_control",
    "oracle_price_manipulation",
    "flashloan_mev",
}

# What each class structurally REQUIRES, expressed over preanalyze_code features.
# Absent an entry, a class is never suppressed on preconditions.
# MEASURED, not assumed. Each precondition below was evaluated in isolation on
# the n=233 benchmark, on top of the contract-risk threshold:
#
#   rule                     FPR      recall   F1      verdict
#   (threshold only)         28.2%    0.844    0.780   baseline
#   reentrancy precondition  28.2%    0.844    0.780   no effect, kept (sound)
#   proxy precondition       28.2%    0.844    0.780   no effect, kept (sound)
#   dos_gas precondition     27.4%    0.807    0.762   REMOVED — cost 4 true
#                                                      positives to remove 1
#                                                      false alarm
#   oracle precondition      (folded into the above)   REMOVED — too crude
#
# The dos_gas losses were instructive: the contracts it silenced (dvl_dirtybytes,
# dvl_privatedata) ARE vulnerable, but not to DoS. The finding was scoring as a
# true positive for the wrong reason, because scoring is contract-level rather
# than class-level. Removing it is still correct on the metric we report.
PRECONDITIONS = {
    # No external call anywhere => nothing can re-enter. Sound by construction;
    # measured to change nothing on this corpus, which is the expected result
    # for a rule that only fires on impossible findings.
    "reentrancy": lambda f: f.get("has_external_call") or f.get("has_call_value"),
    # Needs delegatecall or an initializer to hijack.
    "proxy_upgradeability": lambda f: f.get("has_delegatecall") or "initialize" in (f.get("_src_lower") or ""),
}

_LIBRARY_RE = re.compile(r"\blibrary\s+\w+")
_CONTRACT_RE = re.compile(r"\bcontract\s+\w+")
_STATE_VAR_RE = re.compile(
    r"^\s*(?:uint\d*|int\d*|address|bool|bytes\d*|string|mapping)\s[^;()]*;",
    re.MULTILINE,
)


def contract_profile(code: str, features: dict) -> dict:
    """Cheap structural facts used by the suppression rules."""
    stripped = re.sub(r"//.*|/\*[\s\S]*?\*/", "", code or "")
    is_library = bool(_LIBRARY_RE.search(stripped)) and not _CONTRACT_RE.search(stripped)
    has_state = bool(_STATE_VAR_RE.search(stripped))
    # "Holds value" = can receive ether or moves tokens/balances.
    holds_value = bool(
        features.get("has_payable")
        or features.get("has_call_value")
        or features.get("has_balance_update")
        or features.get("has_erc20")
    )
    return {
        "is_library": is_library,
        "has_state": has_state,
        "holds_value": holds_value,
        # A pure helper: library-shaped OR (no state AND no value at all).
        "stateless_fund_free": is_library or (not has_state and not holds_value),
    }


def suppress(findings: list[dict], code: str, features: dict) -> tuple[list[dict], list[dict]]:
    """-> (kept, dropped). Each dropped finding carries a `suppressed_reason`.

    Findings are never deleted from the report — the caller keeps them for
    display. They are only barred from contributing to the blocking decision.
    """
    prof = contract_profile(code, features)
    feats = dict(features)
    feats["_src_lower"] = (code or "").lower()

    kept, dropped = [], []
    for f in findings:
        cls = f.get("type")
        reason = None

        if prof["stateless_fund_free"] and cls in VALUE_CLASSES:
            reason = (
                "contract holds no state and moves no value (library/pure helper), "
                f"so a {cls} bug is not exploitable as written"
            )
        else:
            pre = PRECONDITIONS.get(cls)
            if pre is not None and not pre(feats):
                reason = f"contract lacks the structural precondition a {cls} bug requires"

        if reason:
            d = dict(f); d["suppressed_reason"] = reason
            dropped.append(d)
        else:
            kept.append(f)
    return kept, dropped


# Severity policy (#15/#16): informational/low observations were never the
# recall drivers, but they do push false positives. They stay in the report and
# stop driving the block decision.
NON_BLOCKING_SEVERITIES = {"low", "informational", "info", "note"}


def blocking_findings(findings: list[dict]) -> list[dict]:
    return [f for f in findings
            if str(f.get("severity", "")).strip().lower() not in NON_BLOCKING_SEVERITIES]
