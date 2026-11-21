# External Critique — Verified Actionables

An external reviewer critiqued `docs/RESEARCH.md` on 27 October 2026. Every
factual claim in that critique was checked against the project's own data before
being accepted. This document records **what was verified, what was found to be
worse than reported, and what must be done**, in priority order.

**Headline: all three of the reviewer's primary issues are real. One of them is
materially worse than the critique states, and it is live on the public site.**

---

## A1 — The per-tier contract counts are stale. **CONFIRMED, AND WORSE.**

### What the reviewer said

The safe-tier counts (172 + 240 + 191 = 603) and vulnerable-tier counts
(214 + 170 + 167 = 551) sum to 1,154 — the *old* evaluation size — while the
same documents report 2,142 scored contracts and 1,046 scored safe contracts.

### What we verified

Correct, and the gap is larger than a documentation slip. Reconstructing the
true per-tier counts from the full-corpus ensemble-size table in
`docs/PAPER_FACTS.md` (§2b), summing each tier's column across k = 1…6:

| Safe tier | Published count | Reconstructed from the k-table | Error |
|---|--:|--:|--:|
| Audited libraries | 172 | **270** | −98 |
| Real-world, no bug reported | 191 | **182** | +9 |
| Audit-reviewed, clean | 240 | **551** | **−311** |
| **Total** | **603** | **1,003** | **−400** |

The k-table omits k = 7–8 cells (n ≤ 15 each). 1,003 + ~24 = **1,027**, which is
exactly the figure the site itself prints — *"1,027 of 1,046 safe contracts;
k = 7–8 omitted."* The reconstruction reconciles to the unit.

So the per-tier `n` column is not approximately stale, it is **wrong by a factor
approaching 2.3 for the largest tier**, and it is printed on the public
Datasets page directly beside false-alarm rates computed over the full corpus.

### Why this is the most serious item

`docs/PAPER_FACTS.md` opens with a header warning about exactly this trap —
that the per-tier figures were caught holding `n = 1,154` values a second time.
That header states the problem was fixed because *"the n column beside them was
already full-corpus."* **That statement is false.** The fix updated the rates
and left the counts. The file documenting the error contains the error.

A paper whose thesis is that plausible-looking numbers conceal silent failures
cannot ship a denominator that does not reconcile.

### Action

1. Build one authoritative evaluation ledger: per experiment — original corpus
   size, exclusions, failed runs, scored contracts, safe/vulnerable split, tier
   membership, and exact confusion-matrix counts.
2. Regenerate **every** table and interval from that ledger — site, paper draft,
   findings register, research record.
3. Correct the `PAPER_FACTS.md` header, which currently certifies a fix that did
   not happen.
4. Correct the live site's Datasets page.

**Owner:** benchmark & experimental design. **Blocks:** any submission.

---

## A2 — The ensemble-size finding is associational, not causal. **CONFIRMED.**

### What the reviewer said

Contracts are *grouped* by how many specialists the router selected. Those
groups contain different contracts. A contract drawing six specialists may be
structurally more complex, so the k gradient may be a complexity gradient. Also,
`FPR(k) = 1 − (1 − p)^k` assumes independent detectors sharing one per-detector
rate `p`; our specialists have different roles and may fail in correlated ways.
The formula is a *model* of OR-aggregation, not proof that it explains the
measurements.

### What we verified

Accurate, and already acknowledged — `RESEARCH.md` §7 states that cyclomatic
complexity and external-call count are not controlled, and §9 lists this as
**O5, "the most important threat to F0."** The reviewer's addition is the
sharper point about the formula: we have been presenting a mechanism and a
measurement as if the first explained the second, when it is a plausible model
fitted to a monotone trend.

The replication on held-out seed 1 raises confidence that the *association* is
real. It does nothing for causality — the same confound is present in both
seeds.

### Action

Run a paired, controlled experiment. On a stratified sample of the **same** safe
contracts, force specialist-set sizes rather than letting the router choose.
Hold aggregation and all other settings fixed. Measure incremental false alarms
as specialists are added. Include contract complexity and source-project as
covariates.

This is a within-contract design, so it isolates the effect of k directly and
would convert F0 from the project's largest association into its largest causal
result. It needs no new corpus.

**Note:** this experiment is an exceptionally good fit for **MSR 2027's
Registered Reports track** (deadline 20 November 2026), where reviewers accept
the *design* before results exist.

**Owner:** benchmark & experimental design, with council & verdict rule.

---

## A3 — The label-noise bound overstates its evidence. **CONFIRMED.**

### What the reviewer said

The hand-review table accounts for 20 contracts (14 + 4 + 2), not the 21
claimed. And "at most 30% of the false-alarm rate could be label noise" is
stronger than 20 observations support: the four "unclear" contracts have not
been established as tool errors, and a small sample cannot guarantee a
population ceiling.

### What we verified

Both correct — and the original source document is **more careful than our own
later write-ups.** `docs/FP_REVIEW_SAMPLE.md` says:

> "2–3 of 21 inspected contracts look like genuine unreported vulnerabilities
> marked safe. That is enough to state the direction — the measured rate is an
> upper bound — and not enough to quote a correction factor."

The 21st contract (`TwoKeyDeepFreezeTokenPool`) is explicitly outside the
20-row tally, from an earlier read. So the counting is defensible, but the
presentation is not: `RESEARCH.md` §3.2 and `PAPER_MSR2027.md` §3.2 both harden
"not enough to quote a correction factor" into "at most 30% could be label
noise."

A Wilson interval on 6/20 is roughly **[14%, 52%]**. Quoting 30% as a ceiling
hides that.

### Action

1. Reconcile the 20-vs-21 presentation so the tally and the narrative agree.
2. Expand the sample and obtain **independent** review with a documented
   adjudication process — currently the assessments are the authors' own, with
   no inter-rater agreement measured.
3. Report observed proportions **with intervals**, and describe the exercise as
   preliminary evidence about label quality rather than a validated bound.
4. Restore the source document's own caution to the downstream write-ups.

**Owner:** corpus & ground truth.

---

## B — Secondary issues a reviewer will raise

| # | Issue | Verified? | Action |
|---|---|---|---|
| B1 | Overlapping confidence intervals do not establish equivalence between provenance tiers | Yes — we wrote "statistically indistinguishable" from overlap alone | Run direct pairwise contrasts or formal equivalence tests, stratified by k |
| B2 | The 25.5% vs 82.2% recall spread mixes protocol with coverage | Already handled — we report the coverage-controlled 31.6 points as the claim | Lead with the controlled figure; move the uncontrolled 56.7 to a secondary position |
| B3 | RQ3's safe-class arm failed; only 20 contracts scored in both arms | Yes, documented | Re-run both classes with robust resume; report denominators and paired uncertainty |
| B4 | RQ4 conflates machine, runtime and backend effects | Yes | Repeat runs; pin the full software stack, not just model digests |
| B5 | A verbatim quote does not prove the quote *supports* the claim | Yes — this is a real gap in the evidence gate's guarantee | Measure whether cited spans substantiate the finding. This is open item **O2** and is answerable from stored checkpoints |
| B6 | Threshold-selection splits may leak related contracts between dev and test | **Not yet checked** | Determine whether splits are by contract or by source project/family, and document grouping explicitly |

**B6 is new and we have not verified it.** If splits are per-contract and the
corpus contains clones or same-project siblings, τ = 0.925 may be tuned on
contracts related to those it is evaluated on. That would weaken the "re-selected
identically in 8 of 10 random dev splits" claim. **This needs checking before
submission.**

---

## C — Positioning changes we accept

### C1. Soften the headline formulation

The reviewer proposes replacing:

> "A false-alarm rate is a property of the benchmark, not the tool."

with:

> A reported false-alarm rate is a property of the tool, the evaluated corpus,
> its labels and the scoring protocol **together** — not an intrinsic property
> of the tool alone.

**Accepted.** Our version is rhetorically stronger and literally false: it
deletes the tool from an explanation in which the tool obviously participates.
The replacement keeps the insight and is much harder to attack. This wording
should propagate to the site, the paper and the proposal.

### C2. Do not let the GPTScan/Slither comparison become a leaderboard

Those figures exist in our paper to demonstrate *incommensurability* —
GPTScan's 4.39% is against its own Top200 non-vulnerable set; Slither's 10.9% is
one-minus-precision from manual inspection of flagged contracts. They must stay
framed as an argument about denominators, never as a ranking we sit inside.

**Accepted** — and largely already true of §5.5, which prints the denominator
beside every row. Keep it that way.

### C3. Make the distinct contribution explicit against Berriche et al.

Pipeline-dependence of benchmark scores is not ours to claim. Our distinct
contribution in the smart-contract setting is four specific things, and the
paper should enumerate them rather than imply novelty:

1. A provenance-stratified **negative** class.
2. Vulnerability-**matching semantics** as a measured variable.
3. The observed relationship between router-selected ensemble size and false
   alarms.
4. Concrete silent-failure modes in security evaluation **infrastructure**.

---

## D — The thesis statement to lead with

The reviewer's proposed framing, which we accept as more defensible:

> We construct a provenance-stratified benchmark of Solidity smart contracts and
> investigate how negative-label provenance, vulnerability-matching rules, model
> context limits and execution environment affect measured detection
> performance. We observe a strong association between the number of specialists
> selected by our router and false-alarm rates. Our experiments also expose
> silent evaluation failures that can produce plausible but misleading results.
> We distinguish replicated findings from scoped results and unresolved causal
> explanations, and identify the controlled experiments necessary to establish
> the remaining claims.

It is less dramatic than "ensemble size dominates false alarms" and much harder
to dismantle, because it separates what we observed from what we have
established.

**Consequence for the paper title.** "Nobody Chooses k: Ensemble Size *Dominates*
False Alarms" asserts causality we have not earned. Either run the A2 experiment
and keep the title, or retitle to claim association.

---

## E — Order of work

| # | Task | Blocks | Effort |
|---|---|---|---|
| 1 | **Denominator ledger and full regeneration** (A1) | Everything | Days, no compute |
| 2 | **Controlled k experiment** (A2) | The paper's central claim | One corpus pass |
| 3 | **Check split leakage** (B6) | τ's robustness claim | Hours |
| 4 | **Repair negative-class validation** (A3) | The label-noise bound | Review time |
| 5 | **Re-run the context-window experiment, both classes** (B3) | RQ3's scope | One corpus pass |
| 6 | **Propagate the softened thesis wording** (C1) | Site, paper, proposal | Hours |
| 7 | **Make reproducibility claims precise** | Artifact credibility | Hours |

On (7): specify the exact repository revision, current regression-test status,
backend configuration, and the distinction between local execution and the
hosted demo — and **demonstrate** that local mode makes no external calls rather
than asserting it from configuration intent. A network-level check would settle
it.

---

## F — What the critique got right that we had not written down

Three things were genuinely new to us rather than already on our open list:

1. **The formula-versus-evidence distinction** (A2). We had the confound logged;
   we had not noticed we were treating `1 − (1 − p)^k` as explanation rather
   than as a fitted model with assumptions our specialists violate.
2. **Split leakage** (B6). Not previously considered at all.
3. **Verbatim ≠ supporting** (B5). We had this as an open question about
   fabrication; the reviewer's framing is sharper — a quote can be real and
   still not substantiate the claim, which is a limit on the evidence gate's
   guarantee rather than a measurement gap.

The denominator error (A1) was ours to find and we did not find it. It was
sitting under a header that claimed it had been fixed.
