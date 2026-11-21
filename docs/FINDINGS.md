# ThirdEye — findings register

Every finding the project has produced, with its **current status**. The
companion to `DECISION_LOG.md`: that file is chronological and records *how* we
got here; this one is indexed by claim and answers *what do we currently
believe, and how much*.

Maintained because a two-month project accumulates results faster than it
retires them, and a finding that was superseded three weeks ago is more
dangerous than one that was never made — it reads as settled. Nothing here is
deleted when it is overturned; it is marked and the replacement is linked.

**Status vocabulary**

| tag | meaning |
|---|---|
| **SOUND** | measured on a healthy pipeline, replayable from checkpoints, no known confound |
| **SOUND (scoped)** | solid within a stated scope; does not generalise past it |
| **HYPOTHESIS** | measured effect, but selected post-hoc or otherwise not yet validated |
| **RETRACTED** | was reported, now known wrong or unearned; kept for the record |
| **SUPERSEDED** | correct when made, replaced by a better measurement |
| **UNSOUND** | the pipeline that produced it was not healthy; must not be cited |
| **OPEN** | identified, not yet measured |

Last updated 2026-10-24. Cross-references are to `DECISION_LOG.md` phases.

---

## A. Headline results — the paper's spine

### A1. Safe-label provenance changes the false-alarm rate · **SOUND (effect)** / **RETRACTED (interpretation)**
Same tool, same contracts, same decision rule. Only the *origin* of the "safe"
label varies. Regenerated 2026-10-24 on all 1,046 safe rows of the full corpus
(evidence gate, Wilson intervals):

| safe tier | n | FPR |
|---|--:|--:|
| audited_library | 273 | **27.8%** [22.9, 33.4] |
| realworld_no_bug_reported | 192 | **44.8%** [37.9, 51.9] |
| audit_reviewed_clean | 581 | **54.7%** [50.7, 58.7] |

**The effect is real and larger than reported**: a 26.9-point spread against the
earlier 21.8, and the `audited_library` / `audit_reviewed_clean` intervals do not
overlap. The claim that label provenance moves the headline more than
tool-versus-tool differences stands, and strengthens.

> **The interpretation does not survive.** Phase 8 reported the per-tier
> residual as 19% / 25% / 34% — **monotonic in label trust** — and that
> monotonicity was the whole argument that the residual is *unreported real
> bugs* rather than tool error: the weakest-labelled tier should carry the most
> hidden bugs. At full corpus the ordering **inverts**: `audit_reviewed_clean`
> is the *worst* tier (54.7%), above `realworld_no_bug_reported` (44.8%).
> Whatever drives the spread, it is not a clean gradient in label quality.
> Do not cite the "residual tracks label trust" reading. The superseded figures
> came from the n = 1,154 replay (see E6); the earlier ordering was an artifact
> of the half corpus.
>
> **Confound found and measured — see A4.** `audited_library` runs a median of
> **2** specialists against **3** for both other tiers, and false alarms
> compound with ensemble size (B1). Stratifying by k, the tier effect
> **vanishes at k = 2** (18.9 / 15.3 / 18.7, intervals fully overlapping) and
> appears only at k ≥ 3. Provenance survives as a within-stratum effect but is
> **substantially smaller** than the marginal comparison shows, and the
> inversion of the ordering is plausibly a composition artifact. **A1 must be
> reported stratified by k, or with ensemble size as a stated covariate — the
> marginal 27.8% vs 54.7% overstates it.**

*Phase 8, regenerated Phase 10.*

### A2. The decision rule moves the headline more than any model change · **SOUND**
On **identical verdicts** over 2,142 asym-sound contracts, false alarms move
**72.2% [69.4, 74.8] → 45.9% [42.9, 48.9]** depending only on which rule reads
the stored findings. Recall 95.9% → 89.1%. *Phase 9, regenerated Phase 10.*

### A4. How many specialists ran dominates the false-alarm rate · **SOUND**
On the same safe contracts, scored the same way, false alarms rise
monotonically with the number of specialists the router actually fired:

| k (specialists run) | audited_library | realworld_no_bug | audit_reviewed_clean |
|--:|--:|--:|--:|
| 1 | 16.0% [8.3, 28.5] | 11.1% [3.1, 32.8] | — |
| 2 | 18.9% [12.1, 28.2] | 15.3% [8.2, 26.5] | 18.7% [12.8, 26.5] |
| 3 | 26.8% [17.9, 38.1] | 53.1% [36.4, 69.1] | 42.0% [34.6, 49.7] |
| 4 | 41.9% [28.4, 56.7] | 62.2% [47.6, 74.9] | 69.3% [60.3, 77.0] |
| 5 | 68.8% [44.4, 85.8] | 75.0% [56.6, 87.3] | 84.6% [75.8, 90.6] |
| 6 | — | — | 90.2% [80.2, 95.4] |

**16% at k = 1 to 90.2% at k = 6** — a larger movement than any other single
factor in this register, on a quantity the user never sees and never chooses.
This is B1's OR-gate compounding (FP ≈ 1−(1−p)^k) measured directly rather than
inferred, and it is the mechanism underneath A1, C1 and C3:

- **It confounds A1.** At k = 2 the three provenance tiers are
  indistinguishable (18.9 / 15.3 / 18.7, intervals fully overlapping). The tier
  spread only appears at k ≥ 3, and `audited_library` carries
  disproportionately many low-k contracts. A residual tier effect survives
  within each stratum (library stays lowest at k = 3, 4, 5), so provenance is
  real — but much smaller than the marginal 27.8% vs 54.7% implies.
- **It predicts C3's mechanism (whose magnitude is retired).**
  `business_logic` is always selected by the static router, so it adds 1 to k
  on *every* contract; excluding it reduces ensemble size by one corpus-wide,
  which is a topology change rather than a threshold change. The in-sample
  **+8.3 points of recall did not reproduce out of sample** — see the C3
  out-of-sample block (§C3). Mechanism stands, magnitude does not.
- **It explains C1's floor.** Thresholding cannot undo an OR over k detectors;
  it can only raise the bar each detector must clear. The floor is a property of
  the aggregation topology, not of the threshold.

*Phase 10, 2026-10-24. Offline over `eval/checkpoints/benchmark/*/seed*/`.*

### A3. A silently truncating context window breaks the council structurally · **SOUND**
Measured per specialist *call*, not per contract:

| arm | calls failed | rate [95% Wilson] |
|---|--:|---|
| VULN 4k | 36/92 | 39.1% [29.8, 49.3] |
| VULN 16k | 14/437 | 3.2% [1.9, 5.3] |
| SAFE 4k | 43/97 | 44.3% [34.8, 54.2] |
| SAFE 16k | 11/485 | 2.3% [1.3, 4.0] |

z = 10.71, p = 9.5e-27 and z = 13.03, p = 7.8e-39. **Twelve contracts at 4k
returned GO from a council in which one to three specialists never ran; at 16k
that happened zero times.** *Aug 28 session; reframed Phase 9.*

> Supersedes the earlier framing of A3 as a recall effect (12.5% → 81.2%,
> McNemar p = 0.0162, 4.01× slower). That rested on 20 paired rows of which
> exactly **one** had an intact council in both arms — see A3-R.

### A3-R. Context window as a recall effect · **RETRACTED**
"Recall 12.5% → 81.2%, p = 0.0162, while running 4.01× slower." Removed from
the abstract. The paired subset had one usable row. Replaced by A3, which is
stronger and rests on 1,111 specialist calls.

---

## B. The method itself

### B1. The council is an OR-gate, so false positives compound with ensemble size · **SOUND**
A contract is NO-GO if *any* specialist yields one surviving finding — a logical
OR over k detectors, so contract-level FP ≈ 1−(1−p)^k. Measured:

| specialists run | n safe | FP rate |
|--:|--:|--:|
| 1 | 10 | 50% |
| 2 | 18 | 61% |
| 3 | 21 | 71% |
| 4 | 11 | 73% |

Model diversity is simultaneously what buys recall and what destroys precision.
No prompt tuning fixes an aggregation rule. *Phase 6.*

### B2. The fix that worked was not the fix that was running · **SOUND**
The reported result (threshold on pooled noisy-OR risk) existed only in
`eval/weighted_aggregation.py`; `council.py::_aggregate` shipped a per-finding
0.6 floor plus "any survivor → NO-GO", i.e. the same rule at τ→0. **We were
reporting 28% FPR from a rule the product did not implement.** Ported; replaying
all 233 checkpoints through the live function: OR-gate 63.7% FPR / 0.927 recall
→ risk ≥ 0.925 at 28.2% / 0.844. *Phase 8.*

### B3. Per-class specialist weighting does not earn its place · **SOUND**
The control that varies one thing at a time:

| rule | precision | recall | F1 | FPR |
|---|--:|--:|--:|--:|
| OR-gate | 0.555 ± 0.020 | 0.935 ± 0.020 | 0.696 | 0.655 |
| **threshold only** | **0.730 ± 0.023** | 0.857 ± 0.049 | **0.787** | **0.277** |
| weighted noisy-OR | 0.717 ± 0.036 | 0.848 ± 0.125 | 0.771 | 0.298 |

Threshold-alone scores higher with roughly half the variance; weighting wins
only 4/10 splits. Weights estimated from small per-class counts added noise, not
signal. The contribution is "replace the OR-gate with a confidence-thresholded
noisy-OR", not "weight the specialists". *Phase 7.*

### B4. Most "recall-safe, free win" FPR levers are neither · **SOUND**
Measured individually on top of the threshold: stateless/library gate ~neutral
(27.4%), reentrancy and proxy preconditions no effect, **dos_gas precondition
harmful** (recall 0.844 → 0.807), **severity policy harmful** (recall → 0.789).
The levers overlap: each was sized against the old 64% baseline, but the
threshold already removes 44 of those 79 false alarms, leaving a smaller and
harder residual. *Phase 8.*

### B5. Contract-level scoring credits right-verdict/wrong-reason findings · **SOUND**
The `dos_gas` precondition cost 4 true positives to remove 1 false alarm. The
contracts it silenced (`dvl_dirtybytes`, `dvl_privatedata`) **are** vulnerable —
but not to DoS. The finding had been scoring as a true positive for the wrong
reason. Any per-class analysis built on contract-level scoring inherits this
flattery. *Phase 8.*

### B6. The third decision rule is the second one re-derived · **SOUND**
Noisy-OR at τ = 0.925 is **identical to the evidence gate in every cell** and
the two disagree on **0 of 2,142** contracts — because `council.py:472` defines
the shipped verdict as `risk = 1 − Π(1 − conf_i)`, `NO-GO iff risk ≥ RISK_TAU`,
with `RISK_TAU = 0.925` at line 484. τ sweep: 191 disagreements at 0.90, **0**
at 0.925, 1 at 0.95, 108 at 0.99 — the zero sits exactly on the shipped
threshold. Report **two** measured steps, not three. A reader proposing noisy-OR
pooling as an improvement would be proposing this tool's own rule. *Phase 9.*

### B7. The published three-step decomposition is not replayable · **SUPERSEDED**
The 59.0% → 37.5% → 30.2% chain. The third column is a different function of
data the checkpoints do not store (post-suppression findings), since any
noisy-OR over data they *do* store is the second column. Earlier diagnosis
("lands 2 contracts off, unexplained") understated it. See B6.

---

## C. Configuration — what we should actually ship

### C1. The decision threshold is exhausted, and there is a ~32% FPR floor · **SOUND**
τ sweep on 2,142 rows: shipped τ = 0.925 (J = 43.3) is near-optimal; best is
τ = 0.99 (J = 45.0). **FPR will not fall below ~32% at any τ** — at τ = 0.9999
it is still 32.1%. About a third of safe contracts carry at least one
*near-certain* false finding, so the false alarms are confident and wrong, not
low-confidence noise. **Every gate / threshold / pooling / arbitration
experiment is downstream of finding generation and therefore capped by this
floor.** *Phase 10.*

### C2. One specialist produces most of the false findings · **SOUND**
Findings on safe contracts (false by construction), full corpus:

| finding type | on safe | on vuln | FP rate |
|---|--:|--:|--:|
| **business_logic** | 467 | 435 | **52%** |
| arithmetic | 310 | 783 | 28% |
| dos_gas | 208 | 544 | 28% |
| access_control | 191 | 537 | 26% |
| reentrancy | 75 | 538 | 12% |

| model | on safe | on vuln | FP rate |
|---|--:|--:|--:|
| **llama3.2:3b** | 508 | 490 | **51%** |
| gemma3:4b | 208 | 544 | 28% |
| qwen2.5-coder:7b | 589 | 1879 | 24% |

The two tables are one fact: `business_logic` is pinned to `LOGIC_MODEL =
llama3.2:3b` and the static router **always** selects it. A coin-flip specialist
runs on every contract. *Phase 10.*

> **This was found in August and never fixed.** Phase 6 measured
> `business_logic` at precision **0.00** and resolved to handle it via per-class
> weighting; Phase 7 then correctly rejected that weighting as noise (B3) — and
> with it, the only planned remedy. The specialist was never addressed. The
> simpler option (exclude the class) was not considered for two months.

### C3. Dropping `business_logic` reaches the FPR floor at far better recall · **REFUTED as stated; survives as a precision/recall trade**

| configuration | recall | FPR | precision | F1 | J |
|---|--:|--:|--:|--:|--:|
| shipped, τ = 0.925 | 89.1% [87.2, 90.8] | 45.9% [42.9, 48.9] | 67.1% | 0.765 | 43.3 |
| τ = 0.99 | 84.9% [82.7, 86.9] | 40.0% [37.0, 43.0] | 69.0% | 0.762 | 45.0 |
| drop business_logic, τ = 0.925 | 86.2% [84.1, 88.1] | 39.6% [36.7, 42.6] | 69.5% | **0.770** | 46.6 |
| drop business_logic, τ = 0.99 | 81.5% [79.1, 83.7] | **32.6%** [29.8, 35.5] | **72.4%** | 0.767 | **48.9** |
| all findings, τ = 0.9999 | 73.2% | 32.1% | 70.5% | 0.718 | 41.1 |

> **These are IN-SAMPLE (seed 0) figures and the +8.3 did not replicate.** Read
> the out-of-sample block immediately below before citing anything here.

The last two rows were the point: at the same ~32% false-alarm rate, dropping
the coin-flip specialist gives 81.5% recall against 73.2% — +8.3 points,
apparently free. The reasoning was that thresholding buys FPR by sacrificing
recall while removing a bad specialist does not. **Held-out seed 1 refuted the
magnitude**: the specialist also contributes true findings, so it is a trade.

**Why HYPOTHESIS and not SOUND:** `business_logic` was selected by inspecting
this data and the fix was scored on the same data. Part of the gain is fitted
noise. A paper arguing that evaluation setup determines the answer cannot ship
a configuration tuned on its own test set. *Phase 10.*

#### C3 OUT-OF-SAMPLE RESULT — seed 1, n = 334 · **NOT PROMOTED** (Oct 24)

Held-out seed 1 (360 attempted, 334 terminal, 26 quarantined = 7.2%):

| configuration | recall | FPR | precision | F1 | J | dJ |
|---|--:|--:|--:|--:|--:|--:|
| shipped, τ = 0.925 | 88.4% | 38.9% | 70.7% | 0.786 | 49.5 | |
| drop business_logic, τ = 0.925 | 85.5% | 34.6% | 72.4% | 0.784 | 50.9 | **+1.4** |
| shipped, τ = 0.99 | 79.7% | 29.0% | 74.5% | 0.770 | 50.6 | |
| drop business_logic, τ = 0.99 | 72.7% | 24.7% | 75.8% | 0.742 | 48.0 | **−2.7** |

**The sign depends on the threshold**, so there is no single "excluding
`business_logic` is better". The effect out of sample is ±2–3 points of J, i.e.
inside noise. Seed 0's headline — +8.3 recall at matched FPR — **does not
reproduce.** C3 is not promoted and the shipped configuration stands unchanged.

The mechanism/effect split is the reportable part:

- **Mechanism replicates.** `business_logic` still places **42.0%** of its
  findings on safe contracts, CI [34.2, 50.2], which contains seed 0's 52%.
  The specialist is genuinely that noisy.
- **Effect does not.** Excluding it also removes true findings it alone caught:
  recall −2.9 / −7.0 against FPR −4.3 / −4.3. **A noisy specialist is not a
  net-negative specialist**, and seed 0 structurally could not separate those
  because the class was chosen there.

#### C3 FINAL — both held-out seeds, n = 666 · **NOT PROMOTED, CLOSED** (Oct 24)

Seed 2 completed (360 attempted, 332 terminal, 28 quarantined = 7.8%):

| configuration | recall | FPR | precision | F1 | J | dJ |
|---|--:|--:|--:|--:|--:|--:|
| shipped, τ = 0.925 | 81.8% | 34.0% | 71.6% | 0.764 | 47.8 | |
| drop business_logic, τ = 0.925 | 79.4% | 29.0% | 74.2% | 0.767 | 50.4 | **+2.6** |
| shipped, τ = 0.99 | 69.4% | 21.0% | 77.6% | 0.733 | 48.4 | |
| drop business_logic, τ = 0.99 | 68.8% | 19.8% | 78.5% | 0.734 | 49.1 | **+0.6** |

All four held-out dJ values: **+1.4, −2.7 (seed 1), +2.6, +0.6 (seed 2).** Three
positive, one negative, mean ≈ +0.5. The sign varies **both** within a seed
across τ and between seeds, so **C3 is not promoted and the shipped
configuration stands unchanged.** This is the final answer; C3 is closed.

**The mechanism replicated almost exactly on both seeds** — `business_logic`
places **42.0%** [34.2, 50.2] and **42.9%** [34.1, 52.1] of its findings on safe
contracts. That is a stable, reproducible property.

**What is reliable is a trade, not a gain.** Across all four held-out cells the
direction is perfectly consistent in the components, and only the *summary*
statistic is ambiguous:

| | seed 1 τ=.925 | seed 1 τ=.99 | seed 2 τ=.925 | seed 2 τ=.99 |
|---|--:|--:|--:|--:|
| Δ precision | +1.7 | +1.3 | +2.6 | +0.9 |
| Δ FPR | −4.3 | −4.3 | −5.0 | −1.2 |
| Δ recall | −2.9 | −7.0 | −2.4 | −0.6 |

Precision up 4/4, FPR down 4/4, recall down 4/4. **Excluding `business_logic`
reliably buys precision with recall** — which is exactly what thresholding does,
and the original claim was that it was *better* than thresholding because it was
free. It is not free. Report it as an operating-point choice available to a
deployer who prefers precision, never as a Pareto improvement.

#### Resolution limit at n ≈ 333 — **CAUTION, not a finding**

The two held-out seeds differ on the **shipped** configuration by **6.6 points
of recall** (88.4% vs 81.8%) and **4.9 points of FPR** (38.9% vs 34.0%) with
tool, models, machine and τ all fixed — the only difference is which contracts
the sampler drew. **The Wilson intervals overlap in both cases**, so this is
sampling noise and **not** evidence that seed is a sixth unreported choice; it
must not be reported as one.

It is still worth stating as a bound: at n ≈ 333 the headline metrics carry
roughly ±6 points of sampling slop, so any claim resolving two configurations
closer than that at this n is not resolvable at all. C3's ±2–3 points of J sit
**inside** that bound, which is the quantitative reason C3 is inconclusive
rather than merely small. Demonstrating a genuine seed effect would need either
far more seeds or the full 2,250-contract corpus per seed.

*Process note, recorded because it nearly produced a published error:* at
n = 206 mid-run the validator printed **REFUTED** (dJ −1.7, −2.5). At the
complete n = 334 the τ = 0.925 sign flipped positive. The minimum-n gate let a
**partial** seed emit a verdict — thresholds being met is not the same as the
run being done. The interim call was labelled provisional, so it cost nothing,
but the gate needs a run-completion condition, not only a row count.

The validator also *mis-named* this outcome: it printed "held-out seeds
disagree" where the seeds agree and the **thresholds** disagree — a wrong
diagnosis carrying the authority of a verdict, produced by the very instrument
built to prevent that. Fixed (`3b490c2`) to distinguish within-seed threshold
splits from across-seed splits.

### C4. 16k context is mandatory, not an optimisation · **SOUND**
See A3. At 4k, 39–44% of specialist calls fail outright.

### C5. `llama3.2:3b` beats `llama3.1:8b` on the logic role · **SOUND (scoped)**
p = 0.0303 on 184 verified-intact paired rows (p = 0.0180 on an earlier subset).
Scope: the hot role only. **Not** an argument that `business_logic` is fine —
C2 shows the role is the problem, not merely the model on it.

### C6. Cross-machine verdict agreement · **SOUND**
0.735 agreement across two hosts on identical inputs, with batch parallelism
excluded by a control, p = 0.75. *Aug 21 / Aug 28 sessions.*

---

## D. Arbitration — the long story

### D1. "Adversarial arbitration yields no held-out gain" · **RETRACTED (method)**
Reported from a judge that **never answered**: `LOCAL_JUDGE_MODEL` defaulted to
`qwen3:8b`, which was not installed, every call returned HTTP 404, and the
unparseable path **failed open** with `verdict="real", upheld=True,
confidence=0.4`. All **234 of 234** findings received an identical verdict and
identical confidence and were upheld unconditionally, so arbitration dropped
nothing and "no gain" was true by construction. *Phase 9.*

### D2. …but the conclusion was approximately right · **SOUND (scoped)**
Re-measured with a working judge on 281 class-balanced contracts: precision
**49.6% → 52.9% (+3.3 points)** while 83% of findings are dropped, recall falls
**93.6% → 32.9%** and FPR falls **95.0% → 29.3%**. The mechanism is the largest
single intervention we measure and it **does not buy precision**, the property
it was adopted for. So D1 is a correction of *method*, not of conclusion, and
does not license claiming the opposite. *Phase 10.*

### D3. Arbitration is approximately uniform thinning · **SOUND (scoped)**
The judge retains **32.9% of true flags and 29.3% of false flags** — nearly the
same rate. That is why precision barely moves. A threshold knob achieves the
same trade more cheaply and controllably. Scope: the dappclean/dappscan corpus.

### D4. On the access-control slice, arbitration looks like a strong precision mechanism · **SOUND (scoped)**
Paired ablation, n = 52 sound in all arms:

| arm | precision | recall | FPR | F1 |
|---|--:|--:|--:|--:|
| single_llm | 50.0% | 22.2% | 11.8% | 0.308 |
| council | 58.3% | 77.8% | 29.4% | 0.667 |
| council+arbitration | **92.3%** | 66.7% | **2.9%** | **0.774** |

**D3 and D4 disagree**: +34 points of precision on one corpus, +3.3 on another,
same judge and code. Reported as corpus dependence, not resolved by choosing the
flattering one. Also note the arbitration arm here was achieved *despite* 3
judge timeouts, whose fail-open retains findings and therefore understates the
benefit.

### D5. Interim: "arbitration is precision-neutral" / "a real precision mechanism" · **RETRACTED**
Two successive interim readings, both stated confidently, both reversed:
n = 13 gave 50.0% → 50.0%; n = 41 gave 50.0% → 87.5%; n = 280 gave 49.6% →
52.9%. The n = 41 figure was reported to the project owner as "refuted from two
independent designs". The arithmetic was never wrong; treating a partial sweep
as a sample of the corpus was. Recorded because a project about evaluation
discipline has no excuse for quoting an interim as a result.

### D6. The judge is a reasoning model, and 97% of its output is discarded · **SOUND**
23.2 s per judge call: 1,349 chars of `thinking` against 35 chars of used
`response`, `eval_count` 300. ~8 min/contract. **This is a second route to the
fail-open**: with a short `num_predict` or tight timeout the thinking trace
consumes the budget and `response` arrives empty (reproduced directly with
`num_predict: 5`), which is unparseable, which fails open. The judge's output
budget must exceed its thinking budget or the mechanism silently becomes a
no-op. Thinking was deliberately **not** disabled — that would be a different
judge and needs its own arm. *Phase 9.*

---

## E. Corpus and measurement integrity

### E1. Three fail-opens in our own integrity tooling · **SOUND**
All one mechanism: `row.get(k)` returns `None` for an absent key, `None` is
falsy, so **"never recorded" became indistinguishable from "recorded fine."**

- `eval/audit.py` keyed intactness on `specialists_errored`, counting rows with
  no health record as intact; and keyed terminality on `verdict` alone, so
  `arb_sweep` (`council_verdict`), the ablation arms (`ok`/`pred`) and web3bugs
  (`detected`/`slices_errored`) reported `terminal=0` — printed as harmless
  zeros meaning *this tree was never audited*.
- `eval/guard.py` `default_terminal` admitted a GO whose health field was
  absent. Latent, but the trap a new runner on `run_full_analysis` would hit.
- `tests/test_eval_integrity.py` re-implemented the terminal rule in each test
  body and asserted on its own arithmetic, so `guard` was never executed and a
  regression there left all three green.

Closed at the source: `services/llm.py` records `specialists_errored` on the
single-model path, `run_ablation.py` persists health per row, so absence is no
longer possible rather than merely reported. *Phase 9.*

### E2. web3bugs is 72.2% contaminated, and was invisible · **UNSOUND for rates**
65 of 90 contest rows ran with at least one errored slice — the most
contaminated tree in the project, previously reporting `terminal=0`. All 90
remain sound under the asymmetric rule, so the **contest-recall claim survives**
(98.4% [91.5, 99.7]; 33/34 vs GPTScan's 31/34, intervals overlapping — no
difference demonstrated). **No rate or paired claim on this corpus is
supported.** *Phase 9.*

### E3. The fail-open is indistinguishable from a verdict — a verbatim artifact · **SOUND**
From `arb_sweep/02_dappscan_bandpricefeed.json`:

```json
{"type": "arithmetic", "judge_verdict": "real", "judge_ok": false,
 "conf": 0.4, "p_real": 0.4, "upheld": true}
```

Apart from the flag, nothing in the shape, types or value ranges marks it as a
non-answer. Base rate: **234/234 (100%)** in the original run versus **13/784
(1.7%)** in the re-run. Same code, same schema, same absence of errors — the
difference between a worthless result and a sound one is a boolean that did not
exist on 2026-10-22.

Note the fail-open is **correct behaviour** and must not be removed: that
finding sits on a vulnerable contract with a NO-GO verdict, so upholding an
unjudged finding is the safe action for a security tool. The defect was that it
was unobservable.

### E4. A generated report asserted a null result its own table refuted · **SOUND**
`ablation_ac.md` printed "the identical row above is therefore a real null
result" beneath a table where the arms differ by 34 points of precision —
hardcoded from when the two council arms genuinely did produce identical rows.
Now reads agreement off the table. Third instance of one pattern: **a conclusion
that does not check its own premise** (tests that could not fail; an auditor
reporting clean on data it could not read; this). *Phase 9.*

### E5. `gate0` counted models instead of checking them · **SOUND**
The gate reported "N models pulled" and passed — including on the day the
arbitration judge was absent. The count was correct and the run was worthless.
Now verifies each role's model **by name**, with a remediation command, and was
validated against a negative control. `LOCAL_JUDGE_MODEL` is pinned in
`scripts/env.sh`. *Phase 9.*

### E6. Full-corpus figures are materially worse than the half-corpus replay · **SOUND**
Regenerated over 2,142 rows versus the n = 1,154 replay: pre-gate FPR
**59.0% → 72.2%** (+13.2), evidence gate **37.5% → 45.9%** (+8.4). Intervals do
not overlap, so this is not noise — the half-corpus numbers were optimistic.
**Every FPR figure tracing to that replay must be regenerated.** *Phase 10.*

### E11. The guard reported a 100% dead arm as 100% sound · **SOUND, fixed**
The sharpest instance of this project's thesis, committed by the component
whose entire purpose is to prevent it. From one run log, two lines apart:

```
[slither/smartbugs_curated] done: {'ok': 0, 'skipped_checkpoint': 1, 'no_result': 143, 'error': 0}
[baseline:slither/smartbugs_curated] sound=142 quarantined=0 (0%) 159.0/min
```

**`ok: 0` and `sound=142`.** Also 159 rows/min — 0.4 s per contract, which is
the dead-arm signature on its face.

**Cause.** `run_baselines` set `terminal_fn = status in TERMINAL_STATUSES`, and
`no_result` was in that set with the documented reasoning that it means *"a
missing source file — a permanent property of the corpus, not a symptom of the
backend."* That reasoning is correct for its real case and conflates two
opposite things, because both write the same status:

| meaning | terminal? |
|---|---|
| the corpus genuinely lacks the file | **yes** — re-running changes nothing |
| the **tool could not run at all** (x86-64 solc on aarch64) | **no** — says nothing about the corpus |

So an arm that answered nothing, 303 times, certified as healthy.

**Fix, two layers** (a per-row rule alone is still gameable):
1. `_baseline_terminal()` — only a `reason` naming an absent source counts as
   terminal for a `no_result`; a tool failure is quarantined.
2. `Guard` now counts **answers** separately from soundness and sets
   `dead_arm` when a run finishes with rows but zero answers. The line prints a
   loud `!!! DEAD ARM` block. This fires even when every row is legitimately
   terminal — an arm of nothing but corpus gaps is 100% sound and still
   answered nothing, so **soundness can never stand in for a result.**

Verified by replaying the exact 143 dead rows: `sound=0 quarantined=143 (100%)
answers=0` plus the alarm, against the original `sound=142 quarantined=0 (0%)`.
Four regression tests; 54 pass.

### E10. Council slice failures are strongly size-correlated · **SOUND**
Across the 148 access-control-slice council rows (seed 0), rows with at least
one failed slice:

| contract family | rows | rows with a failed slice | |
|---|--:|--:|--:|
| `sb_*` (single-file) | 133 | **2** | 1.5% |
| `w3b_*` (multi-file projects) | 15 | **14** | **93.3%** |

Per-slice detail on the five rows completed after 12:54 — 0/23, 5/29, 1/40,
5/40, 4/15 failed — is ~10% of slices on the large contracts. The failures are
`gemma3:4b` and `llama3.2:3b` HTTP 500s ("model runner has unexpectedly
stopped", "unexpected EOF") and 600 s timeouts, i.e. resource exhaustion on
large inputs, not a logic error.

**Why this is sound rather than disqualifying:** all 148 rows are NO-GO, and
under the asymmetric terminal rule a dead specialist can only fail to raise a
flag, never invent one — so a NO-GO with errored slices stands. This is the
case that rule was adopted for, and it earns its keep here.

**Why it still matters for the paper:** on the largest contracts the council is
not the ensemble it is advertised as. Model diversity — a headline property of
the design — **degrades silently as contract size grows**, and the degradation
is invisible in the verdict. It is the same shape as FINDING 0 (the ensemble is
not the size you think) measured on the other axis: there, k varies by router
selection; here, effective k varies by whether the specialist survived the
input. Any claim about council model diversity must be stated for single-file
contracts, or stratified by size.

Cost note: each `w3b_*` row is 15–40 slices and takes 14–60 min (815–3626 s
measured), which is why the baseline tail runs ~35 min/contract.

### E10a. A buffered log was read as live · **process error, recorded**
While diagnosing the above I tailed `~/thirdeye_logs/baselines.log`, found
`gemma3:4b` timeouts, and reported them as currently happening. **The log was
last written at 12:54, over three hours earlier** — Python block-buffers stdout
to a file without `-u`, which this project had already documented and annotated
in `status.sh` today. Checkpoints (15:13) and the ollama log (live) were the
authoritative sources and said the run was progressing normally. The faults are
real; their timing was not established. Corrected within minutes, recorded
because the same trap has now been hit twice in one day.

### E9. The baseline report builder could not see 580 completed rows · **SOUND, fixed**
Two independent loader defects, each individually sufficient to empty the
baseline table, found while checking whether the council (278) and
`single_llm` (301) arms were even being compared on the same contracts.

1. **`_load_checkpoints` globbed one level too shallow.** `run_baselines
   --seed N` writes `<baseline>/<dataset>/seedN/`; the loader matched
   `*.json` directly under the dataset directory, so **every seeded arm
   loaded zero rows.**
2. **Lookups used the raw `contract_id` while filenames use `_safe_id()`**
   (`:` → `_`). Every `sb:` / `w3b:` id missed its own checkpoint.
   `smartbugs_curated` ids need no sanitizing, **so that one dataset worked
   and the defect stayed invisible** — `access_control_slice` scored 0 of 148
   council and 0 of 159 `single_llm` rows.

Combined: **~580 rows hidden, including ~21 h of council GPU time.** The skip
line read *"no checkpoints on this machine"* — false, and reassuring enough
that it survived a day of active work. Now states where the loader looked and
that the arm may have written elsewhere. `build_reports` imports `_safe_id`
from `run_baselines` instead of re-implementing it, because two copies of a
sanitizer drift and the drift presents as a missing row. Seeds are never
pooled: two seeds hold rows for the same `contract_id`, so merging would let
one overwrite the other and score a mixture no run produced.

**A wrong intermediate diagnosis, recorded:** the id mismatch first looked like
a changed dataset definition, i.e. 307 permanently orphaned rows and a council
job 11 h from finishing unscoreable work. The colon→underscore test refuted
that — 148/148 and 159/159 recover. Nothing was orphaned.

**What became visible.** Four real table rows where these arms had none. On
`access_control_slice` — the only one of the two datasets with a real negative
class — **`single_llm` beats council on F1 (0.420 vs 0.363) and precision
(0.268 vs 0.221) while council wins recall (1.000 vs 0.971).**

**New instrument, `eval/baseline_parity.py`.** `build_reports` scores each arm
on its own coverage and then prints the arms side by side; nothing restricted
them to a common contract set, so two rows could be two benchmarks in one
table. The checker rescores on the intersection and reports the movement:
**≤ 0.7 points of F1/recall on both datasets, so the rows are comparable —
measured, not assumed.** It also refuses to compare an arm with zero usable
rows, which is how the dead slither arm (E8) would otherwise enter a table.

Three regression tests cover all of it (seeded discovery, no seed pooling,
sanitized-id lookup). The first version of the third used a hand-rolled item
stub that drifted from `EvalItem` and failed inside `metrics` instead of
testing the lookup — the same defect one layer up, so it now uses the real
schema object. 50 tests pass.

### E7. Earlier discards · **UNSOUND, archived not deleted**
- A 1,152-contract run at ~98% accuracy on safe tiers: `business_logic` pinned
  to an uninstalled `llama3.1:8b`, always selected by the router, so every
  contract had a guaranteed-erroring specialist; with 2 specialists exactly 50%
  errored, which does not trip the `>50%` fail-closed rule. Median latency ~1 s.
  Archived under `_invalid_2026-08-04_missing_models/`. *Phase 0.*
- `ctx_ctx4k_safe`: 176 rows, 145 INCONCLUSIVE, 173 with errored specialists
  (2026-09-25 outage). 385 rows purged to `_poisoned/`.
- `LLM_TIMEOUT` was dead code, and was biasing the sample by size. *Aug 28.*
- The GPTScan comparison was unfair in our favour, twice. *Aug 28.*

---

## F. Open — identified, not measured

### F1. Retrieval grounding is wired to nothing · **OPEN**
`run_ablation` records that retrieved precedents are surfaced in output but
**not injected into specialist prompts**, which is why `council+retrieval` was
correctly skipped as a guaranteed no-delta arm. This is the **only** candidate
we have for moving the ~32% FPR floor (C1), because it changes what the
specialists *assert* rather than how findings are counted. Scoped as future
work, not this paper.

### F2. Do the confident-wrong findings fabricate their evidence? · **OPEN — now answerable** (Oct 24)
`evidence_quote` is dropped when checkpoints are written (only
type/severity/confidence/source/model persist). Confirmed on completed seed 1:
**610 findings, 0 quotes** — the key does not exist on any row, while the
verdicts read "nothing quote-backed above the confidence bar". The quotes
existed at runtime, decided the verdict, and were discarded at serialization.
`run_benchmark.py:151` even carries a comment reasoning that per-finding detail
must be stored so future aggregation questions never need a re-run — and omits
the one field this question needs.

**The earlier remedy ("re-run with quotes stored") was wrong, and this is the
substantive part.** `services/council.py::_aggregate` keeps a finding *iff* its
quote appears in the submitted source, and recorded nothing about the rejects.
Stored rows are therefore **post-gate**: every surviving finding has a genuine
quote **by construction**, so the measured fabrication rate is 0% however often
a model invents one. No volume of cached runs — and no re-run that merely stored
quotes — could have answered F2. **The question was unmeasurable, not
unmeasured**: the strongest form of this project's thesis so far, since the
instrument could not produce the number at all rather than producing a wrong one.

Fixed (`2a7a6f7`): the gate now reports its own rejections by reason —
`not_found` / `below_conf` / `quote_empty` / **`quote_not_in_code`** — and keeps
≤ 8 fabricated samples with role, confidence, model and the quote text.
`quote_not_in_code` *is* the F2 number. Rows additionally carry `evidence_quote`
(300 chars) and the `gate` block; schema 2 → 3, and nothing branches on schema
so old rows still load. Verified end-to-end on synthetic input (5 findings → 1
kept, the fabricated `selfdestruct` counted and sampled); 47 tests pass,
including a bound on the sample so a diagnostic cannot grow without limit.

**Still OPEN.** This does not retrofit seeds 0–2, and seed 2 was deliberately
not restarted to pick it up — a schema change mid-validation would cost the
two-seed comparison, which is worth more. Answerable on the next run.

### F3. Does the `business_logic` exclusion hold out of sample? · **CLOSED — answered: no**
**CLOSED (Oct 24): no — both held-out seeds in, C3 not promoted.** Final dJ
across all four held-out cells: +1.4, −2.7, +2.6, +0.6 (mean ≈ +0.5), sign
varying both across τ within a seed and between seeds. The mechanism replicated
on both (42.0% / 42.9% of `business_logic` findings on safe contracts) and the
component directions are 4/4 consistent — precision up, FPR down, recall down —
so the honest residual claim is a **trade**, not the free gain seed 0 showed.
Shipped configuration unchanged. Detail in §C3.

*Superseded first answer, kept for the record:* See the C3 out-of-sample block. 334
terminal rows; dJ +1.4 at τ = 0.925 and −2.7 at τ = 0.99, so the sign is
threshold-dependent and the effect sits inside noise. C3 is **not promoted**;
the shipped configuration is **unchanged**. The mechanism replicates (42.0% of
`business_logic` findings land on safe contracts) but the specialist is noisy
rather than net-negative. Seed 2 running, ETA ~15:00, for the two-seed
agreement test; it can no longer rescue seed 0's +8.3 magnitude, only decide
whether the small effect is consistent.

### F4. Reconcile "the council hypothesis is refuted" with D4/C2 · **OPEN**
The paper states flatly that a model-diverse council raising precision is
**refuted**. On the access-control slice the council beats the single LLM
decisively (F1 0.667 vs 0.308, recall 77.8% vs 22.2%). Both can be true — the
refutation concerns *precision on a different corpus* — but stated unqualified
it reads as contradicted by our own ablation. Needs one sentence of scope.

---

## G. Deliberately not done

Standing decisions, kept so they are not relitigated: per-class specialist
weights (B3), the `dos_gas` precondition and severity policy (B4), extending
parity beyond 184 intact pairs (p = 0.0303 already significant), the remaining
~1,177 contracts of the arbitration sweep (42 GPU-hours to narrow an interval on
a null effect, D2/D3), and disabling judge thinking as a performance tweak (D6).

### E8. The slither baseline arm on the campus box was 100% dead · **UNSOUND, quarantined**
All **301 of 301** rows were `status=no_result, reason=error`, latency ~0.4 s.
Slither never ran on a single contract.

**Cause:** the box is **aarch64** (DGX GB10). All 76 solc binaries in
`~/.solc-select/artifacts` are **x86-64 ELF** — solc ships official Linux
builds for x86-64 only. No version was selected either (no `global-version`
file), and selecting one gives `Exec format error`. No apt solc, no node, so
the solcjs fallback is unavailable. **Slither cannot run on this machine.**

**Why it went unnoticed for a full day.** Three independent instruments agreed
it was fine: the row count (301/303) read as near-complete and was reported as
"slither done ✓" in every progress update; `eval/audit.py` did not cover the
baseline trees at all; and when it was taught to, slither rows carry no verdict
key, so the arm printed as a parsing gap rather than a dead stage. A failed arm
that writes one checkpoint per contract is indistinguishable from a finished one
by volume, which is the only signal anyone was watching.

**The danger beyond the lost data:** `run_baselines` skips any contract that
already has a checkpoint, so those 301 files would have **permanently prevented
the slither arm from being retried**, including on hardware where it works.
Moved to `_slither_dead_aarch64_20261024_1258/` with a README, not deleted.

**The paper is NOT affected.** Its slither baseline is `slither_bench.json` —
150 contracts, 46 answered, 104 abstentions each diagnosed with solc and exactly
1 attributed to our toolchain (`slither_failure_audit.json`) — produced on an
x86 host. Only the attempted extension to the 303-contract corpus is lost, and
**it must be run on x86**; no amount of GPU time on the campus box will produce
it. The `single_llm` and `council` arms of the same run are unaffected, being
pure LLM inference.

**Fixed forward:** `eval/audit.py` now covers `slither/`, `single_llm/` and
`council/`, reads the baseline schema (`status`, and health as the *survivor*
count `n_slices_ok`/`n_slices` rather than a failure count), and distinguishes a
**DEAD ARM** — every row a failure state, "it RAN AND PRODUCED NOTHING, row
count makes this look finished" — from an unparseable schema, because the two
need different fixes. Verified against the quarantined tree.

This is the fifth and largest instance of the project's own thesis: not a wrong
number, but a **missing** one that every available indicator reported as present.
