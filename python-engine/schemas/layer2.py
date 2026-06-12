from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from .graph import CausalGraph


class InputType(str, Enum):
    CSV = "csv"
    TEXT = "text"


class AgentAction(BaseModel):
    agent_id: str
    agent_role: str = Field(..., description="'explorer', 'exploiter', or 'contrarian'")
    think: str = Field(..., description="ReAct THINK step — the agent's reasoning")
    decide: str = Field(..., description="ReAct DECIDE step — the chosen intervention")
    act: str = Field(..., description="ReAct ACT step — the executed action and result")
    expected_improvement: float = Field(..., description="Bayesian Expected Improvement score")


class SimulationResult(BaseModel):
    iteration: int
    agent_actions: List[AgentAction]
    best_intervention: str
    predicted_outcome: float = Field(..., description="Predicted value after intervention")
    confidence: float = Field(..., ge=0.0, le=100.0)


class Layer2Request(BaseModel):
    graph: CausalGraph
    target_node_id: str = Field(..., description="The node we are trying to optimise")
    max_iterations: int = Field(default=10, description="Maximum Bayesian optimisation rounds")


class Layer2Response(BaseModel):
    final_graph: CausalGraph
    simulation_results: List[SimulationResult]
    best_intervention: str
    confidence: float
