from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

# --- STEP 1 Models ---

class InputType(str, Enum):
    DATA = "data"
    TEXT = "text"

class PipelineMode(str, Enum):
    SIMULATION = "SIMULATION_MODE"
    LITERATURE = "LITERATURE_MODE"

class ModeDetectorInput(BaseModel):
    graph_data: Dict[str, Any] = Field(description="The causal graph topology from Layer 1")
    unknown_nodes: List[Dict[str, Any]] = Field(default_factory=list, description="List of unknown nodes with rankings")
    input_type: InputType = Field(description="Type of input data processed in Layer 1 (data or text)")

class ModeDetectorOutput(BaseModel):
    mode: PipelineMode = Field(description="The detected pipeline mode based on input type")
    message: str = Field(description="Explanation of the routing decision")

# --- STEP 2 Models ---

class GraphEdge(BaseModel):
    source: str
    target: str
    weight: Optional[float] = None
    confidence: Optional[float] = None

class SearchSpace(BaseModel):
    min: float
    max: float

class VariableIdentifierInput(BaseModel):
    nodes: List[str] = Field(description="List of node names")
    edges: List[GraphEdge] = Field(description="List of directed edges")
    domain_config: Optional[Dict[str, SearchSpace]] = Field(default=None, description="Optional min/max config for source nodes")

class IdentifiedNode(BaseModel):
    name: str
    search_space: Optional[SearchSpace] = None

class VariableIdentifierOutput(BaseModel):
    source_nodes: List[IdentifiedNode] = Field(description="Controllable variables (no incoming edges)")
    sink_nodes: List[str] = Field(description="Outcomes to maximize (no outgoing edges)")
    intermediate_nodes: List[str] = Field(description="Nodes with both incoming and outgoing edges")

# --- STEP 3 Models ---

class GaussianPrediction(BaseModel):
    mean: float
    std_dev: float

class SimulationStepInput(BaseModel):
    nodes: List[str]
    edges: List[GraphEdge]
    source_values: Dict[str, float] = Field(description="Intervention values for source nodes (e.g. temperature=68)")

class SimulationStepOutput(BaseModel):
    predictions: Dict[str, GaussianPrediction] = Field(description="Mean and std_dev for every node in the graph")

# --- STEP 4 Models ---

class AgentProposal(BaseModel):
    agent_name: str
    proposed_values: Dict[str, float]
    justification: str

class SimulationResult(BaseModel):
    agent_name: str
    yield_prediction: GaussianPrediction
    ambiguity_reduction: float
    is_winner: bool = False

class RoundInput(BaseModel):
    round_number: int
    nodes: List[str]
    edges: List[GraphEdge]
    historical_data: List[Dict[str, Any]] = Field(description="List of past successful simulation results to fit GP")
    domain_config: Optional[Dict[str, SearchSpace]] = None
    sink_node: Optional[str] = Field(default=None, description="Name of output node to maximize. Auto-detected if None.")

class RoundHistory(BaseModel):
    round_number: int
    winner_agent: Optional[str] = None  # None if all proposals returned 0 yield
    tested_values: Dict[str, float]
    yield_result: float
    ambiguity_score: float
    all_results: List[SimulationResult]

# --- STEP 5 Models ---

class HeatmapPoint(BaseModel):
    x_val: float
    y_val: float
    z_val: float = Field(description="The predicted yield")
    is_cliff: bool = Field(default=False, description="Flagged true if yield drops suddenly")

class HeatmapInput(BaseModel):
    nodes: List[str]
    edges: List[GraphEdge]
    domain_config: Dict[str, SearchSpace]
    historical_data: List[Dict[str, Any]] = Field(default_factory=list)
    resolution: int = Field(default=10, ge=2, description="Number of points per axis (min 2, default 10 = 10x10 grid)")
    sink_node: Optional[str] = Field(default=None, description="Name of output node to maximize. Auto-detected if None.")
    cliff_sigma: float = Field(default=1.5, description="Cliff threshold: points below (mean - cliff_sigma * std) are flagged")

class HeatmapOutput(BaseModel):
    x_label: str
    y_label: str
    is_1d: bool = Field(default=False, description="True when only one source node exists (axes are the same variable)")
    data: List[HeatmapPoint]

# --- STEP 6 Models ---

class UnexploredZone(BaseModel):
    parameter_name: str
    range_min: float
    range_max: float
    predicted_yield: float
    uncertainty: float
    message: str

class ZoneFinderInput(BaseModel):
    nodes: List[str]
    edges: List[GraphEdge]
    domain_config: Dict[str, SearchSpace]
    historical_data: List[Dict[str, Any]] = Field(default_factory=list, description="Past simulation results; defaults to empty list")
    sink_node: Optional[str] = Field(default=None, description="Name of output node to maximize. Auto-detected if None.")
    gap_threshold: float = Field(default=0.2, description="Minimum percentage of space (0.0 to 1.0) to be considered a gap")

class ZoneFinderOutput(BaseModel):
    unexplored_zones: List[UnexploredZone]
