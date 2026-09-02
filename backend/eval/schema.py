"""
Common internal schema that every dataset loader maps into.

This schema is intentionally file/project-level, not line-level: that's the
granularity the existing analysis pipeline (run_full_analysis) and the
existing Etherscan-50 dataset already operate at, and it's the only
granularity Web3Bugs's bugs.csv actually provides (it names a Contest ID,
not a file or line). SmartBugs-Curated has line-level annotations available
(see its `meta["lines"]`), but nothing currently consumes line-level ground
truth, so it's preserved in `meta` rather than promoted into the schema.

Categories are kept as each dataset's own native taxonomy string, tagged
with which taxonomy they came from (`taxonomy_*`). Cross-dataset category
mapping (e.g. DASP-10 "reentrancy" vs Web3Bugs "L1" vs OWASP categories) is
a deliberately separate, harder design decision and is not done here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASETS_ROOT = REPO_ROOT / "datasets"


@dataclass
class VulnCategory:
    taxonomy: str  # e.g. "dasp10", "web3bugs"
    category: str  # the dataset's own native category code/name


@dataclass
class EvalItem:
    contract_id: str  # unique within source_dataset
    source_dataset: str  # "smartbugs_curated" | "web3bugs" | "etherscan50"
    code_paths: list[Path]  # one path for file-level entries, many for project-level
    ground_truth_label: str  # "vulnerable" | "likely_safe"
    vuln_categories: list[VulnCategory] = field(default_factory=list)
    severity: str | None = None
    meta: dict = field(default_factory=dict)

    def read_code(self) -> str:
        """Concatenate all source files for this item into one string.

        For multi-file projects (Web3Bugs) this is a simple concatenation
        with filename headers, not real import resolution — good enough to
        feed the existing single-string analysis pipeline, not a substitute
        for proper multi-file ingestion (see docs/GAP_ANALYSIS.md).
        """
        parts = []
        for p in self.code_paths:
            try:
                parts.append(f"// === {p.name} ===\n" + p.read_text(encoding="utf-8", errors="ignore"))
            except OSError:
                continue
        return "\n\n".join(parts)

    def read_slices(self, in_scope_only: bool = True):
        """Analyzable units for this item (see eval/slicing.py).

        Single-file items (SmartBugs, the AC slice) return exactly one slice —
        the whole file — so callers can treat single- and multi-file datasets
        uniformly. Multi-file projects (Web3Bugs) return one slice per
        first-party file (and per top-level contract for oversized files),
        which is what makes them analyzable at all instead of one
        uncompilable mega-concatenation.

        in_scope_only drops obvious vendored/test files (OpenZeppelin, mocks,
        forge-std, *.t.sol). For single-file items the filter is never applied
        (one file == the thing under test)."""
        from eval.slicing import slice_paths, is_in_scope

        paths = self.code_paths
        if in_scope_only and len(paths) > 1:
            scoped = [p for p in paths if is_in_scope(p)]
            paths = scoped or paths  # never slice down to nothing
        return slice_paths(paths)
