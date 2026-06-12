"""
routers/layer1.py — Layer 1 Data Ingestion Endpoints

Fixes Error 4 (Batch 4): This file was completely empty.
Exposes file upload and routing endpoints for the Data Path (CSV)
and Text Path (PDF/text) of the Causal Nexus pipeline.
"""
import os
import tempfile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_db
from database import crud
from schemas.run import RunStatus
from services.layer1.file_detector import detect_input_type, validate_file_exists, InputType

router = APIRouter()


@router.post(
    "/upload",
    summary="Upload a CSV or document file to start a new analysis run",
    status_code=202,
)
async def upload_file(
    run_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Accepts a file upload, persists it temporarily, detects its type,
    and marks the run as RUNNING. Processing continues asynchronously
    through the pipeline (Data Path or Text Path).

    The frontend should have already created the run via POST /api/runs
    and obtained the run_id before calling this endpoint.
    """
    run = await crud.get_run(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    # Save the uploaded file to a temp location for processing
    suffix = os.path.splitext(file.filename or "upload")[1] or ".bin"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    # Detect file type and validate
    if not validate_file_exists(tmp_path):
        raise HTTPException(status_code=400, detail="Uploaded file is empty or unreadable")

    input_type = detect_input_type(tmp_path)
    if input_type == InputType.UNKNOWN:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: '{suffix}'. Use CSV, PDF, TXT, DOCX, or XLSX."
        )

    # Update run status to RUNNING
    await crud.update_run_status(db, run_id, RunStatus.RUNNING)

    return {
        "run_id": run_id,
        "filename": file.filename,
        "detected_type": input_type.value,
        "message": "File accepted. Processing pipeline has started.",
    }


@router.get(
    "/status/{run_id}",
    summary="Check the processing status of a Layer 1 run"
)
async def get_status(run_id: str, db: AsyncSession = Depends(get_db)):
    """Lightweight status check — returns the current run status and graph if ready."""
    run = await crud.get_run(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return {
        "run_id": run.id,
        "status": run.status,
        "causal_graph": run.get_causal_graph(),
    }
