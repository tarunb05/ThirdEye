// ─────────────────────────────────────────────────────────────────────────────
// The pipeline's six stages — the single definition.
//
// Lives here because three places render them now: the How-it-works rail, the
// pinned scroll panel, and the Tool page's audit progress. Three copies of a
// six-item list is three chances for the Tool to claim a stage the pipeline
// does not have, which on a page whose subject is measurement discipline would
// be the worst possible place to let content drift.
// ─────────────────────────────────────────────────────────────────────────────

export type Stage = { n: string; name: string; what: string; why: string };

export const STAGES: Stage[] = [
  {
    n: "01",
    name: "Static pre-pass",
    what: "Slither runs if it is installed, and a lightweight feature extractor always does — payable functions, low-level calls, delegatecall, loops over dynamic arrays, assembly blocks.",
    why: "Its job is not to find the bug. It is to tell the router what kind of contract this is, cheaply, before any model is loaded.",
  },
  {
    n: "02",
    name: "Router",
    what: "Selects which of the 8 specialists to run, from the static signals and code features. A contract with no external call does not get the reentrancy specialist.",
    why: "Firing all 8 at every contract made safe code fail: each specialist is an independent chance to raise a flag, so the false-alarm rate compounds. This is the single biggest lever on precision — see the findings page.",
  },
  {
    n: "03",
    name: "Model-diverse council",
    what: "Each selected specialist is a separate prompt to a model chosen for that role, across three distinct model families running locally on Ollama.",
    why: "Different families fail differently. One model asked eight questions correlates its own mistakes; three families asked one question each do not.",
  },
  {
    n: "04",
    name: "Evidence gate",
    what: "A finding survives only if the specialist set found = true, returned a confidence of at least 0.6, AND quoted a line that appears verbatim in the submitted source.",
    why: "This is the anti-hallucination step. A model that invents a vulnerable line cannot produce a quote that matches the file, so the claim is dropped before it reaches you.",
  },
  {
    n: "05",
    name: "Risk pooling",
    what: "Surviving findings are combined with a noisy-OR: risk = 1 − Π(1 − confidence). The verdict is NO-GO when risk ≥ τ = 0.925.",
    why: "A single medium-confidence finding should not block a deploy, and five should. τ was re-selected identically in 8 of 10 random dev splits, so it is an operating point rather than one lucky partition.",
  },
  {
    n: "06",
    name: "Verdict",
    what: "GO, NO-GO, or INCONCLUSIVE — with the quotes, the per-specialist health, and the reason attached.",
    why: "INCONCLUSIVE exists so a broken run cannot masquerade as a clean one. If half or more of the specialists that ran errored, you get INCONCLUSIVE, never a green GO — two dead out of four is already enough.",
  },
];
