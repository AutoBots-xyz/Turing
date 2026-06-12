"""
routers/layer2.py — Layer 2 Agent Simulation Endpoints

Fixes Error 4 (Batch 4): This file was completely empty.
Exposes the /simulate endpoint that runs the Bayesian Optimization +
Do-Calculus + 3-Agent ReAct loop on a given causal graph.
"""
from fastapi import APIRouter, HTTPException

from schemas.layer2 import Layer2Request, Layer2Response
from services.layer2.bayesian_optimizer import run_bayesian_optimization

router = APIRouter()


@router.post(
    "/simulate",
    response_model=Layer2Response,
    summary="Layer 2 — Run Bayesian agent simulation on a causal graph"
)
async def simulate(request: Layer2Request):
    """
    Accepts a CausalGraph and a target node id. Runs up to `max_iterations`
    rounds of Bayesian Optimization where three ReAct agents (Explorer,
    Exploiter, Contrarian) propose causal interventions. Returns the best
    intervention and all simulation results.
    """
    try:
        return await run_bayesian_optimization(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
