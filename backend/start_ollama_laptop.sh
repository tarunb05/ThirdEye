#!/bin/bash
# Ollama for the laptop benchmark, tuned for a 4GB card.
#
# NUMERICS-RELEVANT (must match the existing 233 exactly, do not touch):
#   NUM_PARALLEL=1      batch-1 inference, as the baseline ran
#   CONTEXT_LENGTH=4096 the 0.24.0 default the baseline inherited
#
# RESIDENCY-ONLY (free to tune; affects speed, not results):
#   MAX_LOADED_MODELS=1 the card holds 4096 MiB and qwen2.5-coder:7b alone is
#     4.7GB. The default (3) makes ollama juggle three models that cannot
#     co-reside, thrashing loads until the 300s client timeout kills them --
#     which is what produced 4/6 specialists failing and INCONCLUSIVE at 380s.
#   KEEP_ALIVE=30m      council._schedule_groups batches specialists by model,
#     so a model is reused across several calls before the next swap. The 5m
#     default was expiring models mid-contract and paying the load twice.
export OLLAMA_MODELS=            # shell profile points at D:, which lacks 2 of 3 families
export OLLAMA_HOST=127.0.0.1:11434
export OLLAMA_NUM_PARALLEL=1
export OLLAMA_CONTEXT_LENGTH=4096
export OLLAMA_MAX_LOADED_MODELS=1
export OLLAMA_KEEP_ALIVE=30m
exec ollama serve
