def _simple_summary(code: str) -> str:
    """
    Very dumb heuristic summary so we don't need any API keys.
    """
    code_lower = code.lower()
    if "token" in code_lower:
        return "This contract manages tokens and basic balance-related operations."
    if "erc20" in code_lower:
        return "This contract looks like an ERC20-style token implementation."
    if "payable" in code_lower:
        return "This contract receives ETH and handles simple payment flows."
    return "This is a Solidity contract with basic state variables and functions."


async def summarize_code(code: str) -> str:
    """
    Mock async wrapper for summary.
    """
    return _simple_summary(code)


async def analyze_with_gpt4_mini(code: str) -> list:
    """
    Mock Model A: returns a fixed 'no critical issues' list.
    """
    return []


async def analyze_with_claude_sonnet(code: str) -> list:
    """
    Mock Model B.
    """
    return []


async def analyze_with_gpt4(code: str) -> list:
    """
    Mock Model C.
    """
    return []
