// ─────────────────────────────────────────────────────────────────────────────
// Every number the site displays, in one place, each traceable to a document
// in docs/.
//
// This file exists because the previous site baked in an n = 1,154 snapshot
// that was later superseded: regenerated over the full 2,142-row corpus, the
// pre-gate false-alarm rate moved 59.0% -> 72.2% and the gate rate
// 37.5% -> 45.9%, with non-overlapping intervals. A figure scattered across
// six components is a figure that gets half-updated. Import from here.
//
// The same trap caught the per-tier figures a second time, after this header
// was written: TIERS.fprShipped still held the n = 1,154 values (15.7 / 37.5 /
// 33.0) while the n column beside them was already full-corpus, so the table
// displayed two different denominators as one row. They are now the 2,142-row
// figures (27.8 / 54.7 / 44.8). The lesson the file was created for applies to
// the file itself: a superseded number survives wherever nobody re-reads it.
//
// Sources: docs/PAPER_FACTS.md, docs/FINDINGS.md, docs/PAPER_MSR2027.md.
// ─────────────────────────────────────────────────────────────────────────────

export const CORPUS = {
  total: 2250,
  safe: 1125,
  vulnerable: 1125,
  scored: 2142,
  scoredSafe: 1046,
  scoredVuln: 1096,
} as const;

export type Tier = {
  key: string;
  label: string;
  n: number;
  klass: "safe" | "vulnerable";
  how: string;
  fprShipped?: string;
};

// The point of the corpus: the SAFE class is stratified by how the label was
// obtained, which is what makes label provenance measurable at all.
export const TIERS: Tier[] = [
  {
    key: "audited_library",
    label: "Audited libraries",
    n: 172,
    klass: "safe",
    how: "OpenZeppelin and Solady releases — code that has been through repeated professional audit and very wide production use.",
    fprShipped: "27.8% [22.9, 33.4]",
  },
  {
    key: "audit_reviewed_clean",
    label: "Audit-reviewed, clean",
    n: 240,
    klass: "safe",
    how: "Contracts that appeared in a published audit report and received no finding. Reviewed by humans, but once, and under time pressure.",
    fprShipped: "54.7% [50.7, 58.7]",
  },
  {
    key: "realworld_no_bug_reported",
    label: "Real-world, no bug reported",
    n: 191,
    klass: "safe",
    how: "Deployed contracts with no public disclosure against them. The weakest safe label in the set: absence of a report is not evidence of absence.",
    fprShipped: "44.8% [37.9, 51.9]",
  },
  {
    key: "curated",
    label: "Curated vulnerable",
    n: 214,
    klass: "vulnerable",
    how: "SmartBugs-Curated and similar teaching sets — small, single-bug, unambiguous.",
  },
  {
    key: "injected",
    label: "Injected vulnerable",
    n: 170,
    klass: "vulnerable",
    how: "SolidiFI-style synthetic injection into otherwise clean code. Ground truth is exact by construction.",
  },
  {
    key: "audit_report",
    label: "Audit-report vulnerable",
    n: 167,
    klass: "vulnerable",
    how: "Real findings from published audits and DeFi incident write-ups. The hardest and most realistic bugs in the set.",
  },
];

// Headline detection performance. SAME verdicts in all three rows; only the
// rule that reads the stored findings changes.
export const SCORING_RULES = [
  {
    rule: "Before any gating",
    recall: "95.9%",
    recallCI: "[94.6, 96.9]",
    fpr: "72.2%",
    fprCI: "[69.4, 74.8]",
    shipped: false,
  },
  {
    rule: "Evidence gate",
    recall: "89.1%",
    recallCI: "[87.2, 90.8]",
    fpr: "45.9%",
    fprCI: "[42.9, 48.9]",
    shipped: true,
  },
  {
    rule: "Noisy-OR at τ = 0.99",
    recall: "84.9%",
    recallCI: "[82.7, 86.9]",
    fpr: "40.0%",
    fprCI: "[37.0, 43.0]",
    shipped: false,
  },
] as const;

// FINDING 0 — the largest effect in the project, and the one that replicated.
export const ENSEMBLE_SIZE = {
  seed0: [
    { k: 1, fpr: 12.2, n: 82 },
    { k: 2, fpr: 18.0, n: 272 },
    { k: 3, fpr: 39.2, n: 265 },
    { k: 4, fpr: 61.9, n: 202 },
    { k: 5, fpr: 80.7, n: 135 },
    { k: 6, fpr: 90.1, n: 71 },
  ],
  seed1: [
    { k: 2, fpr: 17.4, n: 46 },
    { k: 3, fpr: 33.3, n: 39 },
    { k: 4, fpr: 58.1, n: 31 },
    { k: 5, fpr: 70.0, n: 20 },
  ],
} as const;

export const SPECIALISTS = [
  { role: "reentrancy", label: "Reentrancy", model: "qwen2.5-coder:7b" },
  { role: "access_control", label: "Access control", model: "qwen2.5-coder:7b" },
  { role: "arithmetic", label: "Arithmetic", model: "qwen2.5-coder:7b" },
  { role: "proxy_upgradeability", label: "Proxy / upgradeability", model: "qwen2.5-coder:7b" },
  { role: "business_logic", label: "Business logic", model: "llama3.2:3b" },
  { role: "oracle_price_manipulation", label: "Oracle / price", model: "llama3.2:3b" },
  { role: "flashloan_mev", label: "Flash-loan / MEV", model: "llama3.2:3b" },
  { role: "dos_gas", label: "DoS / gas", model: "gemma3:4b" },
] as const;

export type Finding = {
  id: string;
  title: string;
  status: "SOUND" | "SOUND (scoped)" | "REFUTED" | "RETRACTED" | "OPEN";
  body: string;
  evidence: string;
};

export const FINDINGS: Finding[] = [
  {
    id: "F0",
    title: "The biggest driver of false alarms is a number nobody chooses",
    status: "SOUND",
    body:
      "On identical safe contracts, the false-alarm rate climbs monotonically with how many specialists the router happened to fire — 12.2% at k = 1 to 90.1% at k = 6. The council is a logical OR over k detectors, so contract-level false positives grow as 1 − (1 − p)^k. Nobody sets k; it falls out of the routing.",
    evidence:
      "2,142 scored contracts, replicated on a held-out seed (17.4 / 33.3 / 58.1 / 70.0 at k = 2–5).",
  },
  {
    id: "F1",
    title: "A false-alarm rate is a property of the benchmark, not the tool",
    status: "SOUND",
    body:
      "Holding the tool, the seed, the model digests and the machine fixed, five unreported evaluation choices each move the headline metric by more than any tool-versus-tool difference we found in the literature. The same stored verdicts, scored two defensible ways, give recall of 25.5% or 82.2%.",
    evidence: "docs/PAPER_MSR2027.md §5; the five choices are enumerated there.",
  },
  {
    id: "F2",
    title: "Label provenance moves the false-alarm rate — but less than it first appeared",
    status: "SOUND (scoped)",
    body:
      "Audited libraries draw a 27.8% false-alarm rate against 54.7% on audit-reviewed code. The effect is real but partly confounded by ensemble size: audited libraries draw a median of 2 specialists against 3 elsewhere, and at matched k = 2 the three tiers are statistically indistinguishable — 18.9% / 15.3% / 18.7%, intervals fully overlapping. The spread appears only at k ≥ 3, so it is reported stratified by k.",
    evidence: "Wilson intervals on the 1,046 asym-sound safe contracts of the full corpus; the k = 2 intervals fully overlap.",
  },
  {
    id: "F3",
    title: "The ~32% false-alarm floor is structural, not a threshold you can tune",
    status: "SOUND",
    body:
      "Raising the verdict threshold buys a lower false-alarm rate by giving up recall, and cannot push below roughly 32%. That floor is a property of the aggregation topology — an OR over k detectors — rather than of τ. Moving it needs a different way of combining findings, not a different number.",
    evidence: "Threshold sweep across the full corpus; τ = 0.9999 still sits at 32.1%.",
  },
  {
    id: "F4",
    title: "Dropping the noisiest specialist does not generalise",
    status: "REFUTED",
    body:
      "Excluding business_logic — which places ~42% of its findings on safe contracts — bought +8.3 points of recall at a matched ~32% false-alarm rate in-sample. On two held-out seeds the sign flipped with the threshold (+1.4, −2.7, +2.6, +0.6). The mechanism replicated; the benefit did not. A noisy specialist is not the same as a net-negative one, and we did not ship the change.",
    evidence: "Two held-out seeds, 334 and 332 scored contracts, pre-registered validator.",
  },
  {
    id: "F5",
    title: "Adversarial arbitration costs more than it returns on this corpus",
    status: "SOUND (scoped)",
    body:
      "A stronger independent judge re-reading each finding against its quote moves precision 49.6% → 52.9% (+3.3 points) while discarding 83% of all findings — recall collapses 93.6% → 32.9%. It retains 32.9% of true flags and 29.3% of false ones, i.e. near-uniform thinning, which is why precision barely moves: it does not buy the property it was adopted for, and a threshold achieves the same trade more cheaply. On the access-control slice it does add 34 points of precision, so the effect is corpus-dependent and we report both. Shipped OFF.",
    evidence: "n = 281 class-balanced contracts; the access-control ablation is n = 52 sound in all arms. Judge cost: 23.2 s/call as measured in the sweep, 83 s/call for qwen3:8b on the 4 GB demo laptop.",
  },
  {
    id: "F6",
    title: "A smaller model beat a larger one on the hardest role",
    status: "SOUND (scoped)",
    body:
      "llama3.2:3b outperforms llama3.1:8b on the business-logic specialist (p = 0.0303, 184 verified-intact paired contracts). Scope: that role only. It is not an argument that bigger models are worse — it is an argument that the role, not the model, was the problem.",
    evidence: "Paired McNemar test on contracts where both configurations ran an intact council.",
  },
];

export const TESTING = {
  tests: 54,
  quarantineRate: "7–8%",
  seeds: 2,
  seedSize: 360,
} as const;
