// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface ITransferValidator721 {
    function validateTransfer(
        address caller,
        address from,
        address to,
        uint256 tokenId
    ) external view;
}

contract AlwaysAllowValidator is ITransferValidator721 {

    function validateTransfer(
        address, /* caller */
        address, /* from */
        address, /* to */
        uint256  /* tokenId */
    ) external pure override {
        // Intentionally empty — always allow
    }
}