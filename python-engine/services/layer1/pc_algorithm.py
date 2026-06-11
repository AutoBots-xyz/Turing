"""
FILE: python-engine/services/layer1/pc_algorithm.py
PURPOSE: Implements the PC Algorithm (Peter-Clark) to discover causal graphs purely from mathematical data.
"""
import logging
import pandas as pd
import networkx as nx
import numpy as np

# Note: causal-learn handles the heavy lifting of PC Algorithm
try:
    from causallearn.search.ConstraintBased.PC import pc
    from causallearn.utils.GraphUtils import GraphUtils
except ImportError:
    logging.warning("causal-learn is not installed. PC Algorithm will fail if triggered.")

logger = logging.getLogger(__name__)

class PCGraphBuilder:
    """
    Step 3 (DATA PATH): Converts a pristine DataFrame into a mathematical
    causal graph using the PC Algorithm.
    """

    @staticmethod
    def build_graph(df: pd.DataFrame, alpha: float = 0.05) -> dict:
        """
        Runs the PC algorithm on the DataFrame.
        Returns a networkx compatible JSON dictionary.
        
        Args:
            df: Clean numeric DataFrame (from Step 2).
            alpha: Significance level for conditional independence tests.
        """
        if df.empty:
            raise ValueError("Cannot build graph from empty DataFrame.")

        columns = df.columns.tolist()
        data_matrix = df.to_numpy()

        logger.info(f"Running PC Algorithm on {len(df)} rows, {len(columns)} columns with alpha={alpha}")

        # Run PC Algorithm
        # default fisherz test for continuous data
        cg = pc(data_matrix, alpha, indep_test='fisherz', show_progress=False)

        # Convert causal-learn graph to NetworkX
        nx_graph = nx.DiGraph()

        # Add nodes
        for i, col in enumerate(columns):
            nx_graph.add_node(col, id=col, label=col, type="variable")

        # The causal-learn graph is stored in cg.G
        # cg.G.graph[i, j] contains edge information:
        # -1 (tail), 1 (arrowhead), 0 (circle)
        # So [i, j] = -1 and [j, i] = 1 means i -> j
        
        adj_matrix = cg.G.graph
        num_nodes = len(columns)

        for i in range(num_nodes):
            for j in range(num_nodes):
                if i == j:
                    continue
                
                # Check for directed edge i -> j
                # causal-learn convention: graph[i,j] = -1 and graph[j,i] = 1
                if adj_matrix[i, j] == -1 and adj_matrix[j, i] == 1:
                    # Calculate correlation for the visual edge weight
                    correlation = float(np.corrcoef(data_matrix[:, i], data_matrix[:, j])[0, 1])
                    
                    # Extract actual conditional independence test p-value
                    try:
                        p_value = float(cg.ci_test(i, j, set()))
                        confidence = max(0.0, 1.0 - p_value)
                    except Exception:
                        confidence = abs(correlation) # Fallback if ci_test fails
                    
                    nx_graph.add_edge(
                        columns[i], 
                        columns[j], 
                        weight=correlation,
                        confidence=confidence,
                        type="CAUSES" # Default mathematical relation
                    )

        # Serialize to JSON format expected by UI
        return PCGraphBuilder._serialize_nx(nx_graph)

    @staticmethod
    def _serialize_nx(graph: nx.DiGraph) -> dict:
        """
        Converts a NetworkX DiGraph into a standardized JSON payload.
        """
        nodes = []
        for node, data in graph.nodes(data=True):
            nodes.append({"id": node, **data})

        edges = []
        for source, target, data in graph.edges(data=True):
            edges.append({"source": source, "target": target, **data})

        return {
            "nodes": nodes,
            "edges": edges
        }
