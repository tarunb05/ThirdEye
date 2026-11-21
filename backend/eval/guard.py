"""The guard every runner needs before anything runs unattended.

A watched run is protected by a person noticing. An unattended one is protected
by nothing, and the failure is silent in the worst direction: a dead backend
returns fast, so throughput LOOKS fine while every row is garbage. On
2026-09-25 that cost a session and produced FPR 9.7% -> 54.8%, p = 0.0005, from
145 of 176 rows that were backend failures checkpointed as results. The numbers
looked BETTER than the truth, which is why nobody caught it from the output.

Only run_benchmark has a breaker today. run_web3bugs, run_parity,
arbitration_sweep, run_class_coverage, run_ablation and run_baselines have
neither a breaker nor quarantining, and those are exactly the stages that would
run overnight with nobody watching.

Three things, used together:

    Quarantine   a non-terminal row goes to _transient/, never to the
                 checkpoint path, so a resume genuinely retries it instead of
                 baking a provider outage into the result forever.
    Breaker      a run of consecutive failures means the backend died; stop
                 writing rather than plough on.
    Rate guard   a breaker only catches a TOTAL death. A backend that fails
                 30% of calls never trips it and quietly biases the sample,
                 because the calls that fail are the large, complex contracts.
                 So the rolling failure RATE is capped too.

The terminal rule is asymmetric on purpose, and the asymmetry is the whole
argument. An errored specialist can only fail to raise a flag, never invent
one:

    NO-GO with errors  -> sound. The finding came from a specialist that DID
                          run; the missing ones could only have added more.
    GO with errors     -> unsound. A specialist that never ran might have been
                          the one to find something, so the clean bill of
                          health is unearned.

Requiring an intact council for both discards ~46% of completed work and
removes no bias from the NO-GO side.
"""

from __future__ import annotations

import json
import time
from collections import deque
from pathlib import Path

TERMINAL_VERDICTS = ("GO", "NO-GO")


def default_terminal(row: dict) -> bool:
    """The single-contract rule: a terminal verdict, and -- for GO only -- an
    intact council. See the asymmetry argument in the module docstring."""
    v = (row.get("verdict") or "").upper()
    if v not in TERMINAL_VERDICTS:
        return False
    if v == "GO":
        # A GO must PROVE an intact council, not merely fail to report a
        # broken one. `row.get("specialists_errored")` returns None for a row
        # that never recorded council health, which is falsy, which admitted
        # the row as a trustworthy GO on no evidence. That is the same
        # fail-open that let eval/audit.py report unaudited trees as CLEAN:
        # absence of a record is not a record of absence. Every tree governed
        # by this rule (benchmark, parity) does carry the field, so this is
        # closing a latent trap rather than rejecting existing data -- a new
        # runner wiring run_full_analysis through here would have hit it.
        if "specialists_errored" not in row:
            return False
        if row["specialists_errored"]:
            return False
    return True


def aggregate_terminal(positive_key: str, errored_key: str):
    """Terminality for a row that aggregates many sub-scans -- a Web3Bugs
    contest over its slices, a sliced project, a sweep over one contract's
    findings.

    The same asymmetry, lifted one level. A POSITIVE aggregate is sound however
    many sub-scans died, because the detection came from one that actually ran
    and the dead ones could only have added more. A NEGATIVE aggregate with any
    failed sub-scan is not sound: the bug may have been in precisely the slice
    that errored, so "we scanned it and found nothing" is unearned, and scoring
    it as a miss understates recall rather than overstating it.
    """
    def _fn(row: dict) -> bool:
        if row.get(positive_key):
            return True
        return not row.get(errored_key)
    return _fn


class RunAborted(RuntimeError):
    """Raised when the guard stops a run. Carries why, for the log."""


class Guard:
    """Shared health guard. One instance per run.

    max_consecutive: consecutive non-terminal rows before aborting.
    window / max_rate: rolling failure-rate cap, e.g. 50 and 0.25 means abort
        if more than a quarter of the last 50 rows failed.
    terminal_fn: override for runners whose row is not one contract's verdict.
        Web3Bugs rows aggregate a contest's slices; the ablation writes a bare
        prediction. Use `aggregate_terminal` rather than inventing a fresh rule
        per runner -- the asymmetry has to survive the lift.
    """

    def __init__(self, label: str, max_consecutive: int = 15,
                 window: int = 50, max_rate: float = 0.25,
                 terminal_fn=None, answer_fn=None) -> None:
        self.label = label
        self.terminal_fn = terminal_fn or default_terminal
        # A row can be legitimately TERMINAL while containing no answer -- a
        # contract absent from the corpus, for instance. Counting answers
        # separately is the whole-arm check that no per-row rule can fake: if
        # an arm finished with zero answers, it did not run, whatever its
        # soundness rate says. See _baseline_terminal in run_baselines.
        self.answer_fn = answer_fn or (lambda r: r.get("status") == "ok"
                                       or r.get("verdict") in ("GO", "NO-GO")
                                       or r.get("final_verdict") in ("GO", "NO-GO"))
        self.answers = 0
        self.max_consecutive = max_consecutive
        self.window = window
        self.max_rate = max_rate
        self._recent: deque[bool] = deque(maxlen=window)
        self._consecutive = 0
        self.sound = 0
        self.quarantined = 0
        self.aborted: str | None = None
        self.started = time.time()

    # ---------------------------------------------------------------- policy

    def is_terminal(self, row: dict) -> bool:
        """Whether this row may be written as a result."""
        return bool(self.terminal_fn(row))

    def observe(self, row: dict) -> bool:
        """Record one completed row. Returns True if it is terminal.

        Raises RunAborted when the guard decides the backend is unhealthy. The
        caller should let that propagate: completed checkpoints are kept and a
        re-run resumes, so aborting is always cheaper than continuing.
        """
        ok = self.is_terminal(row)
        try:
            if self.answer_fn(row):
                self.answers += 1
        except Exception:  # noqa: BLE001 — a diagnostic must never break a run
            pass
        self._recent.append(ok)
        if ok:
            self.sound += 1
            self._consecutive = 0
        else:
            self.quarantined += 1
            self._consecutive += 1

        if self._consecutive >= self.max_consecutive:
            self._abort(f"{self._consecutive} consecutive non-terminal rows — "
                        f"the backend has almost certainly died")

        if len(self._recent) == self.window:
            bad = self._recent.count(False)
            rate = bad / self.window
            if rate > self.max_rate:
                self._abort(f"{bad}/{self.window} of the last rows failed "
                            f"({rate:.0%} > {self.max_rate:.0%}) — a partial failure rate "
                            f"this high biases the sample toward small contracts without "
                            f"ever tripping a consecutive-failure breaker")
        return ok

    def _abort(self, why: str) -> None:
        if self.aborted:
            return
        self.aborted = why
        print()
        print("=" * 72)
        print(f"  GUARD ABORT — {self.label}")
        print(f"  {why}.")
        print(f"  sound={self.sound} quarantined={self.quarantined}. Completed checkpoints")
        print("  are kept; a re-run resumes from them. Restart the backend and relaunch.")
        print("=" * 72)
        print(flush=True)
        raise RunAborted(why)

    # ------------------------------------------------------------- bookkeeping

    def write(self, row: dict, ckpt: Path) -> bool:
        """Checkpoint a row to the right place. Terminal rows go to `ckpt`,
        everything else to `ckpt.parent/_transient/`."""
        terminal = self.observe(row)
        target = ckpt if terminal else (ckpt.parent / "_transient" / ckpt.name)
        target.parent.mkdir(parents=True, exist_ok=True)
        json.dump(row, open(target, "w"))
        return terminal

    def summary(self) -> dict:
        mins = (time.time() - self.started) / 60.0
        total = self.sound + self.quarantined
        return {
            "label": self.label,
            "sound": self.sound,
            "quarantined": self.quarantined,
            "quarantine_rate": round(self.quarantined / total, 4) if total else 0.0,
            "answers": self.answers,
            # The number that would have caught the dead slither arm instantly.
            "dead_arm": bool(total and not self.answers),
            "aborted": self.aborted,
            "minutes": round(mins, 1),
            "rows_per_min": round(total / mins, 2) if mins > 0.1 else None,
        }

    def line(self) -> str:
        s = self.summary()
        out = (f"[{self.label}] sound={s['sound']} quarantined={s['quarantined']} "
               f"({s['quarantine_rate']:.0%}) answers={s['answers']} "
               f"{s['rows_per_min'] or '—'}/min")
        if s["dead_arm"]:
            # Loud, because the quiet version of this line read
            # "sound=142 quarantined=0 (0%)" for an arm that answered nothing.
            out += (
                "\n  !!! DEAD ARM — "
                f"{s['sound'] + s['quarantined']} rows, ZERO answers. "
                "This arm RAN AND PRODUCED NOTHING; the row count makes it look "
                "finished. Do not score it, and do not let a soundness rate "
                "computed over empty rows stand in for a result.")
        if s["aborted"]:
            out += f"  ABORTED: {s['aborted']}"
        return out


STAGE_LOG = Path(__file__).resolve().parent / "results" / "stage_health.jsonl"


def record_stage(summary: dict) -> None:
    """Append a stage's health summary. One line per stage, append-only, so a
    pipeline that dies still leaves a readable history of how far it got and
    which stage went bad."""
    STAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
    summary = {**summary, "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    with open(STAGE_LOG, "a") as fh:
        fh.write(json.dumps(summary) + chr(10))


def last_stage() -> dict | None:
    if not STAGE_LOG.exists():
        return None
    last = None
    for raw in open(STAGE_LOG):
        raw = raw.strip()
        if not raw:
            continue
        try:
            last = json.loads(raw)
        except json.JSONDecodeError:
            continue
    return last


def acknowledge(reason: str) -> None:
    """Record that a human diagnosed an abort and fixed the cause.

    preflight reads the LAST stage entry, so a single abort latches the whole
    pipeline shut -- which is correct, and is exactly what it did on
    2026-10-09. But the operator then needs a way to say "I found it and fixed
    it" that is honest about what happened. This appends an explicit
    acknowledgement rather than rewriting or deleting the abort, so the log
    still shows the failure, the diagnosis, and the restart in order.
    """
    STAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
    row = {"label": "OPERATOR ACKNOWLEDGEMENT", "sound": 0, "quarantined": 0,
           "quarantine_rate": 0.0, "aborted": None, "reason": reason,
           "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    with open(STAGE_LOG, "a") as fh:
        fh.write(json.dumps(row) + chr(10))
    print(f"[guard] acknowledged: {reason}")


def preflight(stage: str, max_quarantine_rate: float = 0.25) -> None:
    """Gate between stages of an unattended pipeline.

    A pipeline running ten stages back to back overnight must not start stage
    N+1 on a backend that just wrecked stage N. Without this, one outage at
    hour three silently poisons every stage after it, and the only evidence is
    a quarantine count nobody is awake to read.

    Exits non-zero rather than raising, so a shell orchestrator stops on it.
    """
    prev = last_stage()
    if prev is None:
        print(f"[preflight] {stage}: no previous stage recorded — proceeding")
        return
    if prev.get("aborted"):
        print(f"[preflight] {stage}: REFUSING — previous stage {prev.get('label')!r} "
              f"aborted: {prev['aborted']}")
        raise SystemExit(2)
    rate = prev.get("quarantine_rate", 0.0)
    if rate > max_quarantine_rate:
        print(f"[preflight] {stage}: REFUSING — previous stage {prev.get('label')!r} "
              f"quarantined {rate:.0%} of its rows (cap {max_quarantine_rate:.0%}). "
              f"The backend is unhealthy; fix it before spending more GPU time.")
        raise SystemExit(2)
    print(f"[preflight] {stage}: previous stage {prev.get('label')!r} healthy "
          f"({prev.get('sound')} sound, {rate:.0%} quarantined) — proceeding")


def main() -> int:
    """CLI so a shell orchestrator can gate on it:  python -m eval.guard <stage>"""
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("stage")
    ap.add_argument("--max-quarantine-rate", type=float, default=0.25)
    ap.add_argument("--acknowledge", metavar="REASON", default=None,
                    help="record that an abort was diagnosed and fixed, then proceed. "
                         "Appends to the log; never rewrites it.")
    a = ap.parse_args()
    if a.acknowledge:
        acknowledge(a.acknowledge)
        return 0
    preflight(a.stage, a.max_quarantine_rate)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
