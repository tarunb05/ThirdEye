PROMPT_MODEL_A = '''You are a Solidity security expert focusing on COMMON vulnerabilities.
Analyze this contract and identify:
1. Reentrancy issues
2. Integer overflow/underflow
3. Unchecked external calls
4. Missing access controls

Format as JSON: [{\"type\": \"...\", \"line\": X, \"severity\": \"critical|high|medium\", \"confidence\": 0.0-1.0}]

Examples:
- Reentrancy: external call before state update → critical
- Overflow: uint256 + 1 without SafeMath → high

Contract code:
{code}
'''

PROMPT_MODEL_B = '''You are a Solidity architect analyzing BUSINESS LOGIC vulnerabilities.
Look for:
1. State mutation order issues
2. Economic exploits (arbitrage, sandwich attacks)
3. Access control logic flaws
4. Unexpected behavior under edge cases

Format as JSON: [{\"type\": \"...\", \"line\": X, \"severity\": \"...\", \"confidence\": 0.0-1.0}]

Contract code:
{code}
'''

PROMPT_MODEL_C = '''You are a Solidity AUDITOR looking for OBSCURE, NOVEL vulnerabilities.
Ignore common issues (already covered by other models).
Focus on:
1. Unusual patterns that might break assumptions
2. Interaction with other contracts
3. Governance/flash loan vulnerabilities
4. Compiler-specific quirks

Format as JSON: [{\"type\": \"...\", \"line\": X, \"severity\": \"...\", \"confidence\": 0.0-1.0}]

Contract code:
{code}
'''
