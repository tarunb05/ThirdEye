import type {
  CouncilResult,
  CouncilVuln,
  CouncilStats,
  SimilarExploit,
  FinalVerdict,
  ArbitrationSummary,
  RoutingInfo,
} from "../../lib/api";
import { sevTokens, humanizeRole } from "../../lib/theme";
import { ShieldCheckIcon, AlertIcon, CheckIcon, FlowIcon } from "../ui/icons";
import { ModelChip, ConfidenceMeter, SectionLabel, Eyebrow } from "../ui/primitives";

// Verdict palette — GO is the only green state. INCONCLUSIVE is amber (NOT a
// clean bill of health), NO-GO is rose.
type VerdictTone = {
  verdict: FinalVerdict;
  label: string;
  fg: string; // text color class
  ringBg: string; // icon chip bg + ring
  panelBg: string; // banner gradient
  border: string;
  shadow: string;
  rule: string; // bottom rule gradient
  icon: React.ReactNode;
};

function verdictTone(v: FinalVerdict): VerdictTone {
  if (v === "GO") {
    return {
      verdict: v,
      label: "Cleared by Council",
      fg: "text-[#16150F]",
      ringBg: "bg-[#ECEFE9] ring-[#16150F]/25",
      panelBg: "linear-gradient(135deg, rgba(16,185,129,0.12), rgba(14,10,20,0.35))",
      border: "rgba(16,185,129,0.28)",
      shadow: "0 0 60px -28px rgba(16,185,129,0.4)",
      rule: "linear-gradient(90deg, rgba(16,185,129,0.55), transparent)",
      icon: <ShieldCheckIcon size={28} />,
    };
  }
  if (v === "INCONCLUSIVE") {
    return {
      verdict: v,
      label: "Scan Incomplete — Not Cleared",
      fg: "text-amber-300",
      ringBg: "bg-amber-500/14 ring-amber-400/35",
      panelBg: "linear-gradient(135deg, rgba(245,158,11,0.13), rgba(14,10,20,0.35))",
      border: "rgba(245,158,11,0.32)",
      shadow: "0 0 60px -28px rgba(245,158,11,0.45)",
      rule: "linear-gradient(90deg, rgba(245,158,11,0.6), transparent)",
      icon: <AlertIcon size={28} />,
    };
  }
  return {
    verdict: v,
    label: "Deployment Blocked",
    fg: "text-[#B4351F]",
    ringBg: "bg-[#F6E7E2] ring-[#B4351F]/35",
    panelBg: "linear-gradient(135deg, rgba(244,63,94,0.13), rgba(14,10,20,0.35))",
    border: "rgba(244,63,94,0.3)",
    shadow: "0 0 60px -28px rgba(244,63,94,0.45)",
    rule: "linear-gradient(90deg, rgba(244,63,94,0.65), transparent)",
    icon: <AlertIcon size={28} />,
  };
}

// ─── Verdict banner ───
export function VerdictBanner({ result }: { result: CouncilResult }) {
  const t = verdictTone(result.final_verdict);
  const stats = result.stats;
  const errored = stats?.specialists_errored ?? 0;
  const ran = stats?.specialists_run ?? 0;
  // Only claim completion when nothing errored.
  const completed = Math.max(0, ran - errored);
  const arb = result.arbitration_summary;

  return (
    <section
      className="animate-scale-in relative overflow-hidden rounded-2xl border"
      style={{ background: t.panelBg, borderColor: t.border, boxShadow: t.shadow }}
      aria-label={`Verdict ${result.final_verdict}`}
    >
      <div className="bg-grid opacity-40 absolute inset-0" aria-hidden="true" />
      <div className="relative flex flex-col sm:flex-row sm:items-center gap-5 px-6 py-5">
        <div className={`flex items-center gap-3 px-5 py-3 rounded-xl ring-1 flex-shrink-0 ${t.ringBg}`}>
          <span className={t.fg}>{t.icon}</span>
          <div>
            <div className={`text-2xl font-bold tracking-tight leading-none ${t.fg}`}>
              {result.final_verdict}
            </div>
            <div className="text-[10px] uppercase tracking-[0.18em] text-[#6B675C] mt-1">{t.label}</div>
          </div>
        </div>
        <div className="min-w-0 flex-1">
          {result.contract_name && (
            <div className="flex items-center gap-2 mb-1">
              <span className="text-[10px] uppercase tracking-[0.18em] text-[#5E6B78]">Contract</span>
              <span className="text-sm font-mono font-semibold text-[#16150F] truncate">{result.contract_name}</span>
            </div>
          )}

          {/* Specialist health — only show GO context alongside a completed scan. */}
          {stats && (
            <div className="flex flex-wrap items-center gap-2 mb-2 text-[10px] font-mono">
              <span
                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md ring-1 ${
                  errored > 0
                    ? "text-amber-300 bg-amber-500/12 ring-amber-400/25"
                    : "text-emerald-300/90 bg-emerald-500/10 ring-emerald-400/20"
                }`}
              >
                {completed}/{ran} specialists completed
              </span>
              {errored > 0 && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-amber-300 bg-amber-500/12 ring-1 ring-amber-400/25">
                  <AlertIcon size={10} /> {errored} errored
                </span>
              )}
            </div>
          )}

          {/* verdict_reason — the "why" under the verdict. */}
          {result.verdict_reason && (
            <p
              className={`text-[12px] leading-relaxed mb-2 ${
                result.final_verdict === "INCONCLUSIVE" ? "text-amber-200/90" : "text-[#3A372E]"
              }`}
            >
              {result.verdict_reason}
            </p>
          )}

          {result.raven_note && (
            <div className="flex items-start gap-2.5">
              <span className="mt-0.5 flex-shrink-0 text-[9px] font-mono font-bold uppercase tracking-[0.14em] text-[#1F6FB2] bg-[#EDE9DF] ring-1 ring-[#D8D3C7] px-2 py-1 rounded-md">
                Raven's read
              </span>
              <p className="text-[13px] text-[#3A372E] leading-relaxed">{result.raven_note}</p>
            </div>
          )}

          {/* Precision story — arbitration upheld X, dropped Y false positives. */}
          {arb && (arb.upheld != null || arb.dropped != null) && (
            <p className="text-[11px] text-[#6B675C] mt-2">
              Arbitration upheld{" "}
              <span className="font-semibold text-[#1F6FB2] tabular-nums">{arb.upheld ?? 0}</span>, dropped{" "}
              <span className="font-semibold text-[#1F6FB2] tabular-nums">{arb.dropped ?? 0}</span>{" "}
              {arb.dropped === 1 ? "false positive" : "false positives"}
              {arb.dropped_types?.length ? ` (${arb.dropped_types.join(", ")})` : ""}.
            </p>
          )}
        </div>
      </div>
      <div className="h-1 w-full" style={{ background: t.rule }} />
    </section>
  );
}

// ─── Routing summary panel (which specialists the static router selected) ───
export function RoutingSummary({ routing }: { routing?: RoutingInfo }) {
  if (!routing || !routing.roles?.length) return null;
  const trace = routing.trace ?? {};
  return (
    <section aria-label="Static routing" className="rounded-xl border border-[#D8D3C7] bg-[#FFFFFF] px-5 py-4">
      <SectionLabel count={routing.roles.length}>
        <span className="inline-flex items-center gap-1.5">
          <FlowIcon size={12} /> Static routing
        </span>
      </SectionLabel>
      <p className="text-[12px] text-[#6B675C] leading-relaxed mb-3">
        {routing.static_used === false
          ? "The heuristic router could not narrow the surface, so the full council was convened."
          : "A heuristic pre-scan routed the contract to only the relevant specialists — the rest were skipped."}
      </p>
      <div className="flex flex-wrap gap-1.5">
        {routing.roles.map((r) => (
          <span
            key={r}
            className="inline-flex items-center gap-1 text-[10px] font-mono text-[#6B675C] bg-[#EDE9DF] ring-1 ring-[#D8D3C7] px-2 py-0.5 rounded-md"
            title={trace[r]}
          >
            {humanizeRole(r)}
          </span>
        ))}
      </div>
    </section>
  );
}

// ─── Stats strip ───
export function StatsStrip({ stats }: { stats: CouncilStats }) {
  const errored = stats.specialists_errored ?? 0;
  return (
    <section
      aria-label="Council statistics"
      className={`grid grid-cols-2 gap-3 ${errored > 0 ? "sm:grid-cols-5" : "sm:grid-cols-4"}`}
    >
      <Stat label="Models Run" value={stats.models_run} sub={stats.tier ? `${stats.tier} tier` : undefined} />
      <Stat label="Specialists" value={stats.specialists_run} sub="invoked" />
      <Stat label="Findings" value={stats.specialists_found} sub="flagged a risk" tone="danger" />
      <Stat label="Confirmed" value={stats.specialists_confirmed} sub="exploitable" tone="danger" />
      {errored > 0 && <Stat label="Errored" value={errored} sub="incomplete" tone="warn" />}
    </section>
  );
}

function Stat({
  label,
  value,
  sub,
  tone,
}: {
  label: string;
  value: number | string;
  sub?: string;
  tone?: "danger" | "warn";
}) {
  const hot = Number(value) > 0;
  const valColor =
    tone === "danger" && hot ? "text-rose-400" : tone === "warn" && hot ? "text-amber-300" : "text-[#16150F]/90";
  return (
    <div className="rounded-xl bg-[#FFFFFF] border border-[#D8D3C7] px-4 py-3">
      <div className="text-[9px] uppercase tracking-[0.14em] text-[#5E6B78] mb-1">{label}</div>
      <div className={`text-xl font-bold tabular-nums leading-none ${valColor}`}>{value}</div>
      {sub && <div className="text-[9px] font-mono text-[#5E6B78] mt-1">{sub}</div>}
    </div>
  );
}

// ─── Confirmed vulnerabilities ───
function DynamicStatusBadge({ status }: { status: string }) {
  if (status === "CONFIRMED-EXPLOITABLE") {
    return (
      <span className="inline-flex items-center gap-1 text-[9px] font-bold uppercase tracking-wide text-rose-200 bg-rose-500/20 ring-1 ring-rose-400/40 px-2 py-0.5 rounded-md">
        <CheckIcon size={10} /> Confirmed Exploitable
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-[9px] font-bold uppercase tracking-wide text-amber-300 bg-amber-500/15 ring-1 ring-amber-400/30 px-2 py-0.5 rounded-md">
      Suspected
    </span>
  );
}

function VulnRow({ v }: { v: CouncilVuln }) {
  const s = sevTokens(v.severity);
  return (
    <article className={`rounded-xl ring-1 ${s.ring} ${s.bg} px-4 py-3.5 space-y-3`}>
      <div className="flex flex-wrap items-center gap-2">
        <span className={`w-2 h-2 rounded-full ${s.dot}`} aria-hidden="true" />
        <span className="text-[14px] font-semibold text-[#16150F]/90 capitalize">{humanizeRole(v.type)}</span>
        <span className={`text-[9px] font-mono font-bold uppercase ${s.text}`}>{v.severity}</span>
        <div className="ml-auto">
          <DynamicStatusBadge status={v.dynamic_status} />
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <ModelChip model={v.model} provider={v.provider} />
        {v.source && (
          <span className="text-[9px] font-mono text-[#6B675C] bg-[#F1EEE6] px-1.5 py-0.5 rounded">via {v.source}</span>
        )}
        <div className="flex-1 min-w-[120px]">
          <ConfidenceMeter value={v.confidence} tone="danger" />
        </div>
      </div>
      {v.description && <p className="text-[12px] text-[#6B675C] leading-relaxed">{v.description}</p>}
      {v.evidence_quote && (
        <div>
          <Eyebrow>Evidence</Eyebrow>
          <pre className="text-[10px] font-mono text-rose-200/80 bg-black/40 ring-1 ring-rose-500/10 rounded-lg px-3 py-2 leading-relaxed whitespace-pre-wrap break-words max-h-44 overflow-auto">
            {v.evidence_quote}
          </pre>
        </div>
      )}
      {v.proposed_property && (
        <div>
          <Eyebrow>Proposed Invariant</Eyebrow>
          <p className="text-[11px] font-mono text-[#6B675C] bg-[#EDE9DF] ring-1 ring-[#D8D3C7] rounded-lg px-3 py-2 leading-relaxed">
            {v.proposed_property}
          </p>
        </div>
      )}
    </article>
  );
}

export function VulnList({
  vulnerabilities,
  inconclusive = false,
}: {
  vulnerabilities: CouncilVuln[];
  inconclusive?: boolean;
}) {
  if (!vulnerabilities || vulnerabilities.length === 0) {
    // When the scan is inconclusive, "none found" is NOT reassuring — use amber.
    return (
      <section aria-label="Confirmed vulnerabilities">
        <SectionLabel count={0}>Confirmed Vulnerabilities</SectionLabel>
        {inconclusive ? (
          <div className="rounded-xl border border-amber-500/20 bg-amber-500/[0.04] px-4 py-6 text-center">
            <p className="text-[13px] text-amber-200/85">
              No vulnerabilities were confirmed — but the scan did not complete, so this is not a clean bill of health.
            </p>
          </div>
        ) : (
          <div className="rounded-xl border border-emerald-500/15 bg-emerald-500/[0.03] px-4 py-6 text-center">
            <p className="text-[13px] text-emerald-300/80">No vulnerabilities confirmed by the council.</p>
          </div>
        )}
      </section>
    );
  }
  const order = ["critical", "high", "medium", "low"];
  const sorted = [...vulnerabilities].sort(
    (a, b) => order.indexOf((a.severity || "").toLowerCase()) - order.indexOf((b.severity || "").toLowerCase())
  );
  return (
    <section aria-label="Confirmed vulnerabilities">
      <SectionLabel count={sorted.length}>Confirmed Vulnerabilities</SectionLabel>
      <div className="space-y-3">
        {sorted.map((v, i) => (
          <VulnRow key={`${v.type}-${i}`} v={v} />
        ))}
      </div>
    </section>
  );
}

// ─── Similar known exploits ───
export function PrecedentPanel({ exploits }: { exploits?: SimilarExploit[] }) {
  if (!exploits || exploits.length === 0) return null;
  return (
    <section aria-label="Similar known exploits">
      <SectionLabel count={exploits.length}>Similar Known Exploits</SectionLabel>
      <div className="grid gap-3 sm:grid-cols-2">
        {exploits.map((e, i) => {
          const s = e.severity ? sevTokens(e.severity) : null;
          return (
            <article key={i} className="rounded-xl border border-[#D8D3C7] bg-[#FFFFFF] px-4 py-3.5 space-y-2">
              <div className="flex items-center gap-2">
                {e.category && (
                  <span className="text-[12px] font-semibold text-[#16150F] capitalize">
                    {e.category.replace(/_/g, " ")}
                  </span>
                )}
                {e.severity && s && (
                  <span className={`ml-auto text-[9px] font-mono font-bold uppercase ${s.text}`}>{e.severity}</span>
                )}
              </div>
              {e.snippet && (
                <pre className="text-[10px] font-mono text-[#6B675C] bg-black/35 ring-1 ring-[#D8D3C7] rounded-lg px-3 py-2 leading-relaxed whitespace-pre-wrap break-words max-h-36 overflow-auto">
                  {e.snippet}
                </pre>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}
