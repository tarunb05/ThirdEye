// ─────────────────────────────────────────────────────────────────────────────
// ThirdEye site design tokens — "instrument readout".
//
// This is the exhibit's own palette (frontend/src/lib/exhibit-theme.ts, as of
// 504d975), restored. It was built for exactly this audience and says so: a
// panel review runs on a projector in a lit room, where dark themes wash out
// and low-contrast text is unreadable from the back row. Every AI demo ships
// dark violet; bone paper reads as a different kind of artefact.
//
// ONE HUE, AND IT MEANS SOMETHING. The signal is vermillion #B4351F and it is
// the only chromatic colour in the chrome. Everything structural is bone, ink
// and a hairline. Hue is therefore information rather than decoration, which is
// why the page can carry seven pages of figures without looking like a
// dashboard.
//
// NO BLUE. The exhibit paired vermillion with a validated data blue (#1F6FB2)
// for series 1 and used a blue-grey #3E5772 for low severity. Both are gone:
// series 2 is the warm grey #7C7466 and low severity is taupe #726B5E. The
// pair still separates by lightness (4.24:1 against 5.55:1) rather than by hue
// alone, which is the property that mattered about the validated pair.
//
// COLOURS ARE MEASURED, NOT EYEBALLED. Against the bone surface:
//   ink 16.79 · inkMid 7.97 · inkDim 5.18 · signal 5.55 · go 5.87 · nogo 7.98
//   severity 7.98 / 6.28 / 6.20 / 4.84
// hairline is 1.37:1 by intent — it is a rule, never information. These were
// recomputed rather than copied: the exhibit's header claimed 16.8 / 5.2 / 5.5
// and all three check out.
//
// The exhibit had no green, because the old page had no GO verdict. #2F6B3A is
// the one addition — warm-leaning so it sits with vermillion rather than
// fighting it.
// ─────────────────────────────────────────────────────────────────────────────

export const C = {
  // ground — the exhibit's bone paper, restored verbatim
  bg: "#F7F5F0",      // surface
  bgAlt: "#F1EEE6",   // surfaceAlt, recessed panel
  panel: "#FFFFFF",   // surfaceLift, raised card
  panelHi: "#F1EEE6",
  line: "#D8D3C7",    // hairline — 1.37:1 BY INTENT, it is a rule, never information
  lineHi: "#C7C0B1",  // tick, calibration marks

  // ink — three steps, measured on bone: 16.79 / 7.97 / 5.18
  ink: "#16150F",
  inkMid: "#4F4B42",
  inkDim: "#6B675C",  // the exhibit's inkMuted

  // THE SIGNAL — vermillion. One hue, and it means "look here".
  accent: "#B4351F",
  accentDim: "#7C7466",            // de-emphasised mark / second series, warm grey
  accentGhost: "rgba(180,53,31,0.09)",

  // semantic, verdicts ONLY. Never colour alone: every verdict ships with its
  // word and a mark, so these survive colourblindness and a greyscale print.
  go: "#2F6B3A",
  goGhost: "rgba(47,107,58,0.10)",
  nogo: "#8E2417",                 // deeper than the signal, so chrome and alarm stay apart
  nogoGhost: "rgba(142,36,23,0.09)",
  inconc: "#726B5E",
  inconcGhost: "rgba(114,107,94,0.10)",

  // severity ramp — the exhibit's own steps, each re-tuned for bone and each
  // clearing 4.5:1 on it. `low` was #3E5772, a blue-grey; it is warm taupe now
  // so no blue survives anywhere in the palette.
  sev: {
    critical: "#8E2417",
    high: "#8A4A12",
    medium: "#6B5A1E",
    low: "#726B5E",
  } as Record<string, string>,
} as const;

export const F = {
  sans: "'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif",
  mono: "'JetBrains Mono', ui-monospace, 'SF Mono', Menlo, monospace",
  serif: "'Source Serif 4', 'Iowan Old Style', Charter, Georgia, serif",
} as const;

export function sevColor(severity?: string | null): string {
  return C.sev[(severity || "low").toLowerCase()] || C.sev.low;
}

export function verdictColor(v?: string | null) {
  if (v === "GO") return { fg: C.go, bg: C.goGhost };
  if (v === "NO-GO") return { fg: C.nogo, bg: C.nogoGhost };
  return { fg: C.inconc, bg: C.inconcGhost };
}

// Shared inline-style fragments. Inline styles rather than utility classes so
// every page is readable on its own without cross-referencing a config.
export const S = {
  page: {
    maxWidth: 1120,
    margin: "0 auto",
    padding: "0 28px 96px",
  } as React.CSSProperties,

  // Headings take the serif. The site is a lab report: prose and headings
  // carry the argument, sans is reserved for chrome, mono for measurements.
  h1: {
    fontFamily: F.serif,
    fontSize: "clamp(30px, 5.4vw, 40px)",
    lineHeight: 1.1,
    fontWeight: 600,
    letterSpacing: "-0.015em",
    color: C.ink,
    textWrap: "balance",
    margin: "0 0 14px",
    fontOpticalSizing: "auto",
  } as React.CSSProperties,

  h2: {
    fontFamily: F.serif,
    fontSize: "clamp(20px, 3.2vw, 24px)",
    fontWeight: 600,
    letterSpacing: "-0.01em",
    color: C.ink,
    margin: "44px 0 14px",
    fontOpticalSizing: "auto",
  } as React.CSSProperties,

  h3: {
    fontFamily: F.sans,
    fontSize: 15,
    fontWeight: 600,
    letterSpacing: "-0.005em",
    color: C.ink,
    margin: "0 0 8px",
  } as React.CSSProperties,

  p: {
    fontFamily: F.sans,
    fontSize: 15,
    lineHeight: 1.65,
    color: C.inkMid,
    maxWidth: "68ch",
    margin: "0 0 14px",
  } as React.CSSProperties,

  eyebrow: {
    fontFamily: F.mono,
    fontSize: 11,
    letterSpacing: "0.13em",
    textTransform: "uppercase",
    color: C.accent,
    margin: "0 0 12px",
  } as React.CSSProperties,

  // A card is a white sheet on bone. One hairline plus the surface step is
  // enough; a shadow on top of both would read as a dark-theme habit.
  card: {
    background: C.panel,
    border: `1px solid ${C.line}`,
    borderRadius: 10,
    padding: 20,
  } as React.CSSProperties,

  code: {
    fontFamily: F.mono,
    fontSize: 12.5,
    lineHeight: 1.6,
    color: C.ink,
    background: C.bgAlt,
    border: `1px solid ${C.line}`,
    borderRadius: 8,
    padding: 14,
    overflowX: "auto",
  } as React.CSSProperties,

  tableWrap: {
    overflowX: "auto",
    border: `1px solid ${C.line}`,
    borderRadius: 10,
    background: C.panel,
  } as React.CSSProperties,

  table: {
    width: "100%",
    borderCollapse: "collapse",
    fontFamily: F.sans,
    fontSize: 13.5,
    fontVariantNumeric: "tabular-nums",
  } as React.CSSProperties,

  th: {
    textAlign: "left",
    padding: "11px 14px",
    color: C.inkDim,
    fontWeight: 600,
    fontSize: 11.5,
    letterSpacing: "0.07em",
    textTransform: "uppercase",
    borderBottom: `1px solid ${C.line}`,
    whiteSpace: "nowrap",
    background: C.panelHi,
  } as React.CSSProperties,

  td: {
    padding: "11px 14px",
    color: C.inkMid,
    borderBottom: `1px solid ${C.line}`,
    verticalAlign: "top",
  } as React.CSSProperties,
};
