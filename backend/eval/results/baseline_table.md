# Baseline ablation table (with model-diverse council)

## Provenance — read this before citing any number

This table merges results from two different machines/sessions:

- **`slither`, `single_llm`, `current_thirdeye` rows** — from the prior
  sessions' checkpointed runs (Slither: Windows + WSL2; LLM baselines: local
  Ollama via WSL2 on `llama3.2:3b`). Those checkpoints are **not** present on
  the machine that generated the council rows, so they are reproduced here
  from the Session 1–4 results, not recomputed. `build_reports.py` on this
  machine deliberately skips any (baseline, dataset) pair it has no
  checkpoints for rather than emitting a misleading 0.000 row.
- **`council` rows** — computed fresh on this machine (macOS, local Ollama)
  from real checkpoints under `eval/checkpoints/council/`, 50/50 + 143/143
  items, no skips. Reproduce with:
  `python -m eval.run_baselines --datasets etherscan50,smartbugs_curated --baselines council --llm-backend ollama`
  then `python -m eval.build_reports`.

Binary precision/recall/F1 are not meaningful pooled across datasets:
SmartBugs-Curated has **zero** negative (likely_safe) examples, so its
precision is mechanically 1.000 whenever recall is nonzero. Only Etherscan-50
has real negative-class signal — and its ground truth is heuristic/scraped
(several entries' own `notes` say "vulnerabilities not checked yet"), so treat
its absolute numbers as noisy. The council-vs-baseline comparison on
Etherscan-50 is still apples-to-apples: every row is scored against the same
(noisy) ground truth.

## Ablation table

| dataset | baseline | model(s) | n_analyzed/n_total | precision | recall | F1 | top categories detected |
|---|---|---|---|---|---|---|---|
| smartbugs_curated | single_llm | llama3.2:3b | 143/143 | 1.000 | 0.811 | 0.896 | access_control(5), unchecked_low_level_calls(5), arithmetic(3) |
| etherscan50 | single_llm | llama3.2:3b | 50/50 | 0.182 | 0.667 | 0.286 | access_control(2) |
| smartbugs_curated | current_thirdeye (LLM+Slither) | llama3.2:3b + Slither | 143/143 | 1.000 | 0.958 | 0.979 | unchecked_low_level_calls(52), reentrancy(29), access_control(9) |
| etherscan50 | current_thirdeye (LLM+Slither) | llama3.2:3b + Slither | 50/50 | 0.140 | 1.000 | 0.245 | access_control(4) |
| smartbugs_curated | council (model-diverse, agreement-gated) | qwen2.5-coder:7b + llama3.2:3b | 143/143 | 1.000 | 0.881 | 0.937 | reentrancy(29), access_control(13), other(2) |
| etherscan50 | council (model-diverse, agreement-gated) | qwen2.5-coder:7b + llama3.2:3b | 50/50 | 0.067 | 0.167 | 0.095 | access_control(1) |

(Slither-only rows, for reference, from prior sessions: smartbugs_curated
122/143 P/R/F1 = 1.000/1.000/1.000; etherscan50 50/50 = 0.120/1.000/0.214;
web3bugs 1/102 = 1.000/1.000/1.000.)

## The result, stated honestly

**The council did NOT deliver the paper's central claim.** The thesis was:
raise Etherscan-50 precision above the single-LLM / current-ThirdEye baselines
while holding recall at or near current_thirdeye's 1.0. It did the opposite.

Etherscan-50 confusion matrix for the council: **tp=1, fp=14, tn=30, fn=5**
(only ~6 positives exist in this set's ground truth).

- **Precision fell to 0.067** — below single_llm (0.182) and current_thirdeye
  (0.140). Of the 15 contracts the council flagged, only 1 was a true positive.
- **Recall collapsed to 0.167** — far below single_llm's 0.667 and
  current_thirdeye's 1.000. The agreement gate suppressed 5 of 6 real
  vulnerabilities.
- So the gate traded away most of the recall AND precision still got worse,
  because the few findings that survived the gate were mostly false positives.

On SmartBugs-Curated the council is respectable (R=0.881, F1=0.937) but that's
the easy, all-positive dataset where precision is mechanically 1.000 — it does
not test the precision hypothesis at all.

### Why (diagnostic, not yet fixed — no test-set tuning per the build constraints)

1. **Specialists miss textbook cases.** On `eth-046_custodian_Bank.sol` the
   reentrancy specialist (qwen2.5-coder:7b) returned `found=false,
   confidence=0.0` despite a canonical call-before-state-update reentrancy.
   The gate can only confirm what a specialist surfaces; weak per-specialist
   recall caps council recall.
2. **The surviving findings are noisy.** fp=14 means the agreement/high-conf
   path is confirming the wrong contracts on Etherscan-50's flattened,
   real-world code — a different failure mode than the clean SmartBugs samples.
3. **Etherscan-50 ground truth is heuristic.** Some "positives" may not be real
   and some "safe" contracts may be vulnerable, inflating both fp and fn. This
   limits how much weight any Etherscan-50 number (council or baseline) should
   carry — a documented pre-existing caveat, not a council-specific excuse.

### Recommendation (for a later session — NOT done here)
Do not tune thresholds against Etherscan-50. The honest next steps are:
(a) improve per-specialist recall with better few-shots / a stronger code model
before touching the gate; (b) get expert-verified ground truth for a real
negative-class benchmark, since Etherscan-50's scraped labels are too noisy to
anchor the paper's precision claim; (c) only then re-evaluate the gate.
