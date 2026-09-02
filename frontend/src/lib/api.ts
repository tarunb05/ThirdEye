// ─── Third-Eye API client + shared types ───────────────────────────
// Base URL follows the existing VITE_API_URL pattern (defaults to "/api"
// which the Vite dev server proxies to the FastAPI backend).

export const API = import.meta.env.VITE_API_URL || "/api";

// ─── Auth / session ───
export type User = { user_id: number; username: string; token: string };
export type Session = {
  id: number;
  title: string;
  created_at: string;
  msg_count?: number;
};
export type Message = {
  id: number;
  role: string;
  content: string;
  created_at: string;
};

// ─── Council result schema (mirrors POST /api/analyze/council) ───
export type Severity = "critical" | "high" | "medium" | "low";
export type DynamicStatus = "SUSPECTED" | "CONFIRMED-EXPLOITABLE";

export type CouncilVuln = {
  type: string;
  severity: Severity | string;
  confidence: number;
  description: string;
  evidence_quote: string;
  proposed_property: string;
  source: string;
  model: string;
  provider: string;
  dynamic_status: DynamicStatus | string;
};

export type CouncilDetail = {
  role: string;
  provider: string;
  model: string;
  found: boolean;
  confidence: number;
  severity: string;
  evidence_quote: string;
  property: string;
};

export type CouncilStats = {
  models_run: number;
  specialists_run: number;
  specialists_found: number;
  specialists_confirmed: number;
  specialists_errored?: number;
  tier: string;
  models_used: string[];
};

// ─── Static router trace (which specialists were selected + why) ───
export type RoutingInfo = {
  roles: string[];
  trace?: Record<string, string>;
  static_used?: boolean;
};

// ─── Arbitration / cross-examination summary ───
export type ArbitrationSummary = {
  reviewed?: number;
  upheld?: number;
  dropped?: number;
  dropped_types?: string[];
};

export type SimilarExploit = {
  category?: string;
  severity?: string;
  snippet?: string;
};

export type FinalVerdict = "GO" | "NO-GO" | "INCONCLUSIVE";

export type CouncilResult = {
  final_verdict: FinalVerdict;
  verdict_reason?: string;
  vulnerabilities: CouncilVuln[];
  summary: string;
  raven_note?: string;
  contract_name?: string;
  stats?: CouncilStats;
  council_detail?: CouncilDetail[];
  similar_exploits?: SimilarExploit[];
  mode?: string;
  // new architecture surfaces
  routing?: RoutingInfo;
  arbitration_summary?: ArbitrationSummary;
  // pipeline extras (optional)
  pipeline?: Record<string, unknown>;
  arbitration?: Record<string, unknown>;
  dynamic?: Record<string, unknown>;
};

// ─── Sample contracts (GET /api/samples) ───
export type SampleContract = {
  id: string;
  name: string;
  category: string;
  expected: "GO" | "NO-GO" | string;
  blurb: string;
  code: string;
};

// ─── SSE stream events ───
export type SpecialistMeta = { role: string; provider: string; model: string };

export type StreamStart = {
  event: "start";
  tier: string;
  specialists: SpecialistMeta[];
};
// Static/heuristic router picked which specialists to run (not always all 8).
export type StreamRouting = {
  event: "routing";
  roles: string[];
  trace?: Record<string, string>;
  static_used?: boolean;
};
// Arbitration / cross-examination step (after all specialists, before result).
export type StreamArbitrating = {
  event: "arbitrating";
  count: number;
};
export type StreamSpecialistDone = {
  event: "specialist_done";
  role: string;
  model: string;
  provider: string;
  found: boolean;
  confidence: number;
  severity: string;
  evidence_quote: string;
  llm_error: boolean;
};
export type StreamFinal = { event: "final"; result: CouncilResult };
export type StreamEvent =
  | StreamStart
  | StreamRouting
  | StreamArbitrating
  | StreamSpecialistDone
  | StreamFinal
  | { event: string; [k: string]: unknown };

// ─── Benchmark stats schema (GET /api/stats/benchmark) ───
export type Kpi = { label: string; value: string | number; sub?: string; delta?: number };
export type AblationConfig = {
  config: string;
  precision: number;
  recall: number;
  f1: number;
  tp: number;
  fp: number;
  tn: number;
  fn: number;
};
export type VulnDistEntry = { category: string; count: number; pct: number };
export type AblationSample = { n?: number; pos?: number; neg?: number; seed?: number };
export type Baseline = {
  tool: string;
  dataset: string;
  recall: number;
  f1: number | null;
  cost?: string;
  note?: string;
};
export type TierResult = {
  tier?: string;
  label?: string;
  expected?: "safe" | "vulnerable" | string;
  bucket?: string;
  n?: number;
  scored?: number;
  inconclusive?: number;
  errored?: number;
  tp?: number;
  fp?: number;
  tn?: number;
  fn?: number;
  precision?: number | null;
  recall?: number | null;
  f1?: number | null;
  accuracy?: number | null;
  correct_go_rate_on_safe?: number | null;
  detection_rate_on_vuln?: number | null;
};
export type ApiAccounting = {
  available?: boolean;
  contracts?: number;
  total_api_calls?: number;
  calls_per_contract?: { min?: number; max?: number; mean?: number; median?: number; p95?: number };
  latency_s_per_contract?: { min?: number; max?: number; mean?: number; median?: number } | null;
  rate_limit_note?: string;
};
export type TierBenchmark = {
  available?: boolean;
  note?: string;
  backend?: string;
  n_total?: number;
  tiers?: TierResult[];
  safe_aggregate?: TierResult;
  vuln_aggregate?: TierResult;
  overall?: TierResult;
  api_accounting?: ApiAccounting;
  verdict_note?: string;
};
export type H2HScore = {
  tp?: number; fp?: number; tn?: number; fn?: number;
  precision?: number; recall?: number; f1?: number; fpr?: number;
};

export type BenchmarkStats = {
  kpis?: Kpi[];
  ablation?: {
    available?: boolean;
    task?: string;
    sample?: AblationSample | number | string;
    configs?: AblationConfig[];
  };
  tier_benchmark?: TierBenchmark;
  // Arbitration precision-gate experiment: council NO-GO verdicts re-adjudicated
  // by an adversarial red-team/judge pair, split by ground truth. Counts, not
  // rates — the sample is small.
  arbitration_ablation?: {
    available?: boolean;
    note?: string;
    judge?: string;
    n_adjudicated?: number;
    false_positives_seen?: number;
    false_positives_corrected?: number;
    true_positives_seen?: number;
    true_positives_destroyed?: number;
  };
  // Council vs Slither on IDENTICAL contracts — the only genuine head-to-head.
  // Published-baseline rows are other papers on other datasets (context only).
  head_to_head?: {
    available?: boolean;
    n_common?: number;
    note?: string;
    council?: H2HScore;
    slither?: H2HScore;
    coverage?: { council_scored?: number; slither_scored?: number };
  };
  // The two fixes for the council's OR-gate. Both are reported held-out
  // (weights/threshold fit on dev, scored on a disjoint test split, averaged
  // over random splits).
  proposed_methods?: {
    available?: boolean;
    note?: string;
    weighted?: {
      or_gate?: H2HScore; or_gate_std?: H2HScore;
      tuned?: H2HScore; tuned_std?: H2HScore;
      wins?: number; n_splits?: number; median_tau?: number;
      n_rows?: number; extra_llm_calls?: number | string;
      weights?: Record<string, number>;
      // The per-class-weighted variant, kept as the ablation that justifies
      // NOT using it: it lost to the plain threshold on most splits.
      weighted_variant?: H2HScore;
      weighting_wins?: number;
    };
    calibrated_arbitration?: {
      baseline_f1?: number; tuned_f1?: number; tuned_f1_std?: number;
      baseline_fpr?: number; tuned_fpr?: number;
      wins?: number; n_splits?: number; extra_llm_calls?: number | string;
    };
  };
  // Derived series for the narrative charts: the OR-gate compounding curve and
  // per-specialist reliability. Computed from checkpoints, not hand-entered.
  story?: {
    available?: boolean;
    n_rows?: number;
    compounding?: { specialists: number; n: number; fpr: number }[];
    reliability?: { cls: string; tp: number; fp: number; precision: number }[];
  };
  // What the PRODUCTION verdict rule scores right now, obtained by replaying
  // checkpoints through the live functions rather than re-deriving the rule.
  shipped_rule?: {
    available?: boolean; n?: number; tau?: number; note?: string;
    before?: H2HScore; after?: H2HScore;
    per_tier?: Record<string, { n: number; fpr_before: number; fpr_after: number }>;
  };
  vuln_distribution?: {
    smartbugs_curated?: VulnDistEntry[];
    web3bugs?: VulnDistEntry[];
  };
  published_baselines?: Baseline[];
  thesis?: string;
};

// ─── Auth helpers ───
export async function authRequest(
  mode: "login" | "register",
  username: string,
  password: string
): Promise<User> {
  const r = await fetch(`${API}/${mode}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!r.ok) {
    let detail = `Error ${r.status}`;
    try {
      const d = await r.json();
      if (d.detail) detail = d.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return (await r.json()) as User;
}

// The token is now VERIFIED server-side, so it has to actually be sent. It
// previously sat unused in localStorage while every session route trusted a
// user id taken from the URL — anyone could read anyone's scans by changing a
// number. The server derives the user from this header instead.
function authHeaders(token?: string): HeadersInit {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function listSessions(token: string): Promise<Session[]> {
  // Note the route: /sessions (the caller's own), not /sessions/{id}.
  const r = await fetch(`${API}/sessions`, { headers: authHeaders(token) });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return (await r.json()) as Session[];
}

export async function createSession(token: string): Promise<Session> {
  const r = await fetch(`${API}/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders(token) },
  });
  if (!r.ok) throw new Error(`Could not start session (HTTP ${r.status})`);
  return (await r.json()) as Session;
}

export async function getMessages(sessionId: number, token: string): Promise<Message[]> {
  const r = await fetch(`${API}/sessions/${sessionId}/messages`, { headers: authHeaders(token) });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return (await r.json()) as Message[];
}

export async function logout(token: string): Promise<void> {
  try {
    await fetch(`${API}/logout`, { method: "POST", headers: authHeaders(token) });
  } catch {
    /* best effort: local sign-out proceeds regardless */
  }
}

export async function getBenchmarkStats(): Promise<BenchmarkStats> {
  const r = await fetch(`${API}/stats/benchmark`);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return (await r.json()) as BenchmarkStats;
}

// ─── Sample contracts for the "try it" demo flow (GET /api/samples) ───
export async function getSamples(): Promise<SampleContract[]> {
  const r = await fetch(`${API}/samples`);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  const d = await r.json();
  return (Array.isArray(d) ? d : []) as SampleContract[];
}

async function errDetail(r: Response): Promise<string> {
  try {
    const d = await r.json();
    if (d.detail) return typeof d.detail === "string" ? d.detail : JSON.stringify(d.detail);
  } catch {
    /* ignore */
  }
  return `HTTP ${r.status}`;
}

// ─── SSE: stream the council (POST /api/analyze/council/stream) ───
// Consumed via fetch + ReadableStream (not EventSource since it's a POST).
export async function streamCouncil(
  code: string,
  onEvent: (ev: StreamEvent) => void,
  opts: { sessionId?: number | null; signal?: AbortSignal } = {}
): Promise<void> {
  // AnalyzeReq has session_id + user_id OPTIONAL. We send { code } always and
  // attach session_id ONLY when the user actually has one — anonymous/trial
  // scans (no login, no session) work with just { code }. We never send user_id.
  const payload: { code: string; session_id?: number } = { code };
  if (opts.sessionId != null) payload.session_id = opts.sessionId;

  const r = await fetch(`${API}/analyze/council/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal: opts.signal,
  });
  if (!r.ok || !r.body) throw new Error(await errDetail(r));

  const reader = r.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // SSE frames are separated by a blank line.
    let idx: number;
    while ((idx = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      const dataLines = frame
        .split("\n")
        .filter((l) => l.startsWith("data:"))
        .map((l) => l.slice(5).trim());
      if (!dataLines.length) continue;
      const json = dataLines.join("\n");
      try {
        // Forward EVERY event through untouched — including newer event types
        // like "routing" and "arbitrating". No allow-list here on purpose.
        onEvent(JSON.parse(json) as StreamEvent);
      } catch {
        /* skip malformed frame */
      }
    }
  }
  // Flush any trailing frame without a terminating blank line.
  const tail = buffer.trim();
  if (tail.startsWith("data:")) {
    try {
      onEvent(JSON.parse(tail.slice(5).trim()) as StreamEvent);
    } catch {
      /* ignore */
    }
  }
}
