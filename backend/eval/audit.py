"""Audit EVERY checkpoint tree for contamination, and say which claims survive.

WHY. On 2026-10-09 we found that A2's safe arm was 145/176 INCONCLUSIVE from a
backend outage -- PAPER_FACTS had already caught that one and marked it
UNSOUND. On 2026-10-23 we found the SAME defect in the VULNERABLE arm, which
PAPER_FACTS marks SOUND and whose numbers are in the abstract: of 20 paired
rows scored in both arms, exactly ONE had an intact council in both.

The lesson is not "check the ctx arms". It is that contamination was found
twice, by hand, in the two places someone happened to look. This script looks
everywhere, every time, so the question "is this number clean?" is answered by
running something rather than by remembering.

On 2026-10-23 this script was itself caught by the defect it audits. It keyed
intactness on `row.get("specialists_errored")`, so a row that never recorded
council health at all -- every row produced through run_full_analysis, which
emits only `llm_error_detected` -- was indistinguishable from a row that
recorded a healthy council, and the ablation and arb_sweep trees were reported
CLEAN on no evidence whatsoever. Hence the third tier below: unrecorded health
is UNKNOWN, is reported loudly, and never counts as intact. A checker that
fails open is worse than no checker, because it manufactures confidence.

THE BIAS DIRECTION IS THE POINT. A specialist that errored can only fail to
raise a flag, never invent one. So contamination does not add noise
symmetrically -- it pushes verdicts toward GO. In an arm measuring RECALL that
depresses recall; if the contaminated arm is the one you are arguing is worse,
the contamination manufactures your result. That is why a "sound" label has to
mean intact-council, not merely terminal, wherever two arms are COMPARED.

Usage:
    python -m eval.audit               # everything
    python -m eval.audit --json out.json
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

CKPT = Path(__file__).resolve().parent / "checkpoints"
TERMINAL = ("GO", "NO-GO")
VERDICT_KEYS = ("verdict", "council_verdict", "final_verdict")


def _verdict(r: dict) -> str:
    """The verdict under whichever key this tree happens to use.

    Two trees do not carry a verdict STRING at all, and both have a real
    soundness rule that eval/purge.py already encodes -- the ablation rows
    carry ok/pred (guarded on `ok`) and the web3bugs rows carry
    detected/slices_errored (guard.aggregate_terminal). Mapping them onto the
    same GO/NO-GO vocabulary keeps ONE definition of soundness in this report
    instead of silently excluding whatever it cannot parse.
    """
    for k in VERDICT_KEYS:
        if r.get(k):
            return str(r[k]).upper()
    if "ok" in r and "pred" in r:                      # ablation arm
        return ("NO-GO" if r.get("pred") else "GO") if r.get("ok") else ""
    if "detected" in r and "slices_errored" in r:      # web3bugs contest row
        return "NO-GO" if r.get("detected") else ("GO" if not r.get("slices_errored") else "")
    # Static-analyser baseline rows (slither): no verdict, just a status. A
    # `no_result` is an ABSTENTION and must never be read as a verdict -- on
    # 2026-10-24 all 301 slither rows on the aarch64 box were
    # status=no_result/reason=error (every solc binary in solc-select is
    # x86-64, so the compiler could not execute), and because this function
    # returned "" for them the whole arm printed as NOT AUDITED while progress
    # probes reported "slither 301 done". A dead baseline that looks finished
    # is worse than a missing one, so status is now read explicitly and
    # `answered` is reported in the status line.
    if "status" in r and ("slither_message" in r or "reason" in r):
        st = str(r.get("status") or "").lower()
        if st in ("no_result", "error", ""):
            return ""                                   # abstention, not a verdict
        return "NO-GO" if r.get("predicted_label") in (True, "vulnerable") else "GO"
    return ""


def load_tree(pattern: str) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for d in sorted(CKPT.glob(pattern)):
        if not d.is_dir() or d.name in ("_transient", "_poisoned", "_pre8b", "_8b_run"):
            continue
        rows = []
        for f in sorted(d.glob("*.json")):
            try:
                rows.append(json.load(open(f, encoding="utf-8")))
            except Exception:  # noqa: BLE001
                rows.append({"_unreadable": True})
        if rows:
            out[str(d.relative_to(CKPT))] = rows
    return out


def classify(rows: list[dict]) -> dict:
    """Three tiers, because they answer different questions.

    terminal      -- has a usable verdict at all
    intact        -- terminal AND no specialist errored (required for PAIRED
                     comparisons, where a missing specialist in one arm makes
                     the pair non-comparable)
    asym_sound    -- terminal under the asymmetric rule: NO-GO is sound even
                     with errors, GO is not. Correct for single-arm detection
                     questions, WRONG for paired ones.
    """
    n = len(rows)
    unreadable = sum(1 for r in rows if r.get("_unreadable"))
    # Trees do not agree on the verdict key: the benchmark/ctx/parity runners
    # write `verdict`, arbitration_sweep writes `council_verdict`, and the
    # service layer writes `final_verdict`. Keying on `verdict` alone made
    # this script report terminal=0 for arb_sweep, the ablation arms, and
    # web3bugs -- a row of zeros that reads as "nothing wrong" when it
    # actually means "this tree was never audited". Try every known key, and
    # if a non-empty tree still yields no verdict at all, SAY SO (below)
    # rather than printing a reassuring zero.
    verdicts = Counter(_verdict(r) or "?" for r in rows)
    terminal = [r for r in rows if _verdict(r) in TERMINAL]
    # THREE states, not two. `specialists_errored` ABSENT is not the same fact
    # as `specialists_errored == 0`, but `.get()` collapses them: both are
    # falsy, so a row whose council health was never recorded was being
    # counted as intact. That is this script's own failure mode -- the exact
    # one it exists to catch -- and it reported the ablation and arb_sweep
    # trees as CLEAN on rows that carry no health field at all. Unrecorded
    # health is now its own tier and NEVER counts as intact.
    # web3bugs records council health per contest under its own name.
    def _health_key(r: dict) -> str | None:
        for k in ("specialists_errored", "slices_errored"):
            if k in r:
                return k
        return None

    def _health_bad(r: dict) -> bool | None:
        """How many sub-units failed, or None if the row records nothing.

        The baseline runners express health as a SURVIVOR count rather than a
        failure count: `n_slices_ok` out of `n_slices`. Reading only failure
        keys made these rows look like they carried no health at all, when in
        fact they carry it inverted.
        """
        k = _health_key(r)
        if k is not None:
            return bool(r[k])
        if "n_slices" in r and "n_slices_ok" in r:
            try:
                return int(r["n_slices_ok"]) < int(r["n_slices"])
            except (TypeError, ValueError):
                return None
        return None
    unrecorded = [r for r in terminal if _health_bad(r) is None]
    intact = [r for r in terminal if _health_bad(r) is False]
    # The asymmetric rule still holds on an unrecorded row: a NO-GO is sound
    # whatever the council did, because a dead specialist can only suppress a
    # flag. A GO with UNKNOWN health is not sound -- it is exactly the case the
    # rule excludes, so it must not pass merely because the field is missing.
    asym = [r for r in terminal
            if _verdict(r) == "NO-GO"
            or _health_bad(r) is False]
    return {
        "n": n,
        "unreadable": unreadable,
        "verdicts": dict(verdicts),
        "terminal": len(terminal),
        "intact_council": len(intact),
        "unrecorded_health": len(unrecorded),
        "asym_sound": len(asym),
        # Raw states, so a tree with no verdicts can be DIAGNOSED rather than
        # merely flagged: "every row abstained" and "I do not understand this
        # schema" need different fixes, and printing ['?'] for both sent the
        # dead slither arm back to the same blind spot twice.
        "raw_states": dict(Counter(
            str(r.get("status") or r.get("reason") or
                next((r[k] for k in VERDICT_KEYS if r.get(k)), "?"))
            for r in rows).most_common(4)),
        "contaminated_pct": round(100 * (len(terminal) - len(intact)) / len(terminal), 1) if terminal else None,
    }


def paired(a: list[dict], b: list[dict]) -> dict:
    """What a PAIRED comparison actually has to work with."""
    A = {r.get("contract_id"): r for r in a if r.get("contract_id")}
    B = {r.get("contract_id"): r for r in b if r.get("contract_id")}
    common = set(A) & set(B)
    both_term = [c for c in common
                 if _verdict(A[c]) in TERMINAL and _verdict(B[c]) in TERMINAL]
    # Same three-state rule as classify(): a pair is intact only if BOTH arms
    # positively recorded a healthy council. A missing field cannot buy a pair
    # into the comparison -- the whole point of intact_both is that the two
    # arms are known to be comparable.
    def _healthy(r: dict) -> bool:
        return "specialists_errored" in r and not r["specialists_errored"]
    both_intact = [c for c in both_term if _healthy(A[c]) and _healthy(B[c])]
    both_unrec = [c for c in both_term
                  if "specialists_errored" not in A[c] or "specialists_errored" not in B[c]]
    return {"common": len(common), "scored_both": len(both_term),
            "intact_both": len(both_intact), "unrecorded_either": len(both_unrec),
            "usable_pct": round(100 * len(both_intact) / len(both_term), 1) if both_term else None}


def verdict_line(label: str, s: dict) -> str:
    c = s["contaminated_pct"]
    u = s.get("unrecorded_health", 0)
    flag = ""
    if s["n"] and not s["terminal"]:
        # A non-empty tree in which NOTHING parsed as a verdict is an audit
        # FAILURE, not a clean result. Printing "terminal=0 intact=0" and
        # stopping is how arb_sweep, web3bugs and the ablation arms went
        # unaudited while appearing in this report as rows of harmless zeros.
        states = s.get("raw_states") or {}
        # One state covering every row, and it reads as a failure/abstention:
        # the arm RAN and produced nothing. That is a dead arm, not a parsing
        # gap, and it is the more dangerous of the two because the row count
        # makes it look finished.
        dead = (len(states) == 1 and next(iter(states)).lower()
                in ("no_result", "error", "", "none", "inconclusive"))
        if dead:
            return (f"  {label:<34} n={s['n']:<5} *** DEAD ARM: every row is "
                    f"{list(states)[0]!r} -- it RAN AND PRODUCED NOTHING. "
                    f"Row count makes this look finished; it is not ***")
        return (f"  {label:<34} n={s['n']:<5} *** NOT AUDITED: no recognised verdict key "
                f"(saw {list(states)[:3]}) -- THIS TREE IS UNVERIFIED ***")
    if u:
        # Loudest state in the report. "No errors recorded" and "no record of
        # errors" are different claims, and only one of them is evidence.
        flag = f"  *** {u} ROWS: COUNCIL HEALTH NOT RECORDED -- NOT CLEAN, UNKNOWN ***"
    elif c is not None:
        flag = "  CLEAN" if c == 0 else (f"  {c}% contaminated" if c < 25 else f"  *** {c}% CONTAMINATED ***")
    return (f"  {label:<34} n={s['n']:<5} terminal={s['terminal']:<5} "
            f"intact={s['intact_council']:<5} unrec={u:<5} asym={s['asym_sound']:<5}{flag}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", type=Path, default=None)
    a = ap.parse_args()

    report = {}
    print("=" * 94)
    print("CHECKPOINT CONTAMINATION AUDIT")
    print("  terminal = has a verdict | intact = no specialist errored | asym = NO-GO-or-clean-GO")
    print("=" * 94)

    # The baseline trees were absent from this list until 2026-10-24, so
    # slither / single_llm / council -- the entire baseline comparison table --
    # had never been audited by the script whose job is to audit everything.
    # Their rows also use a third naming scheme (`status` for terminality,
    # n_slices/n_slices_ok for health), which is why they needed teaching
    # rather than just listing. 14 of 273 council rows turned out to have
    # failed slices.
    for pat in ("benchmark/*/seed*", "ctx_*", "parity_*", "web3bugs", "arb_sweep",
                "ablation/*/*", "slither/*/seed*", "single_llm/*/seed*", "council/*/seed*"):
        trees = load_tree(pat)
        if not trees:
            continue
        print(f"\n[{pat}]")
        for name, rows in trees.items():
            s = classify(rows)
            report[name] = s
            print(verdict_line(name, s))

    # The paired comparisons the paper actually reports.
    print("\n" + "=" * 94)
    print("PAIRED COMPARISONS — what the claim can legitimately rest on")
    print("=" * 94)
    pairs = [("ctx_ctx4k", "ctx_ctx16k", "FINDING 3 vulnerable arm (recall 12.5% -> 81.2%, p=0.0162)"),
             ("ctx_ctx4k_safe", "ctx_ctx16k_safe", "FINDING 3 safe arm (already marked UNSOUND)"),
             ("parity_full3b", "parity_full8b", "model capacity on the hot role (p=0.0303)")]
    for x, y, what in pairs:
        tx, ty = load_tree(x), load_tree(y)
        if not tx or not ty:
            print(f"\n  {what}\n    (missing one arm)")
            continue
        p = paired(list(tx.values())[0], list(ty.values())[0])
        report[f"paired:{x}|{y}"] = p
        warn = ""
        if p["intact_both"] is not None and p["intact_both"] < 20:
            warn = "   <-- TOO FEW INTACT PAIRS TO SUPPORT A CLAIM"
        print(f"\n  {what}")
        print(f"    common={p['common']}  scored in both={p['scored_both']}  "
              f"INTACT IN BOTH={p['intact_both']} ({p['usable_pct']}%)" + warn)

    print("\n" + "=" * 94)
    print("Rule of thumb: a PAIRED claim needs intact_both, not scored_both. A dead")
    print("specialist can only suppress a flag, so contamination biases toward GO --")
    print("which in a recall comparison MANUFACTURES the effect rather than hiding it.")
    if a.json:
        json.dump(report, open(a.json, "w"), indent=2)
        print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
