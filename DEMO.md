# Running the demo

Everything below runs on one laptop with no API key and no network. The
contract source never leaves the machine.

---

## 1. One-time setup

```bash
# Ollama + the three council models
ollama pull llama3.2:3b          # 2.0 GB  — logic roles
ollama pull gemma3:4b            # 3.3 GB  — DoS / gas
ollama pull qwen2.5-coder:3b     # 1.9 GB  — code roles, SMALL-GPU profile
ollama pull qwen2.5-coder:7b     # 4.7 GB  — code roles, benchmark profile
```

```bash
cd backend
python -m venv venv && venv/Scripts/activate      # or source venv/bin/activate
pip install -r requirements.txt
```

```bash
cd frontend
npm install
```

**No `.env` is required.** The tool is local-only by default: `LLM_BACKEND`
defaults to `ollama`, and any hosted provider raises unless you explicitly set
`THIRDEYE_ALLOW_CLOUD=1`.

---

## 2. Pick a model profile — this matters more than it sounds

The code-reading roles are the expensive ones. Which model fills that slot is
set by `OLLAMA_CODER_MODEL`.

| GPU VRAM | Set | Why |
|---|---|---|
| ≥ 8 GB | *(leave default)* `qwen2.5-coder:7b` | What the published benchmark used |
| ≤ 4 GB | `OLLAMA_CODER_MODEL=qwen2.5-coder:3b` | The 7B does not fit and degrades badly |

**Measured on the demo laptop (RTX 3050, 4 GB), same contracts:**

| | latency | specialist errors | agreed with expected |
|---|--:|--:|--:|
| `qwen2.5-coder:3b` | **22–38 s** | **3 / 10 runs** | **6 / 10** |
| `qwen2.5-coder:7b` | 46–62 s | 4 in the first 7 runs | 2 / 7 |

The 7B is not a better model here — it is 4.68 GB against 4 GB of VRAM, so it
spills, and under memory pressure it dies with
`CUDA error: shared object initialization failed`, erroring a specialist
mid-scan. A dead specialist cannot raise a flag, so the verdict degrades.

> Do **not** read the 3B row as "the small model is better." It is better *on
> this machine*. On the campus GPU the 7B is the correct choice, and that is
> the configuration the benchmark numbers come from.

---

## 3. Start it

Three things, in this order. **Ollama first** — if it is not serving, preflight
reports "Ollama is not reachable at http://localhost:11434" and every scan
fails, which is the single most likely thing to go wrong.

```bash
# terminal 0 — the engine
ollama serve
```

Then two more terminals.

```bash
# terminal 1 — backend
cd backend
OLLAMA_CODER_MODEL=qwen2.5-coder:3b uvicorn main:app --port 8000
```

```bash
# terminal 2 — site
cd frontend
npm run dev
```

Open <http://localhost:5173>. Go to **Tool**. The banner at the top is a
preflight check: it verifies the council's models **by name**, not by count,
and tells you exactly what is missing and the command to fix it.

---

## 4. Before you present — run this

```bash
cd backend
OLLAMA_CODER_MODEL=qwen2.5-coder:3b python -u build_demo_cache.py
```

It scans all six samples, prints what each returned, and writes
`frontend/src/site/demo-cache.json`. Two reasons to run it:

1. **It proves the machine works** right now, with the models actually
   installed, minutes before you walk in.
2. **It warms the models.** The first call of a session is the slowest; after
   this, scans in the room are the warm numbers.

A clean run ends with `0 specialist error(s)`. Anything else, investigate
before presenting rather than discovering it live.

---

## 5. What to expect in the room

**A scan takes 22–38 seconds** on the small-GPU profile. The Tool page shows a
live timer and each specialist turning from *waiting* to *clean* or *flagged*,
so the wait is legible rather than a frozen screen.

**The tool will get some samples "wrong", and that is the demo.** It raises a
false alarm on 45.9% of safe contracts on the full benchmark, and the sample
set is a deliberate 3 safe / 3 vulnerable so a false alarm can show up live
rather than being something you only read about on the Findings page. On the
last recorded run it did exactly that: 4 of 6 matched, with two safe contracts
flagged. When
a verdict disagrees with the sample's expected answer, the page says so and
links to why.

If someone asks why you did not tune the samples until they all pass: because
the number on the Findings page is the measured false-alarm rate of the
shipped configuration, and a demo rigged to beat it would contradict the one
result this project is actually about.

---

## 6. If something breaks

| Symptom | Cause | Fix |
|---|---|---|
| Preflight red, "models not in the store it is serving" | Ollama started with `OLLAMA_MODELS` pointing at a different model directory | Restart Ollama with that variable unset |
| `CUDA error: shared object initialization failed` | Coder model too big for VRAM | `OLLAMA_CODER_MODEL=qwen2.5-coder:3b` |
| Every verdict is INCONCLUSIVE | Half or more of the specialists errored — this is the fail-closed rule working | Check preflight; usually a missing model |
| Scan hangs past ~90 s | A model is loading cold, or another process holds the GPU | Wait once; if it repeats, restart Ollama |
| Tool page says "backend not reachable" | Only the frontend is running | Start `uvicorn` in the second terminal |
| Preflight says Ollama unreachable at :11434 | `ollama serve` is not running | Start it; this is the most common failure |
| A scan never finishes and the stage rail sits on "council" | Arbitration is on; the local judge is ~83 s per finding | Unset `THIRDEYE_ARBITRATION` — it is OFF by default |

**Offline fallback:** every other page on the site is static and needs no
backend at all. If the backend cannot start, the content pages still present
fine — only live scanning is lost.
