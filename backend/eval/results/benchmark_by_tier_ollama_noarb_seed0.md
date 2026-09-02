# ThirdEye benchmark by tier — backend=ollama_noarb, seed=0

1154 scored contracts. Prediction: NO-GO=vulnerable, GO=safe, INCONCLUSIVE=abstain (excluded from P/R/F1).

## Per-tier

| tier | expected | n | scored | inconcl. | TP | FP | TN | FN | precision | recall | F1 | accuracy |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| Audited libraries (OZ/Solady) | safe | 172 | 172 | 0 | 0 | 40 | 132 | 0 | 0.000 | — | 0.000 | 0.767 |
| Audit-reviewed, clean | safe | 240 | 240 | 0 | 0 | 106 | 134 | 0 | 0.000 | — | 0.000 | 0.558 |
| Real-world, no bug reported | safe | 191 | 191 | 0 | 0 | 80 | 111 | 0 | 0.000 | — | 0.000 | 0.581 |
| Curated vulnerable (SmartBugs-style) | vulnerable | 214 | 214 | 0 | 185 | 0 | 0 | 29 | 1.000 | 0.864 | 0.927 | 0.864 |
| Injected vulnerability | vulnerable | 170 | 170 | 0 | 152 | 0 | 0 | 18 | 1.000 | 0.894 | 0.944 | 0.894 |
| Real audit-report findings | vulnerable | 167 | 167 | 0 | 118 | 0 | 0 | 49 | 1.000 | 0.707 | 0.828 | 0.707 |

## Aggregates

| slice | n | scored | inconcl. | TP | FP | TN | FN | precision | recall | F1 | accuracy |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| SAFE (all safe tiers) | 603 | 603 | 0 | 0 | 226 | 377 | 0 | 0.000 | — | 0.000 | 0.625 |
| VULN (all vuln tiers) | 551 | 551 | 0 | 455 | 0 | 0 | 96 | 1.000 | 0.826 | 0.905 | 0.826 |
| OVERALL | 1154 | 1154 | 0 | 455 | 226 | 377 | 96 | 0.668 | 0.826 | 0.739 | 0.721 |

## API-call accounting (per-user rate-limit sizing)

- Total LLM calls across the run: **4390** over 1154 contracts.
- Calls per contract: min=1, median=4.0, mean=3.8, p95=6, max=8.
- A single scan makes up to this many LLM calls. Size a per-user limit as (acceptable concurrent scans) x (p95 calls/contract). e.g. p95=6 calls/scan -> allowing 2 scans/user/min ~= 12 calls/user/min.
