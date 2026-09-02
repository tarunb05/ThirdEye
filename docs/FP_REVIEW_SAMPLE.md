# False-positive review sample (n=20)

Random sample (seed 2026) of the 79 safe-labelled contracts the council blocked.
The question each row answers: **is this a tool error, or a real unreported bug
in a contract the dataset calls safe?**

My assessment is from the contract's externally-callable surface and from
knowing the codebase it comes from. Where I could not settle it from signatures
alone I say so rather than guessing. **The verdict column is deliberately blank —
these should be your calls, since it is your name on the claim.**

Confidence legend: **high** = settled by the contract's nature (pure library,
canonical audited code); **medium** = pattern is standard but I did not read the
whole body; **low** = needs a real read.

| # | contract | tool flagged | my assessment | conf | your verdict |
|--:|---|---|---|---|---|
| 1 | `ozup_proxy_utils_uupsupgradeable` | business_logic | **Tool error.** OZ UUPS upgrade hook, `onlyProxy` applied. Canonical audited code. | high | |
| 2 | `w3b_31_openzeppelin_accesscontrol` | business_logic | **Tool error.** OZ AccessControl. `grantRole`/`revokeRole` carry `onlyRole(getRoleAdmin(role))`; my lexical scan missed it. | high | |
| 3 | `solady_accounts_erc7821` | business_logic | **Tool error.** Solady batch executor; `execute` authorises in-body via `_authorizeExecute`, not a modifier. | medium | |
| 4 | `w3b_83_convexstakingwrapper` | business_logic | **Unclear.** `addRewards` / `requestWithdraw` lack modifiers. Permissionless reward-sync is a normal design here, but worth reading. | low | |
| 5 | `dappclean_dappmaintenance` | business_logic | **Tool error.** Every state-changing entrypoint is `onlyOwner`. | high | |
| 6 | `solady_accounts_eip7702proxy` | business_logic | **Tool error.** No external state-changing functions at all. | high | |
| 7 | `oz_token_erc721_enumerable` | business_logic, dos_gas | **Tool error.** Extension logic only, no external entrypoints. The `dos_gas` flag on `tokenOfOwnerByIndex` is a known-cost view, not a vulnerability. | high | |
| 8 | `dappclean_milestonepricing` | business_logic | **Tool error.** The "unguarded" functions are all getters written in Solidity 0.4 style (`constant`, not `view`), so my scan misread them as state-changing. | high | |
| 9 | `w3b_124_notional_trade_module` (a) | business_logic | **Tool error.** No external state-changing surface. | high | |
| 10 | `w3b_106_hexstrings` | business_logic, dos_gas | **Tool error.** Pure `library`, hex formatting, loop bounded by a `uint8`. Hand-read in full. | high | |
| 11 | `w3b_31_openzeppelin_*_lib` | business_logic | **Tool error.** Pure library, no state. | high | |
| 12 | `w3b_23_batchaction` (Notional) | business_logic | **Likely tool error.** `batchBalanceAction*` are user entrypoints acting on the caller's own account — permissionless by design. Confirm they key off `msg.sender`. | medium | |
| 13 | `w3b_124_notional_trade_module` (b) | business_logic | **Unclear.** `invokePreIssueHook` / `invokePreRedeemHook` are external without modifiers. If genuinely callable by anyone, that is worth a hard look. | low | |
| 14 | `w3b_90_indexlogic` | business_logic | **NEEDS REVIEW — highest priority.** `mint` and `burn` are external with no modifier. If not gated in-body, that is a real and severe finding in a "safe" contract. | low | |
| 15 | `ozup_finance_vestingwalletupgradeable` | business_logic, flashloan_mev | **Tool error.** `initialize` carries OZ's `initializer` modifier (missed by my scan); `release` is *intentionally* permissionless — anyone may push funds to the beneficiary. | high | |
| 16 | `w3b_68_amunbasket_bridge` | business_logic | **NEEDS REVIEW — highest priority.** `withdraw` / `withdrawTo` external with no modifier on a bridge contract. Either in-body accounting protects it or this is serious. | low | |
| 17 | `w3b_106_lendticketsvg` | business_logic | **Tool error.** SVG/descriptor rendering, no external state change. | high | |
| 18 | `dappclean_gsn_gsnrecipient` | business_logic | **Unclear.** `preRelayedCall` / `postRelayedCall` should be `onlyRelayHub`. If they are not, this is a known GSN weakness. | low | |
| 19 | `w3b_110_openzeppelin_timelockcontroller` | reentrancy | **Tool error.** `updateDelay` is guarded in-body by `require(msg.sender == address(this))` — self-call through the timelock. Canonical OZ. | high | |
| 20 | `w3b_31_bcvx_tokenswappathregistry` | business_logic | **Tool error.** No external state-changing functions. | high | |

## Tally (my assessment, pending your review)

| | count | share |
|---|--:|--:|
| Clear tool error | 14 | 70% |
| Unclear — needs a read | 4 | 20% |
| Possible real bug in a "safe" contract | 2 | 10% |

Plus `TwoKeyDeepFreezeTokenPool` from the earlier hand-read (unprotected
`setInitialParams`), which is a 21st data point and looks like a genuine defect.

## What this changes in the paper

**1. The false-alarm rate is mostly real.** ~70% of blocked safe contracts are
unambiguous tool errors. The headline number is not an artifact of label noise —
it is a real precision problem, and the paper should keep saying so.

**2. But a non-trivial tail is label noise.** 2–3 of 21 inspected contracts look
like genuine unreported vulnerabilities marked safe. That is enough to state the
direction — the measured rate is an upper bound — and not enough to quote a
correction factor.

**3. My earlier "46% have unguarded entrypoints" figure was inflated and should
not be used.** The lexical scan cannot see: OZ's `initializer` modifier,
in-body `require(msg.sender == …)` checks, `onlyRole(getRoleAdmin(role))`, or
Solidity 0.4 `constant` getters. At least 5 of the 20 above were misread by it.
The structural claim that survives is the narrow one: **12/79 (15%) are pure
libraries and therefore unexploitable by construction.**

## Priority for expert review

Read these two first — they are the ones that would change a number:

1. **`w3b_90_indexlogic`** — unguarded `mint`/`burn`
2. **`w3b_68_amunbasket_bridge`** — unguarded `withdraw`/`withdrawTo`

If either is genuinely exploitable, you have a second finding worth stating:
*balanced smart-contract benchmarks carry label noise in the safe class, and an
LLM auditor's measured false-positive rate is therefore an upper bound.*
