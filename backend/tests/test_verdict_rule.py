"""The verdict rule: pooling, threshold, and fail-closed behaviour.

These exist because the project's history is a list of silent failures — a rule
that measured one way offline and behaved another way live, a half-dead council
recording clean passes. Each test below pins one of those behaviours so it
cannot regress unnoticed.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.council import _contract_risk, RISK_TAU, _aggregate, CONF_MIN


def f(conf, **kw):
    return {"found": True, "confidence": conf, "type": kw.get("type", "reentrancy"),
            "evidence_quote": kw.get("quote", "x"), "severity": kw.get("severity", "high")}


class TestContractRisk:
    def test_no_findings_is_zero_risk(self):
        assert _contract_risk([]) == 0.0

    def test_single_finding_risk_equals_its_confidence(self):
        assert abs(_contract_risk([f(0.7)]) - 0.7) < 1e-9

    def test_findings_pool_rather_than_max(self):
        # Two 0.8s must exceed either alone: 1-(0.2*0.2)=0.96. This is the whole
        # difference between the threshold rule and the old OR-gate.
        assert abs(_contract_risk([f(0.8), f(0.8)]) - 0.96) < 1e-9

    def test_risk_is_monotonic_in_finding_count(self):
        assert _contract_risk([f(0.5)]) < _contract_risk([f(0.5), f(0.5)])

    def test_risk_never_exceeds_one(self):
        assert _contract_risk([f(0.99)] * 20) <= 1.0

    def test_missing_confidence_treated_as_certain(self):
        # Matches eval/weighted_aggregation.py::risk. If these two ever disagree
        # the paper stops describing the product — the original defect.
        assert _contract_risk([{"confidence": None}]) == 1.0

    def test_confidence_is_clamped(self):
        assert _contract_risk([f(5.0)]) == 1.0
        assert _contract_risk([f(-1.0)]) == 0.0


class TestThresholdBehaviour:
    def test_lone_medium_finding_does_not_block(self):
        # The exact false alarm the fix targets: one 0.6 finding on audited code.
        assert _contract_risk([f(0.6)]) < RISK_TAU

    def test_lone_high_finding_below_tau_does_not_block(self):
        assert _contract_risk([f(0.9)]) < RISK_TAU

    def test_two_strong_findings_block(self):
        assert _contract_risk([f(0.8), f(0.8)]) >= RISK_TAU

    def test_or_gate_is_this_rule_at_tau_zero(self):
        # Guards the claim made in the paper and in council.py's comments.
        assert _contract_risk([f(0.01)]) > 0.0

    def test_tau_is_the_tuned_value(self):
        assert abs(RISK_TAU - 0.925) < 1e-9, "tau changed — re-run eval/weighted_aggregation.py"


class TestEvidenceGate:
    def test_finding_must_quote_real_source(self):
        code = "contract A { function f() public {} }"
        kept = _aggregate([f(0.9, quote="this text is not in the contract")], code)
        assert kept == []

    def test_quoted_finding_survives(self):
        code = "contract A { function f() public { msg.sender.call{value: 1}(''); } }"
        kept = _aggregate([f(0.9, quote="msg.sender.call{value: 1}('')")], code)
        assert len(kept) == 1

    def test_low_confidence_dropped_before_pooling(self):
        code = "contract A {}"
        assert _aggregate([f(CONF_MIN - 0.1, quote="contract A {}")], code) == []

    def test_not_found_is_dropped(self):
        code = "contract A {}"
        r = f(0.9, quote="contract A {}"); r["found"] = False
        assert _aggregate([r], code) == []
