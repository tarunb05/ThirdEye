// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract Counter {
    uint256 public number;
    address public owner;

    event NumberChanged(uint256 newNumber);

    constructor(uint256 initialNumber) {
        owner = msg.sender;
        number = initialNumber;
        emit NumberChanged(initialNumber);
    }

    function setNumber(uint256 newNumber) external {
        require(msg.sender == owner, "not owner");
        number = newNumber;
        emit NumberChanged(newNumber);
    }

    function increment() external {
        number += 1;
        emit NumberChanged(number);
    }
}