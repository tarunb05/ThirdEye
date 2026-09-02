# ThirdEye benchmark by tier — backend=hosted_fast, seed=0

57 scored contracts. Prediction: NO-GO=vulnerable, GO=safe, INCONCLUSIVE=abstain (excluded from P/R/F1).

## Per-tier

| tier | expected | n | scored | inconcl. | TP | FP | TN | FN | precision | recall | F1 | accuracy |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| Audited libraries (OZ/Solady) | safe | 27 | 27 | 0 | 0 | 13 | 14 | 0 | 0.000 | — | 0.000 | 0.519 |
| Audit-reviewed, clean | safe | 16 | 16 | 0 | 0 | 13 | 3 | 0 | 0.000 | — | 0.000 | 0.188 |
| Real-world, no bug reported | safe | 9 | 9 | 0 | 0 | 3 | 6 | 0 | 0.000 | — | 0.000 | 0.667 |
| Curated vulnerable (SmartBugs-style) | vulnerable | 5 | 5 | 0 | 3 | 0 | 0 | 2 | 1.000 | 0.600 | 0.750 | 0.600 |
| Injected vulnerability | vulnerable | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | — | — |
| Real audit-report findings | vulnerable | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | — | — |

## Aggregates

| slice | n | scored | inconcl. | TP | FP | TN | FN | precision | recall | F1 | accuracy |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| SAFE (all safe tiers) | 52 | 52 | 0 | 0 | 29 | 23 | 0 | 0.000 | — | 0.000 | 0.442 |
| VULN (all vuln tiers) | 5 | 5 | 0 | 3 | 0 | 0 | 2 | 1.000 | 0.600 | 0.750 | 0.600 |
| OVERALL | 57 | 57 | 0 | 3 | 29 | 23 | 2 | 0.094 | 0.600 | 0.162 | 0.456 |

## API-call accounting (per-user rate-limit sizing)

- Total LLM calls across the run: **284** over 57 contracts.
- Calls per contract: min=1, median=4, mean=4.98, p95=11, max=13.
- A single scan makes up to this many LLM calls. Size a per-user limit as (acceptable concurrent scans) x (p95 calls/contract). e.g. p95=11 calls/scan -> allowing 2 scans/user/min ~= 22 calls/user/min.
