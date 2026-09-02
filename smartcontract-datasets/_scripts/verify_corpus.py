#!/usr/bin/env python3
"""Verify that the corpus on disk and the labels in _manifests/ agree.

WHY THIS EXISTS. Every loader in eval/loaders/ already records
`code_path_exists` on each item it produces — and nothing has ever read it. A
labelled contract whose file is missing therefore flows into a benchmark run,
fails to analyse, and is recorded as an abstention or an error rather than as a
broken corpus. That is the project's signature failure mode: the pipeline does
not crash, it silently reports a slightly different number.

The reverse is just as bad. A file sitting in a scored bucket with no row in
labels.jsonl is invisible to every measurement, so the corpus can drift out from
under a published result with nothing to show for it.

And duplicates are worse than either. The same contract under two ids inflates n
and double-counts one verdict, which is benchmark contamination: it moves a rate
without moving anything real.

WHAT IT CHECKS

  1. schema      every labelled row has the required fields, and its bucket,
                 label and tier values are ones the loaders actually accept
  2. missing     every scored row points at a file that exists
  3. orphans     every file in a scored bucket has a labelled row
  4. duplicate   no id appears twice
     ids
  5. duplicate   no two ids point at byte-identical contract source
     content
  6. balance     reports the safe/vulnerable split per bucket and per tier,
                 because a benchmark that has quietly become unbalanced makes
                 precision and recall incomparable to earlier runs

Exit code is 0 when the corpus is clean, 1 when any check fails, and 2 when
there is nothing to check (no manifest) — so CI can distinguish "broken" from
"not present here", which matters because the corpus is gitignored and CI never
has it.

Usage:
    python smartcontract-datasets/_scripts/verify_corpus.py
    python smartcontract-datasets/_scripts/verify_corpus.py --json report.json
    python smartcontract-datasets/_scripts/verify_corpus.py --quiet
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

BENCH_ROOT = Path(__file__).resolve().parents[1]
LABELS = BENCH_ROOT / "_manifests" / "labels.jsonl"

# Mirrors eval/loaders/thirdeye_bench.py::SCORED_BUCKETS. Only these carry a
# ground-truth label that enters an accuracy number; the rest are throughput,
# contest-level or retrieval corpora and are deliberately not checked for
# label coverage.
SCORED_BUCKETS = {"01_safe", "02_vuln_labelled"}
ALL_BUCKETS = SCORED_BUCKETS | {"03_massive_mix", "04_gptscan_web3bugs", "05_similar_exploits"}

REQUIRED_FIELDS = {"id", "bucket", "filepath", "label"}
VALID_LABELS = {"safe", "vulnerable"}
VALID_SAFE_TIERS = {"audited_library", "audit_reviewed_clean", "realworld_no_bug_reported"}
VALID_VULN_TIERS = {"curated", "audit_report"}

CODE_SUFFIXES = {".sol"}


def read_labels() -> list[dict]:
    rows = []
    with open(LABELS, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise SystemExit(f"{LABELS}:{lineno}: not valid JSON — {e}")
    return rows


def check_schema(rows: list[dict]) -> list[str]:
    problems = []
    for i, r in enumerate(rows):
        rid = r.get("id", f"<row {i}, no id>")

        missing = REQUIRED_FIELDS - r.keys()
        if missing:
            problems.append(f"{rid}: missing required field(s) {sorted(missing)}")
            continue

        if r["bucket"] not in ALL_BUCKETS:
            problems.append(f"{rid}: unknown bucket {r['bucket']!r}")

        if r["label"] not in VALID_LABELS:
            problems.append(f"{rid}: label is {r['label']!r}, expected one of {sorted(VALID_LABELS)}")

        # A scored row must carry the tier matching its class — the per-tier
        # false-alarm gradient is the paper's central result and it cannot be
        # computed from rows whose tier is absent or belongs to the other class.
        if r["bucket"] in SCORED_BUCKETS:
            if r.get("label") == "safe":
                tier = r.get("safe_tier")
                if tier is None:
                    problems.append(f"{rid}: safe row has no safe_tier")
                elif tier not in VALID_SAFE_TIERS:
                    problems.append(f"{rid}: unknown safe_tier {tier!r}")
                if r.get("vuln_tier"):
                    problems.append(f"{rid}: safe row also carries vuln_tier {r['vuln_tier']!r}")
            elif r.get("label") == "vulnerable":
                tier = r.get("vuln_tier")
                if tier is None:
                    problems.append(f"{rid}: vulnerable row has no vuln_tier")
                elif tier not in VALID_VULN_TIERS:
                    problems.append(f"{rid}: unknown vuln_tier {tier!r}")
                if not r.get("vuln_types"):
                    problems.append(f"{rid}: vulnerable row has no vuln_types")

        # A safe row asserting vulnerabilities is a contradiction, not a warning.
        if r.get("label") == "safe" and r.get("vuln_types"):
            problems.append(f"{rid}: labelled safe but lists vuln_types {r['vuln_types']}")

    return problems


def check_missing_files(rows: list[dict]) -> list[str]:
    out = []
    for r in rows:
        if r.get("bucket") not in SCORED_BUCKETS:
            continue
        fp = r.get("filepath")
        if not fp:
            continue
        if not (BENCH_ROOT / fp).exists():
            out.append(f"{r.get('id')}: labelled but file absent — {fp}")
    return out


def check_orphans(rows: list[dict]) -> list[str]:
    labelled = {r["filepath"] for r in rows if r.get("filepath")}
    out = []
    for bucket in sorted(SCORED_BUCKETS):
        bdir = BENCH_ROOT / bucket
        if not bdir.exists():
            continue
        for f in sorted(bdir.rglob("*")):
            if not f.is_file() or f.suffix.lower() not in CODE_SUFFIXES:
                continue
            rel = str(f.relative_to(BENCH_ROOT))
            if rel not in labelled:
                out.append(f"unlabelled file in a scored bucket — {rel}")
    return out


def check_duplicate_ids(rows: list[dict]) -> list[str]:
    seen = Counter(r["id"] for r in rows if r.get("id"))
    return [f"id {rid!r} appears {n} times" for rid, n in sorted(seen.items()) if n > 1]


def check_duplicate_content(rows: list[dict]) -> list[str]:
    by_hash: dict[str, list[str]] = defaultdict(list)
    for r in rows:
        if r.get("bucket") not in SCORED_BUCKETS or not r.get("filepath"):
            continue
        p = BENCH_ROOT / r["filepath"]
        if not p.exists():
            continue  # already reported by check_missing_files
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        by_hash[h].append(r["id"])

    out = []
    for h, ids in sorted(by_hash.items()):
        if len(ids) > 1:
            out.append(f"identical source under {len(ids)} ids: {', '.join(sorted(ids))} (sha256 {h[:12]})")
    return out


def balance(rows: list[dict]) -> dict:
    per_bucket: dict[str, Counter] = defaultdict(Counter)
    per_tier: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        if r.get("bucket") not in SCORED_BUCKETS:
            continue
        label = r.get("label", "?")
        per_bucket[r["bucket"]][label] += 1
        tier = r.get("safe_tier") or r.get("vuln_tier") or "<no tier>"
        per_tier[tier][label] += 1
    return {
        "per_bucket": {k: dict(v) for k, v in sorted(per_bucket.items())},
        "per_tier": {k: dict(v) for k, v in sorted(per_tier.items())},
    }


CHECKS = [
    ("schema", check_schema),
    ("missing files", check_missing_files),
    ("orphan files", check_orphans),
    ("duplicate ids", check_duplicate_ids),
    ("duplicate content", check_duplicate_content),
]


def run() -> tuple[dict, bool]:
    rows = read_labels()
    report = {"n_rows": len(rows), "checks": {}, "balance": balance(rows)}
    ok = True
    for name, fn in CHECKS:
        problems = fn(rows)
        report["checks"][name] = problems
        if problems:
            ok = False
    return report, ok


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", metavar="PATH", help="write the full report as JSON")
    ap.add_argument("--quiet", action="store_true", help="only print failures")
    ap.add_argument("--max-listed", type=int, default=10,
                    help="how many examples to print per failing check (default 10)")
    args = ap.parse_args()

    if not LABELS.exists():
        print(f"no manifest at {LABELS}")
        print("The corpus is gitignored — see docs/DATASETS.md for how to populate it.")
        return 2

    report, ok = run()

    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2))

    if not args.quiet:
        print(f"{report['n_rows']} labelled rows\n")
        print("balance (scored buckets only)")
        for bucket, counts in report["balance"]["per_bucket"].items():
            print(f"  {bucket:<20} {counts}")
        for tier, counts in report["balance"]["per_tier"].items():
            print(f"    {tier:<28} {counts}")
        print()

    for name, problems in report["checks"].items():
        if problems:
            print(f"FAIL  {name} — {len(problems)} problem(s)")
            for p in problems[:args.max_listed]:
                print(f"        {p}")
            if len(problems) > args.max_listed:
                print(f"        …and {len(problems) - args.max_listed} more")
        elif not args.quiet:
            print(f"ok    {name}")

    if ok:
        if not args.quiet:
            print("\ncorpus and labels agree")
        return 0
    print("\ncorpus does NOT match its labels — fix before trusting any number produced from it")
    return 1


if __name__ == "__main__":
    sys.exit(main())
