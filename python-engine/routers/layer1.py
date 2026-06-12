"""
routers/layer1.py — Layer 1 Data Ingestion Endpoints

Exposes both the high-level orchestration endpoints (upload, status)
and the granular, step-by-step pipeline microservices for the Data Path and Text Path.
"""
import os
import tempfile
from typing import Dict, Any, Optional

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Form
from sqlalchemy.ext.asyncio import AsyncSession

# Mayank's DB & Orchestration Imports
from database.database import get_db
from database import crud
from schemas.run import RunStatus

# Layer 1 Detection & Pipeline Imports
from services.layer1.file_detector import detect_input_type, validate_file_exists, InputType, UniversalFileDetector
from services.layer1.extractor import UniversalExtractor
from services.layer1.pc_algorithm import PCGraphBuilder
from services.layer1.ontology_builder import LLMGraphBuilder
from services.layer1.validator import GraphValidator
from services.layer1.fitter import StructuralFitter
from services.layer1.classifier import NodeClassifier
from services.layer1.ambiguity import AmbiguityDetector
from services.layer1.confidence import ConfidenceChecker

router = APIRouter()

# ==============================================================================
# 1. ORCHESTRATION ENDPOINTS (Mayank)
# ==============================================================================

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
    and marks the run as RUNNING.
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


# ==============================================================================
# 2. GRANULAR PIPELINE ENDPOINTS (Harsh)
# ==============================================================================

@router.post("/detect")
async def detect_file_type(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Step 1: Universal File Detector.
    Receives an uploaded file, analyzes its contents (in-memory),
    and routes it to either the DATA PATH or TEXT PATH.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
        
    try:
        file_bytes = await file.read()
        result = UniversalFileDetector.analyze_file(file_bytes, file.filename)
        
        result["filename"] = file.filename
        result["size_bytes"] = len(file_bytes)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/extract")
async def extract_data(
    path_type: str = Form(...),
    file: UploadFile = File(...)
) -> Dict[str, Any]:
    """
    Step 2: Universal Data Extractor.
    Takes a file and the detected path_type ('DATA' or 'TEXT').
    Returns a standardized mathematical table (JSON array) or a clean text string.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
        
    if path_type not in ["DATA", "TEXT"]:
        raise HTTPException(status_code=400, detail="path_type must be DATA or TEXT")
        
    try:
        file_bytes = await file.read()
        
        response = {
            "path_type": path_type,
            "filename": file.filename,
            "data": None,
            "text": None,
            "warnings": [],
            "columns": []
        }
        
        if path_type == "DATA":
            df, warnings = UniversalExtractor.extract_data(file_bytes, file.filename)
            response["data"] = df.to_dict(orient="records")
            response["columns"] = df.columns.tolist()
            response["warnings"] = warnings
        else:
            text = UniversalExtractor.extract_text(file_bytes, file.filename)
            response["text"] = text
            
        return response
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/build-graph")
async def build_graph(
    payload: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Step 3: Graph Builder.
    Takes the extracted payload (data or text) and returns a unified 
    NetworkX causal graph representation.
    """
    path_type = payload.get("path_type")
    
    if path_type not in ["DATA", "TEXT"]:
        raise HTTPException(status_code=400, detail="Invalid or missing path_type")
        
    try:
        if path_type == "DATA":
            data = payload.get("data")
            if not data:
                raise ValueError("DATA path requires 'data' array in payload")
            
            df = pd.DataFrame(data)
            graph_json = PCGraphBuilder.build_graph(df)
            return graph_json
            
        else:
            text = payload.get("text")
            model_name = payload.get("model_name", "gpt-4o") # User specified model
            
            if not text:
                raise ValueError("TEXT path requires 'text' string in payload")
                
            graph_json = LLMGraphBuilder.build_graph(text, model_name)
            return graph_json
            
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/validate-graph")
async def validate_graph(
    payload: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Step 4: Graph Validator.
    Takes a raw JSON graph {"nodes": [], "edges": []} from Step 3,
    runs the autonomous physics checks, breaks cycles, and flags contradictions.
    """
    graph_data = payload.get("graph")
    model_name = payload.get("model_name", "gpt-4o")
    
    if not graph_data or not isinstance(graph_data, dict):
        raise HTTPException(status_code=400, detail="Missing or invalid 'graph' object in payload")
        
    if "nodes" not in graph_data or "edges" not in graph_data:
        raise HTTPException(status_code=400, detail="'graph' must contain 'nodes' and 'edges' arrays")
        
    try:
        validated_result = GraphValidator.validate(graph_data, model_name)
        return validated_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/fit-equations")
async def fit_equations(
    payload: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Step 5: Structural Equation Fitter.
    Fits Gaussian Processes to the edges (DATA path only), saves the models,
    and returns a session_id and fit metrics.
    """
    graph_data = payload.get("graph")
    path_type = payload.get("path_type")
    data = payload.get("data", [])
    
    if not graph_data or not isinstance(graph_data, dict):
        raise HTTPException(status_code=400, detail="Missing or invalid 'graph' object in payload")
        
    if not path_type or path_type not in ["DATA", "TEXT"]:
        raise HTTPException(status_code=400, detail="path_type must be DATA or TEXT")
        
    try:
        if path_type == "DATA":
            if not data:
                raise ValueError("DATA path requires 'data' array in payload for fitting")
            df = pd.DataFrame(data)
            fitted_graph = StructuralFitter.fit_graph(df, graph_data, path_type)
        else:
            # Skip text path
            fitted_graph = StructuralFitter.fit_graph(pd.DataFrame(), graph_data, path_type)
            
        return fitted_graph
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/classify-nodes")
async def classify_nodes(
    payload: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Step 6: Node Classifier.
    Takes a graph from Step 5, calculates in/out degrees, and applies
    semantic labels and UI themes (Source, Sink, Bottleneck, Mediator).
    """
    graph_data = payload.get("graph")
    
    if not graph_data or not isinstance(graph_data, dict):
        raise HTTPException(status_code=400, detail="Missing or invalid 'graph' object in payload")
        
    if "nodes" not in graph_data or "edges" not in graph_data:
        raise HTTPException(status_code=400, detail="'graph' must contain 'nodes' and 'edges' arrays")
        
    try:
        classified_graph = NodeClassifier.classify_graph(graph_data)
        return classified_graph
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/detect-ambiguity")
async def detect_ambiguity(
    payload: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Step 7: Ambiguity Detector.
    Takes the classified graph, scores edges, and ranks unknown nodes.
    """
    graph_data = payload.get("graph")
    
    if not graph_data or not isinstance(graph_data, dict):
        raise HTTPException(status_code=400, detail="Missing or invalid 'graph' object in payload")
        
    try:
        final_graph = AmbiguityDetector.analyze_graph(graph_data)
        return final_graph
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/confidence-check")
async def confidence_check(
    payload: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Step 8: Confidence Check.
    Makes the final routing decision and assembles the Output Package.
    """
    graph_data = payload.get("graph")
    path_type = payload.get("path_type", "DATA")
    
    if not graph_data or not isinstance(graph_data, dict):
        raise HTTPException(status_code=400, detail="Missing or invalid 'graph' object in payload")
        
    try:
        output_package = ConfidenceChecker.evaluate_graph(graph_data, path_type)
        return output_package
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))