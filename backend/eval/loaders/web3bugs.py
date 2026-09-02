"""
Loader for Web3Bugs (datasets/web3bugs/).

Source: https://github.com/ZhangZhuoSJTU/Web3Bugs (the ICSE'23 "Demystifying
Exploitable Bugs in Smart Contracts" dataset — NOT the MetaTrustLabs
GPTScan-Web3Bugs fork, which contains only PDF reports + GPTScan's own scan
results and no source code at all; that repo was tried first and rejected,
see docs/GAP_ANALYSIS.md discussion).

Format actually inspected (not assumed):
  - results/bugs.csv: one row per confirmed bug. Columns: "Contest ID",
    "Bug ID", "Bug Label", "Difficulty", "Bug Description", "Reference",
    "Comment". Every Bug ID in the current snapshot is "H-..." (Code4rena
    High severity) — there is no severity variance to derive here, all
    bugs in this dataset are High.
  - results/contests.csv: one row per contest. Columns: "ID", "Name",
    "Type", "Award Pool", "# Auditor", "Time", "# High", "Defillama".
  - contracts/<Contest ID>/: a snapshot of that project's repo at audit
    time. Layout is NOT uniform across projects (some use contracts/,
    others src/, etc.) — .sol files are found via a recursive glob, not an
    assumed fixed subpath.

Ground truth is project-level, not file/line-level: bugs.csv names a
contest, not a specific file or line. Every contest that has a contracts/
folder also has >=1 bug.csv row in the current snapshot, so this dataset
has NO clean/negative examples — it cannot be used alone to measure false
positive rate or precision against "safe" code, only recall-style metrics
against known-vulnerable projects (consistent with how GPTScan's own paper
reports mostly recall/F1 on this set).

Two Contest IDs referenced in bugs.csv (50, 11) have no contracts/ folder
in this clone — skipped, logged in the returned items' absence rather than
silently dropped (see load()'s return value vs row count if you need to
audit this).
"""

from __future__ import annotations

import csv

from eval.schema import DATASETS_ROOT, EvalItem, VulnCategory

ROOT = DATASETS_ROOT / "web3bugs"

_SEVERITY_RANK = {"H": 3, "M": 2, "L": 1}
_SEVERITY_NAME = {"H": "High", "M": "Medium", "L": "Low"}


def _read_csv(path):
    # DictReader fills short rows with None (restval) rather than "" — some
    # bugs.csv rows are short a trailing empty "Comment" field, so this is
    # real input shape, not something to special-case as an error.
    with open(path, encoding="utf-8-sig") as f:
        return [
            {k.strip(): (v.strip() if v is not None else "") for k, v in row.items() if k is not None}
            for row in csv.DictReader(f)
        ]


def load() -> list[EvalItem]:
    bugs = _read_csv(ROOT / "results" / "bugs.csv")
    contests = {c["ID"]: c for c in _read_csv(ROOT / "results" / "contests.csv")}

    bugs_by_contest: dict[str, list[dict]] = {}
    for b in bugs:
        bugs_by_contest.setdefault(b["Contest ID"], []).append(b)

    items = []
    skipped_no_source = []
    for contest_id, contest_bugs in bugs_by_contest.items():
        project_dir = ROOT / "contracts" / contest_id
        if not project_dir.is_dir():
            skipped_no_source.append(contest_id)
            continue

        sol_files = sorted(project_dir.rglob("*.sol"))
        categories = [VulnCategory(taxonomy="web3bugs", category=b["Bug Label"]) for b in contest_bugs]

        prefixes = {b["Bug ID"].split("-")[0] for b in contest_bugs if "-" in b["Bug ID"]}
        best = max(prefixes, key=lambda p: _SEVERITY_RANK.get(p, 0), default=None)
        severity = _SEVERITY_NAME.get(best, best)

        contest_meta = contests.get(contest_id, {})
        items.append(EvalItem(
            contract_id=contest_id,
            source_dataset="web3bugs",
            code_paths=sol_files,
            ground_truth_label="vulnerable",  # every contest here has >=1 confirmed bug
            vuln_categories=categories,
            severity=severity,
            meta={
                "contest_name": contest_meta.get("Name"),
                "contest_type": contest_meta.get("Type"),
                "bug_ids": [b["Bug ID"] for b in contest_bugs],
                "bug_descriptions": [b["Bug Description"] for b in contest_bugs],
                "references": [b["Reference"] for b in contest_bugs],
                "sol_file_count": len(sol_files),
            },
        ))

    if skipped_no_source:
        print(f"[web3bugs loader] skipped {len(skipped_no_source)} contest(s) with no contracts/ folder: {skipped_no_source}")

    return items
