"""
Access-Control slice — the "hard frontier" benchmark from the ThirdEye plan
(real-world access control: traditional tools get 3-8% recall; GPT-4o-mini
gets high recall but ~951 false positives; precision+recall together is the
open problem).

Why this exists separately from the smartbugs_curated loader: the all-positive
datasets (SmartBugs, Web3Bugs) cannot measure precision for a SPECIFIC vuln
class, because there is no contract that is "vulnerable but NOT in this class"
to act as a negative. This slice fixes that for access control by relabelling
the data into a binary access-control-detection task:

  - POSITIVE (ground_truth_label="vulnerable"): the contract has a confirmed
    access-control vulnerability.
  - NEGATIVE (ground_truth_label="likely_safe"): the contract is vulnerable in
    SOME other way (reentrancy, arithmetic, ...) but has NO access-control bug.
    A system that reports an access-control finding here is producing a real
    false positive — which is exactly the failure mode the AC literature is
    about.

So a tool's precision/recall on THIS slice is precision/recall *for access
control specifically*, with genuine negative-class signal. Sources combined:
SmartBugs-Curated (DASP-10 access_control) + Web3Bugs contests whose bug label
maps to access_control (Code4rena real-world, via eval/taxonomy.py). Web3Bugs
is included only when its clone is present on disk; absence is logged, not
fatal.
"""

from __future__ import annotations

import json

from eval.schema import DATASETS_ROOT, EvalItem, VulnCategory
from eval import taxonomy

SMARTBUGS_ROOT = DATASETS_ROOT / "smartbugs-curated"
WEB3BUGS_ROOT = DATASETS_ROOT / "web3bugs"

AC = "access_control"


def _smartbugs_items() -> list[EvalItem]:
    manifest_path = SMARTBUGS_ROOT / "vulnerabilities.json"
    if not manifest_path.exists():
        return []
    manifest = json.load(open(manifest_path, encoding="utf-8"))

    items = []
    for entry in manifest:
        cats = [v["category"] for v in entry.get("vulnerabilities", [])]
        has_ac = AC in cats
        code_path = SMARTBUGS_ROOT / entry["path"]
        items.append(EvalItem(
            contract_id=f"sb:{entry['name']}",
            source_dataset="access_control_slice",
            code_paths=[code_path],
            ground_truth_label="vulnerable" if has_ac else "likely_safe",
            # Only the AC category is carried as ground truth for this task;
            # the contract's other (non-AC) bugs are irrelevant to AC detection
            # and would pollute the per-category metric if included.
            vuln_categories=[VulnCategory(taxonomy="dasp10", category=AC)] if has_ac else [],
            meta={
                "origin": "smartbugs_curated",
                "all_categories": cats,
                "is_ac_positive": has_ac,
                "code_path_exists": code_path.exists(),
            },
        ))
    return items


def _web3bugs_ac_items() -> list[EvalItem]:
    """Web3Bugs contests whose confirmed bug maps to access_control under the
    DASP-10 bridge. Real-world Code4rena positives. These are positives only
    (Web3Bugs has no negatives), so they add recall signal without affecting
    the negative-class precision signal that SmartBugs provides."""
    import csv

    bugs_csv = WEB3BUGS_ROOT / "results" / "bugs.csv"
    if not bugs_csv.exists():
        print("[access_control_slice] web3bugs clone not present — using SmartBugs AC data only")
        return []

    with open(bugs_csv, encoding="utf-8-sig") as f:
        rows = [{k.strip(): (v.strip() if v else "") for k, v in r.items() if k} for r in csv.DictReader(f)]

    ac_by_contest: dict[str, list[str]] = {}
    for r in rows:
        label = r.get("Bug Label", "")
        if taxonomy.normalize("web3bugs", label) == AC:
            ac_by_contest.setdefault(r["Contest ID"], []).append(label)

    items = []
    for contest_id, labels in ac_by_contest.items():
        project_dir = WEB3BUGS_ROOT / "contracts" / contest_id
        if not project_dir.is_dir():
            continue
        sol_files = sorted(project_dir.rglob("*.sol"))
        if not sol_files:
            continue
        items.append(EvalItem(
            contract_id=f"w3b:{contest_id}",
            source_dataset="access_control_slice",
            code_paths=sol_files,
            ground_truth_label="vulnerable",
            vuln_categories=[VulnCategory(taxonomy="dasp10", category=AC)],
            meta={"origin": "web3bugs", "contest_id": contest_id, "web3bugs_labels": labels},
        ))
    return items


def load() -> list[EvalItem]:
    items = _smartbugs_items() + _web3bugs_ac_items()
    n_pos = sum(1 for it in items if it.ground_truth_label == "vulnerable")
    n_neg = len(items) - n_pos
    print(f"[access_control_slice] {len(items)} items: {n_pos} AC-positive, {n_neg} AC-negative")
    return items
