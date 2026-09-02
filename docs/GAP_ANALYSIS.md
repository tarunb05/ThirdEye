# ThirdEye → Argus: Gap Analysis

Audit pass only. No code was modified, deleted, or created — this document is the sole output.

Note on sourcing: `docs/ARGUS_PLAN.md` does not exist anywhere in this repo (confirmed by full-tree search). The plan content used for Step 2/3 below was supplied directly by the user as a PDF ("Argus A-Z Plan (v2, hardware-adapted)") in this conversation, not read from a file. If a `docs/ARGUS_PLAN.md` should exist going forward, it should be created from that PDF as a follow-up — it currently isn't checked into the repo at all.

---

## Step 1 — Repo Inventory

Working directory is `thirdeye-v2/` and **is itself the live app's root** (backend/ and frontend/ live directly under it). The confusing part: there is *also* a nested `thirdeye-v2/thirdeye-v2/` subdirectory that is a full, separate, older copy of the same project. All paths below are relative to the outer `thirdeye-v2/` root unless stated otherwise.

### Root-level files

| Path | Classification | Notes |
|---|---|---|
| `backend/` | **LIVE** | The running FastAPI app. See breakdown below. |
| `frontend/` | **LIVE** | The running React/Vite app. See breakdown below. |
| `run.ps1` | **LIVE** | Documented launcher (README references it); spins up venv, npm install, Ollama check, starts both servers. This is how the product is actually run. |
| `README.md` | **LIVE** | Describes the current (root) app's structure and setup; accurate. |
| `thirdeye-v2/` (nested) | **DEAD** | Entire subtree. Confirmed via `diff` against root `backend/main.py`: nested version is FastAPI app `version="2.0"`, imports `services.llm.summarize_code/model_a_fast/model_b_logic/model_c_edge` and a separate `services/aggregator.py` — an earlier multi-model-vote architecture that was abandoned. Has no auth, no sessions, no `vectordb.py`, no `report.py`, no dataset runner. Strictly superseded by root. Nothing imports into it; nothing depends on it. |
| `etherscan_verified-20260420T143345Z-3-001/` (50 `.sol` files) | **LIVE** | Consumed by `backend/dataset_runner.py` via `SOL_ROOT = BASE_DIR.parent / "etherscan_verified-..."`. This is real input data for the dataset runner. |
| `etherscan_verified-20260420T143345Z-3-001.zip` | **DEAD** | Redundant — the zip's contents are already extracted into the folder above. Pure disk bloat (330KB). |
| `ThirdEye-dataset-index.xlsx` | **DEAD (orphaned)** | No script in the repo reads this file (`grep -ri xlsx backend/` only matches `index.json`'s own filename and `main.py`'s comment, not actual xlsx parsing code). `openpyxl` is in `requirements.txt` but unused by any committed file. This was almost certainly the source someone hand-copied into `datasets/index.json` once, by hand, and the generation script was never committed (or was deleted). Not reproducible as-is. |
| `examples/go.txt`, `examples/no-go.txt`, `examples/combined.txt` | **DEAD** | Confirmed zero references in `backend/` or `frontend/src/`. Sample contracts for manual copy-paste testing, not wired into the app or any test suite. |
| `code_recursor.py` | **UTILITY** | Dev script; recursively dumps all source files into `directory_recursor_output.txt` for sharing with an LLM. Not part of the shipped product. |
| `export-code.ps1` | **UTILITY** | Same purpose as above, PowerShell version, writes `thirdeye-code-export.txt`. Not part of the shipped product. |
| `directory_recursor_output.txt` | **DEAD** | Stale generated output of `code_recursor.py` (263KB). An artifact, not a source file. |
| `thirdeye-code-export.txt` | **DEAD** | Stale generated output of `export-code.ps1` (99KB, dated Apr 21). Artifact. |
| `no i need a direct action plan on what i can use t.md` | **DEAD** | Exported Perplexity AI chat transcript (stray export, has the Perplexity logo embedded). Historical planning chatter, not documentation. |
| `so basically we only use the sol files and label t.md` | **DEAD** | Same — exported chat transcript. |
| `we have a presentation on wednesday. is it possibl.md` | **DEAD** | Same — exported chat transcript. |
| `what will the code4arena and tob files + audit rep.md` | **DEAD** | Same — exported chat transcript. |
| `.claude/`, `.git/`, `.gitignore` | **UTILITY** | Tooling/VCS, not product code. |

### `backend/` breakdown (LIVE app)

| Path | Classification | Notes |
|---|---|---|
| `main.py` | LIVE | FastAPI app: auth, sessions/chat, `/api/analyze`, `/api/report`, `/api/ollama-status`, `/api/dataset/*`. |
| `db.py` | LIVE | aiosqlite — users/sessions/messages. Passwords hashed with raw SHA-256, no salt (flag for later — auth debt the plan itself calls out in its "industry-readiness checklist": *"JWT + argon2/bcrypt ... fix the original auth debt"*). |
| `dataset_runner.py` | LIVE | Batch-runs the pipeline over the 50 Etherscan contracts; writes `datasets/index.json` + `results_summary.csv`. **See Step 2's evaluation-harness finding — this is methodologically broken in `--static-only` mode.** |
| `services/llm.py` | LIVE | `preanalyze_code()` (regex feature flags), single Ollama call (`_query`/`_detect_model`), `_scan_vulnerabilities`, `_merge_vulns` with Slither, verdict logic, "Raven" personality text. This is the entire current "analysis engine." |
| `services/slither.py` | LIVE | Subprocess wrapper around the real `slither` CLI; gracefully degrades if not installed. |
| `services/vectordb.py` | LIVE | ChromaDB wrapper; stores/retrieves the app's *own past analysis results* (not an external exploit corpus). |
| `services/report.py` | LIVE | ReportLab PDF generator — fully working, dark-themed audit report. |
| `services/__init__.py` | LIVE | Empty package marker. |
| `requirements.txt`, `.env.example` | LIVE | Config. |
| `datasets/index.json`, `datasets/results_summary.csv` | LIVE (data) | 50-contract dataset state. |
| `venv/` | UTILITY | Local virtualenv, gitignored, not source. |

### `frontend/` breakdown (LIVE app)

| Path | Classification | Notes |
|---|---|---|
| `src/App.tsx` (828 lines) | LIVE | Single-file UI: auth, session list, chat-style analysis flow, PDF download, dataset dashboard (`/api/dataset/*` calls confirmed via grep). |
| `src/main.tsx`, `src/index.css` | LIVE | Entry point + Tailwind. |
| `vite.config.ts`, `tsconfig.json`, `package.json`, `index.html`, `postcss.config.js` | LIVE | Build config. |
| `dist/`, `node_modules/`, `package-lock.json` | UTILITY | Build artifacts/deps, gitignored (dist, node_modules) or lockfile noise. |

**Bottom line on Step 1:** the actually-running product is small — one FastAPI service, one regex-feature-extractor + single-Ollama-call "analysis," a Slither subprocess, a self-referential ChromaDB cache, a PDF generator, and a React chat UI. Everything else at root is either an abandoned duplicate, a generated artifact, or exported chat logs that should be deleted in a cleanup pass (not done here, per instructions).

---

## Step 2 — Argus Architecture vs. Current LIVE Code

Per-component mapping. "LIVE code" = the root `backend/`+`frontend/` only.

### 1. Ingest & Normalize → Unified Program Representation (UPR)
- **(a) Exists today?** Barely. `services/llm.py:preanalyze_code()` does regex pattern-matching over raw source text (`has_external_call`, `has_delegatecall`, `has_selfdestruct`, etc.) — a flat bag of booleans, not an AST/CFG/call-graph. No `solc` invocation, no slicing, no language tag, no adapter interface.
- **(b) Salvage verdict:** **Delete and rebuild from scratch.** Regex flags cannot be incrementally evolved into a UPR — they're a fundamentally different representation (no structure, no node identity to anchor evidence units to, as the plan's evidence-anchoring scheme requires). The *feature flags themselves* are reusable as a cheap pre-filter/sanity-check layer on top of a real UPR, not as the UPR.
- **(c) External dependency before code can be written:** Needs a Solidity compiler toolchain (`solc`/`py-solc-x`/`solc-select`) and ideally Slither's own AST/IR as the structural base. This is pip/binary-installable without WSL2 — Claude Code can do this unattended once permitted to run installs.

### 2. Static evidence harvesters (Slither/Aderyn/Semgrep) + 2b Symbolic (Mythril/Halmos)
- **(a) Exists today?** Yes, partially — `services/slither.py:run_slither()` and `services/llm.py:_parse_slither()`/`_merge_vulns()`. Real, working Slither subprocess integration.
- **(b) Salvage verdict:** **Salvageable with rework.** Current version: writes the contract to one temp file (no multi-file/import resolution, can't handle a real Foundry/Hardhat repo), hardcoded 30s timeout, broad `except: return []` swallowing on parse failure, and findings aren't anchored to UPR node IDs — just a `line` number guess. Needs: multi-file ingestion, normalized evidence-unit schema, and Aderyn + Semgrep added alongside Slither.
- **(c) External dependency:** Slither (pip + a compiler) and Semgrep (pip) install fine natively on Windows. Aderyn is a standalone Rust binary (`cargo install aderyn`) — also native-Windows-installable, no WSL2 strictly required. **Mythril and Halmos are where the plan's own WSL2 requirement bites** — both are Linux-native tooling per the plan's hardware note. This component is only fully buildable after WSL2 exists (see Step 4); the Slither/Aderyn/Semgrep slice can proceed without it.

### 3. Retrieval grounding (Qwen3-Embedding → LanceDB, curated exploit corpus)
- **(a) Exists today?** Yes, but it is *exactly* the thing the plan's own design-deliberation section explicitly rejects: `services/vectordb.py:store_analysis()`/`find_similar()` is ChromaDB storing the app's own past run outputs (a 300-char code snippet + verdict + vuln types). The plan literally says: *"v1 idea — 'RAG over our own past runs' (the original ThirdEye scaffold). Rejected: thin, circular, no ground signal."* That is precisely what's live right now.
- **(b) Salvage verdict:** **Delete and rebuild from scratch.** Different embedding model (Qwen3-Embedding vs. Chroma's default), arguably a different vector store (plan picked LanceDB to dodge a server process — though Chroma's `PersistentClient` is also embedded/serverless, so this swap is a nice-to-have, not mandatory), and — the actual hard part — an entirely new curated corpus of real exploit+fix narratives from Solodit/Code4rena/SmartBugs/DeFiHackLabs that does not exist anywhere in this repo today.
- **(c) External dependency:** Building the corpus is a data-collection task (scraping/downloading from Solodit/Code4rena/SmartBugs/DeFiHackLabs), which has ToS implications the user should sign off on explicitly (see Step 4) — this is not something to do unattended/silently. Pulling Qwen3-Embedding via Ollama is a straightforward local download, no signup needed.

### 4. The Council (model-diverse specialist agents)
- **(a) Exists today?** Only the single-LLM baseline, not the council. `services/llm.py:_detect_model()`/`_query()`/`_scan_vulnerabilities()` runs exactly one auto-detected local Ollama model through two prompts (a summary, a vuln scan). No role specialization, no model diversity, no concurrency across different base models, no LangGraph.
- **(b) Salvage verdict:** **Keep the existing single-LLM path as-is — it's not dead weight, it's the "single-LLM" baseline row the plan's own ablation table requires** (current-ThirdEye and single-LLM are two separate baselines the plan wants re-run; this code conveniently *is* the single-LLM one). The actual council (8 OWASP-category specialists, each on a different base model, via LangGraph) is **new code, built from scratch** — nothing today does role prompts, model diversity, or parallel specialist execution.
- **(c) External dependency:** Free API signups for Groq, Cerebras, and OpenRouter (the "council models" tier) are required before any council code can be *run* (though the orchestration code itself can be written and stubbed without keys). `pip install langgraph` has no system dependency beyond Python.

### 5. Dynamic exploitability confirmation (ItyFuzz/Medusa/Foundry/Echidna)
- **(a) Exists today?** Nothing. Zero references to Foundry, Echidna, Medusa, or ItyFuzz anywhere in the live code.
- **(b) Salvage verdict:** **Build from scratch, entirely.** There is no harness-generation code, no invariant/property templating, no witness-capture/promotion logic (`SUSPECTED → CONFIRMED`).
- **(c) External dependency: this is the hardest blocker in the whole plan.** The plan's own hardware note states these tools are Linux-native and requires WSL2 (Ubuntu) on Windows. WSL2 enablement is a Windows feature toggle that typically needs a reboot and (depending on the machine's policy) admin rights — **this cannot be done by Claude Code; it is a user action, full stop.** No code for this component should be attempted until WSL2 + Foundry/ItyFuzz/Medusa/Echidna are confirmed installed and reachable from a shell Claude Code can use.

### 6. Evidence-anchored debate & arbitration
- **(a) Exists today?** Only a faint echo: `services/llm.py:_merge_vulns()` does key-based dedup between LLM findings and Slither findings, bumping confidence on overlap. That's a heuristic merge, not a debate — there's no PROPOSER/RED-TEAM/JUDGE structure, no requirement to cite evidence units, no disagreement clustering.
- **(b) Salvage verdict:** **Delete and rebuild from scratch.** `_merge_vulns()`'s confidence-bumping idea is conceptually reusable as a *starting intuition* (overlap = more confidence) but the actual debate/arbitration machinery is a LangGraph state-machine concept that doesn't exist in any form yet.
- **(c) External dependency:** None beyond what Component 4 already requires (multiple models + LangGraph already provisioned there). This component has no *additional* blocker — it's purely a "write the code" problem once the council exists.

### 7. Reporting / SARIF / CI integration
- **(a) Exists today?** Partial and real. `services/report.py:generate_pdf_report()` is a fully working, well-built dark-themed PDF generator. The `/api/analyze` endpoint already returns structured JSON. That covers two of the plan's four target formats (PDF, JSON).
- **(b) Salvage verdict:** **Keep PDF/JSON generation as-is.** SARIF output, the GitHub Action (PR annotations + CI gate), the CLI (`argus scan`), the VS Code extension, and the pre-commit hook are **all separate, from-scratch deliverables** — none of them are reworks of existing code, they're net-new surface area.
- **(c) External dependency:** None for SARIF/CLI/GitHub Action (just code + YAML). The VS Code extension needs Node tooling (already present for the frontend) but if it's ever published to the Marketplace that needs a separate publisher account — not required for local/sideloaded use.

### The foundation: a real evaluation harness (the user's reframed Gate 1)
This isn't one of the plan's seven architecture boxes, but it's the thing the user is explicitly asking to move first — and the audit found a serious problem with what currently exists.

- **(a) Exists today?** `backend/dataset_runner.py` + `backend/datasets/index.json` (50 contracts) + `main.py`'s `/api/dataset/*` endpoints look like an evaluation harness, and partially function as one. But: **the `--static-only` mode is methodologically circular.** `dataset_runner.py:run_static_only()` sets `final_verdict = "NO-GO" if auto_label == "vulnerable" else "GO"` — i.e., it derives the "prediction" directly from the same `auto_label` field that `compare_verdict()` then checks it against. That's comparing a label to itself, not evaluating a detector. Whatever "accuracy" number this mode reports is meaningless. The non-static (`full_pipeline`) mode is more honest — it actually runs `run_full_analysis()` (real LLM + Slither) — but the ground-truth `auto_label` values themselves are unverified: the `notes` field on multiple entries literally says *"vulnerabilities not checked yet."* This is heuristic/scraped labeling, not expert-reviewed ground truth. There are also no per-category precision/recall/F1/confusion-matrix computations anywhere — `compare_verdict()` only produces a binary match/no-match.
- **(b) Salvage verdict:** **Salvageable with heavy rework.** Keep the harness scaffolding (background-task runner, JSON/CSV I/O, the dataset-of-50 as a quick smoke test) but: (1) remove or clearly relabel the tautological static-only branch, (2) add real precision/recall/F1/confusion-matrix-per-category metrics, (3) add loaders for the plan's mandated benchmark datasets (Web3Bugs, DefiHacks, SmartBugs-Curated), (4) add Slither/Mythril/single-LLM/current-ThirdEye as distinct, separately-recorded comparison rows instead of one blended pipeline.
- **(c) External dependency:** Downloading Web3Bugs/DefiHacks/SmartBugs-Curated (public GitHub research repos, no signup, just bandwidth) and getting Mythril runnable (pip-installable; has historically worked natively on Windows in some configurations, but the plan recommends WSL2 — try native first, fall back to WSL2 if it fails). The 50-contract Etherscan set's labels need either manual verification by the user or should be set aside in favor of the benchmark datasets' existing peer-reviewed ground truth.

---

## Step 3 — Phased Build Order for ONE Person

The plan's own 8-week / 4-person schedule is **32 person-weeks of planned effort**. Scaled naively to one person at the same intensity that's 6–8 calendar months, and realistically longer because solo work loses the plan's parallelism (e.g., Anvita building the corpus *while* Umar builds the UPR *while* Tarun builds the eval harness — all at once). **Do not try to preserve the plan's week-by-week schedule; re-sequence around dependencies and accept that scope must shrink, not just the timeline stretch.**

The user's framing is correct and the plan's own structure agrees: **the evaluation harness must come first**, because every later claim ("beats GPTScan," "Pareto improvement on precision," "ablation table") is meaningless without honest baseline numbers to compare against — the plan's Week 1 already calls this "Kill the lie, build the truth," it's just listed after a Week 0 tooling-install phase that, for a solo build, should be folded into Phase 0 rather than treated as separately gated.

### Phase 0 — Honest foundation: evaluation harness + re-run baselines
**This is the actual first deliverable, full stop. Nothing else starts until this exists.**
- Fix `dataset_runner.py`'s circular static-only logic; build real precision/recall/F1 + confusion-matrix-per-category metrics, not just match/no-match.
- Download Web3Bugs, DefiHacks, SmartBugs-Curated; write loaders that map their ground truth into a common schema.
- Re-run, on the same data: Slither, Mythril (native attempt, WSL2 fallback), current-ThirdEye (the live app, unmodified), and a single-LLM baseline (the existing `services/llm.py` path with Slither merging disabled, to isolate the LLM-only number).
- Output: one command prints a real metrics table. **This is the plan's own Gate 1**, just moved to Phase 0 instead of Week 1.
- **Effort: multi-day.** Dataset wrangling, metric code, and getting Mythril to actually run reliably is consistently underestimated work — budget 3–7 solo days, not a single session.

### Phase 1 — UPR + static evidence harvesters
- Build a minimal UPR: function boundaries + AST via Slither's own IR (don't insist on a full custom CFG/call-graph immediately — that's gold-plating before it's needed).
- Rework `services/slither.py` for multi-file ingestion; add Aderyn + Semgrep as additional harvesters; normalize all three into UPR-anchored evidence units.
- Plug into the Phase 0 harness as a new "static-only, multi-tool" comparison row.

### Phase 2 — Retrieval corpus + embeddings
- Curate the exploit+fix corpus from Solodit/Code4rena/SmartBugs/DeFiHackLabs (user sign-off needed on sourcing — see Step 4).
- Pull Qwen3-Embedding via Ollama; decide LanceDB vs. keeping ChromaDB (the latter is lower-effort and still serverless — don't treat the swap as mandatory if time is short).
- Replace `services/vectordb.py`'s self-referential cache with real precedent retrieval.

### Phase 3 — Council v0 (scaled down)
- Do **not** start with all 8 OWASP-category specialists. Start with 2–3 (e.g., AccessControl, Reentrancy, BusinessLogic) on 2 different free hosted models (Groq + OpenRouter) via LangGraph, to get the model-diversity mechanism proven before expanding category coverage.
- Wire into Phase 0's harness as the "+council" ablation row.
- Keep the single-LLM path from the live app untouched as the baseline it already is.

### Phase 4 — Dynamic exploitability confirmation
**Flag: this is the single highest-effort, highest-external-dependency component. Do it last, and treat it as a stretch goal, not a prerequisite for a usable system.**
- Cannot start until WSL2 + Foundry/ItyFuzz/Medusa/Echidna are installed and confirmed reachable (user action, Step 4).
- Start with template invariants per vulnerability category (the plan's own risk-mitigation suggestion) rather than fully general harness codegen.
- **Effort: multi-day-to-multi-week**, genuinely. This is not a single-session task even once tooling exists.

### Phase 5 — Evidence-anchored debate & arbitration
- Only meaningful once Phase 3 (council, for disagreement to arbitrate) and ideally Phase 4 (dynamic witness as the decisive evidence tier) exist.
- PROPOSER/RED-TEAM/JUDGE roles, evidence-unit citation requirement, calibrated confidence output.

### Phase 6 — Reporting/SARIF/CLI/CI (lowest risk — can run in parallel slices throughout)
- Keep PDF/JSON as-is.
- Add SARIF writer, GitHub Action, CLI (`argus scan`) incrementally — none of this blocks or is blocked by Phases 1–5, so slot it into idle moments rather than treating it as its own dedicated phase.

### What should explicitly NOT be attempted in a single session, ever, regardless of phase
- WSL2 + Linux toolchain setup (Phase 4 prerequisite) — environment work, not code.
- Full dynamic exploit-confirmation harness codegen (Phase 4) — multi-day minimum once tooling exists.
- The full 8-OWASP-category council with all model-diversity wiring (Phase 3 expanded) — start with 2–3 categories per above.
- A second language adapter (Vyper) — the plan itself calls this a stretch ("Tier 2"); for solo scope, defer indefinitely or document as pluggable-but-not-built (the plan's own "Tier 3" treatment), don't build it.
- The arXiv paper, reproducibility package, and demo video (plan's Week 8) — meaningful writing/packaging work that depends on every other phase being *done and frozen* first; don't draft it speculatively.
- A VS Code extension beyond a local sideload — Marketplace publishing is its own separate, non-code task.

### Blunt scope call
If forced to the plan's own "if you can only do three things" list — honest eval harness, model-diverse council, dynamic exploit-confirmation gate — that is *still* a multi-month solo effort once WSL2/API-signup dependencies are factored in, primarily because of Phase 4. A more realistic solo S-tier outcome is: **Phase 0 + Phase 1 + Phase 2 + Phase 3 (scaled-down council), with Phase 4 explicitly marked "not attempted" and reported honestly as future work**, rather than a token/fake dynamic-confirmation implementation. A fake confirmation gate that doesn't actually run a fuzzer is worse than no claim at all, given the plan's whole thesis rests on that gate being real.

---

## Step 4 — External Actions Required Before Any of Step 3 Can Start

### Must be done by the user personally (Claude Code cannot do these)
1. **Enable WSL2 + install Ubuntu** on the target machine. Windows feature toggle, likely needs a reboot, may need admin rights. Blocks Mythril, Halmos, ItyFuzz, Medusa, Echidna entirely (Foundry has a native Windows build, but the plan's chosen fuzzers are Linux-first) — i.e., blocks all of Phase 4 and part of Phase 1.
2. **Sign up for free API accounts and obtain keys**: Groq, Cerebras, OpenRouter (the "council models" tier). Each is a personal account signup — an agent cannot create these.
3. **Decide on and confirm the sourcing approach for the retrieval corpus** (Solodit/Code4rena/SmartBugs/DeFiHackLabs). Some of this may involve scraping a site with its own ToS — this needs explicit user sign-off before any scraping code runs, even though the scraping itself is technically scriptable.
4. **Verify or replace the existing ground-truth labels.** The current `datasets/index.json`'s `auto_label` field is heuristic/unverified (some entries literally note "vulnerabilities not checked yet"). Either hand-verify these 50 contracts, or commit to relying solely on the public benchmark datasets' existing ground truth instead — an agent should not invent vulnerability labels.
5. **Download/clone the benchmark datasets**: Web3Bugs, DefiHacks, SmartBugs-Curated (and SolidiFI if reporting it). These are public research repos with no signup, but the decision to pull them and where to store them is the user's call to make (disk space, licensing skim).
6. **Confirm the actual hardware** being used (plan assumes a Dell G15 5520, 4GB VRAM, 16GB RAM) — this gates which models can realistically run in the "privacy tier" locally; if the hardware differs, the model-size assumptions throughout the plan need re-checking.
7. **Kick off large local model downloads** (`ollama pull` for 7B+ "privacy tier" models, Qwen3-Embedding) if going forward with local privacy-tier validation — multi-GB downloads, user should confirm bandwidth/disk before starting.

### Can be done by Claude Code unattended, once the above are in place
- Write the real evaluation harness: dataset loaders, metrics (precision/recall/F1/confusion matrix), baseline-comparison code.
- Install pip-installable tools (slither-analyzer, semgrep, mythril-attempt) and cargo-installable tools (aderyn) via the Bash tool, within whatever permission mode is active.
- Write/refactor all application code across every phase: UPR + adapters, evidence harvesters, retrieval pipeline (once a corpus exists), council orchestration (once API keys exist in `.env`), debate/arbitration logic, dynamic-confirmation harness generation (once WSL2 + fuzzers exist), SARIF/report writers, GitHub Action YAML, CLI.
- Wire `.env`/config code to *read* API keys and model names — but cannot generate the keys themselves.
- Execute the dead-file cleanup identified in Step 1 (nested `thirdeye-v2/` duplicate, stray exported `.md` chat logs, the redundant `.zip`, the generated `directory_recursor_output.txt`/`thirdeye-code-export.txt`) — not done in this pass per instructions, but ready to execute on request once this document is reviewed.
