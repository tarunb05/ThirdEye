import { useRef, useState } from "react";
import { EX, MONO, SANS } from "../../lib/exhibit-theme";
import { humanizeRole } from "../../lib/theme";
import { streamCouncil, type StreamEvent } from "../../lib/api";

/** Runs a REAL scan against the live backend, rendered like the replay.
 *
 * The replay exists because a panel review cannot depend on a warm GPU. This
 * exists because somebody will inevitably ask "is that just a video?" — so the
 * same screen can run the real thing on demand.
 *
 * It is explicitly the slow path: a cold local model takes 30-200s. The UI says
 * so up front rather than letting a spinner imply something is broken, and any
 * failure surfaces the actual reason (backend asleep, no models, rate limited)
 * instead of a generic error.
 */

type Row = {
  role: string;
  model?: string;
  state: "waiting" | "clear" | "flag" | "error";
  confidence?: number;
  quote?: string;
};

export function LiveScan({ code, contractId }: { code: string; contractId: string }) {
  const [rows, setRows] = useState<Row[]>([]);
  const [status, setStatus] = useState<"idle" | "running" | "done" | "failed">("idle");
  const [verdict, setVerdict] = useState<{ v?: string; reason?: string } | null>(null);
  const [error, setError] = useState<string>("");
  const [t0, setT0] = useState(0);
  const [now, setNow] = useState(0);
  const abort = useRef<AbortController | null>(null);
  const timer = useRef<number | null>(null);

  function stop() {
    abort.current?.abort();
    if (timer.current) window.clearInterval(timer.current);
    timer.current = null;
  }

  async function run() {
    setRows([]); setVerdict(null); setError(""); setStatus("running");
    const start = Date.now();
    setT0(start); setNow(start);
    timer.current = window.setInterval(() => setNow(Date.now()), 250);
    abort.current = new AbortController();
    try {
      await streamCouncil(
        code,
        (ev: StreamEvent) => {
          const e = ev as Record<string, unknown>;
          if (e.event === "start" || e.event === "routing") {
            const list = (e.specialists as { role: string; model: string }[] | undefined)
              ?? ((e.roles as string[] | undefined) ?? []).map((r) => ({ role: r, model: "" }));
            if (list.length) {
              setRows(list.map((s) => ({ role: s.role, model: s.model, state: "waiting" })));
            }
          } else if (e.event === "specialist_done") {
            setRows((prev) => {
              const next = [...prev];
              const i = next.findIndex((r) => r.role === e.role);
              const row: Row = {
                role: e.role as string,
                model: (e.model as string) ?? next[i]?.model,
                state: e.llm_error ? "error" : e.found ? "flag" : "clear",
                confidence: e.confidence as number,
                quote: e.evidence_quote as string,
              };
              if (i >= 0) next[i] = row; else next.push(row);
              return next;
            });
          } else if (e.event === "final") {
            const r = e.result as { final_verdict?: string; verdict_reason?: string };
            setVerdict({ v: r?.final_verdict, reason: r?.verdict_reason });
            setStatus("done");
            stop();
          }
        },
        { signal: abort.current.signal }
      );
      setStatus((s) => (s === "running" ? "done" : s));
    } catch (err) {
      // Say what actually went wrong. The three real causes are a sleeping free
      // Render dyno, a backend with no local models, and the rate limiter.
      const msg = err instanceof Error ? err.message : String(err);
      setError(
        /429/.test(msg) ? "Rate limit reached — the scan endpoint allows a fixed number per hour."
        : /Failed to fetch|NetworkError|502|503/.test(msg)
          ? "The analysis backend is asleep or unreachable. It is a free instance and can take ~60s to wake — try again, or use the recorded scan."
          : msg
      );
      setStatus("failed");
    } finally {
      stop();
    }
  }

  const elapsed = ((now - t0) / 1000).toFixed(0);
  const MARK = { waiting: "◌", clear: "○", flag: "●", error: "×" } as const;

  return (
    <div style={{ fontFamily: SANS }}>
      <div className="flex items-center gap-3 flex-wrap mb-3">
        <button
          onClick={() => (status === "running" ? (stop(), setStatus("idle")) : run())}
          style={{
            fontFamily: MONO, fontSize: 12, letterSpacing: ".05em", padding: "9px 16px",
            background: status === "running" ? "transparent" : EX.signal,
            color: status === "running" ? EX.ink : "#fff",
            border: `1px solid ${status === "running" ? EX.ink : EX.signal}`, cursor: "pointer",
          }}
        >
          {status === "running" ? "CANCEL" : status === "done" ? "RUN AGAIN" : "RUN IT LIVE NOW"}
        </button>
        {status === "running" && (
          <span style={{ fontFamily: MONO, fontSize: 12, color: EX.inkMuted }}>
            scanning… {elapsed}s &middot; a real scan takes 30–200s
          </span>
        )}
        {status === "idle" && (
          <span style={{ fontFamily: MONO, fontSize: 11.5, color: EX.slate }}>
            hits the real backend &middot; slow by nature
          </span>
        )}
      </div>

      {error && (
        <div style={{ fontFamily: MONO, fontSize: 12, color: EX.signal, background: EX.signalWash,
                      border: `1px solid ${EX.signal}`, padding: "10px 12px", marginBottom: 14 }}>
          {error}
        </div>
      )}

      {rows.length > 0 && (
        <div className="grid sm:grid-cols-2 gap-x-8">
          {rows.map((r) => {
            const color = r.state === "flag" ? EX.signal : r.state === "waiting" ? EX.slate : EX.ink;
            return (
              <div key={r.role} style={{ borderBottom: `1px solid ${EX.hairline}`, padding: "10px 0" }}>
                <div className="flex items-baseline gap-3">
                  <span style={{ fontFamily: MONO, color, width: 14 }}>{MARK[r.state]}</span>
                  <span style={{ fontSize: 14, flex: 1 }}>{humanizeRole(r.role)}</span>
                  <span style={{ fontFamily: MONO, fontSize: 11, color: EX.slate }}>{r.model}</span>
                  <span style={{ fontFamily: MONO, fontSize: 12, color, minWidth: 64, textAlign: "right" }}>
                    {r.state === "waiting" ? "…"
                      : r.state === "error" ? "ERROR"
                      : r.state === "flag" ? `${(r.confidence ?? 0).toFixed(2)} FLAG`
                      : "clear"}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {verdict && (
        <div style={{ marginTop: 20, borderTop: `2px solid ${EX.ink}`, paddingTop: 14 }}>
          <div style={{ fontFamily: MONO, fontSize: 26, letterSpacing: ".06em",
                        color: verdict.v === "NO-GO" ? EX.signal : EX.ink }}>
            {verdict.v === "NO-GO" ? "■ BLOCKED" : verdict.v === "GO" ? "□ CLEARED" : "◍ INCONCLUSIVE"}
          </div>
          <p style={{ fontSize: 14, lineHeight: 1.55, maxWidth: "62ch", marginTop: 8 }}>{verdict.reason}</p>
          <div style={{ fontFamily: MONO, fontSize: 11, color: EX.slate, marginTop: 6 }}>
            live run &middot; {contractId} &middot; {elapsed}s
          </div>
        </div>
      )}
    </div>
  );
}
