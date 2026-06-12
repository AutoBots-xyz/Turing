"""
routers/runs.py — Session Management Endpoints

Combines REST endpoints for database-backed runs (Mayank)
and the in-memory background orchestrator (Harsh).
"""
from typing import List, Dict, Any
import time

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

# Mayank's DB Imports
from database.database import get_db
from database import crud
from schemas.run import Run, RunCreate, RunStatus

router = APIRouter()

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

# In-memory store: { runId: { "currentLayer": int, "layer1Status": str, "graph": dict } }
RUNS_STORE = {}

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

async def process_layer1(run_id: str, file_bytes: bytes, filename: str):
    # This background task orchestrates the 8 steps of Layer 1 autonomously
    try:
        RUNS_STORE[run_id]["layer1Status"] = "processing"
        
        # Step 1: Detect
        from services.layer1.file_detector import UniversalFileDetector
        detection = UniversalFileDetector.analyze_file(file_bytes, filename)
        path_type = detection.get("path_type", "DATA")
        
        # Step 2: Extract
        from services.layer1.extractor import UniversalExtractor
        if path_type == "DATA":
            df, _ = UniversalExtractor.extract_data(file_bytes, filename)
            # Step 3: Build Graph
            from services.layer1.pc_algorithm import PCGraphBuilder
            graph = PCGraphBuilder.build_graph(df)
        else:
            text = UniversalExtractor.extract_text(file_bytes, filename)
            from services.layer1.ontology_builder import LLMGraphBuilder
            graph = LLMGraphBuilder.build_graph(text, "gpt-4o")
            
        # Update State immediately to feed UI
        RUNS_STORE[run_id]["graph"] = graph
        
        # Step 4-8
        try:
            from services.layer1.validator import GraphValidator
            graph = GraphValidator.validate(graph, "gpt-4o")
            RUNS_STORE[run_id]["graph"] = graph
            
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
        except Exception as e:
            print(f"Warning during advanced layer 1 steps: {e}")
            
        RUNS_STORE[run_id]["layer1Status"] = "completed"
        RUNS_STORE[run_id]["currentLayer"] = 2
        RUNS_STORE[run_id]["layer2Status"] = "processing"
        
    except Exception as e:
        print(f"Error in background task for run {run_id}: {e}")
        RUNS_STORE[run_id]["layer1Status"] = "failed"


@router.post("/{run_id}/layer1/upload")
async def upload_dataset(run_id: str, background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if run_id not in RUNS_STORE:
        RUNS_STORE[run_id] = get_default_state(run_id)
        
    file_bytes = await file.read()
    background_tasks.add_task(process_layer1, run_id, file_bytes, file.filename)
    return {"status": "accepted", "runId": run_id}


@router.get("/{run_id}/state")
async def get_state(run_id: str):
    if run_id not in RUNS_STORE:
        RUNS_STORE[run_id] = get_default_state(run_id)
    return RUNS_STORE[run_id]


@router.get("/{run_id}/layer1/graph")
async def get_graph(run_id: str):
    if run_id not in RUNS_STORE or not RUNS_STORE[run_id].get("graph"):
        # The frontend expects {"nodes": [], "edges": []} initially
        return {"nodes": [], "edges": []}
    return RUNS_STORE[run_id]["graph"]