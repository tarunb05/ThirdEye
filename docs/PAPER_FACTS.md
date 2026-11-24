# Paper facts — every number, with provenance

**Status: 2026-10-09.** One place to look up any figure that goes into the
submission. Each row names the artefact it came from. Nothing here is typed from
memory; everything was read out of a committed result file, a generated table, or
a verified source paper.

Three labels are used throughout and they are not interchangeable:

- **SOUND** — measured, checkpointed, reproducible, safe to cite.
- **UNSOUND** — the run was corrupted (backend outage); do not cite any figure.
- **EXTERNAL (v)** — from another paper, checked against that paper's own text.

> **The three-rule trap.** There are *three* decision rules in this codebase, not
> two, and the one this file used to call "OR-gate" was the wrong one of them.
> Replayed 2026-10-09 from `eval/checkpoints/benchmark/ollama_noarb/seed0`
> (1,154 rows, all schema 2, zero null confidences):
>
> | rule | where it sits | tp/fp/tn/fn | FPR |
> |---|---|--:|--:|
> | `n_findings > 0` | **pre-gate** — any specialist raised anything | 498 / 356 / 247 / 53 | 59.0% |
> | `verdict == NO-GO` | post evidence-gate + agreement vote | 455 / 226 / 377 / 96 | 37.5% |
> | noisy-OR, τ = 0.925 | pooling over the surviving findings | 446 / 182 / 421 / 105 | 30.2% |
>
> The first two reproduce **exactly** — the second is `benchmark_by_tier.json`'s
> `overall` to the contract. The third lands 2 contracts off the figure the paper
> reports (445/180/423/106), at *every* τ in [0.80, 0.999] and under every
> treatment of a missing confidence, so the published replay applied something the
> checkpoints do not record. Structural suppression (`services/suppression.py`) is
> the candidate: it drops findings *after* the council, and the stored `findings`
> list is pre-suppression. Rerun `python -m eval.verify_facts` to reproduce any of
> this; it exits non-zero on a mismatch.
>
> **The correction this forces.** Calling the pre-gate count "the OR-gate" credits
> the pooling rule with the evidence gate's work. The OR over *surviving* findings
> is 37.5%, not 59.0%. So the honest framing is a three-step decomposition —
> 59.0% (flag anything) → 37.5% (evidence gate) → 30.2% (pooling) — and the gate
> does more of that work than the pooling does. Do not write "59.0% → 29.9%" as a
> single step attributable to noisy-OR.
>
> Two fixes owed: store post-suppression findings in the checkpoint (or apply
> suppression inside `verify_facts`), and relabel every "OR-gate" column below
> according to which of the three rules it actually is.
>
> ### UPDATE 2026-10-23 — the third rule is not a third rule
>
> Replayed on the **full** corpus (2,142 rows, all asym-sound under
> `guard.default_terminal`). The two reproducible rules move as expected, and
> both are substantially worse than at n=1,154:
>
> | rule | tp/fp/tn/fn | recall | FPR | was (n=1,154) |
> |---|--:|--:|--:|--:|
> | pre-gate `n_findings > 0` | 1051 / 755 / 291 / 45 | 95.9% | **72.2%** | 59.0% |
> | evidence gate `NO-GO` | 977 / 480 / 566 / 119 | 89.1% | **45.9%** | 37.5% |
> | noisy-OR, τ = 0.925 | 977 / 480 / 566 / 119 | 89.1% | **45.9%** | 30.2% |
>
> The noisy-OR column is **identical to the evidence gate in every cell**, and
> the two rules disagree on **0 of 2,142 contracts**. That is not a measurement,
> it is an identity: `services/council.py:472` defines the shipped verdict as
> `risk = 1 − Π(1 − conf_i)`, `NO-GO iff risk ≥ RISK_TAU`, and line 484 sets
> `RISK_TAU = 0.925`. Recomputing a noisy-OR at τ = 0.925 over the stored
> findings therefore re-derives the verdict rule by construction. A τ sweep
> confirms it: disagreement is 191 rows at τ = 0.90, **0** at 0.925, 1 at 0.95,
> 108 at 0.99 — the zero sits exactly on the shipped threshold.
>
> **So the published three-step decomposition cannot be replayed from the
> checkpoints, and the earlier "2 contracts off" diagnosis understates it.** The
> gap is not a 2-contract discrepancy; the third column is a *different
> function* of data the checkpoints do not contain (post-suppression findings),
> because any noisy-OR computed from data they *do* contain is the second
> column. Until post-suppression findings are stored, the third step is
> unverifiable.
>
> **Report two measured steps, not three:** 72.2% → 45.9% on identical
> verdicts, a 26.3-point move attributable to the decision rule alone. This is
> still the cleanest form of the paper's thesis — the aggregation rule is worth
> more than most model changes — and it no longer credits a step we cannot
> reproduce. Note also that a reader proposing noisy-OR pooling as an
> improvement over this tool would be proposing the tool's own shipped rule.
>
> Both reproducible rules degrade at full corpus (FPR +13.2 and +8.4 points),
> so every FPR figure in this file derived from the 1,154-row replay is
> optimistic and must be regenerated before submission.

---

## 1. The corpus

| fact | value | source |
|---|--:|---|
| total contracts | 2,250 | `eval/loaders/thirdeye_bench` |
| balance | 1,125 safe : 1,125 vulnerable | ditto |
| scored in the main run | **1,154** (603 safe, 551 vulnerable) | `benchmark_by_tier.json` |
| safe tiers | audited libraries 172 · audit-reviewed 240 · real-world-no-bug 191 | ditto |
| safe-tier median contract size (full corpus) | audited 6,649 · audit-reviewed 3,531 · real-world 3,783 chars | computed 2026-09-25 |
| vulnerable tiers | curated 214 · injected 170 · audit-report 167 | ditto |
| vulnerable contracts with a mapped DASP-10 label | 349 (202 carry none) | `class_coverage_shipped.json` |
| contracts overflowing a 4,096-token window | 540 / 2,250 (24.0%), skewed 350 vulnerable : 190 safe | `run_ctx_ablation.py` docstring |
| safe overflow pool under the 12,230-token ceiling | 176 (190 without the ceiling) | `reconstruct_ctx_sample.py`, verified |

---

## 2. Headline result at scale — SOUND

`benchmark_by_tier.json` + shipped replay in `frontend/src/data/benchmark.ts`,
n = 1,154, backend `ollama_noarb`, seed 0, 0 abstentions, 0 errors.

| | pre-gate (`n_findings > 0`) | evidence gate (`NO-GO`) | **noisy-OR (shipped)** |
|---|--:|--:|--:|
| tp / fp / tn / fn | 498 / 356 / 247 / 53 | 455 / 226 / 377 / 96 | **445 / 180 / 423 / 106** |
| false-alarm rate | 59.0% [55.1, 62.9] | 37.5% [33.7, 41.4] | **29.9% [26.3, 33.6]** |
| recall | 90.4% [87.6, 92.6] | 82.6% [79.2, 85.5] | **80.8% [77.3, 83.8]** |
| precision | 0.583 | 0.668 | **0.712** |
| F1 | 0.709 | 0.739 | **0.757** |

The middle column is the one the committed JSON holds; the first column is *not*
"the OR-gate", it is the rule before any gating at all. Replaying the shipped
column from these checkpoints gives 446/182/421/105 (FPR 30.2%) — 2 contracts
off, unexplained, see the three-rule note at the top. **Cite the shipped column
as 29.9% only alongside that caveat, or cite the replayable 30.2%.**

### SUPERSEDED — regenerate from the full corpus (2026-10-24)

The table above is the **n = 1,154** replay and is **optimistic**. Regenerated
over all **2,142** rows (every one asym-sound under `guard.default_terminal`;
1,046 safe / 1,096 vulnerable), Wilson intervals:

| rule | tp / fp / tn / fn | false-alarm rate | recall |
|---|--:|--:|--:|
| pre-gate (`n_findings > 0`) | 1051 / 755 / 291 / 45 | **72.2% [69.4, 74.8]** | 95.9% [94.6, 96.9] |
| evidence gate (`NO-GO`) | 977 / 480 / 566 / 119 | **45.9% [42.9, 48.9]** | 89.1% [87.2, 90.8] |

The shipped/noisy-OR column is **deliberately absent**: at τ = 0.925 it is the
evidence gate re-derived (0 disagreements in 2,142 — see the three-rule note at
the top of this file), so printing it as a third column would double-count one
rule.

Both figures move against us, and the intervals do not overlap the old ones:
false alarms are **+13.2 points** worse on the pre-gate and **+8.4 points**
worse on the evidence gate than the half-corpus replay suggested. Recall rises
slightly on both. **Every FPR number elsewhere in this file that traces to the
1,154-row replay inherits this bias and must be regenerated before submission;
the n = 1,154 table is retained above only to document what changed.**

Regenerate with the snippet in the three-rule note, or re-derive from
`eval/checkpoints/benchmark/*/seed*/` — no GPU required, it is arithmetic over
cached rows.

---

## 2b. FINDING 0 — ensemble size — SOUND (new, 2026-10-24)

**The largest single effect in this file, on a quantity no user selects.** Same
safe contracts, same rule; the only variable is how many specialists the static
router actually fired. All 1,046 asym-sound safe rows of the full corpus,
evidence gate, Wilson intervals:

| k = specialists run | audited_library | realworld_no_bug | audit_reviewed_clean |
|--:|--:|--:|--:|
| 1 | 16.0% [8.3, 28.5] (n=50) | 11.1% [3.1, 32.8] (n=18) | — |
| 2 | 18.9% [12.1, 28.2] (n=90) | 15.3% [8.2, 26.5] (n=59) | 18.7% [12.8, 26.5] (n=123) |
| 3 | 26.8% [17.9, 38.1] (n=71) | 53.1% [36.4, 69.1] (n=32) | 42.0% [34.6, 49.7] (n=162) |
| 4 | 41.9% [28.4, 56.7] (n=43) | 62.2% [47.6, 74.9] (n=45) | 69.3% [60.3, 77.0] (n=114) |
| 5 | 68.8% [44.4, 85.8] (n=16) | 75.0% [56.6, 87.3] (n=28) | 84.6% [75.8, 90.6] (n=91) |
| 6 | — | — | 90.2% [80.2, 95.4] (n=61) |

**16.0% at k = 1 to 90.2% at k = 6, monotone.** This is §7's OR-gate
compounding (contract-level FP ≈ 1−(1−p)^k) measured directly rather than
inferred from the aggregate, and it is the mechanism beneath three other
findings in this file:

1. **It confounds FINDING 1 (§3).** `audited_library` draws a median of **2**
   specialists; both other tiers draw **3**. At matched k = 2 the three tiers
   are statistically indistinguishable — 18.9% / 15.3% / 18.7%, intervals fully
   overlapping. The provenance spread appears only at k ≥ 3. A within-stratum
   effect survives (library stays lowest at k = 3, 4, 5), so provenance is real,
   but it is **substantially smaller than the marginal comparison shows** and
   must be reported stratified by k or with k as a stated covariate.
2. **It explains the ~32% FPR floor.** Thresholding cannot undo an OR over k
   detectors; it only raises the bar each detector must clear. The floor is a
   property of the aggregation *topology*, not of τ.
3. **It predicts that excluding `business_logic` is a topology change, not a
   threshold change.** That specialist is always selected by the router, so
   dropping it reduces k by one corpus-wide. **The +8.3-recall figure that
   originally appeared here is RETIRED** — it did not reproduce out of sample
   (C3, FINDINGS.md: dJ +1.4 at τ = 0.925, −2.7 at τ = 0.99 on held-out seed 1,
   so the sign is threshold-dependent and the effect is inside noise). The
   mechanism stands and the magnitude does not: reducing k does move the
   operating point, but `business_logic` also contributes true findings, so the
   net is a trade rather than the free gain seed 0 suggested.

**Replication, held-out seed 1 (n = 162 sound safe rows, Oct 24).** Pooled
across tiers, against seed 0 pooled the same way:

| k | seed 0 | seed 1 (held-out) |
|--:|--:|--:|
| 1 | 12.2% (n=82) | 0.0% (n=15) |
| 2 | 18.0% (n=272) | 17.4% (n=46) |
| 3 | 39.2% (n=265) | 33.3% (n=39) |
| 4 | 61.9% (n=202) | 58.1% (n=31) |
| 5 | 80.7% (n=135) | 70.0% (n=20) |
| 6 | 90.1% (n=71) | 100.0% (n=9) |

Monotone on both seeds, tracking within a few points at every k with n ≥ 20.
**This is the one headline claim that replicated on the day C3 failed to**, and
it is the relevant contrast: C3 was selected by inspecting seed 0, FINDING 0 is
a structural property of the aggregation that seed 0 merely made visible.
(k = 7–8 cells are n ≤ 15 and carry no weight.)

Reproduce offline from `eval/checkpoints/benchmark/*/seed*/` — no GPU, no
re-run; `n_specialists_run` is recorded per row.

---

## 3. FINDING 1 — label provenance — SOUND (effect) / CONFOUNDED (magnitude)

> **Read §2b first.** The marginal spread below is partly an ensemble-size
> artifact: these tiers differ in how many specialists the router fires, and at
> matched k = 2 they are statistically indistinguishable. The provenance effect
> is real but smaller than this table implies. The n = 1,154 figures here are
> also superseded — at full corpus the tiers measure 27.8% [22.9, 33.4]
> (audited_library), 44.8% [37.9, 51.9] (realworld_no_bug_reported) and 54.7%
> [50.7, 58.7] (audit_reviewed_clean), which **inverts** the ordering below and
> therefore retires the "residual tracks label trust" interpretation, since that
> argument rested on monotonicity.

Same tool, seed, machine, contracts. Only how the *safe* label was obtained changes.

| safe tier | n | fp (shipped) | FPR, shipped | FPR, pre-gate |
|---|--:|--:|--:|--:|
| Audited libraries (OZ / Solady) | 172 | 27 | **15.7% [11.0, 21.9]** | 49.4% [42.0, 56.8] |
| Audit-reviewed, clean | 240 | 90 | **37.5% [31.6, 43.8]** | 66.2% [60.1, 71.9] |
| Real-world, no bug reported | 191 | 63 | **33.0% [26.7, 39.9]** | 58.6% [51.6, 65.4] |

The right-hand column sums to 85 + 159 + 112 = 356 false positives, which is the
**pre-gate** count, not the OR over surviving findings — relabelled 2026-10-09,
see the three-rule note at the top.

Two-level, **not** a monotonic gradient: audited libraries separate from both
weaker tiers; the two weaker tiers overlap and are not distinguishable.

**Label-noise bound (hand review, `FP_REVIEW_SAMPLE.md`).** Random sample
(seed 2026) of 20 of the 79 blocked safe contracts, plus 1 from an earlier read:

| assessment | count | share |
|---|--:|--:|
| clear tool error | 14 | **70%** |
| unclear, needs a read | 4 | 20% |
| possible real bug in a "safe" contract | 2 | 10% |

Detection by vulnerable tier (evidence-gate tp, 185+152+118 = 455): curated 185/214 = 86.4% [81.2, 90.4] ·
injected 152/170 = 89.4% [83.9, 93.2] · audit-report 118/167 = 70.7% [63.4, 77.0].

---

## 4. FINDING 2 — the matching rule — SOUND (new, 2026-09-25)

`class_coverage_shipped.json`. Identical contracts, verdicts and rule; only the
protocol changes. Denominator = 349 labelled vulnerable contracts.

| protocol | detected | recall |
|---|--:|--:|
| any-slice-positive | 287 | **82.2%** |
| type-matched | 89 | **25.5%** |

**Spread: 56.7 points**, which decomposes. 158 / 349 (45.3%) carry only classes
the council has no specialist for, so part of the spread is our coverage gap.
Restricting to contracts carrying ONLY covered classes isolates the protocol:

| set | n | any-slice | type-matched | spread |
|---|--:|--:|--:|--:|
| all labelled | 349 | 82.2% | 25.5% | 56.7 pts |
| **coverage-controlled** | **187** | **77.0%** | **45.5%** | **31.6 pts** |

**Cite 31.6 as the protocol effect.** 56.7 is protocol + coverage jointly.

| DASP-10 class | n | any-slice | type-matched | specialist? | Durieux |
|---|--:|--:|--:|---|---|
| unchecked low-level calls | 109 | 89.0% | — | **none** | Slither 33% (4/12) |
| reentrancy | 86 | 76.7% | 29.1% [20.5, 39.4] | yes | Slither 88% (7/8) |
| arithmetic | 79 | 77.2% | 62.0% [51.0, 71.9] | yes | Mythril 68% (15/22) |
| time manipulation | 40 | 92.5% | — | **none** | Slither 40% (2/5) |
| access control | 17 | 88.2% | 70.6% [46.9, 86.7] | yes | best 21% (4/19) |
| bad randomness | 9 | 66.7% | — | **none** | ZERO of 9 tools |
| denial of service | 8 | 62.5% | 50.0% [21.5, 78.5] | yes | ZERO of 9 tools |
| front running | 4 | 100.0% | 0.0% [0.0, 49.0] | yes | Mythril/Securify 29% |
| short addresses | 1 | 100.0% | — | **none** | ZERO of 9 tools |

`[25.5%, 82.2%]` is a bracket: 25.5% is a **lower** bound (only 5 of 8 roles have
an unambiguous DASP slot; `business_logic`, `oracle_price_manipulation`,
`proxy_upgradeability` are deliberately unmapped).

**Independent corroboration of the coverage gap** — the older 2-model council on
SmartBugs-curated scored recall **0** on bad_randomness (0/8), denial_of_service
(0/6) and arithmetic (0/15). `council_baseline_smartbugs_curated.json`.

---

## 5. FINDING 3 — silent input truncation — SOUND, REFRAMED 2026-10-23

**The claim changed, and it got stronger.** Earlier drafts reported this as a
recall effect (12.5% -> 81.2%, McNemar p = 0.0162, 4.01x slower). That figure
rested on 20 paired rows **of which exactly ONE had an intact council in both
arms** -- 27 of the 29 scored 4k rows had errored specialists. Since a dead
specialist can only fail to raise a flag, never invent one, the contamination
pushed 4k recall DOWN and therefore *manufactured* the effect. It is the same
defect this file already caught in the safe arm, present unnoticed in the
vulnerable arm. **Do not cite 12.5% -> 81.2%, and do not cite 4.01x: at 4k
most specialist calls terminate on the client deadline, so the measured
latency is the timeout, not the model.**

Re-run clean on 2026-10-23, the effect is not on recall but on whether the
council *runs at all*, and it is measured per SPECIALIST CALL, so it does not
depend on paired rows:

| arm | specialist calls | failed | rate [95% Wilson] |
|---|--:|--:|--:|
| vulnerable, num_ctx 4,096 | 92 | 36 | **39.1% [29.8, 49.3]** |
| vulnerable, num_ctx 16,384 | 437 | 14 | 3.2% [1.9, 5.3] |
| safe, num_ctx 4,096 | 97 | 43 | **44.3% [34.8, 54.2]** |
| safe, num_ctx 16,384 | 485 | 11 | 2.3% [1.3, 4.0] |

Two-proportion test: vulnerable z = 10.71, **p = 9.5e-27**; safe z = 13.03,
**p = 7.8e-39**. Both classes, same direction, order-of-magnitude effect.

| | 4k | 16k |
|---|--:|--:|
| contracts with an intact council | 22.2% / 20.0% | 85.7% / 92.5% |
| inconclusive | 33.3% / 45.0% | 1.1% / 1.7% |
| **GO returned by a BROKEN council** | **7 / 5** | **0 / 0** |

**The sentence for the abstract.** Twelve contracts at 4,096 tokens returned
GO -- no vulnerability -- from a council in which one to three specialists
never ran. At 16,384 that happened zero times. A silently truncating context
window does not degrade detection gracefully: it makes specialist calls fail
outright, and the harness reports the wreckage as a clean bill of health. The
failure is both silent and biased toward false SAFETY.

Provenance: `ctx_ctx4k` / `ctx_ctx16k` / `ctx_ctx4k_safe` / `ctx_ctx16k_safe`,
all purged of pre-2026-10-23 rows, re-run with the 4k arms at concurrency 2
and a 1,800s deadline so the failures are the model's and not the queue's.
Verify with `python -m eval.audit`.

**Known limit, state it.** The 4k arms are small (n = 18 and 20 contracts)
*because* they fail -- 78% and 80% of attempted rows quarantined. That is the
finding, not a sampling shortfall, but the per-CONTRACT rates carry wide
intervals and only the per-CALL rates should be quoted as precise.

---

## 6. FINDING 4 — execution environment — SOUND

| arm | n scored | agreement w/ laptop | acc DGX | acc laptop | median latency |
|---|--:|--:|--:|--:|--:|
| `full3b` (main) | 230 | **0.735** | 0.722 | 0.622 | — |
| `full3b_np1` (control) | 227 | 0.727 | 0.736 | 0.621 | 7.5 s vs 60.6 s |
| `full8b` (capacity) | 232 | 0.767 | 0.651 | 0.625 | 22.6 s vs 60.6 s |

`num_parallel = 1` control excludes batch parallelism: paired McNemar **p = 0.75**.

**Capacity ablation (negative result).** Restoring a 2.7× larger model on the 3
semantic roles: false alarms **49 → 74** (McNemar **p = 0.00008**), misses
**15 → 7** (p = 0.043), net accuracy **0.722 → 0.651**. Capability is not the lever.

---

## 7. Verdict rule — SOUND

`weighted_aggregation.json`, 10 random dev/test splits, n = 233 rows (116 dev / 117 test), τ = 0.575.

| rule | FPR | precision | recall | F1 |
|---|--:|--:|--:|--:|
| OR-gate | 64.8% ± 5.4 | 0.563 ± 0.021 | 0.938 ± 0.020 | 0.703 ± 0.017 |
| noisy-OR threshold (shipped) | **27.4% ± 7.8** | 0.733 ± 0.043 | 0.824 ± 0.101 | 0.770 ± 0.033 |

Held-out test: OR-gate 51/43/19/4, FPR 69.4%, F1 0.685 → noisy-OR 48/19/43/7,
FPR 30.6%, F1 0.787. Wins **9 of 10** splits. Per-class weighting beats a flat
threshold on only **3 of 10** — so the gain is attributed to **thresholding**,
not weighting (`threshold_only` F1 0.790 vs weighted 0.770).

**Arbitration — NEGATIVE result.** `arbitration_sweep.json`, n = 233.
Council-only 101/79/45/8, P 0.561, R 0.927, F1 0.699. Best in-sample τ = 0.15
gives F1 0.711 but is **not reportable** (fitted in-sample). Held out, arbitration
wins **4 of 10** splits — no gain, despite visibly cutting the FPR column.

---

## 8. Baselines — SOUND

**Slither, identical 150 contracts** (`slither_bench.json`, rule: NO-GO iff ≥1 High/Medium):

| | Slither | ThirdEye |
|---|--:|--:|
| answered | **46 / 150** | **150 / 150** |
| abstained | 104 (69%) | 0 |
| tp / fp / tn / fn | 32 / 2 / 8 / 4 | — |
| precision where it answers | **0.941** | 0.712 |
| recall where it answers | 0.889 | 0.808 |

False-discovery 2/34 = **5.9%**, corroborating the **10.9%** Slither's own paper
reports. All 104 abstentions diagnosed with `solc`; **exactly 1** attributable to
our toolchain (`slither_failure_audit.json`).

**Access-control ablation** (`ablation_ac.json`, 8 positive + 8 negative, seed 0) —
the one place the council clearly wins, on a set with real negative signal:

| config | tp/fp/tn/fn | precision | recall | F1 |
|---|---|--:|--:|--:|
| single LLM (llama3.1:8b) | 1/0/8/7 | 1.000 | 0.125 | 0.222 |
| **council** | 6/0/8/2 | 1.000 | **0.750** | **0.857** |
| council + arbitration | 1/0/8/7 | 1.000 | 0.125 | 0.222 |

**Etherscan-50 — the council LOST** (`baseline_table.md`). Council P 0.067 /
R 0.167, against single-LLM 0.182 / 0.667 and LLM+Slither 0.140 / 1.000.
Council confusion 1/14/30/5. Ground truth is scraped and noisy — the table says
so itself — but the original hypothesis ("the council raises precision") is
**refuted** on the only early set with a negative class. Report it.

---

## 9. Prior work — EXTERNAL (v)

| source | figure |
|---|---|
| **GPTScan** (ICSE'24) | tp 40 / fp 30 / tn 154 / fn 8 = 232 checks; P 0.571, R 0.833, F1 0.678; FPR **4.39%** on Top200; 10 DeFi types, reentrancy & overflow excluded; 10/72 static failures |
| **Slither** (WETSEB'19) | **10.9%** "false positives" = 1 − precision, reentrancy only, ≥50 sampled, no TN set; 112 flagged; 0.79 ± 1 s; 0% timeout; 0.1% failed. Securify 25%, SmartCheck 73.6%, Solhint 91.3% |
| **Durieux et al.** (ICSE'20) | 9 tools, 47,518 wild + 69 annotated (115 vulns), 428,337 analyses, 564 days. **93%** of wild flagged. All 9 combined **48/115 (42%)**; Mythril 31/115 (27%); Slither 20/115 (17%). DoS / bad randomness / short addresses: **zero by any tool** |
| **Heimdallr** (2601.17833) | GPTScan **97.50%** FPR on Sherlock; LLMSmartAudit 99.01%; Hound 80.20%; their own 31.27–49.12% |
| **COMPSAC'26** (2605.11163) | local 4-bit FPR **34.09%** vs hosted 25%; 44 s vs 3 s; lexical bias 4–8% |
| **Berriche et al.** (2609.08765, Sept 2026) | 15 failure modes, 8 cyber **QA** benchmarks, 10 models; one pipeline choice moves a score **>80 pp**; denominator inflation 99.8 pp. **No negative class anywhere** |

**Our head-to-head vs GPTScan** (`web3bugs_gptscan.json`): 63 contests scored,
62 detected, contest recall 98.4% [91.5, 99.7], median latency 226.9 s, 3,547 API
calls, 205 S-class bugs. On the **34 gradable** shared projects: **33/34 vs
31/34, intervals overlapping — no difference demonstrated.**

**Council health on this corpus (added 2026-10-23, from `eval/audit.py`).**
Of the 90 web3bugs contest rows, **only 25 ran with every slice intact — 65
(72.2%) had at least one errored slice.** This is the most contaminated tree in
the project and it had been **invisible**: `audit.py` keyed terminality on a
`verdict` field that these rows do not have (they carry `detected` /
`slices_errored`), so the corpus reported `terminal=0` — printed as a row of
zeros that reads as "nothing to see" and actually meant "never audited."

What survives and what does not:
- **The contest-recall claim survives.** All 90 rows are sound under the
  asymmetric rule (`asym=90`): a slice that errored can only fail to raise a
  flag, never invent one, so a *detection* cannot be manufactured by a dead
  slice. The 98.4% recall and the 33/34 head-to-head stand.
- **No rate or paired claim on web3bugs may rest on this tree.** A
  non-detection cannot be distinguished from a slice that never ran, so any
  FPR-like or per-contest comparative figure is unsupported at 72.2%
  contamination.

Reported here rather than in a limitations footnote because the bias direction
is the whole point: contamination on this corpus pushes toward *missing* bugs,
which is the direction that would flatter a recall number if the rule were
reversed, and the only reason we can state which way it cuts is that the field
was recorded per row.

---

## 10. Engineering artefact

| fact | value |
|---|--:|
| source LOC (py/ts/tsx/sh/yml, excl. lockfiles & venv) | **18,078** |
| — Python / TSX / TS | 10,909 / 4,526 / 1,686 |
| documentation | 3,707 lines |
| commits | 61 |
| backend tests | 42, all passing |
| silent failure modes documented | 7, with 6 proposed invariants |

**We then committed one of our own invariants' violations.** The ablation runner
checkpointed transient backend failures as results and reused them on resume —
defect #3 ("transient ≠ deterministic"), by the instrument that measures the
headline. Found and fixed 2026-09-25 (`c687ff8`).
