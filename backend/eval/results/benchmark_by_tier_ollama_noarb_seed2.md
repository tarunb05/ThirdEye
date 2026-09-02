# ThirdEye benchmark by tier — backend=ollama, seed=2

90 scored contracts. Prediction: NO-GO=vulnerable, GO=safe, INCONCLUSIVE=abstain (excluded from P/R/F1).

## Per-tier

| tier | expected | n | scored | inconcl. | TP | FP | TN | FN | precision | recall | F1 | accuracy |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| Audited libraries (OZ/Solady) | safe | 15 | 10 | 5 | 0 | 3 | 7 | 0 | 0.000 | — | 0.000 | 0.700 |
| Audit-reviewed, clean | safe | 15 | 15 | 0 | 0 | 5 | 10 | 0 | 0.000 | — | 0.000 | 0.667 |
| Real-world, no bug reported | safe | 15 | 14 | 1 | 0 | 5 | 9 | 0 | 0.000 | — | 0.000 | 0.643 |
| Curated vulnerable (SmartBugs-style) | vulnerable | 15 | 15 | 0 | 14 | 0 | 0 | 1 | 1.000 | 0.933 | 0.966 | 0.933 |
| Injected vulnerability | vulnerable | 15 | 15 | 0 | 10 | 0 | 0 | 5 | 1.000 | 0.667 | 0.800 | 0.667 |
| Real audit-report findings | vulnerable | 15 | 12 | 3 | 8 | 0 | 0 | 4 | 1.000 | 0.667 | 0.800 | 0.667 |

## Aggregates

| slice | n | scored | inconcl. | TP | FP | TN | FN | precision | recall | F1 | accuracy |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| SAFE (all safe tiers) | 45 | 39 | 6 | 0 | 13 | 26 | 0 | 0.000 | — | 0.000 | 0.667 |
| VULN (all vuln tiers) | 45 | 42 | 3 | 32 | 0 | 0 | 10 | 1.000 | 0.762 | 0.865 | 0.762 |
| OVERALL | 90 | 81 | 9 | 32 | 13 | 26 | 10 | 0.711 | 0.762 | 0.736 | 0.716 |

## API-call accounting (per-user rate-limit sizing)

- Total LLM calls across the run: **341** over 90 contracts.
- Calls per contract: min=1, median=4.0, mean=3.79, p95=6, max=7.
- A single scan makes up to this many LLM calls. Size a per-user limit as (acceptable concurrent scans) x (p95 calls/contract). e.g. p95=6 calls/scan -> allowing 2 scans/user/min ~= 12 calls/user/min.
