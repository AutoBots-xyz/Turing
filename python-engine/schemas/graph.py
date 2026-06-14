from typing import List, Optional
from pydantic import BaseModel, Field

class Node(BaseModel):
    id: str
    label: str
    domain: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=100.0, description="Confidence percentage from 0 to 100")
    is_unknown: bool = Field(default=False, description="Explicitly marked as an unknown node")
    description: Optional[str] = None

class Edge(BaseModel):
    source: str
    target: str
    relation: str
    confidence: float = Field(..., ge=0.0, le=100.0, description="Confidence percentage from 0 to 100")
    weight: float = Field(default=1.0, description="Edge weight (e.g., correlation coefficient)")

class CausalGraph(BaseModel):
    nodes: List[Node]
    edges: List[Edge]
