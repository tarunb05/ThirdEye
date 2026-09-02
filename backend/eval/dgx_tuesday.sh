#!/bin/bash
# ============================================================================
# ThirdEye — campus GPU session. Runs ON the DGX. Launched by tuesday_start.sh.
#
# Budget-aware: each stage gets a slice of TOTAL_MINUTES and stops cleanly at
# its deadline rather than being killed, so every stage writes its report.
# Everything checkpoints per contract, so re-running resumes rather than redoes.
#
# Stage order is value-per-minute to the paper:
#   A  finish the 8B ablation   ~223/233 already computed, minutes to close
#   B  NUM_PARALLEL=1 control   decides whether the parity finding is real
#   C  web3bugs                 the GPTScan comparison -- the biggest remaining
#                               gap in the paper, and the one a reviewer asks
#                               about first. Given the large middle slot.
#   D  full-scale benchmark     the laptop already reached n=1089 unaided and
#                               is still running, so this is now top-up only.
# ============================================================================
set -u
TOTAL_MINUTES="${TOTAL_MINUTES:-210}"
cd ~/thirdeye/backend
PY=~/thirdeye/venv/bin/python
MAN=~/thirdeye/backend/eval/parity_manifest_full.json
export OLLAMA_URL=http://127.0.0.1:11434
export LLM_TIMEOUT=600
export OLLAMA_MODELS=

log () { echo "[$(date +%H:%M:%S)] $*"; }
T0=$(date +%s)
left () { echo $(( TOTAL_MINUTES - ( ($(date +%s) - T0) / 60 ) )); }

start_ollama () {  # $1 = num_parallel
  # NOT "pkill -f 'ollama serve'": over ssh that pattern matches the invoking
  # shell's own command line, and the script kills itself. Bracket the match.
  pkill -f "olla[m]a serve" 2>/dev/null || true
  sleep 4
  OLLAMA_HOST=127.0.0.1:11434 OLLAMA_CONTEXT_LENGTH=4096 \
  OLLAMA_NUM_PARALLEL="$1" OLLAMA_MAX_LOADED_MODELS=6 OLLAMA_KEEP_ALIVE=4h \
  setsid nohup ~/.local/bin/ollama serve > ~/ollama.log 2>&1 < /dev/null &
  for _ in $(seq 1 30); do
    sleep 2
    curl -sf http://127.0.0.1:11434/api/version >/dev/null 2>&1 && break
  done
  log "ollama up $(curl -s http://127.0.0.1:11434/api/version) parallel=$1"
}

warm () {  # pay each cold model load once, before anything is timed
  for m in qwen2.5-coder:7b gemma3:4b llama3.2:3b "$@"; do
    [ -n "$m" ] || continue
    curl -s -o /dev/null -m 900 http://127.0.0.1:11434/api/generate \
      -d "{\"model\":\"$m\",\"prompt\":\"ok\",\"stream\":false,\"options\":{\"num_predict\":2}}"
    log "warmed $m"
  done
}

log "=== SESSION START — budget ${TOTAL_MINUTES} min ==="
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null | head -1

# ------------------------------------------------------------------ A. 8B arm
start_ollama 4
warm llama3.1:8b
log "### A. finish 8B ablation (n=233) — $(left) min left"
OLLAMA_LOGIC_MODEL=llama3.1:8b $PY -u -m eval.run_parity \
  --arm full8b --seed 0 --concurrency 4 --manifest "$MAN" || log "A EXITED NONZERO -- check the traceback above"

# --------------------------------------------------------- C. NUM_PARALLEL=1
log "### C. NUM_PARALLEL=1 control — $(left) min left"
start_ollama 1
warm ""
# 45 min is enough for the control to detect a large batching effect;
# it does not need all 233 to answer the question.
C_BUDGET=45
[ "$(left)" -lt 70 ] && C_BUDGET=$(( $(left) - 25 ))
[ "$C_BUDGET" -lt 10 ] && C_BUDGET=10
timeout "${C_BUDGET}m" $PY -u -m eval.run_parity \
  --arm full3b_np1 --seed 0 --concurrency 1 --manifest "$MAN" || log "C stopped at budget"

# ----------------------------------------------------------------- D. web3bugs
log "### D. web3bugs — $(left) min left"
start_ollama 4
warm ""
D_BUDGET=$(( $(left) - 25 ))   # leave 25 min for the bench top-up
if [ "$D_BUDGET" -gt 10 ]; then
  # HEAD-TO-HEAD FIRST. GPTScan's authors published per-project TP/TN/FP/FN for
  # 72 Web3Bugs projects; 63 of them carry S-class bugs and are runnable here.
  # Scoring our tool on exactly that set converts "our recall on some Web3Bugs
  # subset" into a direct comparison on identical data -- the single biggest gap
  # in the paper. It runs BEFORE the open-ended sweep so a budget overrun costs
  # the sweep, never the comparison.
  #
  # concurrency 8: 120GB holds every council model resident, so the sequential
  # slice loop left the card mostly idle. Scheduling only -- OLLAMA_NUM_PARALLEL
  # is unchanged, so no verdict numerics move.
  timeout $(( D_BUDGET * 2 / 3 ))m $PY -u -m eval.run_web3bugs \
    --gptscan-set --contests 0 --max-slices 25 --backend ollama --seed 0 --concurrency 8 \
    || log "D1 (gptscan head-to-head) EXITED NONZERO -- budget OR crash, check above"
  $PY -u -m eval.run_web3bugs --gptscan-set --report-only || true

  timeout $(( D_BUDGET / 3 ))m $PY -u -m eval.run_web3bugs \
    --contests 0 --max-slices 25 --backend ollama --seed 0 --concurrency 8 \
    || log "D2 (full sweep) EXITED NONZERO -- budget OR crash, check above"
  $PY -u -m eval.run_web3bugs --report-only || true
else
  log "skipping D — no time left"
fi

# -------------------------------------------------------- B. full-scale bench
B_BUDGET=$(( $(left) - 20 ))          # bench takes what is left AFTER C and D
[ "$B_BUDGET" -lt 20 ] && B_BUDGET=20
log "### B. full-scale benchmark — budget ${B_BUDGET} min"
# --limit-per-tier 0 still shuffles now, and the task list is interleaved across
# tiers, so stopping at the deadline leaves a BALANCED, scorable sample.
# --max-minutes stops STARTING work at the deadline but lets in-flight
# contracts finish, so B can overrun by up to one LLM_TIMEOUT. The outer
# timeout is a backstop for --max-minutes failing outright; it sits well past
# the clean stop so it never pre-empts the report B writes for itself.
timeout $(( B_BUDGET + 20 ))m $PY -u -m eval.run_benchmark --backend ollama --seed 0 --no-arbitration \
  --limit-per-tier 0 --sample-seed 0 --concurrency 4 \
  --max-minutes "$B_BUDGET" || log "B stopped (budget or backstop)"
# Always leave a scored report, even if the backstop fired mid-write.
$PY -u -m eval.run_benchmark --backend ollama --seed 0 --no-arbitration --report-only || true

log "=== SESSION DONE — $(( ($(date +%s) - T0) / 60 )) min used ==="
