import { useState } from "react";
import { authRequest, type User } from "../lib/api";
import { ThirdEyeMark, ArrowRightIcon, ShieldCheckIcon, EyeIcon, ChipIcon, HomeIcon } from "../components/ui/icons";
import { Spinner } from "../components/ui/primitives";

const FEATURES = [
  { icon: EyeIcon, title: "Eight model-diverse specialists", body: "A council of distinct base models, each pinned to one vulnerability class — real architectural diversity, not the same weights asked twice." },
  { icon: ShieldCheckIcon, title: "Raven arbitrates the evidence", body: "Raven cross-examines every claim against the source and discards anything not grounded in the code — then delivers the verdict." },
  { icon: ChipIcon, title: "Dynamic exploit confirmation", body: "Suspected issues are escalated to Foundry proof-of-concept execution before they're called exploitable." },
];

export function Login({ onAuth, onBack }: { onAuth: (u: User) => void; onBack?: () => void }) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const u = await authRequest(mode, username, password);
      onAuth(u);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen grid lg:grid-cols-[1.05fr_0.95fr] bg-[#F7F5F0]">
      {/* ─── Left brand panel ─── */}
      <div className="relative hidden lg:flex flex-col justify-between p-12 overflow-hidden border-r border-[#D8D3C7]">
        <div className="absolute inset-0 bg-grid opacity-60" aria-hidden="true" />
        <div
          className="absolute -top-32 -left-24 w-[28rem] h-[28rem] rounded-full blur-3xl"
          style={{ background: "radial-gradient(circle, rgba(44,74,107,0.08), transparent 70%)" }}
          aria-hidden="true"
        />
        <div className="relative">
          <div className="flex items-center gap-3">
            <div className="text-[#1F6FB2]" style={{ animationDuration: "30s" }}>
              <ThirdEyeMark size={38} />
            </div>
            <div>
              <div className="text-2xl font-bold text-[#16150F] tracking-tight leading-none">Third-Eye</div>
              <div className="text-[10px] uppercase tracking-[0.24em] text-[#5E6B78] mt-1.5">
                Smart-Contract Security Auditor
              </div>
            </div>
          </div>
        </div>

        <div className="relative max-w-md">
          <h2 className="text-3xl font-bold text-[#16150F] leading-tight tracking-tight">
            One unblinking eye on your on-chain code.
          </h2>
          <p className="text-[13px] text-[#6B675C] leading-relaxed mt-4">
            Third-Eye convenes a council of model-diverse specialists, grounds them in a corpus of real
            exploits, and confirms exploitability with dynamic execution. Then Raven arbitrates the
            evidence and delivers the verdict — so a GO means something.
          </p>

          <div className="mt-8 space-y-4">
            {FEATURES.map((f) => {
              const Icon = f.icon;
              return (
                <div key={f.title} className="flex gap-3">
                  <div className="mt-0.5 w-8 h-8 rounded-lg bg-[#EDE9DF] ring-1 ring-[#D8D3C7] flex items-center justify-center text-[#1F6FB2] flex-shrink-0">
                    <Icon size={15} />
                  </div>
                  <div>
                    <div className="text-[12.5px] font-semibold text-[#16150F]">{f.title}</div>
                    <div className="text-[11px] text-[#5E6B78] leading-relaxed mt-0.5">{f.body}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="relative text-[10px] font-mono text-[#5E6B78]">
          Third-Eye is a decision-support tool — it does not replace a professional audit.
        </div>
      </div>

      {/* ─── Right form ─── */}
      <div className="flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-sm animate-fade-in">
          {/* compact brand for mobile */}
          <div className="lg:hidden flex items-center gap-2.5 mb-10">
            <span className="text-[#1F6FB2]">
              <ThirdEyeMark size={28} />
            </span>
            <span className="text-xl font-bold text-[#16150F] tracking-tight">ThirdEye</span>
          </div>

          {onBack && (
            <button
              onClick={onBack}
              className="inline-flex items-center gap-1.5 text-[12px] text-[#6B675C] hover:text-[#1F6FB2] transition-colors mb-6"
            >
              <HomeIcon size={13} /> Back to home
            </button>
          )}

          <h1 className="text-xl font-bold text-[#16150F] tracking-tight">
            {mode === "login" ? "Sign in to Third-Eye" : "Create your account"}
          </h1>
          <p className="text-[12px] text-[#5E6B78] mt-1.5">
            {mode === "login" ? "Access the audit console." : "Minimum 3-char username, 4-char password."}
          </p>

          <form onSubmit={submit} className="mt-8 space-y-3.5">
            <Field
              label="Username"
              type="text"
              value={username}
              onChange={setUsername}
              autoComplete="username"
            />
            <Field
              label="Password"
              type="password"
              value={password}
              onChange={setPassword}
              autoComplete={mode === "login" ? "current-password" : "new-password"}
            />

            {error && (
              <div className="rounded-lg border border-rose-500/25 bg-rose-500/[0.08] px-3 py-2 text-[12px] text-rose-300">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading || !username || !password}
              className="w-full inline-flex items-center justify-center gap-2 bg-[#16150F] hover:bg-[#3A372E] text-[#F7F5F0] font-semibold py-2.5 rounded-lg transition-colors disabled:opacity-30 disabled:cursor-not-allowed text-[13px]"
            >
              {loading ? (
                <Spinner size={15} />
              ) : (
                <>
                  {mode === "login" ? "Sign In" : "Create Account"}
                  <ArrowRightIcon size={15} />
                </>
              )}
            </button>
          </form>

          <p className="text-center text-[12px] text-[#5E6B78] mt-6">
            {mode === "login" ? "Don't have an account? " : "Already registered? "}
            <button
              onClick={() => {
                setMode(mode === "login" ? "register" : "login");
                setError("");
              }}
              className="text-[#1F6FB2] hover:text-[#1F6FB2] font-medium transition-colors"
            >
              {mode === "login" ? "Register" : "Sign in"}
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}

function Field({
  label,
  type,
  value,
  onChange,
  autoComplete,
}: {
  label: string;
  type: string;
  value: string;
  onChange: (v: string) => void;
  autoComplete?: string;
}) {
  return (
    <label className="block">
      <span className="block text-[11px] uppercase tracking-[0.14em] text-[#5E6B78] mb-1.5">{label}</span>
      <input
        type={type}
        value={value}
        autoComplete={autoComplete}
        onChange={(e) => onChange(e.target.value)}
        className="w-full bg-[#F1EEE6] border border-[#D8D3C7] rounded-lg px-3.5 py-2.5 text-[13px] text-[#16150F] placeholder:text-[#5E6B78] outline-none focus:border-[#D8D3C7] focus:bg-[#F1EEE6] transition-colors"
      />
    </label>
  );
}
