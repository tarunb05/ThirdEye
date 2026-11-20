import React, { useEffect, useRef } from "react";
import { C, F, S, verdictColor } from "./design";
import { CountUp, Reveal, prefersReducedMotion } from "./motion";

/* ── primitives shared by every page ─────────────────────────────────────── */

export function Section({
  eyebrow,
  title,
  children,
  id,
}: {
  eyebrow?: string;
  title?: string;
  children: React.ReactNode;
  id?: string;
}) {
  return (
    <section id={id} style={{ marginTop: 56 }}>
      <Reveal>
        {eyebrow && <div style={S.eyebrow}>{eyebrow}</div>}
        {title && <h2 style={{ ...S.h2, marginTop: 0 }}>{title}</h2>}
        {children}
      </Reveal>
    </section>
  );
}

export function P({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return <p style={{ ...S.p, ...style }}>{children}</p>;
}

export function Card({
  children,
  style,
  flat,
}: {
  children: React.ReactNode;
  style?: React.CSSProperties;
  /** Opt out of the hover lift for cards that are not themselves a unit of
   *  content (chart frames, wrappers around a table). */
  flat?: boolean;
}) {
  return (
    <div className={flat ? undefined : "te-card"} style={{ ...S.card, ...style }}>
      {children}
    </div>
  );
}

export function Grid({
  cols = 3,
  gap = 16,
  children,
  min = 240,
  stagger,
}: {
  cols?: number;
  gap?: number;
  min?: number;
  children: React.ReactNode;
  /** Reveal the cells in sequence instead of as one block. Worth it for a row
   *  of headline stats; noise on a grid of twelve. */
  stagger?: boolean;
}) {
  const inner = (
    <div
      style={{
        display: "grid",
        gap,
        gridTemplateColumns: `repeat(auto-fit, minmax(${min}px, 1fr))`,
        // cols is advisory: auto-fit keeps it responsive without media queries.
        maxWidth: cols <= 2 ? 820 : undefined,
      }}
    >
      {children}
    </div>
  );
  // The Reveal must BE the grid for stagger to see the cells as its direct
  // children, so the grid styles move onto it rather than wrapping it.
  if (!stagger) return inner;
  return (
    <Reveal
      stagger={0.085}
      style={{
        display: "grid",
        gap,
        gridTemplateColumns: `repeat(auto-fit, minmax(${min}px, 1fr))`,
        maxWidth: cols <= 2 ? 820 : undefined,
      }}
    >
      {children}
    </Reveal>
  );
}

export function Stat({
  value,
  label,
  sub,
  tone,
}: {
  value: string;
  label: string;
  sub?: string;
  tone?: string;
}) {
  return (
    <Card>
      <div
        style={{
          fontFamily: F.mono,
          fontSize: 30,
          fontWeight: 500,
          color: tone || C.accent,
          letterSpacing: "-0.02em",
          fontVariantNumeric: "tabular-nums",
        }}
      >
        <CountUp value={value} />
      </div>
      <div style={{ ...S.h3, marginTop: 8, marginBottom: 4 }}>{label}</div>
      {sub && (
        <div style={{ fontFamily: F.sans, fontSize: 13, lineHeight: 1.55, color: C.inkDim }}>
          {sub}
        </div>
      )}
    </Card>
  );
}

export function Badge({
  children,
  fg,
  bg,
}: {
  children: React.ReactNode;
  fg?: string;
  bg?: string;
}) {
  return (
    <span
      style={{
        display: "inline-block",
        fontFamily: F.mono,
        fontSize: 11,
        letterSpacing: "0.06em",
        padding: "3px 8px",
        borderRadius: 5,
        color: fg || C.accent,
        background: bg || C.accentGhost,
        whiteSpace: "nowrap",
      }}
    >
      {children}
    </span>
  );
}

export function VerdictPill({ verdict }: { verdict?: string | null }) {
  const { fg, bg } = verdictColor(verdict);
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 7,
        fontFamily: F.mono,
        fontSize: 13,
        fontWeight: 500,
        padding: "5px 12px",
        borderRadius: 6,
        color: fg,
        background: bg,
        border: `1px solid ${fg}44`,
      }}
    >
      <span style={{ width: 7, height: 7, borderRadius: 99, background: fg }} />
      {verdict || "—"}
    </span>
  );
}

/* ── a table that never lies about alignment ─────────────────────────────── */

export function Table({
  head,
  rows,
  emphasiseRow,
}: {
  head: string[];
  rows: React.ReactNode[][];
  emphasiseRow?: number;
}) {
  return (
    <div style={S.tableWrap}>
      <table style={S.table}>
        <thead>
          <tr>
            {head.map((h, i) => (
              <th key={i} style={{ ...S.th, textAlign: i === 0 ? "left" : "right" }}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr
              key={i}
              style={i === emphasiseRow ? { background: C.accentGhost } : undefined}
            >
              {r.map((cell, j) => (
                <td
                  key={j}
                  style={{
                    ...S.td,
                    textAlign: j === 0 ? "left" : "right",
                    color: i === emphasiseRow ? C.ink : S.td.color,
                    fontWeight: i === emphasiseRow ? 600 : 400,
                    fontFamily: j === 0 ? F.sans : F.mono,
                  }}
                >
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ── a callout for the things we are NOT claiming ────────────────────────── */

export function Caveat({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div
      style={{
        borderLeft: `2px solid ${C.lineHi}`,
        paddingLeft: 16,
        margin: "22px 0",
      }}
    >
      <div
        style={{
          fontFamily: F.mono,
          fontSize: 11,
          letterSpacing: "0.1em",
          textTransform: "uppercase",
          color: C.inkDim,
          marginBottom: 7,
        }}
      >
        {title}
      </div>
      <div style={{ ...S.p, margin: 0, fontSize: 14.5, color: C.inkMid }}>{children}</div>
    </div>
  );
}

/* ── horizontal bar chart, used for the ensemble-size result ─────────────── */

export function BarPair({
  rows,
  maxValue = 100,
  labelA,
  labelB,
}: {
  rows: { label: string; a: number | null; b: number | null; nA?: number; nB?: number }[];
  maxValue?: number;
  labelA: string;
  labelB: string;
}) {
  return (
    <div>
      <div style={{ display: "flex", gap: 18, marginBottom: 14 }}>
        <LegendKey color={C.accent} label={labelA} />
        <LegendKey color={C.accentDim} label={labelB} />
      </div>
      <div style={{ display: "grid", gap: 10 }}>
        {rows.map((r) => (
          <div key={r.label} style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div
              style={{
                fontFamily: F.mono,
                fontSize: 12,
                color: C.inkDim,
                width: 46,
                textAlign: "right",
                flexShrink: 0,
              }}
            >
              {r.label}
            </div>
            <div style={{ flex: 1, display: "grid", gap: 3 }}>
              <Bar value={r.a} max={maxValue} color={C.accent} />
              <Bar value={r.b} max={maxValue} color={C.accentDim} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function Bar({ value, max, color }: { value: number | null; max: number; color: string }) {
  const fill = useRef<HTMLDivElement>(null);
  const num = useRef<HTMLSpanElement>(null);

  /* Bars grow from the axis and the label counts with them, so the monotone
   * climb in FINDING 0 is something you watch rather than read off six static
   * rows. scaleX, not width: compositor-only, and there are twelve on screen.
   *
   * Same guarantee as CountUp -- the final state is forced by a timer, because
   * a bar left at scaleX(0) with the label reading "0.0%" would not be a
   * missing animation, it would be a wrong number on a results page. */
  useEffect(() => {
    const f = fill.current;
    if (!f || value == null || prefersReducedMotion()) return;

    let raf = 0;
    let safety = 0;
    let done = false;
    const DUR = 950;

    const finish = () => {
      if (done) return;
      done = true;
      cancelAnimationFrame(raf);
      clearTimeout(safety);
      f.style.transform = "scaleX(1)";
      if (num.current) num.current.textContent = `${value.toFixed(1)}%`;
    };

    const run = () => {
      const t0 = performance.now();
      const step = (now: number) => {
        const t = Math.min(1, (now - t0) / DUR);
        const e = 1 - Math.pow(1 - t, 3);
        f.style.transform = `scaleX(${e})`;
        if (num.current) num.current.textContent = `${(value * e).toFixed(1)}%`;
        if (t < 1) raf = requestAnimationFrame(step);
        else finish();
      };
      f.style.transform = "scaleX(0)";
      raf = requestAnimationFrame(step);
      safety = window.setTimeout(finish, DUR + 400);
    };

    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((x) => x.isIntersecting)) {
          io.disconnect();
          run();
        }
      },
      { threshold: 0.25 }
    );
    io.observe(f);

    return () => {
      io.disconnect();
      cancelAnimationFrame(raf);
      clearTimeout(safety);
      f.style.transform = "";
      if (num.current) num.current.textContent = `${value.toFixed(1)}%`;
    };
  }, [value, max]);

  if (value == null) {
    return (
      <div style={{ height: 13, display: "flex", alignItems: "center" }}>
        <span style={{ fontFamily: F.mono, fontSize: 10.5, color: C.inkDim }}>
          not measured
        </span>
      </div>
    );
  }
  return (
    <div style={{ height: 13, display: "flex", alignItems: "center", gap: 8 }}>
      <div
        style={{
          height: 11,
          width: `${Math.max(1, (value / max) * 100)}%`,
          borderRadius: 2,
          minWidth: 2,
          overflow: "hidden",
        }}
      >
        <div
          ref={fill}
          style={{
            height: "100%",
            width: "100%",
            background: color,
            borderRadius: 2,
            transformOrigin: "0 50%",
            willChange: "transform",
          }}
        />
      </div>
      <span
        ref={num}
        style={{
          fontFamily: F.mono,
          fontSize: 11,
          color: C.inkMid,
          fontVariantNumeric: "tabular-nums",
        }}
      >
        {value.toFixed(1)}%
      </span>
    </div>
  );
}

function LegendKey({ color, label }: { color: string; label: string }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 7 }}>
      <span style={{ width: 11, height: 11, background: color, borderRadius: 2 }} />
      <span style={{ fontFamily: F.sans, fontSize: 12.5, color: C.inkMid }}>{label}</span>
    </span>
  );
}
