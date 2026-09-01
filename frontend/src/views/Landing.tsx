import {
  ThirdEyeMark,
  ArrowRightIcon,
  ScanIcon,
  FlowIcon,
  ShieldCheckIcon,
  AlertIcon,
  ChipIcon,
  EyeIcon,
  CheckIcon,
} from "../components/ui/icons";

// ─── Public marketing / product landing (pre-login) ───
// Two CTAs: "Try a scan" (anonymous trial straight into the Scan view) and
// "Sign in". Dependency-free, responsive, bone surface, consistent with theme.
export function Landing({
  onTryScan,
  onSignIn,
}: {
  onTryScan: () => void;
  onSignIn: () => void;
}) {
  return (
    <div className="min-h-screen bg-[#F7F5F0] text-[#16150F] overflow-x-hidden">
      {/* ─── Top nav ─── */}
      <header className="sticky top-0 z-30 border-b border-[#D8D3C7] bg-[#F7F5F0]/80 backdrop-blur">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-14 flex items-center gap-3">
          <span className="text-[#1F6FB2]">
            <ThirdEyeMark size={24} />
          </span>
          <div className="leading-none">
            <span className="text-[15px] font-bold text-[#16150F] tracking-tight">ThirdEye</span>
            <span className="ml-2 text-[9px] uppercase tracking-[0.22em] text-[#6B675C] align-middle">
              Contract Security
            </span>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <button
              onClick={onSignIn}
              className="text-[12.5px] font-medium text-[#3A372E] hover:text-[#16150F] px-3 py-1.5 rounded-lg hover:bg-[#F1EEE6] transition-colors"
            >
              Sign in
            </button>
            <button
              onClick={onTryScan}
              className="inline-flex items-center gap-1.5 text-[12.5px] font-semibold bg-[#16150F] hover:bg-[#3A372E] text-[#F7F5F0] px-3.5 py-1.5 rounded-lg transition-colors"
            >
              Try a scan <ArrowRightIcon size={13} />
            </button>
          </div>
        </div>
      </header>

      {/* ─── Hero ─── */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-grid opacity-[0.35]" aria-hidden="true" />
        <div
          className="absolute -top-40 left-1/2 -translate-x-1/2 w-[52rem] h-[52rem] rounded-full blur-3xl pointer-events-none"
          style={{ background: "radial-gradient(circle, rgba(44,74,107,0.08), transparent 65%)" }}
          aria-hidden="true"
        />
        <div className="relative max-w-6xl mx-auto px-4 sm:px-6 pt-16 sm:pt-24 pb-16 text-center">
          {/* Raven agent mark */}
          <div className="inline-flex items-center justify-center mb-7">
            <span className="relative">
              <span
                className="absolute inset-0 rounded-full blur-2xl"
                style={{ background: "radial-gradient(circle, rgba(44,74,107,0.08), transparent 70%)" }}
                aria-hidden="true"
              />
              <span className="relative inline-flex w-20 h-20 rounded-2xl bg-[#FFFFFF] ring-1 ring-[#D8D3C7] items-center justify-center text-[#1F6FB2]">
                <ThirdEyeMark size={44} className="animate-lid-blink" />
              </span>
            </span>
          </div>

          <div className="inline-flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-[0.2em] text-[#6B675C] bg-[#EDE9DF] ring-1 ring-[#D8D3C7] px-3 py-1 rounded-full mb-6">
            <span className="w-1.5 h-1.5 rounded-full bg-[#16150F] animate-pulse-glow" />
            Meet Raven
          </div>

          <h1 className="text-4xl sm:text-6xl font-bold text-[#16150F] tracking-tight leading-[1.05]">
            ThirdEye
          </h1>
          <p className="mt-5 prose-report text-[15px] sm:text-lg text-[#3F3B31] max-w-2xl mx-auto">
            A model-diverse council of LLM specialists that audits your smart contracts and returns a
            single <span className="text-[#16150F] font-semibold">GO</span> /{" "}
            <span className="text-[#B4351F] font-semibold">NO-GO</span> verdict — grounded in real evidence,
            not vibes.
          </p>

          <div className="mt-9 flex flex-col sm:flex-row items-center justify-center gap-3">
            <button
              onClick={onTryScan}
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl text-[14px] font-semibold bg-[#16150F] hover:bg-[#3A372E] text-[#F7F5F0] shadow-[0_10px_30px_-12px_rgba(44,74,107,0.08)] transition-colors"
            >
              <ScanIcon size={16} /> Try a scan
              <span className="text-[10px] font-mono font-normal text-[#6B675C]">no login</span>
            </button>
            <button
              onClick={onSignIn}
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl text-[14px] font-semibold border border-[#D8D3C7] text-[#16150F] hover:bg-[#F1EEE6] transition-colors"
            >
              Sign in <ArrowRightIcon size={15} />
            </button>
          </div>
          <p className="mt-4 text-[11px] font-mono text-[#5E6B78]">
            Anonymous scans run instantly — sign in to keep a history.
          </p>
        </div>
      </section>

      {/* ─── How it works strip ─── */}
      <section className="relative max-w-6xl mx-auto px-4 sm:px-6 py-12 sm:py-16">
        <SectionEyebrow icon={<FlowIcon size={12} />}>How it works</SectionEyebrow>
        <h2 className="text-2xl sm:text-3xl font-bold text-[#16150F] tracking-tight mt-3 max-w-2xl">
          One pipeline, four defensible stages.
        </h2>

        <div className="mt-8 grid gap-3 lg:grid-cols-4 sm:grid-cols-2">
          {PIPELINE.map((step, i) => (
            <div
              key={step.title}
              className="relative rounded-2xl border border-[#D8D3C7] bg-[#FFFFFF] px-5 py-5"
            >
              <div className="flex items-center gap-2.5">
                <span className="w-9 h-9 rounded-xl bg-[#EDE9DF] ring-1 ring-[#D8D3C7] flex items-center justify-center text-[#1F6FB2] flex-shrink-0">
                  {step.icon}
                </span>
                <span className="text-[10px] font-mono text-[#6B675C]">
                  {String(i + 1).padStart(2, "0")}
                </span>
              </div>
              <div className="mt-3.5 text-[14px] font-semibold text-[#16150F]">{step.title}</div>
              <p className="mt-1.5 text-[12px] text-[#6B675C] leading-relaxed">{step.body}</p>
              {i < PIPELINE.length - 1 && (
                <span
                  className="hidden lg:block absolute -right-2 top-1/2 -translate-y-1/2 text-[#6B675C] z-10"
                  aria-hidden="true"
                >
                  <ArrowRightIcon size={16} />
                </span>
              )}
            </div>
          ))}
        </div>

        {/* Verdict legend */}
        <div className="mt-6 flex flex-wrap items-center gap-2.5">
          <VerdictChip tone="go" icon={<ShieldCheckIcon size={13} />} label="GO" note="cleared" />
          <VerdictChip tone="nogo" icon={<AlertIcon size={13} />} label="NO-GO" note="blocked" />
          <VerdictChip
            tone="incon"
            icon={<AlertIcon size={13} />}
            label="INCONCLUSIVE"
            note="scan incomplete — not a clean bill of health"
          />
        </div>
      </section>

      {/* ─── What it catches ─── */}
      <section className="relative max-w-6xl mx-auto px-4 sm:px-6 py-12 sm:py-16">
        <div className="absolute inset-x-0 top-0 h-px bg-[#D8D3C7]" />
        <SectionEyebrow icon={<EyeIcon size={12} />}>What it catches</SectionEyebrow>
        <h2 className="text-2xl sm:text-3xl font-bold text-[#16150F] tracking-tight mt-3 max-w-2xl">
          Eight specialists, each pinned to a different attack surface.
        </h2>
        <p className="mt-3 text-[13px] text-[#6B675C] max-w-2xl leading-relaxed">
          Real architectural diversity — distinct base models, not the same weights asked twice. A static
          router picks the ones that matter for your contract.
        </p>

        <div className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {CATCHES.map((c) => (
            <div
              key={c.title}
              className="group rounded-xl border border-[#D8D3C7] bg-[#FFFFFF] px-4 py-4 hover:border-[#D8D3C7] hover:bg-[#EDE9DF] transition-colors"
            >
              <div className="flex items-center gap-2 text-[#1F6FB2]">
                <EyeIcon size={14} />
                <span className="text-[13px] font-semibold text-[#16150F]">{c.title}</span>
              </div>
              <p className="mt-1.5 text-[11.5px] text-[#5E6B78] leading-relaxed">{c.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ─── CTA band ─── */}
      <section className="relative max-w-6xl mx-auto px-4 sm:px-6 pb-20">
        <div className="relative overflow-hidden rounded-3xl border border-[#D8D3C7] bg-[#FFFFFF] px-6 sm:px-10 py-10 sm:py-12 text-center">
          <div className="absolute inset-0 bg-grid opacity-[0.3]" aria-hidden="true" />
          <div
            className="absolute -right-24 -top-24 w-80 h-80 rounded-full blur-3xl pointer-events-none"
            style={{ background: "radial-gradient(circle, rgba(44,74,107,0.08), transparent 70%)" }}
            aria-hidden="true"
          />
          <div className="relative">
            <h2 className="text-2xl sm:text-3xl font-bold text-[#16150F] tracking-tight">
              Point ThirdEye at your contract.
            </h2>
            <p className="mt-3 text-[13.5px] text-[#6B675C] max-w-xl mx-auto leading-relaxed">
              Paste Solidity, upload a <code className="text-[#6B675C]">.sol</code>, or pick a sample.
              Watch every specialist land its verdict live — then Raven arbitrates.
            </p>
            <div className="mt-7 flex flex-col sm:flex-row items-center justify-center gap-3">
              <button
                onClick={onTryScan}
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl text-[14px] font-semibold bg-[#16150F] hover:bg-[#3A372E] text-[#F7F5F0] shadow-[0_10px_30px_-12px_rgba(44,74,107,0.08)] transition-colors"
              >
                <ScanIcon size={16} /> Try a scan
              </button>
              <button
                onClick={onSignIn}
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl text-[14px] font-semibold border border-[#D8D3C7] text-[#16150F] hover:bg-[#F1EEE6] transition-colors"
              >
                Sign in
              </button>
            </div>
          </div>
        </div>

        <p className="mt-8 text-center text-[11px] font-mono text-[#5E6B78]">
          ThirdEye is a decision-support tool — it does not replace a professional audit.
        </p>
      </section>
    </div>
  );
}

// ─── Pipeline stages (the real architecture) ───
const PIPELINE: { title: string; body: string; icon: React.ReactNode }[] = [
  {
    title: "Static routing",
    body: "A heuristic pre-scan reads the contract and routes it to only the relevant specialists — not always all eight.",
    icon: <FlowIcon size={16} />,
  },
  {
    title: "Model-diverse council",
    body: "Up to eight specialists, each a distinct base model pinned to one vulnerability class, examine the source in parallel.",
    icon: <ChipIcon size={16} />,
  },
  {
    title: "Evidence-anchored arbitration",
    body: "Raven cross-examines every claim against the code and drops anything not grounded in an actual quote.",
    icon: <ShieldCheckIcon size={16} />,
  },
  {
    title: "GO / NO-GO / INCONCLUSIVE",
    body: "One defensible verdict. INCONCLUSIVE means the scan couldn't finish — never a false all-clear.",
    icon: <CheckIcon size={16} />,
  },
];

// ─── Vulnerability classes the council covers ───
const CATCHES: { title: string; body: string }[] = [
  { title: "Reentrancy", body: "Cross-function and cross-contract re-entry into unguarded state changes." },
  { title: "Access control", body: "Missing or broken authorization on privileged and admin paths." },
  { title: "Oracle / price", body: "Manipulable price feeds and spot-price reads used for accounting." },
  { title: "Flash-loan / MEV", body: "Atomic capital attacks, sandwiching, and value-extraction ordering." },
  { title: "Arithmetic", body: "Overflow, precision loss, rounding, and unchecked math corners." },
  { title: "Business logic", body: "Invariant violations and economic assumptions that break under edge cases." },
  { title: "DoS / gas", body: "Unbounded loops and griefing that can wedge the contract." },
  { title: "Proxy / upgrade", body: "Storage-collision and initialization flaws in upgradeable patterns." },
];

function SectionEyebrow({ children, icon }: { children: React.ReactNode; icon?: React.ReactNode }) {
  return (
    <div className="inline-flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-[0.2em] text-[#6B675C] bg-[#EDE9DF] ring-1 ring-[#D8D3C7] px-2.5 py-1 rounded-md">
      {icon}
      {children}
    </div>
  );
}

function VerdictChip({
  tone,
  icon,
  label,
  note,
}: {
  tone: "go" | "nogo" | "incon";
  icon: React.ReactNode;
  label: string;
  note: string;
}) {
  const cls =
    tone === "go"
      ? "text-emerald-300 bg-emerald-500/10 ring-emerald-400/25"
      : tone === "nogo"
      ? "text-rose-300 bg-rose-500/10 ring-rose-400/25"
      : "text-amber-300 bg-amber-500/10 ring-amber-400/25";
  return (
    <span className={`inline-flex items-center gap-1.5 text-[11px] px-2.5 py-1 rounded-lg ring-1 ${cls}`}>
      {icon}
      <span className="font-mono font-bold uppercase tracking-wide">{label}</span>
      <span className="text-[#6B675C]/80 font-normal normal-case tracking-normal">— {note}</span>
    </span>
  );
}
