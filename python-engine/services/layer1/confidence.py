"""
FILE: python-engine/services/layer1/confidence.py
PURPOSE: Step 8 - Confidence Check. Assembles the final Layer 1 Output Package and makes the exact routing decision for Layer 2/3 based on path_type.
"""
import logging

logger = logging.getLogger(__name__)

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

        # 1. Attach the explicit input type tag for Layer 2
        graph_data["input_type"] = path_type

        # 2. Extract Step 7 confidence metrics
        overall_conf = graph_data.get("overall_graph_confidence", 100)
        urgent_nodes = graph_data.get("urgent_nodes", [])
        lowest_node_conf = urgent_nodes[0]["urgency_score"] if urgent_nodes else 100

        is_low_confidence = overall_conf < 85 or lowest_node_conf < 85

        # 3. Apply exact routing logic (fixing the Layer 3 jump for TEXT)
        if not is_low_confidence:
            # ABOVE 85%: Skip Layer 2. Go to Layer 3.
            graph_data["routing"] = "SKIP_TO_L3"
            logger.info(f"Graph passed confidence check ({overall_conf}%). Routing: SKIP_TO_L3")
        else:
            # BELOW 85%:
            if path_type == "DATA":
                # DATA PATH below 85%: Agents run simulations
                graph_data["routing"] = "ROUTE_TO_L2_SIMULATION"
                logger.info(f"DATA graph failed confidence check ({overall_conf}%). Routing: ROUTE_TO_L2_SIMULATION")
            else:
                # TEXT PATH below 85%: Skip Layer 2 completely, jump to Literature Search (Layer 3)
                graph_data["routing"] = "SKIP_TO_L3"
                logger.info(f"TEXT graph failed confidence check ({overall_conf}%), but Text path skips Simulation. Routing: SKIP_TO_L3")

        # 4. Assemble the Output Package (Fix for Error 8.2)
        graph_data["domain_constraints"] = [] # Initialize empty constraints list for Layer 2
        
        # Promote fitter global warnings to top-level sparsity_warnings
        graph_data["sparsity_warnings"] = graph_data.pop("global_warnings", [])
        
        return graph_data
