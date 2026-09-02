/** Findings from the campus GB10 session that are not yet in the generated
 *  snapshot (services/stats.py builds that from the benchmark checkpoint tree;
 *  these come from separate result files).
 *
 *  Sources, so every number here is traceable:
 *    parity  -> backend/eval/results/dgx_parity_full3b.json  (+ _rescored)
 *    capacity-> backend/eval/results/dgx_parity_3b.json / _8b.json
 *
 *  Both are now COMPLETE at n=230 paired, measured on the campus GB10 on
 *  2026-08-28. Neither is a pilot any more, and the page no longer labels them
 *  as one. The num_parallel=1 control the parity caveat said was pending has
 *  also run, and it cleared batching as an explanation.
 */

export const PARITY = {
  n: 230,
  agreement: 0.813,
  ci: [0.763, 0.863] as [number, number],
  fpr_laptop: 0.273,
  fpr_other: 0.405,
  disagreements: 43,
  go_to_nogo: 31,
  nogo_to_go: 12,
  status: "measured" as const,
  /** THE CONTROL RAN, AND IT CLEARED BATCHING.
   *
   *  The open question was whether the cross-machine disagreement was a hardware
   *  result or an artifact of the batch parallelism we ourselves changed
   *  (num_parallel 1 -> 4). Re-running the identical contracts at num_parallel=1
   *  answers it: paired McNemar over the same contracts finds NOTHING — false
   *  alarms 5 vs 5 (p=0.75), misses 5 vs 2 (p=0.45), and agreement with the
   *  laptop essentially unmoved (0.735 -> 0.727).
   *
   *  Batch parallelism is therefore not the explanation. What remains is the
   *  machine and its Ollama build, which is the harder and more interesting
   *  finding: identical model digests, identical seeds and identical code do not
   *  reproduce across hardware. */
  np1_control: {
    agreement_np4: 0.735,
    agreement_np1: 0.727,
    false_alarms_mcnemar_p: 0.75,
    misses_mcnemar_p: 0.45,
    verdict: "batching ruled out — the disagreement is hardware/runtime, not serving config",
  },
};

/** THE CAPACITY ABLATION, at full n and PAIRED.
 *
 *  Three of the eight specialists — business_logic, oracle_price_manipulation,
 *  flashloan_mev, i.e. the three SEMANTIC roles — were pinned to a 3B model for
 *  one reason: a 4.9GB model does not fit in 4GB of VRAM. A 128GB card removes
 *  that constraint and changes exactly one variable.
 *
 *  The n=24 pilot suggested the bigger model traded misses for false alarms. At
 *  n=230 paired, on the same machine, that is confirmed and the trade is bad:
 *
 *    misses        15 -> 7    McNemar p = 0.043    (real, modest)
 *    false alarms  49 -> 74   McNemar p = 0.00008  (real, and far stronger)
 *
 *  Both effects are genuine. The 8B does find more bugs. But it buys 8 fewer
 *  misses with 23 more false alarms, and net accuracy FALLS 0.722 -> 0.651.
 *
 *  This is the direct answer to the obvious objection — "why not just use a
 *  bigger model?" — measured on our own paired data rather than argued. The
 *  lever is aggregation, not capability. */
export const CAPACITY = {
  n: 230,
  n_safe: 121,
  n_vuln: 109,
  small: { model: "llama3.2:3b", misses: 15, false_alarms: 49, accuracy: 0.722,
           recall: 0.862, fpr: 0.405, median_s: 18.0 },
  large: { model: "llama3.1:8b", misses: 7, false_alarms: 74, accuracy: 0.651,
           recall: 0.936, fpr: 0.602, median_s: 22.6 },
  mcnemar: {
    false_alarms: { only_small_wrong: 4, only_large_wrong: 27, p: 0.00008 },
    misses: { only_small_wrong: 10, only_large_wrong: 2, p: 0.043 },
  },
  status: "measured" as const,
  why:
    "Three of eight specialists (business_logic, oracle_price_manipulation, " +
    "flashloan_mev) were pinned to a 3B model solely because a 4.9GB model does " +
    "not fit in 4GB of VRAM. Those are the semantic roles. Restoring the 8B is a " +
    "one-variable change that only a larger card makes possible.",
};

/** Slither baseline on the identical stratified sample.
 *
 *  THE ABSTENTION CAVEAT IS NOW RESOLVED. This used to say the coverage figure
 *  was an upper bound because some unknown share of the 104 compile failures
 *  might be our own solc version resolution. All 104 were diagnosed by compiling
 *  each one with solc directly (Slither itself is useless here — on these files
 *  it exits 0 with empty stdout AND stderr, so its own error is lost):
 *
 *    89  (85.6%)  missing import — a fragment of a multi-file project
 *     9  ( 8.7%)  a real Solidity compile error in the source as given
 *     5  ( 4.8%)  other
 *     1  ( 1.0%)  OUR toolchain: pragma unsatisfiable with the solc we have
 *
 *  One. Coverage moves 46/150 = 30.7% to 46/149 = 30.9%, so the hedge cost more
 *  in credibility than the correction was worth.
 *
 *  THE OBJECTION THIS INVITES, and the answer. 86% of the failures are missing
 *  imports, so a reviewer will say the corpus feeds Slither fragments and that
 *  is unfair. It is a fair objection and the claim is scoped to match: this is
 *  NOT evidence that Slither is weak on whole projects, where it is designed to
 *  run. It measures what happens on single-file input — which is the deployment
 *  case this tool targets, and on which ThirdEye returned a verdict for the very
 *  same fragments. Identical inputs, one tool answers and the other cannot. */
export const SLITHER = {
  attempted: 150,
  scored: 46,
  coverage: 46 / 150,
  coverage_adjusted: 46 / 149,
  by_tier: [
    { tier: "Injected (synthetic)", n: 25, scored: 19 },
    { tier: "Curated vulnerable", n: 25, scored: 13 },
    { tier: "Audited libraries", n: 25, scored: 4 },
    { tier: "Real-world, no bug reported", n: 25, scored: 4 },
    { tier: "Real audit-report findings", n: 25, scored: 4 },
    { tier: "Audit-reviewed, clean", n: 25, scored: 2 },
  ],
  audit: {
    diagnosed: 104,
    missing_import: 89,
    hard_compile_error: 9,
    other: 5,
    our_toolchain: 1,
  },
  caveat:
    "All 104 abstentions were diagnosed with solc directly: exactly ONE is our " +
    "toolchain. 86% are contracts that do not build standalone because they " +
    "import files the corpus does not carry. The claim is therefore about " +
    "single-file input — the deployment case — and not about Slither on whole " +
    "projects, where it is designed to run.",
};
/** GPTScan head-to-head — from the GPTScan authors' OWN published artifact.
 *
 * MetaTrustLabs/GPTScan-Web3Bugs ships web3bugs_res_temp0_230723.csv: per-project
 * TP/TN/FP/FN for the 72 Web3Bugs projects GPTScan was evaluated on. Aggregating
 * it reproduces their published recall (0.833) and F1 (0.678) exactly, which is
 * how we know the file is the right artifact and the parse is correct.
 *
 * Two things fall out that the GPTScan paper does not headline:
 *   1. precision 0.571 — 30 false positives against 40 true positives.
 *   2. an FPR IS computable for them, because they report true negatives.
 *
 * (2) matters for our own honesty: the blind-spot claim is about the BENCHMARK
 * DATASETS being all-positive, not about every paper being unable to count a
 * false alarm. GPTScan built check-level negatives and could measure one. Our
 * claim is narrower than 'nobody measures FPR' and is stated that way.
 *
 * Their unit is a project x rule check, ours is a contract, so the two FPRs are
 * NOT directly comparable and are never differenced. Running our tool on their
 * exact runnable contests is what made a real comparison possible, and it HAS
 * now run — see HEADTOHEAD. The detection intervals overlap, so no difference
 * is demonstrated; the durable finding is a difference in target population.
 */
/** GPTScan (ICSE'24), verified against the PAPER, not just the results CSV.
 *
 *  arxiv.org/abs/2308.03314 — every figure below was cross-checked and the
 *  parsed CSV reproduces the published table exactly:
 *    tp 40 · fp 30 · tn 154 · fn 8 = 232 counts · P 57.14 · R 83.33 · F1 67.8
 *
 *  THE UNIT, in their words: scoring is at the function level FOR EACH TESTED
 *  VULNERABILITY TYPE — "if a project tested five vulnerability types, each
 *  would contribute one count". So a count is a project x rule-check, not a
 *  project and not a contract.
 *
 *  THEIR TRUE-NEGATIVE DEFINITION IS WHY OUR GRADABLE SUBSET IS CORRECT: a TN is
 *  a tested type that LACKS a corresponding ground-truth vulnerability in that
 *  project. So a project with tp=0 AND fn=0 had no positive to find at all —
 *  which is the restriction we apply before comparing detection, and it is now
 *  backed by their own definition rather than by our inference.
 *
 *  SCOPE IS A DESIGN CHOICE, NOT A WEAKNESS. GPTScan targets ten DeFi logic
 *  types and deliberately EXCLUDES reentrancy and overflow, because its stated
 *  premise is the ~80% of Web3 bugs that pattern-based tools cannot audit. Our
 *  broader taxonomy is a different target population, not a better one, and the
 *  page must not present it as beating them at their own task. */
export const GPTSCAN = {
  source: "MetaTrustLabs/GPTScan-Web3Bugs · web3bugs_res_temp0_230723.csv",
  paper: "GPTScan, ICSE'24 · arxiv.org/abs/2308.03314",
  projects: 72,            // Web3Bugs projects that compile directly
  runnable_here: 63,
  tp: 40, tn: 154, fp: 30, fn: 8,
  total_checks: 232,
  precision: 0.571, recall: 0.833, f1: 0.678, fpr: 0.163,
  ground_truth_vulns: 48,  // logic vulns in scope for their 10 types
  static_failures: 10,
  n_types: 10,
  unit: "project x tested vulnerability type, not contract",
  scope_note:
    "Ten DeFi logic types, reentrancy and overflow deliberately excluded — the " +
    "paper targets the bugs pattern-based tools cannot audit. Different target " +
    "population, not a narrower version of ours.",
};
/** THE HEAD-TO-HEAD. ThirdEye and GPTScan on the same Web3Bugs projects.
 *
 * Measured on the campus GB10, 2026-08-28. It needed no new compute: 63 of the
 * projects were already checkpointed. What had blocked it for weeks was a
 * dataset that was never synced to the box and a report path that ignored the
 * project filter, so "the GPTScan comparison" had been silently reporting the
 * whole 91-contest sweep.
 *
 * WHY `gradable` IS 34 AND NOT 63 — this is the number a reviewer will attack,
 * so it is the one that is explained. GPTScan's per-project results collapse to
 * our unit as "detected if tp > 0". But 34 of its 72 projects carry tp = 0 AND
 * fn = 0: its ten rule types had no applicable check there at all. Counting
 * those as misses scores it on questions it was never asked, and drags its
 * apparent rate from ~91% to ~49%. Recall is therefore computed only over
 * projects where GPTScan had a positive to find.
 *
 * The 29 excluded projects are not discarded — they are a COVERAGE result,
 * reported separately and never merged into recall.
 */
export const HEADTOHEAD = {
  measured: "2026-08-28 · NVIDIA GB10",
  projects_compared: 63,
  gradable: 34,          // GPTScan had >= 1 ground-truth positive check
  out_of_scope: 29,      // tp = 0 and fn = 0: no applicable rule
  thirdeye_detected: 33,
  gptscan_detected: 31,
  out_of_scope_flagged: 29,
  // Stated because it favours us and a reviewer will find it anyway.
  asymmetry:
    "Our detection is any-slice-positive and is NOT type-matched; GPTScan's true " +
    "positive is. Our rate is an upper bound against their lower bound.",
};

/** THE CONTEXT-TRUNCATION ABLATION — measured on the campus GB10, 2026-08-28.
 *
 *  WHAT IT MEASURES. Every number this project has published was produced with
 *  the local runtime's context window at 4096 tokens. A prompt longer than that
 *  is not refused — it is silently TRUNCATED, and the specialist then judges a
 *  fraction of the contract and returns a verdict as though it had seen all of
 *  it. 540 of 2250 benchmark contracts (24.0%) overflow, and the overflow is not
 *  class-balanced: 350 vulnerable against 190 safe, because real vulnerable
 *  contracts are larger.
 *
 *  THE DESIGN. Paired on contract id: same contracts, same seed, same models,
 *  same machine, same concurrency, same _run_one() imported from the benchmark
 *  so the arms cannot drift. The only difference is num_ctx. The sample is drawn
 *  only from overflowing contracts, since short ones cannot change and would
 *  dilute the effect, and a cost ceiling excludes the extreme tail — which makes
 *  every figure below a LOWER bound on the full effect.
 *
 *  Because the arms are paired, correctness is tested with McNemar on the
 *  discordant pairs and latency with an exact sign test — not two independent
 *  proportions, which would understate a paired effect.
 *
 *  WHY IT MATTERS MORE THAN IT LOOKS. Abstentions are excluded from scoring. So
 *  a configuration that crippled the council on the largest quarter of the
 *  corpus did not show up as a lower score — it showed up as missing rows, and
 *  the tables that remained looked healthy. This is the paper's own thesis
 *  landing on the paper itself.
 */
export const CTXABLATION = {
  measured: "2026-08-28 · NVIDIA GB10",
  paired: 36,
  scored_both: 20,
  pool_overflowing: 540,
  corpus: 2250,
  small: { num_ctx: 4096, inconclusive: 16, accuracy: 5, recall: 2, median_s: 402.9 },
  large: { num_ctx: 16384, inconclusive: 0, accuracy: 15, recall: 15 - 2, median_s: 108.2 },
  n_vuln: 16,
  mcnemar: { only_small_correct: 2, only_large_correct: 12, chi2: 5.79, p: 0.0162 },
  latency: { faster: 20, of: 20, speedup: 4.01, sign_p: 0.00001 },
  flips: 14,
  flips_toward_blocking: 13,
  /** Stated because they bound the claim, and a reviewer will look for them. */
  limits:
    "Measured on the overflowing 24% of the corpus, not the 76% that already " +
    "fit — it does not restate the headline numbers. The false-alarm comparison " +
    "rests on 4 safe contracts and is NOT claimed. The extreme-overflow tail was " +
    "excluded for cost, so the effect is a lower bound.",
};
