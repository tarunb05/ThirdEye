import { useEffect, useMemo, useRef, useState } from "react";
import { EX, MONO, SANS } from "../../lib/exhibit-theme";
import { humanizeRole } from "../../lib/theme";

/** Replays a REAL recorded scan, specialist by specialist.
 *
 * Why a recording rather than an animation: the trace is captured from the same
 * streaming code path the live button uses (backend/eval/record_replay.py), with
 * real wall-clock offsets. Nothing here is invented — it is a scan that actually
 * happened, played back. A panel review cannot depend on a laptop GPU being warm,
 * but it also must not be shown fabricated behaviour.
 *
 * Playback is time-compressed by `speed` (a real scan is ~80s; nobody watches
 * that). The true duration is shown so the compression is never hidden.
 */

type Ev = {
  t: number;
  event: string;
  role?: string;
  model?: string;
  provider?: string;
  found?: boolean;
  confidence?: number;
  severity?: string;
  evidence_quote?: string;
  llm_error?: boolean;
  specialists?: { role: string; provider: string; model: string }[];
  result?: {
    final_verdict?: string;
    verdict_reason?: string;
    vulnerabilities?: { type: string; confidence?: number; evidence_quote?: string }[];
    stats?: Record<string, unknown>;
  };
};

export type Replay = {
  contract_id: string;
  label: string;
  ground_truth: string;
  duration_s: number;
  code: string;
  events: Ev[];
};

type RowState = "waiting" | "running" | "clear" | "flag" | "error";

export function ScanReplay({
  replay,
  speed = 8,
  autoStart = false,
  onDone,
}: {
  replay: Replay;
  speed?: number;
  autoStart?: boolean;
  onDone?: () => void;
}) {
  const [elapsed, setElapsed] = useState(0);
  const [playing, setPlaying] = useState(autoStart);
  // A timer, not requestAnimationFrame: rAF is suspended entirely in a
  // backgrounded or non-composited tab, which froze the replay mid-scan. The
  // position is recomputed from wall-clock each tick, so even a throttled timer
  // stays truthful rather than drifting.
  const timer = useRef<number | null>(null);
  const startedAt = useRef<number>(0);

  const total = replay.duration_s;
  const roster = useMemo(
    () => replay.events.find((e) => e.event === "start")?.specialists ?? [],
    [replay]
  );
  const done = useMemo(
    () => replay.events.filter((e) => e.event === "specialist_done"),
    [replay]
  );
  const final = useMemo(
    () => replay.events.find((e) => e.event === "final")?.result,
    [replay]
  );

  useEffect(() => {
    if (!playing) return;
    startedAt.current = Date.now() - (elapsed / speed) * 1000;
    const tick = () => {
      const e = ((Date.now() - startedAt.current) / 1000) * speed;
      if (e >= total) {
        setElapsed(total);
        setPlaying(false);
        if (timer.current) window.clearInterval(timer.current);
        onDone?.();
        return;
      }
      setElapsed(e);
    };
    timer.current = window.setInterval(tick, 50);
    return () => {
      if (timer.current) window.clearInterval(timer.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playing, speed, total]);

  const finished = elapsed >= total;

  function stateOf(role: string): { s: RowState; ev?: Ev } {
    const ev = done.find((d) => d.role === role);
    if (!ev) return { s: "waiting" };
    if (elapsed < ev.t) return { s: "running", ev };
    if (ev.llm_error) return { s: "error", ev };
    return { s: ev.found ? "flag" : "clear", ev };
  }

  const settled = done.filter((d) => elapsed >= d.t).length;
  const MARK: Record<RowState, string> = {
    waiting: "·",
    running: "◌",
    clear: "○",
    flag: "●",
    error: "×",
  };

  return (
    <div style={{ fontFamily: SANS }}>
      <div className="flex items-center gap-3 flex-wrap mb-4">
        <button
          onClick={() => {
            if (finished) setElapsed(0);
            setPlaying((p) => !p);
          }}
          className="px-4 py-2 text-sm"
          style={{
            background: playing ? "transparent" : EX.ink,
            color: playing ? EX.ink : EX.surface,
            border: `1px solid ${EX.ink}`,
            fontFamily: MONO,
            letterSpacing: ".04em",
            cursor: "pointer",
          }}
        >
          {playing ? "PAUSE" : finished ? "REPLAY" : "PLAY RECORDED SCAN"}
        </button>
        <div style={{ fontFamily: MONO, fontSize: 12, color: EX.inkMuted }}>
          {elapsed.toFixed(1)}s / {total.toFixed(1)}s &middot; {settled}/{roster.length} specialists
        </div>
        <div style={{ fontFamily: MONO, fontSize: 11, color: EX.slate, marginLeft: "auto" }}>
          recorded run &middot; played at {speed}&times;
        </div>
      </div>

      <div style={{ height: 2, background: EX.hairline, marginBottom: 18 }}>
        <div
          style={{
            height: "100%",
            width: `${Math.min(100, (elapsed / total) * 100)}%`,
            background: EX.data,
          }}
        />
      </div>

      <div className="grid sm:grid-cols-2 gap-x-8">
        {roster.map((sp) => {
          const { s, ev } = stateOf(sp.role);
          const color = s === "flag" ? EX.signal : s === "waiting" ? EX.slate : EX.ink;
          return (
            <div
              key={sp.role}
              style={{
                borderBottom: `1px solid ${EX.hairline}`,
                padding: "10px 0",
                opacity: s === "waiting" ? 0.45 : 1,
                transition: "opacity .25s",
              }}
            >
              <div className="flex items-baseline gap-3">
                <span style={{ fontFamily: MONO, color, width: 14, fontSize: 15 }}>{MARK[s]}</span>
                <span style={{ fontSize: 14, color: EX.ink, flex: 1 }}>{humanizeRole(sp.role)}</span>
                <span style={{ fontFamily: MONO, fontSize: 11, color: EX.slate }}>{sp.model}</span>
                {ev && elapsed >= ev.t && (
                  <span
                    style={{
                      fontFamily: MONO,
                      fontSize: 12,
                      color,
                      minWidth: 64,
                      textAlign: "right",
                    }}
                  >
                    {s === "error"
                      ? "ERROR"
                      : s === "flag"
                      ? `${(ev.confidence ?? 0).toFixed(2)} FLAG`
                      : "clear"}
                  </span>
                )}
              </div>
              {s === "flag" && ev?.evidence_quote && (
                <div
                  style={{
                    fontFamily: MONO,
                    fontSize: 11,
                    color: EX.inkMuted,
                    background: EX.signalWash,
                    borderLeft: `2px solid ${EX.signal}`,
                    padding: "6px 8px",
                    marginTop: 6,
                    marginLeft: 26,
                    whiteSpace: "pre-wrap",
                    overflowX: "auto",
                  }}
                >
                  {ev.evidence_quote.slice(0, 150)}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {finished && final && <Verdict result={final} groundTruth={replay.ground_truth} />}
    </div>
  );
}

function Verdict({
  result,
  groundTruth,
}: {
  result: NonNullable<Ev["result"]>;
  groundTruth: string;
}) {
  const blocked = result.final_verdict === "NO-GO";
  const stats = (result.stats ?? {}) as Record<string, number>;
  const truth = groundTruth === "vulnerable" ? "known vulnerable" : "known safe";
  const correct = blocked === (groundTruth === "vulnerable");
  return (
    <div style={{ marginTop: 22, borderTop: `2px solid ${EX.ink}`, paddingTop: 16 }}>
      <div className="flex items-baseline gap-4 flex-wrap">
        {/* Status always carries a WORD and a mark, never colour alone — it has
            to survive colourblindness, a greyscale print, and a bad projector. */}
        <div
          style={{
            fontFamily: MONO,
            fontSize: 28,
            letterSpacing: ".06em",
            color: blocked ? EX.signal : EX.ink,
          }}
        >
          {blocked ? "■ BLOCKED" : "□ CLEARED"}
        </div>
        <div style={{ fontFamily: MONO, fontSize: 12, color: EX.inkMuted }}>
          ground truth: {truth} &mdash; {correct ? "correct" : "incorrect"}
        </div>
      </div>
      <p style={{ marginTop: 10, fontSize: 14, color: EX.ink, maxWidth: "62ch", lineHeight: 1.55 }}>
        {result.verdict_reason}
      </p>
      {stats.contract_risk != null && (
        <div style={{ fontFamily: MONO, fontSize: 12, color: EX.inkMuted, marginTop: 8 }}>
          combined risk {Number(stats.contract_risk).toFixed(3)} vs bar{" "}
          {Number(stats.risk_tau ?? 0).toFixed(3)} &mdash;{" "}
          {blocked
            ? "at or above the bar, so it blocks"
            : "below the bar, so findings are reported without blocking"}
        </div>
      )}
    </div>
  );
}
