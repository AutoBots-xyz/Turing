"""
FILE: python-engine/services/layer1/ambiguity.py
PURPOSE: Steps 7 & 8 - Ambiguity Detector & Confidence Check. Scores edges, ranks unknown nodes, and decides if Layer 2 Swarm is required.
"""
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class AmbiguityDetector:
    """
    Steps 7 & 8: Gatekeeper for Layer 1. Evaluates graph confidence.
    """

    @staticmethod
    def analyze_graph(graph_data: dict) -> dict:
        """
        Calculates edge confidences and ranks node urgency.
        """
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])

        if not nodes or not edges:
            graph_data["requires_layer2"] = False
            graph_data["overall_graph_confidence"] = 100
            graph_data["urgent_nodes"] = []
            return graph_data

        logger.info(f"Running Ambiguity Detector on {len(edges)} edges...")

        total_confidence = 0
        node_confidences: Dict[str, List[float]] = {n["id"]: [] for n in nodes}

        # Step 7a: Score Every Edge
        for edge in edges:
            # Try to grab weight (PC Algorithm) or confidence (LLM/Fitter)
            raw_val = edge.get("confidence")
            if raw_val is None:
                # If weight exists (e.g. PC Algorithm p-value or coefficient)
                raw_val = edge.get("weight", 0.5)

            # Convert to absolute value bounded between 0 and 1
            abs_val = min(abs(float(raw_val)), 1.0)
            
            # Convert to 0-100 scale
            pct_val = round(abs_val * 100)
            edge["confidence_score"] = pct_val
            total_confidence += pct_val

            # Apply strict visual flags
            if pct_val > 85:
                edge["confidence_flag"] = "✅"
            elif pct_val >= 50:
                edge["confidence_flag"] = "⚠️"
            else:
                edge["confidence_flag"] = "❌"

            # Format the output for the UI (e.g. "temperature -> enzyme 94% ✅")
            source = edge.get("source", "?")
            target = edge.get("target", "?")
            edge["confidence_label"] = f"{source} \u2192 {target} {pct_val}% {edge['confidence_flag']}"

            # Track for node urgency
            if source in node_confidences:
                node_confidences[source].append(pct_val)
            if target in node_confidences:
                node_confidences[target].append(pct_val)

        # Step 7b: Find Unknown Nodes and Rank by Urgency
        urgent_nodes = []
        for node in nodes:
            node_id = node["id"]
            confs = node_confidences.get(node_id, [])
            
            # Urgency metric: Minimum confidence of any edge connected to this node
            # If no edges, it's completely isolated, so confidence is 0%
            min_conf = min(confs) if confs else 0
            
            node["urgency_score"] = min_conf
            
            # Only nodes with low confidence (or completely isolated) are considered "urgent"
            if min_conf < 85:
                urgent_nodes.append({
                    "node_id": node_id,
                    "urgency_score": min_conf,
                    "label": f"Node {node_id} {min_conf}%"
                })

        # Rank by lowest confidence first (most urgent)
        urgent_nodes.sort(key=lambda x: x["urgency_score"])
        
        # Attach to graph
        graph_data["urgent_nodes"] = urgent_nodes
        
        # We also need to pass the overall confidence to Step 8
        overall_conf = round(total_confidence / len(edges)) if edges else 100
        graph_data["overall_graph_confidence"] = overall_conf

        logger.info(f"Ambiguity Detector finished. Ranked {len(urgent_nodes)} nodes by urgency.")
        return graph_data
