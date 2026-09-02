import { useEffect, useRef, useState, type ChangeEvent } from "react";
import {
  streamCouncil,
  createSession,
  getSamples,
  type CouncilResult,
  type SampleContract,
  type StreamEvent,
  type User,
} from "../lib/api";
import { SPECIALIST_ROLES } from "../lib/theme";
import type { RoutingInfo } from "../lib/api";
import { SpecialistCard, type SpecialistState } from "../components/analyze/SpecialistCard";
import { VerdictBanner, StatsStrip, VulnList, PrecedentPanel, RoutingSummary } from "../components/analyze/ResultPanel";
import { SectionLabel, Spinner, Pill } from "../components/ui/primitives";
import { BoltIcon, UploadIcon, EyeIcon, ScanIcon, FlowIcon, ChartIcon, ArrowRightIcon } from "../components/ui/icons";
import type { Tab } from "../components/Layout";

type Phase = "idle" | "running" | "done" | "error";

function initialStates(): Record<string, SpecialistState> {
  const m: Record<string, SpecialistState> = {};
  for (const r of SPECIALIST_ROLES) m[r] = { role: r, status: "queued" };
  return m;
}

export function Analyze({
  user,
  onNavigate,
  onScanComplete,
}: {
  user: User;
  onNavigate?: (t: Tab) => void;
  onScanComplete?: () => void;
}) {
  const [code, setCode] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [error, setError] = useState("");
  const [tier, setTier] = useState<string>("");
  const [specs, setSpecs] = useState<Record<string, SpecialistState>>(initialStates);
  const [result, setResult] = useState<CouncilResult | null>(null);
  const [activeSample, setActiveSample] = useState<string | null>(null);
  // Static-router selection (which specialists actually run) + arbitration step.
  const [routing, setRouting] = useState<RoutingInfo | null>(null);
  const [arbitrating, setArbitrating] = useState<{ count: number } | null>(null);

  const [samples, setSamples] = useState<SampleContract[]>([]);
  const [samplesErr, setSamplesErr] = useState(false);

  const fileRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const editorRef = useRef<HTMLElement>(null);
  const sessionRef = useRef<number | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const order = SPECIALIST_ROLES as readonly string[];
  const list = order.map((r) => specs[r]);
  // Progress is driven by the ROUTED subset — the router may pick fewer than 8.
  const selectedRoles = routing?.roles?.length ? routing.roles : (order as string[]);
  const activeList = list.filter((s) => s.status !== "skipped");
  const doneCount = activeList.filter((s) => s.status === "done").length;
  const totalActive = Math.max(activeList.length, selectedRoles.length, 1);
  const running = phase === "running";

  useEffect(() => {
    let alive = true;
    getSamples()
      .then((s) => alive && setSamples(s))
      .catch(() => alive && setSamplesErr(true));
    return () => {
      alive = false;
    };
  }, []);

  // Best-effort session — anonymous scans still work if this fails.
  async function ensureSession(): Promise<number | null> {
    if (sessionRef.current != null) return sessionRef.current;
    try {
      const s = await createSession(user.token);
      sessionRef.current = s.id;
      return s.id;
    } catch {
      return null;
    }
  }

  function reset() {
    setResult(null);
    setError("");
    setTier("");
    setRouting(null);
    setArbitrating(null);
    setSpecs(initialStates());
  }

  function focusEditor() {
    editorRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    setTimeout(() => textareaRef.current?.focus(), 350);
  }

  async function run(srcOverride?: string) {
    const trimmed = (srcOverride ?? code).trim();
    if (trimmed.length < 10 || running) return;
    reset();
    setPhase("running");
    try {
      const sid = await ensureSession();
      await runLive(trimmed, sid);
      setPhase("done");
      onScanComplete?.();
    } catch (e) {
      if ((e as Error).name === "AbortError") {
        setPhase("idle");
        return;
      }
      setError(e instanceof Error ? e.message : "Analysis failed");
      setPhase("error");
    }
  }

  function applyFinal(r: CouncilResult) {
    setResult(r);
    setArbitrating(null);
    // Backfill routing from the result if the stream didn't emit a routing event.
    if (r.routing?.roles?.length) {
      setRouting((prev) => prev ?? r.routing!);
      const selected = new Set(r.routing.roles);
      setSpecs((prev) => {
        const next = { ...prev };
        for (const role of SPECIALIST_ROLES) {
          if (!selected.has(role) && next[role].status !== "done") {
            next[role] = { ...next[role], role, status: "skipped", skip_reason: r.routing!.trace?.[role] };
          }
        }
        return next;
      });
    }
    if (r.council_detail?.length) {
      setSpecs((prev) => {
        const next = { ...prev };
        for (const d of r.council_detail!) {
          next[d.role] = {
            role: d.role,
            provider: d.provider,
            model: d.model,
            status: "done",
            found: d.found,
            confidence: d.confidence,
            severity: d.severity,
            evidence_quote: d.evidence_quote,
          };
        }
        return next;
      });
    }
  }

  async function runLive(trimmed: string, sid: number | null) {
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    await streamCouncil(
      trimmed,
      (ev: StreamEvent) => {
        if (ev.event === "routing") {
          // Static/heuristic router picked the subset of specialists to run.
          const r = ev as Extract<StreamEvent, { event: "routing" }>;
          const selected = new Set(r.roles ?? []);
          setRouting({ roles: r.roles ?? [], trace: r.trace, static_used: r.static_used });
          setSpecs((prev) => {
            const next = { ...prev };
            for (const role of SPECIALIST_ROLES) {
              if (!selected.has(role)) {
                next[role] = {
                  ...next[role],
                  role,
                  status: "skipped",
                  skip_reason: r.trace?.[role],
                };
              }
            }
            return next;
          });
        } else if (ev.event === "arbitrating") {
          // Cross-examination / arbitration step in the pipeline.
          const a = ev as Extract<StreamEvent, { event: "arbitrating" }>;
          setArbitrating({ count: a.count });
        } else if (ev.event === "start") {
          const start = ev as Extract<StreamEvent, { event: "start" }>;
          setTier(start.tier);
          setSpecs((prev) => {
            const next = { ...prev };
            for (const sp of start.specialists ?? []) {
              next[sp.role] = {
                ...(next[sp.role] || { role: sp.role }),
                role: sp.role,
                provider: sp.provider,
                model: sp.model,
                status: "analyzing",
              };
            }
            // Any specialist not already skipped by the router and still queued
            // is now analyzing. Never flip a "skipped" card back on.
            for (const r of SPECIALIST_ROLES) {
              if (next[r].status === "queued") next[r] = { ...next[r], status: "analyzing" };
            }
            return next;
          });
        } else if (ev.event === "specialist_done") {
          const d = ev as Extract<StreamEvent, { event: "specialist_done" }>;
          setSpecs((prev) => ({
            ...prev,
            [d.role]: {
              role: d.role,
              provider: d.provider,
              model: d.model,
              status: "done",
              found: d.found,
              confidence: d.confidence,
              severity: d.severity,
              evidence_quote: d.evidence_quote,
              llm_error: d.llm_error,
            },
          }));
        } else if (ev.event === "final") {
          const f = ev as Extract<StreamEvent, { event: "final" }>;
          applyFinal(f.result);
        }
      },
      { sessionId: sid, signal: ctrl.signal }
    );
  }

  function cancel() {
    abortRef.current?.abort();
  }

  function handleFile(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setActiveSample(null);
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === "string") {
        setCode(reader.result);
        focusEditor();
      }
    };
    reader.readAsText(file);
    e.target.value = "";
  }

  function loadSample(s: SampleContract) {
    setActiveSample(s.id);
    setCode(s.code);
    focusEditor();
  }

  return (
    <div className="px-4 sm:px-6 py-6">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Hero header */}
        <header className="relative overflow-hidden rounded-2xl border border-[#D8D3C7] bg-[#FFFFFF]">
          <div className="bg-grid opacity-40 absolute inset-0" aria-hidden="true" />
          <div
            className="absolute -right-24 -top-28 w-96 h-96 rounded-full blur-3xl"
            style={{ background: "radial-gradient(circle, rgba(44,74,107,0.08), transparent 70%)" }}
            aria-hidden="true"
          />
          <div className="relative px-6 sm:px-8 py-7 flex items-center gap-5">
            <div className="text-[#1F6FB2] flex-shrink-0">
              <ScanIcon size={34} />
            </div>
            <div className="min-w-0">
              <h2 className="text-xl font-bold text-[#16150F] tracking-tight leading-tight">
                Audit a contract with the Third-Eye council.
              </h2>
              <p className="text-[13px] text-[#6B675C] mt-1.5 max-w-2xl leading-relaxed">
                Eight model-diverse specialists examine your Solidity live. When they finish,
                <span className="text-[#6B675C]"> Raven </span>
                delivers a single, defensible verdict.
              </p>
            </div>
          </div>
        </header>

        {/* Three ways to provide a contract */}
        <div className="grid sm:grid-cols-3 gap-3">
          <ProvideCard
            icon={<ScanIcon size={16} />}
            title="Paste source"
            body="Drop a Solidity contract into the editor below."
            onClick={focusEditor}
          />
          <ProvideCard
            icon={<UploadIcon size={16} />}
            title="Upload .sol"
            body="Load a file straight from your machine."
            onClick={() => fileRef.current?.click()}
          />
          <ProvideCard
            icon={<EyeIcon size={16} />}
            title="Try a sample"
            body="No contract handy? Pick one from below."
            onClick={() =>
              document.getElementById("samples")?.scrollIntoView({ behavior: "smooth", block: "start" })
            }
          />
        </div>

        {/* Code editor */}
        <section
          ref={editorRef}
          className="rounded-xl border border-[#D8D3C7] bg-[#FFFFFF] overflow-hidden focus-within:border-[#D8D3C7] transition-colors scroll-mt-4"
        >
          <div className="flex items-center gap-2 px-4 py-2.5 border-b border-[#D8D3C7]">
            <span className="text-[10px] uppercase tracking-[0.16em] text-[#6B675C]">Solidity Source</span>
            {activeSample && <Pill tone="accent">sample loaded</Pill>}
            <input ref={fileRef} type="file" className="hidden" accept=".sol,.vy,.txt" onChange={handleFile} />
            <div className="ml-auto flex items-center gap-3">
              {code && (
                <button
                  type="button"
                  onClick={() => {
                    setCode("");
                    setActiveSample(null);
                  }}
                  className="text-[10px] text-[#5E6B78] hover:text-[#3A372E] transition-colors"
                >
                  Clear
                </button>
              )}
              <button
                type="button"
                onClick={() => fileRef.current?.click()}
                className="text-[10px] text-[#6B675C] hover:text-[#1F6FB2] transition-colors flex items-center gap-1"
              >
                <UploadIcon size={12} /> Upload .sol
              </button>
            </div>
          </div>
          <textarea
            ref={textareaRef}
            value={code}
            onChange={(e) => {
              setCode(e.target.value);
              setActiveSample(null);
            }}
            disabled={running}
            spellCheck={false}
            rows={12}
            placeholder={"// Paste your Solidity contract here\npragma solidity ^0.8.0;\n\ncontract MyContract {\n  ...\n}"}
            className="w-full bg-transparent outline-none resize-y text-[12px] font-mono leading-relaxed text-[#3A372E] placeholder:text-[#5E6B78] px-4 py-3 min-h-[220px]"
          />
          <div className="flex items-center gap-3 px-4 py-3 border-t border-[#D8D3C7]">
            <span className="text-[10px] font-mono text-[#5E6B78]">{code.length} chars</span>
            {tier && <Pill tone="accent">{tier} tier</Pill>}
            {running ? (
              <button
                onClick={cancel}
                className="ml-auto inline-flex items-center gap-2 px-4 py-2 rounded-lg text-[12px] font-semibold border border-[#D8D3C7] text-[#3A372E] hover:bg-[#F1EEE6] transition-colors"
              >
                <Spinner size={13} /> Cancel
              </button>
            ) : (
              <button
                onClick={() => run()}
                disabled={code.trim().length < 10}
                className="ml-auto inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-[12.5px] font-semibold bg-[#16150F] hover:bg-[#3A372E] text-[#F7F5F0] shadow-[0_8px_24px_-10px_rgba(44,74,107,0.08)] transition-colors disabled:opacity-25 disabled:cursor-not-allowed disabled:shadow-none"
              >
                <BoltIcon size={14} />
                Run Third-Eye
              </button>
            )}
          </div>
        </section>

        {error && (
          <div className="rounded-lg border border-rose-500/30 bg-rose-500/[0.08] px-4 py-3 text-[12px] text-rose-200">
            {error}
          </div>
        )}

        {/* Static routing story — the router picked N of 8 specialists */}
        {(routing || running || phase === "done") && (routing?.roles?.length ?? 0) > 0 && (
          <div className="rounded-xl border border-[#D8D3C7] bg-[#EDE9DF] px-5 py-4 animate-fade-in">
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
              <span className="inline-flex items-center gap-1.5 text-[9px] font-mono font-bold uppercase tracking-[0.14em] text-[#1F6FB2] bg-[#EDE9DF] ring-1 ring-[#D8D3C7] px-2 py-1 rounded-md">
                <FlowIcon size={11} /> Static routing
              </span>
              <span className="text-[13px] font-medium text-[#16150F]">
                Router selected{" "}
                <span className="text-[#1F6FB2] font-semibold tabular-nums">
                  {routing!.roles.length} of {order.length}
                </span>{" "}
                specialists
                {routing!.static_used === false && (
                  <span className="text-[#5E6B78]"> (fallback — full council)</span>
                )}
              </span>
            </div>
            <p className="text-[11px] text-[#5E6B78] leading-relaxed mt-1.5">
              A heuristic pre-scan routes the contract to only the relevant attack-surface specialists —
              the rest are skipped, shown greyed below.
            </p>
          </div>
        )}

        {/* Live progress */}
        {(running || phase === "done") && (
          <div className="rounded-xl border border-[#D8D3C7] bg-[#FFFFFF] px-5 py-4 animate-fade-in">
            <div className="flex items-center gap-3">
              <span
                className={`w-2 h-2 rounded-full ${running ? "bg-[#16150F] animate-pulse-glow" : "bg-emerald-400"}`}
              />
              <span className="text-[13px] font-medium text-[#16150F]">
                {arbitrating
                  ? "Arbitration — Raven cross-examining every claim against the source…"
                  : running
                  ? "Council in session — specialists examining attack surfaces…"
                  : "Council adjourned."}
              </span>
              <span className="ml-auto text-[11px] font-mono text-[#6B675C] tabular-nums">
                {doneCount} / {totalActive}
              </span>
            </div>
            <div className="mt-3 h-1.5 rounded-full bg-[#F1EEE6] overflow-hidden">
              <div
                className="h-full bg-[#1F6FB2] rounded-full transition-all duration-500"
                style={{ width: `${Math.min(100, (doneCount / totalActive) * 100)}%` }}
              />
            </div>

            {/* Arbitration / cross-examination step */}
            {arbitrating && (
              <div className="mt-3 flex items-center gap-2.5 rounded-lg bg-[#EDE9DF] ring-1 ring-[#D8D3C7] px-3 py-2 animate-fade-in">
                <Spinner size={13} />
                <span className="text-[11.5px] text-[#1F6FB2]">
                  Evidence-anchored arbitration on{" "}
                  <span className="font-mono font-semibold tabular-nums">{arbitrating.count}</span>{" "}
                  candidate {arbitrating.count === 1 ? "finding" : "findings"} — dropping anything not grounded in the code.
                </span>
              </div>
            )}
          </div>
        )}

        {/* Specialist grid */}
        {(running || phase === "done") && (
          <section aria-label="Specialist council">
            <SectionLabel count={routing?.roles?.length ?? order.length}>The Council</SectionLabel>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {list.map((s, i) => (
                <SpecialistCard key={s.role} s={s} index={i} />
              ))}
            </div>
          </section>
        )}

        {/* Final result */}
        {phase === "done" && result && (
          <div className="space-y-5 animate-fade-in pt-1">
            <VerdictBanner result={result} />
            {result.stats && <StatsStrip stats={result.stats} />}
            <RoutingSummary routing={result.routing ?? routing ?? undefined} />
            <VulnList
              vulnerabilities={result.vulnerabilities ?? []}
              inconclusive={result.final_verdict === "INCONCLUSIVE"}
            />
            <PrecedentPanel exploits={result.similar_exploits} />
            {result.summary && (
              <section className="rounded-xl border border-[#D8D3C7] bg-[#FFFFFF] px-5 py-4">
                <SectionLabel>Summary</SectionLabel>
                <p className="text-[13px] text-[#6B675C] leading-relaxed">{result.summary}</p>
              </section>
            )}
          </div>
        )}

        {/* Sample contracts */}
        <section id="samples" className="scroll-mt-4 pt-1">
          <SectionLabel count={samples.length || undefined}>Sample contracts — try it instantly</SectionLabel>
          {samplesErr ? (
            <div className="rounded-xl border border-[#D8D3C7] bg-[#F1EEE6] px-5 py-6 text-center text-[12px] text-[#5E6B78]">
              Couldn't load samples right now — paste or upload a contract above to get started.
            </div>
          ) : samples.length === 0 ? (
            <div className="rounded-xl border border-[#D8D3C7] bg-[#F1EEE6] px-5 py-6 text-center text-[12px] text-[#5E6B78]">
              <Spinner /> <span className="ml-2 align-middle">Loading samples…</span>
            </div>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {samples.map((s) => (
                <SampleCard
                  key={s.id}
                  s={s}
                  active={activeSample === s.id}
                  disabled={running}
                  onLoad={() => loadSample(s)}
                  onRun={() => {
                    setActiveSample(s.id);
                    setCode(s.code);
                    focusEditor();
                    run(s.code);
                  }}
                />
              ))}
            </div>
          )}
        </section>

        {/* Idle explainer (only before first run) */}
        {phase === "idle" && (
          <div className="rounded-xl border border-[#D8D3C7] bg-[#F1EEE6] px-6 py-8 text-center">
            <div className="inline-flex w-12 h-12 rounded-2xl bg-[#EDE9DF] ring-1 ring-[#D8D3C7] items-center justify-center text-[#6B675C] mb-3">
              <EyeIcon size={22} />
            </div>
            <p className="text-[13px] text-[#3A372E] mb-1">Eight specialists, each pinned to a different base model.</p>
            <p className="text-[12px] text-[#5E6B78] max-w-md mx-auto">
              You'll watch every verdict land live as it arrives — then Raven sums it up.
            </p>
            <div className="flex flex-wrap items-center justify-center gap-1.5 mt-4">
              {SPECIALIST_ROLES.map((r) => (
                <span
                  key={r}
                  className="inline-flex items-center gap-1 text-[9px] font-mono text-[#6B675C] bg-[#EDE9DF] px-2 py-1 rounded"
                >
                  <EyeIcon size={9} />
                  {r.replace(/_/g, " ")}
                </span>
              ))}
            </div>
            {/* The "how it works" and "benchmarks" links used to sit here. Both
                views are gone -- the exhibit carries the method and the
                measurements now, from the generated snapshot rather than a
                second hand-maintained copy. */}
          </div>
        )}
      </div>
    </div>
  );
}

function ProvideCard({
  icon,
  title,
  body,
  onClick,
}: {
  icon: React.ReactNode;
  title: string;
  body: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="group flex items-start gap-3 rounded-xl border border-[#D8D3C7] bg-[#FFFFFF] px-4 py-3.5 text-left hover:border-[#D8D3C7] hover:bg-[#EDE9DF] transition-colors"
    >
      <span className="mt-0.5 w-8 h-8 rounded-lg bg-[#EDE9DF] ring-1 ring-[#D8D3C7] flex items-center justify-center text-[#1F6FB2] flex-shrink-0 transition-colors">
        {icon}
      </span>
      <div className="min-w-0">
        <div className="text-[12.5px] font-semibold text-[#16150F]">{title}</div>
        <div className="text-[10.5px] text-[#5E6B78] leading-snug mt-0.5">{body}</div>
      </div>
    </button>
  );
}

function SampleCard({
  s,
  active,
  disabled,
  onLoad,
  onRun,
}: {
  s: SampleContract;
  active: boolean;
  disabled: boolean;
  onLoad: () => void;
  onRun: () => void;
}) {
  const noGo = s.expected === "NO-GO";
  return (
    <article
      className={`flex flex-col rounded-xl border px-4 py-3.5 transition-colors ${
        active ? "border-[#D8D3C7] bg-[#EDE9DF]" : "border-[#D8D3C7] bg-[#FFFFFF] hover:border-[#D8D3C7]"
      }`}
    >
      <div className="flex items-start gap-2">
        <div className="min-w-0 flex-1">
          <div className="text-[13px] font-semibold text-[#16150F] truncate">{s.name}</div>
          <div className="text-[9.5px] uppercase tracking-[0.14em] text-[#6B675C] mt-0.5">{s.category}</div>
        </div>
        <span
          className={`flex-shrink-0 text-[9px] font-mono font-bold uppercase tracking-wide px-2 py-0.5 rounded-md ring-1 ${
            noGo
              ? "text-rose-200 bg-rose-500/15 ring-rose-400/30"
              : "text-emerald-200 bg-emerald-500/12 ring-emerald-400/25"
          }`}
          title={`Expected verdict: ${s.expected}`}
        >
          {s.expected}
        </span>
      </div>
      <p className="text-[11px] text-[#5E6B78] leading-relaxed mt-2 flex-1">{s.blurb}</p>
      <div className="flex items-center gap-2 mt-3">
        <button
          onClick={onRun}
          disabled={disabled}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-semibold bg-[#16150F] hover:bg-[#3A372E] text-[#F7F5F0] transition-colors disabled:opacity-30"
        >
          <BoltIcon size={12} /> Analyze
        </button>
        <button
          onClick={onLoad}
          disabled={disabled}
          className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[11px] font-medium text-[#6B675C] hover:text-[#1F6FB2] hover:bg-[#F1EEE6] transition-colors disabled:opacity-30"
        >
          Load <ArrowRightIcon size={12} />
        </button>
      </div>
    </article>
  );
}
