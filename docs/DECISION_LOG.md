# ThirdEye — research decision log

Chronological record of what was tried, what it measured, and why the approach
changed or stayed. Written for the supervisor review and as the raw material for
the paper's methodology section.

Rule followed throughout: **a result is only kept if the pipeline that produced
it can be shown to have been healthy.** Several early results failed that test
and were discarded — those discards are recorded here, not hidden, because the
reason for each is itself a finding.

---

## Phase 0 — Inherited state (pre-2026-08-04)

Prior sessions had produced a 1,152-contract local benchmark run reporting
~98% accuracy on safe tiers. It looked like a strong result.

**Decision: discarded entirely.** Diagnosis: the council pins `business_logic`
to `llama3.1:8b`, which was not installed. The router *always* selects
`business_logic`, so every contract had a guaranteed-erroring specialist. Where
only 2 specialists were selected, exactly 50% errored — which does **not** trip
the `>50%` fail-closed rule, so a half-dead council recorded a clean GO.
Tell-tale: median latency ~1s (instant model-not-found errors, not analysis).

**Why this mattered more than the lost run:** it established the project's
central methodological risk — LLM pipelines fail *silently and asymmetrically*.
A dead specialist can only fail to raise a flag, never raise a false one, so
every silent failure biases toward GO (i.e. toward "safe"). Archived, not
deleted, under `eval/checkpoints/_invalid_2026-08-04_missing_models/`.

---

## Phase 1 — Making the harness trustworthy (2026-08-04 → 08-05)

Seven distinct defects were found, each of which produced *plausible* numbers.
Full table in `PAPER_DRAFT.md` §5. The ones that changed the design:

| # | Defect | Why it mattered | Decision |
|---|---|---|---|
| 1 | Missing pinned model (above) | half-dead council → clean GO | install models; archive run |
| 2 | Partial-council results treated as terminal | 32/198 rows had errored specialists — **100% of them GO** | terminal only if the whole council ran |
| 3 | Provider quota drain → INCONCLUSIVE checkpointed as terminal | bakes a transient outage permanently into recall | transient results quarantined in `_transient/`, retried |
| 4 | Arbitration silently defaulted to hosted whenever a key existed | a run invoked as "local" was making hosted 120B calls | arbitration follows the run's backend |
| 5 | Arbiter config keyed on names the caller never passes | hosted runs adjudicated by a **local 8B judge**; nothing in the output said so | explicit mapping; fail loudly on unknown key |
| 6 | Subsampling by `items[:N]` | filename order clusters by project — the "sample" was 263 consecutive OpenZeppelin files | seeded **nested** stratified sampling |
| 7 | Health probe timeout (60s) < cold model load (90–230s) | aborted a healthy backend | probe timeout derived from measured cold start |

**Sampling decision (defect 6) is worth calling out.** Replaced first-N with
shuffle-once-then-prefix, so N=10 ⊂ N=25 ⊂ N=50. Consequence: a small run
extends into a larger one reusing every checkpoint, and the population never
silently changes. This is what made "run small now, extend overnight" free.

---

## Phase 2 — Hardware feasibility (2026-08-05)

**Question:** can a model-diverse council run locally, as the "free tier"
selling point claims?

**Measured on RTX 3050 (4GB VRAM / 15.7GB RAM):**
- Only ONE model is GPU-resident; every other runs CPU-only at 224–270s/call
  **regardless of size** — the 2.0GB model was slower than the 4.7GB one when
  the latter held the GPU. Residency, not parameter count, is the variable.
- Model switching costs 72–229s.
- **Decision: group specialists by model** (all of model A's roles, then B's).
  Scheduling change only — same models, prompts, seeds, aggregation, so verdicts
  are unaffected. Effect: specialist errors went 1/2, 2/3, 4/4 → **0/6, 0/4, 0/1**.
- **Decision: `llama3.1:8b` → `llama3.2:3b` for logic roles.** The 8B does not
  fit 4GB and failed under memory pressure; it sat on `business_logic`, which
  always runs, so every contract paid it. Three model families preserved.
- **Attempted and rejected: a stronger local judge.** Pulled `qwen3:8b` (newest
  8B generation). On the documented `eth-046` regression case: `llama3.1:8b`
  dropped 4/4 findings, `qwen3:8b` upheld 4/4 — neither discriminates, and
  qwen3 was 3× slower (thinking model). A 14B judge (~9GB) will not fit at all.
  **Conclusion: consumer hardware has a real ceiling for a judge.** Reported as
  a negative result rather than shipping a gate that is a no-op.

---

## Phase 3 — First trustworthy numbers (2026-08-05 → 08-06)

Local council, arbitration off, nested stratified sample.

| n | recall (vuln) | FPR (safe) |
|--:|--:|--:|
| 40 | 0.850 | 60% |
| **121** | **0.868** | **65%** |

Agreement between n=40 and n=121 established the finding as robust to sample
size. Per-tier: injected **15/15**, curated 19/22, real audit-report 12/16.
Zero abstentions.

**Decision: arbitration disabled for the main run.** Rationale at the time: it
was burning ~125s/contract retrying a drained hosted quota and achieving
nothing, and running it locally would have shipped a gate measured to be a
no-op. Recorded as a council-only ablation row rather than presented as the
full pipeline.

---

## Phase 4 — Baseline comparison (2026-08-06)

**Problem identified:** the GPTScan/GPT-4o-mini numbers being quoted are from
other papers on other datasets. That is context, not comparison, and a reviewer
would reject it. **Decision: run a real baseline on identical contracts.**

Slither, same contracts, same ground truth, same nested sample. Verdict rule
stated explicitly (NO-GO iff ≥1 High/Medium detector); compile failures treated
as abstentions, not silent passes.

| tool | precision | recall | F1 | FPR | scored |
|---|--:|--:|--:|--:|--:|
| ThirdEye council | 0.840 | **1.000** | 0.913 | 0.500 | **121** |
| Slither | **0.947** | 0.857 | 0.900 | **0.125** | 46 |

**Two findings.** (a) F1 is effectively tied — neither dominates; this is a
trade-off characterisation, not a win. (b) **Coverage bias:** Slither abstained
on 69%, and non-randomly — it compiled 36/75 vulnerable (old, simple files) but
only 10/75 safe (modern OZ/Solady needing exact solc). Static-analyser accuracy
on corpora like this is therefore measured on a subset selected for being easy
to compile. The council needs no compilation and has no such subset.

---

## Phase 5 — Arbitration: negative result, then reconsidered (2026-08-06)

**Experiment:** re-adjudicate every council NO-GO, split by ground truth.

- False positives corrected: **9/12 (75%)**
- True positives destroyed: **12/17 (71%)**

| config | FPR | precision | recall | F1 |
|---|--:|--:|--:|--:|
| council only | 60% | 0.586 | 0.850 | **0.694** |
| council + arbitration | 15% | 0.625 | 0.250 | **0.357** |

**Decision: rejected as a binary gate.** It drops real and spurious findings at
similar rates — suppression, not discrimination — halving F1.

**Decision: NOT abandoned as a mechanism.** The judge emits a
`calibrated_confidence` that the binary gate discards. Converting it to a
monotone score (`p_real = conf if "real" else 1−conf`) and sweeping a threshold
turns one bad operating point into a curve. Early evidence the score is
informative:

```
findings on SAFE contracts:       mean p_real 0.230
findings on VULNERABLE contracts: mean p_real 0.629
```

**Process note:** at n=1 vulnerable contract the separation looked negligible
(0.126 vs 0.197) and the mechanism looked dead. It was not — the ordering was
the problem (below). A conclusion was nearly drawn from a one-sample artifact.

**Decision: interleave collection order by ground truth.** Contracts were
processed in ID order, so all 44 safe (`01_*`) preceded all 46 vulnerable
(`02_*`). Under a quota-throttled multi-day run that means collecting only one
class for the entire first half, and the sweep needs both. Now alternating, so
any partial result is a balanced sample.

---

## Phase 6 — Structural analysis of the method (2026-08-06)

Two flaws found by analysing existing checkpoints — no new inference.

**Flaw A: the council is an OR-gate, so FPR compounds with ensemble size.**
A contract is NO-GO if *any* specialist yields one surviving finding — a logical
OR over k detectors, so contract-level FP ≈ 1−(1−p)^k.

| specialists run | n safe | FP rate |
|--:|--:|--:|
| 1 | 10 | 50% |
| 2 | 18 | 61% |
| 3 | 21 | 71% |
| 4 | 11 | 73% |

Model diversity is simultaneously what buys recall and what destroys precision —
the same mechanism. No prompt tuning fixes an aggregation rule.

**Flaw B: specialists differ wildly in precision but are weighted equally.**

| class | on SAFE | on VULN | precision |
|---|--:|--:|--:|
| business_logic | 18 | **0** | **0.00** |
| dos_gas | 18 | 2 | 0.10 |
| reentrancy | 2 | 2 | 0.50 |

Two of eight specialists produce 65% of false-positive findings and 18% of the
true ones — and `business_logic`, precision 0.00 here, is the class the router
*always* fires.

**Decision: replace the OR-gate with per-class calibrated noisy-OR.**

```
risk = 1 − Π_i ( 1 − w_class(i) · p_real(i) )        NO-GO iff risk ≥ τ
```

Chosen because it (a) attacks the measured failure rather than a guessed one,
(b) requires **zero new LLM calls** — a different aggregation over scores already
collected, so it is evaluated offline, and (c) reports an operating *curve*
instead of a single point.

**Prerequisite identified:** checkpoints stored only `n_findings`, so
aggregation experiments were limited to the 26 arbitrated contracts. Schema
enriched to record per-finding class and confidence for every contract, so one
run now supports many offline experiments.

---

---

## Phase 7 — The control that changed the claim (2026-08-08)

The weighted noisy-OR changes TWO things at once versus the OR-gate: it adds
per-class reliability weights AND a confidence threshold. Before claiming the
weighting as the contribution, we ran the obvious control — threshold with every
weight fixed at 1.

| rule | precision | recall | F1 | FPR |
|---|--:|--:|--:|--:|
| OR-gate (current) | 0.555 +/- 0.020 | 0.935 +/- 0.020 | 0.696 +/- 0.019 | 0.655 |
| **threshold only (no weights)** | **0.730 +/- 0.023** | 0.857 +/- 0.049 | **0.787 +/- 0.027** | **0.277** |
| weighted noisy-OR | 0.717 +/- 0.036 | 0.848 +/- 0.125 | 0.771 +/- 0.047 | 0.298 |

**The weighting does not earn its place.** Threshold-alone scores higher and has
roughly half the variance; the weighted variant wins only 4/10 splits. Weights
estimated from small per-class counts added noise, not signal.

**Decision: report the simpler rule.** The contribution is "replace the OR-gate
with a confidence-thresholded noisy-OR", not "weight the specialists". Fewer
parameters, better numbers, lower variance, and nothing to tune per deployment.

**Why this is recorded rather than quietly swapped:** the weighted version was
the headline for two days and is already written into an earlier draft. A
reviewer would have run this exact control — it is the first thing anyone asks
when a method changes two variables simultaneously. Finding it ourselves is the
difference between an ablation and a retraction.

---

---

## Phase 8 — Shipping the fix, and re-measuring the rest (2026-08-08)

An independent precision review (`ThirdEye_FPR_Reduction_Critique`) raised 33
recall-safe levers for cutting FPR. Its headline was the important one.

### The headline was correct and severe

**The fix that works was not the fix that was running.** The paper's result
(threshold-only on pooled noisy-OR risk) lived exclusively in
`eval/weighted_aggregation.py`. `council.py::_aggregate` shipped a per-finding
0.6 floor followed by `if any finding survived -> NO-GO` — which is that same
rule at tau -> 0. We were reporting 28% FPR from a rule the product did not
implement.

**Decision: ported it.** `_contract_risk()` computes `1 - PROD(1 - conf_i)`
over findings that clear the evidence gate; the verdict blocks iff
`risk >= RISK_TAU`. tau = 0.925, chosen identically in 8 of 10 dev splits.
The port is faithful by construction — it mirrors the offline `risk()` with all
weights = 1, including its treatment of a missing confidence as 1.0, so the live
verdict and the offline measurement cannot drift.

Verified by replaying all 233 checkpoints through the LIVE function:

| rule | FPR | recall | F1 | false alarms |
|---|--:|--:|--:|--:|
| OR-gate (was shipping) | 63.7% | 0.927 | 0.699 | 79 |
| risk >= 0.925 (now shipping) | 28.2% | 0.844 | 0.780 | 35 |

Per-class weights remain excluded — the earlier control disproved them.

### The other levers did NOT survive measurement

The review described structural suppression (stateless libraries, per-class
preconditions) and severity policy as "free wins, recall-safe by construction".
Measured individually on top of the threshold:

| lever | FPR | recall | F1 | verdict |
|---|--:|--:|--:|---|
| threshold only | 28.2% | 0.844 | 0.780 | the win |
| + stateless/library gate | 27.4% | 0.835 | 0.778 | ~neutral |
| + reentrancy precondition | 28.2% | 0.844 | 0.780 | no effect |
| + proxy precondition | 28.2% | 0.844 | 0.780 | no effect |
| + dos_gas precondition | 27.4% | 0.807 | 0.762 | **harmful** |
| + severity policy | 25.0% | 0.789 | 0.761 | **harmful** |

**Why the estimates were wrong: the levers overlap.** The review sized each
against the OLD 64% baseline ("12 of 79 false positives were pure libraries").
But the threshold fix already removes 44 of those 79 — including most of the
library cases — so the residual 35 is a smaller and harder population with far
less headroom than the item-by-item arithmetic suggests.

**Instructive failure.** The `dos_gas` precondition cost 4 true positives to
remove 1 false alarm. The contracts it silenced (`dvl_dirtybytes`,
`dvl_privatedata`) ARE vulnerable — but not to DoS. The finding had been scoring
as a true positive *for the wrong reason*, because scoring is contract-level
rather than class-level. Worth stating in the paper: contract-level scoring
credits right-verdict/wrong-reason findings, which flatters any per-class
analysis built on top of it.

**Decision: ship the threshold plus only the two preconditions that measured
non-harmful; drop the dos_gas precondition and the severity policy.** Final
shipped configuration, n=233:

| | FPR | recall | F1 | FP | FN |
|---|--:|--:|--:|--:|--:|
| before | 63.7% | 0.927 | 0.699 | 79 | 8 |
| **after** | **26.6%** | 0.835 | **0.781** | **33** | 18 |

Per safe tier, the residual now tracks label trust — 19% on audited libraries,
25% audit-reviewed-clean, 34% real-world-no-bug-reported — which is the ordering
expected if the weakest-labelled tier carries unreported real bugs.

---

## Standing decisions (things deliberately NOT done)

- **No larger dataset.** 2,250 labelled contracts exist; 121 have been used.
  The bottleneck is inference throughput, not data. Adding contracts adds
  nothing processable.
- **No dynamic exploit confirmation.** Auto-harness generation for arbitrary
  contracts is an open problem; the bundled reentrancy PoC is real but
  template-based. Off by default, claimed as scaffold only.
- **No retrieval-in-prompt.** Precedents are surfaced but not injected, so
  retrieval does not affect verdicts. Stated rather than implied.
- **No tuning on test data.** Thresholds are to be fit on a dev split and
  reported with curves.

---

## Cross-hardware reproducibility (2026-08-21, campus NVIDIA GB10)

Campus GPU access (DGX Spark, GB10, 119 GB unified) let us ask a question the
project had never been able to ask: **does the same contract get the same
verdict on different hardware?** The shipped n=233 was measured entirely on one
4 GB laptop GPU. If it does not reproduce, every headline number is partly a
property of that laptop rather than of the method.

Method: the same 233 contract ids, the same seed, the same no-arbitration
config, replayed on the GB10. Throughput 28.8 min vs 4.8 h on the laptop (~10x).

**Two comparison traps had to be closed before the numbers meant anything.**

1. **The stored `verdict` field is the OLD OR-gate rule.** The shipped noisy-OR
   result is produced by replaying checkpoints through `stats._shipped_rule`
   (`_contract_risk` + `suppress`), not by reading `verdict`. A first pass
   compared stored-laptop against live-DGX and "found" a 0.75 agreement with all
   flips running one direction — that was measuring our own rule change. Both
   sides must be replayed through one rule. `eval/parity_rescore.py` does this by
   importing the live functions rather than reimplementing them a fourth time.

2. **`num_ctx` is never set by the application.** It inherits the Ollama server
   default: 4096 on the laptop's 0.24.0, but the model maximum (131072) on
   current builds — which would silently stop truncating long contracts. Pinned
   to 4096 on both sides. (It also inflates the KV cache to ~62 GB for a 3B
   model and evicts the rest of the council.)

Result, n=230 scored, one identical rule:

| | agreement | FPR | recall |
|---|--:|--:|--:|
| laptop (replayed) | — | 27.3% | 0.835 |
| GB10 | **0.813** (95% CI 0.763–0.863) | **40.5%** | 0.862 |

The laptop's 27.3% reproduces the shipped 26.6%, which validates the replay.
But the same code on other hardware moves the headline false-alarm rate by 13
points, and the 43 disagreements are asymmetric — 31 GO→NO-GO against 12 the
other way. That is a systematic shift, not symmetric kernel jitter.

**This is NOT yet reportable as hardware nondeterminism.** Three variables moved
together: GPU, Ollama build (0.24.0 → 0.32.15), and batch parallelism
(`OLLAMA_NUM_PARALLEL` 1 → 4, which we set). Model digests are byte-identical on
both machines (`a80c4f17acd5`, `46e0c10c039e`, `dae161e27b0e`, `a2af6cc3eb7f`),
so weights and their sampling defaults are excluded. Batching is the leading
suspect precisely because it predicts a *directional* skew: batched inference
changes GEMM shapes and reduction order, so logits shift and a fixed seed no
longer pins the sampled token.

**Open, and blocking any claim here:** a `NUM_PARALLEL=1`, one-contract-in-flight
arm reproducing the laptop's serving config exactly. If agreement jumps, the
finding is "batched serving perturbs verdicts" — narrower, more actionable, and
still novel. If it holds near 0.81, the reproducibility problem is real. Not
separable in general: Ollama 0.24.0's CUDA build has no arch for compute 12.1
and will likely not run on a GB10 at all.

### Capacity ablation (llama3.1:8b), n=24 pilot

`council.py` pins business_logic / oracle_price_manipulation / flashloan_mev to
`llama3.2:3b` solely because `llama3.1:8b` (4.9 GB) does not fit in 4 GB of
VRAM — a hardware compromise sitting on the three *semantic* roles. Restoring
the 8B is a one-variable change the GB10 makes possible.

Pilot result (n=24, 12 safe / 12 vulnerable, same seed, same rule):

| arm | misses | false alarms | accuracy |
|---|--:|--:|--:|
| llama3.2:3b | 2 | 6 | 0.667 |
| **llama3.1:8b** | **0** | **9** | 0.625 |

The 8B caught every bug it had been missing and raised three more false alarms.
All five differing verdicts moved the same direction (GO→NO-GO). Median latency
was unchanged (24.1 s vs 24.4 s).

If it holds at n=233, this is direct evidence for the paper's thesis: **more
model capability made the crying-wolf worse, not better.** It answers the
obvious reviewer objection — "why not just use a bigger model?" — with our own
data, and it argues the lever is aggregation, not capability. The n=233 arm is
~223/233 computed and resumes on next campus access.


---

## 2026-08-28 — Campus GB10 session

### The 8B capacity ablation, at full n

The n=24 pilot held. Final arm, n=233 (232 scored, 1 inconclusive):

| | DGX / llama3.1:8b | laptop / llama3.2:3b |
|---|--:|--:|
| accuracy | 0.651 | 0.625 |
| median latency | 22.6 s | 60.6 s |
| agreement with laptop | 0.767 | — |

Note the confound this arm does NOT resolve: it varies model AND hardware AND
Ollama version at once. The `NUM_PARALLEL=1` control (n=233, 227 scored) is the
lever that separates serving config from the rest.

### The GPTScan head-to-head had never run

`run_web3bugs --gptscan-set` reads `datasets/gptscan/comparison_set.json`, which
lives at the repo root. `TUESDAY_START.sh` synced only three `backend/` paths,
so the file was never on the box: the stage died with `FileNotFoundError` on
every session, and the session script logged it as `stopped at budget`. The
failure read as a clock problem for weeks. It needed **zero** new GPU time —
63 of the projects were already checkpointed.

Two further defects in the same path, both of which would have put a wrong
number in the paper:

* `--report-only` ignored `--gptscan-set` and globbed every checkpoint, so "the
  GPTScan comparison" silently reported the whole 91-contest sweep.
* Both runs wrote `web3bugs_bench.json`, so whichever finished last became "the"
  web3bugs result.

### The comparison was unfair in our favour, twice

**Wald at the boundary.** 63/63 printed as `100.0% [100.0-100.0]` — perfect
certainty claimed from a finite sample, on a project whose thesis is that rates
are published without their uncertainty. Backend and exhibit both moved to
Wilson. This also tightened the headline FPR from `[25.7, 33.2]` to
`[26.8, 32.2]`.

**Scoring GPTScan on questions it was never asked.** Collapsing their per-project
rule-check counts to "detected if tp > 0" counted 34 of 72 projects as misses.
Those have `tp = 0` AND `fn = 0`: their ten rule types had no applicable check
there at all. That single error dragged their apparent rate from ~91% to ~49%
and would have been fatal in review.

Recall is now computed only over projects where GPTScan had a positive to find:

| on 34 gradable projects | detected | |
|---|--:|---|
| ThirdEye | 33/34 | 97.1% [85.1, 99.5] |
| GPTScan | 31/34 | 91.2% [77.0, 97.0] |

**Intervals overlap — no detection difference is demonstrated.** That is the
result, and claiming a win across overlapping intervals would forfeit the
paper's own argument.

The real finding is **scope**, reported separately and never merged into recall:
29 of the 63 shared projects carry a confirmed bug outside GPTScan's rule set,
and ThirdEye returns a verdict on all 29. Coverage is not accuracy — an
any-slice flag on an all-positive set is nearly free.

Positioning that follows: **comparable detection where both tools apply, on
roughly twice the applicable projects, at a false-alarm cost we measure and they
do not have to pay** (their published precision 0.571; our FPR 29.4% on buckets
01/02 — different negative sets, never subtracted).

### `LLM_TIMEOUT` was dead code, and it was biasing the sample

`_query` does `timeout or LLM_TIMEOUT`, and `_run_specialist` passed
`timeout=240` explicitly, so the env var never governed anything on any machine.
`arbitration.py` had two more hardcoded 240s and never imported `LLM_TIMEOUT`.

This is a validity bug, not a throughput one. With N contracts in flight x 8
specialists against `OLLAMA_NUM_PARALLEL`, requests queue, and queue wait counts
against the client-side deadline. A blown deadline fails closed to INCONCLUSIVE
and quarantines the contract — and the calls that blow it are the **large,
complex** contracts. The discards are not random, so the scored sample skews
toward simpler code.

Measured on the GB10 before the fix: 9 INCONCLUSIVE in 39 contracts (23%), with
deaths clustered at 303.0 s, 303.4 s and 405.4 s — the signature of a 240 s
per-call cap plus queueing. Stage B was relaunched with the fix live and
`--retry-quarantined`.

### Operational: a pkill that killed its own launcher

`TUESDAY_START.sh` ran `pkill -f 'dgx_tue[s]day'` to clear a stale session. The
bracket stops the *pattern* matching itself, but the same command line contains
the literal path `.../dgx_tuesday.sh`, so pkill matched the shell running the
launch and killed its parent. ssh died with 255 before the launch line ran, and
the script reported success because it never checked ssh's exit code. It now
refuses to double-start and verifies the process exists rather than inferring it
from `rc=0`.

### Verifying GPTScan against the paper, not just its CSV

Checked the published paper (arxiv.org/abs/2308.03314) rather than trusting the
results file alone. The parse reproduces the published table exactly: tp 40,
fp 30, tn 154, fn 8 over 232 counts, giving 57.14% / 83.33% / 67.8%. (A search
summary claiming "recall 71.43%" for Web3Bugs is wrong; the paper's Web3Bugs row
is 83.33%, and the abstract's "over 70%" is a cross-dataset statement.)

Two things the paper settles that we had been inferring:

**The unit.** Scoring is at the function level *for each tested vulnerability
type* — "if a project tested five vulnerability types, each would contribute one
count". A count is a project x rule-check.

**The true-negative definition licenses our gradable subset.** A TN is a tested
type that lacks a corresponding ground-truth vulnerability in that project.
So `tp = 0 and fn = 0` means there was no positive of the relevant type to find.
Restricting the detection comparison to projects with `tp + fn > 0` is therefore
required by their own definition, not a choice of ours. The earlier version that
scored those 34 projects as GPTScan misses was wrong by their definition, not
merely unfair.

**A fairness correction the paper forced.** GPTScan targets ten DeFi logic types
and DELIBERATELY excludes reentrancy and integer overflow, on the premise that
pattern-based tools already cover those and that ~80% of Web3 bugs cannot be
audited by them. Its narrower project coverage is a design decision in service of
that premise. Our draft had presented "roughly twice the applicable projects" as
a differentiator; that reads as claiming credit for someone else's deliberate
scoping. It is now reported as a difference in TARGET POPULATION — our taxonomy
is broader, which is a different claim from being better at the task GPTScan set
itself.

### The context-truncation ablation (result)

Paired on contract id, 36 pairs / 20 scored in both arms, one variable (num_ctx):

| | 4,096 (shipped) | 16,384 |
|---|--:|--:|
| abstained | 44.4% [29.5, 60.4] | 0.0% [0.0, 9.6] |
| accuracy | 25.0% | 75.0% |
| recall | 12.5% | 81.2% |
| median latency | 402.9 s | 108.2 s |

McNemar on the discordant pairs: 12 vs 2, chi2 = 5.79, **p = 0.016**. Latency:
faster on **20/20**, x4.01, exact sign test p < 0.0001. 14/20 verdicts flipped,
13 of them GO -> NO-GO on genuinely vulnerable contracts.

The finding behind the finding: abstentions are excluded from scoring, so this
did not depress any published number — it deleted rows and left healthy-looking
tables. A configuration failure that hides itself in exactly the way this project
accuses the field of doing.

Bounds, stated because they matter: measured only on the overflowing 24% of the
corpus; the FPR arm rests on 4 safe contracts and is not claimed; the extreme
tail was excluded on cost grounds (decided from latency alone, before any verdict
was inspected), so everything above is a LOWER bound.

### Safe-class context ablation — PRELIMINARY, and it points the wrong way

The mixed ablation left the false-alarm question on n=4. A safe-only arm was run
to answer it. **Partial at time of collection** (21 paired; the 4,096 control was
still running on the box and will be complete on the next visit):

| | 4,096 | 16,384 |
|---|--:|--:|
| abstained | 47.6% [28.3, 67.6] | **0.0%** [0.0, 15.5] |
| FPR (paired subset) | 27.3% [9.7, 56.6] | **63.6%** [35.4, 84.8] |

The abstention intervals **separate**, replicating the vulnerable-class result on
the safe class: truncation was removing these contracts from scoring altogether
(the completed 16,384 arm abstains on 2 of 70; the control on roughly half).

The false-alarm direction is the uncomfortable one. On the paired subset it
**rises** with a correct context window, and the completed treatment arm sits at
45.6% [34.3, 57.3] over 68 scored contracts. If that holds, the contracts
truncation was hiding are disproportionately the ones the council false-alarms
on, and the reported 29.9% is an UNDER-estimate rather than a conservative one.

NOT YET A RESULT, and must not be quoted as one:
- 21 paired, 4 discordant, McNemar p = 0.13 — underpowered by our own rule.
- The 16,384 arm's 45.6% is on the OVERFLOWING safe population only (large
  contracts), which may draw more alarms regardless of window.
- It is the raw verdict, not the shipped noisy-OR rule that produces 29.9%.
  Cross-referencing the two without a shipped-rule replay would repeat exactly
  the rule-mixing error caught earlier in this session.

Next visit: let the control arm finish (it was budgeted to ~18:30 and
checkpoints), then replay both arms through the shipped rule before comparing
anything to the headline.
