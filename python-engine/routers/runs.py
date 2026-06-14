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
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
import json

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
        "layer1Progress": 0,
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


async def process_full_pipeline(run_id: str, file_bytes: bytes, filename: str):
    """Background task: orchestrates all 4 Layers autonomously."""
    try:
        # ==========================================
        # LAYER 1: Causal Discovery
        # ==========================================
        if run_id not in RUNS_STORE:
            RUNS_STORE[run_id] = get_default_state(run_id)
            
        RUNS_STORE[run_id]["layer1Status"] = "processing"
        RUNS_STORE[run_id]["layer1Progress"] = 5
        await _persist_status(run_id, RunStatus.RUNNING)

        from services.layer1.file_detector import UniversalFileDetector
        detection = UniversalFileDetector.analyze_file(file_bytes, filename)
        path_type = detection.get("path", "DATA")
        RUNS_STORE[run_id]["layer1Progress"] = 10

        import asyncio
        from services.layer1.extractor import UniversalExtractor
        if path_type == "DATA":
            df, _ = UniversalExtractor.extract_data(file_bytes, filename)
            RUNS_STORE[run_id]["layer1Progress"] = 20
            await asyncio.sleep(1.5)
            from services.layer1.pc_algorithm import PCGraphBuilder
            graph = PCGraphBuilder.build_graph(df)
            RUNS_STORE[run_id]["layer1Progress"] = 40
            await asyncio.sleep(1.5)
        else:
            text = UniversalExtractor.extract_text(file_bytes, filename)
            RUNS_STORE[run_id]["layer1Progress"] = 20
            await asyncio.sleep(1.5)
            from services.layer1.ontology_builder import LLMGraphBuilder
            _model = os.getenv("DEFAULT_LLM_MODEL", "gpt-4o")
            graph = LLMGraphBuilder.build_graph(text, _model)
            RUNS_STORE[run_id]["layer1Progress"] = 40
            await asyncio.sleep(1.5)

        RUNS_STORE[run_id]["graph"] = graph
        await _persist_graph(run_id, graph)

        try:
            from services.layer1.validator import GraphValidator
            _model = os.getenv("DEFAULT_LLM_MODEL", "gpt-4o")
            result = GraphValidator.validate(graph, _model)
            graph = result.get("graph", graph) if isinstance(result, dict) and "graph" in result else result
            RUNS_STORE[run_id]["graph"] = graph
            RUNS_STORE[run_id]["layer1Progress"] = 60
            await _persist_graph(run_id, graph)

            from services.layer1.gaussian_process import StructuralFitter
            if path_type == "DATA":
                StructuralFitter.fit_graph(df, graph, path_type)
            RUNS_STORE[run_id]["layer1Progress"] = 75
            await asyncio.sleep(1.5)

            from services.layer1.classifier import NodeClassifier
            graph = NodeClassifier.classify_graph(graph)
            RUNS_STORE[run_id]["graph"] = graph
            RUNS_STORE[run_id]["layer1Progress"] = 85
            await asyncio.sleep(1.5)

            from services.layer1.extractor import AmbiguityDetector
            graph = AmbiguityDetector.analyze_graph(graph)
            RUNS_STORE[run_id]["graph"] = graph
            RUNS_STORE[run_id]["layer1Progress"] = 95
            await asyncio.sleep(1.5)

            from services.layer1.validator import ConfidenceChecker
            ConfidenceChecker.evaluate_graph(graph, path_type)

            await _persist_graph(run_id, graph)
        except Exception as e:
            # Non-fatal: advanced LLM/fitting steps failed, but we already have
            # the raw graph from PC/LLM extraction. Log the error and continue
            # the pipeline so the user still sees their graph and results.
            logger.warning(
                f"Advanced Layer 1 steps failed for run {run_id} (non-fatal, "
                f"continuing with raw graph): {e}"
            )
            # Make sure graph is still persisted even if enrichment failed
            await _persist_graph(run_id, graph)

        RUNS_STORE[run_id]["layer1Progress"] = 100
        RUNS_STORE[run_id]["layer1Status"] = "completed"
        
        # ==========================================
        # LAYER 2: Bayesian Optimization
        # ==========================================
        RUNS_STORE[run_id]["currentLayer"] = 2
        RUNS_STORE[run_id]["layer2Status"] = "processing"
        
        RUNS_STORE[run_id]["layer2Data"] = {
            "status": "Running Agent Swarm...",
            "nodesComputed": 0,
            "agents": [],
            "heatmapNodes": [],
            "heatmapLines": []
        }
        
        # Find target node
        target_node = "Output"
        if graph and "nodes" in graph and len(graph["nodes"]) > 0:
            target_node = graph["nodes"][-1]["id"]
            
        from services.layer2.orchestrator import run_bayesian_optimization
        from schemas.layer2 import Layer2Request
        from schemas.graph import CausalGraph
        
        try:
            layer2_req = Layer2Request(
                graph=CausalGraph(**graph),
                target_node_id=target_node,
                max_iterations=3
            )
            layer2_res = await run_bayesian_optimization(layer2_req)
            
            agents = []
            agent_index = 0
            for i, res in enumerate(layer2_res.simulation_results):
                for action in res.agent_actions:
                    agents.append({
                        "id": f"action-{i}-{action.agent_id}",
                        "type": action.agent_role,
                        "agentId": action.agent_id,
                        "y": 50 + (agent_index * 90),
                        "content": action.act,
                        "delayMs": agent_index * 150
                    })
                    agent_index += 1
                    
            RUNS_STORE[run_id]["layer2Data"].update({
                "status": "Completed Bayesian Optimization",
                "nodesComputed": len(agents),
                "agents": agents,
            })
        except Exception as e:
            logger.error(f"Layer 2 failed for run {run_id}: {e}", exc_info=True)
            RUNS_STORE[run_id]["layer2Data"]["status"] = f"Failed: {e}"

        RUNS_STORE[run_id]["layer2Status"] = "completed"

        # ==========================================
        # LAYER 3: Cross-Domain Search
        # ==========================================
        RUNS_STORE[run_id]["currentLayer"] = 3
        RUNS_STORE[run_id]["layer3Status"] = "processing"
        
        RUNS_STORE[run_id]["layer3Data"] = {
            "status": "Searching Literature...",
            "query": f"Optimize {target_node}",
            "streamSources": [],
            "topBridges": [],
            "isLocked": False
        }
        
        from schemas.layer3 import StructuralQuery, Step13Request, Step14Request, IsomorphismThresholds
        from routers.layer3 import run_step_11_search, extract, match, rank
        
        try:
            query = StructuralQuery(
                original_node_id=target_node,
                original_confidence=80.0,
                structural_description=f"Mechanisms that causally influence {target_node}"
            )
            
            step11_res = await run_step_11_search(query)
            RUNS_STORE[run_id]["layer3Data"]["streamSources"] = [
                {"src": res.title, "title": res.merged_summary[:50] + "...", "match": res.confidence}
                for res in step11_res.results
            ]
            RUNS_STORE[run_id]["layer3Data"]["status"] = "Extracting Graphs..."
            
            step12_res = await extract(step11_res)
            RUNS_STORE[run_id]["layer3Data"]["status"] = "Matching Isomorphisms..."
            
            step13_req = Step13Request(
                target_graph=CausalGraph(**graph),
                candidates=step12_res.extracted_mechanisms,
                thresholds=IsomorphismThresholds()
            )
            step13_res = await match(step13_req)
            RUNS_STORE[run_id]["layer3Data"]["status"] = "Ranking Bridges..."
            
            step14_req = Step14Request(matches=step13_res.matches)
            step14_res = await rank(step14_req)
            
            RUNS_STORE[run_id]["layer3Data"]["topBridges"] = [
                {
                    "sourceDomain": b.match.mechanism.source_result.sources[0].value if b.match.mechanism.source_result.sources else "UNKNOWN",
                    "targetDomain": "USER_PROBLEM",
                    "isomorphismScore": b.match.isomorphism_score,
                    "description": b.match.mechanism.source_result.underlying_mechanism,
                    "title": b.match.mechanism.source_result.title,
                    "evidenceTier": "HIGH" if b.scores.final_score > 0.8 else "MEDIUM"
                }
                for b in step14_res.top_bridges
            ]
            RUNS_STORE[run_id]["layer3Data"]["status"] = "Completed Bridge Discovery"
        except Exception as e:
            logger.error(f"Layer 3 failed for run {run_id}: {e}", exc_info=True)
            RUNS_STORE[run_id]["layer3Data"]["status"] = f"Failed: {e}"
            step14_res = None
            
        RUNS_STORE[run_id]["layer3Data"]["isLocked"] = True
        RUNS_STORE[run_id]["layer3Status"] = "completed"

        # ==========================================
        # LAYER 4: Report Generation
        # ==========================================
        RUNS_STORE[run_id]["currentLayer"] = 4
        RUNS_STORE[run_id]["layer4Status"] = "processing"
        
        RUNS_STORE[run_id]["layer4Data"] = {
            "isComplete": False,
            "mechanismExplanation": "Generating report...",
            "bridgeSummary": "",
            "experimentResults": "",
            "warnings": []
        }
        
        try:
            from services.layer4.report_builder import build_report
            from schemas.layer3 import Step14Response
            
            if step14_res is None:
                step14_res = Step14Response(top_bridges=[])
                
            final_report = await build_report(run_id, step14_res)
            
            RUNS_STORE[run_id]["layer4Data"] = {
                "isComplete": True,
                "mechanismExplanation": final_report.problem_statement + "\n\n" + final_report.executive_summary,
                "bridgeSummary": "\n".join([b.match.mechanism.source_result.title for b in final_report.top_bridges]) if final_report.top_bridges else "No bridges found.",
                "experimentResults": final_report.recommended_experiment,
                "warnings": final_report.contradiction_warnings
            }
        except Exception as e:
            logger.error(f"Layer 4 failed for run {run_id}: {e}", exc_info=True)
            RUNS_STORE[run_id]["layer4Data"]["isComplete"] = True
            RUNS_STORE[run_id]["layer4Data"]["mechanismExplanation"] = f"Failed to generate report: {e}"
            
        RUNS_STORE[run_id]["layer4Status"] = "completed"
        await _persist_status(run_id, RunStatus.COMPLETE)

    except Exception as e:
        logger.error(f"Fatal error in background task for run {run_id}: {e}", exc_info=True)
        RUNS_STORE[run_id]["layer1Status"] = "failed"
        await _persist_status(run_id, RunStatus.FAILED, str(e))


@router.post("/{run_id}/layer1/upload")
async def upload_dataset(run_id: str, background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if run_id not in RUNS_STORE:
        RUNS_STORE[run_id] = get_default_state(run_id)

    # Immediately set 'processing' so the frontend sees it on its very next poll
    # — this eliminates the race condition where the background task sets it too late.
    RUNS_STORE[run_id]["layer1Status"] = "processing"
    RUNS_STORE[run_id]["layer1Progress"] = 2

    file_bytes = await file.read()
    background_tasks.add_task(process_full_pipeline, run_id, file_bytes, file.filename)
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
        "layer1Progress": 0 if progress["layer1Status"] == "pending" else (100 if progress["layer1Status"] == "completed" else 50),
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


@router.get("/{run_id}/layer2/agents")
async def get_layer2_agents(run_id: str):
    """Returns the Layer 2 UI state (JSON polling)."""
    if run_id in RUNS_STORE and "layer2Data" in RUNS_STORE[run_id]:
        return RUNS_STORE[run_id]["layer2Data"]
        
    # Return empty default state if not ready yet
    return {
        "status": "Waiting for Layer 1...",
        "nodesComputed": 0,
        "agents": [],
        "heatmapNodes": [],
        "heatmapLines": []
    }


@router.get("/{run_id}/layer3/search/stream")
async def get_layer3_stream(run_id: str):
    """Streams Layer 3 state updates via Server-Sent Events (SSE)."""
    async def event_generator():
        last_status = None
        while True:
            if run_id in RUNS_STORE and "layer3Data" in RUNS_STORE[run_id]:
                data = RUNS_STORE[run_id]["layer3Data"]
                # Only yield if status changes or periodically to keep alive
                yield f"data: {json.dumps(data)}\n\n"
                if data.get("isLocked"):
                    break
            else:
                # Send empty state until ready
                yield f"data: {json.dumps({'status': 'Waiting...', 'query': '', 'streamSources': [], 'topBridges': [], 'isLocked': False})}\n\n"
            await asyncio.sleep(1.0)
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/{run_id}/layer4/report/stream")
async def get_layer4_stream(run_id: str):
    """Streams Layer 4 report generation updates via SSE."""
    async def event_generator():
        while True:
            if run_id in RUNS_STORE and "layer4Data" in RUNS_STORE[run_id]:
                data = RUNS_STORE[run_id]["layer4Data"]
                yield f"data: {json.dumps(data)}\n\n"
                if data.get("isComplete"):
                    break
            else:
                yield f"data: {json.dumps({'isComplete': False, 'mechanismExplanation': 'Waiting for prior layers...', 'bridgeSummary': '', 'experimentResults': '', 'warnings': []})}\n\n"
            await asyncio.sleep(1.0)
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")