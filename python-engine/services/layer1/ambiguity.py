"""
services/layer1/ambiguity.py — Step 7: Ambiguity Detector

Scores every node in the causal graph for structural ambiguity and
computes an overall graph-level confidence score that Step 8
(ConfidenceChecker) uses for routing decisions.

Previously this file was an empty stub ('# teammate's file').

Ambiguity signals scored here
------------------------------
1. Low edge confidence    — edges below 60 % confidence reduce node certainty.
2. HIDDEN nodes           — inferred nodes added by NodeClassifier carry
                            inherent uncertainty.
3. Contradicted edges     — edges flagged is_contradicted=True by GraphValidator.
4. Missing fit metrics    — nodes whose GP fit failed or was skipped (DATA path).
5. Structural isolation   — nodes with degree == 1 (single connection) are
                            more ambiguous than well-connected nodes.

Output fields added to graph_data
-----------------------------------
- node["ambiguity_score"]      float  0–100  (higher = more ambiguous)
- node["urgency_score"]        float  0–100  mirrors ambiguity for ConfidenceChecker
- graph_data["urgent_nodes"]   list   sorted by urgency_score desc (nodes < 85 conf)
- graph_data["overall_graph_confidence"]  float  0–100
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Penalty weights (all additive, capped at 100)
_PENALTY_LOW_EDGE_CONF = 20       # any adjacent edge has confidence < 0.60
_PENALTY_HIDDEN_NODE = 30         # node is inferred / hidden
_PENALTY_CONTRADICTED_EDGE = 25   # node has at least one contradicted edge
_PENALTY_BAD_FIT = 15             # GP fit failed or is missing for DATA path
_PENALTY_LOW_DEGREE = 10          # node has only 1 connection total


class AmbiguityDetector:
    """
    Step 7 of the Layer 1 pipeline.
    Adds ambiguity/urgency scores to each node and an overall confidence score
    to the graph dict so that ConfidenceChecker (Step 8) can make routing
    decisions without re-traversing the topology.
    """

    @staticmethod
    def analyze_graph(graph_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Annotates every node in ``graph_data`` with an ``ambiguity_score``
        and ``urgency_score`` (0–100, higher = more uncertain), then writes:

        - graph_data["overall_graph_confidence"] — mean node confidence
        - graph_data["urgent_nodes"]             — list of nodes below 85 % conf

        Parameters
        ----------
        graph_data : dict
            A graph dict with keys ``"nodes"`` and ``"edges"``.

        Returns
        -------
        dict
            The same ``graph_data`` dict, mutated in-place with scores added.
        """
        nodes: List[Dict] = graph_data.get("nodes", [])
        edges: List[Dict] = graph_data.get("edges", [])

        if not nodes:
            logger.info("AmbiguityDetector: no nodes to score — skipping.")
            graph_data["overall_graph_confidence"] = 100.0
            graph_data["urgent_nodes"] = []
            return graph_data

        logger.info(f"AmbiguityDetector: scoring {len(nodes)} nodes …")

        # ── Pre-compute edge lookup maps ──────────────────────────────────────
        # adjacent_edges[node_id] = list of edge dicts touching that node
        adjacent_edges: Dict[str, List[Dict]] = {n["id"]: [] for n in nodes}
        for edge in edges:
            src = edge.get("source")
            tgt = edge.get("target")
            if src in adjacent_edges:
                adjacent_edges[src].append(edge)
            if tgt and tgt in adjacent_edges:
                adjacent_edges[tgt].append(edge)

        # ── Score each node ───────────────────────────────────────────────────
        urgent_nodes: List[Dict] = []

        for node in nodes:
            node_id = node["id"]
            penalty = 0.0

            adj = adjacent_edges.get(node_id, [])

            # 1. Low edge confidence
            if any(e.get("confidence", 1.0) < 0.60 for e in adj):
                penalty += _PENALTY_LOW_EDGE_CONF

            # 2. Hidden / inferred node
            if node.get("is_hidden", False):
                penalty += _PENALTY_HIDDEN_NODE

            # 3. Contradicted edges touching this node
            if any(e.get("is_contradicted", False) for e in adj):
                penalty += _PENALTY_CONTRADICTED_EDGE

            # 4. Bad or missing GP fit (DATA path)
            fit = node.get("fit_metrics", {})
            if fit:
                fit_status = fit.get("status", "")
                if fit_status not in ("FITTED", "SOURCE"):
                    penalty += _PENALTY_BAD_FIT

            # 5. Structural isolation (degree == 1)
            if len(adj) == 1:
                penalty += _PENALTY_LOW_DEGREE

            ambiguity = min(penalty, 100.0)
            confidence = round(100.0 - ambiguity, 2)

            node["ambiguity_score"] = round(ambiguity, 2)
            node["urgency_score"] = round(ambiguity, 2)  # mirrored for ConfidenceChecker
            node["confidence"] = confidence

            logger.debug(
                f"  {node_id}: ambiguity={ambiguity:.1f}  confidence={confidence:.1f}"
            )

            if confidence < 85.0:
                urgent_nodes.append({
                    "node_id": node_id,
                    "urgency_score": ambiguity,
                    "confidence": confidence,
                })

        # ── Graph-level confidence ────────────────────────────────────────────
        all_conf = [n.get("confidence", 100.0) for n in nodes]
        overall = round(sum(all_conf) / len(all_conf), 2)

        graph_data["overall_graph_confidence"] = overall
        graph_data["urgent_nodes"] = sorted(
            urgent_nodes, key=lambda x: x["urgency_score"], reverse=True
        )

        logger.info(
            f"AmbiguityDetector complete: overall_confidence={overall:.1f}%, "
            f"urgent_nodes={len(urgent_nodes)}"
        )
        return graph_data
