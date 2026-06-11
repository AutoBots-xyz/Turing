from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Dict, Any
from services.layer1.file_detector import UniversalFileDetector

router = APIRouter(
    prefix="/api/v1/layer1",
    tags=["layer1"],
)

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
        # Spool file contents into memory
        file_bytes = await file.read()
        
        # Analyze using the UniversalFileDetector
        result = UniversalFileDetector.analyze_file(file_bytes, file.filename)
        
        # Add metadata for the frontend
        result["filename"] = file.filename
        result["size_bytes"] = len(file_bytes)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
