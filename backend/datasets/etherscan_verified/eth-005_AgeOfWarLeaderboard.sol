// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract AgeOfWarLeaderboard {
    struct ScoreEntry {
        address player;
        uint256 score;
        uint8 difficulty;  // 0=easy, 1=normal, 2=hard
        uint8 era;         // 1-5
        uint256 timestamp;
    }

    uint256 public constant MAX_SCORE = 50000;
    uint256 public constant COOLDOWN = 30;
    uint256 public constant LEADERBOARD_SIZE = 10;

    ScoreEntry[10] public leaderboard;
    uint256 public entryCount;

    mapping(address => uint256) public lastSubmitTime;
    mapping(address => uint256) public personalBest;
    mapping(address => string) public usernames;

    event ScoreSubmitted(address indexed player, uint256 score, uint8 difficulty, uint8 era, uint256 timestamp);
    event LeaderboardUpdated(address indexed player, uint256 score, uint256 rank);
    event UsernameSet(address indexed player, string name);

    function setUsername(string calldata _name) external {
        require(bytes(_name).length > 0 && bytes(_name).length <= 16, "Name 1-16 chars");
        usernames[msg.sender] = _name;
        emit UsernameSet(msg.sender, _name);
    }

    function submitScore(uint256 _score, uint8 _difficulty, uint8 _era) external {
        require(_score > 0 && _score <= MAX_SCORE, "Invalid score");
        require(_difficulty <= 2, "Invalid difficulty");
        require(_era >= 1 && _era <= 5, "Invalid era");
        require(block.timestamp >= lastSubmitTime[msg.sender] + COOLDOWN, "Cooldown active");

        lastSubmitTime[msg.sender] = block.timestamp;

        if (_score > personalBest[msg.sender]) {
            personalBest[msg.sender] = _score;
        }

        emit ScoreSubmitted(msg.sender, _score, _difficulty, _era, block.timestamp);

        if (entryCount < LEADERBOARD_SIZE || _score > leaderboard[LEADERBOARD_SIZE - 1].score) {
            _insertScore(ScoreEntry({
                player: msg.sender,
                score: _score,
                difficulty: _difficulty,
                era: _era,
                timestamp: block.timestamp
            }));
        }
    }

    function _insertScore(ScoreEntry memory entry) internal {
        uint256 existingIdx = type(uint256).max;
        for (uint256 i = 0; i < entryCount; i++) {
            if (leaderboard[i].player == entry.player) {
                if (entry.score <= leaderboard[i].score) return;
                existingIdx = i;
                break;
            }
        }

        if (existingIdx != type(uint256).max) {
            for (uint256 i = existingIdx; i < entryCount - 1; i++) {
                leaderboard[i] = leaderboard[i + 1];
            }
            entryCount--;
        }

        uint256 insertAt = entryCount;
        for (uint256 i = 0; i < entryCount; i++) {
            if (entry.score > leaderboard[i].score) {
                insertAt = i;
                break;
            }
        }

        uint256 end = entryCount < LEADERBOARD_SIZE ? entryCount : LEADERBOARD_SIZE - 1;
        for (uint256 i = end; i > insertAt; i--) {
            leaderboard[i] = leaderboard[i - 1];
        }

        leaderboard[insertAt] = entry;
        if (entryCount < LEADERBOARD_SIZE) entryCount++;

        emit LeaderboardUpdated(entry.player, entry.score, insertAt + 1);
    }

    function getLeaderboard() external view returns (ScoreEntry[] memory) {
        ScoreEntry[] memory result = new ScoreEntry[](entryCount);
        for (uint256 i = 0; i < entryCount; i++) {
            result[i] = leaderboard[i];
        }
        return result;
    }

    function getPersonalBest(address _player) external view returns (uint256) {
        return personalBest[_player];
    }
}