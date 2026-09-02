"""
Loader for the existing 50-contract Etherscan-verified set
(backend/datasets/index.json + backend/datasets/etherscan_verified/*.sol), wrapped
into the common schema so the new metrics module can run against data
whose shape is already understood — used only as a sanity check on the
metrics math itself (see docs/GAP_ANALYSIS.md and the Phase 0 task), not
as a real evaluation result.

Ground truth here (`auto_label`) is heuristic/scraped, not expert-verified
— several entries' own `notes` field says "vulnerabilities not checked
yet". That caveat is preserved in meta, not fixed here: fixing the ground
truth itself is a separate decision, not a loader's job.
"""

from __future__ import annotations

import json

from eval.schema import REPO_ROOT, EvalItem, VulnCategory

INDEX_PATH = REPO_ROOT / "backend" / "datasets" / "index.json"
SOL_ROOT = REPO_ROOT / "backend" / "datasets" / "etherscan_verified"


def load() -> list[EvalItem]:
    with open(INDEX_PATH, encoding="utf-8") as f:
        data = json.load(f)

    items = []
    for entry in data.get("contracts", []):
        code_path = SOL_ROOT / entry["filename"]
        categories = [
            VulnCategory(taxonomy="etherscan50_auto", category=vt)
            for vt in entry.get("vuln_types", [])
        ]
        items.append(EvalItem(
            contract_id=entry["id"],
            source_dataset="etherscan50",
            code_paths=[code_path],
            ground_truth_label=entry.get("auto_label", "unknown"),
            vuln_categories=categories,
            severity=entry.get("expected_severity"),
            meta={
                "contract_name": entry.get("contract_name"),
                "etherscan_address": entry.get("etherscan_address"),
                "report_url": entry.get("report_url"),
                "solidity_version": entry.get("solidity_version"),
                "notes": entry.get("notes"),
                "code_path_exists": code_path.exists(),
            },
        ))
    return items
