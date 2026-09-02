import { useState } from "react";
import { EX, MONO, SANS } from "../../lib/exhibit-theme";
import { ScanReplay, type Replay } from "./ScanReplay";
import { LiveScan } from "./LiveScan";
import safeReplay from "../../data/replays/safe.json";
import vulnReplay from "../../data/replays/vulnerable.json";

/** The tool, inline in the page — not a separate destination.
 *
 * Splitting the artifact onto its own route meant maintaining two design
 * systems and asking a reader to leave the argument to see the evidence. Here
 * the scanner sits inside the flow: pick a contract whose answer is already
 * known, watch a recorded run, or paste your own and run it live.
 *
 * Recorded is the default because a panel review cannot depend on a warm GPU,
 * and because a known-answer contract makes the result checkable. Live exists
 * so "is that just a video?" has an answer.
 */

const SAMPLES = [
  { key: "vulnerable" as const, label: "Known vulnerable", replay: vulnReplay as unknown as Replay,
    blurb: "A curated contract with a confirmed bug. Six specialists engage, all flag, and it blocks." },
  { key: "safe" as const, label: "Known safe", replay: safeReplay as unknown as Replay,
    blurb: "An audited OpenZeppelin component. One specialist engages, and it clears." },
];

export function TryIt() {
  const [pick, setPick] = useState<"vulnerable" | "safe" | "own">("vulnerable");
  const [mode, setMode] = useState<"recorded" | "live">("recorded");
  const [own, setOwn] = useState("");

  const sample = SAMPLES.find((s) => s.key === pick);
  const code = pick === "own" ? own : sample?.replay.code ?? "";
  const label = pick === "own" ? "your contract" : sample?.replay.contract_id ?? "";
  // A pasted contract has no recording, so it can only be run live.
  const effMode = pick === "own" ? "live" : mode;

  const btn = (active: boolean) => ({
    fontFamily: MONO, fontSize: 11, letterSpacing: ".05em", padding: "8px 14px",
    cursor: "pointer", border: "none",
    background: active ? EX.ink : "transparent",
    color: active ? EX.surface : EX.inkMuted,
  });

  return (
    <div style={{ fontFamily: SANS }}>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 16 }}>
        <div style={{ display: "flex", border: `1px solid ${EX.ink}` }}>
          {SAMPLES.map((s) => (
            <button key={s.key} onClick={() => setPick(s.key)} style={btn(pick === s.key)}>
              {s.label.toUpperCase()}
            </button>
          ))}
          <button onClick={() => setPick("own")} style={{ ...btn(pick === "own"), borderLeft: `1px solid ${EX.ink}` }}>
            PASTE YOUR OWN
          </button>
        </div>

        {pick !== "own" && (
          <div style={{ display: "flex", border: `1px solid ${EX.hairline}` }}>
            {(["recorded", "live"] as const).map((m) => (
              <button key={m} onClick={() => setMode(m)} style={btn(mode === m)}>
                {m === "recorded" ? "RECORDED" : "RUN LIVE"}
              </button>
            ))}
          </div>
        )}
      </div>

      {pick !== "own" && sample && (
        <p style={{ fontSize: 14.5, color: EX.inkMuted, lineHeight: 1.55, marginBottom: 14, maxWidth: "66ch" }}>
          {sample.blurb}
        </p>
      )}

      {pick === "own" && (
        <div style={{ marginBottom: 14 }}>
          <textarea
            value={own}
            onChange={(e) => setOwn(e.target.value)}
            spellCheck={false}
            placeholder={"// Paste Solidity here\npragma solidity ^0.8.0;\n\ncontract MyContract {\n  ...\n}"}
            style={{
              width: "100%", minHeight: 190, resize: "vertical",
              fontFamily: MONO, fontSize: 12.5, lineHeight: 1.6,
              background: "#fff", color: EX.ink,
              border: `1px solid ${EX.hairline}`, padding: "12px 14px", outline: "none",
            }}
          />
          <div style={{ fontFamily: MONO, fontSize: 11, color: EX.slate, marginTop: 6 }}>
            {own.trim() ? `${own.split("\n").length} lines · runs against the live backend` : "no recording exists for a pasted contract, so this runs live"}
          </div>
        </div>
      )}

      <div style={{ background: "#fff", border: `1px solid ${EX.hairline}`, padding: "20px 22px" }}>
        <div style={{ fontFamily: MONO, fontSize: 11, color: EX.slate, marginBottom: 14 }}>{label}</div>
        {effMode === "recorded" && sample ? (
          <ScanReplay key={pick} replay={sample.replay} speed={7} />
        ) : code.trim() ? (
          <LiveScan key={`${pick}-live`} code={code} contractId={label} />
        ) : (
          <div style={{ fontFamily: MONO, fontSize: 12, color: EX.slate, padding: "26px 0" }}>
            Paste a contract above to run a scan.
          </div>
        )}
      </div>
    </div>
  );
}
