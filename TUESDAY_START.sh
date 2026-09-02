#!/bin/bash
# ============================================================================
# RUN THIS ON THE LAPTOP, ON CAMPUS, ONCE. Then walk away.
#
#     ./TUESDAY_START.sh
#
# It re-syncs the fixed eval code to the DGX, starts the session detached (so
# closing the laptop or dropping wifi does NOT kill it), and returns.
# Check progress later with ./TUESDAY_STATUS.sh, collect with ./TUESDAY_FETCH.sh
# ============================================================================
set -u
BOX=student-9@10.1.72.54
MINUTES="${1:-210}"        # ./TUESDAY_START.sh 150  -> shorter session

echo "== 1. reachable? =="
if ! ssh -o BatchMode=yes -o ConnectTimeout=10 "$BOX" 'echo ok' >/dev/null 2>&1; then
  echo "CANNOT REACH $BOX."
  echo "  - is the box powered on?"
  echo "  - are you on the campus network? (it is a private 10.x address)"
  exit 1
fi
echo "   reachable"

echo "== 2. sync the fixed eval code =="
# The box has a pre-fix copy of run_benchmark.py. The interleaving, the
# unconditional shuffle and --max-minutes all live there, and stage B is
# WRONG without them: tier-major order means a time-truncated run finishes the
# safe tiers and starves the vulnerable ones.
# .env is excluded on purpose -- that box is shared with other students.
tar czf - --exclude='.env' --exclude='venv*' --exclude='__pycache__' \
          --exclude='*.pyc' --exclude='eval/checkpoints' --exclude='*.db' \
    backend/eval backend/services backend/requirements.txt datasets/gptscan 2>/dev/null \
  | ssh "$BOX" 'tar xzf - -C ~/thirdeye --strip-components=0 && echo "   code synced"'

echo "== 3. sanity checks =="
ssh "$BOX" 'cd ~/thirdeye/backend
  ~/thirdeye/venv/bin/python -c "import ast;ast.parse(open(\"eval/run_benchmark.py\").read())" \
    && echo "   run_benchmark parses"
  grep -q "max_minutes" eval/run_benchmark.py && echo "   --max-minutes present"
  grep -q "_queues" eval/run_benchmark.py && echo "   tier interleaving present"
  test -f eval/parity_manifest_full.json && echo "   parity manifest present"
  test -d ~/thirdeye/datasets/web3bugs/contracts && echo "   web3bugs data present"
  ls ~/.ollama/models/manifests/registry.ollama.ai/library 2>/dev/null | tr "\n" " " | sed "s/^/   models: /"
  echo
  if [ ! -f ~/thirdeye/backend/eval/dgx_tuesday.sh ]; then echo "   ERROR: session script missing"; fi'

echo "== 4. launch, detached =="
# DO NOT pkill here. The bracket trick stops the PATTERN matching itself, but
# this same command line also contains the literal path .../dgx_tuesday.sh, so
# "pkill -f dgx_tue[s]day" matched the shell running THIS command and killed its
# own parent: ssh died with 255 before the launch line ran, and this script
# reported success because it never checked ssh's exit code. Killing a live
# session would also be destructive -- stages are budgeted, so a mid-run kill
# costs the whole remaining budget. Refuse to double-start instead.
ALIVE='pgrep -f "^/bin/bash .*dgx_tuesday[.]sh$" >/dev/null'
if ssh "$BOX" "$ALIVE"; then
  echo "A session is ALREADY RUNNING on the box. Not starting a second one."
  echo "  progress : ./TUESDAY_STATUS.sh"
  exit 1
fi
ssh "$BOX" "chmod +x ~/thirdeye/backend/eval/dgx_tuesday.sh
  TOTAL_MINUTES=$MINUTES setsid nohup ~/thirdeye/backend/eval/dgx_tuesday.sh \
      > ~/tuesday.log 2>&1 < /dev/null &
  sleep 8
  echo '   started:'; head -3 ~/tuesday.log" || { echo "LAUNCH SSH FAILED"; exit 1; }

# Trust nothing: prove the process exists rather than inferring it from rc=0.
sleep 4
if ! ssh "$BOX" "$ALIVE"; then
  echo "LAUNCH FAILED -- no session process on the box. Last log lines:"
  ssh "$BOX" 'tail -20 ~/tuesday.log 2>/dev/null || echo "(no log written)"'
  exit 1
fi
echo "   verified: session process alive"

echo
echo "RUNNING. Budget ${MINUTES} min. Safe to close the laptop lid."
echo "  progress : ./TUESDAY_STATUS.sh"
echo "  collect  : ./TUESDAY_FETCH.sh      <-- run before you leave campus"
