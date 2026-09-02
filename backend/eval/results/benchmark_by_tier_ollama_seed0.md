# ThirdEye benchmark by tier — backend=ollama, seed=0

314 scored contracts. Prediction: NO-GO=vulnerable, GO=safe, INCONCLUSIVE=abstain (excluded from P/R/F1).

## Per-tier

| tier | expected | n | scored | inconcl. | TP | FP | TN | FN | precision | recall | F1 | accuracy |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| Audited libraries (OZ/Solady) | safe | 156 | 156 | 0 | 0 | 6 | 150 | 0 | 0.000 | — | 0.000 | 0.962 |
| Audit-reviewed, clean | safe | 48 | 48 | 0 | 0 | 1 | 47 | 0 | 0.000 | — | 0.000 | 0.979 |
| Real-world, no bug reported | safe | 44 | 44 | 0 | 0 | 1 | 43 | 0 | 0.000 | — | 0.000 | 0.977 |
| Curated vulnerable (SmartBugs-style) | vulnerable | 47 | 47 | 0 | 13 | 0 | 0 | 34 | 1.000 | 0.277 | 0.433 | 0.277 |
| Injected vulnerability | vulnerable | 19 | 19 | 0 | 6 | 0 | 0 | 13 | 1.000 | 0.316 | 0.480 | 0.316 |
| Real audit-report findings | vulnerable | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | — | — |

## Aggregates

| slice | n | scored | inconcl. | TP | FP | TN | FN | precision | recall | F1 | accuracy |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| SAFE (all safe tiers) | 248 | 248 | 0 | 0 | 8 | 240 | 0 | 0.000 | — | 0.000 | 0.968 |
| VULN (all vuln tiers) | 66 | 66 | 0 | 19 | 0 | 0 | 47 | 1.000 | 0.288 | 0.447 | 0.288 |
| OVERALL | 314 | 314 | 0 | 19 | 8 | 240 | 47 | 0.704 | 0.288 | 0.409 | 0.825 |

## API-call accounting (per-user rate-limit sizing)

- Total LLM calls across the run: **2898** over 314 contracts.
- Calls per contract: min=1, median=7.0, mean=9.23, p95=22, max=42.
- A single scan makes up to this many LLM calls. Size a per-user limit as (acceptable concurrent scans) x (p95 calls/contract). e.g. p95=22 calls/scan -> allowing 2 scans/user/min ~= 44 calls/user/min.
