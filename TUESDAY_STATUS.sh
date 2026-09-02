#!/bin/bash
# Progress check. Safe to run any time, as often as you like.
BOX=student-9@10.1.72.54
ssh -o BatchMode=yes -o ConnectTimeout=10 "$BOX" '
cd ~/thirdeye/backend/eval/checkpoints 2>/dev/null || exit 1
c () { ls "$1"/*.json 2>/dev/null | wc -l; }
echo "stage A  8B ablation      $(c parity_full8b)/233"
echo "stage B  full benchmark   $(c benchmark/ollama_noarb/seed0)/2250   (quarantined: $(c benchmark/ollama_noarb/seed0/_transient))"
echo "stage C  np=1 control     $(c parity_full3b_np1)/233"
echo "stage D  web3bugs         $(c web3bugs)/102"
echo
echo "--- current stage ---"; grep "###\|SESSION" ~/tuesday.log 2>/dev/null | tail -3
echo "--- alive? ---"; pgrep -f "eval\.run_" >/dev/null && echo RUNNING || echo "NOT RUNNING"
echo "--- last 3 lines ---"; tail -3 ~/tuesday.log 2>/dev/null
' 2>&1
