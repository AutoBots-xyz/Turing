import asyncio
from typing import List, Dict, Any, Optional

from schemas.layer2 import (
    Layer2Request, Layer2Response, IterationResult, AgentAction,
    RoundInput, GraphEdge, SearchSpace
)
# We need to import the agents and simulator here
from services.layer2.agent_explorer import AgentExplorer
from services.layer2.agent_exploiter import AgentExploiter
from services.layer2.agent_contrarian import AgentContrarian
from services.layer2.do_calculus import DoCalculusSimulator
from services.layer2.bayesian_optimizer import BayesianOptimizer

async def run_bayesian_optimization(request: Layer2Request) -> Layer2Response:
    """
    Orchestration loop that runs max_iterations of the Bayesian Optimization cycle
    using three ReAct agents (Explorer, Exploiter, Contrarian).
    """
    optimizer = BayesianOptimizer()
    explorer = AgentExplorer()
    exploiter = AgentExploiter()
    contrarian = AgentContrarian()
    simulator = DoCalculusSimulator()

    nodes = [node.id for node in request.graph.nodes]
    # We will build domain config manually from the graph (synthesizing it if none exists)
    # The actual implementation of domain_config should probably be derived or passed,
    # but we will default to 0.0 -> 100.0 for source nodes.
    
    edges_list = []
    in_degrees = {n: 0 for n in nodes}
    out_degrees = {n: 0 for n in nodes}

    for e in request.graph.edges:
        edges_list.append(GraphEdge(source=e.source, target=e.target, weight=e.weight, confidence=e.confidence))
        out_degrees[e.source] += 1
        in_degrees[e.target] += 1

    source_nodes = [n for n in nodes if in_degrees[n] == 0]
    domain_config = {
        n: SearchSpace(min=0.0, max=100.0) for n in source_nodes
    }

    historical_data = []
    simulation_results = []
    
    best_intervention_str = "None"
    overall_confidence = 0.0

    for i in range(request.max_iterations):
        base_point = optimizer.get_base_point(historical_data, domain_config, sink_node=request.target_node_id)
        
        proposals = [
            explorer.propose(base_point, domain_config),
            exploiter.propose(historical_data, domain_config, sink_node=request.target_node_id),
            contrarian.propose(base_point, domain_config)
        ]
        
        async def simulate_proposal(prop):
            res = await asyncio.to_thread(simulator.simulate, nodes, edges_list, prop.proposed_values)
            return prop, res
            
        sim_tasks = [simulate_proposal(p) for p in proposals]
        results = await asyncio.gather(*sim_tasks)

        best_agent = None
        best_score = -float('inf')
        best_yield = 0.0
        best_values = {}
        
        agent_actions = []

        for prop, sim_res in results:
            pred = sim_res.predictions.get(request.target_node_id)
            if not pred:
                continue
                
            ambiguity_reduction = pred.mean / (pred.std_dev + 0.001)
            
            agent_actions.append(AgentAction(
                agent_id=prop.agent_name,
                agent_role=prop.agent_name.lower().replace("agent ", ""),
                think=prop.justification,
                decide=str(prop.proposed_values),
                act=f"Yield Prediction: {pred.mean:.4f} ± {pred.std_dev:.4f}",
                expected_improvement=ambiguity_reduction
            ))
            
            if ambiguity_reduction > best_score:
                best_score = ambiguity_reduction
                best_agent = prop.agent_name
                best_yield = pred.mean
                best_values = prop.proposed_values

        if best_agent is not None:
            historical_data.append({
                request.target_node_id: best_yield,
                "values": best_values
            })
            
            best_intervention_str = str(best_values)
            overall_confidence = max(0.0, min(100.0, best_score * 10)) # Heuristic confidence mapping

            simulation_results.append(IterationResult(
                iteration=i+1,
                agent_actions=agent_actions,
                best_intervention=best_intervention_str,
                predicted_outcome=best_yield,
                confidence=overall_confidence
            ))
        else:
            # Graph couldn't be simulated
            break

    return Layer2Response(
        final_graph=request.graph,
        simulation_results=simulation_results,
        best_intervention=best_intervention_str,
        confidence=round(overall_confidence, 2)
    )
