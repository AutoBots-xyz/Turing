"""
routers/runs.py — Session Management Endpoints

Combines REST endpoints for database-backed runs (Mayank)
and the in-memory background orchestrator (Harsh).
"""
from typing import List, Dict, Any
import logging
import os
import time

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

# Mayank's DB Imports
from database.database import get_db
from database import crud
from schemas.run import Run, RunCreate, RunStatus

router = APIRouter()

logger = logging.getLogger(__name__)

# ==============================================================================
# 1. DATABASE-BACKED CRUD ENDPOINTS (Mayank)
# ==============================================================================

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

# ==============================================================================
# 2. IN-MEMORY STATE ORCHESTRATOR & BACKGROUND TASKS (Harsh)
# ==============================================================================

# RUNS_STORE is an in-process cache for real-time polling during an active run.
# All durable state is also written to the database so it survives server
# restarts and works correctly in multi-worker deployments.
# { runId: { "currentLayer": int, "layer1Status": str, "graph": dict, ... } }
RUNS_STORE: Dict[str, Dict[str, Any]] = {}


def get_default_state(run_id: str) -> Dict[str, Any]:
    return {
        "runId": run_id,
        "currentLayer": 1,
        "layer1Status": "pending",
        "layer2Status": "pending",
        "layer3Status": "pending",
        "layer4Status": "pending",
        "graph": None,
    }


async def _persist_status(run_id: str, status: RunStatus, error: str | None = None) -> None:
    """Write the run status to the database (fire-and-forget, errors are logged)."""
    try:
        from database.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            await crud.update_run_status(db, run_id, status, error)
            await db.commit()
    except Exception as exc:
        logger.error(f"Failed to persist status '{status}' for run {run_id}: {exc}")


async def _persist_graph(run_id: str, graph: dict) -> None:
    """Write the causal graph to the database (fire-and-forget, errors are logged)."""
    try:
        from database.database import AsyncSessionLocal
        from schemas.graph import CausalGraph
        graph_schema = CausalGraph(**graph)
        async with AsyncSessionLocal() as db:
            await crud.update_run_graph(db, run_id, graph_schema)
            await db.commit()
    except Exception as exc:
        logger.error(f"Failed to persist graph for run {run_id}: {exc}")


async def process_layer1(run_id: str, file_bytes: bytes, filename: str):
    """Background task: orchestrates all 8 steps of Layer 1 autonomously."""
    try:
        RUNS_STORE[run_id]["layer1Status"] = "processing"
        await _persist_status(run_id, RunStatus.RUNNING)

        # Step 1: Detect
        from services.layer1.file_detector import UniversalFileDetector
        detection = UniversalFileDetector.analyze_file(file_bytes, filename)
        path_type = detection.get("path", "DATA")

        # Step 2: Extract  /  Step 3: Build Graph
        from services.layer1.extractor import UniversalExtractor
        if path_type == "DATA":
            df, _ = UniversalExtractor.extract_data(file_bytes, filename)
            from services.layer1.pc_algorithm import PCGraphBuilder
            graph = PCGraphBuilder.build_graph(df)
        else:
            text = UniversalExtractor.extract_text(file_bytes, filename)
            from services.layer1.ontology_builder import LLMGraphBuilder
            _model = os.getenv("DEFAULT_LLM_MODEL", "gpt-4o")
            graph = LLMGraphBuilder.build_graph(text, _model)

        # Immediately expose the raw graph to the UI and persist it
        RUNS_STORE[run_id]["graph"] = graph
        await _persist_graph(run_id, graph)

        # Steps 4–8: validate, fit, classify, score ambiguity, check confidence
        try:
            from services.layer1.validator import GraphValidator
            _model = os.getenv("DEFAULT_LLM_MODEL", "gpt-4o")
            result = GraphValidator.validate(graph, _model)
            # GraphValidator.validate returns {"graph": ..., "logs": [...]}
            graph = result.get("graph", graph) if isinstance(result, dict) and "graph" in result else result
            RUNS_STORE[run_id]["graph"] = graph
            await _persist_graph(run_id, graph)

            from services.layer1.fitter import StructuralFitter
            if path_type == "DATA":
                StructuralFitter.fit_graph(df, graph, path_type)

            from services.layer1.classifier import NodeClassifier
            graph = NodeClassifier.classify_graph(graph)
            RUNS_STORE[run_id]["graph"] = graph

            from services.layer1.ambiguity import AmbiguityDetector
            graph = AmbiguityDetector.analyze_graph(graph)
            RUNS_STORE[run_id]["graph"] = graph

            from services.layer1.confidence import ConfidenceChecker
            ConfidenceChecker.evaluate_graph(graph, path_type)

            # Persist the fully-enriched graph after all steps succeed
            await _persist_graph(run_id, graph)

        except Exception as e:
            logger.error(f"Advanced layer 1 steps failed for run {run_id}: {e}", exc_info=True)
            RUNS_STORE[run_id]["layer1Status"] = "failed"
            await _persist_status(run_id, RunStatus.FAILED, str(e))
            return

        RUNS_STORE[run_id]["layer1Status"] = "completed"
        RUNS_STORE[run_id]["currentLayer"] = 2
        RUNS_STORE[run_id]["layer2Status"] = "processing"

    except Exception as e:
        logger.error(f"Fatal error in background task for run {run_id}: {e}", exc_info=True)
        RUNS_STORE[run_id]["layer1Status"] = "failed"
        await _persist_status(run_id, RunStatus.FAILED, str(e))


@router.post("/{run_id}/layer1/upload")
async def upload_dataset(run_id: str, background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if run_id not in RUNS_STORE:
        RUNS_STORE[run_id] = get_default_state(run_id)

    file_bytes = await file.read()
    background_tasks.add_task(process_layer1, run_id, file_bytes, file.filename)
    return {"status": "accepted", "runId": run_id}


@router.get("/{run_id}/state")
async def get_state(run_id: str, db: AsyncSession = Depends(get_db)):
    """
    Returns the real-time pipeline state for a run.

    Priority:
    1. In-memory cache  — fast, available during an active background task.
    2. Database record  — fallback when the cache is cold (server restart /
                          multi-worker deployment / run completed long ago).
    """
    if run_id in RUNS_STORE:
        return RUNS_STORE[run_id]

    # Cold-start: rebuild state from the persisted DB record
    row = await crud.get_run(db, run_id)
    if not row:
        # Initialise a fresh default state — the upload endpoint hasn't been called yet
        RUNS_STORE[run_id] = get_default_state(run_id)
        return RUNS_STORE[run_id]

    # Map DB status → in-memory layer progress so the frontend renders correctly
    status_map = {
        "PENDING":  {"layer1Status": "pending",   "currentLayer": 1},
        "RUNNING":  {"layer1Status": "processing", "currentLayer": 1},
        "COMPLETE": {"layer1Status": "completed",  "currentLayer": 4},
        "FAILED":   {"layer1Status": "failed",     "currentLayer": 1},
    }
    progress = status_map.get(row.status, {"layer1Status": "pending", "currentLayer": 1})

    state = {
        "runId": run_id,
        "currentLayer": progress["currentLayer"],
        "layer1Status": progress["layer1Status"],
        "layer2Status": "pending",
        "layer3Status": "pending",
        "layer4Status": "pending",
        "graph": row.get_causal_graph(),
    }
    RUNS_STORE[run_id] = state  # Warm the cache
    return state


@router.get("/{run_id}/layer1/graph")
async def get_graph(run_id: str, db: AsyncSession = Depends(get_db)):
    # Try in-memory cache first (fast path during active processing)
    if run_id in RUNS_STORE and RUNS_STORE[run_id].get("graph"):
        return RUNS_STORE[run_id]["graph"]

    # Fall back to the persisted graph from the database
    row = await crud.get_run(db, run_id)
    if row:
        graph = row.get_causal_graph()
        if graph:
            return graph

    # The frontend expects {\"nodes\": [], \"edges\": []} when no graph exists yet
    return {"nodes": [], "edges": []}
"]