"""Record a real council scan as a replayable event trace.

The exhibit needs to show a scan resolving specialist-by-specialist without
depending on a laptop GPU being warm during a panel review. This captures an
ACTUAL run (same code path the live button uses) with wall-clock offsets, so
the replay is a recording of real behaviour rather than an animation of
invented data. Nothing here is synthesised.
"""
import asyncio, json, sys, time
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

from eval.loaders import thirdeye_bench as tb
from services.council import run_council_stream
from services.router import select_specialists
from services.llm import preanalyze_code
from services.slither import run_slither

OUT = Path(__file__).resolve().parents[2] / "frontend" / "src" / "data" / "replays"


async def record(contract_id: str, item, label: str):
    code = item.read_code()
    # Route first, exactly as POST /api/analyze/council/stream does. Calling the
    # council directly runs all eight specialists, which is NOT what the product
    # does — and it showed: an unrouted run of OpenZeppelin AccessControl flagged
    # 4 of 8 and blocked at risk 0.98, where the routed pipeline selects 2 and
    # clears it at 0.60. A recording has to be of the real thing.
    features = preanalyze_code(code)
    # Slither output feeds the router, and it prunes hard: without it the router
    # woke 6 specialists on OpenZeppelin AccessControl and the pooled risk hit
    # 0.98 (a false alarm); with it the pipeline selects far fewer and clears the
    # contract. Skipping this step would have recorded the tool behaving worse
    # than it does.
    static = None
    try:
        from services.llm import _parse_slither
        out = await asyncio.to_thread(run_slither, code)
        if out.get("status") == "completed":
            static = _parse_slither(out)
    except Exception:
        static = None
    routed = select_specialists(code, features, static)
    print(f"  slither: {'used' if static else 'unavailable'}")
    print(f"  router selected {len(routed['roles'])}: {', '.join(routed['roles'])}")
    t0 = time.time()
    events = []
    async for ev in run_council_stream(code, backend="ollama", seed=0, roles=routed["roles"]):
        ev = dict(ev)
        ev["t"] = round(time.time() - t0, 2)
        if ev.get("event") == "final":
            r = ev["result"]
            ev["result"] = {k: r.get(k) for k in
                            ("final_verdict", "verdict_reason", "vulnerabilities",
                             "summary", "raven_note", "contract_name", "stats", "routing")}
        events.append(ev)
        print(f"  [{ev['t']:6.1f}s] {ev.get('event'):16} {ev.get('role') or ''}")
    rec = {"contract_id": contract_id, "label": label,
           "routed_roles": routed["roles"],
           "ground_truth": item.ground_truth_label,
           "duration_s": round(time.time() - t0, 1),
           "code": code, "events": events,
           "recorded_at": time.strftime("%Y-%m-%d %H:%M:%S")}
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"{label}.json"
    p.write_text(json.dumps(rec, indent=1), encoding="utf-8")
    print(f"-> {p.name}  {len(events)} events, {rec['duration_s']}s\n")


async def main():
    safe = tb.load_safe(tier="audited_library")[0]
    vuln = tb.load_vuln(tier="curated")[0]
    await record(safe.contract_id, safe, "safe")
    await record(vuln.contract_id, vuln, "vulnerable")

asyncio.run(main())
