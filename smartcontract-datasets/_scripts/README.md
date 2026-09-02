# Dataset build and verification scripts

| Script | What it does |
|---|---|
| `verify_corpus.py` | Checks that the contracts on disk and the labels in `../_manifests/` agree — schema, missing files, orphans, duplicate ids, duplicate content, and the class balance per bucket and tier. Exit 0 clean, 1 broken, 2 no manifest. |

Anything that fetches or assembles the buckets from their upstream sources
belongs here too, tracked, so the corpus is reproducible rather than a folder
someone happens to have. A fetch script should write contracts into the right
bucket directory and append one row per scored contract to
`../_manifests/labels.jsonl` — then `verify_corpus.py` will confirm the two
agree. Anything that cannot be re-derived from an upstream source should say so
in `docs/DATASETS.md` rather than silently existing.
