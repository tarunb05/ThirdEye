"""
Curated sample contracts for the "try it" / demo section — pre-verified
examples a user can one-click load and scan, without pasting their own code.
Mix of deliberately vulnerable and deliberately safe contracts across the main
classes, each with the expected verdict so the demo is self-explanatory.

These are small, self-contained, and intentionally illustrative (not the
benchmark datasets — those are for evaluation). Kept inline (tracked in git)
so they ship with the app regardless of the gitignored datasets.
"""

SAMPLES = [
    {
        "id": "reentrancy-bank",
        "name": "Vulnerable Bank",
        "category": "Reentrancy",
        "expected": "NO-GO",
        "blurb": "Classic external-call-before-state-update. The withdraw pays out before zeroing the balance — re-entrant drain.",
        "code": """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract VulnerableBank {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw() external {
        uint256 bal = balances[msg.sender];
        require(bal > 0, "no balance");
        (bool ok, ) = msg.sender.call{value: bal}(""); // external call FIRST
        require(ok, "transfer failed");
        balances[msg.sender] = 0;                       // state update AFTER
    }

    receive() external payable {}
}
""",
    },
    {
        "id": "access-control-drain",
        "name": "Unprotected Treasury",
        "category": "Access Control",
        "expected": "NO-GO",
        "blurb": "withdrawAll() has no owner/role check — anyone can drain the contract.",
        "code": """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Treasury {
    address public owner;
    constructor() { owner = msg.sender; }
    function deposit() external payable {}

    // BUG: no onlyOwner / access check — anyone can call this.
    function withdrawAll() external {
        payable(msg.sender).transfer(address(this).balance);
    }
}
""",
    },
    {
        "id": "tx-origin-auth",
        "name": "tx.origin Auth",
        "category": "Access Control",
        "expected": "NO-GO",
        "blurb": "Authorization via tx.origin is phishable — a malicious intermediary contract bypasses it.",
        "code": """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Wallet {
    address public owner;
    constructor() { owner = msg.sender; }

    function transfer(address payable to, uint256 amount) external {
        // BUG: tx.origin instead of msg.sender — phishable authorization.
        require(tx.origin == owner, "not owner");
        to.transfer(amount);
    }
    receive() external payable {}
}
""",
    },
    {
        "id": "safe-vault",
        "name": "Safe Vault (CEI + Ownable)",
        "category": "Safe",
        "expected": "GO",
        "blurb": "Checks-Effects-Interactions, owner-gated admin, checked arithmetic. Should pass clean.",
        "code": """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract SafeVault {
    address public immutable owner;
    mapping(address => uint256) public balances;
    constructor() { owner = msg.sender; }

    modifier onlyOwner() { require(msg.sender == owner, "not owner"); _; }

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "insufficient");
        balances[msg.sender] -= amount;            // effects BEFORE interaction
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "transfer failed");
    }

    function sweepDust(address payable to) external onlyOwner {
        to.transfer(address(this).balance);
    }
    receive() external payable {}
}
""",
    },
    {
        "id": "bad-randomness-lottery",
        "name": "Predictable Lottery",
        "category": "Bad Randomness",
        "expected": "NO-GO",
        "blurb": "Winner picked from block.timestamp/prevrandao — miner/validator-influenceable, not real randomness.",
        "code": """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Lottery {
    address[] public players;
    function enter() external payable { require(msg.value == 1 ether); players.push(msg.sender); }

    function pickWinner() external {
        // BUG: predictable on-chain "randomness".
        uint256 idx = uint256(keccak256(abi.encodePacked(block.timestamp, block.prevrandao))) % players.length;
        payable(players[idx]).transfer(address(this).balance);
        delete players;
    }
}
""",
    },
]


# The demo set: three GO, three NO-GO.
#
# Ten samples was too many to walk a panel through in the time available, and a
# balanced six makes the point faster: the tool is shown as likely to raise a
# false alarm as to catch a bug, which is the actual result. Each half spans
# three different patterns rather than three flavours of the same one --
# reentrancy / access control / bad randomness against guarded-withdraw /
# checks-effects-interactions / pull-payment.
#
# `safe-guarded-withdraw` is the one that must stay: it is the deliberate
# false-positive probe, raw .call{value:} with the state zeroed first AND a
# guard, so a pattern matcher flags it and a reader of the logic should not.
#
# The contracts dropped from the demo are NOT deleted -- they are still defined
# above and in samples_extra, still exercised by the test suite, and restoring
# one is a single line here.
DEMO_SET = (
    "safe-guarded-withdraw",
    "safe-vault",
    "safe-pull-payment",
    "reentrancy-bank",
    "access-control-drain",
    "bad-randomness-lottery",
)


def list_samples() -> list[dict]:
    """Public list (includes code so the UI can load it directly).

    Ordered SAFE-first. The original set was 4 NO-GO to 1 GO, so a demo run
    top-to-bottom only ever showed the tool finding bugs -- which proves very
    little, since flagging everything achieves it. Leading with contracts that
    SHOULD come back clean puts the harder claim first.
    """
    from services.samples_extra import EXTRA_SAMPLES

    all_samples = SAMPLES + EXTRA_SAMPLES
    ids = [s["id"] for s in all_samples]
    assert len(ids) == len(set(ids)), f"duplicate sample id: {ids}"

    by_id = {s["id"]: s for s in all_samples}
    missing = [i for i in DEMO_SET if i not in by_id]
    assert not missing, f"DEMO_SET names a sample that does not exist: {missing}"
    chosen = [by_id[i] for i in DEMO_SET]

    n_go = sum(1 for s in chosen if s["expected"] == "GO")
    assert n_go == 3 and len(chosen) - n_go == 3, (
        f"demo set must stay 3 GO / 3 NO-GO, got {n_go} GO of {len(chosen)}"
    )
    return sorted(chosen, key=lambda s: (s["expected"] != "GO", s["name"]))
