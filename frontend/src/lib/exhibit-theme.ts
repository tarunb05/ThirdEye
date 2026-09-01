/** ThirdEye exhibit design tokens — "instrument readout".
 *
 * THE ORGANISING IDEA: uncertainty is the visual language. This paper's whole
 * argument is that the field reports rates without saying how sure it is, so
 * every rate on this page is drawn as a point estimate ON a 95% interval, on a
 * shared 0–100% scale. That single decision gives the page an identity nothing
 * else would have — the design and the thesis are the same statement.
 *
 * LIGHT, deliberately. Every AI demo ships dark violet; this reads as a
 * different kind of artefact. More practically, a panel review runs on a
 * projector in a lit room, where dark themes wash out and low-contrast text is
 * unreadable from the back row.
 *
 * COLOUR IS VALIDATED, NOT EYEBALLED. The two-series categorical pair was run
 * through the palette validator (light mode, surface #F7F5F0):
 *   lightness band PASS · chroma floor PASS · contrast PASS
 *   CVD separation ΔE 22.2 (protan) / 30.4 (tritan) · normal vision ΔE 28.2
 * The previous data blue (#2C4A6B) FAILED two checks — outside the lightness
 * band and below the chroma floor, i.e. it read as grey rather than as a hue.
 *
 * TEXT WEARS TEXT TOKENS. `data` is a MARK colour only; it is not rated for
 * body text on this surface. Ink, inkMuted and slate carry all type. A coloured
 * mark beside a label carries identity — the label itself stays in ink.
 *
 * WCAG against the bone surface, computed:
 *   ink 16.8:1 · inkMuted 5.2:1 · slate 5.0:1 · signal 5.5:1
 * hairline is 1.37:1 by intent — it is a rule, never information.
 *
 * Status is never colour alone: BLOCKED/CLEARED always ship with a word and a
 * mark, so the page survives colourblindness and greyscale printing.
 */
export const EX = {
  surface: "#F7F5F0",      // bone paper
  surfaceAlt: "#F1EEE6",   // recessed panel
  surfaceLift: "#FFFFFF",  // raised card
  ink: "#16150F",          // body text
  inkMuted: "#6B675C",     // secondary text
  hairline: "#D8D3C7",     // rules (decorative)
  tick: "#C7C0B1",         // calibration marks
  signal: "#B4351F",       // vermillion — the alarm / series 2
  signalWash: "#F6E7E2",   // vermillion at low weight
  data: "#1F6FB2",         // MARKS ONLY — series 1, validated
  dataWash: "#E2EDF6",
  slate: "#5E6B78",        // de-emphasised text AND marks
} as const;

/** Monospace for every number. Data should look measured, not typeset. */
export const MONO =
  "'Berkeley Mono','JetBrains Mono','IBM Plex Mono',ui-monospace,'SF Mono',Menlo,Consolas,monospace";
/** A serif for prose gives the page a report register rather than SaaS. */
export const SERIF =
  "'Source Serif 4','Iowan Old Style','Charter',Georgia,'Times New Roman',serif";
export const SANS =
  "'Inter','Helvetica Neue',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif";

/** One type scale, so sizes are chosen from a set rather than invented. */
export const T = {
  display: 52,
  h2: 34,
  lede: 18.5,
  body: 14.5,
  small: 13,
  micro: 11,
  stat: 38,
} as const;

/** Motion tokens.
 *
 * Motion here must REVEAL STRUCTURE, never decorate: an interval drawing out to
 * its true width, a bar growing to its measured value. A panel reviewing
 * research reads decorative animation as compensation, so there is none.
 * Durations are short enough to feel snappy rather than staged.
 */
export const M = {
  fast: 180,
  base: 260,
  slow: 420,
  ease: "cubic-bezier(0.22, 0.61, 0.36, 1)",
} as const;
