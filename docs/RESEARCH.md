# ThirdEye — Complete Research Record

**A single self-contained document for external critique.**

Umar Ahmed (PES2UG23CS662), Anvita Agarwal (PES2UG23CS085), Tarun B (PES2UG23CS644), V Lakshitha (PES2UG23CS665)
Department of Computer Science and Engineering, PES University, Bengaluru, India

Compiled 27 October 2026. Everything below traces to `docs/PAPER_FACTS.md`,
`docs/FINDINGS.md`, `docs/PAPER_MSR2027.md` and `docs/DECISION_LOG.md` in the
project repository. Where this document and those disagree, **§11 says so
explicitly** rather than silently picking one.

---

## 0. How to read this, and where to attack it

This is a research record, not a sales document. It is written to be attacked,
so it front-loads the places we already know are weak.

**The one-paragraph version.** We built a 2,250-contract Solidity benchmark
whose *safe* class is stratified by how the safe label was obtained, ran a
model-diverse local LLM council over 2,142 of them, and found that unreported
evaluation choices move the headline metric further than any tool-versus-tool
difference we could find in the literature. The single largest effect is one
nobody selects: how many specialists the router happened to fire. Our original
hypothesis — that a model-diverse council raises precision — is **refuted**.

**If you have ten minutes, attack these five things first:**

1. **§11.1** — the paper draft contains two different headline false-alarm
   rates (29.9% and 45.9%) from two different corpus sizes, in the same
   document. We found this while compiling this record. It is not yet fixed in
   the draft.
2. **§11.2** — the abstract's flagship span "16.0% → 90.2%" compares *different
   provenance tiers at different k*. The pooled, like-for-like span is
   12.2% → 90.1%. The claim survives; the way it is stated does not.
3. **§3.2** — our entire negative class rests on a 21-contract hand review. If
   that bound is wrong, every false-alarm number here moves.
4. **§5.3** — RQ3 is established on the vulnerable class only. The safe-class
   arm was destroyed by a backend outage and we never re-ran it.
5. **§6** — we published six invariants for avoiding silent failures and then
   violated one of them, in the instrument that produced §5.3.

**What would falsify the central claim.** FINDING 0 (§5.0) predicts that
false-alarm rate rises monotonically with *k* for any OR-style aggregation over
independent-ish detectors. Show a council whose FPR is flat in *k*, or show that
our *k* gradient is fully explained by a confound we did not control (contract
size runs the wrong way; cyclomatic complexity and external-call count are
**not** controlled — see §9), and the paper's spine breaks.

---

## 1. The problem

A paper reporting a new LLM-based vulnerability detector reports a recall and a
false-alarm rate. Readers compare those against the previous paper's two numbers
and form a view about which tool is better. That comparison is close to
meaningless.

Two figures from the literature, both verified against their source papers:

- **GPTScan** reports a **4.39%** false-alarm rate on a curated set of
  non-vulnerable contracts.
- **Heimdallr** measures *the same tool* at **97.50%** on real audit-contest
  projects.

Twenty-two-fold, with no change to the tool. The difference lies entirely in
which contracts were designated "not vulnerable."

Now the most-cited low-false-positive figure in the field, **Slither's 10.9%**.
Read the denominator: it is the share of *flagged* contracts that manual review
found wrong — one minus precision — established by sampling at least fifty
flagged contracts, on the reentrancy detector alone, **with no true-negative set
at all**. It is not FP/(FP+TN) and cannot be converted into one from the
published data. It is nonetheless the number LLM tools are informally held
against.

Berriche et al. show that scoring *pipelines* move benchmark outcomes in
cybersecurity question-answering by as much as eighty percentage points, across
eight benchmarks and ten models. Every benchmark in that study is
question-answering. **A multiple-choice question cannot produce a false alarm.**
A detection benchmark is a different object: it must *construct* the class of
things that are not bugs, and it must *decide* what counts as having found one.
Neither construction has a correct answer, both are usually unreported, and both
— we find — move the headline further than the tool does.

**Research questions.**

| | |
|---|---|
| **RQ1** | Does the *provenance of the safe label* change the false-alarm rate? |
| **RQ2** | Does the *matching rule* change recall? |
| **RQ3** | Does what the model was *permitted to read* change measured performance? |
| **RQ4** | Does the *execution environment* change the verdicts themselves? |

A fifth result, **FINDING 0**, was not an RQ. It emerged late, it is the largest
effect in the project, and it partially subsumes RQ1.

---

## 2. Claims at a glance

Status vocabulary is used strictly. **SOUND** = measured and replicated or
otherwise robust. **SCOPED** = holds, but only on a stated subset. **REFUTED** =
we tested it and it failed. **RETRACTED** = we published it and withdrew it.
**OPEN** = identified, not measured.

| # | Claim | Status | Key evidence |
|---|---|---|---|
| **F0** | Ensemble size *k* dominates the false-alarm rate: 12.2% at k=1 → 90.1% at k=6, monotone | **SOUND** | 2,142 scored; replicated on held-out seed 1 |
| **F1** | A false-alarm rate is a property of the benchmark, not the tool | **SOUND** | Same verdicts → recall 25.5% or 82.2% |
| **F2** | Label provenance moves the FPR — but far less than it first appeared | **SCOPED** | At matched k=2 the three tiers are indistinguishable |
| **F3** | There is a ~32% FPR floor, structural rather than tunable | **SOUND** | τ = 0.9999 still sits at 32.1% |
| **F4** | Dropping the noisiest specialist (`business_logic`) is a free win | **REFUTED** | Sign flipped on two held-out seeds |
| **F5** | Adversarial arbitration buys precision | **SCOPED / mostly negative** | +3.3 pts precision while discarding 83% of findings |
| **F6** | `llama3.2:3b` beats `llama3.1:8b` on the business-logic role | **SCOPED** | Paired McNemar, *p* = 0.0303, n = 184 |
| **H0** | *Original project hypothesis:* a model-diverse council raises precision | **REFUTED** | Council buys recall, not precision (§4) |

---

## 3. Benchmark construction

The benchmark is the instrument, so its construction is a contribution rather
than a preliminary.

### 3.1 Balance and tiers

2,250 Solidity contracts, balanced **1,125 safe : 1,125 vulnerable**. Both
halves are stratified into three tiers. The safe tiers are ordered by *how much
the safe label can be trusted* — this is the novel part.

| Safe tier | n scored | How "safe" was established |
|---|--:|---|
| Audited libraries | 172 | OpenZeppelin / Solady — repeated professional audit, very wide production use |
| Audit-reviewed, clean | 240 | In a published audit's scope, no finding filed. Reviewed by humans, once, under time pressure |
| Real-world, no bug reported | 191 | Deployed, no public disclosure — *absence of evidence* |

| Vulnerable tier | n scored | How "vulnerable" was established |
|---|--:|---|
| Curated | 214 | SmartBugs-style annotated vulnerabilities — small, single-bug, unambiguous |
| Injected | 170 | SolidiFI-style synthetic injection; ground truth exact by construction |
| Audit-report findings | 167 | Real findings from published audits and DeFi incident write-ups |

Tier 1 is as close to ground truth as this domain offers. Tier 3 is an inference
from silence. A tool's false-alarm rate is conventionally reported against
whichever of these a paper happened to use, without saying which.

### 3.2 The negative class is a claim, not a fact — and this is our weakest foundation

Because tier 3 is absence of evidence, some "false alarms" against it may be
real unreported bugs. We bound this by hand. A random sample (seed 2026) of 20
of the 79 blocked safe contracts, plus one from an earlier read, reviewed
against each contract's externally callable surface:

| Assessment | Count | Share |
|---|--:|--:|
| Clear tool error | 14 | **70%** |
| Unclear, needs a full read | 4 | 20% |
| Possible real bug in a "safe" contract | 2 | 10% |

So roughly 70% of blocked safe contracts are genuine tool errors, and **at most
30% of the false-alarm rate could be label noise.** Two contracts —
`w3b_90_indexlogic` and `w3b_68_amunbasket_bridge`, both with unmodified
external `mint`/`withdraw` surfaces — are flagged in the artifact as candidate
real defects in contracts the datasets call safe.

> **Attack this.** The bound rests on **21 contracts**, assessed from externally
> callable surfaces rather than full reads, by the authors rather than by
> independent reviewers, with no inter-rater agreement measured. Every
> false-alarm figure in this document inherits that uncertainty.

### 3.3 Sampling discipline

Samples are **nested and seeded**: extending a run from *n* to *n′* > *n* yields
a strict superset, so a longer run cannot silently change the population. Every
contract is checkpointed individually, which makes every table here re-scorable
without re-running inference — a property §5.2 relies on, producing a new result
from old checkpoints at zero inference cost.

### 3.4 One corpus we excluded

`web3bugs` is **72.2% contaminated** for our purposes and the contamination was
invisible until we looked for it. It is excluded from rate computations and the
exclusion is recorded rather than silent.

---

## 4. The instrument

The tool under measurement is not the contribution; we describe it only as far
as the experiments require.

**ThirdEye** routes a contract to up to eight single-class specialists —
reentrancy, access control, arithmetic, business logic, oracle/price
manipulation, flash-loan/MEV, DoS/gas, proxy upgradeability — each pinned to a
distinct open-weights base model served locally by **Ollama**. No API key, no
network call; the source never leaves the machine.

**Pipeline.**

1. **Static pre-pass.** Slither if installed, plus a lightweight feature
   extractor (payable functions, low-level calls, `delegatecall`, loops over
   dynamic arrays, assembly blocks). Its job is not to find the bug; it is to
   tell the router what kind of contract this is, cheaply, before any model
   loads.
2. **Router.** Selects which of the 8 specialists to run. A contract with no
   external call does not get the reentrancy specialist. **This is the single
   biggest lever on precision — see §5.0.**
3. **Model-diverse council.** Each selected specialist is a separate prompt to a
   model chosen for that role, across three distinct model families. Different
   families fail differently; one model asked eight questions correlates its own
   mistakes, three families asked one question each do not.
4. **Evidence gate.** A finding survives only if the specialist set
   `found = true`, returned `confidence ≥ 0.6`, **and** quoted a line appearing
   verbatim in the submitted source. This is the anti-hallucination step.
5. **Risk pooling.** `risk = 1 − ∏(1 − confᵢ)`, blocking at **τ = 0.925**.
6. **Verdict.** GO / NO-GO / INCONCLUSIVE, with quotes, per-specialist health
   and reason attached.

**The asymmetric terminal rule.** A dead specialist can only *suppress* a flag,
never invent one. Therefore NO-GO with errored specialists is sound; GO with
errored specialists is not. If **half or more** of the specialists that ran
errored, the verdict is INCONCLUSIVE, never GO — two dead out of four is already
enough.

**Verdict rules are never interchanged.** An earlier rule blocked on *any*
surviving finding — the same rule at τ → 0.

| Rule (n = 1,154) | tp/fp/tn/fn | FPR | Recall | Precision | F1 |
|---|---|--:|--:|--:|--:|
| OR-gate (as recorded) | 498/356/247/53 | 59.0% | 90.4% | 0.583 | 0.709 |
| **noisy-OR, τ = 0.925 (shipped)** | **445/180/423/106** | **29.9%** | **80.8%** | **0.712** | **0.757** |

> ⚠️ **These are n = 1,154 figures, superseded by the full corpus.** See §11.1.

Across 10 random dev/test splits (n = 233) thresholding wins 9 of 10. Per-class
weighting beats a flat threshold on only 3 of 10, so we attribute the gain to
**thresholding, not weighting**, and report the simpler mechanism. τ = 0.925 was
re-selected identically in 8 of 10 random dev splits, so it is an operating
point rather than one lucky partition.

**A result that undercuts our own design.** At τ = 0.925 the noisy-OR and the
evidence gate **disagree on 0 of 2,142 contracts.** The "third decision rule" we
had been reporting is the second one re-derived. We report this because it means
one of our stated mechanisms is, on this corpus, doing no independent work.

### 4.1 The original hypothesis is refuted

The project's founding hypothesis was that a model-diverse council raises
**precision**. On the access-control slice, re-run at n = 52 paired contracts
sound in all arms (superseding an n = 16 pilot whose precision figure did not
survive the larger sample):

| Arm | Precision | Recall | FPR | F1 |
|---|--:|--:|--:|--:|
| Single LLM | 50.0% | 22.2% | 11.8% | 0.308 |
| Council | 58.3% | 77.8% | 29.4% | 0.667 |
| Council + arbitration | 92.3% | 66.7% | 2.9% | 0.774 |

The gain is in **recall** (22.2% → 77.8%), not precision (50.0% → 58.3%). On
Etherscan-50, the only other early corpus with a negative class, the council
**loses**: precision 0.067 / recall 0.167, against a single LLM's 0.182 / 0.667
and an LLM+Slither pipeline's 0.140 / 1.000.

That corpus has scraped, noisy ground truth and we weight it accordingly. But
the hypothesis was about precision, and on the available evidence that specific
hypothesis is **refuted**. Model diversity is simultaneously what buys the
recall and what destroys the precision; they are not separable by prompt tuning,
only by the aggregation rule.

---

## 5. Results

All experiments hold the tool, the seed, the model digests and — except in RQ4 —
the machine fixed. Wilson intervals throughout; never Wald, whose width
collapses to zero at the boundaries where several of these rates sit.

### 5.0 FINDING 0 — ensemble size, the effect nobody chooses

Same safe contracts, same rule. The only variable is how many specialists the
static router actually fired. All 1,046 asym-sound safe rows, evidence gate:

| k | audited_library | realworld_no_bug | audit_reviewed_clean |
|--:|--:|--:|--:|
| 1 | 16.0% [8.3, 28.5] (n=50) | 11.1% [3.1, 32.8] (n=18) | — |
| 2 | 18.9% [12.1, 28.2] (n=90) | 15.3% [8.2, 26.5] (n=59) | 18.7% [12.8, 26.5] (n=123) |
| 3 | 26.8% [17.9, 38.1] (n=71) | 53.1% [36.4, 69.1] (n=32) | 42.0% [34.6, 49.7] (n=162) |
| 4 | 41.9% [28.4, 56.7] (n=43) | 62.2% [47.6, 74.9] (n=45) | 69.3% [60.3, 77.0] (n=114) |
| 5 | 68.8% [44.4, 85.8] (n=16) | 75.0% [56.6, 87.3] (n=28) | 84.6% [75.8, 90.6] (n=91) |
| 6 | — | — | 90.2% [80.2, 95.4] (n=61) |

**Pooled across tiers, and replicated on a held-out seed:**

| k | seed 0 | seed 1 (held out) |
|--:|--:|--:|
| 1 | 12.2% (n=82) | 0.0% (n=15) |
| 2 | 18.0% (n=272) | 17.4% (n=46) |
| 3 | 39.2% (n=265) | 33.3% (n=39) |
| 4 | 61.9% (n=202) | 58.1% (n=31) |
| 5 | 80.7% (n=135) | 70.0% (n=20) |
| 6 | 90.1% (n=71) | 100.0% (n=9) |

Monotone on both seeds, tracking within a few points at every k with n ≥ 20.
(k = 7–8 cells are n ≤ 15 and carry no weight.)

**The mechanism.** The council is a logical OR over *k* detectors, so
contract-level false positives grow as **1 − (1 − p)^k**. Nobody sets *k*; it
falls out of the routing. This is the mechanism beneath three other results:

1. **It confounds RQ1.** `audited_library` draws a median of **2** specialists;
   both other tiers draw **3**. At matched k = 2 the three tiers are
   statistically indistinguishable — 18.9% / 15.3% / 18.7%, intervals fully
   overlapping.
2. **It explains the ~32% FPR floor.** Thresholding cannot undo an OR over *k*
   detectors; it only raises the bar each detector must clear. The floor is a
   property of the aggregation *topology*, not of τ.
3. **It predicts that excluding `business_logic` is a topology change, not a
   threshold change** — that specialist is always selected, so dropping it
   reduces *k* corpus-wide. See §5.6 for why that prediction's *magnitude*
   failed anyway.

This is the one headline claim that replicated on the same day another failed.
It was not selected by inspecting seed 0 — it is a structural property of the
aggregation that seed 0 merely made visible.

### 5.1 RQ1 — the provenance of the safe label

| Tier | n | Blocked | FPR (full corpus) |
|---|--:|--:|--:|
| Audited libraries | 172 | — | **27.8% [22.9, 33.4]** |
| Audit-reviewed, clean | 240 | — | **54.7% [50.7, 58.7]** |
| Real-world, no bug reported | 191 | — | **44.8% [37.9, 51.9]** |

The same tool evaluated against OpenZeppelin would report ~28%; evaluated
against contest code it reports ~55%. **But see §5.0:** at matched *k* = 2 the
tiers are indistinguishable, so the spread appears only at *k* ≥ 3 and must be
reported stratified by *k* or with *k* as a stated covariate. A within-stratum
effect survives (library stays lowest at k = 3, 4, 5), so provenance is real,
but it is **substantially smaller than the marginal comparison implies.**

We found this confound in our own headline claim, after publishing a draft that
reported it marginally.

### 5.2 RQ2 — what counts as a detection

Two protocols appear in the literature and neither is usually named:

- **any-slice-positive** — the tool flagged the contract and the contract
  carries the label. Most head-to-head comparisons use this.
- **type-matched** — the finding that fired must itself name the labelled
  category. Durieux et al.'s unit, and GPTScan's.

Re-scoring the *same checkpoints* through the *same shipped rule*, changing
nothing but the protocol (denominator: the 349 vulnerable contracts carrying a
mapped DASP-10 label; 202 of 551 carry none and are excluded):

| Protocol | Detected | Recall |
|---|--:|--:|
| any-slice-positive | 287 / 349 | **82.2%** |
| type-matched | 89 / 349 | **25.5%** |

**A 56.7-point spread with no change to any verdict** — but that mixes two
different things. The council has eight roles, five of which map unambiguously
onto DASP-10, and **158 of 349 contracts (45.3%) carry only classes no role
covers.** Part of the spread is *our* coverage gap, not a property of the
protocol.

| Set | n | any-slice | type-matched | Spread |
|---|--:|--:|--:|--:|
| All labelled contracts | 349 | 82.2% | 25.5% | 56.7 pts |
| **Coverage-controlled** | **187** | **77.0%** | **45.5%** | **31.6 pts** |

So ~25 points are attributable to our role set and **31.6 points to the scoring
protocol alone.** We take the controlled figure as the claim. The uncontrolled
56.7 is not discarded — it is the number a reader of our headline recall would
actually be misled by — but it is reported as a *joint* effect, never as
protocol alone.

| DASP-10 class | n | any-slice | type-matched | Specialist? |
|---|--:|--:|--:|---|
| unchecked low-level calls | 109 | 89.0% | — | **none** |
| reentrancy | 86 | 76.7% | 29.1% [20.5, 39.4] | yes |
| arithmetic | 79 | 77.2% | 62.0% [51.0, 71.9] | yes |
| time manipulation | 40 | 92.5% | — | **none** |
| access control | 17 | 88.2% | 70.6% [46.9, 86.7] | yes |
| denial of service | 8 | 62.5% | 50.0% [21.5, 78.5] | yes |

Our two largest labelled classes have **no specialist at all** and are
nonetheless "detected" at 89.0% and 92.5%. Reentrancy — the class the field has
studied longest — is flagged on 76.7% of its contracts but *named* by the
reentrancy specialist on 29.1%.

We report **[25.5%, 82.2%]** as a bracket rather than either endpoint. 25.5% is
a *lower* bound: only five of eight roles have an unambiguous DASP slot, and we
deliberately refuse to stretch `business_logic`, `oracle_price_manipulation` and
`proxy_upgradeability` into "other," which would manufacture type-matched hits.

**This makes comparison with prior work fair for the first time.** Durieux et
al.'s units are type-matched: nine tools combined reach 42% of 115 tagged
vulnerabilities, the best single tool 27%, Slither 17%. Our 25.5% sits inside
that band, while returning a verdict on 100% of contracts against Slither's 31%.
Reported as 82.2%, the same comparison would read as a two-fold win over the
entire field combined — an artifact of protocol, not of capability.

### 5.3 RQ3 — what the model was permitted to read

The local runtime truncates any prompt exceeding `num_ctx` **without error**,
and abstentions are excluded from scoring. A misconfiguration therefore *removes
rows* rather than lowering a score. 540 of 2,250 contracts (24.0%) overflow a
4,096-token window, and the overflow is class-skewed — 350 vulnerable against
190 safe, because real buggy contracts are larger.

Paired ablation on identical contracts, 4,096 → 16,384, vulnerable class
(36 paired, 20 scored in both arms):

| | 4,096 | 16,384 |
|---|--:|--:|
| Abstention | 44.4% | **0.0%** |
| Recall | 12.5% | **81.2%** |
| Accuracy | 25.0% | **75.0%** |

McNemar *b* = 2, *c* = 12, ***p* = 0.016**. The larger window is also **4.01×
faster** (sign test *p* < 0.0001) — truncation triggers context shifting, so the
misconfiguration cost both accuracy and time while appearing in neither.

> **Limitation, stated rather than managed.** The safe-class arm of this
> experiment is **not reported**. Our 2026-09-25 run was corrupted by a backend
> outage that left 145/176 and 108/176 rows as total council failures; only 31
> pairs scored in both arms, and those 31 are whatever ran while the backend was
> alive. **RQ3 is therefore established on the vulnerable class only**, and our
> headline false-alarm rate may be an under-estimate by an amount this work does
> not bound. This is our most important open item.

### 5.4 RQ4 — which machine produced the verdicts

Identical contract ids, seeds and byte-identical model digests, two hosts:

| Arm | n | Agreement with laptop | Acc (DGX) | Acc (laptop) |
|---|--:|--:|--:|--:|
| `full3b` (main) | 230 | **0.735** | 0.722 | 0.622 |
| `full3b`, `num_parallel = 1` | 227 | 0.727 | 0.736 | 0.621 |

Roughly **one verdict in four flips across machines.** A `num_parallel = 1`
control excludes batch parallelism as the cause (paired McNemar *p* = 0.75).
Backend and hardware nondeterminism is documented elsewhere; what we add is its
**propagation to security verdicts**, and therefore to a published rate.

**Capacity is not the lever (negative result).** Restoring a 2.7× larger model
on the three semantic roles — a one-variable change on the same 230 contracts —
*increases* false alarms 49 → 74 (McNemar ***p* = 0.00008**) while reducing
misses 15 → 7 (*p* = 0.043), for a net accuracy drop of 0.722 → 0.651. Stronger
associative reasoning reads more benign patterns as vulnerabilities.

### 5.5 Calibration against the literature

| Source | Rate | Negative class | Denominator |
|---|--:|---|---|
| GPTScan, self-reported | 4.39% | Top200 non-vulnerable | FP/(FP+TN) |
| Slither, self-reported | 10.9% | *none* — sample of flagged | **1 − precision** |
| **ThirdEye, audited-library tier** | **27.8%** | OpenZeppelin / Solady | FP/(FP+TN) |
| COMPSAC'26, local 4-bit | 34.09% | Paired safe variants | FP/(FP+TN) |
| **ThirdEye, overall** | **45.9%** | 1,046 safe, three tiers | FP/(FP+TN) |
| **ThirdEye, audit-reviewed tier** | **54.7%** | Contest code, no bug filed | FP/(FP+TN) |
| GPTScan, measured by Heimdallr | 97.50% | Sherlock contest projects | FP/(FP+TN) |

We do **not** claim 45.9% is good. We claim it is *interpretable*: it carries a
stated negative class, a per-tier decomposition, a hand-audited label-noise
bound, and intervals.

**Against Slither on 150 identical contracts.** Slither answered 46; ThirdEye
answered 150. Where Slither answers it is **more precise than we are** —
32 tp / 2 fp, a 5.9% false-discovery rate corroborating the 10.9% its own paper
reports — against our 0.712 precision. Its 104 abstentions were diagnosed with
`solc` directly and **exactly one** was attributable to our toolchain; the rest
are multi-file contest codebases and pragma mismatches. Slither is a
high-precision, low-coverage instrument; we are a moderate-precision,
full-coverage one.

**Against GPTScan on 34 gradable shared projects.** 33/34 against 31/34, with
**overlapping** intervals: no detection difference is demonstrated, and we report
that rather than a win.

### 5.6 F4 — the result we retracted

Excluding `business_logic` — which places ~42% of its findings on safe contracts
— bought **+8.3 points of recall at a matched ~32% false-alarm rate in-sample.**
On two held-out seeds the sign flipped with the threshold: **+1.4, −2.7, +2.6,
+0.6** (dJ at τ = 0.925 and τ = 0.99). The mechanism replicated; the benefit did
not.

A noisy specialist is not the same as a net-negative one. **We did not ship the
change**, and the +8.3 figure is retired rather than quietly dropped.

### 5.7 F5 — adversarial arbitration

A stronger independent judge re-reads each finding against its quote.

| | Precision | Recall | FPR |
|---|--:|--:|--:|
| Baseline | 49.6% | 93.6% | 95.0% |
| + arbitration | **52.9%** | **32.9%** | **29.3%** |

It moves precision **+3.3 points while discarding 83% of all findings.** It
retains 32.9% of true flags and 29.3% of false ones — **near-uniform thinning**,
which is why precision barely moves. It does not buy the property it was adopted
for, and a threshold achieves the same trade more cheaply.

On the access-control slice it adds **+34 points** of precision (58.3% → 92.3%).
Same judge, same code, +34 on one corpus and +3.3 on another. We report the
disagreement rather than the flattering half of it. **Shipped OFF.**

Cost: 23.2 s/call in the sweep, 83 s/call for `qwen3:8b` on the 4 GB demo
laptop. The judge is a reasoning model and **97% of its output is discarded.**

> **This result was retracted once.** We previously reported arbitration winning
> 4 of 10 held-out splits. That number was produced by a judge that never
> answered: `LOCAL_JUDGE_MODEL` defaulted to a model not installed on the
> evaluation host, every call returned HTTP 404, and the unparseable-output path
> **failed open** — returning `verdict="real", upheld=True, confidence=0.4`. All
> 234 findings received an identical verdict and were upheld unconditionally, so
> arbitration dropped nothing and "no gain" was true by construction. Nothing in
> the output distinguished this from a judge that had adjudicated and agreed.
> Re-measured with a working judge, the conclusion held. **The retraction is a
> correction of method, not of conclusion** — the earlier number was unearned,
> and it was also approximately right.

### 5.8 F6 — a smaller model beat a larger one

`llama3.2:3b` outperforms `llama3.1:8b` on the business-logic specialist
(paired McNemar, *p* = 0.0303, 184 verified-intact paired contracts). **Scope:
that role only.** It is not an argument that bigger models are worse — it is an
argument that the role, not the model, was the problem.

---

## 6. Silent failure modes

Seven defects found during this work, each of which produced *plausible* metrics
rather than obvious garbage. Directional bias is what makes them dangerous.

| # | Defect | Effect on the reported metric |
|--:|---|---|
| 1 | Pinned model absent; at exactly 50% errored the `>50%` fail-closed rule does not trip | Half-dead council records a clean GO; a 1,152-contract run invalidated |
| 2 | Partial-council results treated as terminal | 32/198 rows had errored specialists — **100% of them GO** |
| 3 | Provider quota drained mid-run, checkpointed as terminal | Bakes a transient outage permanently into recall |
| 4 | Arbitration silently defaulted to a hosted backend | The "local tier" was not local |
| 5 | Arbiter config keyed on names the caller never passes | Precision collapsed to 0.094 and looked like a finding |
| 6 | Subsampling by `items[:N]` | Filename order clusters by project; the "sample" was 263 consecutive files |
| 7 | Health-probe timeout shorter than a cold model load | Aborts a healthy backend |

Additional instances found in our own measurement infrastructure: a guard that
reported a **100% dead arm as 100% sound**; a `gate0` check that **counted
models instead of checking them by name** (a healthy-looking Ollama was serving
a different model store, and every call to the missing model failed silently); a
baseline report builder that could not see 580 completed rows; a generated
report that asserted a null result **its own table refuted**; and a buffered log
read as live.

**Proposed invariants.**

1. A verdict is terminal only if the whole council ran.
2. Transient ≠ deterministic — provider failures must never be checkpointed as
   results.
3. Every stage records the backend and model it *actually used*.
4. Config lookups must fail loudly, never fall back.
5. Samples must be nested and seeded.
6. Probe timeouts must exceed measured worst-case cold start.

**We then violated invariant (2) ourselves.** The context-ablation runner — the
instrument measuring RQ3 — wrote rows in which every specialist had errored into
its checkpoint directory, and its resume path returned them verbatim, so a retry
silently reused an outage instead of repairing it. That is the failure reported
in §5.3. We record it because it is the strongest available evidence that these
invariants are not obvious in retrospect: they were written by the authors,
published in a prior draft, and violated in the same codebase.

---

## 7. Threats to validity

**Construct.** Tier-3 "safe" is absence of evidence. §3.2 bounds this at ≈30% by
hand review, but the bound rests on 21 contracts assessed from externally
callable surfaces, not full reads, by the authors, with no inter-rater
agreement.

**Internal.** RQ3 is established on the vulnerable class only. The type-matched
mapping in RQ2 covers five of eight roles; a more generous map would raise
25.5%, which is why it is a lower bound and why the coverage-controlled 31.6
points, not 56.7, is the claim. The RQ1 gradient is not explained by contract
size, which runs opposite to it — but we have **not** controlled for cyclomatic
complexity or external-call count, either of which could still carry part of the
effect, including part of the *k* gradient in §5.0.

**External.** One tool, one language, one model family set, two machines. The
*mechanisms* — constructed negatives, matching rules, silent truncation,
execution nondeterminism — are not specific to any of these, but the magnitudes
certainly are.

**Statistical.** RQ3 rests on 20 paired contracts and RQ1's smallest tier on
172. The k = 1 and k = 6 cells in §5.0 are n = 82 and n = 71 pooled, and the
held-out seed's k = 1 cell is n = 15 with an observed 0.0%. Wilson intervals
throughout, never Wald.

---

## 8. What is not claimed

- **Not** that ThirdEye is a good auditor. A 45.9% false-alarm rate is not
  deployable unattended, and scored type-matched our recall falls inside the
  band of the static analysers we set out to beat.
- **Not** that the benchmark is representative of all Solidity.
- **Not** that benchmark scores being configuration-dependent is a new
  observation — Berriche et al. established that, in a neighbouring domain,
  first.
- **Not** that our rate is comparable to every figure in §5.5. Two are computed
  on a different denominator, which is why the denominator is printed beside
  each.
- **Not** that we beat GPTScan. The head-to-head intervals overlap.
- **Not** that the council was a good idea for its stated purpose. It was
  adopted to raise precision and it does not.

---

## 9. Open questions

| | Question | Status |
|---|---|---|
| **O1** | Retrieval grounding is wired to nothing — what would it buy? | OPEN, not measured |
| **O2** | Do the confident-wrong findings *fabricate* their evidence, or quote real code and misread it? | OPEN, now answerable from stored checkpoints |
| **O3** | Reconcile "the council hypothesis is refuted" with the access-control slice where the council clearly wins | OPEN — we have a mechanism story (recall vs precision) but not a measurement |
| **O4** | The safe-class arm of RQ3 | OPEN — needs a clean re-run |
| **O5** | Does the *k* gradient survive controlling for cyclomatic complexity and external-call count? | **OPEN — the most important threat to F0** |
| **O6** | x86 Slither re-run for a cleaner baseline | OPEN |

---

## 10. Reproduction

Corpus, loaders, per-contract checkpoints for every run, replay tooling, the
generated results index, and a chronological decision log recording each
correction made during this work are in the repository. **Every table above is
re-scorable from committed checkpoints without re-running inference** — no GPU
required.

The full pipeline runs on a 4 GB laptop GPU (RTX 3050). A live demo of the
architecture, with a recorded run replayable stage by stage, is deployed at
`third-eye-capstone.vercel.app`.

Artifact scale at last count: 18,078 lines of source across 61 commits, 42
backend regression tests pinning the defects in §6, and 3,707 lines of
documentation.

---

## 11. Known internal inconsistencies — read before citing any number

These are defects in **our own documents**, found while compiling this record on
27 October 2026. They are listed here rather than fixed silently, because a
paper whose thesis is "unreported choices corrupt reported numbers" has no
business hiding its own.

### 11.1 Two headline false-alarm rates in the same paper draft

`docs/PAPER_MSR2027.md` reports **45.9%** in the abstract (full corpus, 2,142
rows) and **29.9%** in §4, §5.3 and §8 (n = 1,154, superseded). Per-tier figures
have the same problem: §5.1 and §5.5 of the draft still carry **15.7% / 37.5%**
where the full corpus gives **27.8% / 54.7%**.

The full-corpus regeneration moved the pre-gate rate 59.0% → 72.2% and the gated
rate 37.5% → 45.9%, **with non-overlapping intervals**. The full-corpus figures
are correct; the draft has not been swept end to end. **This document uses the
full-corpus figures throughout.**

### 11.2 The abstract's flagship span mixes tiers

The abstract states false alarms "rise from **16.0%** at one specialist to
**90.2%** at six." Those endpoints come from the *per-tier* table: 16.0% is
`audited_library` at k = 1, and 90.2% is `audit_reviewed_clean` at k = 6 —
**different tiers**. A reviewer will call this a confounded comparison, and they
will be right about the presentation.

The like-for-like pooled span is **12.2% → 90.1%**, which is what this document
and the public site use. The finding survives the correction; the sentence does
not.

### 11.3 Repository URL

§10 of the paper draft points at `github.com/tarunb05/ThirdEye`. The live
repository is `github.com/umarahmed10/third-eye-capstone`. One of these needs to
become the other before submission.

### 11.4 Status of the τ-sweep third rule

The paper describes three decision rules. At τ = 0.925 the noisy-OR and the
evidence gate **disagree on 0 of 2,142 contracts** — the third rule is the
second re-derived. The draft's three-step decomposition is marked SUPERSEDED in
the findings register but still reads as three independent mechanisms in places.

---

## 12. Author note

Author order in the current draft is a proposal, not a decision. For any venue
offering institutional reimbursement, only one author is eligible and must be
the corresponding author; that has not been fixed.

---

*This document is deliberately adversarial toward its own project. If you find
something it does not already admit, that is the most useful thing you can tell
us.*
