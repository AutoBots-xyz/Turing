from enum import Enum
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from .graph import CausalGraph
from .layer3 import RankedBridge


class RunStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class RunCreate(BaseModel):
    input_file: Optional[str] = Field(default="unknown.csv", description="Filename of the uploaded CSV or PDF")
    input_type: Optional[str] = Field(default="DATA_PATH", description="'csv' for Data Path, 'text' for Text Path")
    domain: Optional[str] = Field(default="Biology")


class Run(BaseModel):
    id: str
    status: RunStatus = RunStatus.PENDING
    input_file: str
    input_type: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    causal_graph: Optional[CausalGraph] = None
    top_bridges: Optional[List[RankedBridge]] = None
    error_message: Optional[str] = None
