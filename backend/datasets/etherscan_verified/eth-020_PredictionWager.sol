/**
 *Submitted for verification at Etherscan.io on 2026-02-15
*/

// https://cipherchan.com/ Autoresolver
// SPDX-License-Identifier: MIT               
  pragma solidity ^0.8.24;

  interface IERC20 {
    function balanceOf(address a) external view returns (uint256);
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns
  (bool);
  }

  contract PredictionWager {
    IERC20 public immutable token;
    address public immutable resolver;
    address public immutable treasury;
    address public immutable owner;

    uint256 public constant MIN_WAGER = 1e18;
    uint256 public constant HOUSE_FEE_BPS = 500;

    enum Status { Open, Resolved, Cancelled }

    struct Wager {
      bytes32 predictionId;
      address creator;
      uint256 deadline;
      Status status;
      uint8 winSide;
      uint256 totalUp;
      uint256 totalDown;
      uint256 bettorCount;
    }

    struct Bet {
      uint8 side;
      uint256 amount;
      bool claimed;
    }

    mapping(bytes32 => Wager) public wagers;
    mapping(bytes32 => mapping(address => Bet)) public bets;
    mapping(bytes32 => address[]) internal _bettors;

    event WagerCreated(bytes32 indexed wagerId, bytes32 indexed predictionId, address
  indexed creator, uint256 amount, uint8 side, uint256 deadline);
    event WagerJoined(bytes32 indexed wagerId, address indexed bettor, uint8 side,
  uint256 amount);
    event WagerResolved(bytes32 indexed wagerId, uint8 winSide, uint256 totalPool,
  uint256 houseFee);
    event PayoutClaimed(bytes32 indexed wagerId, address indexed bettor, uint256
  payout);
    event WagerCancelled(bytes32 indexed wagerId, address indexed cancelledBy);

    constructor(address _token, address _resolver, address _treasury) {
      require(_token != address(0), "token=0");
      require(_resolver != address(0), "resolver=0");
      require(_treasury != address(0), "treasury=0");
      token = IERC20(_token);
      resolver = _resolver;
      treasury = _treasury;
      owner = msg.sender;
    }

    function createWager(bytes32 wagerId, bytes32 predictionId, uint256 amount, uint8
  side, uint256 deadline) external {
      require(wagers[wagerId].creator == address(0), "wager exists");
      require(amount >= MIN_WAGER, "below min");
      require(side == 1 || side == 2, "side must be 1 or 2");
      require(deadline > block.timestamp, "deadline passed");
      require(token.transferFrom(msg.sender, address(this), amount), "transfer failed");
      Wager storage w = wagers[wagerId];
      w.predictionId = predictionId;
      w.creator = msg.sender;
      w.deadline = deadline;
      w.status = Status.Open;
      w.bettorCount = 1;
      if (side == 1) { w.totalUp = amount; } else { w.totalDown = amount; }
      bets[wagerId][msg.sender] = Bet({ side: side, amount: amount, claimed: false });
      _bettors[wagerId].push(msg.sender);
      emit WagerCreated(wagerId, predictionId, msg.sender, amount, side, deadline);
    }

    function joinWager(bytes32 wagerId, uint8 side, uint256 amount) external {
      Wager storage w = wagers[wagerId];
      require(w.creator != address(0), "wager not found");
      require(w.status == Status.Open, "wager not open");
      require(block.timestamp <= w.deadline, "deadline passed");
      require(side == 1 || side == 2, "side must be 1 or 2");
      require(amount >= MIN_WAGER, "below min");
      require(token.transferFrom(msg.sender, address(this), amount), "transfer failed");
      Bet storage b = bets[wagerId][msg.sender];
      if (b.amount == 0) {
        b.side = side;
        b.amount = amount;
        _bettors[wagerId].push(msg.sender);
        w.bettorCount++;
      } else {
        require(b.side == side, "cannot switch sides");
        b.amount += amount;
      }
      if (side == 1) { w.totalUp += amount; } else { w.totalDown += amount; }
      emit WagerJoined(wagerId, msg.sender, side, amount);
    }

    function resolveWager(bytes32 wagerId, uint8 winSide) external {
      require(msg.sender == resolver, "not resolver");
      Wager storage w = wagers[wagerId];
      require(w.creator != address(0), "wager not found");
      require(w.status == Status.Open, "not open");
      require(block.timestamp > w.deadline, "deadline not passed");
      require(winSide == 1 || winSide == 2, "winSide must be 1 or 2");
      w.status = Status.Resolved;
      w.winSide = winSide;
      uint256 totalPool = w.totalUp + w.totalDown;
      uint256 houseFee = (totalPool * HOUSE_FEE_BPS) / 10000;
      if (houseFee > 0) { require(token.transfer(treasury, houseFee), "fee transfer failed"); }
      emit WagerResolved(wagerId, winSide, totalPool, houseFee);
    }

    function claimPayout(bytes32 wagerId) external {
      Wager storage w = wagers[wagerId];
      require(w.status == Status.Resolved, "not resolved");
      Bet storage b = bets[wagerId][msg.sender];
      require(b.amount > 0, "no bet");
      require(!b.claimed, "already claimed");
      require(b.side == w.winSide, "not winner");
      b.claimed = true;
      uint256 totalPool = w.totalUp + w.totalDown;
      uint256 houseFee = (totalPool * HOUSE_FEE_BPS) / 10000;
      uint256 distributable = totalPool - houseFee;
      uint256 winnerPool = w.winSide == 1 ? w.totalUp : w.totalDown;
      uint256 payout = (b.amount * distributable) / winnerPool;
      require(token.transfer(msg.sender, payout), "payout transfer failed");
      emit PayoutClaimed(wagerId, msg.sender, payout);
    }

    function cancelWager(bytes32 wagerId) external {
      Wager storage w = wagers[wagerId];
      require(w.creator != address(0), "wager not found");
      require(w.status == Status.Open, "not open");
      if (msg.sender == owner) {
      } else if (msg.sender == w.creator) {
        require(w.totalUp == 0 || w.totalDown == 0, "both sides have bets");
      } else { revert("not authorized"); }
      w.status = Status.Cancelled;
      address[] storage addrs = _bettors[wagerId];
      for (uint256 i = 0; i < addrs.length; i++) {
        Bet storage b = bets[wagerId][addrs[i]];
        if (b.amount > 0 && !b.claimed) { b.claimed = true; token.transfer(addrs[i],
  b.amount); }
      }
      emit WagerCancelled(wagerId, msg.sender);
    }

    function getWager(bytes32 wagerId) external view returns (bytes32 predictionId,
  address creator, uint256 deadline, Status status, uint8 winSide, uint256 totalUp,
  uint256 totalDown, uint256 bettorCount) {
      Wager storage w = wagers[wagerId];
      return (w.predictionId, w.creator, w.deadline, w.status, w.winSide, w.totalUp,
  w.totalDown, w.bettorCount);
    }

    function getBettorCount(bytes32 wagerId) external view returns (uint256) { return
  wagers[wagerId].bettorCount; }

    function getStake(bytes32 wagerId, address bettor) external view returns (uint8
  side, uint256 amount, bool claimed) {
      Bet storage b = bets[wagerId][bettor];
      return (b.side, b.amount, b.claimed);
    }

    function getBettors(bytes32 wagerId) external view returns (address[] memory) {
  return _bettors[wagerId]; }
  }