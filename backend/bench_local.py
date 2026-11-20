# -*- coding: utf-8 -*-
"""Measure what a LIVE demo on this laptop actually costs.

The classroom demo stands or falls on latency, and this machine is not the
campus GB10: an RTX 3050 Laptop has 4 GB of VRAM, while qwen2.5-coder:7b alone
is 4.68 GB. At least one council model therefore cannot stay resident and will
swap against the others. Guessing at that is how a demo dies in front of a
panel, so measure it per model on a contract the size of a demo sample.
"""
import asyncio
import os
import time

os.environ.setdefault("LLM_BACKEND", "ollama")

from services import council  # noqa: E402

SAMPLE = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Vault {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "insufficient");
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "transfer failed");
        balances[msg.sender] -= amount;
    }
}
"""


async def main():
    # qwen3:8b (5.2 GB) is deliberately NOT measured: it is the ARBITRATION
    # judge, arbitration ships OFF by default, and on 4 GB of VRAM it spilled
    # to CPU and did not return a single reply in 20 minutes. That is the
    # measurement -- it is not demo-viable on this laptop, and the demo does
    # not need it.
    models = ["llama3.2:3b", "gemma3:4b", "qwen2.5-coder:7b"]
    prompt = ("You are a smart-contract security specialist. In ONE sentence, "
              "does this contract have a reentrancy bug? Answer yes or no and "
              "name the line.\n\n" + SAMPLE)

    print(f"{'model':<22}{'cold (s)':>10}{'warm (s)':>10}   reply")
    print("-" * 78)
    results = {}
    for m in models:
        t0 = time.time()
        try:
            r1 = await council._query_ollama_model(m, prompt, timeout=600)
            cold = time.time() - t0
        except Exception as e:  # noqa: BLE001
            print(f"{m:<22}{'ERROR':>10}   {str(e)[:40]}")
            continue
        t1 = time.time()
        try:
            await council._query_ollama_model(m, prompt, timeout=600)
            warm = time.time() - t1
        except Exception:  # noqa: BLE001
            warm = float("nan")
        results[m] = (cold, warm)
        print(f"{m:<22}{cold:>10.1f}{warm:>10.1f}   {(r1 or '')[:34].strip()!r}")

    print()
    if results:
        trio = [m for m in ("llama3.2:3b", "gemma3:4b", "qwen2.5-coder:7b") if m in results]
        cold_sum = sum(results[m][0] for m in trio)
        warm_sum = sum(results[m][1] for m in trio)
        print(f"shipped council trio, one call each: cold {cold_sum:.0f}s, warm {warm_sum:.0f}s")
        print("A real scan makes a median of 11 such calls, so multiply accordingly.")


if __name__ == "__main__":
    asyncio.run(main())
