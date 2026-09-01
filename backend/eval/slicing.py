"""
Slicing — the fix for the Web3Bugs "1/102 analyzable" problem.

The prior approach concatenated every .sol file in a multi-file project into
one string with `// === filename ===` headers and fed that as a single
prompt. That failed two ways: (a) it blew past local context windows on big
projects, and (b) for the Slither baseline the unresolved cross-file imports
never compiled. Result: only 1 of 102 Web3Bugs projects was ever analyzed.

The key realisation: the LLM council does NOT need the project to compile.
It reads source. So we can slice a project into analyzable units — per file,
and per top-level contract within an oversized file — and analyze each unit
independently. A project is then predicted vulnerable if ANY of its slices
is flagged (Web3Bugs ground truth is project-level: a contest is "vulnerable"
if it has >=1 confirmed bug, so any-slice-positive is the matching rule).

This is a lightweight stand-in for the PDF's full UPR (normalized AST + CFG +
call-graph slicing). It is NOT semantic slicing — it does not resolve imports
or follow call edges. It is a pragmatic unit boundary that makes the dataset
analyzable at all, documented as such. Cross-slice data-flow bugs that span
two files can still be missed; that limitation is reported, not hidden.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# A slice larger than this many characters is split further by top-level
# contract/library/interface so no single prompt is enormous. ~24k chars is
# roughly 6-8k tokens of Solidity — comfortably inside a 7B/8B local context
# and well inside the hosted models' windows.
MAX_SLICE_CHARS = 24_000

# Top-level definition header, e.g. "contract Foo is Bar {" / "library L {".
_TOPLEVEL_RE = re.compile(
    r"^\s*(?:abstract\s+)?(contract|library|interface)\s+([A-Za-z_]\w*)",
    re.MULTILINE,
)


@dataclass
class CodeSlice:
    name: str          # human/debug label, e.g. "src/Vault.sol::Vault"
    code: str          # the source text of this slice
    origin_file: str   # the file it came from


def _split_file_by_contract(text: str, file_label: str) -> list[CodeSlice]:
    """Split one file's text at top-level contract/library/interface
    boundaries. The pragma/import preamble before the first definition is
    prepended to every slice so each unit keeps its compiler version and any
    `using` directives in scope for the model to see."""
    matches = list(_TOPLEVEL_RE.finditer(text))
    if len(matches) <= 1:
        return [CodeSlice(name=file_label, code=text, origin_file=file_label)]

    preamble = text[: matches[0].start()].strip()
    slices: list[CodeSlice] = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        name = m.group(2)
        unit = (preamble + "\n\n" + body) if preamble else body
        slices.append(CodeSlice(name=f"{file_label}::{name}", code=unit, origin_file=file_label))
    return slices


def slice_paths(code_paths: list[Path], max_slice_chars: int = MAX_SLICE_CHARS) -> list[CodeSlice]:
    """Turn a list of source files into analyzable slices.

    - One file under the size cap -> one slice (whole file).
    - One file over the cap -> split by top-level contract; any still-oversize
      piece is kept as-is (a single giant contract isn't safely splittable
      without real parsing, so we keep it and let the prompt truncate rather
      than fabricate a boundary).
    """
    slices: list[CodeSlice] = []
    for p in code_paths:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        # Use a repo-relative-ish label: last two path components are enough
        # to disambiguate without leaking absolute machine paths into reports.
        label = "/".join(p.parts[-2:]) if len(p.parts) >= 2 else p.name
        if len(text) <= max_slice_chars:
            slices.append(CodeSlice(name=label, code=text, origin_file=label))
        else:
            slices.extend(_split_file_by_contract(text, label))
    return slices


# Files that are vendored dependencies / test scaffolding, not the audited
# code. Slicing every OpenZeppelin file would balloon the slice count and
# dilute precision with findings in library code the contest didn't scope.
_SKIP_PATH_SUBSTRINGS = (
    "node_modules/", "/lib/", "/mock", "mock/", "/test/", "/tests/",
    ".t.sol", "/openzeppelin", "@openzeppelin", "/forge-std",
)


def is_in_scope(path: Path) -> bool:
    """Heuristic: exclude obvious vendored/test files from slicing. Conservative
    — only excludes well-known dependency/test markers, so first-party code is
    never dropped. Logged by the caller so the exclusion is auditable."""
    s = str(path).replace("\\", "/").lower()
    return not any(marker in s for marker in _SKIP_PATH_SUBSTRINGS)
