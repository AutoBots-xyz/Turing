from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from .graph import CausalGraph

class StructuralQuery(BaseModel):
    original_node_id: str
    original_confidence: float
    structural_description: str = Field(..., description="The domain-blind structural description of the problem")

class Step10Request(BaseModel):
    graph: CausalGraph
    confidence_threshold: float = Field(default=80.0, description="Nodes with confidence below this threshold are extracted")

class Step10Response(BaseModel):
    queries: List[StructuralQuery]

class SearchSource(str, Enum):
    PAPER = "PAPER"
    WIKIPEDIA = "WIKIPEDIA"
    WEB = "WEB"
    PATENT = "PATENT"

class SearchResult(BaseModel):
    source: SearchSource
    title: str
    summary: str
    url: Optional[str] = None
    confidence: float = Field(..., description="Initial confidence score from this single source (0-100)")
    original_query: StructuralQuery

class DebateTranscript(BaseModel):
    proposer_argument: str
    skeptic_rebuttal: str
    synthesizer_consensus: str

class ContradictionDetails(BaseModel):
    conflict_detected: bool
    nature_of_conflict: str = Field(..., description="Description of the disagreement between sources")
    debate_log: DebateTranscript
    recommended_experiment: str = Field(..., description="Suggested experiment to resolve the conflict")

class MergedResult(BaseModel):
    title: str
    merged_summary: str
    underlying_mechanism: str
    sources: List[SearchSource]
    source_results: List[SearchResult]
    confidence: float = Field(..., description="Boosted confidence score due to combined evidence (0-100)")
    contradiction_analysis: Optional[ContradictionDetails] = Field(default=None, description="Output of the Step 11.5 3-Agent Debate")

class Step11Response(BaseModel):
    query: StructuralQuery
    results: List[MergedResult]
