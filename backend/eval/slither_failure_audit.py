"""Classify Slither's abstentions: genuinely unbuildable, or our misconfiguration?

WHY THIS EXISTS. The Slither head-to-head is one of only two like-for-like
comparisons in the paper, and it currently reports an UPPER BOUND: Slither scored
46 of 150 sampled contracts and the other 104 were compile failures. Some
unknown fraction of those is our own solc version resolution rather than a
property of the contract, so "Slither covers 30.7%" cannot be claimed outright.
This measures the split.

WHY IT ASKS SOLC RATHER THAN SLITHER. Slither fails SILENTLY on these: run
directly on a failing contract it exits 0 with empty stdout AND empty stderr, so
`run_slither` records the bare status string "error" and the actual reason is
lost. (Its own source comments describe this: crytic-compile's exception is
swallowed by the --json redirect.) solc, given the same file, says exactly what
went wrong in one line. So the diagnosis comes from the compiler.

WHICH CONTRACTS. run_slither_bench uses a deterministic nested stratified sample
and checkpoints only the contracts that SCORED. So the sample can be regenerated
with the same seed, and the failures are exactly sample-minus-checkpoints — no
Slither re-run is needed, and the audit covers precisely the contracts the
published coverage number was computed on.

THE CLASSIFICATION, and which way each cuts:

  OURS    the solc version could not be resolved, installed, or satisfies no
          pragma we can obtain. Our problem; must NOT count against Slither.

  CORPUS  the contract genuinely does not build standalone because it imports
          files that are not present — it is a fragment of a multi-file project.
          A real limit on running any static analyser over a single-file corpus,
          but a property of the CORPUS as much as of Slither, so it is reported
          as its own category and folded into neither side.

  HARD    a real Solidity error in the source as given.
"""
from __future__ import annotations
import argparse, json, os, random, re, subprocess, sys, time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from eval.loaders import thirdeye_bench
from eval.schema import REPO_ROOT
from eval.run_benchmark import TIERS

OUT = REPO_ROOT / "backend" / "eval" / "results"
BENCH_CK = REPO_ROOT / "backend" / "eval" / "checkpoints" / "slither_bench"
CK = REPO_ROOT / "backend" / "eval" / "checkpoints" / "slither_audit"

# First match wins; ordered most specific first.
RULES = [
    ("CORPUS: missing import (multi-file project)",
     r'not found:\s*File not found|Source ".*" not found|File not found|'
     r'Source not found|could not be found'),
    ("OURS: pragma unsatisfiable with installed solc",
     r"requires different compiler version|Source file requires|"
     r"different compiler version"),
    ("OURS: solc unavailable",
     r"not available|failed to install|no such version|unknown version|"
     r"solc-select|SolcNotInstalled"),
    ("HARD: solidity compile error",
     r"ParserError|SyntaxError|DeclarationError|TypeError|CompilerError|"
     r"Expected |Identifier not found|UnimplementedFeature|Error: "),
    ("timeout", r"timeout|timed out"),
]


def classify(err: str) -> str:
    e = (err or "").strip()
    if not e:
        return "unknown (compiler said nothing)"
    for label, pat in RULES:
        if re.search(pat, e, re.I):
            return label
    return "other"


def _solc_exe() -> str:
    return str(Path(sys.executable).parent / "solc.exe"
               if os.name == "nt" else Path(sys.executable).parent / "solc")


def diagnose(code: str, workdir: Path) -> tuple[bool, str]:
    """Compile the single file with solc and return (ok, first_error_line)."""
    from services.slither import _detect_solc_version, _ensure_solc_version
    f = workdir / "audit_probe.sol"
    f.write_text(code, encoding="ascii", errors="ignore")
    env = os.environ.copy()
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
    v = None
    try:
        v = _detect_solc_version(code)
        if v:
            _ensure_solc_version(v)
            env["SOLC_VERSION"] = v
    except Exception as e:
        return False, f"OURS: solc unavailable — {e}"
    try:
        r = subprocess.run([_solc_exe(), "--bin", f.name],
                           capture_output=True, text=True, timeout=90,
                           cwd=str(workdir), env=env)
    except subprocess.TimeoutExpired:
        return False, "timed out"
    except FileNotFoundError:
        return False, "OURS: solc unavailable — binary not found"
    finally:
        try:
            f.unlink()
        except Exception:
            pass
    if r.returncode == 0:
        return True, ""
    msg = (r.stderr or r.stdout or "").strip()
    first = next((ln for ln in msg.splitlines() if ln.strip()), "")
    return False, (first or msg)[:300]


def sample_ids() -> list[tuple[str, str, str]]:
    """Regenerate the identical nested stratified sample run_slither_bench used."""
    out = []
    for bucket, tier, expected in TIERS:
        items = thirdeye_bench.load(buckets={bucket}, tier=tier)
        items = [it for it in items if it.code_paths and it.code_paths[0].exists()]
        rng = random.Random(f"0:{bucket}:{tier}")
        items = list(items)
        rng.shuffle(items)
        for it in items[:25]:
            out.append((it.contract_id, tier, bucket))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="cap failures to diagnose")
    ap.add_argument("--report-only", action="store_true")
    a = ap.parse_args()

    CK.mkdir(parents=True, exist_ok=True)
    scored = {p.stem for p in BENCH_CK.glob("*.json")}
    samp = sample_ids()
    by_id = {cid: (tier, bucket) for cid, tier, bucket in samp}
    failures = [cid for cid, _, _ in samp if cid not in scored]
    print(f"sample {len(samp)} · scored by Slither {len(samp)-len(failures)} · "
          f"abstained {len(failures)}")

    rows = []
    if not a.report_only:
        work = REPO_ROOT / "backend" / "eval" / "_audit_tmp"
        work.mkdir(parents=True, exist_ok=True)
        src = {}
        for it in thirdeye_bench.load():
            if it.contract_id in by_id:
                src[it.contract_id] = it
        todo = failures[: a.limit] if a.limit else failures
        for i, cid in enumerate(todo, 1):
            cp = CK / f"{cid}.json"
            if cp.exists():
                rows.append(json.load(open(cp, encoding="utf-8")))
                continue
            it = src.get(cid)
            if it is None:
                continue
            t0 = time.time()
            try:
                ok, err = diagnose(it.read_code(), work)
            except Exception as e:
                ok, err = False, f"audit error: {e}"
            row = {"contract_id": cid, "tier": by_id[cid][0], "bucket": by_id[cid][1],
                   "solc_ok": ok, "error": err, "category": "compiles under solc" if ok
                   else classify(err), "latency_s": round(time.time() - t0, 1)}
            json.dump(row, open(cp, "w"), indent=1)
            rows.append(row)
            print(f"  [{i}/{len(todo)}] {row['category']:<44} {cid[:40]}", flush=True)
    else:
        for f in sorted(CK.glob("*.json")):
            try:
                rows.append(json.load(open(f, encoding="utf-8")))
            except Exception:
                continue

    if not rows:
        print("nothing audited yet")
        return

    cats = Counter(r["category"] for r in rows)
    print(f"\n=== SLITHER ABSTENTION AUDIT ===")
    print(f"abstentions diagnosed    {len(rows)} of {len(failures)}")
    print("\nby cause:")
    ours = corpus = hard = other = 0
    for k, v in cats.most_common():
        print(f"  {k:<46} {v:>4}  ({100*v/len(rows):.1f}%)")
        if k.startswith("OURS"):
            ours += v
        elif k.startswith("CORPUS"):
            corpus += v
        elif k.startswith("HARD"):
            hard += v
        else:
            other += v

    n_sample, n_scored = len(samp), len(samp) - len(failures)
    # Scale the diagnosed split up to all abstentions if only a subset was run.
    frac_ours = ours / len(rows)
    est_ours = round(frac_ours * len(failures))
    print(f"\nOURS (toolchain)         {ours}   -> ~{est_ours} of {len(failures)} abstentions")
    print(f"CORPUS (needs its project) {corpus}")
    print(f"HARD (real source error) {hard}")
    print(f"other/unknown            {other}")

    print(f"\nSlither coverage, raw                {n_scored}/{n_sample} = "
          f"{100*n_scored/n_sample:.1f}%")
    den = n_sample - est_ours
    if den > 0:
        print(f"Slither coverage, our faults removed {n_scored}/{den} = "
              f"{100*n_scored/den:.1f}%")
    print("\nThe second figure is the defensible one. Contracts we could not build")
    print("for reasons that are not Slither's are removed from the denominator")
    print("rather than counted as its failures.")

    bt = defaultdict(Counter)
    for r in rows:
        bt[r["tier"]][r["category"].split(":")[0]] += 1
    print("\nabstention causes by tier:")
    for t, c in sorted(bt.items()):
        print(f"  {t:<30} " + "  ".join(f"{k}={v}" for k, v in c.most_common()))

    OUT.mkdir(parents=True, exist_ok=True)
    json.dump({"sample": n_sample, "scored": n_scored, "abstained": len(failures),
               "diagnosed": len(rows), "by_cause": dict(cats),
               "ours": ours, "ours_estimated_total": est_ours,
               "corpus": corpus, "hard": hard, "rows": rows},
              open(OUT / "slither_failure_audit.json", "w"), indent=1)
    print(f"\nwrote {OUT / 'slither_failure_audit.json'}")


if __name__ == "__main__":
    main()
