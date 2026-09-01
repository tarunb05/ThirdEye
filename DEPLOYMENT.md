# Deploying ThirdEye

ThirdEye runs in two modes that share the same codebase. Nothing in the analysis logic
(`preanalyze_code`, the vulnerability-scanning prompts, `_merge_vulns`, `_determine_verdict`,
`dataset_runner.py`'s evaluation methodology) changes between them — only infrastructure does.

## The two modes

| | **local-dev** | **deployed-demo** |
|---|---|---|
| LLM | Ollama, local | Groq (hosted, free tier) |
| Database | SQLite (`backend/thirdeye.db`) | Postgres (e.g. Neon) |
| Vector memory (ChromaDB) | on | off |
| Frontend → backend | Vite dev proxy | direct HTTPS to Render |
| CORS | `http://localhost:5173` | the deployed Vercel URL |

### Env vars that differ between the two modes

| Var | local-dev | deployed-demo |
|---|---|---|
| `LLM_BACKEND` | `ollama` (default) | `groq` |
| `GROQ_API_KEY` | unset | your Groq key |
| `GROQ_MODEL` | unset (unused) | `llama-3.3-70b-versatile` (default) |
| `DATABASE_URL` | unset → SQLite | your Postgres connection string |
| `ENABLE_VECTORDB` | unset → `true` | `false` |
| `ALLOWED_ORIGINS` | unset → `http://localhost:5173` | your Vercel URL |
| `VITE_API_URL` (frontend) | unset → `/api` via Vite proxy | full Render backend URL + `/api` |

All of these have working defaults for local dev in `backend/.env.example` and
`frontend/.env.example` — copy them to `.env` and you're running the same way as before this
pass, with Ollama and SQLite, untouched.

**Breaking change:** password hashing moved from raw SHA-256 to bcrypt (via passlib). Any
existing local SQLite users created before this change will no longer be able to log in —
this is a one-time breakage. Just register again; there's no migration path and none is needed
for a capstone-scale user table.

---

## Render (backend)

A `render.yaml` blueprint is checked in at the repo root. If Render's blueprint sync doesn't
pick it up cleanly (blueprint support for `rootDir` + free-tier Python services has been known
to be flaky), set these up manually in the dashboard instead:

1. **New Web Service** → connect this repo.
2. **Root Directory:** `backend`
3. **Runtime:** Python 3
4. **Build Command:**
   ```
   pip install -r requirements.txt && (pip install solc-select && solc-select install 0.8.20 && solc-select use 0.8.20 || echo "solc/Slither setup failed, continuing without it")
   ```
   The `solc-select` part is wrapped so a failure there **cannot** break the deploy —
   `services/slither.py` already degrades gracefully (`FileNotFoundError` → `{"status": "skipped"}`)
   when Slither/solc aren't available, so the app boots and serves requests either way.
5. **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. **Environment variables** to set in the dashboard:
   - `PYTHON_VERSION=3.11.9` — **set this one first.** Render's default Python (3.14 at time of
     writing) has no prebuilt wheel for `pydantic-core==2.23.2`, so pip falls back to building it
     from source via Rust/maturin — which fails on Render's build sandbox because the Cargo
     registry cache directory is read-only there. Pinning the Python version sidesteps the
     source build entirely by letting pip pull pydantic-core's existing wheel.
   - `LLM_BACKEND=groq`
   - `GROQ_API_KEY=<your key>`
   - `GROQ_MODEL=llama-3.3-70b-versatile` (or leave default)
   - `DATABASE_URL=<your Neon/Postgres connection string>`
   - `ENABLE_VECTORDB=false`
   - `ALLOWED_ORIGINS=<your Vercel URL>` — **you won't know this until after Step 2 below.
     Deploy the backend first with a placeholder, then come back and fix it.**

Once deployed, note the Render URL (e.g. `https://third-eye-capstone.onrender.com`).

## Vercel (frontend)

Vercel auto-detects the Vite framework from `frontend/package.json` — no `vercel.json` is
needed (the app has no client-side router; it's a single-page app with state-based view
switching, so there are no SPA-fallback rewrites to configure).

1. **New Project** → connect this repo → set **Root Directory** to `frontend`.
2. Vercel auto-fills build command (`npm run build` → runs `tsc -b && vite build`) and output
   directory (`dist`). Leave as detected.
3. **Environment variable:** `VITE_API_URL=https://third-eye-capstone.onrender.com/api`
   (use the Render URL from the previous section, with the `/api` suffix).
4. Deploy. Note the resulting Vercel URL (e.g. `https://thirdeye.vercel.app`).

### The ordering caveat (read this before you start)

Render needs the Vercel URL (for `ALLOWED_ORIGINS`). Vercel needs the Render URL (for
`VITE_API_URL`). They depend on each other, so there's an unavoidable two-pass deploy:

1. Deploy the **backend** to Render first, with `ALLOWED_ORIGINS` set to a placeholder.
2. Copy the resulting Render URL.
3. Deploy the **frontend** to Vercel with `VITE_API_URL` set to that Render URL.
4. Copy the resulting Vercel URL.
5. Go back to Render, set `ALLOWED_ORIGINS` to the real Vercel URL, and **redeploy the backend
   once** (Render redeploys automatically on env var change, or trigger manually).

After that one backend redeploy, both ends point at each other correctly and you're done.

---

## What this actually is, for a non-technical visitor

A teacher (or anyone else) visiting the Vercel URL will see a chat-style web app: they can
register/log in, paste a Solidity smart contract, and get back a GO/NO-GO verdict with a list
of flagged vulnerabilities, a plain-English summary, and a downloadable PDF audit report. There's
also a dataset dashboard showing batch results across a 50-contract Etherscan-verified test set.
Under the hood it's a single hosted LLM call (Groq) combined with Slither static analysis (when
available) and a regex-based pre-filter that suppresses some hallucinated findings — **not** the
multi-agent "council" of model-diverse specialists, the retrieval-grounded exploit corpus, or the
dynamic exploit-confirmation/fuzzing layer described in the Argus plan. None of those exist in
any version of this codebase yet, deployed or otherwise — this pass only made the *existing*
single-LLM pipeline deployable, it didn't add new analysis capability.
