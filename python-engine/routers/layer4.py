"""
routers/layer4.py — Layer 4 Report Generation Endpoints

Fixes Error 4 (Batch 4): This file was completely empty.
Exposes the /report endpoint that generates the final human-readable report
from the Top 3 cross-domain bridges produced by Layer 3.
"""
from fastapi import APIRouter, HTTPException

from schemas.report import FinalReport
from schemas.layer3 import Step14Response
from services.layer4.report_builder import build_report

router = APIRouter()


@router.post(
    "/report",
    response_model=FinalReport,
    summary="Layer 4 — Generate final cross-domain bridge report"
)
async def generate_report(run_id: str, bridges: Step14Response):
    """
    Accepts the Step 14 Top 3 ranked bridges and generates a full
    human-readable FinalReport including problem statement, executive
    summary, recommended experiment, and contradiction warnings.
    """
    try:
        return await build_report(run_id=run_id, step14_response=bridges)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
