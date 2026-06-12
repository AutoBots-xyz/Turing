"""
FastAPI Router for Layer 2: Mathematical Simulation & Causal Optimization.
"""
from fastapi import APIRouter
import asyncio
from schemas.layer2 import (
    ModeDetectorInput, ModeDetectorOutput, PipelineMode, InputType,
    VariableIdentifierInput, VariableIdentifierOutput, IdentifiedNode, SearchSpace,
    SimulationStepInput, SimulationStepOutput, GaussianPrediction,
    RoundInput, RoundHistory, SimulationResult,
    HeatmapInput, HeatmapOutput,
    ZoneFinderInput, ZoneFinderOutput
)
from services.layer2.do_calculus import DoCalculusSimulator
from services.layer2.bayesian_optimizer import BayesianOptimizer
from services.layer2.agent_explorer import AgentExplorer
from services.layer2.agent_exploiter import AgentExploiter
from services.layer2.agent_contrarian import AgentContrarian
from services.layer2.heatmap import HeatmapGenerator
from services.layer2.unexplored_zone_finder import UnexploredZoneFinder

router = APIRouter(
    prefix="/layer2",
    tags=["Layer 2 - Simulation & Optimization"]
)

@router.post("/mode-detect", response_model=ModeDetectorOutput)
async def detect_mode(payload: ModeDetectorInput):
    if payload.input_type == InputType.DATA:
        return ModeDetectorOutput(
            mode=PipelineMode.SIMULATION,
            message="Data input detected. Routing to SIMULATION MODE for mathematical simulation."
        )
    else:
        return ModeDetectorOutput(
            mode=PipelineMode.LITERATURE,
            message="Text input detected. Routing to LITERATURE MODE. Skipping simulation."
        )

@router.post("/identify-variables", response_model=VariableIdentifierOutput)
def identify_variables(payload: VariableIdentifierInput):
    in_degrees = {node: 0 for node in payload.nodes}
    out_degrees = {node: 0 for node in payload.nodes}
    
    for edge in payload.edges:
        if edge.source in out_degrees:
            out_degrees[edge.source] += 1
        if edge.target in in_degrees:
            in_degrees[edge.target] += 1
            
    source_nodes = []
    sink_nodes = []
    intermediate_nodes = []
    
    for node in payload.nodes:
        if in_degrees[node] == 0 and out_degrees[node] > 0:
            space = payload.domain_config.get(node) if payload.domain_config else None
            source_nodes.append(IdentifiedNode(name=node, search_space=space))
        elif out_degrees[node] == 0 and in_degrees[node] > 0:
            sink_nodes.append(node)
        elif out_degrees[node] > 0 and in_degrees[node] > 0:
            intermediate_nodes.append(node)
            
    return VariableIdentifierOutput(
        source_nodes=source_nodes,
        sink_nodes=sink_nodes,
        intermediate_nodes=intermediate_nodes
    )

@router.post("/simulate-chain", response_model=SimulationStepOutput)
def simulate_chain(payload: SimulationStepInput):
    simulator = DoCalculusSimulator()
    return simulator.simulate(payload.nodes, payload.edges, payload.source_values)

@router.post("/run-round", response_model=RoundHistory)
async def run_round(payload: RoundInput):
    optimizer = BayesianOptimizer()
    explorer = AgentExplorer()
    exploiter = AgentExploiter()
    contrarian = AgentContrarian()
    simulator = DoCalculusSimulator()
    
    domain_config = payload.domain_config or {}
    
    # Resolve sink node dynamically
    if getattr(payload, "sink_node", None):
        sink_node_name = payload.sink_node
    else:
        in_degrees = {node: 0 for node in payload.nodes}
        out_degrees = {node: 0 for node in payload.nodes}
        for edge in payload.edges:
            if edge.source in out_degrees:
                out_degrees[edge.source] += 1
            if edge.target in in_degrees:
                in_degrees[edge.target] += 1
        sink_candidates = [n for n in payload.nodes if out_degrees.get(n, 0) == 0 and in_degrees.get(n, 0) > 0]
        sink_node_name = sink_candidates[-1] if sink_candidates else payload.nodes[-1]
        
    base_point = optimizer.get_base_point(payload.historical_data, domain_config, sink_node=sink_node_name)
    
    proposals = [
        explorer.propose(base_point, domain_config),
        exploiter.propose(payload.historical_data, domain_config, sink_node=sink_node_name),
        contrarian.propose(base_point, domain_config)
    ]
    
    async def simulate_proposal(prop):
        res = await asyncio.to_thread(simulator.simulate, payload.nodes, payload.edges, prop.proposed_values)
        return prop, res
        
    sim_tasks = [simulate_proposal(p) for p in proposals]
    results = await asyncio.gather(*sim_tasks)
    
    sim_outputs = []
    best_agent = None
    best_score = -float('inf')
    best_yield = 0.0
    best_values = {}
    
    for prop, sim_res in results:
        pred = sim_res.predictions.get(sink_node_name, GaussianPrediction(mean=0.0, std_dev=1.0))
        
        ambiguity_reduction = pred.mean / (pred.std_dev + 0.001)
        
        sim_outputs.append(SimulationResult(
            agent_name=prop.agent_name,
            yield_prediction=pred,
            ambiguity_reduction=round(ambiguity_reduction, 4),
            is_winner=False
        ))
        
        if ambiguity_reduction > best_score:
            best_score = ambiguity_reduction
            best_agent = prop.agent_name
            best_yield = pred.mean
            best_values = prop.proposed_values
            
    for out in sim_outputs:
        if out.agent_name == best_agent:
            out.is_winner = True
            
    return RoundHistory(
        round_number=payload.round_number,
        winner_agent=best_agent,  # None if no proposals produced yield
        tested_values=best_values,
        yield_result=round(best_yield, 4),
        ambiguity_score=round(max(best_score, 0.0), 4),
        all_results=sim_outputs
    )

@router.post("/generate-heatmap", response_model=HeatmapOutput)
def generate_heatmap(payload: HeatmapInput):
    generator = HeatmapGenerator()
    return generator.generate(payload)

@router.post("/find-unexplored-zones", response_model=ZoneFinderOutput)
def find_unexplored_zones(payload: ZoneFinderInput):
    """
    Step 6 — Unexplored Zone Finder
    Checks historical data against the boundaries to flag
    mathematically uncertain but promising gaps.
    """
    finder = UnexploredZoneFinder()
    return finder.find_zones(payload)
