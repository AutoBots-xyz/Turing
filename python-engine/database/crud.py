"""
database/crud.py — CRUD Operations for RunModel

Fixes Error 8 (Batch 4): This file was completely empty.
Provides async create/read/update functions used by the FastAPI routers.
All functions accept an AsyncSession and return Pydantic models or ORM objects.
"""
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import RunModel
from schemas.run import Run, RunCreate, RunStatus
from schemas.graph import CausalGraph
from schemas.layer3 import RankedBridge


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

async def create_run(db: AsyncSession, payload: RunCreate) -> RunModel:
    """
    Persists a new Run with PENDING status and returns the ORM row.
    The caller is responsible for committing the session (handled by get_db).
    """
    run = RunModel(
        id=str(uuid.uuid4()),
        status="PENDING",
        input_file=payload.input_file,
        input_type=payload.input_type,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(run)
    await db.flush()   # Flush to get the id without committing
    return run


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

async def get_run(db: AsyncSession, run_id: str) -> Optional[RunModel]:
    """Returns the RunModel for the given run_id, or None if not found."""
    result = await db.execute(select(RunModel).where(RunModel.id == run_id))
    return result.scalar_one_or_none()


async def get_all_runs(db: AsyncSession, limit: int = 50) -> List[RunModel]:
    """Returns the most recent `limit` runs, newest first."""
    result = await db.execute(
        select(RunModel).order_by(RunModel.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

async def update_run_status(
    db: AsyncSession,
    run_id: str,
    status: RunStatus,
    error_message: Optional[str] = None,
) -> Optional[RunModel]:
    """Updates only the status (and optional error message) of a run."""
    run = await get_run(db, run_id)
    if not run:
        return None
    run.status = status.value
    run.updated_at = datetime.utcnow()
    if error_message is not None:
        run.error_message = error_message
    await db.flush()
    return run


async def update_run_graph(
    db: AsyncSession,
    run_id: str,
    graph: CausalGraph,
) -> Optional[RunModel]:
    """Persists the causal graph produced by Layer 1/2 for a given run."""
    run = await get_run(db, run_id)
    if not run:
        return None
    run.set_causal_graph(graph.model_dump())
    run.updated_at = datetime.utcnow()
    await db.flush()
    return run


async def update_run_bridges(
    db: AsyncSession,
    run_id: str,
    bridges: List[RankedBridge],
) -> Optional[RunModel]:
    """Persists the Top 3 bridges produced by Layer 3 for a given run."""
    run = await get_run(db, run_id)
    if not run:
        return None
    run.set_top_bridges([b.model_dump() for b in bridges])
    run.status = "COMPLETE"
    run.updated_at = datetime.utcnow()
    await db.flush()
    return run


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

async def delete_run(db: AsyncSession, run_id: str) -> bool:
    """Deletes a run by id. Returns True if deleted, False if not found."""
    run = await get_run(db, run_id)
    if not run:
        return False
    await db.delete(run)
    await db.flush()
    return True
