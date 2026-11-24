// ─────────────────────────────────────────────────────────────────────────────
// The hero instrument.
//
// This is not decoration, and that was the whole design constraint: the hero of
// a research site should be the result, not a logo with a glow on it. So the
// iris IS the council — eight arcs, one per specialist — and the animation is
// the project's largest finding (FINDING 0) played back from its measured
// numbers.
//
// As k rises, arcs light up and the false-alarm rate climbs 12.2% -> 90.1%.
// Every frame is a real row from ENSEMBLE_SIZE.seed0, including the n for that
// cell, so there is no invented curve anywhere in it. A viewer who watches the
// loop once has read the finding.
//
// The arcs light in ROUTER ORDER, not clockwise: business_logic is always
// selected (it is why k is never 0), so it lights first, every cycle. That is
// the specialist the findings register calls a coin flip, and the visual should
// not imply the council is a neutral ring of equals when it is not.
// ─────────────────────────────────────────────────────────────────────────────

import { useEffect, useRef, useState } from "react";
import { C, F } from "./design";
import { ENSEMBLE_SIZE, SPECIALISTS } from "./facts";
import { gsap, prefersReducedMotion } from "./motion";

const K = ENSEMBLE_SIZE.seed0; // [{k, fpr, n}] for k = 1..6

/* Router order. business_logic first because the static router always selects
 * it; the rest in the order the pipeline fires them. */
const ORDER = [
  "business_logic",
  "arithmetic",
  "access_control",
  "dos_gas",
  "reentrancy",
  "oracle_price_manipulation",
  "proxy_upgradeability",
  "flashloan_mev",
];
const ROLES = ORDER.map((r) => SPECIALISTS.find((s) => s.role === r)!).filter(Boolean);

/** Polar arc path for segment i of n around radius r. */
function arc(i: number, n: number, r: number, gapDeg: number) {
  const step = 360 / n;
  const a0 = (i * step - 90 + gapDeg / 2) * (Math.PI / 180);
  const a1 = ((i + 1) * step - 90 - gapDeg / 2) * (Math.PI / 180);
  const x0 = 110 + r * Math.cos(a0);
  const y0 = 110 + r * Math.sin(a0);
  const x1 = 110 + r * Math.cos(a1);
  const y1 = 110 + r * Math.sin(a1);
  return `M ${x0.toFixed(2)} ${y0.toFixed(2)} A ${r} ${r} 0 0 1 ${x1.toFixed(2)} ${y1.toFixed(2)}`;
}

export function CouncilEye() {
  const reduced = prefersReducedMotion();
  // Reduced motion gets the median routing (k = 3) as a still frame: a real
  // row, not the most alarming one.
  const [idx, setIdx] = useState(reduced ? 2 : 0);
  const [live, setLive] = useState(!reduced);
  const wrap = useRef<HTMLDivElement>(null);
  const fprRef = useRef<HTMLSpanElement>(null);

  /* Pause while off screen. An animation nobody is looking at should not hold
   * the main thread, and this one sits above a long document. */
  useEffect(() => {
    const el = wrap.current;
    if (!el || reduced) return;
    const io = new IntersectionObserver(
      ([e]) => setLive(e.isIntersecting),
      { threshold: 0.15 }
    );
    io.observe(el);
    return () => io.disconnect();
  }, [reduced]);

  useEffect(() => {
    if (!live) return;
    const t = setInterval(() => setIdx((i) => (i + 1) % K.length), 1750);
    return () => clearInterval(t);
  }, [live]);

  /* Tween the readout rather than snapping it, so the number reads as a
   * measurement moving along a curve instead of six unrelated values. */
  const row = K[idx];
  useEffect(() => {
    const el = fprRef.current;
    if (!el) return;
    if (reduced) {
      el.textContent = row.fpr.toFixed(1);
      return;
    }
    const from = { v: parseFloat(el.textContent || "0") || 0 };
    const tw = gsap.to(from, {
      v: row.fpr,
      duration: 0.72,
      ease: "power2.out",
      onUpdate: () => {
        el.textContent = from.v.toFixed(1);
      },
    });
    return () => {
      tw.kill();
    };
  }, [row.fpr, reduced]);

  const lit = row.k;

  return (
    <div ref={wrap} className="te-eye">
      <svg viewBox="0 0 220 220" width="220" height="220" role="img"
        style={{ maxWidth: "100%", height: "auto" }}
        aria-label={`Council diagram: ${lit} of 8 specialists selected, measured false-alarm rate ${row.fpr.toFixed(1)} percent`}>
        {/* the lens — the ThirdEye mark, echoed from the nav */}
        <path
          d="M12 110s34-62 98-62 98 62 98 62-34 62-98 62-98-62-98-62Z"
          fill="none"
          stroke={C.line}
          strokeWidth="1.5"
        />

        {/* the eight specialists */}
        {ROLES.map((s, i) => {
          const on = i < lit;
          return (
            <path
              key={s.role}
              d={arc(i, 8, 62, 9)}
              fill="none"
              stroke={on ? C.accent : C.lineHi}
              strokeWidth={on ? 7 : 3}
              strokeLinecap="round"
              opacity={on ? 1 : 0.35}
              style={{
                transition: reduced
                  ? "none"
                  : "stroke 420ms ease, stroke-width 420ms ease, opacity 420ms ease",
              }}
            />
          );
        })}

        {/* iris + pupil. The pupil widens with k — the eye "opens" as more of
            the council fires, which is also when it starts crying wolf. */}
        <circle cx="110" cy="110" r="40" fill={C.panel} stroke={C.line} strokeWidth="1" />
        <circle
          cx="110"
          cy="110"
          r={13 + lit * 1.9}
          fill={C.accent}
          opacity={0.1}
          style={{ transition: reduced ? "none" : "r 420ms ease" }}
        />
        <text
          x="110"
          y="104"
          textAnchor="middle"
          style={{ fontFamily: F.mono, fontSize: 25, fill: C.ink, fontWeight: 500 }}
        >
          {lit}
        </text>
        <text
          x="110"
          y="122"
          textAnchor="middle"
          style={{ fontFamily: F.mono, fontSize: 9.5, fill: C.inkDim, letterSpacing: "0.1em" }}
        >
          OF 8 RUN
        </text>
      </svg>

      <div>
        <div
          style={{
            fontFamily: F.mono,
            fontSize: 10.5,
            letterSpacing: "0.14em",
            textTransform: "uppercase",
            color: C.inkDim,
            marginBottom: 8,
          }}
        >
          Measured false-alarm rate at k = {lit}
        </div>

        <div style={{ display: "flex", alignItems: "baseline", gap: 4 }}>
          <span
            ref={fprRef}
            style={{
              fontFamily: F.mono,
              fontSize: 54,
              fontWeight: 500,
              color: C.ink,
              letterSpacing: "-0.03em",
              fontVariantNumeric: "tabular-nums",
            }}
          >
            {row.fpr.toFixed(1)}
          </span>
          <span style={{ fontFamily: F.mono, fontSize: 24, color: C.inkDim }}>%</span>
        </div>

        {/* magnitude rail. Uses the SEVERITY ramp, not the verdict palette —
            this is the size of a problem, not a verdict on a contract. */}
        <div
          style={{
            height: 6,
            background: C.bgAlt,
            borderRadius: 3,
            overflow: "hidden",
            margin: "12px 0 10px",
            maxWidth: 320,
          }}
        >
          <div
            style={{
              height: "100%",
              width: `${row.fpr}%`,
              background:
                row.fpr > 70 ? C.sev.critical : row.fpr > 45 ? C.sev.high : row.fpr > 25 ? C.sev.medium : C.accent,
              borderRadius: 3,
              transition: reduced ? "none" : "width 620ms cubic-bezier(.16,1,.3,1), background 620ms ease",
            }}
          />
        </div>

        <div
          style={{
            fontFamily: F.sans,
            fontSize: 13.5,
            lineHeight: 1.6,
            color: C.inkMid,
            maxWidth: "46ch",
          }}
        >
          Same safe contracts, same rule. The only thing changing is how many
          specialists the router fired —{" "}
          <span style={{ fontFamily: F.mono, fontSize: 12.5, color: C.inkDim }}>
            n = {row.n.toLocaleString()}
          </span>{" "}
          contracts at this k. Nobody chooses this number.
        </div>
      </div>
    </div>
  );
}
