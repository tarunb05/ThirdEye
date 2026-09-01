#!/usr/bin/env python3
"""
ThirdEye CLI — run the smart-contract auditor council from the terminal / CI.

Usage:
    python argus_cli.py scan <path> [--sarif OUT.sarif] [--json OUT.json]
                                    [--backend ollama|groq] [--seed N]

<path> may be a single .sol file or a directory; a directory is scanned by
concatenating every *.sol file under it (each prefixed with a
`// === <name> ===` header) into one submission, so a whole project is judged
as one unit.

The council (services/council.py) runs 8 model-diverse specialists and a
pure-Python agreement judge, then returns a GO / NO-GO verdict. This wrapper:
  - prints a clean, ANSI-colored terminal report,
  - optionally writes SARIF 2.1.0 (--sarif) and/or the raw council JSON (--json),
  - exits 1 on NO-GO and 0 on GO, so it can be dropped straight into a CI gate.

Standard library only (argparse) — no typer/click — so it runs anywhere the
backend deps (httpx, python-dotenv) are installed. Run it from backend/ so the
`from services.council import run_council` import resolves.
"""

import argparse
import asyncio
import json
import os
import sys

from dotenv import load_dotenv

# Load .env (LLM_BACKEND, GROQ/CEREBRAS keys, OLLAMA_URL, …) BEFORE importing
# council — council reads some of these at import time.
load_dotenv()

from services.council import run_council  # noqa: E402  (must follow load_dotenv)
from services.sarif import to_sarif  # noqa: E402


# ─── ANSI colors (disabled automatically when stdout is not a TTY, e.g. in CI
# logs or when piped, so we never emit escape codes into a captured file). ───

_USE_COLOR = sys.stdout.isatty() and os.getenv("NO_COLOR") is None


def _c(text: str, code: str) -> str:
    if not _USE_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"


def _green(t: str) -> str:
    return _c(t, "1;32")


def _red(t: str) -> str:
    return _c(t, "1;31")


def _yellow(t: str) -> str:
    return _c(t, "1;33")


def _dim(t: str) -> str:
    return _c(t, "2")


def _bold(t: str) -> str:
    return _c(t, "1")


# Per-severity coloring for the vulnerability lines.
_SEVERITY_COLOR = {
    "critical": _red,
    "high": _red,
    "medium": _yellow,
    "low": _dim,
}


def read_source(path: str) -> str:
    """Read the contract source.

    - A single file is read verbatim.
    - A directory is scanned recursively for *.sol files; each is concatenated
      under a `// === <relative name> ===` header so the council sees the whole
      project as one submission (and the header survives into evidence quotes).
    """
    if os.path.isdir(path):
        sol_files = []
        for root, _dirs, files in os.walk(path):
            for name in sorted(files):
                if name.endswith(".sol"):
                    sol_files.append(os.path.join(root, name))
        sol_files.sort()
        if not sol_files:
            raise FileNotFoundError(f"no .sol files found under directory: {path}")
        chunks = []
        for fpath in sol_files:
            rel = os.path.relpath(fpath, path)
            with open(fpath, "r", encoding="utf-8", errors="replace") as fh:
                chunks.append(f"// === {rel} ===\n{fh.read()}")
        return "\n\n".join(chunks)

    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()

    raise FileNotFoundError(f"path not found: {path}")


def print_report(result: dict, path: str) -> None:
    """Render a human-readable terminal report from a council result dict."""
    verdict = result.get("final_verdict", "?")
    stats = result.get("stats", {})
    vulns = result.get("vulnerabilities", []) or []

    print()
    print(_bold("ThirdEye council report"))
    print(_dim(f"  target  : {path}"))
    name = result.get("contract_name") or "(unnamed)"
    print(_dim(f"  contract: {name}"))
    print(_dim(f"  tier    : {stats.get('tier', '?')}  "
               f"models: {', '.join(stats.get('models_used', [])) or '?'}"))
    print()

    # Verdict banner.
    if verdict == "GO":
        print(_green("  VERDICT: GO  ✓") + _dim("  (no finding cleared the agreement bar)"))
    else:
        print(_red("  VERDICT: NO-GO  ✗") + _dim("  (one or more confirmed findings)"))
    print()

    # Confirmed vulnerabilities.
    if vulns:
        print(_bold(f"  Confirmed findings ({len(vulns)}):"))
        for i, v in enumerate(vulns, 1):
            sev = (v.get("severity", "") or "").lower()
            color = _SEVERITY_COLOR.get(sev, lambda t: t)
            conf = v.get("confidence")
            conf_str = f"{conf:.2f}" if isinstance(conf, (int, float)) else "?"
            header = (
                f"  {i}. {color(v.get('type', '?'))}  "
                f"[{color(sev or '?')}]  "
                f"conf={conf_str}  "
                + _dim(f"{v.get('provider', '?')}/{v.get('model', '?')}  "
                       f"{v.get('dynamic_status', '')}")
            )
            print(header)
            evidence = (v.get("evidence_quote") or "").strip()
            if evidence:
                # Indent the (possibly multi-line) evidence under the finding.
                for line in evidence.splitlines() or [evidence]:
                    print(_dim(f"       │ {line}"))
            prop = (v.get("proposed_property") or "").strip()
            if prop:
                print(_dim(f"       property: {prop}"))
            print()
    else:
        print(_dim("  No confirmed findings."))
        print()

    # Raven note + stats footer.
    raven = result.get("raven_note", "")
    if raven:
        print(_bold("  Raven's note:"))
        print(f"    {raven}")
        print()

    print(_dim(
        f"  stats: {stats.get('models_run', '?')} models · "
        f"{stats.get('specialists_run', '?')} specialists run · "
        f"{stats.get('specialists_found', '?')} raised · "
        f"{stats.get('specialists_confirmed', '?')} confirmed"
        + (("  " + _red("[LLM ERROR DETECTED]")) if stats.get("llm_error_detected") else "")
    ))
    print()


def cmd_scan(args: argparse.Namespace) -> int:
    """Handle `scan`. Returns the process exit code (0 GO / 1 NO-GO / 2 error)."""
    try:
        code = read_source(args.path)
    except (FileNotFoundError, OSError) as e:
        print(_red(f"error: {e}"), file=sys.stderr)
        return 2

    if not code.strip():
        print(_red("error: source is empty"), file=sys.stderr)
        return 2

    print(_dim("running council… (8 LLM specialists, this can take ~50s)"), file=sys.stderr)

    result = asyncio.run(run_council(code, backend=args.backend, seed=args.seed))

    print_report(result, args.path)

    # Write outputs if requested.
    if args.sarif:
        # Use the relative path of the scanned file as the SARIF artifact URI so
        # GitHub code-scanning can map results back onto the repo's files.
        sarif = to_sarif(result, source_path=os.path.basename(args.path))
        with open(args.sarif, "w", encoding="utf-8") as fh:
            json.dump(sarif, fh, indent=2)
        print(_dim(f"  wrote SARIF -> {args.sarif}"), file=sys.stderr)

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2)
        print(_dim(f"  wrote JSON  -> {args.json}"), file=sys.stderr)

    # CI gate: NO-GO -> nonzero exit so the pipeline fails on a confirmed finding.
    return 1 if result.get("final_verdict") == "NO-GO" else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="argus_cli.py",
        description="ThirdEye — model-diverse smart-contract auditor council.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser(
        "scan",
        help="scan a .sol file or directory and emit a GO/NO-GO verdict",
        description="Run the council on a contract; exit 1 on NO-GO (CI gate).",
    )
    scan.add_argument("path", help="path to a .sol file or a directory of .sol files")
    scan.add_argument("--sarif", metavar="OUT.sarif", help="write SARIF 2.1.0 to this path")
    scan.add_argument("--json", metavar="OUT.json", help="write the raw council result JSON to this path")
    scan.add_argument(
        "--backend",
        choices=["ollama", "groq"],
        default=None,
        help="LLM tier: 'ollama' (local) or 'groq' (hosted). Default: LLM_BACKEND env.",
    )
    scan.add_argument("--seed", type=int, default=None, help="optional sampling seed for reproducibility")
    scan.set_defaults(func=cmd_scan)

    return parser


def main(argv: list | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
