# Tuesday — campus GPU session

## Do this

On campus, on the laptop, in this folder:

```bash
./TUESDAY_START.sh
```

That's it. It checks the box is reachable, re-syncs the fixed eval code, and
launches the session detached. **Safe to close the lid afterwards** — the run is
`setsid`-detached, so dropping wifi or shutting the laptop does not kill it.

Optional: `./TUESDAY_START.sh 150` for a shorter budget (default 210 minutes).

## Then

```bash
./TUESDAY_STATUS.sh     # progress; run as often as you like
./TUESDAY_FETCH.sh      # RUN THIS BEFORE YOU LEAVE CAMPUS
```

`TUESDAY_FETCH.sh` is not optional. The box is on a **private campus address**
(10.1.72.54) and is unreachable from anywhere else — anything left on it is
stranded until the next visit.

## What runs, in order

| | stage | why it needs that machine | time |
|--|---|---|--|
| A | finish the 8B ablation | `llama3.1:8b` does not fit in the laptop's 4GB | ~10 min |
| B | **full-scale benchmark** | the run that fixes the per-tier confidence intervals | ~105 min |
| C | `NUM_PARALLEL=1` control | needs a second machine by definition | ~45 min |
| D | web3bugs | throughput | remainder |

**B is the one that matters.** The per-tier false-alarm gradient (19% / 25% /
34%) currently rests on ~40 contracts per tier, giving ±13-point intervals that
overlap almost completely — so the gradient cannot yet be claimed. At full
scale the intervals separate and the claim holds.

Every stage is checkpointed per contract and budget-aware: it stops cleanly at
its deadline and writes its report rather than being killed. Re-running resumes.

## If something looks wrong

- **"CANNOT REACH"** — box powered on? on the campus network?
- **Stage B counter not moving** — check `_transient` in the status output. A GO
  verdict with an errored specialist is quarantined as unsound, so timeouts cost
  whole contracts. `LLM_TIMEOUT=600` is set to prevent this.
- **Everything INCONCLUSIVE** — model thrashing. The script sets
  `MAX_LOADED_MODELS=6` and warms every model first, which is what fixes it.

## Do NOT

- **Do not update Ollama on the laptop.** It offers 0.32.15; the laptop baseline
  is 0.24.0. That version difference is one of the variables that made the two
  machines' results incomparable in the first place.
- **Do not merge the DGX checkpoints into the laptop tree.** They are different
  platforms and they measurably disagree. `TUESDAY_FETCH.sh` keeps them in a
  separate `dgx_fullscale/` directory on purpose.
- **Do not copy `backend/.env` to the box.** It is shared with other students.
  The sync excludes it.

## Still blocking submission

The **related-work survey**. No compute required, and no amount of GPU time
substitutes for it.
