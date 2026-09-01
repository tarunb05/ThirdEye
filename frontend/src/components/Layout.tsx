import { useState, type ReactNode } from "react";
import type { User } from "../lib/api";
import {
  ThirdEyeMark,
  ScanIcon,
  FlowIcon,
  ChartIcon,
  HistoryIcon,
  LogoutIcon,
  EyeIcon,
} from "./ui/icons";

// "how" and "benchmarks" were removed: the exhibit now carries the method and
// every measurement, from the generated snapshot. Two views rendering the same
// numbers from two sources is precisely the drift this project already hit.
export type Tab = "analyze" | "history";

const NAV: { id: Tab; label: string; icon: (p: { size?: number }) => ReactNode }[] = [
  { id: "analyze", label: "Scan", icon: ScanIcon },
  { id: "history", label: "History", icon: HistoryIcon },
];

export function Layout({
  user,
  tab,
  onTab,
  onLogout,
  children,
  anonymous = false,
  onSignIn,
  onHome,
}: {
  user: User;
  tab: Tab;
  onTab: (t: Tab) => void;
  onLogout: () => void;
  children: ReactNode;
  anonymous?: boolean;
  /** Return to the exhibit. Without a way back, a visitor who clicks into the
      tool can never reach the case for the project again. */
  onHome?: () => void;
  onSignIn?: () => void;
}) {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="h-screen flex overflow-hidden bg-[#F7F5F0] text-[#16150F]">
      {/* ─── Sidebar ─── */}
      <aside
        className={`fixed lg:static z-30 h-full w-[232px] flex-shrink-0 flex flex-col border-r border-[#D8D3C7] bg-[#F1EEE6]/95 backdrop-blur transition-transform duration-300 ${
          mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        }`}
      >
        {/* Brand */}
        <div
          onClick={onHome}
          role={onHome ? "button" : undefined}
          title={onHome ? "Back to the overview" : undefined}
          className="px-5 h-[60px] flex items-center gap-2.5 border-b border-[#D8D3C7]"
          style={onHome ? { cursor: "pointer" } : undefined}
        >
          <div className="text-[#1F6FB2]">
            <ThirdEyeMark size={26} />
          </div>
          <div className="leading-none">
            <div className="text-[15px] font-bold text-[#16150F] tracking-tight">ThirdEye</div>
            <div className="text-[9px] uppercase tracking-[0.22em] text-[#6B675C] mt-1">
              {onHome ? "← Overview" : "Contract Security"}
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-0.5" aria-label="Primary">
          {NAV.map((item) => {
            const active = tab === item.id;
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                onClick={() => {
                  onTab(item.id);
                  setMobileOpen(false);
                }}
                aria-current={active ? "page" : undefined}
                className={`group w-full flex items-center gap-3 px-3 py-2.5 text-[11px] font-mono uppercase tracking-[0.12em] transition-colors border-l-2 ${
                  active
                    ? "bg-[#F1EEE6] text-[#16150F] border-[#16150F]"
                    : "text-[#6B675C] hover:text-[#16150F] hover:bg-[#F1EEE6] border-transparent"
                }`}
              >
                <span className={active ? "text-[#16150F]" : "text-[#5E6B78] group-hover:text-[#16150F]"}>
                  <Icon size={17} />
                </span>
                {item.label}
              </button>
            );
          })}
        </nav>

        {/* User footer */}
        <div className="px-3 py-3 border-t border-[#D8D3C7]">
          {anonymous ? (
            <div className="px-1 py-1 space-y-2">
              <div className="flex items-center gap-2.5 px-1">
                <div className="w-8 h-8 bg-[#F1EEE6] ring-1 ring-[#D8D3C7] flex items-center justify-center text-[#1F6FB2]">
                  <EyeIcon size={15} />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="text-[12px] font-medium text-[#16150F] truncate">Guest</div>
                  <div className="text-[9px] text-[#6B675C]">anonymous trial</div>
                </div>
              </div>
              {onSignIn && (
                <button
                  onClick={onSignIn}
                  className="w-full inline-flex items-center justify-center gap-1.5 text-[12px] font-semibold bg-[#16150F] hover:bg-[#3A372E] text-[#F7F5F0] py-2 transition-colors"
                >
                  Sign in to save history
                </button>
              )}
              <button
                onClick={onLogout}
                className="w-full inline-flex items-center justify-center gap-1.5 text-[11px] text-[#5E6B78] hover:text-[#3A372E] py-1.5 hover:bg-[#F1EEE6] transition-colors"
              >
                <LogoutIcon size={13} /> Exit to home
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2.5 px-2 py-2 rounded-lg">
              <div className="w-8 h-8 rounded-lg bg-[#EDE9DF] ring-1 ring-[#D8D3C7] flex items-center justify-center text-[12px] font-bold text-[#1F6FB2] uppercase">
                {user.username.slice(0, 2)}
              </div>
              <div className="min-w-0 flex-1">
                <div className="text-[12px] font-medium text-[#16150F] truncate">{user.username}</div>
                <div className="text-[9px] text-[#6B675C]">authenticated</div>
              </div>
              <button
                onClick={onLogout}
                title="Sign out"
                aria-label="Sign out"
                className="p-1.5 rounded-md text-[#5E6B78] hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
              >
                <LogoutIcon size={16} />
              </button>
            </div>
          )}
        </div>
      </aside>

      {/* Backdrop for mobile drawer */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/60 lg:hidden"
          onClick={() => setMobileOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* ─── Main column ─── */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="flex-shrink-0 h-[60px] flex items-center gap-3 px-4 sm:px-6 border-b border-[#D8D3C7] bg-[#F1EEE6]/70 backdrop-blur">
          <button
            onClick={() => setMobileOpen(true)}
            className="lg:hidden p-1.5 rounded-md text-[#6B675C] hover:bg-[#F1EEE6]"
            aria-label="Open navigation"
          >
            <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.6}>
              <path strokeLinecap="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
            </svg>
          </button>
          <h1 className="text-[14px] font-semibold text-[#16150F] capitalize">
            {NAV.find((n) => n.id === tab)?.label}
          </h1>
          <div className="ml-auto flex items-center gap-2">
            <span className="hidden sm:inline-flex items-center gap-1.5 text-[10px] font-mono text-[#5E6B78]">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse-glow" />
              engine online
            </span>
          </div>
        </header>

        <main className="flex-1 min-h-0 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}
