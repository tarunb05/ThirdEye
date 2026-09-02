"""
Loader for SmartBugs-Curated (datasets/smartbugs-curated/).

Source: https://github.com/smartbugs/smartbugs-curated
Format actually inspected (not assumed): a single vulnerabilities.json at the
repo root, one entry per .sol file, each with a "vulnerabilities" list of
{"lines": [...], "category": "<dasp10 category>"}. All 143 contracts have at
least one vulnerability — there are no clean/negative examples in this set.
"""

from __future__ import annotations

import json

from eval.schema import DATASETS_ROOT, EvalItem, VulnCategory

ROOT = DATASETS_ROOT / "smartbugs-curated"


def load() -> list[EvalItem]:
    manifest_path = ROOT / "vulnerabilities.json"
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    items = []
    for entry in manifest:
        code_path = ROOT / entry["path"]
        categories = [
            VulnCategory(taxonomy="dasp10", category=v["category"])
            for v in entry.get("vulnerabilities", [])
        ]
        items.append(EvalItem(
            contract_id=entry["name"],
            source_dataset="smartbugs_curated",
            code_paths=[code_path],
            ground_truth_label="vulnerable" if categories else "likely_safe",
            vuln_categories=categories,
            severity=None,  # not tracked by this dataset
            meta={
                "pragma": entry.get("pragma"),
                "source_url": entry.get("source"),
                "lines": [v["lines"] for v in entry.get("vulnerabilities", [])],
                "code_path_exists": code_path.exists(),
            },
        ))
    return items
