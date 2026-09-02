"""Context-window ablation: how much of our result is a truncation artifact?

THE PROBLEM THIS MEASURES. Every number this project has reported was produced
with Ollama's context window at 4096 tokens. A prompt longer than that is not
rejected -- it is silently TRUNCATED, and the specialist then judges a fraction
of the contract while reporting a verdict as though it had seen all of it.
Ollama's own accounting confirms it: an ~11.8k-token prompt evaluated 2050
tokens at the 4096 setting and 9054 tokens at 32768.

Measured on the corpus, 540 of 2250 contracts (24.0%) overflow. The overflow is
NOT class-balanced -- 350 vulnerable against 190 safe, because real buggy
contracts are larger -- so truncation suppresses recall specifically. That is
the direction that would flatter a paper whose thesis is about false alarms, and
it is therefore the direction we are obliged to measure rather than assume.

THE DESIGN. Only contracts that overflow can possibly change, so the sample is
drawn from those; including short contracts would burn GPU time on guaranteed
ties and dilute the effect. Both arms run:
  - the same contract ids, drawn once with a seeded shuffle
  - the same seed, models, machine, concurrency
  - the same _run_one() imported from run_benchmark, so the arms cannot drift
The ONLY difference is OLLAMA_NUM_CTX.

Because the arms are PAIRED on contract id, the right test is McNemar's on the
discordant pairs, not two independent proportions: it asks whether the flips
that appear run predominantly one way. Two overlapping confidence intervals
would understate a real paired effect, and reporting them instead would be the
same error this project keeps finding in other people's work.
"""
from __future__ import annotations
import argparse, asyncio, json, math, os, random, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from eval.loaders import thirdeye_bench
from eval.schema import REPO_ROOT

OUT = REPO_ROOT / "backend" / "eval" / "results"
CKPT_ROOT = REPO_ROOT / "backend" / "eval" / "checkpoints"
# ~4 chars/token is deliberately CONSERVATIVE. Ollama reported 9054 real tokens
# where this heuristic predicted ~11.8k, so it over-estimates and the sample is
# a superset of the truly-overflowing set. Over-including is safe: a contract
# that turns out to fit simply ties in both arms.
CHARS_PER_TOKEN = 4


def wilson(k: int, n: int):
    if n <= 0:
        return None
    z, p = 1.96, k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = (z / d) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return p, max(0.0, c - h), min(1.0, c + h)


def mcnemar(b: int, c: int):
    """McNemar on the discordant counts b and c.

    Normal approximation with continuity correction. Says plainly when the
    discordant total is too small for the test to mean anything, rather than
    printing a p-value that looks authoritative on 3 pairs.
    """
    n = b + c
    if n == 0:
        return None, "no discordant pairs - the arms agreed on every contract"
    chi = (abs(b - c) - 1) ** 2 / n
    p = math.erfc(math.sqrt(chi / 2))
    note = "" if n >= 10 else f" (only {n} discordant pairs - underpowered, indicative only)"
    return p, f"chi2={chi:.2f} p={p:.4f}{note}"


def load_arm(arm: str) -> dict:
    d = CKPT_ROOT / f"ctx_{arm}"
    out = {}
    for f in sorted(d.glob("*.json")):
        try:
            r = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        out[r["contract_id"]] = r
    return out


def compare(arm_a: str, arm_b: str) -> None:
    A, B = load_arm(arm_a), load_arm(arm_b)
    both = sorted(set(A) & set(B))
    print(f"\n=== CONTEXT ABLATION: {arm_a} vs {arm_b} ===")
    print(f"paired contracts        {len(both)}   ({len(A)} in {arm_a}, {len(B)} in {arm_b})")
    if not both:
        print("nothing paired yet")
        return

    def correct(r):
        return (r["verdict"] == "NO-GO") == (r["expected"] == "vulnerable")

    sc = [c for c in both
          if A[c]["verdict"] in ("GO", "NO-GO") and B[c]["verdict"] in ("GO", "NO-GO")]
    print(f"scored in BOTH arms     {len(sc)}")

    # Truncation also shows up as unparseable output, so the inconclusive rate is
    # itself an outcome, not just bookkeeping.
    for nm, D in ((arm_a, A), (arm_b, B)):
        inc = sum(1 for c in both if D[c]["verdict"] not in ("GO", "NO-GO"))
        w = wilson(inc, len(both))
        print(f"  inconclusive {nm:<8} {inc}/{len(both)}  "
              f"{w[0]*100:.1f}% [{w[1]*100:.1f}, {w[2]*100:.1f}]")

    if not sc:
        print("no contracts scored in both arms yet")
        return

    for nm, D in ((arm_a, A), (arm_b, B)):
        k = sum(1 for c in sc if correct(D[c]))
        w = wilson(k, len(sc))
        print(f"  accuracy     {nm:<8} {k}/{len(sc)}  "
              f"{w[0]*100:.1f}% [{w[1]*100:.1f}, {w[2]*100:.1f}]")

    # Recall is the quantity truncation should hurt, so it gets its own line.
    vul = [c for c in sc if A[c]["expected"] == "vulnerable"]
    for nm, D in ((arm_a, A), (arm_b, B)):
        if vul:
            k = sum(1 for c in vul if D[c]["verdict"] == "NO-GO")
            w = wilson(k, len(vul))
            print(f"  recall       {nm:<8} {k}/{len(vul)}  "
                  f"{w[0]*100:.1f}% [{w[1]*100:.1f}, {w[2]*100:.1f}]")
    safe = [c for c in sc if A[c]["expected"] == "safe"]
    for nm, D in ((arm_a, A), (arm_b, B)):
        if safe:
            k = sum(1 for c in safe if D[c]["verdict"] == "NO-GO")
            w = wilson(k, len(safe))
            print(f"  FPR          {nm:<8} {k}/{len(safe)}  "
                  f"{w[0]*100:.1f}% [{w[1]*100:.1f}, {w[2]*100:.1f}]")

    # LATENCY, PAIRED. Not bookkeeping: a prompt longer than the window forces
    # the runtime to shift context rather than process it in one pass, so the
    # truncating configuration can be markedly SLOWER as well as lossy. Measured
    # on the same contracts, so it is a within-pair comparison, not two medians
    # from different samples.
    import statistics as _st
    la = [A[c].get("latency_s") for c in sc if A[c].get("latency_s")]
    lb = [B[c].get("latency_s") for c in sc if B[c].get("latency_s")]
    if la and lb:
        print(f"\nmedian latency {arm_a:<8} {_st.median(la):7.1f}s")
        print(f"  median latency {arm_b:<8} {_st.median(lb):7.1f}s")
        pairs = [(A[c]["latency_s"], B[c]["latency_s"]) for c in sc
                 if A[c].get("latency_s") and B[c].get("latency_s")]
        faster_b = sum(1 for x, y in pairs if y < x)
        ratio = _st.median([x / y for x, y in pairs if y])
        # Exact two-sided SIGN TEST on the paired direction. Latency is not
        # normally distributed and the arms are paired, so the defensible
        # statement is "B was faster on k of n contracts", not a t-test on
        # medians. Unanimity at n=11 is already p<0.001, which is why this is
        # reportable long before the correctness comparison has the power to be.
        n_p = len(pairs)
        if n_p:
            k = max(faster_b, n_p - faster_b)
            tail = sum(math.comb(n_p, i) for i in range(k, n_p + 1)) / (2 ** n_p)
            p_sign = min(1.0, 2 * tail)
            print(f"  {arm_b} faster on   {faster_b}/{n_p} paired contracts, "
                  f"median speedup x{ratio:.2f}")
            print(f"  sign test               p = {p_sign:.5f}"
                  + ("  (significant)" if p_sign < 0.05 else "  (not significant)"))

    # THE PAIRED TEST.
    b = sum(1 for c in sc if correct(A[c]) and not correct(B[c]))
    cc = sum(1 for c in sc if correct(B[c]) and not correct(A[c]))
    p, note = mcnemar(b, cc)
    print(f"\nDiscordant pairs        {arm_a}-only-correct={b}  {arm_b}-only-correct={cc}")
    print(f"McNemar                 {note}")
    if p is not None:
        print("Verdict                 " + (
            "a real paired difference" if p < 0.05
            else "NOT significant - truncation did not measurably change correctness"))

    flips = [c for c in sc if A[c]["verdict"] != B[c]["verdict"]]
    print(f"\nverdict flips           {len(flips)}/{len(sc)}  "
          f"({100*len(flips)/len(sc):.1f}% of paired contracts)")
    for c in flips[:12]:
        print(f"    {A[c]['verdict']:<6} -> {B[c]['verdict']:<6} "
              f"(truth {A[c]['expected']})  {c[:44]}")

    OUT.mkdir(parents=True, exist_ok=True)
    json.dump({"paired": len(both), "scored_both": len(sc),
               "mcnemar_b": b, "mcnemar_c": cc, "p": p,
               "flips": [{"id": c, "a": A[c]["verdict"], "b": B[c]["verdict"],
                          "expected": A[c]["expected"]} for c in flips]},
              open(OUT / f"ctx_compare_{arm_a}_{arm_b}.json", "w"), indent=1)


async def run_arm(a) -> None:
    # num_ctx must be set BEFORE services.council is imported: it reads the
    # environment at module load.
    os.environ["OLLAMA_NUM_CTX"] = str(a.num_ctx)
    from eval.run_benchmark import _run_one
    from services import council
    assert council.NUM_CTX == a.num_ctx, f"num_ctx did not take: {council.NUM_CTX}"

    spec = next(s for s in council.SPECIALISTS if s["role"] == "business_logic")

    pool = []
    max_tokens = a.max_tokens
    excluded_tail = 0
    for it in thirdeye_bench.load():
        try:
            code = it.read_code()
        except Exception:
            continue
        tok = len(council._build_prompt(spec, code)) // CHARS_PER_TOKEN
        # THE COST CEILING, and why it is not outcome-driven selection.
        #
        # The overflow pool is by construction the LARGEST contracts in the
        # corpus, and its extreme tail (up to 12.6x the window) costs 500-700s
        # per contract. A first pass managed 14 contracts in 24 minutes, which
        # would have paired ~16 and left McNemar unable to say anything.
        #
        # Capping the prompt size raises n by roughly 4x within the same budget.
        # The decision was made on MEASURED LATENCY ONLY -- no verdict from
        # either arm had been examined -- so it is a feasibility restriction, not
        # a choice made after seeing results.
        #
        # It biases the estimate CONSERVATIVELY: the excluded contracts are the
        # ones where truncation is most severe, so whatever effect we measure on
        # the retained band is a LOWER bound on the effect over the full pool.
        # THE SAFE-CLASS ARM, and why it needs its own run.
        #
        # The overflow pool is 350 vulnerable against 190 safe, so an unfiltered
        # seeded draw put only FOUR safe contracts into the paired scored set --
        # an FPR comparison with intervals [4.6, 69.9] vs [15.0, 85.0], which
        # says nothing. False alarms are this project's headline metric, so
        # "we do not know what a correct context window does to FPR" is not an
        # acceptable gap. Restricting the pool to one class buys the power.
        if a.label and (
            ("vulnerable" if it.ground_truth_label == "vulnerable" else "safe") != a.label):
            continue
        if tok > 4096 and (not max_tokens or tok <= max_tokens):
            pool.append(it)
        elif tok > 4096:
            excluded_tail += 1
    rng = random.Random(f"ctxablation:{a.sample_seed}")
    rng.shuffle(pool)
    items = pool[: a.n]
    print(f"[ctx] arm={a.arm} num_ctx={a.num_ctx} pool={len(pool)} n={len(items)} "
          f"conc={a.concurrency}"
          + (f"  (cost ceiling {max_tokens} tok excluded {excluded_tail} "
             f"extreme-overflow contracts — conservative)" if max_tokens else ""),
          flush=True)

    ckpt = CKPT_ROOT / f"ctx_{a.arm}"   # arm label carries the class, e.g. ctx4k_safe
    ckpt.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(a.concurrency)
    deadline = time.time() + a.max_minutes * 60 if a.max_minutes else None
    t0 = time.time()

    async def one(i, it):
        cp = ckpt / f"{it.contract_id}.json"
        if cp.exists():
            return json.load(open(cp, encoding="utf-8"))
        if deadline and time.time() > deadline:
            return None
        async with sem:
            if deadline and time.time() > deadline:
                return None
            r = await _run_one(it, "ollama", a.seed, use_arbitration=False)
        r["num_ctx"] = a.num_ctx
        r["expected"] = "vulnerable" if it.ground_truth_label == "vulnerable" else "safe"
        r["tier"] = (it.meta or {}).get("tier", "?")
        json.dump(r, open(cp, "w"), indent=1)
        print(f"  [{i}/{len(items)}] {r['verdict']:<12} {r.get('latency_s')}s  "
              f"{it.contract_id[:46]}", flush=True)
        return r

    got = await asyncio.gather(*[one(i, it) for i, it in enumerate(items, 1)])
    rows = [r for r in got if r]
    scored = [r for r in rows if r["verdict"] in ("GO", "NO-GO")]
    print(f"\n=== CTX ARM {a.arm} (num_ctx={a.num_ctx}) ===")
    print(f"attempted {len(rows)}  scored {len(scored)}  "
          f"inconclusive {len(rows)-len(scored)}  wall {(time.time()-t0)/60:.1f} min")
    OUT.mkdir(parents=True, exist_ok=True)
    json.dump({"arm": a.arm, "num_ctx": a.num_ctx, "rows": rows},
              open(OUT / f"ctx_{a.arm}.json", "w"), indent=1)


def build_parser():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", help="label, e.g. ctx4k or ctx32k")
    ap.add_argument("--num-ctx", type=int)
    ap.add_argument("--n", type=int, default=120, help="contracts per arm")
    ap.add_argument("--max-tokens", type=int, default=0,
                    help="cost ceiling: exclude prompts above this estimated token count")
    ap.add_argument("--label", choices=["safe", "vulnerable"], default=None,
                    help="restrict the pool to one ground-truth class")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--sample-seed", type=int, default=0)
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--max-minutes", type=float, default=0)
    ap.add_argument("--compare", nargs=2, metavar=("ARM_A", "ARM_B"),
                    help="paired comparison of two completed arms")
    return ap


if __name__ == "__main__":
    args = build_parser().parse_args()
    if args.compare:
        compare(args.compare[0], args.compare[1])
    else:
        if not args.arm or args.num_ctx is None:
            raise SystemExit("--arm and --num-ctx are required unless --compare is used")
        asyncio.run(run_arm(args))
