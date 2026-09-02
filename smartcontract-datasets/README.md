# smartcontract-datasets

The evaluation corpus. `_manifests/` is tracked in git; everything else here is
not — see `docs/DATASETS.md` for why, and for how to populate it.

```
smartcontract-datasets/
├── _manifests/            TRACKED — ground-truth labels
├── _scripts/              TRACKED — fetch/build scripts
├── 01_safe/               scored · safe class, three provenance tiers
├── 02_vuln_labelled/      scored · known-vulnerable
├── 03_massive_mix/        unscored · throughput only
├── 04_gptscan_web3bugs/   unscored · contest-level, GPTScan comparison
└── 05_similar_exploits/   unscored · retrieval corpus
```

Only `01_safe` and `02_vuln_labelled` ever enter an accuracy number. The other
three buckets are never mixed in — `thirdeye_bench.py` enforces this with
`SCORED_BUCKETS`.
