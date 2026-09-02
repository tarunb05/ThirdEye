"""Corpus/label agreement — the check nothing was doing.

Every loader in eval/loaders/ records `code_path_exists` on the items it
produces, and until now nothing read it. A labelled contract whose file is
missing therefore reached a benchmark run, failed to analyse, and was recorded
as an abstention rather than as a broken corpus — the project's signature
failure mode, where the pipeline does not crash but the number quietly moves.

These tests exercise the checker in
`smartcontract-datasets/_scripts/verify_corpus.py` against synthetic fixtures,
so they run in CI where the real corpus is absent (it is gitignored). The last
test runs the checker against the real corpus if one happens to be present, and
skips otherwise.
"""
import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CHECKER = REPO_ROOT / "smartcontract-datasets" / "_scripts" / "verify_corpus.py"


def load_checker(bench_root: Path):
    """Import verify_corpus with BENCH_ROOT pointed at a fixture directory."""
    spec = importlib.util.spec_from_file_location(f"verify_corpus_{id(bench_root)}", CHECKER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.BENCH_ROOT = bench_root
    mod.LABELS = bench_root / "_manifests" / "labels.jsonl"
    return mod


def build_corpus(tmp_path: Path, rows: list[dict], files: dict[str, str]) -> Path:
    """Write a fixture corpus: labels.jsonl plus contract files."""
    root = tmp_path / "corpus"
    (root / "_manifests").mkdir(parents=True)
    with open(root / "_manifests" / "labels.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    return root


SAFE = {
    "id": "safe-001",
    "bucket": "01_safe",
    "filepath": "01_safe/audited_library/A.sol",
    "label": "safe",
    "safe_tier": "audited_library",
    "vuln_types": [],
}
VULN = {
    "id": "vuln-001",
    "bucket": "02_vuln_labelled",
    "filepath": "02_vuln_labelled/curated/B.sol",
    "label": "vulnerable",
    "vuln_tier": "curated",
    "vuln_types": ["reentrancy"],
}
FILES = {
    "01_safe/audited_library/A.sol": "contract A { }\n",
    "02_vuln_labelled/curated/B.sol": "contract B { function f() public { } }\n",
}


def test_clean_corpus_passes(tmp_path):
    root = build_corpus(tmp_path, [SAFE, VULN], FILES)
    report, ok = load_checker(root).run()
    assert ok, report["checks"]
    assert report["n_rows"] == 2


def test_missing_file_is_caught(tmp_path):
    """The exact case `code_path_exists` was computing and nobody was reading."""
    root = build_corpus(tmp_path, [SAFE, VULN],
                        {k: v for k, v in FILES.items() if "A.sol" not in k})
    report, ok = load_checker(root).run()
    assert not ok
    assert any("safe-001" in p for p in report["checks"]["missing files"])


def test_orphan_file_is_caught(tmp_path):
    """A contract sitting in a scored bucket with no label is invisible to every
    measurement — the corpus can drift without anything showing it."""
    files = dict(FILES)
    files["01_safe/audited_library/Unlabelled.sol"] = "contract U { }\n"
    root = build_corpus(tmp_path, [SAFE, VULN], files)
    report, ok = load_checker(root).run()
    assert not ok
    assert any("Unlabelled.sol" in p for p in report["checks"]["orphan files"])


def test_duplicate_id_is_caught(tmp_path):
    root = build_corpus(tmp_path, [SAFE, SAFE, VULN], FILES)
    report, ok = load_checker(root).run()
    assert not ok
    assert any("safe-001" in p for p in report["checks"]["duplicate ids"])


def test_duplicate_content_is_caught(tmp_path):
    """Benchmark contamination: the same contract under two ids inflates n and
    double-counts one verdict, moving a published rate without moving anything
    real."""
    twin = dict(SAFE, id="safe-002", filepath="01_safe/audited_library/A_copy.sol")
    files = dict(FILES)
    files["01_safe/audited_library/A_copy.sol"] = FILES["01_safe/audited_library/A.sol"]
    root = build_corpus(tmp_path, [SAFE, twin, VULN], files)
    report, ok = load_checker(root).run()
    assert not ok
    dups = report["checks"]["duplicate content"]
    assert dups and "safe-001" in dups[0] and "safe-002" in dups[0]


def test_safe_row_claiming_vulnerabilities_is_caught(tmp_path):
    bad = dict(SAFE, vuln_types=["reentrancy"])
    root = build_corpus(tmp_path, [bad, VULN], FILES)
    report, ok = load_checker(root).run()
    assert not ok
    assert any("labelled safe but lists vuln_types" in p for p in report["checks"]["schema"])


def test_missing_tier_is_caught(tmp_path):
    """The per-tier false-alarm gradient is the paper's central result. It cannot
    be computed from rows whose tier is absent, so an untiered scored row is a
    failure rather than a warning."""
    bad = dict(SAFE)
    del bad["safe_tier"]
    root = build_corpus(tmp_path, [bad, VULN], FILES)
    report, ok = load_checker(root).run()
    assert not ok
    assert any("no safe_tier" in p for p in report["checks"]["schema"])


def test_unknown_tier_is_caught(tmp_path):
    bad = dict(SAFE, safe_tier="probably_fine")
    root = build_corpus(tmp_path, [bad, VULN], FILES)
    report, ok = load_checker(root).run()
    assert not ok
    assert any("unknown safe_tier" in p for p in report["checks"]["schema"])


def test_balance_is_reported_per_tier(tmp_path):
    root = build_corpus(tmp_path, [SAFE, VULN], FILES)
    report, _ = load_checker(root).run()
    assert report["balance"]["per_bucket"]["01_safe"] == {"safe": 1}
    assert report["balance"]["per_tier"]["audited_library"] == {"safe": 1}
    assert report["balance"]["per_tier"]["curated"] == {"vulnerable": 1}


@pytest.mark.skipif(
    not (REPO_ROOT / "smartcontract-datasets" / "_manifests" / "labels.jsonl").exists(),
    reason="real corpus not present (gitignored); fixtures above cover the logic",
)
def test_real_corpus_matches_its_labels():
    """Runs only where someone has actually populated the corpus."""
    mod = load_checker(REPO_ROOT / "smartcontract-datasets")
    report, ok = mod.run()
    assert ok, {k: v[:5] for k, v in report["checks"].items() if v}
