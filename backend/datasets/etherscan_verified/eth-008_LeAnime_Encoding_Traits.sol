// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

interface ILeAnimeSoulsInHero {
    function getSoulsInHero(
        uint256 heroId
    ) external view returns (uint16[] memory);
}

contract LeAnime_Encoding_Traits {
    address public constant soulsInHeroAddress =
        0x1eb4490091bd0fFF6c3973623C014D082936EA03;

    function attributesJson(
        string memory encoding
    ) external view returns (string memory) {
        Decoded memory decoded = _decodeEncoding(encoding);
        uint16[] memory soulsLocked;
        bool soulsOk = false;
        bytes memory callData = abi.encodeWithSignature(
            "getSoulsInHero(uint256)",
            decoded.heroId
        );
        (bool ok, bytes memory data) = soulsInHeroAddress.staticcall(callData);
        if (ok && data.length >= 64) {
            soulsLocked = abi.decode(data, (uint16[]));
            soulsOk = true;
        }
        bytes memory out = "[";
        bool first = true;
        (out, first) = _appendMergedInfo(out, first, decoded.heroId, soulsOk, soulsLocked);
        (out, first) = _appendBaseTraits(out, first, decoded);
        (out, first) = _appendExtras(out, first, decoded);
        (out, first) = _appendAddLayers(out, first, decoded);
        return string(abi.encodePacked(out, "]"));
    }

    function _getArchetype(
        uint256 heroId,
        uint256 tokensInHero
    ) internal pure returns (string memory, uint256) {
        if (heroId <= 1573) {
            if (tokensInHero == 1) {
                return ("Le Anime", 20);
            }
            return ("Hero", 20);
        }
        if (tokensInHero == 1) {
            return ("Spirit", 1);
        }
        return ("Hero", 1);
    }

    function _appendMergedInfo(
        bytes memory out,
        bool first,
        uint256 heroId,
        bool soulsOk,
        uint16[] memory soulsLocked
    ) internal pure returns (bytes memory, bool) {
        uint256 tokensInHero = (soulsOk ? soulsLocked.length : 0) + 1;
        (string memory archetype, uint256 multiplier) = _getArchetype(
            heroId,
            tokensInHero
        );

        (out, first) = _appendAttributeString(
            out,
            first,
            "Merged NFTs",
            _toString(tokensInHero)
        );
        if (tokensInHero == 1) {
            (out, first) = _appendAttributeNumberWithDisplay(
                out,
                first,
                "Multiplier",
                multiplier,
                "boost_number"
            );
        }
        (out, first) = _appendAttributeString(
            out,
            first,
            "Archetype",
            archetype
        );
        if (soulsOk && soulsLocked.length > 0) {
            (out, first) = _appendAttributeArray(
                out,
                first,
                "Merged Token IDs",
                soulsLocked
            );
        }
        return (out, first);
    }

    function _appendBaseTraits(
        bytes memory out,
        bool first,
        Decoded memory decoded
    ) internal pure returns (bytes memory, bool) {
        (out, first) = _appendAttributeNumber(
            out,
            first,
            "Hero Level",
            _heroMaxLevel(decoded.score)
        );
        (out, first) = _appendAttributeNumber(
            out,
            first,
            "Hero Pose Level",
            decoded.rank
        );
        (out, first) = _appendAttributeNumber(
            out,
            first,
            "Score",
            decoded.score
        );
        (out, first) = _appendAttributeString(
            out,
            first,
            "Skin",
            _skinName(decoded.skin)
        );
        (out, first) = _appendAttributeString(
            out,
            first,
            "Clothes A",
            _clAName(decoded.clA)
        );
        (out, first) = _appendAttributeString(
            out,
            first,
            "Clothes B",
            _clBName(decoded.clB)
        );
        (out, first) = _appendAttributeString(
            out,
            first,
            "Background",
            _bgName(decoded.bg)
        );
        (out, first) = _appendAttributeString(
            out,
            first,
            "Halo",
            _haloName(decoded.halo)
        );
        (out, first) = _appendAttributeString(
            out,
            first,
            "Runes",
            _runesName(decoded.runes)
        );
        string memory runesLevelName = string(
            abi.encodePacked(_runesName(decoded.runes), " Level")
        );
        (out, first) = _appendAttributeNumber(
            out,
            first,
            runesLevelName,
            decoded.runesL
        );
        return (out, first);
    }

    function _appendExtras(
        bytes memory out,
        bool first,
        Decoded memory decoded
    ) internal pure returns (bytes memory, bool) {
        for (uint256 i = 0; i < decoded.extras.length; i++) {
            string memory extraName = _extraHeroName(decoded.extras[i]);
            (out, first) = _appendAttributeString(
                out,
                first,
                "Extra",
                extraName
            );
            string memory extraLevelName = string(
                abi.encodePacked(extraName, " Level")
            );
            (out, first) = _appendAttributeNumber(
                out,
                first,
                extraLevelName,
                decoded.extrasL[i]
            );
        }
        return (out, first);
    }

    function _appendAddLayers(
        bytes memory out,
        bool first,
        Decoded memory decoded
    ) internal pure returns (bytes memory, bool) {
        for (uint256 i = 0; i < decoded.addLayersMain.length; i++) {
            string memory addLayerName = _addLayerName(
                decoded.addLayersMain[i],
                decoded.addLayersId[i]
            );
            if (bytes(addLayerName).length == 0) {
                continue;
            }
            (out, first) = _appendAttributeString(
                out,
                first,
                "Additional Layer",
                addLayerName
            );
        }
        return (out, first);
    }

    struct Decoded {
        uint256 heroId;
        uint256 score;
        uint256 rank;
        uint256 skin;
        uint256 clA;
        uint256 clB;
        uint256 bg;
        uint256 halo;
        uint256 runes;
        uint256 runesL;
        uint256[] extras;
        uint256[] extrasL;
        uint256[] addLayersMain;
        uint256[] addLayersId;
    }

    function _decodeEncoding(
        string memory encoding
    ) internal pure returns (Decoded memory decoded) {
        bytes memory data = bytes(encoding);
        uint256 length = data.length;
        uint256 sIndex;
        uint256 hIndex;
        uint256 gIndex;
        for (uint256 i = 0; i < length; i++) {
            if (data[i] == "S") {
                decoded.heroId = _parseDecimal(data, 0, i);
                sIndex = i;
            } else if (data[i] == "H") {
                hIndex = i;
            } else if (data[i] == "G") {
                gIndex = i;
                break;
            }
        }
        if (hIndex > sIndex + 1) {
            decoded.score = _parseDecimal(data, sIndex + 1, hIndex);
        }
        if (gIndex > hIndex + 1) {
            _decodeTraits(data, hIndex + 1, gIndex, decoded);
        }
        (decoded.addLayersMain, decoded.addLayersId) = _decodeAddLayers(data);
    }

    function _decodeTraits(
        bytes memory data,
        uint256 start,
        uint256 end,
        Decoded memory decoded
    ) internal pure {
        uint256 len = end - start;
        if (len < 16) {
            return;
        }
        decoded.rank = _parseHexPair(data, start) + 1;
        decoded.skin = _parseHexPair(data, start + 2);
        decoded.clA = _parseHexPair(data, start + 4);
        decoded.clB = _parseHexPair(data, start + 6);
        decoded.bg = _parseHexPair(data, start + 8);
        decoded.halo = _parseHexPair(data, start + 10);
        decoded.runes = _parseHexPair(data, start + 12);
        decoded.runesL = _parseHexPair(data, start + 14) + 1;

        uint256 extrasCount = 0;
        if (len > 16) {
            extrasCount = (len / 2 - 8) / 2;
        }
        decoded.extras = new uint256[](extrasCount);
        decoded.extrasL = new uint256[](extrasCount);
        uint256 offset = start + 16;
        for (uint256 i = 0; i < extrasCount; i++) {
            decoded.extras[i] = _parseHexPair(data, offset + i * 4);
            decoded.extrasL[i] = _parseHexPair(data, offset + i * 4 + 2) + 1;
        }
    }

    function _decodeAddLayers(
        bytes memory data
    ) internal pure returns (uint256[] memory main, uint256[] memory ids) {
        uint256 count;
        for (uint256 j = 0; j < data.length; j++) {
            if (data[j] == "X") {
                count++;
            }
        }
        main = new uint256[](count);
        ids = new uint256[](count);
        uint256 idx;
        uint256 i = 0;
        while (i < data.length) {
            if (data[i] == "X") {
                uint256 xStart = i + 1;
                uint256 lPos = _findChar(data, "L", xStart);
                if (lPos > xStart) {
                    main[idx] = _parseHexRange(data, xStart, lPos);
                    uint256 nextX = _findChar(data, "X", lPos + 1);
                    if (nextX == 0 || nextX <= lPos + 1) {
                        nextX = data.length;
                    }
                    ids[idx] = _parseHexRange(data, lPos + 1, nextX);
                    idx++;
                    i = nextX;
                    continue;
                }
            }
            i++;
        }
        if (idx < count) {
            assembly {
                mstore(main, idx)
                mstore(ids, idx)
            }
        }
    }

    function _findChar(
        bytes memory data,
        bytes1 needle,
        uint256 start
    ) internal pure returns (uint256) {
        for (uint256 i = start; i < data.length; i++) {
            if (data[i] == needle) {
                return i;
            }
        }
        return 0;
    }

    function _parseDecimal(
        bytes memory data,
        uint256 start,
        uint256 end
    ) internal pure returns (uint256 value) {
        for (uint256 i = start; i < end; i++) {
            uint8 c = uint8(data[i]);
            if (c < 48 || c > 57) {
                break;
            }
            value = value * 10 + (c - 48);
        }
    }

    function _parseHexPair(
        bytes memory data,
        uint256 index
    ) internal pure returns (uint256) {
        if (index + 1 >= data.length) {
            return 0;
        }
        uint8 hi = _hexValue(data[index]);
        uint8 lo = _hexValue(data[index + 1]);
        return uint256(hi) * 16 + uint256(lo);
    }

    function _parseHexRange(
        bytes memory data,
        uint256 start,
        uint256 end
    ) internal pure returns (uint256 value) {
        for (uint256 i = start; i < end; i++) {
            uint8 v = _hexValue(data[i]);
            value = value * 16 + v;
        }
    }

    function _appendAttributeString(
        bytes memory out,
        bool first,
        string memory traitType,
        string memory value
    ) internal pure returns (bytes memory, bool) {
        if (!first) {
            out = abi.encodePacked(out, ",");
        }
        out = abi.encodePacked(
            out,
            "{\"trait_type\":\"",
            traitType,
            "\",\"value\":\"",
            value,
            "\"}"
        );
        return (out, false);
    }

    function _appendAttributeNumber(
        bytes memory out,
        bool first,
        string memory traitType,
        uint256 value
    ) internal pure returns (bytes memory, bool) {
        if (!first) {
            out = abi.encodePacked(out, ",");
        }
        out = abi.encodePacked(
            out,
            "{\"trait_type\":\"",
            traitType,
            "\",\"value\":",
            _toString(value),
            "}"
        );
        return (out, false);
    }

    function _appendAttributeNumberWithDisplay(
        bytes memory out,
        bool first,
        string memory traitType,
        uint256 value,
        string memory displayType
    ) internal pure returns (bytes memory, bool) {
        if (!first) {
            out = abi.encodePacked(out, ",");
        }
        out = abi.encodePacked(
            out,
            "{\"trait_type\":\"",
            traitType,
            "\",\"value\":",
            _toString(value),
            ",\"display_type\":\"",
            displayType,
            "\"}"
        );
        return (out, false);
    }

    function _appendAttributeArray(
        bytes memory out,
        bool first,
        string memory traitType,
        uint16[] memory values
    ) internal pure returns (bytes memory, bool) {
        if (!first) {
            out = abi.encodePacked(out, ",");
        }
        bytes memory list = "[";
        for (uint256 i = 0; i < values.length; i++) {
            if (i != 0) {
                list = abi.encodePacked(list, ",");
            }
            list = abi.encodePacked(list, _toString(values[i]));
        }
        list = abi.encodePacked(list, "]");
        out = abi.encodePacked(
            out,
            "{\"trait_type\":\"",
            traitType,
            "\",\"value\":",
            list,
            "}"
        );
        return (out, false);
    }

    function _heroMaxLevel(uint256 score) internal pure returns (uint256) {
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

    function _skinName(uint256 index) internal pure returns (string memory) {
        string[28] memory values = [
            "Invisible",
            "Midnight",
            "Crescent Pattern",
            "Pure Black",
            "Dark Lines",
            "Marble Lines",
            "Pure White",
            "Golden Ghost",
            "Pure Gold",
            "Golden Stripes",
            "Wide Stripes",
            "Ethereal Ghost",
            "Cobalt Lines",
            "Cobalt Spectre",
            "Starlight",
            "Cobalt Pattern",
            "Amber Spirit",
            "Wider Amber",
            "Enigma",
            "Emerald Lines",
            "Emerald Stripes",
            "Amethyst Ghost",
            "Amethyst Stripes",
            "Ivory Spectre",
            "Ivory  Stripes",
            "Gold Checker",
            "Dante",
            "Crimson"
        ];
        if (index >= values.length) {
            return "";
        }
        return values[index];
    }

    function _clAName(uint256 index) internal pure returns (string memory) {
        return _skinName(index);
    }

    function _clBName(uint256 index) internal pure returns (string memory) {
        return _skinName(index);
    }

    function _bgName(uint256 index) internal pure returns (string memory) {
        string[14] memory values = [
            "Invisible",
            "Three Pillars",
            "Pillars Frame",
            "Hell Gate",
            "Stargates",
            "Ruins",
            "Frostbite",
            "Inferno",
            "Gold Tree",
            "Cobalt Tree",
            "Death Field",
            "Obsidian",
            "Multi Rings",
            "Tilt"
        ];
        if (index >= values.length) {
            return "";
        }
        return values[index];
    }

    function _haloName(uint256 index) internal pure returns (string memory) {
        string[26] memory values = [
            "Invisible",
            "Thorns Crown",
            "Holy Crown",
            "Rune Circle",
            "Combo",
            "Aurora Cross",
            "Magic Triangle",
            "Reverse Triangle",
            "Hexagram",
            "Grazie Mauro",
            "Aurora Crown",
            "Trinity",
            "Skull Crown",
            "Triple Thorns",
            "Rings",
            "Kami",
            "Square",
            "Amethyst Combo",
            "Amethyst Thorns Crown",
            "Emerald Holy Crown",
            "Emerald Aurora Cross",
            "Amber Rune Circle",
            "Cobalt Thorns Crown",
            "Amber Thorns Crown",
            "Ivory Thorns Crown",
            "Crimson Thorns Crown"
        ];
        if (index >= values.length) {
            return "";
        }
        return values[index];
    }

    function _runesName(uint256 index) internal pure returns (string memory) {
        string[16] memory values = [
            "Invisible",
            "Fish",
            "R",
            "I",
            "Mother",
            "Up Only",
            "Burning S",
            "Daemon Face",
            "Up Only Fish",
            "Roman",
            "Hieroglyphs",
            "Andrea",
            "gm",
            "Loom",
            "Path",
            "Abana"
        ];
        if (index >= values.length) {
            return "";
        }
        return values[index];
    }

    function _extraHeroName(uint256 index) internal pure returns (string memory) {
        string[19] memory values = [
            "Invisible",
            "Wisdom Manuscript",
            "Greatest Sword",
            "Laurel Wings",
            "Heart Staff",
            "Skull Scythe",
            "Magic Harp",
            "Crystal Bow",
            "Up Only",
            "69",
            "777",
            "Lightsaber",
            "Gold Book",
            "Gold Bow",
            "Gold Lyre",
            "Gold Scythe",
            "Gold Staff",
            "Gold Sword",
            "Gold Wings"
        ];
        if (index >= values.length) {
            return "";
        }
        return values[index];
    }

    function _addLayerName(
        uint256 main,
        uint256 id
    ) internal pure returns (string memory) {
        if (main == 1 && id == 1) {
            return "Halloween 2022";
        }
        if (main == 2) {
            if (id == 1) {
                return "Raf Grassetti";
            }
            if (id == 2) {
                return "XSULLO";
            }
        }
        if (main == 3 && id == 1) {
            return "Hell Shackles";
        }
        if (main == 4 && id == 1) {
            return "Royal Crown";
        }
        if (main == 5 && id == 1) {
            return "Golden Snakes";
        }
        if (main == 6 && id == 1) {
            return "Spectral Crystals";
        }
        if (main == 7 && id == 1) {
            return "Frame 1";
        }
        if (main == 8) {
            if (id == 1) {
                return "Frame 2";
            }
            if (id == 2) {
                return "Frame 3";
            }
            if (id == 3) {
                return "Frame 4";
            }
            if (id == 4) {
                return "Frame 5";
            }
        }
        return "";
    }

    function _hexValue(bytes1 value) internal pure returns (uint8) {
        uint8 c = uint8(value);
        if (c >= 48 && c <= 57) {
            return c - 48;
        }
        if (c >= 65 && c <= 70) {
            return c - 55;
        }
        if (c >= 97 && c <= 102) {
            return c - 87;
        }
        return 0;
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