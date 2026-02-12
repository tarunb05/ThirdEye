from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.llm import summarize_code
from services.slither import run_slither
import logging

router = APIRouter()

class AnalyzeRequest(BaseModel):
    code: str
    model_type: str = 'multi-llm'

@router.post('/analyze')
async def analyze(req: AnalyzeRequest):
    '''
    Analyze Solidity contract code.
    Returns streaming response with updates.
    '''
    if not req.code or len(req.code.strip()) < 10:
        raise HTTPException(status_code=422, detail='Code is too short or empty')
    
    try:
        # Step 1: Validate with Slither
        slither_output = run_slither(req.code)
        
        # Step 2: Summarize code
        summary = await summarize_code(req.code)
        
        return {
            'summary': summary,
            'slither_output': slither_output,
            'status': 'success'
        }
    except Exception as e:
        logging.error(f'Analysis failed: {str(e)}')
        raise HTTPException(status_code=500, detail=str(e))
