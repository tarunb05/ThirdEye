# Phase 1 session notes (taxonomy bridge + real baseline runs)

Running log, updated as work progresses. Not a deliverable doc — a checkpoint
of my own, per the instruction not to push through silently for hours.

## Done
- [x] DASP-10 taxonomy bridge (`eval/taxonomy.py`): Web3Bugs O/L/S codes,
      Etherscan-50's 2 ad-hoc strings, ThirdEye's LLM-keyword-dict +
      Slither-detector vocabulary. SmartBugs passthrough confirmed exact
      (zero mismatches). Web3Bugs real-dataset coverage: 100% of the 36
      distinct codes actually present have a table entry — but 58.8% of
      individual bug records (282/480) deliberately resolve to `unmapped`
      because they're S-category business-logic bugs DASP-10 has no slot
      for. That's a finding, not a gap — logged every one, not dropped.
- [x] Wired into `eval/metrics.py` as `normalize_categories=False` default
      (native taxonomy untouched in EvalItem/Prediction either way);
      `Prediction` gained `category_taxonomy` field. Fixed a subtlety:
      taxonomy.normalize() now logs every UNMAPPED result including
      deliberate table entries (e.g. Web3Bugs S3-1), not just genuinely
      unrecognized strings — first version only logged the latter.
- [x] Added `llm_error_detected` diagnostic to `run_full_analysis()`'s
      stats dict (services/llm.py) — purely additive, no existing logic
      touched. Needed because a 429/timeout on the vuln-scan call alone
      produces an empty `vulnerabilities` list indistinguishable from a
      genuinely clean contract without this signal.
- [x] `eval/run_baselines.py`: checkpointed runner (one JSON file per
      baseline/dataset/contract_id under `eval/checkpoints/`, atomic
      writes via temp-file-then-replace), retry-with-backoff on
      `llm_error_detected` (5 attempts, 8s base, exponential).

## First validation batch (2 items/dataset, all 3 baselines) — failed, but usefully
Ran it before trusting the runner with real quota. Result: every single item
failed, across all three baselines. Not real rate-limiting — three
compounding bugs, found by actually reading the failure reasons instead of
assuming "Groq is throttling us":

1. **Slither: 100% `no_result`**, reason `"Slither not installed (optional)"`.
   Root cause: `slither-analyzer`/`solc-select` genuinely weren't installed
   in the venv yet. Fixed: `pip install slither-analyzer solc-select`
   (not yet added to requirements.txt — pending).
2. **Slither: still "not installed" after installing it.** `services/slither.py`
   called bare `subprocess.run(["slither", ...])`, which only resolves via
   PATH when the venv's `Scripts/` dir is on it. This venv was invoked
   directly (`venv/Scripts/python.exe`, no `activate` sourced) both by me
   and by however the deployed app actually starts — so PATH never had it.
   Fixed: `_resolve_slither_executable()` resolves the slither binary path
   relative to `sys.executable`'s parent directory.
3. **Slither: ran, but `output` was always empty, `return_code: 1`.**
   Slither's CLI exits 1 whenever ANY detector fires — that's success WITH
   findings, not failure. The original code did
   `result.stdout if result.returncode == 0 else result.stderr`, which
   silently discarded every real finding (read empty stderr instead) on
   any contract Slither actually found something in. This would have
   permanently zeroed out all real Slither findings, full stop — `_parse_slither`'s
   `json.loads()` failed on the empty string and got swallowed by a bare
   `except: return []`. Fixed: try `json.loads(stdout)` first regardless of
   exit code; only fall back to stderr/error status when stdout genuinely
   isn't JSON.
4. **Slither: still failing after #2 and #3** — `crytic_compile` shells out
   to a bare `solc`, which hit the *same* PATH problem as #2 (the solc-select
   shim lives in the same `venv/Scripts/` dir). Fixed: `run_slither()` now
   builds an explicit `env` dict with `venv/Scripts` prepended to `PATH`
   before calling `subprocess.run`.
5. **Slither: only one solc version (0.4.22) was installed**, so anything
   targeting a different pragma failed to compile. Datasets span Solidity
   0.4 through 0.8. Fixed: `_detect_solc_version()` pulls the first concrete
   version out of the file's `pragma solidity` line, `_ensure_solc_version()`
   installs it on demand via `solc_select.install_artifacts()` (idempotent,
   cached under `~/.solc-select`), and `SOLC_VERSION` is set in the
   subprocess env to pin that version for the call (no global state mutated,
   safe under concurrency).
6. **LLM baselines: 100% `rate_limited_exhausted`** (12/12, all 5 retries
   exhausted, ~30 min wasted) — but the actual stored `reason` was
   `"[Ollama not running]"`, not a Groq 429 at all. Root cause:
   `eval/run_baselines.py` never called `load_dotenv()`, so `LLM_BACKEND`
   fell back to the `"ollama"` default instead of reading `backend/.env`'s
   `LLM_BACKEND=groq`. Fixed: added `load_dotenv()` at the top of the script,
   plus a `_check_backend_config()` pre-flight check that aborts immediately
   (before spending any retries) if `LLM_BACKEND != "groq"` or
   `GROQ_API_KEY` is unset — specifically to prevent this exact silent-waste
   failure mode from recurring.

Cleared `eval/checkpoints/` entirely after this — the checkpointing logic
skips anything already checkpointed regardless of correctness, so the bad
`no_result`/`rate_limited_exhausted` checkpoints from this run would have
permanently blocked legitimate re-runs.

After all 6 fixes, manually verified `run_slither()` end-to-end against a
hand-written reentrancy snippet: `status: completed`, real JSON output,
correctly flagged the reentrancy.

Added `slither-analyzer==0.11.5` and `solc-select==1.2.0` to
`requirements.txt` — these were never in it despite `services/slither.py`
already being called from `run_full_analysis()` in production, meaning the
*deployed* app on Render has (until now) always silently skipped Slither
entirely (`"Slither not installed (optional)"`), merging LLM-only results
and calling it LLM+Slither merge. Worth flagging to the user explicitly —
this is a real production gap, not just an eval-harness one.

## Second validation batch (2 items/dataset) — Slither: 2/2 ok on
smartbugs_curated, 2/2 `no_result` on web3bugs, 2/2 `no_result` on
etherscan50. LLM baselines: smartbugs_curated all ok, etherscan50 mostly ok
(occasional retry then success), web3bugs 100% `rate_limited_exhausted`
even after retries. Investigated rather than assumed:

7. **Slither failing on etherscan50 (NOT the expected web3bugs
   multi-file risk) — root cause was a 7th bug, found by bypassing
   Slither's CLI and calling `crytic_compile.CryticCompile()` directly**
   to get the swallowed traceback: `InvalidCompilation: Unknown file:
   Users:\umara\AppData\Local\Temp\eth001_clean.sol`. Newer solc Windows
   builds (confirmed on 0.8.27, NOT on 0.8.0) emit their own internal
   source path without the drive letter in solc's `--combined-json`
   `sources` key (`/Users/umara/...` instead of `C:/Users/umara/...`).
   crytic-compile's Windows path-fixup heuristic
   (`crytic_compile/utils/naming.py:convert_filename`) assumes the first
   segment after a leading slash IS a one-letter drive code (the WSL/MSYS
   convention, `/c/Users/...`) and rewrites it — `/Users/...` has no such
   segment, so it mangled `Users` itself into a fake drive letter,
   produced a path that doesn't exist on disk, and raised
   `InvalidCompilation`. Slither's own `--json -` (JSON-to-stdout)
   mechanism temporarily redirects stdout to capture printed output for
   embedding in the JSON; when this exception fired mid-redirect, the
   traceback never reached the real stdout/stderr file descriptors before
   `sys.exit(1)` — explaining the totally silent empty-stdout-AND-stderr
   symptom (no message to even log, let alone act on).
   **Fixed**: `run_slither()` now passes Slither a relative filename with
   `cwd` set to the temp file's directory, instead of an absolute path.
   Confirmed (by calling `crytic_compile` directly, bypassing Slither's
   broken redirect) that a relative filename makes solc echo back a clean
   relative path with no leading slash at all, sidestepping the
   heuristic entirely. Verified the fix resolves eth-001 standalone:
   `status: completed`, real findings.
8. **Web3Bugs: 100% `rate_limited_exhausted` on both LLM baselines —
   confirmed NOT rate limiting.** Bypassed the truncated diagnostic and
   called `run_full_analysis()` directly to get the full Groq error body:
   `HTTP 413: "Request too large for model llama-3.3-70b-versatile ...
   on tokens per minute (TPM): Limit 12000, Requested [more]"`. Web3Bugs
   item 3 alone is 134KB of flattened multi-file source — comfortably
   past 12000 tokens on its own, before the prompt template or response
   budget. This is deterministic given the same input: retrying identical
   requests 5 times with backoff cannot ever succeed, it just wastes
   ~2 minutes per item for a guaranteed-identical failure.
   **Fixed the waste** (not the underlying limit, which isn't ours to
   fix): `_run_llm_baseline` in `run_baselines.py` now detects "413"/
   "too large" in the error and fails fast as a new distinct status,
   `too_large_for_backend`, with zero retries — instead of funneling it
   through the same retry path as genuine transient 429s.
   **Open decision, not mine to make unilaterally**: what should the
   per-dataset report do with Web3Bugs items that are simply too large
   for Groq's free tier? This isn't a small edge case — Web3Bugs items
   are whole multi-file projects, so a meaningful fraction of the 102
   are likely well over 12000 tokens once flattened. Options: (a) report
   them honestly as `too_large_for_backend` in the Web3Bugs LLM metrics
   (real, documented coverage gap — Slither's results aren't affected,
   only the two Groq-backed baselines), (b) skip Web3Bugs for
   single_llm/current_thirdeye baselines entirely and only run Slither
   there, (c) truncate large items before sending to the LLM (changes
   what's actually being evaluated — not something to decide silently).
   Stopped here to report back and get a decision before running the
   full 102-item Web3Bugs set against two LLM baselines that may hit
   this wall repeatedly.

**Decision (user, via AskUserQuestion): report 413s as an honest documented
gap.** Re-validated the fail-fast fix works (3 items in 5s instead of ~6min
of wasted retries).

## Discovered a second, much bigger constraint: Groq's real daily token cap
While re-running a 5-item/dataset timing batch to extrapolate full-run
feasibility, every LLM call past a certain point started failing — not
with a 429 per-minute rate limit, but `tokens per day (TPD): Limit 100000,
Used 99655, Requested 3795. Please try again in 49m40.8s`. Confirmed via a
direct raw API call (bypassing the app entirely): **Groq's free tier caps
llama-3.3-70b-versatile at 100,000 tokens per ROLLING 24h window**, not a
per-minute throttle — and this session's own testing/debugging had already
burned nearly all of it.

Computed real dataset sizes to turn this into a concrete estimate:
smartbugs_curated 510,469 chars (143 items), web3bugs **28,920,270 chars**
(102 items — avg 283KB/item, max 2.57MB), etherscan50 1,559,981 chars (50
items). Web3Bugs is 93% of total volume, but most of its items are so
large they'll hit the per-request 413 cap before ever touching daily
budget — so real daily-budget consumption is dominated by
smartbugs_curated + etherscan50 (193 items, ~517K tokens for one pass,
~2M+ tokens for both LLM baselines × summary+vuln calls each). At
100K tokens/24h, that's **~3-4 weeks of calendar time**, not the ~6 hours
I'd estimated from wall-clock latency alone before finding this.

Reported this back in full (including an honest mistake: I reflexively
`rm -rf`'d `eval/checkpoints/` after stopping a validation batch without
checking it contained legitimate, quota-cost successes — small loss, but
avoidable). **User decision: accept the multi-week timeline, run the full
295-item set for real, checkpointed across as many days as it takes.**

Fixed two things in `run_baselines.py` before launching the real run,
both prompted directly by the new daily-quota reality:
1. `TERMINAL_STATUSES = {"ok", "no_result", "too_large_for_backend"}` —
   only these get checkpointed now. `rate_limited_exhausted`/`error` are
   NOT checkpointed, since they're about today's quota window being full,
   not a deterministic property of the contract — checkpointing them
   permanently would silently block every future day's retry forever.
2. `DailyQuotaExhausted` exception — when an error mentions "tokens per
   day"/TPD, raise immediately (no point burning 5 retries × backoff
   against a wall with a quoted ~50min clearance time) and propagate up
   through `main()` to stop the whole run cleanly with a clear "resume
   tomorrow" message, instead of grinding through hundreds of items that
   will all fail identically once the window is full.

**Full run launched** (`python -m eval.run_baselines --datasets
smartbugs_curated,web3bugs,etherscan50`, all 3 baselines, no `--limit`,
background task). Expect it to run for a while, then stop cleanly via
`DailyQuotaExhausted` once today's window fills — that's expected
behavior, not a failure. Re-running the identical command on subsequent
days resumes automatically via checkpoint-skip.

## Day 1 results
Full run executed, stopped cleanly via `DailyQuotaExhausted` exactly as
designed (no wasted retries, clear message, nothing lost).

**Slither — fully done, all 295 items:**
- smartbugs_curated: 122 ok / 21 no_result / 143 total. One distinct new
  failure mode: `0.4.0 solc versions are not available` (rubixi.sol) —
  solc-select can't install some very old exact patch versions at all,
  a real (narrow) ceiling on top of the existing import-resolution gap.
- web3bugs: 1 ok / 101 no_result / 102 total. Matches the predicted risk
  almost exactly — flattening multi-file projects without real import
  resolution makes Slither fail on nearly all of them.
- etherscan50: 50/50 ok. Zero failures — single-file by construction,
  exactly as expected.

**LLM baselines — barely started.** `single_llm/smartbugs_curated` got
through item 1 (FibonacciBalance.sol: ok) before the daily window — already
nearly drained by this session's debugging — ran out. Stopped cleanly,
checkpoint preserved, ready to resume.

## In progress / next
- [ ] Re-run the identical command on subsequent days to make incremental
      LLM-baseline progress as the 24h window drains; Slither needs no
      re-run (already complete and checkpointed).
- [ ] Once all 295 items × 3 baselines have terminal checkpoints, build
      per-dataset metrics reports (NOT pooled — Web3Bugs/SmartBugs have
      zero negative examples, pooling with Etherscan-50 would let its 44
      likely_safe contracts silently supply all negative-class signal).

## Session 5 (WSL2 pivot): Slither baseline extracted, LLM baselines moved to local Ollama

New session, explicit pivot away from continuing the multi-week Groq
timeline: run everything from WSL2 Ubuntu instead of the Windows venv, use
local Ollama for the two LLM baselines (no daily token cap), and extract
the Slither baseline from the 294 checkpoints already on disk rather than
re-running it.

**Environment**: this session's actual shell is Git Bash (MINGW64), not
WSL2 natively — confirmed via `uname -a` before doing anything, since the
task's framing ("this session runs entirely in WSL2") didn't match the
environment metadata. WSL2 Ubuntu *is* installed and running
(`wsl.exe -l -v`), so every command this session routes through
`wsl.exe -d Ubuntu -- bash -c "..."` to actually execute inside it.

**Setup hit two real blockers, both resolved without sudo (no password
available):**
1. Ubuntu's `python3-venv`/`python3-pip` aren't installed and `apt
   install` needs sudo. Worked around with `python3 -m venv --without-pip`
   + pip's standalone `get-pip.py` bootstrap script (no apt needed).
2. Full `requirements.txt` fails to install — `chroma-hnswlib` (a chromadb
   dependency) needs a C++ compiler to build from source, none available.
   Checked imports: the eval harness only actually needs `httpx` +
   `python-dotenv` (everything else in requirements.txt — fastapi,
   chromadb, asyncpg, passlib, reportlab, etc. — is web-app-only, never
   imported by `eval/run_baselines.py`'s import chain). Installed just
   `httpx python-dotenv slither-analyzer solc-select` instead of the full
   file.

Slither smoke-tested clean in WSL2 — zero Windows path workarounds
needed, confirming the relative-path/cwd fix from last session was a
Windows-only problem (real Linux paths don't have the drive-letter
ambiguity that broke crytic-compile on Windows).

**Part 1 (Slither baseline from existing checkpoints)** — wrote
`eval/build_reports.py` (reads checkpoints, "ok" → Prediction, anything
else → skip+reason, never a guess), ran it. Real printed numbers:
- `slither/smartbugs_curated`: 122/143 ok (85.3%). Binary: TP=122 FP=0
  TN=0 FN=0 (precision/recall/F1=1.000 — expected, SmartBugs-Curated has
  no negative examples). Per-category f1 strongest on reentrancy (0.703)
  and unchecked_low_level_calls (0.772); weak on access_control (0.238),
  arithmetic (0.000), front_running (0.000). Macro F1=0.212, micro
  F1=0.387. Heavy unmapped volume (naming-convention×818,
  solc-version×244, etc.) — Slither's code-quality detectors firing
  constantly, not DASP-10-relevant.
- `slither/web3bugs`: 1/102 ok (1.0%) — confirms last session's predicted
  multi-file import-resolution failure almost completely.
- `slither/etherscan50`: 50/50 ok (100%). Binary: TP=6 FP=44 (precision
  0.120, recall 1.000) — the 44 likely_safe ground-truth contracts almost
  all get *something* flagged by Slither's code-quality detectors, which
  is exactly why normalize_categories/DASP-10 filtering matters for this
  dataset's binary number to mean anything.
- Noted one new minor finding: solc-select can't install some exact old
  patch versions at all (`0.4.0 solc versions are not available` for
  smartbugs_curated's rubixi.sol) — a narrow ceiling on top of the
  existing import-resolution gap.
- Also noticed (not yet investigated/fixed): `Predictions: 121` vs
  `n_ok: 122` for smartbugs_curated — a 1-item discrepancy, likely two
  items sharing the same `contract_id` (derived from filename only)
  silently overwriting each other in the `preds` dict. Worth a follow-up
  look, didn't block this session's reporting.

**Part 2 (Ollama via WSL2)**: `localhost:11434` and the `/etc/resolv.conf`
nameserver IP both failed from WSL2 (connection refused) even though
Ollama was confirmed running on Windows (`llama3.2:3b`, `qwen2.5-coder:7b`
loaded). Root cause: Ollama was bound to `127.0.0.1` only (no
`OLLAMA_HOST` set) — unreachable from WSL2's separate network namespace
regardless of IP. This was a bigger ask than the task anticipated
(restarting a currently-running app, widening its network exposure), so
stopped and asked the user before acting — confirmed via AskUserQuestion.
Set `OLLAMA_HOST=0.0.0.0` (user-level env var) and restarted both Ollama
processes. `netstat` confirmed the rebind. Still failed from WSL2 at the
resolv.conf IP — turned out that IP isn't the right one in this WSL2
networking mode; the real address is WSL2's own default gateway
(`ip route | grep default`, NOT `/etc/resolv.conf`'s nameserver — these
differ). `172.29.160.1:11434` worked immediately once found.

Added `--llm-backend {groq,ollama}` to `run_baselines.py` per spec: sets
`os.environ["LLM_BACKEND"]` before any baseline runs (must happen before
`services.llm` is first imported, since it reads `LLM_BACKEND` once into
a module-level constant — confirmed `_run_llm_baseline`'s import is
lazy/local so this ordering is safe), `_check_backend_config` now checks
against the *requested* backend instead of hardcoding "groq", and
`GROQ_API_KEY` is only required when that backend is actually groq.
`OLLAMA_URL` passed as a process env var on the WSL2 invocation only
(`OLLAMA_URL=http://172.29.160.1:11434 python -m eval.run_baselines ...`)
— deliberately did NOT touch the shared `backend/.env`, since it's still
`LLM_BACKEND=groq` for the Windows-side Groq resumption path and
`OLLAMA_URL=172.29.160.1` would be meaningless/wrong from the Windows
venv's perspective.

Cleared `eval/checkpoints/single_llm` and `eval/checkpoints/current_thirdeye`
per the task (stale Groq-quota-exhaustion failures, including the one
legitimate Groq "ok" result for FibonacciBalance.sol — deliberate, the
plan now uses these baseline names for Ollama-backed results going
forward).

Validated end-to-end on a 3-item/dataset batch (12 calls) before
committing to the full run: all 12 succeeded. One real finding: a larger
Etherscan-50 contract (eth-003, 27.5K chars) hit one `llm_error_detected`
retry under `current_thirdeye` (likely a timeout — that baseline runs
Slither + 2 LLM calls concurrently via `asyncio.gather`, and the local 3B
model under that contention plus a bigger prompt can exceed
`LLM_TIMEOUT`), then succeeded on retry. Confirmed via `Get-Process -Name
ollama` CPU-time growth that this was genuine slow computation, not a
hang, before waiting it out. Total batch time: 7m48s for 12 calls ≈ 39s/
call average *including* that outlier — used this (not the faster
~15-18s average from the other 11) for the full-run estimate, since
Etherscan-50 has some much larger contracts (up to 179K chars per last
session's dataset-size analysis) that could reproduce this.

**Full run launched**: 193 items (smartbugs_curated 143 + etherscan50 50)
× 2 baselines (single_llm, current_thirdeye) = 386 calls, estimated
~4.2 hours at the validated-batch average. Within the task's 6-hour
check-in ceiling — launched as a single background run rather than
needing to split it. Web3Bugs deliberately excluded per the task (most
items fail Slither's import resolution regardless of LLM backend,
already documented from last session — not worth spending Ollama time on
items that have no ground-truth-comparable prediction anyway).

## Known risks (both confirmed real, not hypothetical)
- Web3Bugs items are whole multi-file projects (`EvalItem.read_code()`
  concatenates them with `// === filename ===` headers, not real import
  resolution). Slither fails to compile a real fraction of these
  (confirmed: 1/3 ok in the small validation batch, the other 2 hit
  genuine `Source "X.sol" not found` import-resolution errors — expected,
  not a bug). Etherscan-50 and SmartBugs-Curated are single-file by
  construction and unaffected.
- Web3Bugs items can also be too large for Groq's free-tier per-request
  token budget (see #8) — a second, independent reason the LLM baselines
  will have real coverage gaps on this dataset specifically.

## Session 5 wrap-up: full run completed clean, results in eval/results/baseline_table.md

The full Ollama run (193 items × 2 baselines, 386 calls) finished 100%
clean — zero `no_result`/`error`/`rate_limited_exhausted`, confirmed via
checkpoint statuses. Real elapsed time from checkpoint timestamps:
~43.5min for `single_llm`, ~85.6min for `current_thirdeye` (runs Slither
+ 2 LLM calls per item) — ~2.15 hours total, well under the 4.2hr
estimate built from the validation batch's one slow outlier.

Extended `eval/build_reports.py` (Part 3) to cover all 3 baselines ×
their actual datasets (Web3Bugs stays Slither-only — never ran the LLM
baselines against it, documented above) and write
`eval/results/baseline_table.md`. Real numbers:

| dataset | baseline | n_analyzed/n_total | precision | recall | F1 | top categories |
|---|---|---|---|---|---|---|
| smartbugs_curated | slither | 122/143 | 1.000 | 1.000 | 1.000 | unchecked_low_level_calls(49), reentrancy(26) |
| web3bugs | slither | 1/102 | 1.000 | 1.000 | 1.000 | — |
| etherscan50 | slither | 50/50 | 0.120 | 1.000 | 0.214 | access_control(4) |
| smartbugs_curated | single_llm | 143/143 | 1.000 | 0.811 | 0.896 | access_control(5), unchecked_low_level_calls(5) |
| etherscan50 | single_llm | 50/50 | 0.182 | 0.667 | 0.286 | access_control(2) |
| smartbugs_curated | current_thirdeye | 143/143 | 1.000 | 0.958 | 0.979 | unchecked_low_level_calls(52), reentrancy(29) |
| etherscan50 | current_thirdeye | 50/50 | 0.140 | 1.000 | 0.245 | access_control(4) |

(SmartBugs-Curated/Web3Bugs precision is mechanically 1.000 whenever
recall>0 — both have zero negative examples. Etherscan-50 is the only
dataset with real negative-class signal, hence the only meaningful
precision numbers in this table.)

**Real finding worth carrying into Phase 3**: merging Slither into the
LLM (current_thirdeye) clearly helps recall on SmartBugs-Curated (0.958
vs single_llm's 0.811 — the merge catches real bugs the LLM alone
misses) but on Etherscan-50 it pulls precision almost all the way down
to Slither's own number (0.140 vs single_llm's 0.182, vs Slither alone's
0.120) — the merge inherits Slither's over-flagging tendency on
real-world (mixed vulnerable/safe) contracts more than it inherits the
LLM's relative restraint. Single-LLM alone is the more *precise* baseline
on the one dataset that actually has negative examples to be precise
about.

**Known minor artifact, diagnosed not fixed**: `smartbugs_curated`'s
`Predictions: 121` vs `n_ok: 122` discrepancy — traced to one specific
contract (`0x627fa62ccbb1c1b04ffaecd72a53e37fc0e17839.sol`) that
genuinely appears in two SmartBugs-Curated category folders
(`reentrancy/` and `unchecked_low_level_calls/` — the same physical file,
filed under both ground-truth labels by the dataset's own curators, not
a bug in our data). The loaders derive `contract_id` from filename only,
so this collides in any dict keyed by contract_id (`preds`,
`_load_checkpoints`) while the original `items` list still iterates it
twice — mild double-counting in binary confusion for this one contract.
Affects 1/295 total dataset items; did not fix the loader this session
(would mean changing the contract_id scheme, out of this session's Part
1-3 scope) — flagging precisely rather than leaving the discrepancy
unexplained.

**Not done this session, explicitly out of scope**: Mythril (separate
session per the task). Web3Bugs LLM baselines (no decision needed to
revisit — Slither-only coverage there is already well-documented and
expected). The council (Phase 3) is next.

## Session 6 (Phase 3): council built and wired, checkpoint before the eval run

`ollama list`: `llama3.2:3b`, `qwen2.5-coder:7b` — two genuinely different
models already installed, no pull needed.

Built `services/council.py` as a fully independent pipeline — does not
call or modify `run_full_analysis()`/`preanalyze_code()`/`_merge_vulns()`/
`_determine_verdict()` at all, just reuses `preanalyze_code()` (a pure,
deterministic utility) for `contract_name`/`features_detected` in the
returned schema. Three specialists, each pinned to an explicit model
(not the auto-detected single model `services/llm.py` uses):
- **Reentrancy** → `qwen2.5-coder:7b` (code-pattern specialist; reentrancy
  is a precise call-before-state-update pattern, code-tuned model fits)
- **AccessControl** → `qwen2.5-coder:7b` (same reasoning — missing-modifier
  is also a precise pattern, not a holistic judgment call)
- **BusinessLogic** → `llama3.2:3b` (semantic/intent judgment, not a
  literal pattern — general-purpose model gets this one)

So `qwen2.5-coder:7b` runs 2 roles, `llama3.2:3b` runs 1 — genuine
2-models-3-specialists diversity, not 3 parallel calls to the same
weights. Hosted (`--llm-backend groq`) mirrors this with Groq running 2
roles and Cerebras running 1 (`CEREBRAS_API_KEY`/`CEREBRAS_MODEL` added to
`.env.example` — **untested**, no Cerebras key available this session;
the Ollama path is what's actually getting exercised in step 3 below).

Aggregation judge is pure Python (no 4th LLM call), exactly per spec: a
finding is CONFIRMED if ≥2 of the 3 specialists independently flagged
something (regardless of which type each was scoped to — the signal is
cross-model agreement that *something*'s wrong, not type-matching, since
each specialist only ever reports its own single assigned type), OR if
exactly 1 specialist flagged something with confidence ≥0.8 AND a real,
substring-verified `evidence_quote` (whitespace-normalized both sides,
not a fuzzy match — `quote_appears_in_code()`). Verdict is NO-GO iff any
finding is CONFIRMED.

Added `"access_control"` (council's own type string) and
`"business logic"/"business-logic"/"business_logic"` → `"other"` to
`eval/taxonomy.py`'s `THIRDEYE_TO_DASP10` table — the council emits
`type` fields that didn't have exact-match entries before (the existing
table had `"access control"`/`"access-control"` with different
separators, and nothing at all for business-logic).

Wired into `eval/run_baselines.py`: `"council"` added to `BASELINES`,
`_run_council_baseline()` mirrors `_run_llm_baseline()`'s exact
retry/413/TPD-fail-fast logic, `_check_backend_config()` now also gates
on `council` and requires `CEREBRAS_API_KEY` specifically when
`--llm-backend groq` is combined with the council baseline. Checkpoints
log `council_models_used` (role/provider/model/found per specialist) —
the verifiable model-diversity log the spec asked for, not just an
assertion in a docstring.

Added `/api/analyze/council` to `main.py` — same `AnalyzeReq` schema as
`/api/analyze`, calls `run_council()` instead of `run_full_analysis()`,
`run_full_analysis()` itself untouched.

**Live sample result (eth-046_custodian_Bank.sol via Ollama)** — and a
real, slightly uncomfortable finding, reported honestly per the explicit
instruction not to tune anything based on it: the Reentrancy specialist
(`qwen2.5-coder:7b`) returned `found: false` on a contract whose
`Collect()` function has a textbook call-before-state-update reentrancy
bug (`.call{value: _am}` at one line, `acc.balance -= _am` only inside
the following `if (success)` block) — almost exactly the vulnerable
few-shot example in its own prompt. The BusinessLogic specialist
(`llama3.2:3b`) did flag *something* (confidence 0.7, quoting the `if`
condition line) but below the 0.8 single-specialist confirmation bar, so
nothing got CONFIRMED — council verdict: GO.

Checked this against ground truth before drawing any conclusion: this
contract is `eth-046` in the Etherscan-50 set, labeled `likely_safe` with
zero `vuln_categories`. So the council's GO verdict matches the dataset
label — but "likely_safe" in this dataset means "no publicly reported
exploit," not "formally verified safe," and the code pattern looks
genuinely reentrant by inspection (a malicious `msg.sender`'s fallback
could re-enter `Collect()` before `acc.balance` is decremented, draining
more than its real balance). Plausible explanation: this is real
ground-truth label noise in Etherscan-50 (a never-exploited-but-real bug),
not necessarily a council failure — but it could also just be the
specialist genuinely missing the pattern. No way to fully disambiguate
from one example. Did NOT touch the reentrancy prompt or thresholds in
response to this single case — that's tuning on test-set data, exactly
what the task explicitly forbids. The full 193-item run is the real
signal, not this one contract.

## Next: full council eval run (step 3) — 193 items, smartbugs_curated + etherscan50
