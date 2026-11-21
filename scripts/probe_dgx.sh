#!/usr/bin/env bash
# One probe for the DGX runs. Reports what is TRUE, not what was launched.
#
# Every line here exists because its absence caused a wrong call today:
#
#  * TERMINAL vs QUARANTINED counted separately. run_benchmark moves an unsound
#    row (GO with an errored specialist) into _transient/, so the terminal count
#    legitimately DECREASES. That read as data loss twice. The quarantine count
#    is also the only honest fault counter -- grepping the run log for HTTP 500
#    reported 3 faults when 13 rows had been quarantined.
#
#  * Row AGE against the MEASURED latency range, not a guessed one. The first
#    band (28-58 min) came from a handful of early rows; real w3b-tail rows take
#    815-3626 s (14-60 min) and hold 15-40 slices each, so 75+ min between
#    writes is ordinary. The narrow band raised a false stall alarm, and a
#    monitor that cries wolf gets ignored exactly when it is right.
#
#  * GPU sampled SIX times, and still only as CONTEXT. One sample read 0% on a
#    healthy job; six consecutive 0% samples ALSO occurred while ollama was
#    serving normally, because utilisation idles between requests. GPU alone
#    cannot decide liveness.
#
#  * REQUESTS COMPLETED is the real liveness signal. ollama flushes a [GIN] line
#    per request, whereas the orchestrator's own stdout block-buffers to a file
#    without -u -- it was read 3 HOURS STALE today and its contents reported as
#    live. Prefer the channel that flushes.
cd ~/thirdeye/backend/eval/checkpoints || exit 1
date +%H:%M:%S

for s in 1 2; do
  d=benchmark/ollama_noarb/seed$s
  t=$(ls $d/*.json 2>/dev/null | wc -l)
  q=$(ls $d/_transient/*.json 2>/dev/null | wc -l)
  printf "seed%s: terminal=%s quarantined=%s attempted=%s/360\n" "$s" "$t" "$q" "$((t+q))"
done
printf "council: %s/303\n" "$(find council -name '*.json' | wc -l)"

newest=$(find council -name '*.json' -printf '%T@\n' 2>/dev/null | sort -n | tail -1)
if [ -n "$newest" ]; then
  printf "  newest council row: %d min ago (measured 14-60 min/row on the w3b tail; 75+ normal)\n" \
    "$(( ($(date +%s) - ${newest%.*}) / 60 ))"
fi

printf "  gpu (context only):"
for i in 1 2 3 4 5 6; do
  printf " %s" "$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader 2>/dev/null)"
  sleep 4
done
echo

OL=~/ollama_run.log
now=$(date +'%Y/%m/%d - %H:%M')
prev=$(date -d '-1 min' +'%Y/%m/%d - %H:%M')
served=$(grep -F -e "$now" -e "$prev" "$OL" 2>/dev/null | grep -c '\[GIN\]')
printf "  ollama: %s requests completed in the last ~2 min  <-- LIVENESS\n" "${served:-0}"
printf "  (ollama log written %s min ago)\n" \
  "$(( ($(date +%s) - $(stat -c %Y "$OL")) / 60 ))"

ps -u student-9 -o pid,etime,cmd | grep -E "eval\.run_" | grep -v grep || echo "  NONE RUNNING"
