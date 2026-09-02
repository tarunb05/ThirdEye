#!/bin/bash
# Supervised benchmark run. Start this instead of run_full_laptop.sh.
#
# The unsupervised run died twice in one day and each death cost hours of idle
# laptop, from two distinct causes:
#
#   1. The ollama runner wedges. A CUDA shared-memory failure during a model
#      load leaves the server answering /api/version but returning 500 on
#      /api/generate. The benchmark's own pre-flight probe then aborts the whole
#      run. Killing and restarting ollama clears it every time -- the models are
#      fine, the runner is not.
#
#   2. The python process exits (OOM, an unhandled error, a closed lid).
#
# Both are recoverable and both are cheap to detect, so this loop does it:
# verify ollama can actually GENERATE (not just respond), restart it if not,
# then run the benchmark; if it exits and work remains, go again. Checkpointing
# makes every restart resume, so a restart costs one contract at most.
#
# Stops on its own when the benchmark reports nothing left to do.
cd "$(dirname "$0")"
export OLLAMA_MODELS=
export LLM_TIMEOUT=900
LOG=supervised.log
TARGET=2250
MAX_RESTARTS=200

say () { echo "[$(date '+%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

scored () { ls eval/checkpoints/benchmark/ollama_noarb/seed0/*.json 2>/dev/null | wc -l; }

ollama_generates () {
  # /api/version is NOT a health check: a wedged runner still answers it.
  # Only an actual generation proves the server can do work.
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" -m 240 \
    http://127.0.0.1:11434/api/generate \
    -d '{"model":"llama3.2:3b","prompt":"ok","stream":false,"options":{"num_predict":2}}')
  [ "$code" = "200" ]
}

restart_ollama () {
  say "restarting ollama"
  for w in $(ps -W 2>/dev/null | grep -i "ollama" | awk '{print $4}'); do
    taskkill //F //PID "$w" >/dev/null 2>&1
  done
  sleep 6
  nohup ./start_ollama_laptop.sh > ollama_laptop.log 2>&1 &
  sleep 15
  # Warm each family once so the first contracts do not pay three cold loads.
  for m in llama3.2:3b gemma3:4b qwen2.5-coder:7b; do
    curl -s -o /dev/null -m 300 http://127.0.0.1:11434/api/generate \
      -d "{\"model\":\"$m\",\"prompt\":\"ok\",\"stream\":false,\"options\":{\"num_predict\":2}}"
  done
  say "ollama warmed"
}

say "=== supervisor start — $(scored)/$TARGET scored ==="

for i in $(seq 1 $MAX_RESTARTS); do
  n=$(scored)
  if [ "$n" -ge "$TARGET" ]; then say "target reached: $n"; break; fi

  if ! ollama_generates; then
    say "ollama cannot generate — healing"
    restart_ollama
    if ! ollama_generates; then
      say "still unhealthy after restart; waiting 120s"
      sleep 120
      continue
    fi
  fi

  say "attempt $i — $n/$TARGET scored"
  ./venv_win/Scripts/python.exe -u -m eval.run_benchmark \
      --backend ollama --seed 0 --no-arbitration \
      --limit-per-tier 0 --sample-seed 0 --concurrency 1 >> full_run.log 2>&1
  rc=$?
  after=$(scored)
  say "attempt $i ended rc=$rc — $after/$TARGET scored (+$((after - n)))"

  # No forward progress twice running usually means the runner is wedged again
  # rather than that the work is done, so heal before trying once more.
  if [ "$after" -eq "$n" ]; then
    say "no progress this attempt — healing ollama before retry"
    restart_ollama
    sleep 10
  fi
done

say "=== supervisor done — $(scored)/$TARGET scored ==="
./venv_win/Scripts/python.exe -u -m eval.run_benchmark \
  --backend ollama --seed 0 --no-arbitration --report-only >> "$LOG" 2>&1
say "final report written"
