#!/usr/bin/env python3
"""Recover the sampling parameters of an existing ctx-ablation arm.

WHY THIS EXISTS. `run_ctx_ablation.py` writes only `arm` and `num_ctx` into its
result file. It does not record `--n`, `--max-tokens` or `--sample-seed`, so the
population an arm was drawn from cannot be read back off disk. That matters the
moment you want to EXTEND an arm: the sample is nested only while the pool is
identical, and the pool depends on the token ceiling. Extending under a
different ceiling would silently swap the population — defect #6 in the paper's
own list, committed by the tool that measures it.

This recovers the parameters empirically. The arm's result file records the
contract ids it actually ran. For each candidate ceiling we rebuild the pool,
apply the same seeded shuffle, and check whether the first n ids match the ones
on disk. A match pins the ceiling exactly; it is a verification, not a guess.

Run locally — it needs the corpus and the prompt builder, not a GPU:

    python backend/eval/reconstruct_ctx_sample.py ctx16k_safe
"""
from __future__ import annotations

import json
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault('OLLAMA_NUM_CTX', '4096')  # irrelevant to prompt length; set for import

from eval.loaders import thirdeye_bench          # noqa: E402
from eval.schema import REPO_ROOT                # noqa: E402
from services import council                     # noqa: E402

CHARS_PER_TOKEN = 4
RES = REPO_ROOT / 'backend' / 'eval' / 'results'


def find_arm_file(arm):
    for cand in (RES / 'dgx_fullscale' / ('ctx_%s.json' % arm), RES / ('ctx_%s.json' % arm)):
        if cand.exists():
            return cand
    raise SystemExit('no result file found for arm %r' % arm)


def main():
    arm = sys.argv[1] if len(sys.argv) > 1 else 'ctx16k_safe'
    label = 'safe' if arm.endswith('_safe') else ('vulnerable' if arm.endswith('_vuln') else None)

    path = find_arm_file(arm)
    data = json.load(open(path, encoding='utf-8'))
    got = [r['contract_id'] for r in data['rows']]
    print('arm           %s' % arm)
    print('result file   %s' % path.name)
    print('rows on disk  %d' % len(got))
    print('label filter  %s' % label)
    print()

    spec = next(s for s in council.SPECIALISTS if s['role'] == 'business_logic')

    # Estimate tokens once per contract; the ceiling only changes which are kept.
    print('scoring corpus for prompt length ...', flush=True)
    sized = []
    for it in thirdeye_bench.load():
        try:
            code = it.read_code()
        except Exception:
            continue
        if label:
            cls = 'vulnerable' if it.ground_truth_label == 'vulnerable' else 'safe'
            if cls != label:
                continue
        tok = len(council._build_prompt(spec, code)) // CHARS_PER_TOKEN
        if tok > 4096:
            sized.append((it.contract_id, tok))
    print('overflow pool (label=%s, no ceiling): %d contracts' % (label, len(sized)))
    print('token range: %d .. %d' % (min(t for _, t in sized), max(t for _, t in sized)))
    print()

    # Candidate ceilings: 0 (none) plus every value that would actually change
    # the pool, i.e. the distinct token counts themselves.
    cands = [0] + sorted({t for _, t in sized})

    for mt in cands:
        pool = [cid for cid, t in sized if (not mt or t <= mt)]
        rng = random.Random('ctxablation:0')
        rng.shuffle(pool)
        if pool[:len(got)] == got:
            print('MATCH')
            print('  --max-tokens %s' % (mt if mt else '0  (no ceiling)'))
            print('  --n          %d' % len(got))
            print('  --sample-seed 0')
            print('  pool size    %d' % len(pool))
            print()
            print('Extending is therefore NESTED: rerunning with the same ceiling and a')
            print('larger --n yields a strict superset of these %d ids.' % len(got))
            return 0

    # No exact match — report the closest so the failure is diagnosable.
    print('NO EXACT MATCH over %d candidate ceilings.' % len(cands))
    best, bestn = None, -1
    for mt in cands:
        pool = [cid for cid, t in sized if (not mt or t <= mt)]
        rng = random.Random('ctxablation:0')
        rng.shuffle(pool)
        head = pool[:len(got)]
        overlap = len(set(head) & set(got))
        if overlap > bestn:
            best, bestn = mt, overlap
    print('closest ceiling %s overlaps %d/%d ids.' % (best, bestn, len(got)))
    print('The arm was probably run with a different --sample-seed, a different')
    print('corpus revision, or was truncated by --max-minutes mid-run.')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
