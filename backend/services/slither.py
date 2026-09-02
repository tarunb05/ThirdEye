import json, re, subprocess, tempfile, os, sys
from pathlib import Path


def _resolve_slither_executable() -> str:
    """Bare "slither" only resolves via PATH if this venv's Scripts/bin dir
    happens to be on it (true when activated, false for a subprocess that
    just runs venv/Scripts/python.exe directly — which is how this app is
    actually invoked both in dev and via Render's start command). Resolve
    relative to the running interpreter instead, falling back to PATH
    lookup for a system-wide install."""
    venv_bin = Path(sys.executable).parent
    for candidate in (venv_bin / "slither.exe", venv_bin / "slither"):
        if candidate.exists():
            return str(candidate)
    return "slither"


_PRAGMA_RE = re.compile(r"pragma\s+solidity\s+([^;]+);")
_VERSION_RE = re.compile(r"\d+\.\d+\.\d+")
_solc_install_attempted: set[str] = set()


def _detect_solc_version(code: str) -> str | None:
    """Only one solc version is installed by default (whatever solc-select's
    own default is) — contracts targeting a different Solidity version fail
    to compile, which Slither reports as a silent empty result rather than
    a loud error. Pull a concrete version out of the pragma line(s); range
    pragmas (^0.8.0, >=0.5.0 <0.7.0) all contain at least one.

    Flattened/verified Etherscan sources inline their imports (e.g.
    OpenZeppelin) ahead of the actual contract, each with their own
    permissive lower-bound pragma (">=0.4.16", ">=0.6.2", ...) — the FIRST
    pragma in the file is therefore usually the import's, not the contract's.
    Taking the max version across every pragma line is the simpler fix:
    imports' lower bounds are always <= the contract's actual requirement
    in practice, so the highest version found is the one that needs to
    compile the whole file."""
    versions = [
        v.group(0)
        for m in _PRAGMA_RE.finditer(code)
        if (v := _VERSION_RE.search(m.group(1)))
    ]
    if not versions:
        return None
    return max(versions, key=lambda v: tuple(int(p) for p in v.split(".")))


def _ensure_solc_version(version: str) -> None:
    """solc-select only knows about compilers actually downloaded to disk.
    Install on demand — cached permanently under ~/.solc-select, a no-op if
    already present — rather than failing every contract that doesn't match
    whichever version happened to be installed first."""
    if version in _solc_install_attempted:
        return
    _solc_install_attempted.add(version)
    try:
        from solc_select.solc_select import installed_versions, install_artifacts
        if version not in installed_versions():
            install_artifacts([version], silent=True)
    except Exception:
        pass  # fall through — Slither will surface its own compile error


def run_slither(code: str) -> dict:
    try:
        # Non-ASCII characters in source comments (smart quotes, etc. —
        # common in copy-pasted Etherscan-verified source) survive being
        # written as UTF-8 but can come back out of solc's own --json
        # output mangled into invalid UTF-8 byte sequences on Windows,
        # which crashes crytic-compile's json parser before Slither even
        # runs. Solidity syntax itself is pure ASCII; only comments/docs
        # ever contain non-ASCII, so dropping it is harmless for analysis.
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sol", delete=False, encoding="ascii", errors="ignore") as f:
            f.write(code)
            p = f.name

        env = os.environ.copy()
        # Slither shells out to a bare "solc", which solc-select resolves
        # via its own shim — but that shim only resolves if this venv's
        # Scripts/bin dir is on PATH, which it isn't when this process was
        # launched by invoking venv python directly (no `activate` sourced).
        venv_bin = str(Path(sys.executable).parent)
        env["PATH"] = venv_bin + os.pathsep + env.get("PATH", "")
        version = _detect_solc_version(code)
        if version:
            _ensure_solc_version(version)
            env["SOLC_VERSION"] = version

        # Pass a relative filename with cwd set to its directory, not the
        # absolute path. Newer solc Windows builds (confirmed: 0.8.27) emit
        # their own internal source path without the drive letter
        # ("/Users/..." instead of "C:/Users/..."), which trips a
        # crytic-compile Windows path-fixup heuristic that assumes the
        # first segment after a leading slash IS the drive letter — it
        # mangles the filename, fails to find it on disk, and raises
        # InvalidCompilation. Slither's own --json-to-stdout redirect
        # swallows that exception's traceback entirely, so this surfaced
        # as a silent empty stdout/stderr with no error message at all.
        # A relative filename sidesteps the heuristic completely (solc
        # echoes back the same relative path, no leading slash involved).
        temp_dir = str(Path(p).parent)
        temp_name = Path(p).name
        result = subprocess.run(
            [_resolve_slither_executable(), temp_name, "--json", "-"],
            capture_output=True, text=True, timeout=30, env=env, cwd=temp_dir,
        )
        os.unlink(p)
        # Slither's CLI exits 1 whenever any detector fires — that's success
        # WITH findings, not a failure. Trust stdout whenever it's valid
        # JSON regardless of exit code; only treat it as an error (compile
        # failure, wrong solc version, etc.) when stdout isn't JSON at all.
        try:
            json.loads(result.stdout)
            return {"status": "completed", "output": result.stdout, "return_code": result.returncode}
        except (json.JSONDecodeError, ValueError):
            return {"status": "error", "message": result.stderr or result.stdout, "return_code": result.returncode}
    except FileNotFoundError:
        return {"status": "skipped", "message": "Slither not installed (optional)"}
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "Slither timed out"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
