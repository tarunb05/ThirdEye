# ThirdEye benchmark by tier — backend=ollama_noarb, seed=0

47 scored contracts. Prediction: NO-GO=vulnerable, GO=safe, INCONCLUSIVE=abstain (excluded from P/R/F1).

## Per-tier

| tier | expected | n | scored | inconcl. | TP | FP | TN | FN | precision | recall | F1 | accuracy |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| Audited libraries (OZ/Solady) | safe | 6 | 6 | 0 | 0 | 2 | 4 | 0 | 0.000 | — | 0.000 | 0.667 |
| Audit-reviewed, clean | safe | 7 | 7 | 0 | 0 | 4 | 3 | 0 | 0.000 | — | 0.000 | 0.429 |
| Real-world, no bug reported | safe | 8 | 8 | 0 | 0 | 4 | 4 | 0 | 0.000 | — | 0.000 | 0.500 |
| Curated vulnerable (SmartBugs-style) | vulnerable | 11 | 11 | 0 | 11 | 0 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 |
| Injected vulnerability | vulnerable | 7 | 7 | 0 | 6 | 0 | 0 | 1 | 1.000 | 0.857 | 0.923 | 0.857 |
| Real audit-report findings | vulnerable | 8 | 8 | 0 | 6 | 0 | 0 | 2 | 1.000 | 0.750 | 0.857 | 0.750 |

## Aggregates

| slice | n | scored | inconcl. | TP | FP | TN | FN | precision | recall | F1 | accuracy |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| SAFE (all safe tiers) | 21 | 21 | 0 | 0 | 10 | 11 | 0 | 0.000 | — | 0.000 | 0.524 |
| VULN (all vuln tiers) | 26 | 26 | 0 | 23 | 0 | 0 | 3 | 1.000 | 0.885 | 0.939 | 0.885 |
| OVERALL | 47 | 47 | 0 | 23 | 10 | 11 | 3 | 0.697 | 0.885 | 0.780 | 0.723 |

## API-call accounting (per-user rate-limit sizing)

- Total LLM calls across the run: **430** over 47 contracts.
- Calls per contract: min=1, median=7, mean=9.15, p95=24, max=60.
- A single scan makes up to this many LLM calls. Size a per-user limit as (acceptable concurrent scans) x (p95 calls/contract). e.g. p95=24 calls/scan -> allowing 2 scans/user/min ~= 48 calls/user/min.
