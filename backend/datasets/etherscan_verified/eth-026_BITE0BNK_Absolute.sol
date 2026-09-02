/**
 *Submitted for verification at Etherscan.io on 2026-02-15
*/

// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Προσθήκη του Interface ID για να το αναγνωρίζει το Etherscan ως NFT
interface IERC165 {
    function supportsInterface(bytes4 interfaceId) external view returns (bool);
}

contract BITE0BNK_Absolute is IERC165 {
    string public name = "BITE0BANK Absolute Bite";
    string public symbol = "BITE1BNK";
    
    address public owner;
    address public constant ALICEBANK = 0x5c98728bF49c4681eeC04C099d8F99f7C3946a3C;
    uint256 public constant ABSOLUTE_ID = 1;
    address private _tokenOwner;
    string private _uri = "https://yellow-eldest-bedbug-113.mypinata.cloud/ipfs/bafkreibn3pduouoiml5m2gx34ake7feadcdqx2uldcjxu6bdj7b5i7tr7y";

    event Transfer(address indexed from, address indexed to, uint256 indexed tokenId);
    event MitosisCycle(address indexed from, address indexed to, uint256 yield);

    constructor() {
        owner = msg.sender;
        _tokenOwner = msg.sender;
        emit Transfer(address(0), msg.sender, ABSOLUTE_ID);
    }

    // Απαραίτητο για να "πει" στο Etherscan ότι ΕΙΝΑΙ NFT
    function supportsInterface(bytes4 interfaceId) public pure override returns (bool) {
        return interfaceId == 0x80ac58cd || interfaceId == 0x5b5e139f || interfaceId == 0x01ffc9a7;
    }

    function ownerOf(uint256 tokenId) public view returns (address) {
        require(tokenId == ABSOLUTE_ID, "Non-existent ID");
        return _tokenOwner;
    }

    function tokenURI() public view returns (string memory) {
    return _uri;
    }

    function triggerMitosis(address _nextOwner) public {
        require(msg.sender == ALICEBANK, "Absolute Singularity: Use the Teller.");
        address previousOwner = _tokenOwner;
        _tokenOwner = _nextOwner;
        emit Transfer(previousOwner, _nextOwner, ABSOLUTE_ID);
        emit MitosisCycle(previousOwner, _nextOwner, 191);
    }
}