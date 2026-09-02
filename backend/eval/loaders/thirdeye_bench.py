"""
Loader for the ThirdEye evaluation benchmark (smartcontract-datasets/).

This is the real, balanced benchmark (2,250 scored contracts, 1,125 safe :
1,125 vulnerable) described in the dataset overview. Unlike the earlier
all-positive sets, it has a genuine SAFE bucket (audited OpenZeppelin/Solady,
audit-reviewed-clean, real no-bug-reported protocol files) — so precision and
false-positive rate are finally measurable, and a well-audited safe contract
SHOULD come back GO.

Ground truth lives in _manifests/labels.jsonl (one row per scored contract):
  {id, source_dataset, bucket, filepath, language, label ("safe"|"vulnerable"),
   vuln_types[], vuln_lines[], origin_ref, label_quality, safe_tier|vuln_tier}

Only the two SCORED buckets are loaded here (01_safe, 02_vuln_labelled). The
unscored buckets (03_massive_mix throughput, 04_gptscan_web3bugs contest-level,
05_similar_exploits retrieval corpus) are handled separately, never mixed into
accuracy numbers.
"""

from __future__ import annotations

import json

from eval.schema import REPO_ROOT, EvalItem, VulnCategory

BENCH_ROOT = REPO_ROOT / "smartcontract-datasets"
LABELS = BENCH_ROOT / "_manifests" / "labels.jsonl"

SCORED_BUCKETS = {"01_safe", "02_vuln_labelled"}


def _read_labels() -> list[dict]:
    if not LABELS.exists():
        print(f"[thirdeye_bench] labels not found at {LABELS} — is smartcontract-datasets/ present?")
        return []
    rows = []
    with open(LABELS, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load(buckets: set[str] | None = None, tier: str | None = None, limit_per_label: int | None = None) -> list[EvalItem]:
    """Load scored contracts as EvalItems.

    buckets: restrict to a subset (default: both scored buckets).
    tier: restrict to a trust tier (e.g. "audited_library", "curated",
          "audit_report", "audit_reviewed_clean") — for headline-on-highest-
          trust reporting.
    limit_per_label: cap safe/vulnerable each (for fast balanced samples).
    """
    buckets = buckets or SCORED_BUCKETS
    rows = [r for r in _read_labels() if r.get("bucket") in buckets]

    items: list[EvalItem] = []
    n_by_label = {"safe": 0, "vulnerable": 0}
    for r in rows:
        row_tier = r.get("safe_tier") or r.get("vuln_tier")
        if tier and row_tier != tier:
            continue
        label = r.get("label", "")
        gt = "vulnerable" if label == "vulnerable" else "likely_safe"
        if limit_per_label is not None and n_by_label.get(label, 0) >= limit_per_label:
            continue
        n_by_label[label] = n_by_label.get(label, 0) + 1

        code_path = BENCH_ROOT / r["filepath"]
        categories = [VulnCategory(taxonomy="dasp10", category=c) for c in (r.get("vuln_types") or [])]
        items.append(EvalItem(
            contract_id=r["id"],
            source_dataset="thirdeye_bench",
            code_paths=[code_path],
            ground_truth_label=gt,
            vuln_categories=categories,
            severity=None,
            meta={
                "bucket": r.get("bucket"),
                "tier": row_tier,
                "label_quality": r.get("label_quality"),
                "origin": r.get("source_dataset"),
                "origin_ref": r.get("origin_ref"),
                "vuln_lines": r.get("vuln_lines") or [],
                "code_path_exists": code_path.exists(),
            },
        ))
    return items


def load_safe(**kw) -> list[EvalItem]:
    return load(buckets={"01_safe"}, **kw)


def load_vuln(**kw) -> list[EvalItem]:
    return load(buckets={"02_vuln_labelled"}, **kw)


def load_balanced(n_per_label: int, tier: str | None = None) -> list[EvalItem]:
    """A balanced n:n safe:vulnerable sample — the right shape for measuring
    precision AND recall together (the project's core claim)."""
    return load_safe(limit_per_label=n_per_label, tier=tier) + load_vuln(limit_per_label=n_per_label, tier=tier)
