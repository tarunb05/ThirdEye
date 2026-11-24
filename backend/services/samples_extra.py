"""Additional demo contracts, chosen so a live demo can FAIL informatively.

The original five samples were 4 NO-GO to 1 GO. A demo that only ever shows
the tool catching bugs demonstrates nothing a grep could not fake: the hard
claim is that it leaves SAFE code alone, and the interesting claim is that it
sometimes does not. These add:

  * three more safe contracts, so the GO path is the majority of the set and
    a panel can see the tool decline to flag correct code
  * one contract that is safe but LOOKS dangerous (raw call behind a
    reentrancy guard + CEI), which is the honest false-positive risk case
  * two more vulnerability classes the original set missed (unchecked
    external call return, integer-truncation in a cast)

Every contract here is small enough to scan live on a 4 GB laptop GPU, where
the council trio costs roughly 20-36 s per round of calls.
"""

EXTRA_SAMPLES = [
    {
        "id": "safe-ownable-escrow",
        "name": "Ownable Escrow",
        "category": "Safe / access control",
        "expected": "GO",
        "blurb": (
            "Correct access control via a constructor-set owner and a modifier, "
            "with checks-effects-interactions on release. Nothing to flag — this "
            "is the case where a noisy auditor costs you real engineering time."
        ),
        "code": """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract OwnableEscrow {
    address public immutable owner;
    mapping(address => uint256) public deposits;

    error NotOwner();

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        if (msg.sender != owner) revert NotOwner();
        _;
    }

    function deposit() external payable {
        deposits[msg.sender] += msg.value;
    }

    function release(address payable to, uint256 amount) external onlyOwner {
        require(deposits[to] >= amount, "insufficient");
        deposits[to] -= amount;              // effect before interaction
        (bool ok, ) = to.call{value: amount}("");
        require(ok, "transfer failed");
    }
}
""",
    },
    {
        "id": "safe-guarded-withdraw",
        "name": "Guarded Withdraw (looks risky, is not)",
        "category": "Safe / false-positive probe",
        "expected": "GO",
        "blurb": (
            "A raw .call{value:} sits right there in the source, but state is "
            "zeroed first AND a reentrancy guard wraps the function. Pattern "
            "matchers flag this; a reader of the actual logic should not. This "
            "is the sample most likely to expose a false positive — which is "
            "exactly why it is in the set."
        ),
        "code": """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract GuardedWithdraw {
    mapping(address => uint256) public balances;
    uint256 private _lock = 1;

    modifier nonReentrant() {
        require(_lock == 1, "reentrant");
        _lock = 2;
        _;
        _lock = 1;
    }

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw() external nonReentrant {
        uint256 bal = balances[msg.sender];
        require(bal > 0, "nothing to withdraw");
        balances[msg.sender] = 0;            // effect FIRST
        (bool ok, ) = msg.sender.call{value: bal}("");
        require(ok, "transfer failed");
    }
}
""",
    },
    {
        "id": "safe-pull-payment",
        "name": "Pull-Payment Splitter",
        "category": "Safe / business logic",
        "expected": "GO",
        "blurb": (
            "Pull-over-push payouts with fixed shares. No external call in the "
            "accounting path at all, so there is nothing for a reentrancy or "
            "DoS specialist to legitimately raise."
        ),
        "code": """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract PullPaymentSplitter {
    mapping(address => uint256) public owed;
    uint256 public totalOwed;

    function credit(address who) external payable {
        require(who != address(0), "zero address");
        owed[who] += msg.value;
        totalOwed += msg.value;
    }

    function claim() external {
        uint256 amount = owed[msg.sender];
        require(amount > 0, "nothing owed");
        owed[msg.sender] = 0;
        totalOwed -= amount;
        payable(msg.sender).transfer(amount);
    }
}
""",
    },
    {
        "id": "unchecked-call-return",
        "name": "Unchecked Call Return",
        "category": "Unchecked external call",
        "expected": "NO-GO",
        "blurb": (
            "The low-level call's success flag is discarded, so a failed "
            "payout still marks the debt as settled. Funds are silently lost "
            "and the contract's accounting is wrong afterwards."
        ),
        "code": """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract Payout {
    mapping(address => uint256) public owed;

    function fund(address who) external payable {
        owed[who] += msg.value;
    }

    function settle(address who) external {
        uint256 amount = owed[who];
        require(amount > 0, "nothing owed");
        owed[who] = 0;
        who.call{value: amount}("");   // return value never checked
    }
}
""",
    },
    {
        "id": "unsafe-downcast",
        "name": "Truncating Downcast",
        "category": "Arithmetic",
        "expected": "NO-GO",
        "blurb": (
            "Solidity 0.8 checks overflow on arithmetic but NOT on explicit "
            "casts. Depositing more than type(uint64).max wei truncates the "
            "recorded balance, so the ledger silently disagrees with the ether "
            "actually held."
        ),
        "code": """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract Ledger {
    mapping(address => uint64) public balance;

    function deposit() external payable {
        // Explicit cast is NOT overflow-checked by 0.8.x.
        balance[msg.sender] += uint64(msg.value);
    }

    function withdraw(uint64 amount) external {
        require(balance[msg.sender] >= amount, "insufficient");
        balance[msg.sender] -= amount;
        payable(msg.sender).transfer(amount);
    }
}
""",
    },
]
