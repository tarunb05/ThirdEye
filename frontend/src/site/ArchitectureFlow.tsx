// ─────────────────────────────────────────────────────────────────────────────
// The architecture, playing.
//
// This replaces a six-segment progress bar. A bar told you WHICH stage the
// audit had reached; this shows the audit happening — source into the static
// pre-pass, the router selecting from eight specialists, the selected ones
// answering one at a time, their flags walking into the evidence gate, the
// survivors pooling into a noisy-OR risk that climbs toward τ, and the verdict
// latching at the end.
//
// EVERYTHING ON SCREEN IS DERIVED, NOTHING IS INVENTED.
//   · which specialists exist          — facts.SPECIALISTS (8, fixed)
//   · which ones ran                   — the router's own `routing` event
//   · which flagged / came back clean  — `specialist_done`, per specialist
//   · which flags survived the gate    — a flagging specialist with no finding
//                                        in the final result WAS dropped by the
//                                        gate; that is a real drop, not a prop
//   · the risk number                  — risk = 1 − Π(1 − cᵢ) over the
//                                        surviving findings, the shipped formula
//   · τ = 0.925                        — the shipped threshold
// The one thing paced by the component rather than measured is the ORDER the
// specialists resolve in during a recorded replay; live, it is arrival order.
// There are no fake nodes, no decorative packets carrying nothing, and no
// numbers that the pipeline did not produce.
//
// WHY SMIL AND CSS, NOT requestAnimationFrame. rAF was measured at 0 ticks per
// second in a non-compositing context, which would freeze a JS-driven timeline
// mid-pipeline and make a working audit look hung. Every moving thing here is
// either a CSS animation or an SVG <animateMotion> — both declarative, both
// driven by the browser's own compositor, neither dependent on a JS clock.
// ─────────────────────────────────────────────────────────────────────────────

import { useEffect, useState } from "react";
import { C, F } from "./design";
import { SPECIALISTS } from "./facts";
import { prefersReducedMotion } from "./motion";

/* Router order: business_logic first, because the static router always selects
 * it. Same order as the hero's iris, for the same reason — the council is not a
 * neutral ring of equals and should not be drawn as one. */
const ORDER = [
  "business_logic",
  "arithmetic",
  "access_control",
  "dos_gas",
  "reentrancy",
  "oracle_price_manipulation",
  "proxy_upgradeability",
  "flashloan_mev",
] as const;

const ROLES = ORDER.map((r) => SPECIALISTS.find((s) => s.role === r)!);

export const TAU = 0.925;

export type FlowFinding = {
  type: string;
  severity: string;
  confidence: number;
};

/* ── geometry ─────────────────────────────────────────────────────────────── */

const W = 980;
const H = 452;

const SRC = { x: 16, y: 196, w: 84, h: 60 };
const PRE = { x: 126, y: 196, w: 96, h: 60 };
const RTR = { x: 248, y: 186, w: 92, h: 80 };
const SPEC = { x: 392, w: 164, h: 32, top: 18, gap: 52 };
const GATE = { x: 610, y: 140, w: 74, h: 172 };
const POOL = { x: 718, y: 96, w: 56, h: 260 };
const VER = { x: 836, y: 196, w: 128, h: 60 };

const specY = (i: number) => SPEC.top + i * SPEC.gap;
const specMid = (i: number) => specY(i) + SPEC.h / 2;

const RTR_OUT = { x: RTR.x + RTR.w, y: RTR.y + RTR.h / 2 };
const GATE_IN = { x: GATE.x, y: GATE.y + GATE.h / 2 };

/** A flat-S bezier from the router's output port to specialist row i. */
function routerEdge(i: number) {
  const y = specMid(i);
  const x0 = RTR_OUT.x;
  const x1 = SPEC.x;
  const mx = (x0 + x1) / 2;
  return `M ${x0} ${RTR_OUT.y} C ${mx} ${RTR_OUT.y}, ${mx} ${y}, ${x1} ${y}`;
}

/** Specialist row i back into the gate's input. */
function gateEdge(i: number) {
  const y = specMid(i);
  const x0 = SPEC.x + SPEC.w;
  const x1 = GATE_IN.x;
  const mx = (x0 + x1) / 2;
  return `M ${x0} ${y} C ${mx} ${y}, ${mx} ${GATE_IN.y}, ${x1} ${GATE_IN.y}`;
}

/* ── the component ────────────────────────────────────────────────────────── */

export function ArchitectureFlow({
  stage,
  roles,
  done,
  findings,
  verdict,
  complete,
}: {
  /** Index into STAGES: 0 static, 1 router, 2 council, 3 gate, 4 pooling, 5 verdict. */
  stage: number;
  /** Roles the router selected. */
  roles: string[];
  /** Specialists that have answered, in arrival order. */
  done: { role: string; found: boolean; model: string }[];
  /** Findings that survived the gate — empty until the result lands. */
  findings: FlowFinding[];
  verdict?: string | null;
  complete?: boolean;
}) {
  const reduced = prefersReducedMotion();
  const routed = new Set(roles);

  /* Narrow viewports get nothing from this, and that is the honest answer.
   *
   * The schematic is 980 units wide. Scaled into a phone it draws its model
   * names at under 4px -- not a smaller diagram, an unreadable one. The
   * alternative, a horizontal scrollbar, is worse: it asks the reader to drag
   * a FLOW past its own verdict to see the end of it. So below 760px the stage
   * rail underneath carries the audit on its own, which is what it was built
   * to do. Same reasoning as the pinned pipeline's narrow fallback. */
  const [wide, setWide] = useState(
    typeof window === "undefined" ? true : window.innerWidth >= 760
  );
  useEffect(() => {
    const decide = () => setWide(window.innerWidth >= 760);
    decide();
    window.addEventListener("resize", decide);
    return () => window.removeEventListener("resize", decide);
  }, []);
  if (!wide) return null;

  /* A specialist's state, read off real events only. */
  const stateOf = (role: string) => {
    if (!routed.has(role)) return "skipped" as const;
    const d = done.find((x) => x.role === role);
    if (!d) return stage >= 2 ? ("running" as const) : ("selected" as const);
    return d.found ? ("flagged" as const) : ("clean" as const);
  };

  /* Which flags survived. A specialist that reported found=true but owns no
   * finding in the final result was dropped by the evidence gate — it could not
   * quote a line that appears in the source. Until the result arrives we do not
   * know, so nothing is drawn as dropped before stage 3. */
  const flagged = done.filter((d) => d.found).map((d) => d.role);
  const gateKnown = stage >= 3 && findings.length >= 0 && (complete || stage >= 4);
  const survivors = findings.map((f) => f.type);
  const dropped = gateKnown ? flagged.filter((r) => !survivors.includes(r)) : [];

  /* Noisy-OR over the survivors — the shipped formula, not a progress value. */
  const risk =
    stage >= 4 && findings.length
      ? 1 - findings.reduce((p, f) => p * (1 - f.confidence), 1)
      : 0;
  const riskShown = stage >= 4 ? risk : 0;
  const poolFill = Math.max(0, Math.min(1, riskShown));

  /* Edges carry a travelling token only while their stage is executing. */
  const liveEdge = (s: number) => !reduced && stage === s;

  return (
    <div
      role="img"
      aria-label={`Pipeline schematic. Stage ${Math.min(stage + 1, 6)} of 6.${
        roles.length ? ` ${roles.length} of 8 specialists routed.` : ""
      }${verdict ? ` Verdict ${verdict}.` : ""}`}
      data-stage={stage}
      data-risk={riskShown.toFixed(3)}
      style={{
        border: `1px solid ${C.line}`,
        borderRadius: 10,
        background: C.panel,
        padding: "14px 12px 10px",
      }}
      className="te-flow-in"
    >
      <svg
        viewBox={`0 0 ${W} ${H}`}
        /* Scales to the column, never scrolls. A minWidth floor here put a
           horizontal scrollbar under the panel at every realistic width, which
           is the one interaction a diagram of a FLOW must not ask for -- the
           reader would have had to drag the pipeline past its own verdict. The
           viewBox does the fitting instead. */
        style={{ width: "100%", display: "block" }}
      >
        <defs>
          {ROLES.map((r, i) => (
            <path key={`rp${r.role}`} id={`te-rt-${i}`} d={routerEdge(i)} fill="none" />
          ))}
          {ROLES.map((r, i) => (
            <path key={`gp${r.role}`} id={`te-gt-${i}`} d={gateEdge(i)} fill="none" />
          ))}
          <path id="te-src" d={`M ${SRC.x + SRC.w} 226 L ${PRE.x} 226`} fill="none" />
          <path id="te-pre" d={`M ${PRE.x + PRE.w} 226 L ${RTR.x} 226`} fill="none" />
          <path
            id="te-pool"
            d={`M ${GATE.x + GATE.w} ${GATE_IN.y} L ${POOL.x} ${GATE_IN.y}`}
            fill="none"
          />
          <path
            id="te-ver"
            d={`M ${POOL.x + POOL.w} ${GATE_IN.y} L ${VER.x} ${GATE_IN.y}`}
            fill="none"
          />
          {/* The pool's liquid is clipped to the meter's rounded box, so the
              fill cannot bleed past the instrument's own frame. */}
          <clipPath id="te-poolclip">
            <rect x={POOL.x} y={POOL.y} width={POOL.w} height={POOL.h} rx={6} />
          </clipPath>
        </defs>

        {/* ── stage 01 · source and static pre-pass ── */}
        <Edge id="te-src" on={stage >= 0} live={liveEdge(0)} />
        <Node
          {...SRC}
          label="Source"
          sub=".sol"
          state={stage >= 0 ? "done" : "idle"}
          delay={0}
        />
        <Node
          {...PRE}
          n="01"
          label="Static"
          sub="features"
          state={stage === 0 ? "active" : stage > 0 ? "done" : "idle"}
          delay={70}
        />

        {/* ── stage 02 · router ── */}
        <Edge id="te-pre" on={stage >= 1} live={liveEdge(1)} />
        <Node
          {...RTR}
          n="02"
          label="Router"
          sub={roles.length ? `${roles.length} of 8` : "selects k"}
          state={stage === 1 ? "active" : stage > 1 ? "done" : "idle"}
          delay={140}
        />

        {/* ── stage 03 · the council ── */}
        {ROLES.map((r, i) => {
          const state = stateOf(r.role);
          const sel = state !== "skipped";
          return (
            <g key={r.role}>
              {/* The router edge keeps streaming into a specialist for as long
                  as that specialist is still thinking. The council is by far
                  the longest stage -- 25s of a live run against 4GB of VRAM --
                  and without this it is also the only stage with nothing
                  moving, which reads as a hang rather than as work. */}
              <Edge
                id={`te-rt-${i}`}
                on={stage >= 1 && sel}
                live={(liveEdge(1) && sel) || (!reduced && stage === 2 && state === "running")}
                dim={!sel}
                dashed={!sel}
              />
              <Edge
                id={`te-gt-${i}`}
                on={stage >= 3 && state === "flagged"}
                live={liveEdge(3) && state === "flagged"}
                tone={C.accent}
              />
              <SpecialistNode
                i={i}
                delay={210 + i * 45}
                label={r.label}
                /* The model that ACTUALLY answered, once it has. The config
                   pairs this role with a 7b coder; a 4GB laptop GPU serves the
                   3b, and the run reports which one it used. Showing the
                   configured name after a different model replied would be the
                   same class of mistake as counting models instead of checking
                   them by name, which cost this project an evaluation run. */
                model={done.find((d) => d.role === r.role)?.model || r.model}
                state={state}
              />
            </g>
          );
        })}

        {/* ── stage 04 · evidence gate ── */}
        <GateNode
          delay={600}
          state={stage === 3 ? "active" : stage > 3 ? "done" : "idle"}
          passed={gateKnown ? findings.length : null}
          dropped={gateKnown ? dropped.length : null}
        />

        {/* ── stage 05 · risk pooling ── */}
        <Edge id="te-pool" on={stage >= 4} live={liveEdge(4)} tone={C.accent} />
        <PoolNode
          delay={670}
          state={stage === 4 ? "active" : stage > 4 ? "done" : "idle"}
          fill={poolFill}
          risk={riskShown}
          show={stage >= 4}
        />

        {/* ── stage 06 · verdict ── */}
        <Edge id="te-ver" on={stage >= 5} live={liveEdge(5)} tone={C.accent} />
        <VerdictNode
          delay={740}
          state={stage === 5 ? "active" : complete ? "done" : "idle"}
          verdict={complete ? verdict : null}
        />
      </svg>

      {/* The dropped flags, named. A number alone ("2 dropped") is a claim; the
          roles are the evidence for it, and this is the project's headline
          mechanism, so it gets words rather than a tooltip. */}
      {dropped.length > 0 && (
        <div
          style={{
            marginTop: 4,
            display: "flex",
            gap: 8,
            flexWrap: "wrap",
            alignItems: "baseline",
            fontFamily: F.mono,
            fontSize: 11,
            color: C.inkDim,
          }}
        >
          <span style={{ color: C.accent }}>gate dropped</span>
          {dropped.map((r) => (
            <span key={r} style={{ textDecoration: "line-through" }}>
              {r}
            </span>
          ))}
          <span>— flagged, but could not quote the submitted source</span>
        </div>
      )}
    </div>
  );
}

/* ── parts ────────────────────────────────────────────────────────────────── */

type NodeState = "idle" | "selected" | "running" | "active" | "done" | "skipped";

function strokeFor(state: NodeState) {
  if (state === "active" || state === "running") return C.accent;
  if (state === "done") return C.lineHi;
  return C.line;
}

/** An edge, plus a token travelling along it while its stage executes. */
function Edge({
  id,
  on,
  live,
  dim,
  dashed,
  tone,
}: {
  id: string;
  on: boolean;
  live: boolean;
  dim?: boolean;
  dashed?: boolean;
  tone?: string;
}) {
  const col = dim ? C.line : on ? (tone ?? C.lineHi) : C.line;
  return (
    <>
      <use
        href={`#${id}`}
        stroke={col}
        strokeWidth={dim ? 1 : 1.4}
        strokeDasharray={dashed ? "2 5" : undefined}
        fill="none"
        opacity={dim ? 0.55 : on ? 1 : 0.5}
        style={{ transition: "stroke 320ms ease, opacity 320ms ease" }}
      />
      {live && (
        <circle r={3} fill={tone ?? C.accent}>
          <animateMotion dur="1.05s" repeatCount="indefinite" calcMode="linear">
            <mpath href={`#${id}`} />
          </animateMotion>
        </circle>
      )}
    </>
  );
}

function Node({
  x,
  y,
  w,
  h,
  n,
  label,
  sub,
  state,
  delay,
}: {
  x: number;
  y: number;
  w: number;
  h: number;
  n?: string;
  label: string;
  sub?: string;
  state: NodeState;
  delay?: number;
}) {
  const on = state === "active";
  return (
    <g className="te-pop" style={{ animationDelay: `${delay ?? 0}ms` }}>
      {on && (
        <rect
          x={x - 4}
          y={y - 4}
          width={w + 8}
          height={h + 8}
          rx={10}
          fill="none"
          stroke={C.accent}
          strokeWidth={1}
          className="animate-ring-pulse"
        />
      )}
      <rect
        x={x}
        y={y}
        width={w}
        height={h}
        rx={7}
        fill={on ? C.accentGhost : state === "done" ? C.bgAlt : C.panel}
        stroke={strokeFor(state)}
        strokeWidth={on ? 1.6 : 1}
        style={{ transition: "fill 320ms ease, stroke 320ms ease" }}
      />
      {n && (
        <text
          x={x + 9}
          y={y + 15}
          fontFamily={F.mono}
          fontSize={9}
          letterSpacing="0.1em"
          fill={on ? C.accent : C.inkDim}
        >
          {n}
        </text>
      )}
      <text
        x={x + w / 2}
        y={y + h / 2 + (sub ? -1 : 4)}
        textAnchor="middle"
        fontFamily={F.sans}
        fontSize={12.5}
        fontWeight={on ? 600 : 500}
        fill={state === "idle" ? C.inkDim : C.ink}
      >
        {label}
      </text>
      {sub && (
        <text
          x={x + w / 2}
          y={y + h / 2 + 14}
          textAnchor="middle"
          fontFamily={F.mono}
          fontSize={9.5}
          fill={on ? C.accent : C.inkDim}
        >
          {sub}
        </text>
      )}
    </g>
  );
}

/** One of the eight. Skipped ones stay on screen, drawn as not-run — the point
 *  of the router is what it DIDN'T fire, so hiding them would hide the finding. */
function SpecialistNode({
  i,
  label,
  model,
  state,
  delay,
}: {
  i: number;
  label: string;
  model: string;
  state: "skipped" | "selected" | "running" | "flagged" | "clean";
  delay?: number;
}) {
  const y = specY(i);
  const skipped = state === "skipped";
  const running = state === "running";
  const tone =
    state === "flagged" ? C.nogo : state === "clean" ? C.go : running ? C.accent : C.line;

  /* The entrance lives on an OUTER group. A `both`-filled animation settles on
   * opacity 1, so putting it on the same element that carries the not-routed
   * dimming would have un-dimmed every skipped specialist the moment the
   * entrance finished. */
  return (
    <g className="te-pop" style={{ animationDelay: `${delay ?? 0}ms` }}>
    <g opacity={skipped ? 0.42 : 1} style={{ transition: "opacity 320ms ease" }}>
      {running && (
        <rect
          x={SPEC.x - 3}
          y={y - 3}
          width={SPEC.w + 6}
          height={SPEC.h + 6}
          rx={8}
          fill="none"
          stroke={C.accent}
          strokeWidth={1}
          className="animate-ring-pulse"
        />
      )}
      <rect
        x={SPEC.x}
        y={y}
        width={SPEC.w}
        height={SPEC.h}
        rx={6}
        fill={
          state === "flagged"
            ? C.nogoGhost
            : state === "clean"
              ? C.goGhost
              : running
                ? C.accentGhost
                : C.panel
        }
        stroke={skipped ? C.line : tone}
        strokeWidth={running ? 1.6 : 1}
        strokeDasharray={skipped ? "3 4" : undefined}
        style={{ transition: "fill 320ms ease, stroke 320ms ease" }}
      />
      {/* State mark — never colour alone. A bar for flagged, a ring for clean,
          a pulse for running, nothing for skipped. */}
      <g transform={`translate(${SPEC.x + 11} ${y + SPEC.h / 2})`}>
        {state === "flagged" && <rect x={-3} y={-5} width={6} height={10} rx={1} fill={C.nogo} />}
        {state === "clean" && (
          <circle r={4} fill="none" stroke={C.go} strokeWidth={1.6} />
        )}
        {running && <circle r={3.5} fill={C.accent} className="animate-pulse-glow" />}
        {state === "selected" && <circle r={2} fill={C.inkDim} />}
        {skipped && <line x1={-4} y1={0} x2={4} y2={0} stroke={C.inkDim} strokeWidth={1.2} />}
      </g>
      <text
        x={SPEC.x + 24}
        y={y + 14}
        fontFamily={F.sans}
        fontSize={11.5}
        fontWeight={running ? 600 : 400}
        fill={skipped ? C.inkDim : C.ink}
      >
        {label}
      </text>
      <text
        x={SPEC.x + 24}
        y={y + 25}
        fontFamily={F.mono}
        fontSize={8.5}
        fill={C.inkDim}
      >
        {skipped ? "not routed" : model}
      </text>
    </g>
    </g>
  );
}

/** The evidence gate, drawn as a filter with a lip the dropped flags fall off. */
function GateNode({
  state,
  passed,
  dropped,
  delay,
}: {
  state: NodeState;
  passed: number | null;
  dropped: number | null;
  delay?: number;
}) {
  const on = state === "active";
  return (
    <g className="te-pop" style={{ animationDelay: `${delay ?? 0}ms` }}>
      {on && (
        <rect
          x={GATE.x - 4}
          y={GATE.y - 4}
          width={GATE.w + 8}
          height={GATE.h + 8}
          rx={10}
          fill="none"
          stroke={C.accent}
          strokeWidth={1}
          className="animate-ring-pulse"
        />
      )}
      <rect
        x={GATE.x}
        y={GATE.y}
        width={GATE.w}
        height={GATE.h}
        rx={7}
        fill={on ? C.accentGhost : state === "done" ? C.bgAlt : C.panel}
        stroke={strokeFor(state)}
        strokeWidth={on ? 1.6 : 1}
        style={{ transition: "fill 320ms ease, stroke 320ms ease" }}
      />
      {/* The sieve: three slots, because the gate is three conjoined tests —
          found, confidence ≥ 0.6, and a verbatim quote. */}
      {[0, 1, 2].map((k) => (
        <line
          key={k}
          x1={GATE.x + 14}
          x2={GATE.x + GATE.w - 14}
          y1={GATE.y + 64 + k * 16}
          y2={GATE.y + 64 + k * 16}
          stroke={on ? C.accent : C.lineHi}
          strokeWidth={1.4}
          strokeDasharray="7 6"
          className={on ? "flow-dash" : undefined}
          style={{ transition: "stroke 320ms ease" }}
        />
      ))}
      <text
        x={GATE.x + 9}
        y={GATE.y + 16}
        fontFamily={F.mono}
        fontSize={9}
        letterSpacing="0.1em"
        fill={on ? C.accent : C.inkDim}
      >
        04
      </text>
      <text
        x={GATE.x + GATE.w / 2}
        y={GATE.y + 34}
        textAnchor="middle"
        fontFamily={F.sans}
        fontSize={12}
        fontWeight={on ? 600 : 500}
        fill={state === "idle" ? C.inkDim : C.ink}
      >
        Evidence
      </text>
      <text
        x={GATE.x + GATE.w / 2}
        y={GATE.y + 48}
        textAnchor="middle"
        fontFamily={F.sans}
        fontSize={12}
        fontWeight={on ? 600 : 500}
        fill={state === "idle" ? C.inkDim : C.ink}
      >
        gate
      </text>
      {passed !== null && (
        <>
          <text
            x={GATE.x + GATE.w / 2}
            y={GATE.y + GATE.h - 26}
            textAnchor="middle"
            fontFamily={F.mono}
            fontSize={13}
            fill={C.ink}
          >
            {passed}
          </text>
          <text
            x={GATE.x + GATE.w / 2}
            y={GATE.y + GATE.h - 13}
            textAnchor="middle"
            fontFamily={F.mono}
            fontSize={8.5}
            fill={C.inkDim}
          >
            {dropped ? `−${dropped} cut` : "survived"}
          </text>
        </>
      )}
    </g>
  );
}

/** Noisy-OR pooling, drawn as a filling column against the τ tick. */
function PoolNode({
  state,
  fill,
  risk,
  show,
  delay,
}: {
  state: NodeState;
  fill: number;
  risk: number;
  show: boolean;
  delay?: number;
}) {
  const on = state === "active";
  const h = POOL.h * fill;
  const tauY = POOL.y + POOL.h * (1 - TAU);
  const over = risk >= TAU;
  return (
    <g className="te-pop" style={{ animationDelay: `${delay ?? 0}ms` }}>
      {on && (
        <rect
          x={POOL.x - 4}
          y={POOL.y - 4}
          width={POOL.w + 8}
          height={POOL.h + 8}
          rx={10}
          fill="none"
          stroke={C.accent}
          strokeWidth={1}
          className="animate-ring-pulse"
        />
      )}
      <rect
        x={POOL.x}
        y={POOL.y}
        width={POOL.w}
        height={POOL.h}
        rx={6}
        fill={C.panel}
        stroke={strokeFor(state)}
        strokeWidth={on ? 1.6 : 1}
        style={{ transition: "stroke 320ms ease" }}
      />
      {/* the liquid */}
      <g clipPath="url(#te-poolclip)">
        <rect
          x={POOL.x}
          y={POOL.y + POOL.h - h}
          width={POOL.w}
          height={h}
          fill={over ? C.nogoGhost : C.accentGhost}
          style={{ transition: "y 820ms cubic-bezier(.4,0,.2,1), height 820ms cubic-bezier(.4,0,.2,1), fill 320ms ease" }}
        />
        <rect
          x={POOL.x}
          y={POOL.y + POOL.h - h}
          width={POOL.w}
          height={h > 0 ? 2 : 0}
          fill={over ? C.nogo : C.accent}
          style={{ transition: "y 820ms cubic-bezier(.4,0,.2,1)" }}
        />
      </g>
      {/* τ — the shipped threshold, drawn as a calibration mark */}
      <line
        x1={POOL.x - 6}
        x2={POOL.x + POOL.w + 6}
        y1={tauY}
        y2={tauY}
        stroke={C.ink}
        strokeWidth={1}
        strokeDasharray="4 3"
      />
      <text
        x={POOL.x + POOL.w + 9}
        y={tauY - 4}
        fontFamily={F.mono}
        fontSize={9}
        fill={C.inkMid}
      >
        τ .925
      </text>
      <text
        x={POOL.x + 8}
        y={POOL.y + 14}
        fontFamily={F.mono}
        fontSize={9}
        letterSpacing="0.1em"
        fill={on ? C.accent : C.inkDim}
      >
        05
      </text>
      <text
        x={POOL.x + POOL.w / 2}
        y={POOL.y + POOL.h + 18}
        textAnchor="middle"
        fontFamily={F.sans}
        fontSize={11.5}
        fontWeight={on ? 600 : 500}
        fill={state === "idle" ? C.inkDim : C.ink}
      >
        noisy-OR
      </text>
      <text
        x={POOL.x + POOL.w / 2}
        y={POOL.y + POOL.h + 31}
        textAnchor="middle"
        fontFamily={F.mono}
        fontSize={10}
        fill={show ? (over ? C.nogo : C.ink) : C.inkDim}
      >
        {show ? `risk ${risk.toFixed(3)}` : "risk —"}
      </text>
    </g>
  );
}

function VerdictNode({
  state,
  verdict,
  delay,
}: {
  state: NodeState;
  verdict?: string | null;
  delay?: number;
}) {
  const on = state === "active";
  const tone =
    verdict === "GO" ? C.go : verdict === "NO-GO" ? C.nogo : verdict ? C.inconc : C.line;
  const ghost =
    verdict === "GO"
      ? C.goGhost
      : verdict === "NO-GO"
        ? C.nogoGhost
        : verdict
          ? C.inconcGhost
          : on
            ? C.accentGhost
            : C.panel;
  return (
    <g className="te-pop" style={{ animationDelay: `${delay ?? 0}ms` }}>
      {on && !verdict && (
        <rect
          x={VER.x - 4}
          y={VER.y - 4}
          width={VER.w + 8}
          height={VER.h + 8}
          rx={10}
          fill="none"
          stroke={C.accent}
          strokeWidth={1}
          className="animate-ring-pulse"
        />
      )}
      <rect
        x={VER.x}
        y={VER.y}
        width={VER.w}
        height={VER.h}
        rx={7}
        fill={ghost}
        stroke={verdict ? tone : strokeFor(state)}
        strokeWidth={verdict ? 1.8 : on ? 1.6 : 1}
        style={{ transition: "fill 420ms ease, stroke 420ms ease" }}
      />
      <text
        x={VER.x + 9}
        y={VER.y + 15}
        fontFamily={F.mono}
        fontSize={9}
        letterSpacing="0.1em"
        fill={verdict ? tone : on ? C.accent : C.inkDim}
      >
        06
      </text>
      <text
        x={VER.x + VER.w / 2}
        y={VER.y + VER.h / 2 + 8}
        textAnchor="middle"
        fontFamily={verdict ? F.mono : F.sans}
        fontSize={verdict ? 19 : 12.5}
        fontWeight={600}
        fill={verdict ? tone : C.inkDim}
        style={{ transition: "fill 420ms ease" }}
      >
        {verdict ?? "Verdict"}
      </text>
    </g>
  );
}
