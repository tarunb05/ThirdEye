"""Bucket 04 — Web3Bugs / GPTScan comparison set.

This is the headline benchmark the project has always pointed at and never run:
real Code4rena audit contests on real DeFi protocols, where the bugs are
*semantic* (price manipulation, broken accounting, flawed access logic) rather
than the pattern-matchable classes in buckets 01/02.

It works differently from the per-file benchmark, and the differences matter:

  * GRANULARITY IS THE CONTEST, NOT THE FILE. A Web3Bugs finding points at a
    whole protocol codebase, not a file and line. So a contest counts as
    detected if ANY of its slices is flagged — "any-slice-positive". That is
    generous by construction and we say so rather than hiding it.

  * THERE IS NO SAFE CLASS. Every contest here has at least one confirmed bug,
    so this set measures RECALL ONLY. Precision is meaningless on it — which is
    exactly the property that lets all-positive benchmarks flatter a tool, the
    thing this project has spent its time documenting. False-positive rate stays
    measured on the balanced buckets 01/02, never here.

  * COST IS THE BINDING CONSTRAINT. 102 contests slice to ~3,757 units: roughly
    209 hours locally or 26 hours hosted, and the hosted daily token budget is
    far below that. So we sample contests (seeded, nested, like run_benchmark)
    and cap slices per contest, then report the n we actually ran.

ON CLAIMING A GPTScan COMPARISON: GPTScan reports against its own evaluated
subset of Web3Bugs, not all 300 S-class bugs. Recall computed here over a
different subset is NOT directly comparable to their published figure, and this
script does not pretend otherwise. Treat the number as "our recall on real
audit-contest logic bugs" until the exact GPTScan subset is pinned.

Usage:
    python -m eval.run_web3bugs --contests 20 --max-slices 25 --backend ollama
    python -m eval.run_web3bugs --report-only
"""
from __future__ import annotations

import argparse, asyncio, json, os, random, statistics, time
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from eval.loaders import web3bugs
from eval.slicing import slice_paths, is_in_scope
from eval.schema import REPO_ROOT

CKPT = REPO_ROOT / "backend" / "eval" / "checkpoints" / "web3bugs"
RESULTS = REPO_ROOT / "backend" / "eval" / "results"
FINDINGS = REPO_ROOT / "smartcontract-datasets" / "_manifests" / "web3bugs_findings.jsonl"


def s_class_by_contest() -> dict[str, list[dict]]:
    """The 300 semantic/logic bugs, grouped by contest. These are GPTScan's
    target class and the only ones we score."""
    out: dict[str, list[dict]] = {}
    if not FINDINGS.exists():
        return out
    with open(FINDINGS, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r.get("label_class") == "S":
                out.setdefault(str(r.get("contest_id")), []).append(r)
    return out


async def scan_contest(item, max_slices: int, backend: str, seed: int, concurrency: int = 1) -> dict:
    """Run the pipeline over a contest's slices; contest is detected if ANY
    slice comes back NO-GO."""
    from services.pipeline import run_thirdeye
    from services import council

    in_scope = [p for p in item.code_paths if is_in_scope(p)]
    slices = slice_paths(in_scope)
    dropped = len(item.code_paths) - len(in_scope)
    if max_slices and len(slices) > max_slices:
        # Deterministic subset, so a re-run scans the same slices.
        rng = random.Random(f"{seed}:{item.contract_id}")
        slices = rng.sample(slices, max_slices)

    t0 = time.time()
    before = council.get_api_call_count()["total"]
    flagged, errored, per_slice = [], 0, []
    sem = asyncio.Semaphore(max(1, concurrency))

    async def one(sl):
        async with sem:
            try:
                res = await run_thirdeye(
                    sl.code, backend=backend, seed=seed,
                    use_static_router=True, use_retrieval=False,
                    use_arbitration=False, use_dynamic=False,
                )
                v = res.get("final_verdict")
                types = sorted({(x or {}).get("type") for x in (res.get("vulnerabilities") or [])} - {None})
                return {"slice": sl.name, "verdict": v, "types": types}
            except Exception as e:  # one bad slice must not kill a contest
                return {"slice": sl.name, "verdict": "ERROR", "error": str(e)[:160]}

    per_slice = list(await asyncio.gather(*[one(sl) for sl in slices]))
    for r in per_slice:
        if r["verdict"] == "NO-GO":
            flagged.append({"slice": r["slice"], "types": r.get("types", [])})
        elif r["verdict"] in ("INCONCLUSIVE", "ERROR"):
            errored += 1

    return {
        "contest_id": item.contract_id,
        "detected": bool(flagged),
        "n_slices_scanned": len(slices),
        "n_slices_available": len(slice_paths(in_scope)),
        "n_files_out_of_scope": dropped,
        "flagged": flagged,
        "slices_errored": errored,
        "per_slice": per_slice,
        "api_calls": council.get_api_call_count()["total"] - before,
        "latency_s": round(time.time() - t0, 1),
        "schema": 1,
    }


def score(rows: list[dict], sclass: dict[str, list[dict]]) -> dict:
    scored = [r for r in rows if r.get("n_slices_scanned", 0) > 0]
    detected = [r for r in scored if r["detected"]]
    bugs_total = sum(len(sclass.get(r["contest_id"], [])) for r in scored)
    bugs_hit = sum(len(sclass.get(r["contest_id"], [])) for r in detected)
    lat = [r["latency_s"] for r in scored if r.get("latency_s")]
    return {
        "contests_scored": len(scored),
        "contests_detected": len(detected),
        "contest_recall": round(len(detected) / len(scored), 3) if scored else 0.0,
        "sclass_bugs_in_scored_contests": bugs_total,
        "sclass_bugs_in_detected_contests": bugs_hit,
        "bug_level_recall_upper_bound": round(bugs_hit / bugs_total, 3) if bugs_total else 0.0,
        "median_latency_s": round(statistics.median(lat), 1) if lat else None,
        "total_api_calls": sum(r.get("api_calls", 0) for r in scored),
        "note": ("Contest-level, any-slice-positive. bug_level_recall is an UPPER BOUND: "
                 "it credits every S-class bug in a contest whenever any slice of that "
                 "contest was flagged, which does not prove the flag found THAT bug. "
                 "No safe class exists here, so precision is not computable and is not "
                 "reported — it stays on the balanced buckets."),
    }


def _wilson(k: int, n: int):
    """95% Wilson score interval.

    NOT Wald. Wald is p +/- 1.96*sqrt(p(1-p)/n), whose width is ZERO when p hits
    0 or 1 -- so a tool detecting 63/63 would report "100.0% [100.0-100.0]",
    claiming perfect certainty from a finite sample. That is exactly the kind of
    unqualified rate this paper exists to complain about, and a reviewer would
    rightly kill it. Wilson stays inside (0,1) and keeps sane width at the
    boundary: 63/63 becomes ~[94.3-100.0].
    """
    import math
    if n <= 0:
        return None
    z = 1.96
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = (z / d) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return p, max(0.0, c - h), min(1.0, c + h)


def head_to_head(rows: list[dict]) -> None:
    """ThirdEye vs GPTScan on the SAME projects.

    THE UNIT PROBLEM. GPTScan publishes per-project counts of RULE-CHECK
    outcomes: a tp means one of its ten targeted vulnerability types was matched
    in that project. We produce one decision per project ("was any slice
    flagged"). Comparing those directly is indefensible, so their counts are
    collapsed to our unit -- a project is detected if tp > 0 -- and compared on
    an identical project list.

    THE TRAP THAT MAKES THAT COLLAPSE WRONG IF DONE NAIVELY, and it is a large
    one: 34 of the 72 published projects have tp = 0 AND fn = 0. GPTScan had no
    ground-truth positive check in those projects at all -- its ten rule types
    simply do not cover the bug that Web3Bugs labels there. Counting them as
    GPTScan misses scores it on questions it was never asked, and drags its
    apparent detection rate from ~90% down to ~49%. The first version of this
    function did exactly that. So recall is computed ONLY over projects where
    GPTScan had at least one positive to find.

    What the excluded projects actually measure is SCOPE, not accuracy, and it is
    reported separately: on those projects GPTScan's rule set has nothing
    applicable to look for, while ThirdEye still returns a verdict. That is a
    real difference in coverage and it is worth saying -- but it is not recall,
    and merging the two would be the same error in the other direction.

    Even on the fair subset the remaining asymmetries FAVOUR US, so they are
    printed rather than buried:
      1. our "detected" needs any slice flagged anywhere in the codebase; it does
         NOT require the flag to name the right bug. Their tp does.
      2. collapsing to tp>0 hides their per-check misses inside a project we both
         detect.
    Our rate is therefore an UPPER bound against their LOWER bound.

    And the number that matters most is the one this bucket cannot give: every
    project here is positive, so precision is not computable for us, while
    GPTScan reports 30 FPs against 154 TNs. Their precision is printed beside our
    balanced-bucket FPR, labelled as two DIFFERENT negative sets, never
    subtracted from one another.
    """
    gs = json.load(open(REPO_ROOT / "datasets" / "gptscan" / "gptscan_parsed.json",
                        encoding="utf-8"))
    theirs = {str(r["contest_id"]): r for r in gs["per_project"]}
    ours = {str(r["contest_id"]): r for r in rows if r.get("n_slices_scanned", 0) > 0}
    shared = sorted(set(theirs) & set(ours), key=lambda x: int(x))
    if not shared:
        print("\n[head-to-head] no overlapping projects scored yet")
        return

    # Projects where GPTScan actually had a ground-truth positive check.
    gradable = [c for c in shared if theirs[c]["tp"] + theirs[c]["fn"] > 0]
    out_of_scope = [c for c in shared if theirs[c]["tp"] + theirs[c]["fn"] == 0]

    print("\n=== HEAD-TO-HEAD vs GPTScan (ICSE'24) ===")
    print(f"projects we both cover   {len(shared)}")
    print(f"  gradable for recall    {len(gradable)}   (GPTScan had >=1 positive check)")
    print(f"  outside GPTScan scope  {len(out_of_scope)}   (tp=0 and fn=0: no applicable rule)")

    if gradable:
        od = [c for c in gradable if ours[c]["detected"]]
        td = [c for c in gradable if theirs[c]["tp"] > 0]
        a = _wilson(len(od), len(gradable))
        b = _wilson(len(td), len(gradable))
        print(f"\n-- DETECTION on the {len(gradable)} gradable projects --")
        print(f"ThirdEye                 {len(od):>3}/{len(gradable)}   "
              f"{a[0]*100:.1f}%  [{a[1]*100:.1f}-{a[2]*100:.1f}]")
        print(f"GPTScan                  {len(td):>3}/{len(gradable)}   "
              f"{b[0]*100:.1f}%  [{b[1]*100:.1f}-{b[2]*100:.1f}]")
        sep = "SEPARATED" if (a[1] > b[2] or b[1] > a[2]) else "OVERLAPPING"
        print(f"95% Wilson intervals     {sep}")
        if sep == "OVERLAPPING":
            print("                         -> NO detection difference is demonstrated.")

    if out_of_scope:
        oo = [c for c in out_of_scope if ours[c]["detected"]]
        print(f"\n-- SCOPE on the {len(out_of_scope)} out-of-scope projects --")
        print(f"These carry a confirmed Web3Bugs S-class bug that GPTScan's ten rule")
        print(f"types do not target, so it has no applicable check to run.")
        print(f"ThirdEye still returns a verdict and flags  {len(oo)}/{len(out_of_scope)}.")
        print("This is COVERAGE, not recall. It is not evidence of better detection,")
        print("because an any-slice flag on an all-positive set is nearly free.")

    agg = gs["aggregate"]
    print(f"\nGPTScan precision        {agg['precision']:.3f} "
          f"(tp={agg['tp']} fp={agg['fp']}) — published, rule-check unit")
    print(f"GPTScan FPR              {agg['fpr']:.3f} on its own "
          f"{agg['tn'] + agg['fp']} negative checks")
    print("ThirdEye precision       NOT COMPUTABLE here — every project in this bucket is positive.")
    print("\nREMAINING ASYMMETRIES, all favouring us:")
    print("  * our detection is any-slice-positive and NOT type-matched; their tp is.")
    print("  * collapsing to tp>0 hides their misses inside projects we both detect.")
    print("  * the two false-positive figures come from DIFFERENT negative sets and")
    print("    are not a difference; ThirdEye's FPR is measured on buckets 01/02.")


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--contests", type=int, default=20, help="0 = all 102")
    ap.add_argument("--max-slices", type=int, default=25, help="cap per contest; 0 = no cap")
    ap.add_argument("--backend", default="ollama")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--concurrency", type=int, default=1, help="slices in flight per contest")
    ap.add_argument("--gptscan-set", action="store_true",
                    help="restrict to the 72 contests GPTScan published results for")
    ap.add_argument("--report-only", action="store_true")
    a = ap.parse_args()

    sclass = s_class_by_contest()
    items = [it for it in web3bugs.load() if str(it.contract_id) in sclass]
    # Nested seeded sample, same discipline as run_benchmark: shuffle once, take
    # a prefix, so a bigger run reuses everything a smaller one computed.
    if a.gptscan_set:
        # GPTScan's authors published per-project TP/TN/FP/FN for 72 Web3Bugs
        # projects (MetaTrustLabs/GPTScan-Web3Bugs). Scoring OUR tool on exactly
        # those contests turns "our recall on some Web3Bugs subset" into a real
        # head-to-head. Their aggregate recomputes to recall 0.833 / F1 0.678,
        # matching the published figures, so the file is the right artifact.
        gs = json.load(open(REPO_ROOT / "datasets" / "gptscan" / "comparison_set.json", encoding="utf-8"))
        keep = set(gs["runnable"])
        items = [it for it in items if str(it.contract_id) in keep]
        print(f"[web3bugs] GPTScan comparison set: {len(items)} contests")
    rng = random.Random(f"web3bugs:{a.seed}")
    items = list(items); rng.shuffle(items)
    if a.contests:
        items = items[: a.contests]

    CKPT.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []

    if not a.report_only:
        print(f"[web3bugs] {len(items)} contests with S-class bugs; cap {a.max_slices} slices each; backend={a.backend}")
        for i, it in enumerate(items, 1):
            cp = CKPT / f"contest_{it.contract_id}.json"
            if cp.exists():
                rows.append(json.load(open(cp)))
                continue
            row = await scan_contest(it, a.max_slices, a.backend, a.seed, a.concurrency)
            json.dump(row, open(cp, "w"), indent=1)
            rows.append(row)
            n_bugs = len(sclass.get(str(it.contract_id), []))
            print(f"  [{i}/{len(items)}] contest {it.contract_id:<5} slices={row['n_slices_scanned']:<3} "
                  f"-> {'DETECTED' if row['detected'] else 'missed  '} "
                  f"({n_bugs} S-bug(s), {row['latency_s']}s)")
    else:
        # --report-only used to glob EVERY checkpoint and ignore --gptscan-set, so
        # "the GPTScan comparison" silently reported the whole 91-contest sweep
        # under that label. Same filter as the run path, or the report is a
        # comparison that is not one.
        keep_ids = {str(i.contract_id) for i in items} if a.gptscan_set else None
        for cp in sorted(CKPT.glob("contest_*.json")):
            try:
                r = json.load(open(cp))
            except Exception:
                continue
            if keep_ids is not None and str(r.get("contest_id")) not in keep_ids:
                continue
            rows.append(r)

    if not rows:
        print("[web3bugs] nothing scored yet")
        return

    rep = score(rows, sclass)
    rep["backend"] = a.backend
    rep["max_slices"] = a.max_slices
    RESULTS.mkdir(parents=True, exist_ok=True)
    # Distinct filename: the head-to-head and the open sweep are different
    # populations, and writing both to web3bugs_bench.json meant whichever ran
    # last silently became "the" web3bugs result.
    out = "web3bugs_gptscan.json" if a.gptscan_set else "web3bugs_bench.json"
    json.dump({"summary": rep, "contests": rows}, open(RESULTS / out, "w"), indent=1)

    print(f"\n=== WEB3BUGS (bucket 04) — contest-level ===")
    print(f"contests scored          {rep['contests_scored']}")
    print(f"contests detected        {rep['contests_detected']}")
    print(f"contest recall           {rep['contest_recall']:.3f}")
    print(f"S-class bugs covered     {rep['sclass_bugs_in_scored_contests']}")
    print(f"bug recall (UPPER bound) {rep['bug_level_recall_upper_bound']:.3f}")
    print(f"median latency/contest   {rep['median_latency_s']}s")
    print(f"\n{rep['note']}")

    if a.gptscan_set:
        head_to_head(rows)


asyncio.run(main())
