/** Narrative chart primitives for the Benchmarks story.
 *
 * Re-tuned for the BONE surface (#F7F5F0) when the app moved off the dark theme.
 * The previous steps were selected against a dark plum background and inverted
 * badly here — chart ink was near-white (#e2e8f0), i.e. invisible on paper.
 *
 * Contrast against #F7F5F0, computed: ink 16.8:1, inkDim 5.2:1, inkFaint 5.0:1,
 * accent 8.4:1. Status meaning is never carried by hue alone — an earlier
 * emerald/rose "good vs bad" pair failed at deutan ΔE 4.6, the classic red/green
 * trap — so labels and position carry it and only one hue encodes state.
 *
 * Forms follow the data's job: magnitude → sequential single hue; before/after
 * → one hue in two shades; "one series is the point" → emphasis (accent + gray).
 * No dual axes anywhere.
 */

export const VIZ = {
  accent: "#1F6FB2",       // series 1 / magnitude (ink-blue)
  accent2: "#B4351F",      // series 2 — the signal vermillion
  muted: "#A8A294",        // de-emphasised marks
  grid: "rgba(22,21,15,0.10)",
  ink: "#16150F",
  inkDim: "#6B675C",
  inkFaint: "#5E6B78",
} as const;

const card =
  "rounded-xl border border-[#D8D3C7] bg-white px-5 py-5";

export function ChartFrame({
  title, subtitle, children, footnote,
}: {
  title: string; subtitle?: string; children: React.ReactNode; footnote?: string;
}) {
  return (
    <div className={card}>
      <div className="text-sm font-semibold text-[#16150F]">{title}</div>
      {subtitle && (
        <p className="mt-1 text-xs text-[#6B675C] leading-relaxed">{subtitle}</p>
      )}
      <div className="mt-4">{children}</div>
      {footnote && (
        <p className="mt-3 text-[11px] text-[#5E6B78] leading-relaxed">{footnote}</p>
      )}
    </div>
  );
}

/** One number that carries a section. Not a one-bar bar chart. */
export function HeroStat({
  value, label, sub, tone = "accent",
}: { value: string; label: string; sub?: string; tone?: "accent" | "warn" | "plain" }) {
  const color =
    tone === "accent" ? VIZ.accent : tone === "warn" ? VIZ.accent2 : VIZ.ink;
  return (
    <div className={card}>
      <div className="text-[11px] uppercase tracking-[0.14em] text-[#6B675C]">{label}</div>
      <div className="mt-2 font-mono leading-none" style={{ fontSize: 48, color }}>
        {value}
      </div>
      {sub && <div className="mt-2 text-xs text-[#6B675C] leading-relaxed">{sub}</div>}
    </div>
  );
}

/** Horizontal magnitude bars, sequential single hue, every bar direct-labelled.
 *  `highlight` promotes one row to the accent and greys the rest (emphasis form). */
export function BarList({
  rows, max = 1, fmt = (v: number) => `${(v * 100).toFixed(0)}%`, highlight,
}: {
  rows: { label: string; value: number; note?: string }[];
  max?: number;
  fmt?: (v: number) => string;
  highlight?: (r: { label: string; value: number }) => boolean;
}) {
  const anyHighlight = typeof highlight === "function";
  return (
    <div className="space-y-2.5">
      {rows.map((r) => {
        const on = anyHighlight ? highlight!(r) : true;
        const pct = Math.max(0, Math.min(1, r.value / max)) * 100;
        return (
          <div key={r.label} className="flex items-center gap-3">
            <div className="w-40 shrink-0 text-xs text-[#3A372E] text-right">{r.label}</div>
            <div className="flex-1 h-5 rounded-[3px] relative" style={{ background: "rgba(22,21,15,0.06)" }}>
              <div
                className="h-full rounded-[3px]"
                style={{ width: `${pct}%`, background: on ? VIZ.accent : VIZ.muted }}
              />
            </div>
            <div className="w-24 shrink-0 font-mono text-xs tabular-nums" style={{ color: VIZ.ink }}>
              {fmt(r.value)}
              {r.note && <span className="ml-1 text-[10px]" style={{ color: VIZ.inkFaint }}>{r.note}</span>}
            </div>
          </div>
        );
      })}
    </div>
  );
}

/** Column chart for the compounding curve. Single hue by magnitude (the whole
 *  point is that taller = worse as k grows), n labelled under each column so a
 *  thin cell can't masquerade as a solid finding. */
export function ColumnTrend({
  rows, yMax = 1,
}: { rows: { x: number | string; y: number; n?: number }[]; yMax?: number }) {
  const W = 520, H = 190, padL = 34, padB = 34, padT = 12;
  const plotW = W - padL - 8, plotH = H - padB - padT;
  const bw = Math.min(46, (plotW / rows.length) * 0.62);
  const step = plotW / rows.length;
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((t) => t * yMax);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" role="img"
         aria-label="False-alarm rate rising with the number of specialists consulted">
      {ticks.map((t) => {
        const y = padT + plotH - (t / yMax) * plotH;
        return (
          <g key={t}>
            <line x1={padL} x2={W - 8} y1={y} y2={y} stroke={VIZ.grid} strokeWidth={1} />
            <text x={padL - 8} y={y + 3} textAnchor="end" fontSize={9} fill={VIZ.inkFaint}>
              {Math.round((t / yMax) * 100)}%
            </text>
          </g>
        );
      })}
      {rows.map((r, i) => {
        const h = (r.y / yMax) * plotH;
        const x = padL + i * step + (step - bw) / 2;
        const y = padT + plotH - h;
        return (
          <g key={i}>
            {/* 4px rounded data-end, anchored to the baseline */}
            <path
              d={`M${x},${padT + plotH} L${x},${y + 4} Q${x},${y} ${x + 4},${y} L${x + bw - 4},${y} Q${x + bw},${y} ${x + bw},${y + 4} L${x + bw},${padT + plotH} Z`}
              fill={VIZ.accent}
            />
            <text x={x + bw / 2} y={y - 5} textAnchor="middle" fontSize={10}
                  fill={VIZ.ink} className="font-mono">
              {Math.round(r.y * 100)}%
            </text>
            <text x={x + bw / 2} y={padT + plotH + 14} textAnchor="middle" fontSize={10} fill={VIZ.inkDim}>
              {r.x}
            </text>
            {r.n != null && (
              <text x={x + bw / 2} y={padT + plotH + 26} textAnchor="middle" fontSize={8} fill={VIZ.inkFaint}>
                n={r.n}
              </text>
            )}
          </g>
        );
      })}
      <line x1={padL} x2={W - 8} y1={padT + plotH} y2={padT + plotH} stroke={VIZ.grid} strokeWidth={1} />
    </svg>
  );
}

/** Before → after per metric: one hue, two shades, connected. The dumbbell is
 *  the form for "same thing measured twice" — a grouped bar hides the delta,
 *  which IS the message here. */
export function Dumbbell({
  rows, beforeLabel, afterLabel,
}: {
  rows: { label: string; before: number; after: number; better: "down" | "up" }[];
  beforeLabel: string; afterLabel: string;
}) {
  const W = 520, rowH = 44, padL = 132, padR = 58;
  const H = rows.length * rowH + 26;
  const plotW = W - padL - padR;
  const x = (v: number) => padL + Math.max(0, Math.min(1, v)) * plotW;
  return (
    <div>
      {/* Legend — mandatory at 2 series, so identity is never colour-alone */}
      <div className="flex items-center gap-4 mb-2 text-[11px]" style={{ color: VIZ.inkDim }}>
        <span className="inline-flex items-center gap-1.5">
          <span style={{ width: 9, height: 9, borderRadius: 9, background: VIZ.muted, display: "inline-block" }} />
          {beforeLabel}
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span style={{ width: 9, height: 9, borderRadius: 9, background: VIZ.accent, display: "inline-block" }} />
          {afterLabel}
        </span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" role="img"
           aria-label={`${beforeLabel} versus ${afterLabel} per metric`}>
        {rows.map((r, i) => {
          const y = 18 + i * rowH;
          const improved = r.better === "down" ? r.after < r.before : r.after > r.before;
          return (
            <g key={r.label}>
              <text x={padL - 12} y={y + 4} textAnchor="end" fontSize={11} fill={VIZ.ink}>{r.label}</text>
              <line x1={padL} x2={padL + plotW} y1={y} y2={y} stroke={VIZ.grid} strokeWidth={1} />
              <line x1={x(r.before)} x2={x(r.after)} y1={y} y2={y}
                    stroke={improved ? VIZ.accent : VIZ.muted} strokeWidth={2} opacity={0.55} />
              {/* 2px surface ring so overlapping marks stay separable */}
              <circle cx={x(r.before)} cy={y} r={5.5} fill={VIZ.muted} stroke="#F7F5F0" strokeWidth={2} />
              <circle cx={x(r.after)} cy={y} r={5.5} fill={VIZ.accent} stroke="#F7F5F0" strokeWidth={2} />
              <text x={padL + plotW + 10} y={y + 4} fontSize={11} className="font-mono" fill={VIZ.ink}>
                {Math.round(r.before * 100)}→{Math.round(r.after * 100)}%
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

/** Two proportion bars for coverage — how much of the benchmark each tool could
 *  actually analyse. Part-to-whole, so a filled/unfilled split, not a pie. */
export function CoverageSplit({
  rows,
}: { rows: { label: string; scored: number; total: number; note?: string }[] }) {
  return (
    <div className="space-y-4">
      {rows.map((r, i) => {
        const pct = r.total ? r.scored / r.total : 0;
        return (
          <div key={r.label}>
            <div className="flex items-baseline justify-between mb-1.5">
              <span className="text-xs text-[#6B675C]">{r.label}</span>
              <span className="font-mono text-xs" style={{ color: VIZ.ink }}>
                {r.scored}/{r.total} · {Math.round(pct * 100)}%
              </span>
            </div>
            <div className="h-6 rounded-[3px] overflow-hidden flex" style={{ background: "rgba(22,21,15,0.06)" }}>
              <div style={{ width: `${pct * 100}%`, background: i === 0 ? VIZ.accent : VIZ.accent2 }} />
              {/* 2px surface gap between adjacent fills */}
              <div style={{ width: 2, background: "#FFFFFF" }} />
            </div>
            {r.note && <div className="mt-1 text-[11px]" style={{ color: VIZ.inkFaint }}>{r.note}</div>}
          </div>
        );
      })}
    </div>
  );
}
