"""
routers/runs.py — Session Management Endpoints

Fixes Error 4 (Batch 4): This file was completely empty.
Exposes REST endpoints for creating, listing, and retrieving analysis runs.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_db
from database import crud
from schemas.run import Run, RunCreate, RunStatus

router = APIRouter()


@router.post("/", response_model=Run, status_code=201, summary="Create a new analysis run")
async def create_run(payload: RunCreate, db: AsyncSession = Depends(get_db)):
    """
    Creates a new Run session with PENDING status.
    The frontend calls this first, then polls GET /api/runs/{run_id} for updates.
    """
    row = await crud.create_run(db, payload)
    return _to_schema(row)


@router.get("/", response_model=List[Run], summary="List all runs")
async def list_runs(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """Returns the most recent `limit` runs ordered by creation time (newest first)."""
    rows = await crud.get_all_runs(db, limit=limit)
    return [_to_schema(r) for r in rows]


@router.get("/{run_id}", response_model=Run, summary="Get a single run")
async def get_run(run_id: str, db: AsyncSession = Depends(get_db)):
    """Returns the current state of a run including status, graph, and bridges."""
    row = await crud.get_run(db, run_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return _to_schema(row)


@router.delete("/{run_id}", status_code=204, summary="Delete a run")
async def delete_run(run_id: str, db: AsyncSession = Depends(get_db)):
    """Deletes a run and all associated data."""
    deleted = await crud.delete_run(db, run_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")


# ---------------------------------------------------------------------------
# Internal helper — ORM → Pydantic
# ---------------------------------------------------------------------------

def _to_schema(row) -> Run:
    return Run(
        id=row.id,
        status=RunStatus(row.status),
        input_file=row.input_file,
        input_type=row.input_type,
        created_at=row.created_at,
        updated_at=row.updated_at,
        causal_graph=row.get_causal_graph(),
        top_bridges=row.get_top_bridges(),
        error_message=row.error_message,
    )
