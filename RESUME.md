# Resume after a shutdown

Everything is checkpointed **per contract**, so a shutdown costs only the
contracts actually in flight (at most 2–3). Nothing already measured is lost and
nothing needs redoing.

## What survives / what dies

| | survives a shutdown? |
|---|---|
| All checkpoints (`backend/eval/checkpoints/`) | **yes** — this is every result |
| Scored reports (`backend/eval/results/`) | **yes** |
| Enriched snapshot + live Vercel site | **yes** — already deployed |
| Paper draft, decision log | **yes** |
| Running batch jobs (Phase B / Phase D) | no — relaunch, they skip completed work |
| Ollama server | no — must be restarted **correctly**, see gotcha #1 |
| Contracts mid-analysis | lost, automatically retried on relaunch |

State as of writing: 231 benchmark terminal · 124 quarantined/retryable ·
119 arbitration-sweep · 42 seed-1 rows.

---

## GOTCHA #1 — Ollama must NOT be started from a plain shell

Your shell profile sets `OLLAMA_MODELS=D:\AI-Data\models\ollama`, but the
council's models live in the **default** store (`C:\Users\umara\.ollama\models`).
Start `ollama serve` from a normal terminal and it serves a different, nearly
empty model store — every call returns HTTP 404 and the run aborts at the
pre-flight probe. This cost an hour to diagnose once already.

Start it like this (unsets the override, caps residency):

```bash
env -u OLLAMA_MODELS OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_KEEP_ALIVE=60m ollama serve
```

Verify all four council models are visible before launching anything:

```bash
curl -s http://127.0.0.1:11434/api/tags
```

Expect: `qwen2.5-coder:7b`, `llama3.2:3b`, `gemma3:4b`, `qwen3:8b`.

**Why `OLLAMA_MAX_LOADED_MODELS=1`:** on a 4GB GPU only one model is resident;
any other model runs CPU-only at 224–270s/call regardless of its size. Capping
residency at 1 plus the model-grouped scheduling in `services/council.py` keeps
whichever model is running on the GPU.

## GOTCHA #2 — never run Phase B and Phase D at the same time

Both need the single GPU. Measured: 3 of 5 contracts abstained under contention.
No data is corrupted (abstentions are quarantined and retried) but throughput is
wasted. Phase D's script already waits for Phase B.

## GOTCHA #3 — `pkill -f` does not reliably kill these on Windows

Orphaned runs kept executing and competed for the GPU twice during development.
After killing jobs, always verify:

```bash
ps -W | grep venv_win        # should be empty before relaunching
```

Kill survivors by their Windows PID (4th column): `taskkill //F //PID <winpid>`

---

## Relaunch commands

```bash
cd /c/Users/umara/Downloads/ThirdEye/backend
```

**1. Phase B — arbitration judge scores (quota-bound, resumes automatically):**

```bash
nohup bash eval/phaseB.sh > eval/results/phaseB.log 2>&1 &
```

**2. Phase D — benchmark extension + multi-seed (waits for B automatically):**

```bash
nohup bash eval/phaseD.sh > eval/results/phaseD.log 2>&1 &
```

**3. Score everything currently collected (instant, no LLM calls):**

```bash
./venv_win/Scripts/python.exe -m eval.run_benchmark --backend ollama_noarb --report-only
```

**4. The proposed method, on held-out splits (instant, no LLM calls):**

```bash
./venv_win/Scripts/python.exe -m eval.weighted_aggregation --alpha 1.0 --dev-frac 0.5
```

**5. Refresh the live site with current numbers:**

```bash
cd /c/Users/umara/Downloads/ThirdEye/backend && ./venv_win/Scripts/python.exe -c "from services.stats import write_snapshot; write_snapshot()" && cd ../frontend && npm run build && cd .. && vercel --prod --yes
```

Deploy must run from the repo **root**, not `frontend/` — the Vercel project's
Root Directory is already set to `frontend`, so deploying from inside it makes
Vercel look for `frontend/frontend`.

---

## Progress check

```bash
cd /c/Users/umara/Downloads/ThirdEye/backend
echo "benchmark: $(ls eval/checkpoints/benchmark/ollama_noarb/seed0/*.json | wc -l)"
echo "arb_sweep: $(ls eval/checkpoints/arb_sweep/*.json | wc -l)"
```

## If you only have time for one thing

Steps 3 and 4 need **no GPU, no API quota, and no running jobs** — they score
data already on disk and take seconds. That alone regenerates every number in
the paper and on the site.
