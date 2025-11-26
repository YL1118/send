from fastapi import APIRouter, HTTPException
from schemas.algorithm_schema import AlgoInput, AlgoOutput
from core.logic import compute_result

router = APIRouter()

@router.post("/run", response_model=AlgoOutput)
def run_algorithm(payload: AlgoInput):
    try:
        result = compute_result(payload.x, payload.y)
        return AlgoOutput(result=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
