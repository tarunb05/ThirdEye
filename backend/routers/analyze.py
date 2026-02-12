from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.llm import summarize_code
from services.slither import run_slither
from services.aggregator import aggregate_scans, determine_verdict
from utils.cache import get_cached_analysis, set_cached_analysis
import logging
import asyncio

router = APIRouter()

class AnalyzeRequest(BaseModel):
    code: str
    model_type: str = "multi-llm"

@router.post("/analyze")
async def analyze(req: AnalyzeRequest):
    """
    Analyze Solidity contract code.
    """
    if not req.code or len(req.code.strip()) < 10:
        raise HTTPException(status_code=422, detail="Code is too short or empty")

    code = req.code

    # 1. Cache check
    cached = get_cached_analysis(code)
    if cached:
        cached["from_cache"] = True
        return cached

    try:
        # 2. Static analysis (sync)
        slither_output = run_slither(code)

        # 3. LLM summary (async)
        summary_task = summarize_code(code)

        # (later: add three model scans here and aggregate)
        summary = await summary_task

        result = {
            "summary": summary,
            "slither_output": slither_output,
            "vulnerabilities": [],      # placeholder
            "final_verdict": "GO",      # placeholder
            "from_cache": False,
        }

        # 4. Store in cache
        set_cached_analysis(code, result)

        return result

    except Exception as e:
        logging.exception("Analysis failed")
        raise HTTPException(status_code=500, detail=str(e))
