// ─────────────────────────────────────────────────────────────────────────────
// The pinned pipeline.
//
// Six stages, pinned while you scroll through them, one active at a time. This
// is the one place on the site where a scroll effect carries information rather
// than decorating it: the pipeline IS a sequence, the reader IS moving through
// it, and progress through the scroll maps onto progress through the stages.
// (The Overview's site map, by contrast, is a set of peers — numbering or
// pinning that would be a lie about the content.)
//
// Pinning is the effect most likely to ruin a page, so three guards:
//   1. prefers-reduced-motion gets the plain stacked list, never a pin. A
//      pinned panel with motion disabled is a section you cannot leave.
//   2. Narrow viewports get the plain list too — pinning a two-column layout
//      into a phone leaves a tall empty column and a scroll that fights touch.
//   3. invalidateOnRefresh, because the pin's height is measured from content
//      that reflows on resize and on font load.
// ─────────────────────────────────────────────────────────────────────────────

import { useEffect, useRef, useState } from "react";
import { C, F, S } from "./design";
import { P } from "./ui";
import { ScrollTrigger, gsap, prefersReducedMotion } from "./motion";

import type { Stage } from "./stages";
export type { Stage };

export function Pipeline({ stages }: { stages: Stage[] }) {
  const [pinnable, setPinnable] = useState(false);
  const [active, setActive] = useState(0);
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const decide = () =>
      setPinnable(!prefersReducedMotion() && window.innerWidth >= 880);
    decide();
    window.addEventListener("resize", decide);
    return () => window.removeEventListener("resize", decide);
  }, []);

  useEffect(() => {
    const el = root.current;
    if (!el || !pinnable) return;

    const st = ScrollTrigger.create({
      trigger: el,
      start: "top 92px", // clears the sticky nav
      // One viewport-height of scroll per stage after the first.
      end: () => `+=${(stages.length - 1) * Math.round(window.innerHeight * 0.62)}`,
      pin: true,
      pinSpacing: true,
      invalidateOnRefresh: true,
      onUpdate: (self) => {
        const i = Math.min(
          stages.length - 1,
          Math.floor(self.progress * stages.length)
        );
        setActive(i);
      },
    });

    return () => st.kill();
  }, [pinnable, stages.length]);

  /* Reduced motion / narrow: the honest fallback is the content itself. */
  if (!pinnable) {
    return (
      <div style={{ display: "grid", gap: 12 }}>
        {stages.map((s) => (
          <div key={s.n} className="te-card" style={S.card}>
            <StageBody s={s} />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div
      ref={root}
      style={{
        display: "grid",
        gridTemplateColumns: "232px 1fr",
        gap: 32,
        alignItems: "start",
        minHeight: 420,
      }}
    >
      {/* the rail */}
      <ol
        style={{
          listStyle: "none",
          margin: 0,
          padding: 0,
          display: "grid",
          gap: 2,
          borderLeft: `1px solid ${C.line}`,
        }}
      >
        {stages.map((s, i) => {
          const on = i === active;
          const done = i < active;
          return (
            <li key={s.n}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 11,
                  padding: "9px 0 9px 14px",
                  marginLeft: -1,
                  borderLeft: `2px solid ${on ? C.accent : "transparent"}`,
                  transition: "border-color 320ms ease",
                }}
              >
                <span
                  style={{
                    fontFamily: F.mono,
                    fontSize: 11,
                    color: on ? C.accent : done ? C.inkMid : C.inkDim,
                    transition: "color 320ms ease",
                  }}
                >
                  {s.n}
                </span>
                <span
                  style={{
                    fontFamily: F.sans,
                    fontSize: 13.5,
                    fontWeight: on ? 600 : 400,
                    color: on ? C.ink : C.inkDim,
                    transition: "color 320ms ease",
                  }}
                >
                  {s.name}
                </span>
              </div>
            </li>
          );
        })}
      </ol>

      {/* the panel */}
      <div
        style={{
          ...S.card,
          minHeight: 300,
          display: "grid",
          alignContent: "start",
        }}
      >
        <StagePanel s={stages[active]} />
      </div>
    </div>
  );
}

/** Cross-fades the panel on stage change. Keyed on the stage number so React
 *  remounts it and the tween runs from scratch. */
function StagePanel({ s }: { s: Stage }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el || prefersReducedMotion()) return;
    const tw = gsap.fromTo(
      el,
      { opacity: 0, y: 10 },
      { opacity: 1, y: 0, duration: 0.42, ease: "power2.out" }
    );
    return () => {
      tw.kill();
    };
  }, [s.n]);

  return (
    <div ref={ref} key={s.n}>
      <div
        style={{
          fontFamily: F.mono,
          fontSize: 11,
          letterSpacing: "0.14em",
          color: C.accent,
          marginBottom: 10,
        }}
      >
        STAGE {s.n}
      </div>
      <StageBody s={s} big />
    </div>
  );
}

function StageBody({ s, big }: { s: Stage; big?: boolean }) {
  return (
    <>
      <div style={{ ...S.h3, fontSize: big ? 20 : 15, fontFamily: big ? F.serif : F.sans }}>
        {s.name}
      </div>
      <P style={{ margin: "0 0 12px", fontSize: big ? 15.5 : 14.5 }}>{s.what}</P>
      <div
        style={{
          borderLeft: `2px solid ${C.lineHi}`,
          paddingLeft: 13,
          fontFamily: F.sans,
          fontSize: 13.5,
          lineHeight: 1.6,
          color: C.inkDim,
          maxWidth: "62ch",
        }}
      >
        {s.why}
      </div>
    </>
  );
}
