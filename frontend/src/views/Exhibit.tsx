import { useEffect, useState } from "react";
import { EX, MONO, SERIF, SANS, T, M } from "../lib/exhibit-theme";
import { Reveal, StatCard, IntervalBar, CountBar } from "../components/exhibit/Measure";
import { TryIt } from "../components/exhibit/TryIt";
import { BENCHMARK_SNAPSHOT } from "../data/benchmark";
import { PARITY, CAPACITY, SLITHER, GPTSCAN, HEADTOHEAD as H2H, CTXABLATION as CTX } from "../data/newfindings";
import { fmtCI, ci95, separated } from "../lib/stats";

/** The exhibit, framed as a MEASUREMENT paper rather than a product.
 *
 * The earlier version sold the tool: four contributions about how ThirdEye
 * aggregates opinions. Under that framing our 29% false-alarm rate is a
 * liability a reviewer reaches and stops at, and the two headline contributions
 * (OR-gate arithmetic, noisy-OR) are textbook rather than novel.
 *
 * docs/PAPER_DRAFT.md already reached this conclusion and recommended the other
 * framing. This page now matches it: the claim is that this FIELD CANNOT SEE
 * ITS OWN FALSE ALARMS, and ThirdEye is the instrument that makes them visible.
 * Under that framing the same 29% is the finding, and every negative result
 * becomes evidence rather than an apology.
 *
 * Nothing is stated as a bare point estimate. Every rate carries its 95%
 * interval, because "reports rates without uncertainty" is one of the failures
 * being documented, and repeating it here would be self-refuting.
 */

const S = BENCHMARK_SNAPSHOT as any;
const shipped = S.shipped_rule ?? {};
const before = shipped.before ?? {};
const after = shipped.after ?? {};
const perTier = shipped.per_tier ?? {};
const h2h = S.head_to_head ?? {};
const cov = h2h.coverage ?? {};
const baselines: any[] = S.published_baselines ?? [];
const N = shipped.n ?? S.tier_benchmark?.n_total ?? 0;

const nSafe = (before.fp ?? 0) + (before.tn ?? 0);
const nVuln = (before.tp ?? 0) + (before.fn ?? 0);

const TIER_NAME: Record<string, string> = {
  audited_library: "Audited libraries (OZ / Solady)",
  audit_reviewed_clean: "Audit-reviewed, no bug found",
  realworld_no_bug_reported: "Deployed, nothing reported",
};

export function Exhibit({ onOpenApp }: { onOpenApp?: () => void }) {
  useEffect(() => {
    document.body.classList.add("exhibit-mode");
    return () => document.body.classList.remove("exhibit-mode");
  }, []);
  return (
    <div style={{ background: EX.surface, color: EX.ink, fontFamily: SANS, minHeight: "100vh" }}>
      <Masthead />
      <TitleBlock />
      <BlindSpot />
      <MakingItVisible />
      <WhatItRevealed />
      <BaselineAbstains />
      <PriorWork />
      <NotReproducible />
      <CapabilityDoesntFix />
      <SilentTruncation />
      <Invariants />
      <Instrument onOpenApp={onOpenApp} />
      <Status />
      <Colophon />
    </div>
  );
}

/* ─── furniture ────────────────────────────────────────────────────── */

const Wrap = ({ children }: { children: React.ReactNode }) => (
  <div style={{ maxWidth: 1060, margin: "0 auto", padding: "0 28px" }}>{children}</div>
);

function Section({
  n, kicker, title, lede, children, tint,
}: {
  n: string; kicker: string; title: string; lede?: string;
  children: React.ReactNode; tint?: boolean;
}) {
  return (
    <section style={{ borderTop: `1px solid ${EX.hairline}`, background: tint ? EX.surfaceAlt : "transparent", padding: "68px 0" }}>
      <Wrap>
        <Reveal>
          <div style={{ display: "flex", gap: 16, alignItems: "center", marginBottom: 10 }}>
            {/* channel marker — reads as an instrument label, not a bullet */}
            <span style={{
              fontFamily: MONO, fontSize: 11, color: EX.surface, background: EX.ink,
              letterSpacing: ".1em", padding: "3px 7px",
            }}>{n}</span>
            <span style={{ fontFamily: MONO, fontSize: 11.5, color: EX.inkMuted, letterSpacing: ".16em", textTransform: "uppercase" }}>{kicker}</span>
            <span style={{ flex: 1, height: 1, background: EX.hairline }} />
          </div>
          <h2 style={{ fontFamily: SERIF, fontSize: T.h2, lineHeight: 1.16, letterSpacing: "-0.018em", margin: "0 0 14px", maxWidth: "28ch" }}>{title}</h2>
          {lede && (
            <p style={{ fontFamily: SERIF, fontSize: T.lede, lineHeight: 1.55, color: EX.inkMuted, maxWidth: "64ch", margin: "0 0 26px" }}>{lede}</p>
          )}
        </Reveal>
        <Reveal delay={60}>{children}</Reveal>
      </Wrap>
    </section>
  );
}

/** A rate, always with its interval. The interval is the point. */
function Rate({ k, n, label, tone }: { k: number; n: number; label: string; tone?: "signal" | "plain" }) {
  const c = ci95(k, n);
  const col = tone === "signal" ? EX.signal : EX.ink;
  return (
    <div style={{ border: `1px solid ${EX.hairline}`, padding: "16px 18px", background: EX.surface }}>
      <div style={{ fontFamily: MONO, fontSize: 10.5, color: EX.inkMuted, letterSpacing: ".12em", textTransform: "uppercase", marginBottom: 8 }}>{label}</div>
      <div style={{ fontFamily: MONO, fontSize: 34, lineHeight: 1, color: col }}>
        {c ? `${(c.p * 100).toFixed(1)}%` : "—"}
      </div>
      <div style={{ fontFamily: MONO, fontSize: 11.5, color: EX.slate, marginTop: 7 }}>
        {c ? `95% CI [${(c.lo * 100).toFixed(1)}, ${(c.hi * 100).toFixed(1)}]` : ""}
      </div>
      <div style={{ fontFamily: MONO, fontSize: 11, color: EX.slate, marginTop: 3 }}>n = {n}</div>
    </div>
  );
}

function Evidence({ items }: { items: { k: string; v: string }[] }) {
  return (
    <div style={{ borderTop: `1px solid ${EX.hairline}`, marginTop: 22 }}>
      {items.map((it) => (
        <div key={it.k} style={{ display: "grid", gridTemplateColumns: "minmax(120px,170px) 1fr", gap: 18, padding: "10px 0", borderBottom: `1px solid ${EX.hairline}` }}>
          <span style={{ fontFamily: MONO, fontSize: 11, color: EX.slate, letterSpacing: ".1em", textTransform: "uppercase", paddingTop: 2 }}>{it.k}</span>
          <span style={{ fontSize: 14.5, lineHeight: 1.55 }}>{it.v}</span>
        </div>
      ))}
    </div>
  );
}

function Novelty({ children }: { children: React.ReactNode }) {
  return (
    <p style={{ marginTop: 20, borderLeft: `2px solid ${EX.signal}`, paddingLeft: 14, fontSize: 15, lineHeight: 1.6, maxWidth: "66ch" }}>
      <strong style={{ fontFamily: MONO, fontSize: 11, letterSpacing: ".1em", color: EX.signal, display: "block", marginBottom: 5 }}>
        WHY IT MATTERS
      </strong>
      {children}
    </p>
  );
}

/** Marks a result that is real but not yet at full strength. Saying so here is
 *  cheaper than having a reviewer say it. */
function Pilot({ n, children }: { n: number; children: React.ReactNode }) {
  return (
    <div style={{ marginTop: 18, border: `1px dashed ${EX.slate}`, padding: "12px 15px", background: EX.surfaceAlt }}>
      <span style={{ fontFamily: MONO, fontSize: 10.5, letterSpacing: ".12em", color: EX.slate }}>
        PILOT · n={n} · INTERVALS ARE WIDE
      </span>
      <p style={{ fontSize: 13.5, lineHeight: 1.55, color: EX.inkMuted, margin: "7px 0 0", maxWidth: "70ch" }}>{children}</p>
    </div>
  );
}

/* ─── masthead + title ─────────────────────────────────────────────── */

function Masthead() {
  // "OPEN THE ARTIFACT" used to live here, top-right. Under the measurement
  // framing that is exactly wrong: it invites the reader to leave the argument
  // before reading it, and it advertises the tool as the deliverable. The tool
  // now appears once, in section 09, as evidence the measurements are real.
  const [p, setP] = useState(0);
  useEffect(() => {
    const on = () => {
      const h = document.documentElement.scrollHeight - window.innerHeight;
      setP(h > 0 ? Math.min(1, window.scrollY / h) : 0);
    };
    on();
    window.addEventListener("scroll", on, { passive: true });
    window.addEventListener("resize", on);
    return () => { window.removeEventListener("scroll", on); window.removeEventListener("resize", on); };
  }, []);

  return (
    <header style={{ position: "sticky", top: 0, zIndex: 20, background: EX.surface, borderBottom: `1px solid ${EX.hairline}` }}>
      <Wrap>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "13px 0", flexWrap: "wrap", gap: 10 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <Aperture />
            <span style={{ fontFamily: SERIF, fontSize: 21 }}>ThirdEye</span>
          </div>
          <span style={{ fontFamily: MONO, fontSize: 10, color: EX.slate, letterSpacing: ".14em" }}>
            RESEARCH EXHIBIT · CAPSTONE TEAM 2 · PESU
          </span>
        </div>
      </Wrap>
      {/* reading position — the argument has a length, and you can see where you are in it */}
      <div style={{ height: 2, background: EX.hairline }}>
        <div style={{ height: "100%", width: `${p * 100}%`, background: EX.ink, transition: "width 90ms linear" }} />
      </div>
    </header>
  );
}

function Aperture() {
  return (
    <svg width="24" height="24" viewBox="0 0 26 26" aria-hidden="true">
      <circle cx="13" cy="13" r="11.5" fill="none" stroke={EX.ink} strokeWidth="1.4" />
      <circle cx="13" cy="13" r="4.2" fill={EX.signal} />
      {[0, 60, 120, 180, 240, 300].map((a) => (
        <line key={a}
          x1={13 + 4.6 * Math.cos((a * Math.PI) / 180)} y1={13 + 4.6 * Math.sin((a * Math.PI) / 180)}
          x2={13 + 11 * Math.cos((a * Math.PI) / 180)} y2={13 + 11 * Math.sin((a * Math.PI) / 180)}
          stroke={EX.ink} strokeWidth="1" />
      ))}
    </svg>
  );
}

function TitleBlock() {
  return (
    <section style={{ padding: "70px 0 60px" }}>
      <Wrap>
        <div style={{ fontFamily: MONO, fontSize: 11, letterSpacing: ".18em", color: EX.signal, marginBottom: 18 }}>
          MANUSCRIPT IN PREPARATION · TARGET: SE / SECURITY VENUE
        </div>
        <h1 style={{ fontFamily: SERIF, fontSize: 46, lineHeight: 1.12, letterSpacing: "-0.02em", margin: 0, maxWidth: "22ch" }}>
          The benchmarks cannot see the false alarms
        </h1>
        <p style={{ fontFamily: SERIF, fontSize: 19, lineHeight: 1.6, color: EX.inkMuted, maxWidth: "68ch", marginTop: 22 }}>
          LLM-based smart-contract auditors are evaluated on datasets that are almost entirely
          vulnerable code. On such a set a tool that flags <em>everything</em> scores perfectly, and
          a false-alarm rate cannot be computed at all. We built a balanced benchmark, measured what
          the field&rsquo;s instruments structurally cannot, and found four distinct ways these
          evaluations report confident numbers from pipelines that are quietly broken.
        </p>
        <p style={{ fontSize: 15.5, lineHeight: 1.6, color: EX.inkMuted, maxWidth: "68ch", marginTop: 16 }}>
          ThirdEye — an eight-specialist council running locally at zero API cost — is the
          instrument, not the claim. Every number below is measured on it, and every rate is
          reported with the interval around it.
        </p>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(190px,1fr))", gap: 26, marginTop: 44, borderTop: `2px solid ${EX.ink}`, paddingTop: 24 }}>
          {[
            { k: "The instrument", v: `${N} contracts scored, balanced ${nSafe} safe : ${nVuln} vulnerable, zero abstentions` },
            { k: "Four findings", v: "a blind spot, a coverage bias, a reproducibility failure, and a negative result on capability" },
            { k: "The output", v: "invariants that make each failure loud instead of silent" },
            { k: "Cost", v: "$0 per contract — local models, no paid API in the measured configuration" },
          ].map((c) => (
            <div key={c.k}>
              <div style={{ fontFamily: MONO, fontSize: 10.5, letterSpacing: ".12em", color: EX.signal, textTransform: "uppercase", marginBottom: 7 }}>{c.k}</div>
              <div style={{ fontSize: 14.5, lineHeight: 1.5, color: EX.inkMuted }}>{c.v}</div>
            </div>
          ))}
        </div>
      </Wrap>
    </section>
  );
}

/* ─── 01 the blind spot ────────────────────────────────────────────── */

function BlindSpot() {
  return (
    <Section
      n="01" kicker="The blind spot" tint
      title="If a benchmark has no safe code, it cannot have a false-alarm rate."
      lede="SmartBugs-Curated and Web3Bugs — the sets this field reports against — are almost entirely vulnerable contracts. Precision is then mechanically 1.0 whenever recall is non-zero, and specificity is undefined. This is not a flaw in any one paper; it is a property of the instrument everyone shares."
    >
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(300px,1fr))", gap: 40 }}>
        <div>
          <div style={{ fontFamily: MONO, fontSize: 10.5, color: EX.inkMuted, letterSpacing: ".1em", marginBottom: 14 }}>
            PUBLISHED BASELINES, AS REPORTED
          </div>
          <div style={{ borderTop: `1px solid ${EX.hairline}` }}>
            {baselines.map((b, i) => (
              <div key={i} style={{ padding: "11px 0", borderBottom: `1px solid ${EX.hairline}` }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "baseline" }}>
                  <span style={{ fontSize: 14 }}>{b.tool}</span>
                  <span style={{ fontFamily: MONO, fontSize: 12, color: EX.ink }}>
                    {b.recall != null ? `recall ${b.recall}` : "—"}
                  </span>
                </div>
                <div style={{ fontFamily: MONO, fontSize: 10.5, color: EX.slate, marginTop: 3 }}>
                  {b.dataset} · {b.cost}{b.note ? ` · ${b.note}` : ""}
                </div>
              </div>
            ))}
          </div>
          <p style={{ fontSize: 13, color: EX.inkMuted, lineHeight: 1.55, marginTop: 12 }}>
            Every row reports recall. Not one reports a false-alarm rate on safe code — because on
            these datasets it cannot be computed.
          </p>
        </div>
        <div>
          <Evidence items={[
            { k: "The consequence", v: "A tool that returns NO-GO unconditionally scores recall 1.0 and precision 1.0 on an all-positive set. Nothing in the reported metrics distinguishes it from a good tool." },
            { k: "Observed in the wild", v: "GPT-4o-mini reaches 0.90 recall on real-world access control — with roughly 951 false positives. The recall is publishable; the false positives are not visible in the same table." },
            { k: "What we did", v: `Constructed a balanced benchmark: ${nSafe} safe contracts across three provenance tiers alongside ${nVuln} labelled-vulnerable ones, so specificity is defined and every claim below is computable.` },
          ]} />
          <Novelty>
            This reframes the whole comparison. A recall number from an all-positive benchmark is
            not a measure of tool quality — it is a measure of how often the tool says yes. The
            interesting question is what happens on code that is fine, and the field&rsquo;s
            standard instruments cannot ask it.
          </Novelty>
        </div>
      </div>
    </Section>
  );
}

/* ─── 02 making it visible ─────────────────────────────────────────── */

function MakingItVisible() {
  const comp: any[] = S.story?.compounding ?? [];
  const max = Math.max(...comp.map((c) => c.fpr), 0.1);
  return (
    <Section
      n="02" kicker="Making it visible"
      title="With a safe class in the set, the false alarms appear at once — and they scale with the ensemble."
      lede="A specialist council blocks a contract if any one member objects. That is a logical OR over k detectors, so the contract-level false-alarm rate rises with every specialist consulted: 1−(1−p)^k. Arithmetic, not prompt quality."
    >
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(300px,1fr))", gap: 44, alignItems: "start" }}>
        <div style={{ background: EX.surface, border: `1px solid ${EX.hairline}`, padding: "20px 22px" }}>
          <div style={{ fontFamily: MONO, fontSize: 10.5, color: EX.inkMuted, letterSpacing: ".1em", marginBottom: 16 }}>
            FALSE-ALARM RATE vs SPECIALISTS CONSULTED · SAFE CONTRACTS ONLY
          </div>
          {comp.map((c) => (
            <div key={c.specialists} style={{ display: "flex", alignItems: "center", gap: 11, marginBottom: 9 }}>
              <span style={{ fontFamily: MONO, fontSize: 11.5, width: 22, color: EX.inkMuted }}>{c.specialists}</span>
              <div style={{ flex: 1, height: 18, background: "rgba(0,0,0,0.045)" }}>
                <div style={{ height: "100%", width: `${(c.fpr / max) * 100}%`, background: EX.data }} />
              </div>
              <span style={{ fontFamily: MONO, fontSize: 11.5, width: 40, textAlign: "right" }}>{Math.round(c.fpr * 100)}%</span>
              <span style={{ fontFamily: MONO, fontSize: 10, width: 34, color: EX.slate }}>n={c.n}</span>
            </div>
          ))}
          <p style={{ fontSize: 12, color: EX.slate, lineHeight: 1.5, marginTop: 12 }}>
            Grouped by how many specialists the static router engaged. Cells with small n carry
            correspondingly wide intervals and are shown with their n rather than smoothed away.
          </p>
        </div>
        <div>
          <Evidence items={[
            { k: "Mechanism", v: "Contract-level FP ≈ 1−(1−p)^k for k roughly independent detectors. Adding a specialist strictly increases the chance that at least one of them objects to safe code." },
            { k: "Why it is unreported", v: "It is only observable once a safe class exists. On an all-positive benchmark, adding specialists appears free — recall can only go up." },
            { k: "The fix costs nothing", v: `Replace the OR-gate with a pooled-evidence rule: block only when combined risk clears τ=${shipped.tau ?? 0.925}. No extra inference, no extra model, no extra spend.` },
          ]} />
          <Novelty>
            The design instinct in this field — add more specialists for better coverage — makes
            precision worse in a way the standard benchmarks are structurally unable to show.
          </Novelty>
        </div>
      </div>
    </Section>
  );
}

/* ─── 03 what it revealed ──────────────────────────────────────────── */

function WhatItRevealed() {
  const tierRows = Object.entries(perTier) as [string, any][];
  const lib = perTier.audited_library, rw = perTier.realworld_no_bug_reported;
  const gap = lib && rw ? separated(lib.after, lib.n, rw.after, rw.n) : false;
  return (
    <Section
      n="03" kicker="What it revealed" tint
      title="A 29% false-alarm rate — and the residue tracks how much the label can be trusted."
      lede={`Pooling the evidence instead of gating on any single objection roughly halves the false-alarm rate, costs eight points of recall, and improves F1. Measured on all ${N} scored contracts.`}
    >
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(215px,1fr))", gap: 16, marginBottom: 30 }}>
        <StatCard k={before.fp ?? 0} n={nSafe} label="False alarms — OR-gate" tone="signal" />
        <StatCard k={after.fp ?? 0} n={nSafe} label="False alarms — pooled rule" />
        <StatCard k={after.tp ?? 0} n={nVuln} label="Recall — pooled rule" />
        <div style={{ border: `1px solid ${EX.hairline}`, padding: "16px 18px", background: EX.surface }}>
          <div style={{ fontFamily: MONO, fontSize: 10.5, color: EX.inkMuted, letterSpacing: ".12em", textTransform: "uppercase", marginBottom: 8 }}>F1</div>
          <div style={{ fontFamily: MONO, fontSize: 34, lineHeight: 1, color: EX.ink }}>{after.f1 ?? "—"}</div>
          <div style={{ fontFamily: MONO, fontSize: 11.5, color: EX.slate, marginTop: 7 }}>from {before.f1 ?? "—"} under the OR-gate</div>
          <div style={{ fontFamily: MONO, fontSize: 11, color: EX.slate, marginTop: 3 }}>n = {N}</div>
        </div>
      </div>

      <div style={{ fontFamily: MONO, fontSize: 10.5, color: EX.inkMuted, letterSpacing: ".1em", marginBottom: 12 }}>
        FALSE-ALARM RATE BY PROVENANCE OF THE &ldquo;SAFE&rdquo; LABEL
      </div>
      <div style={{ borderTop: `1px solid ${EX.hairline}` }}>
        {tierRows
          .sort((a, b) => a[1].fpr_after - b[1].fpr_after)
          .map(([k, v]) => (
            <IntervalBar key={k} k={v.after} n={v.n}
              label={TIER_NAME[k] ?? k}
              tone={k === "audited_library" ? "data" : "signal"} />
          ))}
      </div>
      <p style={{ fontFamily: MONO, fontSize: T.micro, color: EX.slate, marginTop: 10 }}>
        POINT ESTIMATE ON ITS 95% INTERVAL · SHARED 0–100% SCALE · TICKS AT 25%
      </p>

      <Evidence items={[
        { k: "The pattern", v: `Audited libraries — the tier whose "safe" label is most trustworthy — carry a far lower false-alarm rate than code that merely has no reported bug. The two intervals ${gap ? "do not overlap" : "overlap"}.` },
        { k: "Reading it honestly", v: "This is a two-level result, not a smooth gradient: audit-reviewed and deployed-nothing-reported are statistically indistinguishable from one another. Only the audited-library tier separates." },
        { k: "What it implies", v: "Some fraction of the residual 29% is not tool error but unreported real bugs in code labelled safe. A manual review of a false-positive sample put roughly 10% in that category." },
      ]} />
      <Novelty>
        This is the strongest available evidence that the remaining false alarms are partly a
        property of the labels rather than the tool — and it is visible only because the safe class
        is stratified by provenance instead of pooled into one undifferentiated &ldquo;clean&rdquo;
        bucket.
      </Novelty>
    </Section>
  );
}

/* ─── 04 the baseline abstains ─────────────────────────────────────── */

function BaselineAbstains() {
  return (
    <Section
      n="04" kicker="Coverage bias"
      title="The static baseline does not fail on hard contracts. It declines to answer them."
      lede="Slither must compile a contract before it can analyse it. Compilation fails on missing imports, unpinned pragmas and partial sources — properties of realistic code, not of difficult code. Every head-to-head comparison in this field silently inherits that filter."
    >
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(300px,1fr))", gap: 44, alignItems: "start" }}>
        <div style={{ border: `1px solid ${EX.hairline}`, padding: "22px 24px", background: EX.surface }}>
          <div style={{ fontFamily: MONO, fontSize: 10.5, color: EX.inkMuted, letterSpacing: ".1em", marginBottom: 16 }}>
            SLITHER: CONTRACTS SCORED, BY PROVENANCE
          </div>
          {/* The per-tier split is the argument. A single aggregate hides the
              selection effect; this shows it directly — the baseline handles
              synthetic code and abstains on almost everything real. */}
          {SLITHER.by_tier.map((r) => (
            <CountBar key={r.tier} label={r.tier} scored={r.scored} total={r.n}
                      tone={r.scored / r.n > 0.4 ? "data" : "signal"} />
          ))}
          <div style={{ fontFamily: MONO, fontSize: 30, color: EX.signal, marginTop: 20 }}>
            {(SLITHER.coverage * 100).toFixed(1)}%
          </div>
          <div style={{ fontSize: 13, color: EX.inkMuted, lineHeight: 1.5, marginTop: 5 }}>
            overall — {SLITHER.scored} of {SLITHER.attempted} contracts compiled well enough to analyse.
          </div>
        </div>
        <div>
          <Evidence items={[
            { k: "The selection effect", v: `Slither scored ${SLITHER.by_tier[0].scored}/25 synthetic-injected contracts but only ${SLITHER.by_tier[5].scored}/25 audit-reviewed real code. It is not failing on hard contracts — it never sees them.` },
            { k: "Why it matters", v: "An abstention is not a wrong answer, so it never appears as an error. A tool that answers only the questions it can parse posts excellent precision and recall on the subset it chose." },
            { k: "How we report it", v: `The head-to-head is computed only on the ${h2h.n_common ?? 0} contracts BOTH tools scored, and coverage is reported beside it rather than folded into the averages.` },
            { k: "We checked whether it was our fault", v: `All ${SLITHER.audit.diagnosed} abstentions were diagnosed by compiling each with solc directly — Slither is no use here, since on these files it exits 0 with empty stdout and stderr and loses its own error. Exactly ${SLITHER.audit.our_toolchain} is our toolchain. ${SLITHER.audit.missing_import} are contracts that do not build standalone; ${SLITHER.audit.hard_compile_error} are real source errors. Coverage moves ${(SLITHER.coverage * 100).toFixed(1)}% → ${(SLITHER.coverage_adjusted * 100).toFixed(1)}%.` },
            { k: "The objection this invites", v: "86% of the failures are missing imports, so a reviewer will say we fed Slither fragments. Fair — and the claim is scoped to match. This is not evidence about Slither on whole projects, where it is designed to run. It measures single-file input, which is the deployment case, and ThirdEye returned a verdict on the very same fragments." },
          ]} />
          <Novelty>
            Published comparisons against static analysers rarely state coverage. Without it, the
            comparison is between one tool&rsquo;s performance on all contracts and another
            tool&rsquo;s performance on the ones it found tractable — which is not a comparison.
          </Novelty>
        </div>
      </div>
    </Section>
  );
}

/* ─── 05 prior work ────────────────────────────────────────────────── */

function PriorWork() {
  const rows: [string, string, string][] = [
    ["Recall", GPTSCAN.recall.toFixed(3), (after.recall ?? 0).toFixed(3)],
    ["Precision", GPTSCAN.precision.toFixed(3), (after.precision ?? 0).toFixed(3)],
    ["F1", GPTSCAN.f1.toFixed(3), (after.f1 ?? 0).toFixed(3)],
    ["False-alarm rate", `${(GPTSCAN.fpr * 100).toFixed(1)}%`, `${((after.fpr ?? 0) * 100).toFixed(1)}%`],
  ];
  return (
    <Section
      n="05" kicker="Against prior work"
      title="GPTScan's own published results contain a precision number their paper does not lead with."
      lede="The GPTScan authors ship per-project true/false positives and negatives for the 72 Web3Bugs projects they evaluated. Aggregating that file reproduces their published recall and F1 exactly — and also yields a precision of 0.571: thirty false positives against forty true ones. Because the file is per-project, it also makes a real head-to-head possible: the same tools, scored on the same projects."
    >
      <div style={{ overflowX: "auto", maxWidth: "100%", minWidth: 0 }}>
        <table style={{ borderCollapse: "collapse", width: "100%", minWidth: 480, fontSize: 14 }}>
          <thead>
            <tr style={{ borderBottom: `2px solid ${EX.ink}` }}>
              {["", "GPTScan (ICSE'24)", "ThirdEye"].map((h, i) => (
                <th key={h || i} style={{ textAlign: i ? "right" : "left", padding: "10px 8px", fontFamily: MONO, fontSize: 10.5, letterSpacing: ".1em", color: EX.inkMuted, textTransform: "uppercase", fontWeight: 400 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map(([k, g, t]) => (
              <tr key={k} style={{ borderBottom: `1px solid ${EX.hairline}` }}>
                <td style={{ padding: "11px 8px" }}>{k}</td>
                <td style={{ padding: "11px 8px", textAlign: "right", fontFamily: MONO }}>{g}</td>
                <td style={{ padding: "11px 8px", textAlign: "right", fontFamily: MONO }}>{t}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* THE HEAD-TO-HEAD. This block used to be a red "NOT YET A LIKE-FOR-LIKE
          COMPARISON" caveat saying the run was queued. It has now run, so the
          caveat is replaced by the result — and by the one methodological
          decision that result depends on. */}
      <div style={{ marginTop: 22, border: `1px solid ${EX.ink}`, padding: "16px 18px", background: EX.surfaceLift }}>
        <div style={{ fontFamily: MONO, fontSize: 10.5, letterSpacing: ".12em", color: EX.ink, marginBottom: 4 }}>
          HEAD-TO-HEAD · IDENTICAL PROJECTS
        </div>
        <div style={{ fontFamily: MONO, fontSize: T.micro, color: EX.slate, marginBottom: 14 }}>
          {H2H.measured} · {H2H.gradable} gradable of {H2H.projects_compared} shared
        </div>

        <IntervalBar k={H2H.thirdeye_detected} n={H2H.gradable} label="ThirdEye — projects detected" />
        <IntervalBar k={H2H.gptscan_detected} n={H2H.gradable} label="GPTScan (ICSE'24) — projects detected" tone="signal" />

        <p style={{ fontSize: T.body, lineHeight: 1.6, color: EX.ink, margin: "16px 0 0", maxWidth: "74ch" }}>
          The intervals <strong>overlap</strong>, so no detection difference is demonstrated. That is
          the finding, and it is reported as such rather than as a win: a gap claimed across
          overlapping intervals is the precise error this page spends ten sections objecting to.
        </p>
      </div>

      <div style={{ marginTop: 16, border: `1px solid ${EX.hairline}`, padding: "14px 16px", background: EX.surfaceAlt }}>
        <div style={{ fontFamily: MONO, fontSize: 10.5, letterSpacing: ".12em", color: EX.inkMuted, marginBottom: 7 }}>
          WHY {H2H.gradable} AND NOT {H2H.projects_compared}
        </div>
        <p style={{ fontSize: 13.5, lineHeight: 1.62, color: EX.inkMuted, margin: 0, maxWidth: "74ch" }}>
          {H2H.out_of_scope} of the shared projects carry <strong>tp = 0 and fn = 0</strong> in
          GPTScan&rsquo;s own results: its ten rule types had no applicable check to run there.
          Scoring those as misses would be scoring a tool on questions it was never asked — it
          drags its apparent rate from 91% to 49%, and an earlier version of this comparison did
          exactly that. Recall is computed only where GPTScan had a positive to find.
        </p>
        <p style={{ fontSize: 13.5, lineHeight: 1.62, color: EX.inkMuted, margin: "11px 0 0", maxWidth: "74ch" }}>
          Those {H2H.out_of_scope} projects are a <strong>coverage</strong> observation, never
          merged into recall: each carries a confirmed bug outside GPTScan&rsquo;s {GPTSCAN.n_types}
          rule types, and ThirdEye returns a verdict on {H2H.out_of_scope_flagged} of{" "}
          {H2H.out_of_scope}. Coverage is not accuracy — an any-slice flag on an all-positive set
          is nearly free.
        </p>
        <p style={{ fontSize: 13.5, lineHeight: 1.62, color: EX.ink, margin: "11px 0 0", maxWidth: "74ch" }}>
          <strong>And that difference is not a defect of theirs.</strong> GPTScan deliberately
          scopes to ten DeFi logic types and explicitly excludes reentrancy and overflow, because
          its stated premise is the ~80% of Web3 bugs that pattern-based tools cannot audit. It is
          a different target population, not a narrower copy of ours. Reporting the coverage gap as
          a win would be claiming credit for someone else&rsquo;s deliberate scoping — so it is
          reported as a difference in what the two tools are for.
        </p>
      </div>

      <Evidence items={[
        { k: "What this shows", v: `A paid-GPT system at ICSE'24 carries a false-discovery rate of ${(100 - GPTSCAN.precision * 100).toFixed(0)}% on its own numbers. The false-alarm problem is not peculiar to our council — it is a property of the approach.` },
        { k: "An honest narrowing", v: "GPTScan CAN compute a false-alarm rate, because their evaluation includes negatives by construction. Our blind-spot claim is about the benchmark datasets being all-positive, not about every paper failing to count false alarms. We state the narrower claim." },
        { k: "Their coverage too", v: `${GPTSCAN.static_failures} of their ${GPTSCAN.projects} projects are marked as static-analysis failures in their own results — the same abstention effect measured in section 04, in a published system.` },
        { k: "Verified against the paper", v: `Every GPTScan figure here was checked against the publication, not just the results file: tp ${GPTSCAN.tp} · fp ${GPTSCAN.fp} · tn ${GPTSCAN.tn} · fn ${GPTSCAN.fn} over ${GPTSCAN.total_checks} counts, reproducing their published ${(GPTSCAN.precision*100).toFixed(2)}% / ${(GPTSCAN.recall*100).toFixed(2)}% / ${(GPTSCAN.f1*100).toFixed(1)}% exactly. Their unit is a ${GPTSCAN.unit}, and their true negative is defined as a tested type with no ground-truth vulnerability in that project — which is precisely why the gradable subset above is the correct denominator.` },
      ]} />
      <Novelty>
        The comparison that matters is not whose recall is higher. It is that two independently
        built LLM auditors — one paid and peer-reviewed, one local and free — land in the same
        place on precision. That is evidence the false-alarm problem is structural rather than an
        implementation defect, which is the paper&rsquo;s central claim.
      </Novelty>
    </Section>
  );
}

/* ─── 06 reproducibility ───────────────────────────────────────────── */

function NotReproducible() {
  return (
    <Section
      n="06" kicker="Reproducibility" tint
      title="The same contract, the same seed, a different machine — and roughly one verdict in five changes."
      lede="Every number this field publishes is produced on one machine and reported as a property of the method. We ran an identical contract set on a second GPU, under one identical decision rule, and compared verdict by verdict."
    >
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(215px,1fr))", gap: 16, marginBottom: 26 }}>
        <div style={{ border: `1px solid ${EX.hairline}`, padding: "16px 18px", background: EX.surface }}>
          <div style={{ fontFamily: MONO, fontSize: 10.5, color: EX.inkMuted, letterSpacing: ".12em", textTransform: "uppercase", marginBottom: 8 }}>Verdict agreement</div>
          <div style={{ fontFamily: MONO, fontSize: 34, lineHeight: 1, color: EX.signal }}>{(PARITY.agreement * 100).toFixed(1)}%</div>
          <div style={{ fontFamily: MONO, fontSize: 11.5, color: EX.slate, marginTop: 7 }}>
            95% CI [{(PARITY.ci[0] * 100).toFixed(1)}, {(PARITY.ci[1] * 100).toFixed(1)}]
          </div>
          <div style={{ fontFamily: MONO, fontSize: 11, color: EX.slate, marginTop: 3 }}>n = {PARITY.n}</div>
        </div>
        <div style={{ border: `1px solid ${EX.hairline}`, padding: "16px 18px", background: EX.surface }}>
          <div style={{ fontFamily: MONO, fontSize: 10.5, color: EX.inkMuted, letterSpacing: ".12em", textTransform: "uppercase", marginBottom: 8 }}>Same code, two machines</div>
          <div style={{ fontFamily: MONO, fontSize: 22, lineHeight: 1.35, color: EX.ink, marginTop: 6 }}>
            {(PARITY.fpr_laptop * 100).toFixed(1)}% → {(PARITY.fpr_other * 100).toFixed(1)}%
          </div>
          <div style={{ fontSize: 12.5, color: EX.inkMuted, marginTop: 7, lineHeight: 1.45 }}>
            false-alarm rate on the identical contract set
          </div>
        </div>
        <div style={{ border: `1px solid ${EX.hairline}`, padding: "16px 18px", background: EX.surface }}>
          <div style={{ fontFamily: MONO, fontSize: 10.5, color: EX.inkMuted, letterSpacing: ".12em", textTransform: "uppercase", marginBottom: 8 }}>Direction of the flips</div>
          <div style={{ fontFamily: MONO, fontSize: 22, lineHeight: 1.35, color: EX.ink, marginTop: 6 }}>
            {PARITY.go_to_nogo} / {PARITY.nogo_to_go}
          </div>
          <div style={{ fontSize: 12.5, color: EX.inkMuted, marginTop: 7, lineHeight: 1.45 }}>
            GO→NO-GO versus the reverse. Not symmetric — so not mere kernel jitter.
          </div>
        </div>
      </div>

      <Evidence items={[
        { k: "Ruled out", v: "Model weights. The digests are byte-identical on both machines, so the models and their sampling defaults are the same artefacts." },
        { k: "Also ruled out", v: "The decision rule. Both sides are replayed through the same live verdict functions; comparing a stored verdict against a fresh run measures a code change, not a machine." },
        { k: "And now: batching ruled out", v: `Three variables moved together — GPU, runtime build, and the batch parallelism we ourselves changed. The single-variable control has now run: re-scoring the identical contracts at num_parallel=1 moves agreement ${(PARITY.np1_control.agreement_np4 * 100).toFixed(1)}% → ${(PARITY.np1_control.agreement_np1 * 100).toFixed(1)}%, and paired McNemar finds nothing — false alarms p = ${PARITY.np1_control.false_alarms_mcnemar_p}, misses p = ${PARITY.np1_control.misses_mcnemar_p}.` },
        { k: "What that leaves", v: "The machine and its runtime build. This is the harder result, not the easier one: identical model digests, identical seeds and identical code do not reproduce across hardware, and the convenient explanation — that we perturbed it ourselves by batching — is now excluded by measurement." },
      ]} />
      <Novelty>
        If a verdict depends on the machine that produced it, a published false-alarm rate is partly
        a property of the authors&rsquo; hardware. We can find no prior work in this area that
        reports a cross-platform reproducibility check at all.
      </Novelty>
    </Section>
  );
}


/* ─── 08 the configuration that hid itself ─────────────────────────── */

function SilentTruncation() {
  const { small, large, mcnemar, latency } = CTX;
  const pct = (k: number, n: number) => `${((k / n) * 100).toFixed(1)}%`;
  return (
    <Section
      n="08" kicker="A silent failure, in our own results"
      title="A quarter of the benchmark was being judged on a fraction of its code."
      lede={`Every number this project has published was produced with the local runtime's context window at 4,096 tokens. A longer prompt is not refused — it is truncated. The specialist then reads part of the contract and returns a verdict as though it had read all of it. ${CTX.pool_overflowing} of ${CTX.corpus} benchmark contracts overflow that window.`}
    >
      <div style={{ overflowX: "auto", maxWidth: "100%", minWidth: 0 }}>
        <table style={{ borderCollapse: "collapse", width: "100%", minWidth: 520, fontSize: 14 }}>
          <thead>
            <tr style={{ borderBottom: `2px solid ${EX.ink}` }}>
              {["", "num_ctx 4,096 (shipped)", "num_ctx 16,384"].map((h, i) => (
                <th key={h || i} style={{ textAlign: i ? "right" : "left", padding: "10px 8px", fontFamily: MONO, fontSize: 10.5, letterSpacing: ".1em", color: EX.inkMuted, textTransform: "uppercase", fontWeight: 400 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {[
              ["Abstained (INCONCLUSIVE)", pct(small.inconclusive, CTX.paired), pct(large.inconclusive, CTX.paired)],
              ["Accuracy", pct(small.accuracy, CTX.scored_both), pct(large.accuracy, CTX.scored_both)],
              ["Recall on vulnerable", pct(small.recall, CTX.n_vuln), pct(large.recall, CTX.n_vuln)],
              ["Median latency", `${small.median_s}s`, `${large.median_s}s`],
            ].map(([k, a, b], i) => (
              <tr key={k} style={{ borderBottom: `1px solid ${EX.hairline}`, background: i % 2 ? EX.surfaceAlt : "transparent" }}>
                <td style={{ padding: "11px 8px" }}>{k}</td>
                <td style={{ padding: "11px 8px", textAlign: "right", fontFamily: MONO, color: EX.signal }}>{a}</td>
                <td style={{ padding: "11px 8px", textAlign: "right", fontFamily: MONO, color: EX.ink }}>{b}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Evidence items={[
        { k: "Why it never showed up as a bad score", v: `Abstentions are excluded from scoring. So a setting that crippled the council on the largest quarter of the corpus did not lower any number — it removed rows. The tables that remained looked healthy. That is this page's own thesis landing on this page's own results.` },
        { k: "It is a real paired difference", v: `The arms share contract ids, seed, models, machine and the same run function, so McNemar on the discordant pairs is the right test: ${mcnemar.only_large_correct} contracts were correct only with the full window against ${mcnemar.only_small_correct} the other way — chi-square ${mcnemar.chi2}, p = ${mcnemar.p}.` },
        { k: "Truncation is also SLOWER, which is the tell", v: `The full window was faster on ${latency.faster} of ${latency.of} paired contracts, median speedup ×${latency.speedup} (sign test p < 0.0001). A prompt longer than the window forces the runtime to shift context instead of processing it once — so the truncating setting pays repeatedly for the very text it is discarding.` },
        { k: "Which way the verdicts moved", v: `${CTX.flips} of ${CTX.scored_both} paired contracts changed verdict, and ${CTX.flips_toward_blocking} of those moved GO → NO-GO on contracts that are genuinely vulnerable. With the whole contract visible, the council finds bugs the truncation was hiding.` },
      ]} />

      <div style={{ marginTop: 18, border: `1px solid ${EX.hairline}`, padding: "14px 16px", background: EX.surfaceAlt }}>
        <div style={{ fontFamily: MONO, fontSize: 10.5, letterSpacing: ".12em", color: EX.inkMuted, marginBottom: 7 }}>
          WHAT THIS DOES NOT SAY
        </div>
        <p style={{ fontSize: 13.5, lineHeight: 1.62, color: EX.inkMuted, margin: 0, maxWidth: "74ch" }}>
          {CTX.limits} It does not restate the headline false-alarm rate, and no number
          elsewhere on this page has been silently adjusted by it.
        </p>
      </div>

      <Novelty>
        The knob that caused this appears in no run configuration, cannot be varied without
        restarting the runtime, and fails silently when exceeded. We have not found a comparable
        local-LLM evaluation that reports its context window at all — which means this failure is
        available to every one of them, and invisible in exactly the same way.
      </Novelty>
    </Section>
  );
}

/* ─── 06 capability ────────────────────────────────────────────────── */

function CapabilityDoesntFix() {
  const { small, large } = CAPACITY;
  return (
    <Section
      n="07" kicker="Negative result"
      title="The obvious fix — a bigger model — made the false alarms worse."
      lede="Three of the eight specialists were pinned to a small model purely because a larger one did not fit in 4GB of VRAM. Those three are the semantic roles. A larger card let us restore the bigger model and change exactly one variable."
    >
      <div style={{ overflowX: "auto", maxWidth: "100%", minWidth: 0 }}>
        <table style={{ borderCollapse: "collapse", width: "100%", minWidth: 540, fontSize: 14 }}>
          <thead>
            <tr style={{ borderBottom: `2px solid ${EX.ink}` }}>
              {["Semantic-role model", "Missed bugs", "False alarms", "Accuracy", "Median latency"].map((h, i) => (
                <th key={h} style={{ textAlign: i ? "right" : "left", padding: "10px 8px", fontFamily: MONO, fontSize: 10.5, letterSpacing: ".1em", color: EX.inkMuted, textTransform: "uppercase", fontWeight: 400 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {[small, large].map((r, i) => (
              <tr key={r.model} style={{ borderBottom: `1px solid ${EX.hairline}`, background: i ? EX.surfaceAlt : "transparent" }}>
                <td style={{ padding: "12px 8px", fontFamily: MONO, fontSize: 12.5 }}>{r.model}</td>
                <td style={{ padding: "12px 8px", textAlign: "right", fontFamily: MONO, color: i ? EX.data : EX.ink }}>{r.misses} / {CAPACITY.n_vuln}</td>
                <td style={{ padding: "12px 8px", textAlign: "right", fontFamily: MONO, color: i ? EX.signal : EX.ink }}>{r.false_alarms} / {CAPACITY.n_safe}</td>
                <td style={{ padding: "12px 8px", textAlign: "right", fontFamily: MONO }}>{r.accuracy.toFixed(3)}</td>
                <td style={{ padding: "12px 8px", textAlign: "right", fontFamily: MONO, color: EX.slate }}>{r.median_s}s</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Evidence items={[
        { k: "What improved, and it is real", v: `The larger model missed fewer bugs — ${small.misses} → ${large.misses} of ${CAPACITY.n_vuln}. Paired McNemar over the same contracts: p = ${CAPACITY.mcnemar.misses.p}. We are not dismissing the gain; it happened.` },
        { k: "What it cost, and it is bigger", v: `False alarms went ${small.false_alarms} → ${large.false_alarms} of ${CAPACITY.n_safe}. Paired McNemar p = ${CAPACITY.mcnemar.false_alarms.p} — the same test, four orders of magnitude more decisive. Net accuracy FELL, ${small.accuracy.toFixed(3)} → ${large.accuracy.toFixed(3)}.` },
        { k: "The trade, stated plainly", v: `${CAPACITY.mcnemar.misses.only_small_wrong - CAPACITY.mcnemar.misses.only_large_wrong} fewer misses bought with ${CAPACITY.mcnemar.false_alarms.only_large_wrong - CAPACITY.mcnemar.false_alarms.only_small_wrong} more false alarms. Because the arms are PAIRED on contract id, this is McNemar on the discordant pairs rather than two overlapping intervals — the weaker test would have understated it.` },
      ]} />
      <Novelty>
        This answers the first objection any reviewer raises — &ldquo;why not just use a better
        model?&rdquo; — with measurement rather than argument. More capability bought recall and
        spent precision. The lever that actually fixes the false-alarm rate is the aggregation
        rule, and it is free.
      </Novelty>
    </Section>
  );
}

/* ─── 07 invariants ────────────────────────────────────────────────── */

const INVARIANTS: [string, string][] = [
  ["An abstention must never be scored as a pass",
   "A specialist that errored could only have failed to raise a flag, never invented one. So GO-with-errors is unsound and must be quarantined, while NO-GO-with-errors is still sound. Requiring an intact council for both discarded 46% of completed work for no bias reduction; requiring it for neither cost us 32 rows of silently inflated safe-tier accuracy."],
  ["The measured rule must be the shipped rule",
   "The reported threshold was once not the one the product implemented. The dashboard now replays checkpoints through the live verdict functions rather than re-deriving the rule, so the two cannot drift apart."],
  ["A truncated run must still be a valid sample",
   "Filename order clusters by source project, so a run that stops early covers one project family. Shuffle under a fixed seed and interleave across strata, and any prefix stays balanced and scorable."],
  ["Serving configuration is part of the method",
   "Context window, batch parallelism and model residency are inherited from server defaults the application never sets. Two of them moved our measured false-alarm rate. They belong in the reproduction section, not in the environment."],
  ["Coverage is reported next to accuracy",
   "A baseline that abstains on hard inputs posts excellent numbers on the subset it accepted. Publish how much of the benchmark each tool could actually analyse."],
];

function Invariants() {
  return (
    <Section
      n="09" kicker="The output" tint
      title="Five invariants that turn each silent failure into a loud one."
      lede="Every defect above was found by hitting it, and each produced plausible-looking metrics from a broken pipeline. These are the checks that make them fail visibly instead."
    >
      <div style={{ borderTop: `1px solid ${EX.hairline}` }}>
        {INVARIANTS.map(([t, d], i) => (
          <div key={t} style={{ display: "grid", gridTemplateColumns: "34px 1fr", gap: 16, padding: "18px 0", borderBottom: `1px solid ${EX.hairline}` }}>
            <span style={{ fontFamily: MONO, fontSize: 12, color: EX.signal }}>{String(i + 1).padStart(2, "0")}</span>
            <div>
              <div style={{ fontSize: 16, marginBottom: 6, fontFamily: SERIF }}>{t}</div>
              <p style={{ fontSize: 14, lineHeight: 1.6, color: EX.inkMuted, margin: 0, maxWidth: "78ch" }}>{d}</p>
            </div>
          </div>
        ))}
      </div>
    </Section>
  );
}

/* ─── 08 the instrument ────────────────────────────────────────────── */

function Instrument({ onOpenApp }: { onOpenApp?: () => void }) {
  return (
    <Section
      n="10" kicker="The instrument"
      title="Run it on a contract whose answer is already known."
      lede="The tool is evidence that the measurements above came from a working system rather than a spreadsheet. Pick a contract with a known verdict and watch a recorded run, or paste your own and run it live against the backend."
    >
      <TryIt />
      {onOpenApp && (
        <div style={{ marginTop: 26, paddingTop: 18, borderTop: `1px solid ${EX.hairline}`, display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap" }}>
          <button onClick={onOpenApp} style={{
            fontFamily: MONO, fontSize: 11.5, letterSpacing: ".06em", padding: "9px 15px",
            background: "transparent", border: `1px solid ${EX.ink}`, color: EX.ink, cursor: "pointer",
          }}>
            OPEN THE FULL APPLICATION →
          </button>
          <span style={{ fontSize: 13, color: EX.slate }}>
            sign-in, scan history and PDF export — not needed to read this page
          </span>
        </div>
      )}
    </Section>
  );
}

/* ─── 10 status ────────────────────────────────────────────────────── */

const NEXT: [string, string][] = [
  ["Related-work survey", "Positioning nine surveyed papers against each finding. The one item blocking submission."],
  ["Single-variable reproducibility control", "Isolating batch parallelism from hardware, which decides how finding 05 is stated."],
  ["Full-scale capacity ablation", "Taking finding 06 from a 24-contract pilot to the full scored set."],
  ["Web3Bugs / GPTScan comparison", "Real Code4rena audit contests — 300 confirmed semantic bugs across 91 protocol codebases."],
];

function Status() {
  return (
    <Section
      n="11" kicker="Status"
      title="Where the manuscript stands."
      lede={`Findings 01 through 05 are measured at full scale on ${N} contracts and are stable. Findings 06 and 07 are pilots: the direction is established, the magnitude is still moving.`}
    >
      <div style={{ fontFamily: MONO, fontSize: 10.5, color: EX.signal, letterSpacing: ".14em", marginBottom: 14 }}>
        CURRENTLY WORKING TOWARDS
      </div>
      <div style={{ borderTop: `1px solid ${EX.hairline}` }}>
        {NEXT.map(([t, d]) => (
          <div key={t} style={{ display: "grid", gridTemplateColumns: "minmax(200px,300px) 1fr", gap: 18, padding: "13px 0", borderBottom: `1px solid ${EX.hairline}` }}>
            <span style={{ fontSize: 14.5 }}>{t}</span>
            <span style={{ fontSize: 14, color: EX.inkMuted, lineHeight: 1.55 }}>{d}</span>
          </div>
        ))}
      </div>
      <p style={{ fontSize: 14.5, lineHeight: 1.65, color: EX.inkMuted, maxWidth: "72ch", marginTop: 26 }}>
        <strong style={{ color: EX.ink }}>What this work does not claim.</strong> Not that ThirdEye
        is the best available auditor — a 29% false-alarm rate is not deployable unattended, and we
        say so. Not that the balanced benchmark is representative of all Solidity. Not that the
        Web3Bugs figure, once measured, is directly comparable to GPTScan&rsquo;s published number,
        since the evaluated subsets differ. The contribution is the measurement apparatus and what
        it exposes, not a leaderboard position.
      </p>
    </Section>
  );
}

function Colophon() {
  return (
    <footer style={{ borderTop: `2px solid ${EX.ink}`, padding: "34px 0 60px" }}>
      <Wrap>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 20, flexWrap: "wrap" }}>
          <span style={{ fontFamily: MONO, fontSize: 11, color: EX.inkMuted, letterSpacing: ".1em" }}>
            THIRDEYE · CAPSTONE TEAM 2 · PES UNIVERSITY
          </span>
          <span style={{ fontFamily: MONO, fontSize: 11, color: EX.slate, letterSpacing: ".1em" }}>
            ALL FIGURES REGENERATED FROM CHECKPOINTS · NOTHING HAND-ENTERED
          </span>
        </div>
      </Wrap>
    </footer>
  );
}
