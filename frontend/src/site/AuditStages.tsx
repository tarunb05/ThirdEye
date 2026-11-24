// ─────────────────────────────────────────────────────────────────────────────
// Audit progress — the six stages, highlighted as the audit walks them.
//
// Stage names come from site/stages.ts, the same definition the How-it-works
// page renders, so this can never show a stage the pipeline does not have.
//
// WHAT THIS IS AND IS NOT. The stage rail is a PROGRESS INDICATOR, not a
// measured timeline: the backend streams routing and per-specialist events, not
// per-stage timings, so the walk between stages is paced by the component. The
// authoritative detail is the specialist list underneath it, which is real
// streamed data, and the elapsed timer, which is a real clock. Nothing here
// invents a number — it shows which stage the audit has reached.
//
// Timers, not animation frames. requestAnimationFrame was measured at 0 ticks
// per second in a non-compositing context, so a rAF-driven walk would freeze on
// stage one and the audit would look hung. setTimeout always fires.
// ─────────────────────────────────────────────────────────────────────────────

import { C, F } from "./design";
import { STAGES } from "./stages";

export function AuditStages({
  active,
  complete,
}: {
  /** Index of the stage currently running; -1 before the audit starts. */
  active: number;
  /** All stages finished — everything reads as done. */
  complete?: boolean;
}) {
  return (
    <ol
      aria-label="Audit progress"
      data-stage={active}
      data-complete={complete ? "1" : "0"}
      style={{
        listStyle: "none",
        margin: "0 0 4px",
        padding: 0,
        display: "grid",
        /* minmax(0,1fr), not 1fr. A 1fr track floors at its content's
           min-width, and "Model-diverse council" cannot wrap below its longest
           word -- so on a phone the six tracks summed past the viewport and
           pushed the whole page 50px sideways. */
        gridTemplateColumns: `repeat(${STAGES.length}, minmax(0, 1fr))`,
        gap: 8,
      }}
    >
      {STAGES.map((s, i) => {
        const done = complete || i < active;
        const on = !complete && i === active;
        const fg = on ? C.accent : done ? C.inkMid : C.inkDim;
        return (
          <li key={s.n}>
            {/* the rail segment */}
            <div
              style={{
                height: 3,
                borderRadius: 2,
                background: on || done ? C.accent : C.lineHi,
                opacity: on || done ? 1 : 0.5,
                transition: "background 300ms ease, opacity 300ms ease",
              }}
            />
            <div
              style={{
                marginTop: 7,
                display: "flex",
                alignItems: "baseline",
                gap: 6,
              }}
            >
              <span
                style={{
                  fontFamily: F.mono,
                  fontSize: 10,
                  color: fg,
                  transition: "color 300ms ease",
                }}
              >
                {s.n}
              </span>
              {/* A dot while running, so the active stage reads as active even
                  in greyscale and without relying on the accent alone. */}
              {on && (
                <span
                  className="animate-pulse-glow"
                  style={{
                    width: 5,
                    height: 5,
                    borderRadius: 99,
                    background: C.accent,
                    flexShrink: 0,
                  }}
                />
              )}
            </div>
            <div
              style={{
                fontFamily: F.sans,
                fontSize: 11.5,
                lineHeight: 1.35,
                overflowWrap: "anywhere",
                fontWeight: on ? 600 : 400,
                color: on ? C.ink : fg,
                transition: "color 300ms ease",
              }}
            >
              {s.name}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
