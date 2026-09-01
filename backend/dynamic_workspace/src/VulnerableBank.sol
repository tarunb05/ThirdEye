// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

// A deliberately reentrancy-vulnerable bank — the canonical
// external-call-before-state-update pattern. Used by the dynamic-confirmation
// layer's reference PoC to prove the exploit harness actually produces a
// witness (the attacker withdraws more than it deposited).
contract VulnerableBank {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw() external {
        uint256 bal = balances[msg.sender];
        require(bal > 0, "no balance");
        // VULNERABLE: external call BEFORE the state update — the callee can
        // re-enter withdraw() while its recorded balance is still non-zero,
        // and each re-entry pays out the full `bal` again until the bank is
        // empty. The `= 0` only runs once, on unwind (canonical DAO pattern;
        // drains cleanly under 0.8 checked arithmetic, no underflow).
        (bool ok, ) = msg.sender.call{value: bal}("");
        require(ok, "transfer failed");
        balances[msg.sender] = 0;
    }

    receive() external payable {}
}
