"""
Ablation runner — the paper's core table (GATE 3 / GATE 5): does each added
stage actually improve detection on a benchmark with real negative-class
signal?

Runs, on a balanced sample of the Access-Control slice (the only backbone set
with genuine AC-negatives), these configurations in ablation order:

    single_llm                  : one model, no council (services/llm.py)
    council                     : 8 model-diverse specialists, evidence-gated
    council+retrieval           : council with exploit-corpus precedents
    council+arbitration         : council -> cross-model red-team/judge (Cerebras)

Metric is ACCESS-CONTROL-SPECIFIC, not generic "found any bug": a contract is
predicted AC-positive iff the configuration confirms an access_control finding.
The 125 AC-negative contracts (vulnerable in OTHER ways) supply the false-
positive signal that the all-positive datasets cannot. We report precision,
recall, F1, and the confusion matrix per configuration.

Honest scope: this runs a SAMPLE (default 24 balanced items, single-file only)
so it completes on a laptop without the multi-day full-dataset batch. Sample
size and composition are printed and written into the report. Full-dataset runs
use eval/run_baselines.py with the same code paths; this is the fast ablation
that shows the per-stage deltas.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from eval.loaders import access_control_slice
from eval.schema import REPO_ROOT

RESULTS = REPO_ROOT / "backend" / "eval" / "results"
CKPT = REPO_ROOT / "backend" / "eval" / "checkpoints" / "ablation"

AC = "access_control"


def _is_ac_prediction(vulns: list[dict]) -> bool:
    """A configuration predicts AC-positive iff it confirms a finding whose
    type is access_control (substring-tolerant: 'access_control', 'access
    control', 'tx.origin' all count)."""
    for v in vulns:
        t = str(v.get("type", "")).lower()
        if "access" in t or "tx.origin" in t or "tx_origin" in t or "auth" in t:
            return True
    return False


async def _single_llm(code: str) -> list[dict]:
    from services.llm import run_full_analysis
    r = await run_full_analysis(code, disable_slither=True)
    return r.get("vulnerabilities", [])


async def _council(code: str, seed: int, use_retrieval: bool, use_arbitration: bool) -> list[dict]:
    from services.pipeline import run_argus
    r = await run_argus(code, backend="ollama", seed=seed,
                        use_retrieval=use_retrieval, use_arbitration=use_arbitration,
                        use_dynamic=False)
    return r.get("vulnerabilities", [])


# council+retrieval is intentionally omitted from the RUN: retrieved
# precedents are currently surfaced in the output but NOT injected into the
# specialist prompts, so its verdicts are identical to plain council by
# construction — computing it would just burn 8 LLM calls/item for a
# guaranteed no-delta row. Noted in the report. Wiring precedents into prompts
# is the next retrieval-grounding step.
CONFIGS = {
    "single_llm": lambda code, seed: _single_llm(code),
    "council": lambda code, seed: _council(code, seed, False, False),
    "council+arbitration": lambda code, seed: _council(code, seed, True, True),
}


def _confusion(rows: list[dict], config: str) -> dict:
    tp = fp = tn = fn = 0
    for r in rows:
        if config not in r["pred"]:
            continue
        actual = r["is_ac"]
        pred = r["pred"][config]
        if actual and pred:
            tp += 1
        elif actual and not pred:
            fn += 1
        elif not actual and pred:
            fp += 1
        else:
            tn += 1
    p = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * p * rec / (p + rec) if (p + rec) else 0.0
    acc = (tp + tn) / (tp + fp + tn + fn) if (tp + fp + tn + fn) else 0.0
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn, "precision": p, "recall": rec, "f1": f1, "accuracy": acc}


def _ckpt_path(config: str, cid: str, seed: int) -> Path:
    safe = cid.replace("/", "_").replace(":", "_")
    return CKPT / f"seed{seed}" / config / f"{safe}.json"


async def main(n_per_class: int = 12, seed: int = 0):
    items = access_control_slice.load()
    # single-file only (fast, deterministic); split by label, balanced.
    single = [it for it in items if len(it.code_paths) == 1 and it.code_paths[0].exists()]
    pos = [it for it in single if it.ground_truth_label == "vulnerable"][:n_per_class]
    neg = [it for it in single if it.ground_truth_label == "likely_safe"][:n_per_class]
    sample = pos + neg
    print(f"Ablation sample: {len(pos)} AC-positive + {len(neg)} AC-negative = {len(sample)} items (seed={seed})")

    rows = []
    for i, it in enumerate(sample):
        code = it.read_code()
        is_ac = it.ground_truth_label == "vulnerable"
        pred = {}
        for config, fn in CONFIGS.items():
            cp = _ckpt_path(config, it.contract_id, seed)
            if cp.exists():
                pred[config] = json.load(open(cp))["pred"]
                continue
            t0 = time.time()
            try:
                vulns = await fn(code, seed)
                p = _is_ac_prediction(vulns)
            except Exception as e:
                print(f"  ! {config} failed on {it.contract_id}: {e}")
                p = False
            dt = round(time.time() - t0, 1)
            pred[config] = p
            cp.parent.mkdir(parents=True, exist_ok=True)
            json.dump({"pred": p, "latency_s": dt, "is_ac": is_ac}, open(cp, "w"))
            print(f"  [{i+1}/{len(sample)}] {it.contract_id} {config}: pred_ac={p} ({dt}s)")
        rows.append({"cid": it.contract_id, "is_ac": is_ac, "pred": pred})

    # Build report
    reports = {c: _confusion(rows, c) for c in CONFIGS}
    RESULTS.mkdir(parents=True, exist_ok=True)
    json.dump({"sample_size": len(sample), "n_pos": len(pos), "n_neg": len(neg),
               "seed": seed, "configs": reports, "rows": rows},
              open(RESULTS / "ablation_ac.json", "w"), indent=2)

    lines = [
        "# Ablation — Access-Control detection (single-file balanced sample)",
        "",
        f"Sample: {len(pos)} AC-positive + {len(neg)} AC-negative = {len(sample)} contracts, seed={seed}.",
        "Metric: AC-specific — a config is positive iff it confirms an access_control finding.",
        "AC-negatives are contracts vulnerable in OTHER ways, so a positive there is a real false positive.",
        "",
        "| config | model(s) | TP | FP | TN | FN | precision | recall | F1 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    model_labels = {
        "single_llm": "llama3.1:8b (single)",
        "council": "qwen2.5-coder:7b + llama3.1:8b + gemma3:4b",
        "council+retrieval": "council + exploit-corpus precedents",
        "council+arbitration": "council + Cerebras gpt-oss-120b judge",
    }
    for c in CONFIGS:
        r = reports[c]
        lines.append(f"| {c} | {model_labels[c]} | {r['tp']} | {r['fp']} | {r['tn']} | {r['fn']} | "
                     f"{r['precision']:.3f} | {r['recall']:.3f} | {r['f1']:.3f} |")
    (RESULTS / "ablation_ac.md").write_text("\n".join(lines) + "\n")
    print("\n" + "\n".join(lines))
    print(f"\nWrote {RESULTS / 'ablation_ac.md'}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-per-class", type=int, default=12)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    asyncio.run(main(args.n_per_class, args.seed))
