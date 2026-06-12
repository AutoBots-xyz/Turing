
from typing import List
import logging
import pandas as pd
import networkx as nx
import numpy as np

from schemas.graph import CausalGraph, Node, Edge
from services.layer1.extractor import extract_numeric_features

logger = logging.getLogger(__name__)

# Note: causal-learn handles the heavy lifting of PC Algorithm
try:
    from causallearn.search.ConstraintBased.PC import pc
    from causallearn.utils.GraphUtils import GraphUtils
    from causallearn.utils.cit import fisherz
except ImportError:
    logging.warning("causal-learn is not installed. PC Algorithm will fail if triggered or use fallbacks.")

# ==============================================================================
# 1. SIMPLE ONE-SHOT EXTRACTION (Mayank)
# ==============================================================================

def run_pc_algorithm(content: dict) -> CausalGraph:
    """
    Runs the PC Algorithm on the numeric columns of the parsed tabular content
    and converts the output into a CausalGraph schema object.
    """
    columns, matrix = extract_numeric_features(content)

    if not columns or len(matrix) < 10:
        return CausalGraph(nodes=[], edges=[])

    try:
        from causallearn.search.ConstraintBased.PC import pc
        from causallearn.utils.cit import fisherz

        data = np.array(matrix, dtype=float)

        # Run PC algorithm with Fisher Z conditional independence test
        cg = pc(data, alpha=0.05, indep_test=fisherz, show_progress=False)

        nodes = [
            Node(id=col, label=col, confidence=70.0)
            for col in columns
        ]

        edges = []
        if hasattr(cg, "G") and hasattr(cg.G, "graph"):
            adj = cg.G.graph
            n = len(columns)
            for i in range(n):
                for j in range(n):
                    if i == j:
                        continue
                    # adj[i][j] = -1 means i → j (i is parent of j)
                    if adj[i][j] == -1 and adj[j][i] == 1:
                        edges.append(Edge(
                            source=columns[i],
                            target=columns[j],
                            relation="CAUSES",
                            confidence=75.0,
                        ))

        return CausalGraph(nodes=nodes, edges=edges)

    except ImportError:
        # causal-learn not installed — return a heuristic correlation graph
        return _fallback_correlation_graph(columns, matrix)


def _fallback_correlation_graph(columns: List[str], matrix: List[List[float]]) -> CausalGraph:
    """
    Fallback when causal-learn is unavailable: builds a graph based on
    Pearson correlation.
    """
    import statistics

    nodes = [Node(id=col, label=col, confidence=50.0) for col in columns]
    edges = []
    n = len(columns)
    num_rows = len(matrix)

    if num_rows < 2:
        return CausalGraph(nodes=nodes, edges=[])

    for i in range(n):
        for j in range(i + 1, n):
            col_i = [matrix[r][i] for r in range(num_rows)]
            col_j = [matrix[r][j] for r in range(num_rows)]

            mean_i = statistics.mean(col_i)
            mean_j = statistics.mean(col_j)
            std_i = statistics.stdev(col_i) if len(col_i) > 1 else 1.0
            std_j = statistics.stdev(col_j) if len(col_j) > 1 else 1.0

            if std_i == 0 or std_j == 0:
                continue

            cov = sum((col_i[r] - mean_i) * (col_j[r] - mean_j) for r in range(num_rows)) / num_rows
            r = cov / (std_i * std_j)

            if abs(r) > 0.5:
                confidence = round(abs(r) * 100, 1)
                edges.append(Edge(
                    source=columns[i],
                    target=columns[j],
                    relation="CORRELATES_WITH",
                    confidence=confidence,
                ))

    return CausalGraph(nodes=nodes, edges=edges)

# ==============================================================================
# 2. ADVANCED NETWORKX EXTRACTION (Harsh)
# ==============================================================================

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
        """
        if df.empty:
            raise ValueError("Cannot build graph from empty DataFrame.")

        columns = df.columns.tolist()
        data_matrix = df.to_numpy()

        logger.info(f"Running PC Algorithm on {len(df)} rows, {len(columns)} columns with alpha={alpha}")

        # Run PC Algorithm
        # default fisherz test for continuous data
        if 'pc' not in globals():
            raise ImportError("causal-learn is not installed.")
            
        cg = pc(data_matrix, alpha, indep_test='fisherz', show_progress=False)

        # Convert causal-learn graph to NetworkX
        nx_graph = nx.DiGraph()

        # Add nodes
        for i, col in enumerate(columns):
            nx_graph.add_node(col, id=col, label=col, type="variable")

        adj_matrix = cg.G.graph
        num_nodes = len(columns)

        for i in range(num_nodes):
            for j in range(num_nodes):
                if i == j:
                    continue
                
                # Check for directed edge i -> j
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