#!/bin/bash
# Full-scale benchmark on the laptop, matching the config that produced the
# existing 233 exactly -- ollama 0.24.0, NUM_PARALLEL=1, num_ctx=4096, same
# seed, same no-arbitration tree. That match is the point: it makes this an
# EXTENSION of the existing sample rather than a second, incomparable one.
#
# OLLAMA_MODELS is cleared because the shell profile points it at D:, a store
# missing qwen2.5-coder:7b and gemma3:4b -- two of the three model families.
# The server would 404 them and record a half-dead council as clean passes.
#
# CONCURRENCY 1, deliberately. The card holds one model at a time
# (MAX_LOADED_MODELS=1), so two contracts in flight fight over that single slot
# and thrash: measured 4/6 specialists failing and INCONCLUSIVE at 380s. Serial,
# it is 13-31s per contract with zero specialist errors.
#
# Resumable: every contract checkpoints, so a shutdown costs one contract.
cd "$(dirname "$0")"
export OLLAMA_MODELS=
# 4GB VRAM cannot hold qwen2.5-coder:7b (4.7GB), so it part-offloads to CPU and
# a call can exceed the 300s default. A timeout makes the specialist ERROR, and
# GO+errors is quarantined as unsound -- so a timeout costs the whole contract.
# 900s converts those losses into slow but valid results.
export LLM_TIMEOUT=900
exec ./venv_win/Scripts/python.exe -u -m eval.run_benchmark \
  --backend ollama --seed 0 --no-arbitration \
  --limit-per-tier 0 --sample-seed 0 --concurrency 1
