# The evaluation corpus

Every accuracy number this project reports comes from here. This document says
what the corpus contains, which parts of it are allowed to enter a score, what
is tracked in git and what is not, and how to populate it on a fresh clone.

---

## Why the corpus exists at all

The datasets this project started with — Etherscan-50, SmartBugs-Curated,
Web3Bugs — are **all-positive**: every contract in them is vulnerable. That
makes a false-positive rate mechanically unmeasurable, because there is no safe
contract to wrongly flag. A tool that flags everything scores perfectly.

`smartcontract-datasets/` exists to fix exactly that. It has a genuine **safe**
class, assembled at three levels of label trust, so precision, false-alarm rate,
and the claim that a well-audited contract should come back GO are all testable
for the first time.

---

## Layout

```
smartcontract-datasets/
├── _manifests/            TRACKED    ground-truth labels
├── _scripts/              TRACKED    fetch / build scripts
├── 01_safe/               not tracked · SCORED
├── 02_vuln_labelled/      not tracked · SCORED
├── 03_massive_mix/        not tracked · unscored
├── 04_gptscan_web3bugs/   not tracked · unscored
└── 05_similar_exploits/   not tracked · unscored
```

### The two scored buckets

Only these ever enter an accuracy number. `eval/loaders/thirdeye_bench.py`
enforces it with a `SCORED_BUCKETS` set rather than by convention, so a bucket
cannot leak into a score by accident.

| Bucket | Class | Tiers |
|---|---|---|
| `01_safe` | safe — should verdict **GO** | `audited_library` (OpenZeppelin, Solady) · `audit_reviewed_clean` · `realworld_no_bug_reported` |
| `02_vuln_labelled` | vulnerable — should verdict **NO-GO** | `curated` (SmartBugs-style) · `audit_report` |

**The three safe tiers are the point, not bookkeeping.** They are ordered by how
much the "safe" label can be trusted, and the measured false-alarm rate tracks
that ordering — lowest on audited libraries, highest on code that merely has no
reported bug. That gradient is the paper's central argument: a false-alarm rate
is partly a statement about how the negative class was assembled. Collapsing
these tiers into one "safe" bucket would destroy the result.

### The three unscored buckets

Never mixed into precision, recall or F1. They exist for other jobs:

| Bucket | Job |
|---|---|
| `03_massive_mix` | throughput and latency measurement only |
| `04_gptscan_web3bugs` | contest-level projects for the GPTScan head-to-head; scored at project level against its own manifest, not the contract-level labels |
| `05_similar_exploits` | retrieval corpus — precedents for `services/retrieval.py`, never a test set |

If a number in the paper cites one of these, it says so explicitly and it is not
an accuracy number.

---

## What is tracked, and why

**The manifests are tracked. The contracts are not.**

The contract files are large third-party corpora that can be re-fetched from
their upstream sources. The manifests are small, are authored here, and are the
only thing that makes a result reproducible — they are the ground truth. The
repository previously ignored the whole directory, which meant the labels for
every published number lived on one laptop and nowhere else. That is now fixed:

```gitignore
smartcontract-datasets/*
!smartcontract-datasets/README.md
!smartcontract-datasets/_manifests/
!smartcontract-datasets/_scripts/
```

### `_manifests/labels.jsonl`

One JSON object per line, one line per scored contract:

```json
{
  "id": "...",
  "source_dataset": "...",
  "bucket": "01_safe",
  "filepath": "01_safe/audited_library/....sol",
  "language": "solidity",
  "label": "safe",
  "vuln_types": [],
  "vuln_lines": [],
  "origin_ref": "...",
  "label_quality": "...",
  "safe_tier": "audited_library"
}
```

`filepath` is relative to `smartcontract-datasets/`. A vulnerable row carries
`vuln_tier` in place of `safe_tier`. Read by
`backend/eval/loaders/thirdeye_bench.py`.

### `_manifests/web3bugs_findings.jsonl`

Code4rena contest findings. Only rows with `label_class == "S"` — the semantic
and logic bugs, which are GPTScan's target class — are scored. Read by
`backend/eval/run_web3bugs.py`.

---

## Populating a fresh clone

The loaders degrade rather than crash when the corpus is absent:
`thirdeye_bench.py` prints `labels not found at … — is smartcontract-datasets/
present?` and returns an empty list, so the app and the test suite still run.
Only the benchmark runners need the real thing.

1. Clone the repo. `_manifests/` and `_scripts/` arrive with it.
2. Drop the bucket directories (`01_safe/` … `05_similar_exploits/`) into
   `smartcontract-datasets/`. They are gitignored, so nothing will be committed.
3. Verify that the files and the labels actually agree:

```bash
python smartcontract-datasets/_scripts/verify_corpus.py
```

It exits 0 when the corpus is clean, 1 when it is not, and 2 when there is no
manifest to check — so CI can tell "broken" from "not present here".

It checks six things: every labelled row has the required fields and a valid
bucket/label/tier; every scored row points at a file that exists; every file in
a scored bucket has a row; no id appears twice; no two ids point at
byte-identical source; and it reports the safe/vulnerable split per bucket and
per tier.

**Why this exists.** Every loader already recorded `code_path_exists` on each
item it produced, and nothing ever read it. A labelled contract whose file was
missing reached a benchmark run, failed to analyse, and was recorded as an
abstention rather than as a broken corpus — the pipeline did not crash, the
number just quietly moved. Duplicate content is the worse case: the same
contract under two ids inflates n and double-counts one verdict, moving a
published rate without moving anything real.

`backend/tests/test_dataset_integrity.py` exercises the checker against
synthetic fixtures, so the logic is tested in CI even though the corpus is not
there.

---

## The older corpora

These predate the balanced benchmark and are kept for the comparisons that cite
them:

| Corpus | Where | Status |
|---|---|---|
| Etherscan-50 | `backend/datasets/etherscan_verified/` + `index.json` | **Not a headline benchmark.** Its ground truth is scraped and heuristic; several entries' own notes say "vulnerabilities not checked yet". Loadable for smoke tests (`--datasets etherscan50`), never in a default run. |
| SmartBugs-Curated | `datasets/` (gitignored, cloned by its loader) | 143 contracts, all vulnerable. Used for the retrieval corpus and as a curated slice. |
| Web3Bugs | `datasets/` (gitignored) | ICSE'23 corpus. Sliced per-file by `eval/slicing.py` — the whole-project concatenation it replaced left only 1 of 102 projects analyzable. |

Dropping Etherscan-50 as a headline set was a deliberate decision, recorded in
`docs/DECISION_LOG.md`. Keeping a dataset whose labels cannot be trusted, just
because it is already there, is how an evaluation quietly stops meaning
anything.
