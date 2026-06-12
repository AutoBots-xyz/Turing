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
    citation_count: int = Field(default=0, description="Number of times this paper/patent has been cited")
    replication_count: int = Field(default=0, description="Number of times this study has been independently replicated")
    deployment_status: str = Field(default="unknown", description="Production deployment evidence: 'deployed', 'replicated', 'single_study', 'blog', 'unknown'")

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

class Step12Request(BaseModel):
    merged_results: List[MergedResult]

class ExtractedMechanism(BaseModel):
    source_result: MergedResult
    causal_graph: CausalGraph

class Step12Response(BaseModel):
    extracted_mechanisms: List[ExtractedMechanism]

class MatchType(str, Enum):
    PERFECT = "PERFECT"
    STRONG_PARTIAL = "STRONG_PARTIAL"
    WEAK_PARTIAL = "WEAK_PARTIAL"
    DISCARDED = "DISCARDED"

class IsomorphismMatch(BaseModel):
    mechanism: ExtractedMechanism
    isomorphism_score: float = Field(..., description="Structural similarity score (0.0 to 100.0)")
    match_type: MatchType

class IsomorphismThresholds(BaseModel):
    perfect: float = Field(default=100.0, description="Score threshold for PERFECT match")
    strong_partial: float = Field(default=70.0, description="Score threshold for STRONG_PARTIAL match")
    weak_partial: float = Field(default=30.0, description="Score threshold for WEAK_PARTIAL match")

class Step13Request(BaseModel):
    target_graph: CausalGraph
    candidates: List[ExtractedMechanism]
    thresholds: IsomorphismThresholds = Field(default_factory=IsomorphismThresholds, description="Configurable match classification thresholds")

class Step13Response(BaseModel):
    matches: List[IsomorphismMatch]

class ValidityScores(BaseModel):
    structural_match: float = Field(..., ge=0.0, le=1.0)
    constraint_compatibility: float = Field(..., ge=0.0, le=1.0)
    solution_transferability: float = Field(..., ge=0.0, le=1.0)
    evidence_strength: float = Field(..., ge=0.0, le=1.0)
    final_score: float = Field(..., ge=0.0, le=1.0)

class RankedBridge(BaseModel):
    match: IsomorphismMatch
    scores: ValidityScores

class Step14Request(BaseModel):
    matches: List[IsomorphismMatch]
    user_domain_context: str = Field(default="", description="The domain-blind structural description from Step 10, used as LLM evaluation context")

class Step14Response(BaseModel):
    top_bridges: List[RankedBridge]

