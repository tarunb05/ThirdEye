"""Evaluation-integrity invariants.

Each test corresponds to a defect that once produced plausible-but-wrong
numbers (docs/DECISION_LOG.md Phases 0-1). They are cheap; the failures they
prevent cost multi-day reruns.
"""
import os, sys, json, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.suppression import contract_profile, suppress, blocking_findings
from services.llm import preanalyze_code


class TestNestedSampling:
    """Defect 6: `items[:N]` clustered by filename, so a 'sample' was 263
    consecutive OpenZeppelin files. Sampling must be random AND nested."""

    @staticmethod
    def sample(items, n, seed="0:b:t"):
        r = random.Random(seed); it = list(items); r.shuffle(it); return it[:n]

    def test_smaller_sample_is_subset_of_larger(self):
        items = list(range(200))
        assert set(self.sample(items, 10)) <= set(self.sample(items, 25))
        assert set(self.sample(items, 25)) <= set(self.sample(items, 50))

    def test_sampling_is_deterministic(self):
        items = list(range(200))
        assert self.sample(items, 30) == self.sample(items, 30)

    def test_sample_is_not_the_first_n(self):
        items = list(range(200))
        assert self.sample(items, 20) != items[:20], "sampling collapsed back to first-N"

    def test_different_seeds_differ(self):
        items = list(range(200))
        assert self.sample(items, 20, "0:a:a") != self.sample(items, 20, "9:z:z")


class TestSuppressionIsRecallSafe:
    """Suppression may only drop findings the contract structurally cannot
    have. Anything broader costs recall (measured: the dos_gas rule did)."""

    LIB = "library L { function add(uint a, uint b) internal pure returns (uint) { return a + b; } }"
    VAULT = """contract V {
        mapping(address => uint) balances;
        function withdraw() public payable {
            (bool ok,) = msg.sender.call{value: balances[msg.sender]}("");
            require(ok);
            balances[msg.sender] = 0;
        }
    }"""

    def test_pure_library_is_detected_as_stateless(self):
        p = contract_profile(self.LIB, preanalyze_code(self.LIB))
        assert p["is_library"] and p["stateless_fund_free"]

    def test_vault_is_not_treated_as_stateless(self):
        p = contract_profile(self.VAULT, preanalyze_code(self.VAULT))
        assert not p["stateless_fund_free"], "a fund-holding contract must never be suppressed"

    def test_value_class_finding_suppressed_on_pure_library(self):
        kept, dropped = suppress([{"type": "reentrancy", "confidence": 0.9}],
                                 self.LIB, preanalyze_code(self.LIB))
        assert kept == [] and len(dropped) == 1
        assert "suppressed_reason" in dropped[0]

    def test_real_finding_on_a_vault_survives(self):
        kept, dropped = suppress([{"type": "reentrancy", "confidence": 0.9}],
                                 self.VAULT, preanalyze_code(self.VAULT))
        assert len(kept) == 1 and dropped == []

    def test_suppression_never_invents_findings(self):
        kept, dropped = suppress([], self.VAULT, preanalyze_code(self.VAULT))
        assert kept == [] and dropped == []

    def test_dropped_findings_are_returned_not_deleted(self):
        """Suppressed findings still reach the report; they only stop blocking."""
        f = [{"type": "reentrancy", "confidence": 0.9}]
        kept, dropped = suppress(f, self.LIB, preanalyze_code(self.LIB))
        assert len(kept) + len(dropped) == len(f)


class TestSeveritySplit:
    def test_low_severity_is_non_blocking(self):
        out = blocking_findings([{"severity": "low"}, {"severity": "high"}])
        assert len(out) == 1 and out[0]["severity"] == "high"

    def test_unknown_severity_still_blocks(self):
        # Fail-closed: an unlabelled finding must not be silently downgraded.
        assert len(blocking_findings([{"severity": ""}])) == 1


class TestCheckpointContract:
    """Defect 2/3: what may be treated as a terminal result."""

    def test_go_with_errored_specialist_is_not_terminal(self):
        row = {"verdict": "GO", "specialists_errored": 1}
        terminal = row["verdict"] == "NO-GO" or (row["verdict"] == "GO" and not row.get("specialists_errored"))
        assert not terminal, "a clean GO from a partial council must never be trusted"

    def test_nogo_with_errored_specialist_is_terminal(self):
        row = {"verdict": "NO-GO", "specialists_errored": 1}
        terminal = row["verdict"] == "NO-GO" or (row["verdict"] == "GO" and not row.get("specialists_errored"))
        assert terminal, "a missing specialist cannot have invented the finding that was raised"

    def test_inconclusive_is_never_terminal(self):
        row = {"verdict": "INCONCLUSIVE", "specialists_errored": 0}
        terminal = row["verdict"] == "NO-GO" or (row["verdict"] == "GO" and not row.get("specialists_errored"))
        assert not terminal
