# Ground-truth manifests

These files are the benchmark's **labels**, not its contracts. They are small,
they are what makes every number in this project reproducible, and unlike the
corpus itself they are tracked in git.

Drop the two manifest files from the dataset archive here:

| File | What it is | Read by |
|---|---|---|
| `labels.jsonl` | One row per scored contract: `{id, source_dataset, bucket, filepath, language, label, vuln_types[], vuln_lines[], origin_ref, label_quality, safe_tier\|vuln_tier}` | `backend/eval/loaders/thirdeye_bench.py` |
| `web3bugs_findings.jsonl` | Code4rena contest findings; only rows with `label_class == "S"` (semantic/logic bugs) are scored | `backend/eval/run_web3bugs.py` |

The contract files these rows point at live in the sibling bucket directories
and are **not** tracked — see `../README.md`.
