# ThirdEye benchmark by tier — backend=ollama, seed=1

90 scored contracts. Prediction: NO-GO=vulnerable, GO=safe, INCONCLUSIVE=abstain (excluded from P/R/F1).

## Per-tier

| tier | expected | n | scored | inconcl. | TP | FP | TN | FN | precision | recall | F1 | accuracy |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| Audited libraries (OZ/Solady) | safe | 15 | 10 | 5 | 0 | 5 | 5 | 0 | 0.000 | — | 0.000 | 0.500 |
| Audit-reviewed, clean | safe | 15 | 11 | 4 | 0 | 6 | 5 | 0 | 0.000 | — | 0.000 | 0.455 |
| Real-world, no bug reported | safe | 15 | 13 | 2 | 0 | 6 | 7 | 0 | 0.000 | — | 0.000 | 0.538 |
| Curated vulnerable (SmartBugs-style) | vulnerable | 15 | 14 | 1 | 13 | 0 | 0 | 1 | 1.000 | 0.929 | 0.963 | 0.929 |
| Injected vulnerability | vulnerable | 15 | 13 | 2 | 10 | 0 | 0 | 3 | 1.000 | 0.769 | 0.870 | 0.769 |
| Real audit-report findings | vulnerable | 15 | 13 | 2 | 9 | 0 | 0 | 4 | 1.000 | 0.692 | 0.818 | 0.692 |

## Aggregates

| slice | n | scored | inconcl. | TP | FP | TN | FN | precision | recall | F1 | accuracy |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| SAFE (all safe tiers) | 45 | 34 | 11 | 0 | 17 | 17 | 0 | 0.000 | — | 0.000 | 0.500 |
| VULN (all vuln tiers) | 45 | 40 | 5 | 32 | 0 | 0 | 8 | 1.000 | 0.800 | 0.889 | 0.800 |
| OVERALL | 90 | 74 | 16 | 32 | 17 | 17 | 8 | 0.653 | 0.800 | 0.719 | 0.662 |

## API-call accounting (per-user rate-limit sizing)

- Total LLM calls across the run: **341** over 90 contracts.
- Calls per contract: min=1, median=4.0, mean=3.79, p95=6, max=7.
- A single scan makes up to this many LLM calls. Size a per-user limit as (acceptable concurrent scans) x (p95 calls/contract). e.g. p95=6 calls/scan -> allowing 2 scans/user/min ~= 12 calls/user/min.
