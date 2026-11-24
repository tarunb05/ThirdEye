import { useCallback, useEffect, useRef, useState } from "react";
import { C, F, S, sevColor } from "../design";
import { Badge, Card, Caveat, P, Section, VerdictPill } from "../ui";
import BUNDLED_SAMPLES from "../samples.json";
import { AuditStages } from "../AuditStages";
import { ArchitectureFlow, type FlowFinding } from "../ArchitectureFlow";
import { STAGES } from "../stages";
import { scrollElementIntoView } from "../motion";
import { SPECIALISTS } from "../facts";
import DEMO_CACHE from "../demo-cache.json";
import {
  API,
  getSamples,
  streamCouncil,
  type CouncilResult,
  type CouncilVuln,
  type SampleContract,
  type StreamEvent,
} from "../../lib/api";

type Preflight = {
  mode: string;
  ollama_running: boolean;
  ready: boolean;
  required_models: string[];
  present: string[];
  missing: string[];
  problems: string[];
  fixes: string[];
  judge_model: string;
  judge_present: boolean;
};

type Phase = "idle" | "routing" | "scanning" | "done" | "error";

/* Is the backend we are asking actually on this machine?
 *
 * This decides whether "no live scan" is a FAULT or just the situation. On a
 * laptop with the backend down it is a fault, and the fix is one command. On a
 * public host it is neither: that host can never run Ollama, so a red "not
 * ready" panel reports a problem nobody can act on and makes a working page
 * look broken -- which is exactly what the deployed site was doing, because
 * VITE_API_URL points it at a hosted backend that then truthfully reports
 * Ollama missing at localhost:11434.
 *
 * "/api" counts as local: that is the dev-server proxy to 127.0.0.1:8000. */
function apiIsLocal(): boolean {
  if (!API || API.startsWith("/")) return true;
  try {
    const h = new URL(API, window.location.href).hostname;
    return h === "localhost" || h === "127.0.0.1" || h === "[::1]" || h.endsWith(".localhost");
  } catch {
    return false;
  }
}

/* A previously-measured local scan, shipped in the bundle.
 *
 * Without this, the deployed site's tool page can only say "no backend" --
 * true, but it demonstrates nothing. These results were produced by
 * backend/build_demo_cache.py against real local models, and are shown ONLY
 * when a live scan is impossible, always labelled as cached. They are never
 * presented as a live run, and a cached verdict that disagrees with the
 * sample's expected answer is shown disagreeing. */
type CachedResult = {
  verdict: string;
  expected: string;
  agrees: boolean;
  latency_s: number;
  roles_routed: string[];
  specialists_errored: number;
  verdict_reason: string;
  findings: {
    type: string;
    severity: string;
    confidence: number;
    evidence_quote: string;
    description: string;
  }[];
};

const CACHE = DEMO_CACHE as unknown as {
  generated_at: string;
  models: Record<string, string>;
  results: Record<string, CachedResult>;
};

export function Tool() {
  // Seeded from the bundle, NOT fetched-then-empty.
  //
  // The sample list used to come only from /api/samples, so with no backend
  // the tool page rendered "SAMPLES · 0" and an empty picker -- which is what
  // every visitor to the deployed site would see, since a public host cannot
  // run Ollama. The same six contracts now ship in the bundle; the API call
  // still runs and replaces them when a backend IS present, so the local path
  // stays the source of truth.
  const [samples, setSamples] = useState<SampleContract[]>(
    BUNDLED_SAMPLES as unknown as SampleContract[]
  );
  const [active, setActive] = useState<SampleContract | null>(null);
  const [code, setCode] = useState("");
  const [pre, setPre] = useState<Preflight | null>(null);
  const [preLoading, setPreLoading] = useState(true);

  const [phase, setPhase] = useState<Phase>("idle");
  const [roles, setRoles] = useState<string[]>([]);
  const [done, setDone] = useState<{ role: string; found: boolean; model: string }[]>([]);
  const [result, setResult] = useState<CouncilResult | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [cached, setCached] = useState<CachedResult | null>(null);
  const abort = useRef<AbortController | null>(null);
  const timer = useRef<number | null>(null);
  /* Which pipeline stage the audit has reached. -1 = not started. */
  const [stage, setStage] = useState(-1);
  /* The findings the schematic pools, held separately from `result`/`cached`.
   * The risk column has to fill at stage 05, which is BEFORE the verdict panel
   * renders -- the pooling is the thing being shown, so it cannot wait for the
   * result card it feeds. */
  const [flowFindings, setFlowFindings] = useState<FlowFinding[]>([]);
  const walkTimers = useRef<number[]>([]);
  const flowRef = useRef<HTMLDivElement>(null);

  /* The schematic's entrance runs ~1.15s: the frame lifts in, then fourteen
   * nodes pop left to right. Starting the pipeline the instant the button is
   * pressed meant stage 01 fired while the diagram was still assembling itself,
   * so the first beat -- source into the static pre-pass -- was always missed.
   * Nothing advances until the entrance has finished. */
  const ENTRANCE_MS = 1150;
  /* How long the scroll to the panel takes before the entrance is released. */
  const SETTLE_MS = 520;
  const INTRO_MS = SETTLE_MS + ENTRANCE_MS;
  const introUntil = useRef(0);
  /* Gates the entrance animation's play-state -- see [data-flow] in index.css. */
  const [flowPlaying, setFlowPlaying] = useState(false);

  /* Run `fn` now, or at the end of the entrance if it is still playing. */
  const afterIntro = useCallback((fn: () => void) => {
    const wait = introUntil.current - Date.now();
    if (wait <= 0) fn();
    else walkTimers.current.push(window.setTimeout(fn, wait));
  }, []);

  /* Mount the schematic, put it under the reader's eye, and hold the pipeline
   * until both have settled. The panel renders below the editor, which on most
   * screens is off the bottom of the window when the button is pressed. */
  const beginRun = useCallback(() => {
    introUntil.current = Date.now() + INTRO_MS;
    setFlowPlaying(false);
    setStage(0);
    /* One frame, so the panel exists before we measure where it is. A paused
     * entrance still lays out, so this measures the right place. */
    walkTimers.current.push(
      window.setTimeout(() => {
        if (flowRef.current) scrollElementIntoView(flowRef.current);
      }, 30)
    );
    // Scroll has landed: let the pipeline draw itself in.
    walkTimers.current.push(window.setTimeout(() => setFlowPlaying(true), SETTLE_MS));
  }, [INTRO_MS]);

  const clearWalk = useCallback(() => {
    walkTimers.current.forEach((t) => window.clearTimeout(t));
    walkTimers.current = [];
  }, []);

  const refreshPreflight = useCallback(async () => {
    setPreLoading(true);
    try {
      /* Bounded, because an unbounded readiness check can hang forever and
       * then reports nothing at all. Observed on the deployed site: the
       * hosted backend was cold, the fetch never settled, and the page sat on
       * "checking for a local engine..." indefinitely -- the same class of
       * defect as a health check that answers confidently without knowing,
       * just failing in the other direction. 4s is longer than a local
       * backend ever needs and short enough that a dead one resolves to the
       * honest answer quickly. */
      const r = await fetch(`${API}/preflight`, {
        signal: AbortSignal.timeout(4000),
      });
      setPre(await r.json());
    } catch {
      setPre(null);
    } finally {
      setPreLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshPreflight();
    const seed = BUNDLED_SAMPLES as unknown as SampleContract[];
    if (seed.length) {
      setActive(seed[0]);
      setCode(seed[0].code);
    }
    getSamples()
      .then((s) => {
        if (s.length) setSamples(s);
      })
      // Keep the bundled list on failure. Replacing it with [] was the bug.
      .catch(() => undefined);
  }, [refreshPreflight]);

  useEffect(() => {
    if (phase === "routing" || phase === "scanning") {
      const t0 = Date.now();
      timer.current = window.setInterval(() => setElapsed((Date.now() - t0) / 1000), 200);
    } else if (timer.current) {
      window.clearInterval(timer.current);
      timer.current = null;
    }
    return () => {
      if (timer.current) window.clearInterval(timer.current);
    };
  }, [phase]);

  function pick(s: SampleContract) {
    clearWalk();
    setStage(-1);
    setActive(s);
    setCode(s.code);
    setCached(null);
    setResult(null);
    setDone([]);
    setRoles([]);
    setFlowFindings([]);
    setPhase("idle");
    setErr(null);
  }

  async function run() {
    abort.current?.abort();
    const ctl = new AbortController();
    abort.current = ctl;
    setPhase("routing");
    setCached(null);
    setResult(null);
    setDone([]);
    setRoles([]);
    setFlowFindings([]);
    setErr(null);
    setElapsed(0);
    clearWalk();
    beginRun(); // mount the schematic, scroll to it, hold stage 01
    try {
      await streamCouncil(
        code,
        (ev: StreamEvent) => {
          const e = ev as unknown as Record<string, unknown>;
          if (e.event === "routing") {
            /* Gated: the router can answer inside the entrance -- it is a
             * static pass, not a model call -- and an ungated handler lit the
             * router node before the reader had seen the source enter it. */
            afterIntro(() => {
              setRoles((e.roles as string[]) || []);
              setPhase("scanning");
              setStage(1); // router has chosen
              // The council is the long stage; move onto it shortly after the
              // router reports, rather than pretending it is instant.
              walkTimers.current.push(window.setTimeout(() => setStage(2), 560));
            });
          } else if (e.event === "specialist_done") {
            setDone((d) => [
              ...d,
              {
                role: String(e.role),
                found: Boolean(e.found),
                model: String(e.model || ""),
              },
            ]);
          } else if (e.event === "final") {
            /* The gate, the pooling and the verdict all happen server-side
               between the last specialist and this event, so they are shown
               completing in sequence rather than all at once. */
            const res = e.result as CouncilResult;
            const vs = (res.vulnerabilities as CouncilVuln[]) || [];
            /* Gated too: a cached-model run can return before the entrance is
             * done, and a verdict landing on a half-drawn pipeline is exactly
             * the beat this change exists to stop skipping. */
            afterIntro(() => {
              setStage(3);
              walkTimers.current.push(
                window.setTimeout(() => {
                  setFlowFindings(
                    vs.map((v) => ({
                      type: String(v.type),
                      severity: String(v.severity || "low"),
                      confidence: Number(v.confidence) || 0,
                    }))
                  );
                  setStage(4);
                }, 700)
              );
              walkTimers.current.push(window.setTimeout(() => setStage(5), 1500));
              walkTimers.current.push(
                window.setTimeout(() => {
                  setResult(res);
                  setPhase("done");
                  setStage(STAGES.length);
                }, 2200)
              );
            });
          }
        },
        { signal: ctl.signal }
      );
    } catch (e) {
      if ((e as Error).name === "AbortError") return;
      setErr((e as Error).message || String(e));
      setPhase("error");
    }
  }

  const canScanLive = Boolean(pre?.ready);
  // Only offer a cached result for UNEDITED sample code. Showing a stored
  // verdict for code the visitor has changed would be straightforwardly wrong.
  const cacheFor =
    active && code === active.code ? (CACHE.results[active.id] ?? null) : null;

  /* Recorded run: play the architecture, then reveal the stored verdict.
   *
   * The previous build dumped the cached result the instant the button was
   * clicked, which showed none of the pipeline the page spends eight hundred
   * words describing. This drives the schematic through the same sequence a
   * live run does, from the SAME recorded data: the router selects the roles it
   * actually selected, the specialists resolve to the answers they actually
   * returned, and the risk column fills to the noisy-OR of the surviving
   * confidences. Nothing is paced-for-effect except the order the specialists
   * arrive in, which a recording does not preserve.
   *
   * ~7s end to end: slow enough that a panel can watch a stage resolve, fast
   * enough to run twice in a demo. */
  const startRecorded = useCallback(() => {
    if (!cacheFor) return;
    clearWalk();
    setResult(null);
    setCached(null);
    setErr(null);
    setDone([]);
    setFlowFindings([]);
    setRoles([]);
    setElapsed(0);
    setPhase("scanning");
    beginRun();

    /* Every beat sits past the entrance, so the replay starts on a pipeline
     * that is fully drawn and in frame rather than part-way through arriving. */
    const at = (ms: number, fn: () => void) =>
      walkTimers.current.push(window.setTimeout(fn, INTRO_MS + ms));

    const roleList = cacheFor.roles_routed;
    const findings: FlowFinding[] = cacheFor.findings.map((f) => ({
      type: f.type,
      severity: f.severity,
      confidence: f.confidence,
    }));
    /* A specialist "flagged" if it owns a surviving finding. The gate's own
     * drops cannot be recovered from a recording -- what it dropped is not in
     * the stored result -- so the schematic shows the drops it can prove and
     * claims no others. */
    const flaggedRoles = new Set(findings.map((f) => f.type));

    /* Which model answered for a role, in the recording.
     *
     * The cache stores one model per FAMILY (coder / logic / dos), not per
     * role, because that is how the pipeline assigns them: the code roles share
     * a coder, business_logic and the oracle roles share a logic model, dos_gas
     * gets its own. Labelling all four with the coder -- which the first cut of
     * this did -- told the reader business_logic ran on qwen when it ran on
     * llama. */
    const recordedModel = (role: string) => {
      const cfg = SPECIALISTS.find((s2) => s2.role === role)?.model || "";
      const fam = cfg.startsWith("qwen")
        ? "coder"
        : cfg.startsWith("llama")
          ? "logic"
          : cfg.startsWith("gemma")
            ? "dos"
            : "";
      return (fam && CACHE.models[fam]) || cfg;
    };

    // 01 static -> 02 router
    at(800, () => {
      setStage(1);
      setRoles(roleList);
    });
    // 03 the council, one specialist at a time
    const COUNCIL_AT = 1600;
    const PER = 460;
    at(COUNCIL_AT, () => setStage(2));
    roleList.forEach((r, i) => {
      at(COUNCIL_AT + PER * (i + 1), () =>
        setDone((d) => [
          ...d,
          { role: r, found: flaggedRoles.has(r), model: recordedModel(r) },
        ])
      );
    });
    const councilEnd = COUNCIL_AT + PER * (roleList.length + 1);
    // 04 gate -> 05 pooling -> 06 verdict
    at(councilEnd, () => setStage(3));
    at(councilEnd + 900, () => {
      setFlowFindings(findings);
      setStage(4);
    });
    at(councilEnd + 1900, () => setStage(5));
    at(councilEnd + 2700, () => {
      setCached(cacheFor);
      setPhase("done");
      setStage(STAGES.length);
    });
  }, [cacheFor, clearWalk, beginRun]);

  useEffect(() => () => clearWalk(), [clearWalk]);

  const scanning = phase === "routing" || phase === "scanning";
  const vulns: CouncilVuln[] = (result?.vulnerabilities as CouncilVuln[]) || [];

  return (
    <div style={S.page}>
      <div style={{ paddingTop: 44 }}>
        <div style={S.eyebrow}>Live tool</div>
        <h1 style={S.h1}>Scan a contract</h1>
        <P>
          This runs the real pipeline on your machine — static pre-pass, router,
          model-diverse council, evidence gate, verdict. No API key, no network
          call, and the source never leaves the laptop. Pick a sample or paste
          your own Solidity.
        </P>
      </div>

      <Preflight pre={pre} loading={preLoading} onRetry={refreshPreflight} />

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(240px, 300px) 1fr",
          gap: 20,
          marginTop: 28,
          alignItems: "start",
        }}
      >
        {/* ── sample picker ── */}
        <div style={{ display: "grid", gap: 8 }}>
          <div style={{ ...S.eyebrow, margin: "0 0 4px" }}>
            Samples · {samples.length}
          </div>
          {samples.map((s) => {
            const on = active?.id === s.id;
            const safe = s.expected === "GO";
            return (
              <button
                key={s.id}
                onClick={() => pick(s)}
                style={{
                  textAlign: "left",
                  background: on ? C.panelHi : C.panel,
                  border: `1px solid ${on ? C.accentDim : C.line}`,
                  borderRadius: 8,
                  padding: "10px 12px",
                  cursor: "pointer",
                  color: C.ink,
                  font: "inherit",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span
                    style={{
                      width: 6,
                      height: 6,
                      borderRadius: 99,
                      background: safe ? C.go : C.nogo,
                      flexShrink: 0,
                    }}
                  />
                  <span style={{ fontSize: 13.5, fontWeight: 500 }}>{s.name}</span>
                </div>
                <div
                  style={{
                    fontFamily: F.mono,
                    fontSize: 11,
                    color: C.inkDim,
                    marginTop: 4,
                    paddingLeft: 14,
                  }}
                >
                  {s.category}
                </div>
              </button>
            );
          })}
        </div>

        {/* ── editor + run ── */}
        <div>
          {active && (
            <Card style={{ marginBottom: 14 }}>
              <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
                <strong style={{ fontSize: 15, color: C.ink }}>{active.name}</strong>
                <Badge
                  fg={active.expected === "GO" ? C.go : C.nogo}
                  bg={active.expected === "GO" ? C.goGhost : C.nogoGhost}
                >
                  expected {active.expected}
                </Badge>
              </div>
              <P style={{ margin: "10px 0 0", fontSize: 14 }}>{active.blurb}</P>
            </Card>
          )}

          <textarea
            value={code}
            onChange={(e) => setCode(e.target.value)}
            spellCheck={false}
            style={{
              ...S.code,
              width: "100%",
              minHeight: 240,
              resize: "vertical",
              display: "block",
            }}
          />

          <div style={{ display: "flex", gap: 12, alignItems: "center", marginTop: 12, flexWrap: "wrap" }}>
            {/* ONE button, one label.
             *
             * It used to read "Run scan" with a backend and "Show cached
             * result" without one, which made the second path look like a
             * consolation prize for a broken page. Both run the same six
             * stages and end on the same verdict panel; whether the models are
             * executing now or the run was recorded is reported where it
             * belongs -- on the result, with its timestamp. */}
            <button
              onClick={
                scanning
                  ? () => {
                      abort.current?.abort();
                      clearWalk();
                      setPhase("idle");
                      setStage(-1);
                    }
                  : canScanLive
                    ? run
                    : startRecorded
              }
              disabled={!code.trim() || (!canScanLive && !cacheFor && !scanning)}
              title={
                canScanLive
                  ? "Run the full pipeline on this contract now"
                  : cacheFor
                    ? "Replay this contract's audit stage by stage"
                    : "This code has been edited and no backend is running, so there is nothing to audit it with"
              }
              style={{
                background: scanning ? "transparent" : C.accent,
                color: scanning ? C.inkMid : C.bg,
                border: `1px solid ${scanning ? C.line : C.accent}`,
                borderRadius: 7,
                padding: "10px 20px",
                fontFamily: F.sans,
                fontSize: 14,
                fontWeight: 600,
                cursor:
                  code.trim() && (canScanLive || cacheFor || scanning)
                    ? "pointer"
                    : "not-allowed",
                opacity:
                  code.trim() && (canScanLive || cacheFor || scanning) ? 1 : 0.45,
              }}
            >
              {scanning ? "Stop" : "Start audit"}
            </button>

            {scanning && (
              <span style={{ fontFamily: F.mono, fontSize: 13, color: C.inkMid }}>
                {stage >= 0 && stage < STAGES.length
                  ? STAGES[stage].name.toLowerCase()
                  : "running"}
                {canScanLive ? ` · ${elapsed.toFixed(1)}s` : ""}
              </span>
            )}

            {!canScanLive && !preLoading && !cacheFor && (
              <span style={{ fontFamily: F.sans, fontSize: 13, color: C.inkDim }}>
                Edited code needs a running backend — start it to audit this.
              </span>
            )}
          </div>

        </div>
      </div>

      {/* Everything below runs the FULL page width, not the editor
          column. The schematic is 980 units of pipeline; squeezed into a
          ~670px column it drew its model names at under 6px, which is a
          diagram you cannot read. The findings cards and their evidence
          quotes want the width for the same reason. */}
      {/* ── the architecture, playing ── */}
      {stage >= 0 && (
        <div
          ref={flowRef}
          data-flow={flowPlaying ? "play" : "hold"}
          style={{ marginTop: 18, display: "grid", gap: 14 }}
        >
          <ArchitectureFlow
            stage={stage}
            roles={roles}
            done={done}
            findings={flowFindings}
            verdict={result?.final_verdict ?? cached?.verdict ?? null}
            complete={stage >= STAGES.length}
          />
          {/* The schematic shows the mechanism; the rail names the stages.
              Both, because a reader who has not read the how-it-works page
              needs the words, and one who has needs the machine. */}
          <AuditStages active={stage} complete={stage >= STAGES.length} />
        </div>
      )}

      {/* Room to scroll against.
       *
       * The schematic is the last thing on the page while an audit is running,
       * so scrolling it to the top of the viewport is impossible -- the browser
       * clamps at the document end and leaves it sitting at the bottom edge.
       * Measured: target 878px, actual 334px, panel still 631px down the
       * window. This spacer exists only for the length of the run; by the time
       * it goes, the result section below has taken its place. */}
      {stage >= 0 && stage < STAGES.length && (
        <div aria-hidden="true" style={{ height: "70vh" }} />
      )}

      {/* expected scan cost, so nobody thinks it hung */}
      {scanning && canScanLive && (
        <P style={{ fontSize: 13, color: C.inkDim, marginTop: 10 }}>
          On a 4&nbsp;GB laptop GPU a scan measured 55–66&nbsp;s for a small
          contract. The models load one at a time, so the first call of a
          session is the slowest.
        </P>
      )}

      {err && (
        <Card style={{ marginTop: 14, borderColor: C.nogo }}>
          <div style={{ ...S.h3, color: C.nogo }}>Scan failed</div>
          <code style={{ fontFamily: F.mono, fontSize: 12.5, color: C.inkMid }}>{err}</code>
        </Card>
      )}

      {/* ── live specialist progress ── */}
      {(roles.length > 0 || done.length > 0) && (
        <Section title="Specialists" id="specialists">
          <P style={{ fontSize: 14 }}>
            The router fired {roles.length} of 8 specialists for this
            contract. Each returns a finding only if it can quote a line of
            the submitted source.
          </P>
          <div style={{ display: "grid", gap: 7 }}>
            {roles.map((r) => {
              const d = done.find((x) => x.role === r);
              return (
                <div
                  key={r}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                    padding: "8px 12px",
                    background: C.panel,
                    border: `1px solid ${C.line}`,
                    borderRadius: 7,
                  }}
                >
                  <span
                    style={{
                      width: 7,
                      height: 7,
                      borderRadius: 99,
                      background: !d ? C.inkDim : d.found ? C.nogo : C.go,
                      flexShrink: 0,
                    }}
                  />
                  <span style={{ fontFamily: F.mono, fontSize: 12.5, color: C.ink }}>
                    {r}
                  </span>
                  <span style={{ marginLeft: "auto", fontFamily: F.mono, fontSize: 11, color: C.inkDim }}>
                    {!d ? "waiting" : d.found ? "flagged" : "clean"}
                    {d?.model ? ` · ${d.model}` : ""}
                  </span>
                </div>
              );
            })}
          </div>
        </Section>
      )}

      {/* ── recorded verdict (shown when the models cannot run here) ── */}
      {cached && !result && (
        <Section title="Audit result">
          <Card style={{ borderColor: C.lineHi }}>
            <div
              style={{
                display: "flex",
                gap: 10,
                alignItems: "center",
                flexWrap: "wrap",
                marginBottom: 10,
              }}
            >
              {/* Provenance, stated as instrumentation rather than as an
                  apology. A live run reads "just now"; this one carries
                  the date it was measured, which is the honest difference
                  and the only one a reader needs. */}
              <span style={{ fontFamily: F.mono, fontSize: 12, color: C.inkDim }}>
                recorded run · {CACHE.generated_at.slice(0, 10)} · coder{" "}
                {CACHE.models.coder} · {cached.latency_s}s ·{" "}
                {cached.roles_routed.length} specialists
              </span>
            </div>

            <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
              <VerdictPill verdict={cached.verdict} />
              <span style={{ fontFamily: F.sans, fontSize: 13.5, color: C.inkMid }}>
                expected <strong style={{ color: C.ink }}>{cached.expected}</strong> ·{" "}
                {cached.agrees ? (
                  <span style={{ color: C.go }}>match</span>
                ) : (
                  <span style={{ color: C.nogo }}>mismatch</span>
                )}
              </span>
            </div>

            {/* A mismatch gets the same explanation on the recorded path
                that it gets on the live one. It did not -- and the deployed
                site only HAS the recorded path, so every visitor who picked
                Safe Vault saw "expected GO - mismatch" with nothing telling
                them that a false alarm on a safe contract is this project's
                headline measurement rather than a broken demo. */}
            {!cached.agrees && (
              <Caveat title="This is a disagreement, and it is not hidden">
                The pipeline returned{" "}
                <strong style={{ color: C.ink }}>{cached.verdict}</strong> on
                a contract that is{" "}
                <strong style={{ color: C.ink }}>{cached.expected}</strong>.
                On the full benchmark it raises a false alarm on{" "}
                <strong style={{ color: C.ink }}>45.9%</strong> of safe
                contracts — the schematic above shows how this one happened,
                with a single specialist returning confidence high enough to
                carry the pooled risk past τ on its own. That floor is
                structural, and the findings page explains why.
              </Caveat>
            )}

            {cached.verdict_reason && (
              <P style={{ fontSize: 14, marginTop: 12 }}>{cached.verdict_reason}</P>
            )}

            {cached.findings.length > 0 && (
              <div style={{ display: "grid", gap: 10, marginTop: 12 }}>
                {cached.findings.map((f, i) => (
                  <div
                    key={i}
                    style={{
                      background: C.bgAlt,
                      border: `1px solid ${C.line}`,
                      borderRadius: 8,
                      padding: 14,
                    }}
                  >
                    <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
                      <Badge fg={sevColor(f.severity)} bg={`${sevColor(f.severity)}22`}>
                        {f.severity}
                      </Badge>
                      <strong style={{ fontSize: 14, color: C.ink }}>{f.type}</strong>
                      <span style={{ fontFamily: F.mono, fontSize: 12, color: C.inkDim }}>
                        confidence {f.confidence}
                      </span>
                    </div>
                    {f.evidence_quote && (
                      <pre style={{ ...S.code, marginTop: 10, marginBottom: 0 }}>
                        {f.evidence_quote}
                      </pre>
                    )}
                  </div>
                ))}
              </div>
            )}
          </Card>

        </Section>
      )}

      {/* ── verdict ── */}
      {result && (
        <Section title="Verdict">
          <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
            <VerdictPill verdict={result.final_verdict} />
            {active && (
              <span style={{ fontFamily: F.sans, fontSize: 13.5, color: C.inkMid }}>
                expected <strong style={{ color: C.ink }}>{active.expected}</strong> ·{" "}
                {result.final_verdict === active.expected ? (
                  <span style={{ color: C.go }}>match</span>
                ) : (
                  <span style={{ color: C.nogo }}>mismatch</span>
                )}
              </span>
            )}
          </div>

          {active && result.final_verdict !== active.expected && (
            <Caveat title="This is a disagreement, and it is not hidden">
              The tool returned a different verdict than this sample
              expects. On the full benchmark it raises a false alarm on{" "}
              <strong style={{ color: C.ink }}>45.9%</strong> of safe
              contracts, so a wrong call here is the measured behaviour
              rather than a surprise. The findings page explains why that
              floor is structural.
            </Caveat>
          )}

          {result.verdict_reason && (
            <P style={{ fontSize: 14, marginTop: 12 }}>{result.verdict_reason}</P>
          )}

          {vulns.length > 0 && (
            <div style={{ display: "grid", gap: 10, marginTop: 14 }}>
              {vulns.map((v, i) => (
                <Card key={i}>
                  <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
                    <Badge fg={sevColor(v.severity)} bg={`${sevColor(v.severity)}22`}>
                      {v.severity}
                    </Badge>
                    <strong style={{ fontSize: 14, color: C.ink }}>{v.type}</strong>
                    <span style={{ fontFamily: F.mono, fontSize: 12, color: C.inkDim }}>
                      confidence {v.confidence}
                    </span>
                  </div>
                  {v.evidence_quote && (
                    <pre style={{ ...S.code, marginTop: 10, marginBottom: 0 }}>
                      {v.evidence_quote}
                    </pre>
                  )}
                  <P style={{ fontSize: 13.5, margin: "10px 0 0" }}>{v.description}</P>
                </Card>
              ))}
            </div>
          )}
        </Section>
      )}
    </div>
  );
}

/* ── preflight banner: the demo's honesty layer ──────────────────────────── */

function Preflight({
  pre,
  loading,
  onRetry,
}: {
  pre: Preflight | null;
  loading: boolean;
  onRetry: () => void;
}) {
  const local = apiIsLocal();

  if (loading) {
    return (
      <Card flat style={{ marginTop: 24 }}>
        <span style={{ fontFamily: F.mono, fontSize: 13, color: C.inkDim }}>
          checking for a local engine…
        </span>
      </Card>
    );
  }

  /* Remote or unreachable backend: one quiet line, no alarm. The audit button
   * still works -- it replays a recorded run -- so there is nothing here for
   * the reader to fix and nothing to warn them about. */
  if (!pre || !pre.ready) {
    if (!local) {
      return (
        <div
          style={{
            marginTop: 24,
            display: "flex",
            gap: 10,
            alignItems: "baseline",
            flexWrap: "wrap",
            fontFamily: F.sans,
            fontSize: 13.5,
            color: C.inkDim,
          }}
        >
          <Badge>local-only</Badge>
          <span>
            The models run on the machine viewing this page, so a live scan
            needs ThirdEye started locally. Start audit replays a recorded run
            of the same pipeline.
          </span>
        </div>
      );
    }
  }

  /* From here: the backend IS local, so anything wrong is actionable. */
  if (!pre) {
    return (
      <Card flat style={{ marginTop: 24, borderColor: C.lineHi }}>
        <div style={{ ...S.h3 }}>Backend not reachable</div>
        <P style={{ fontSize: 14, margin: "6px 0 10px" }}>
          Every other page works without it, but a live scan needs the ThirdEye
          backend on this machine. Start it and retry:
        </P>
        <pre style={S.code}>
{`cd backend
uvicorn main:app --reload --port 8000`}
        </pre>
        <RetryButton onRetry={onRetry} />
      </Card>
    );
  }

  const ok = pre.ready;
  return (
    <Card
      flat
      style={{
        marginTop: 24,
        borderColor: ok ? `${C.go}55` : `${C.nogo}55`,
        background: ok ? C.goGhost : C.nogoGhost,
      }}
    >
      <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
        <span
          style={{ width: 8, height: 8, borderRadius: 99, background: ok ? C.go : C.nogo }}
        />
        <strong style={{ fontSize: 14.5, color: C.ink }}>
          {ok ? "Ready to scan locally" : "Engine not ready"}
        </strong>
        <Badge>{pre.mode}</Badge>
        {pre.required_models.map((m) => (
          <Badge
            key={m}
            fg={pre.present.includes(m) ? C.go : C.nogo}
            bg={pre.present.includes(m) ? C.goGhost : C.nogoGhost}
          >
            {m}
          </Badge>
        ))}
      </div>

      {pre.problems.length > 0 && (
        <div style={{ marginTop: 12 }}>
          {pre.problems.map((p, i) => (
            <P key={i} style={{ fontSize: 13.5, margin: "0 0 8px" }}>
              {p}
            </P>
          ))}
          {pre.fixes.length > 0 && <pre style={S.code}>{pre.fixes.join("\n")}</pre>}
          <RetryButton onRetry={onRetry} />
        </div>
      )}

      {ok && (
        <P style={{ fontSize: 13.5, margin: "10px 0 0" }}>
          Models are checked by name, not counted. That distinction cost this
          project a wasted evaluation run once — a healthy-looking Ollama was
          serving a different model store, and every call to the missing model
          failed silently.
        </P>
      )}
    </Card>
  );
}

function RetryButton({ onRetry }: { onRetry: () => void }) {
  return (
    <button
      onClick={onRetry}
      style={{
        marginTop: 10,
        background: "transparent",
        color: C.accent,
        border: `1px solid ${C.accentDim}`,
        borderRadius: 6,
        padding: "6px 14px",
        fontFamily: F.sans,
        fontSize: 13,
        cursor: "pointer",
      }}
    >
      Check again
    </button>
  );
}
