"""
FILE: python-engine/services/layer1/validator.py
PURPOSE: Step 4 - Graph Validator. Enforces causal logic on the generated graph (breaks cycles, removes disconnected nodes, agentically flips impossible edges, flags contradictions).
"""
import logging
import json
import networkx as nx
from litellm import completion

logger = logging.getLogger(__name__)

class GraphValidator:
    """
    Step 4: Ultimate gatekeeper for the Causal Graph before Layer 2.
    """

    @staticmethod
    def validate(graph_data: dict, model_name: str = "gpt-4o") -> dict:
        """
        Takes a JSON graph dict {"nodes": [], "edges": []}.
        Runs all 4 validations and returns the cleaned JSON graph and logs.
        """
        # Reconstruct networkx graph for easy traversal
        nx_graph = nx.MultiDiGraph() # Allow parallel edges for contradiction checking
        
        for n in graph_data.get("nodes", []):
            nx_graph.add_node(n["id"], **n)
            
        for e in graph_data.get("edges", []):
            nx_graph.add_edge(e["source"], e["target"], **e)
            
        validation_logs = []

        # 1. Flag Contradictions (must run before cycles since it relies on parallel edges)
        nx_graph, logs = GraphValidator._flag_contradictions(nx_graph)
        validation_logs.extend(logs)
        
        # 2. Break Cycles
        nx_graph, logs = GraphValidator._resolve_cycles(nx_graph)
        validation_logs.extend(logs)
        
        # 3. Agentic Impossible Edge Check
        nx_graph, logs = GraphValidator._fix_impossible_edges(nx_graph, model_name)
        validation_logs.extend(logs)
        
        # 4. Remove Disconnected Nodes
        nx_graph, logs = GraphValidator._remove_disconnected(nx_graph)
        validation_logs.extend(logs)
        
        # Serialize back to JSON
        return {
            "graph": GraphValidator._serialize_nx(nx_graph),
            "logs": validation_logs
        }

    @staticmethod
    def _flag_contradictions(graph: nx.MultiDiGraph) -> tuple[nx.MultiDiGraph, list]:
        logs = []
        # Look for parallel edges with opposing relation types between the same nodes
        # MultiDiGraph allows multiple edges between u and v
        for u in list(graph.nodes()):
            for v in list(graph.neighbors(u)):
                # If there are multiple edges from u -> v
                edge_data_dict = graph.get_edge_data(u, v)
                if edge_data_dict and len(edge_data_dict) > 1:
                    types = [d.get("type", "") for d in edge_data_dict.values()]
                    # Very simple contradiction check: ACTIVATES vs INHIBITS
                    if "ACTIVATES" in types and "INHIBITS" in types:
                        logs.append(f"CONTRADICTION DETECTED: Conflicting edges between {u} and {v}.")
                        # Mark all edges between u and v as contradicted
                        for key in edge_data_dict:
                            graph[u][v][key]["is_contradicted"] = True
                            
        return graph, logs

    @staticmethod
    def _resolve_cycles(graph: nx.MultiDiGraph) -> tuple[nx.MultiDiGraph, list]:
        logs = []
        # We need a simple DiGraph to check for cycles easily
        di_graph = nx.DiGraph(graph)
        
        try:
            cycles = list(nx.simple_cycles(di_graph))
            while cycles:
                cycle = cycles[0]
                logs.append(f"CYCLE DETECTED: {' -> '.join(cycle)} -> {cycle[0]}")
                
                # Find the weakest link in the cycle
                min_weight = float('inf')
                weakest_edge = None
                
                for i in range(len(cycle)):
                    u = cycle[i]
                    v = cycle[(i + 1) % len(cycle)]
                    
                    # Graph is a MultiDiGraph, so get all edges between u and v
                    edge_keys = graph[u][v]
                    for key, data in edge_keys.items():
                        # Default confidence to 1.0 if missing so it isn't automatically picked as weakest
                        conf = data.get("confidence", 1.0)
                        if conf < min_weight:
                            min_weight = conf
                            weakest_edge = (u, v, key)
                            
                if weakest_edge:
                    u, v, key = weakest_edge
                    graph.remove_edge(u, v, key=key)
                    logs.append(f"BROKE CYCLE: Removed edge {u} -> {v} (Confidence: {min_weight})")
                    
                # Re-evaluate
                di_graph = nx.DiGraph(graph)
                cycles = list(nx.simple_cycles(di_graph))
                
        except Exception as e:
            logger.error(f"Cycle detection failed: {e}")
            
        return graph, logs

    @staticmethod
    def _fix_impossible_edges(graph: nx.MultiDiGraph, model_name: str) -> tuple[nx.MultiDiGraph, list]:
        """
        Agentic LLM check for physically/logically impossible edges.
        Batches edges to prevent context window overflow.
        """
        logs = []
        edges_to_check = []
        for u, v, k, d in graph.edges(data=True, keys=True):
            edges_to_check.append({"source": u, "target": v, "key": k})
            
        if not edges_to_check:
            return graph, logs
            
        logger.info(f"Validator Agent checking {len(edges_to_check)} edges for physics violations...")
        
        batch_size = 20
        all_flips = []
        
        for i in range(0, len(edges_to_check), batch_size):
            batch = edges_to_check[i:i + batch_size]
            batch_json = json.dumps([{"source": e["source"], "target": e["target"]} for e in batch], indent=2)
            
            prompt = f"""
            You are a Physics and Logic Validator Agent. Look at these discovered causal edges:
            {batch_json}
            
            Are any of these causal directions physically, chronologically, or logically impossible? 
            For example, an outcome/measurement (Yield, Accuracy) cannot cause a fundamental input (Temperature, Epochs).
            
            If an edge is backwards, list it so we can flip it.
            Respond ONLY with a valid JSON array of objects representing the edges that must be flipped.
            Schema: [{{"source": "Yield", "target": "Temperature", "reason": "Outcome cannot cause input"}}]
            If all are fine, return an empty array [].
            """
            
            try:
                response = completion(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"} if "gpt" in model_name else None
                )
                content = response.choices[0].message.content.strip()
                
                # Basic parsing to handle markdown wrappers
                if content.startswith("```json"):
                    content = content[7:-3]
                elif content.startswith("```"):
                    content = content[3:-3]
                    
                flips = json.loads(content)
                
                # Robust parsing for different LLM JSON structures
                if isinstance(flips, dict):
                    # Find the first list value in the dict
                    list_found = False
                    for v in flips.values():
                        if isinstance(v, list):
                            flips = v
                            list_found = True
                            break
                    if not list_found:
                        flips = []
                        
                if isinstance(flips, list):
                    all_flips.extend(flips)
                                
            except Exception as e:
                logger.error(f"Agentic edge validation failed on batch: {e}")
                logs.append(f"Agentic validation skipped for a batch due to error: {e}")
                
        # Apply the collected flips
        for flip in all_flips:
            if not isinstance(flip, dict):
                continue
            u = flip.get("source")
            v = flip.get("target")
            reason = flip.get("reason", "Violates physics/logic")
            
            if u and v and graph.has_edge(u, v):
                # Find the edge data
                edges_dict = dict(graph[u][v])
                for key, edge_data in edges_dict.items():
                    # Remove old edge
                    graph.remove_edge(u, v, key=key)
                    # Add flipped edge
                    graph.add_edge(v, u, **edge_data)
                    logs.append(f"AGENT FLIPPED EDGE: {u} -> {v} is now {v} -> {u}. Reason: {reason}")
                    
        return graph, logs

    @staticmethod
    def _remove_disconnected(graph: nx.MultiDiGraph) -> tuple[nx.MultiDiGraph, list]:
        logs = []
        isolated = list(nx.isolates(graph))
        for node in isolated:
            graph.remove_node(node)
            logs.append(f"REMOVED DISCONNECTED NODE: {node}")
        return graph, logs

    @staticmethod
    def _serialize_nx(graph: nx.MultiDiGraph) -> dict:
        nodes = [{"id": n, **d} for n, d in graph.nodes(data=True)]
        # MultiDiGraph edges include a key, we'll flatten it for JSON
        edges = [{"source": u, "target": v, **d} for u, v, k, d in graph.edges(data=True, keys=True)]
        return {"nodes": nodes, "edges": edges}


# ─── StructuralFitter (Step 5) ────────────────────────────────────────────────
# Consolidated from services/layer1/fitter.py to match folder-structure.md.
# Fits Gaussian Processes to the Data Path graph to learn mathematical
# relationships and uncertainty bounds.

import uuid
import os
import joblib
import numpy as np
import pandas as pd
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "storage", "models")
os.makedirs(MODELS_DIR, exist_ok=True)

class StructuralFitter:
    """
    Step 5: Fits Gaussian Process equations to causal graphs.
    Only processes DATA path graphs. Skips TEXT path.
    """

    @staticmethod
    def fit_graph(df: pd.DataFrame, graph_data: dict, path_type: str) -> dict:
        """
        Fits a GP for every target node based on its causal parents.
        Saves the models to disk and returns augmented graph data.
        """
        if path_type == "TEXT":
            logger.info("Skipping Structural Equation Fitter for TEXT path.")
            graph_data["is_fitted"] = False
            return graph_data

        if df.empty:
            raise ValueError("Cannot fit graph with empty DataFrame.")

        logger.info(f"Fitting Structural Equations for DATA path graph with {len(df)} rows...")

        session_id = str(uuid.uuid4())
        models = {}

        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])

        parents_map = {n["id"]: [] for n in nodes}
        for e in edges:
            target = e["target"]
            source = e["source"]
            if target in parents_map:
                parents_map[target].append(source)

        global_warnings = []

        for node in nodes:
            node_id = node["id"]
            parents = parents_map.get(node_id, [])

            if not parents:
                node["fit_metrics"] = {"r2": None, "mean_uncertainty": None, "status": "SOURCE"}
                continue

            valid_parents = [p for p in parents if p in df.columns]
            if not valid_parents or node_id not in df.columns:
                node["fit_metrics"] = {"r2": None, "mean_uncertainty": None, "status": "MISSING_DATA"}
                continue

            X = df[valid_parents].values
            y = df[node_id].values

            kernel = 1.0 * RBF(length_scale=1.0) + WhiteKernel(noise_level=1.0)
            gp = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=5, normalize_y=True, random_state=42)

            try:
                gp.fit(X, y)
                models[node_id] = {"model": gp, "parents": valid_parents}

                r2 = gp.score(X, y)
                y_pred, std = gp.predict(X, return_std=True)
                mean_uncertainty = float(np.mean(std))

                example_parent_vals = [f"{p}={X[0][i]:.2f}" for i, p in enumerate(valid_parents)]
                example_str = f"{', '.join(example_parent_vals)} → {node_id}={y_pred[0]:.2f} ± {std[0]:.2f}"

                sparse_warning = False
                y_std = float(np.std(y))
                if y_std > 0 and (mean_uncertainty / y_std) > 0.2:
                    sparse_warning = True
                    warning_msg = f"Sparse data detected for {node_id}. High uncertainty relative to variance in causal relationship."
                    global_warnings.append(warning_msg)
                    node.setdefault("warnings", []).append(warning_msg)

                node["fit_metrics"] = {
                    "r2": float(r2),
                    "mean_uncertainty": mean_uncertainty,
                    "status": "FITTED",
                    "example_equation": example_str,
                    "sparse_data_warning": sparse_warning
                }
                logger.debug(f"Fitted GP for {node_id} (R2: {r2:.3f}, Unc: {mean_uncertainty:.3f})")

            except Exception as e:
                logger.error(f"Failed to fit GP for node {node_id}: {e}")
                node["fit_metrics"] = {"r2": None, "mean_uncertainty": None, "status": f"ERROR: {str(e)}"}

        model_path = os.path.join(MODELS_DIR, f"{session_id}.joblib")
        try:
            joblib.dump(models, model_path)
            logger.info(f"Successfully saved {len(models)} models to {model_path}")
        except Exception as e:
            logger.error(f"Failed to save models to disk: {e}")
            raise RuntimeError(f"Model serialization failed: {e}")

        graph_data["is_fitted"] = True
        graph_data["session_id"] = session_id
        if global_warnings:
            graph_data.setdefault("global_warnings", []).extend(global_warnings)

        return graph_data


# ─── ConfidenceChecker (Step 8) ───────────────────────────────────────────────
# Consolidated from services/layer1/confidence.py to match folder-structure.md.
# Final gatekeeper: assembles the Layer 1 output package and makes routing
# decisions for Layer 2 / Layer 3.

class ConfidenceChecker:
    """
    Step 8: The Final Gatekeeper of Layer 1.
    Decides the final routing and assembles the output package.
    """

    @staticmethod
    def evaluate_graph(graph_data: dict, path_type: str) -> dict:
        """
        Reads the ambiguity scores from Step 7 and enforces the Dual Path routing logic.
        """
        path_type = path_type.upper()
        logger.info(f"Running Step 8 Confidence Check for {path_type} path...")

        graph_data["input_type"] = path_type

        overall_conf = graph_data.get("overall_graph_confidence", 100)
        urgent_nodes = graph_data.get("urgent_nodes", [])
        lowest_node_conf = urgent_nodes[0]["urgency_score"] if urgent_nodes else 100

        is_low_confidence = overall_conf < 85 or lowest_node_conf < 85

        if not is_low_confidence:
            graph_data["routing"] = "SKIP_TO_L3"
            logger.info(f"Graph passed confidence check ({overall_conf}%). Routing: SKIP_TO_L3")
        else:
            if path_type == "DATA":
                graph_data["routing"] = "ROUTE_TO_L2_SIMULATION"
                logger.info(f"DATA graph failed confidence check ({overall_conf}%). Routing: ROUTE_TO_L2_SIMULATION")
            else:
                graph_data["routing"] = "SKIP_TO_L3"
                logger.info(f"TEXT graph failed confidence check ({overall_conf}%), but Text path skips Simulation. Routing: SKIP_TO_L3")

        graph_data["domain_constraints"] = []
        graph_data["sparsity_warnings"] = graph_data.pop("global_warnings", [])

        return graph_data
