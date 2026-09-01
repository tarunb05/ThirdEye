// ─── Severity + role tokens (shared across views) ───

export const SPECIALIST_ROLES = [
  "reentrancy",
  "access_control",
  "arithmetic",
  "business_logic",
  "oracle_price_manipulation",
  "flashloan_mev",
  "dos_gas",
  "proxy_upgradeability",
] as const;

const ROLE_LABELS: Record<string, string> = {
  reentrancy: "Reentrancy",
  access_control: "Access Control",
  arithmetic: "Arithmetic",
  business_logic: "Business Logic",
  oracle_price_manipulation: "Oracle / Price",
  flashloan_mev: "Flash-loan / MEV",
  dos_gas: "DoS / Gas",
  proxy_upgradeability: "Proxy / Upgrade",
};

export function humanizeRole(role: string): string {
  return (
    ROLE_LABELS[role] ||
    role.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
  );
}

export type SevToken = {
  text: string;
  bg: string;
  ring: string;
  dot: string;
  hex: string;
};

// Severity, re-tuned for the bone surface. The previous steps were chosen to sit
// on dark plum and dropped to ~2:1 once the surface went light. Each text colour
// here clears 4.5:1 on #F7F5F0, and severity is always rendered with its label,
// so it never depends on hue alone.
export const SEV: Record<string, SevToken> = {
  critical: { text: "text-[#8E2417]", bg: "bg-[#F6E7E2]", ring: "ring-[#B4351F]/40", dot: "bg-[#B4351F]", hex: "#8E2417" },
  high: { text: "text-[#8A4A12]", bg: "bg-[#F6EBDD]", ring: "ring-[#B4711F]/40", dot: "bg-[#B4711F]", hex: "#8A4A12" },
  medium: { text: "text-[#6B5A1E]", bg: "bg-[#F3EEDC]", ring: "ring-[#8A7626]/40", dot: "bg-[#8A7626]", hex: "#6B5A1E" },
  low: { text: "text-[#3E5772]", bg: "bg-[#E9EDF2]", ring: "ring-[#2C4A6B]/35", dot: "bg-[#2C4A6B]", hex: "#3E5772" },
};

export function sevTokens(sev: string): SevToken {
  return SEV[(sev || "").toLowerCase()] || SEV.medium;
}

// Accent colors, shared with the exhibit so the app and the exhibit are one
// design system. ACCENT is the validated data blue: the previous #2C4A6B failed
// the palette validator on both the lightness band and the chroma floor, i.e. it
// read as grey rather than as a hue. The names below are historical — GOLD has
// been the signal vermillion since the theme moved off violet, and renaming it
// would touch every call site for no behavioural gain.
export const ACCENT = "#1F6FB2";
export const ACCENT_SOFT = "#5C7C9E";
export const GOLD = "#B4351F";

// Stable color per provider for model-diversity visualizations (purple-leaning palette).
const PROVIDER_HUES: Record<string, string> = {
  openai: "#34d399",
  anthropic: "#e8c468",
  google: "#7dd3fc",
  groq: "#f472b6",
  ollama: "#c4b5fd",
  cerebras: "#f59e0b",
  mistral: "#fb923c",
  deepseek: "#a855f7",
  together: "#e879f9",
};

export function providerColor(provider: string): string {
  return PROVIDER_HUES[(provider || "").toLowerCase()] || "#a78bfa";
}

// Chart palette (categorical) — violet-forward.
export const CHART_COLORS = [
  "#a855f7",
  "#c4b5fd",
  "#e8c468",
  "#f472b6",
  "#7dd3fc",
  "#34d399",
  "#fb923c",
  "#e879f9",
];
