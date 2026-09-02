# Ablation — Access-Control detection (single-file balanced sample)

Sample: 8 AC-positive + 8 AC-negative = 16 contracts, seed=0.
Metric: AC-specific — a config is positive iff it confirms an access_control finding.
AC-negatives are contracts vulnerable in OTHER ways, so a positive there is a real false positive.

| config | model(s) | TP | FP | TN | FN | precision | recall | F1 |
|---|---|---|---|---|---|---|---|---|
| single_llm | llama3.1:8b (single) | 1 | 0 | 8 | 7 | 1.000 | 0.125 | 0.222 |
| council | qwen2.5-coder:7b + llama3.1:8b + gemma3:4b | 6 | 0 | 8 | 2 | 1.000 | 0.750 | 0.857 |
| council+arbitration | council + Cerebras gpt-oss-120b judge | 1 | 0 | 8 | 7 | 1.000 | 0.125 | 0.222 |

## Interpretation (honest)

**Headline — the council works.** Model-diverse council vs single-LLM on
access-control detection: recall 0.125 → 0.750, F1 0.222 → 0.857, precision
stays 1.000 (zero false positives on the 8 AC-negative contracts). Single-LLM
caught 1 of 8 AC bugs; the council caught 6 of 8. This is the precision+recall-
together improvement the AC literature calls unsolved, on a set with real
negative-class signal — validated here at small scale.

**Arbitration HURT on this slice — and the reason matters.** It knocked recall
back to 0.125 (dropped 5 of 6 true findings). Why: the council ALREADY had
perfect precision here (FP=0), so a precision-first filter had nothing to gain
and could only lose recall. Arbitration is a precision lever; it pays off only
when the council over-flags (cf. eth-046: 5 false findings collapsed to 1 real
one). Applying it unconditionally is wrong. Design implication (NOT tuned on
this test set): gate arbitration on the presence of likely false positives, or
calibrate the judge away from its precision-first default. Reported, not fixed.

**Caveats.** Sample = 16 single-file contracts (8+8), seed=0, local tier. The
≥3-seed mean±std protocol and the full-dataset run (multi-day, multi-provider)
are not done. The metric is AC-SPECIFIC (predicted-positive iff an
access_control finding is confirmed) — it does NOT capture the council's
over-flagging in OTHER categories (which arbitration/dynamic are meant to trim).
council+retrieval omitted: precedents aren't yet injected into prompts, so its
verdicts equal plain council by construction.
