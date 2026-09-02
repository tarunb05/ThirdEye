// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

interface ILeAnimeOldEncoding {
    function getCharTraitsUInt8(
        uint256 tokenId
    ) external view returns (uint8[8] memory);
}

contract LeAnime_Encoding_Converter {
    address public constant oldEncodingAddress =
        0x03121836Fd30E13bb4E25F69A0d1DEeD2778748b;

    function convert(uint256 tokenId) external view returns (string memory) {
        uint8[8] memory traits = ILeAnimeOldEncoding(oldEncodingAddress)
            .getCharTraitsUInt8(tokenId);
        return _convertFromTraits(tokenId, traits);
    }

    function convertFromTraits(
        uint256 tokenId,
        uint8[8] memory traits
    ) external pure returns (string memory) {
        return _convertFromTraits(tokenId, traits);
    }

    function _convertFromTraits(
        uint256 tokenId,
        uint8[8] memory traits
    ) internal pure returns (string memory) {
        uint256 multiplier = tokenId <= 1573 ? 20 : 1;
        uint256 adjustedScore = uint256(traits[0]) * multiplier;
        uint256 heroLevel = _levelMinusOne(_heroLevel(adjustedScore));

        uint256 runesLevel = 0;
        uint256 extraLevel = 0;
        if (multiplier != 1) {
            uint256 levelScore = 20;
            runesLevel = _levelMinusOne(_runesLevel(levelScore, traits[6]));
            extraLevel = _levelMinusOne(_extraLevel(levelScore, traits[7]));
        }

        bytes memory out = abi.encodePacked(
            _toString(tokenId),
            "S",
            _toString(adjustedScore),
            "H"
        );
        out = _appendHex(out, heroLevel);
        out = _appendHex(out, traits[1]);
        out = _appendHex(out, traits[2]);
        out = _appendHex(out, traits[3]);
        out = _appendHex(out, traits[4]);
        out = _appendHex(out, traits[5]);
        out = _appendHex(out, traits[6]);
        out = _appendHex(out, runesLevel);
        out = _appendHex(out, traits[7]);
        out = _appendHex(out, extraLevel);
        out = abi.encodePacked(out, "G00");
        return string(out);
    }

    function _appendHex(
        bytes memory out,
        uint256 value
    ) internal pure returns (bytes memory) {
        return abi.encodePacked(out, _toHex2(value));
    }

    function _heroLevel(uint256 score) internal pure returns (uint256) {
        uint256[15] memory thresholds = [
            uint256(1),
            30,
            70,
            170,
            390,
            800,
            1500,
            2000,
            2500,
            2900,
            6000,
            10000,
            15000,
            20000,
            25000
        ];
        if (score >= thresholds[thresholds.length - 1]) {
            return thresholds.length;
        }
        for (uint256 i = 0; i < thresholds.length; i++) {
            if (thresholds[i] > score) {
                return i;
            }
        }
        return thresholds.length;
    }

    function _runesLevel(
        uint256 score,
        uint256 runes
    ) internal pure returns (uint256) {
        if (runes == 0) {
            return _levelFromList(score, _list1(1));
        }
        if (runes == 1) {
            return _levelFromList(score, _list10(1, 3, 6, 11, 21, 39, 71, 131, 242, 445));
        }
        if (runes == 2) {
            return _levelFromList(score, _list10(1, 3, 5, 10, 17, 30, 52, 92, 162, 285));
        }
        if (runes == 3) {
            return _levelFromList(score, _list10(1, 3, 6, 10, 18, 33, 59, 105, 189, 338));
        }
        if (runes == 4) {
            return _levelFromList(score, _list10(1, 3, 6, 12, 22, 41, 77, 143, 266, 496));
        }
        if (runes == 5) {
            return _levelFromList(score, _list10(1, 3, 5, 9, 15, 26, 45, 77, 132, 227));
        }
        if (runes == 6) {
            return _levelFromList(score, _list10(1, 3, 5, 8, 14, 23, 39, 67, 112, 190));
        }
        if (runes == 7) {
            return _levelFromList(score, _list1(1));
        }
        if (runes == 8) {
            return _levelFromList(score, _list1(1));
        }
        if (runes == 9) {
            return _levelFromList(score, _list10(1, 3, 4, 7, 11, 18, 29, 47, 77, 124));
        }
        if (runes == 10) {
            return _levelFromList(score, _list10(1, 2, 4, 6, 10, 16, 25, 39, 61, 97));
        }
        if (runes == 11) {
            return _levelFromList(score, _list1(1));
        }
        if (runes == 12) {
            return _levelFromList(score, _list1(1));
        }
        if (runes == 13) {
            return _levelFromList(score, _list1(1));
        }
        if (runes == 14) {
            return _levelFromList(score, _list1(1));
        }
        if (runes == 15) {
            return _levelFromList(score, _list1(1));
        }
        return 0;
    }

    function _extraLevel(
        uint256 score,
        uint256 extra
    ) internal pure returns (uint256) {
        if (extra == 0) {
            return _levelFromList(score, _list1(1));
        }
        if (extra == 1) {
            return _levelFromList(score, _list8(1, 4, 7, 14, 27, 53, 103, 201));
        }
        if (extra == 2) {
            return _levelFromList(score, _list5(1, 5, 12, 28, 64));
        }
        if (extra == 3) {
            return _levelFromList(score, _list5(1, 6, 16, 39, 98));
        }
        if (extra == 4) {
            return _levelFromList(score, _list8(1, 4, 9, 18, 36, 74, 152, 312));
        }
        if (extra == 5) {
            return _levelFromList(score, _list10(1, 4, 7, 13, 25, 47, 89, 170, 323, 613));
        }
        if (extra == 6) {
            return _levelFromList(score, _list8(1, 4, 8, 17, 35, 72, 147, 300));
        }
        if (extra == 7) {
            return _levelFromList(score, _list9(1, 4, 8, 15, 30, 58, 115, 227, 447));
        }
        if (extra == 8) {
            return _levelFromList(score, _list1(1));
        }
        if (extra == 9) {
            return _levelFromList(score, _list1(1));
        }
        if (extra == 10) {
            return _levelFromList(score, _list1(1));
        }
        if (extra == 11) {
            return _levelFromList(score, _list1(1));
        }
        if (extra == 12) {
            return _levelFromList(score, _list1(1));
        }
        if (extra == 13) {
            return _levelFromList(score, _list1(1));
        }
        if (extra == 14) {
            return _levelFromList(score, _list1(1));
        }
        if (extra == 15) {
            return _levelFromList(score, _list1(1));
        }
        if (extra == 16) {
            return _levelFromList(score, _list1(1));
        }
        if (extra == 17) {
            return _levelFromList(score, _list1(1));
        }
        if (extra == 18) {
            return _levelFromList(score, _list1(1));
        }
        if (extra == 19) {
            return _levelFromList(score, _list1(1));
        }
        return 0;
    }

    function _levelFromList(
        uint256 score,
        uint256[] memory thresholds
    ) internal pure returns (uint256) {
        if (score >= thresholds[thresholds.length - 1]) {
            return thresholds.length;
        }
        for (uint256 i = 0; i < thresholds.length; i++) {
            if (thresholds[i] > score) {
                return i;
            }
        }
        return thresholds.length;
    }

    function _levelMinusOne(uint256 level) internal pure returns (uint256) {
        if (level == 0) {
            return 0;
        }
        return level - 1;
    }

    function _list1(uint256 a) internal pure returns (uint256[] memory) {
        uint256[] memory list = new uint256[](1);
        list[0] = a;
        return list;
    }

    function _list5(
        uint256 a,
        uint256 b,
        uint256 c,
        uint256 d,
        uint256 e
    ) internal pure returns (uint256[] memory) {
        uint256[] memory list = new uint256[](5);
        list[0] = a;
        list[1] = b;
        list[2] = c;
        list[3] = d;
        list[4] = e;
        return list;
    }

    function _list8(
        uint256 a,
        uint256 b,
        uint256 c,
        uint256 d,
        uint256 e,
        uint256 f,
        uint256 g,
        uint256 h
    ) internal pure returns (uint256[] memory) {
        uint256[] memory list = new uint256[](8);
        list[0] = a;
        list[1] = b;
        list[2] = c;
        list[3] = d;
        list[4] = e;
        list[5] = f;
        list[6] = g;
        list[7] = h;
        return list;
    }

    function _list9(
        uint256 a,
        uint256 b,
        uint256 c,
        uint256 d,
        uint256 e,
        uint256 f,
        uint256 g,
        uint256 h,
        uint256 i
    ) internal pure returns (uint256[] memory) {
        uint256[] memory list = new uint256[](9);
        list[0] = a;
        list[1] = b;
        list[2] = c;
        list[3] = d;
        list[4] = e;
        list[5] = f;
        list[6] = g;
        list[7] = h;
        list[8] = i;
        return list;
    }

    function _list10(
        uint256 a,
        uint256 b,
        uint256 c,
        uint256 d,
        uint256 e,
        uint256 f,
        uint256 g,
        uint256 h,
        uint256 i,
        uint256 j
    ) internal pure returns (uint256[] memory) {
        uint256[] memory list = new uint256[](10);
        list[0] = a;
        list[1] = b;
        list[2] = c;
        list[3] = d;
        list[4] = e;
        list[5] = f;
        list[6] = g;
        list[7] = h;
        list[8] = i;
        list[9] = j;
        return list;
    }

    function _toHex2(uint256 value) internal pure returns (string memory) {
        uint8 v = uint8(value);
        bytes memory out = new bytes(2);
        out[0] = _hexChar(v >> 4);
        out[1] = _hexChar(v & 0x0f);
        return string(out);
    }

    function _hexChar(uint8 value) internal pure returns (bytes1) {
        if (value < 10) {
            return bytes1(uint8(48 + value));
        }
        return bytes1(uint8(87 + value));
    }

    function _toString(uint256 value) internal pure returns (string memory) {
        if (value == 0) {
            return "0";
        }
        uint256 temp = value;
        uint256 digits;
        while (temp != 0) {
            digits++;
            temp /= 10;
        }
        bytes memory buffer = new bytes(digits);
        while (value != 0) {
            digits -= 1;
            buffer[digits] = bytes1(uint8(48 + uint256(value % 10)));
            value /= 10;
        }
        return string(buffer);
    }
}