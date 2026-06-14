import logging
import networkx as nx
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

class GESGraphBuilder:
    """
    Step 3 (DATA PATH): Converts a pristine DataFrame into a mathematical
    causal graph using the Greedy Equivalence Search (GES) Algorithm.
    GES scales much better to high-dimensional datasets (>50 variables) than PC.
    """

    @staticmethod
    def build_graph(df: pd.DataFrame, alpha: float = 0.05) -> dict:
        """
        Runs the GES algorithm on the DataFrame.
        Returns a networkx compatible JSON dictionary.
        """
        if df.empty:
            raise ValueError("Cannot build graph from empty DataFrame.")

        columns = df.columns.tolist()
        data_matrix = df.to_numpy()

        logger.info(f"Running GES Algorithm on {len(df)} rows, {len(columns)} columns")

        try:
            from causallearn.search.ScoreBased.GES import ges
        except ImportError:
            raise ImportError("causal-learn is not installed. GES cannot run.")

        # Run GES (Greedy Equivalence Search) algorithm
        # We use the default score function (local score, e.g., BIC)
        cg = ges(data_matrix)

        # Convert causal-learn graph to NetworkX
        nx_graph = nx.DiGraph()

        # Add all nodes first
        for i, col in enumerate(columns):
            nx_graph.add_node(col, id=col, label=col, type="variable", confidence=100.0)

        # In GES, cg['G'] is the GeneralGraph object containing the adjacency matrix
        if 'G' in cg:
            adj_matrix = cg['G'].graph
        else:
            adj_matrix = cg.G.graph

        num_nodes = len(columns)
        directed_edge_count = 0
        corr_matrix = np.corrcoef(data_matrix, rowvar=False)

        for i in range(num_nodes):
            for j in range(num_nodes):
                if i == j:
                    continue

                # Check for directed edge i -> j (causal-learn uses -1 for source and 1 for target)
                if adj_matrix[i, j] == -1 and adj_matrix[j, i] == 1:
                    correlation = float(corr_matrix[i, j])
                    if np.isnan(correlation):
                        correlation = 0.0
                        
                    # Confidence is a heuristic for GES since it uses scores instead of p-values
                    # We map correlation to confidence as a baseline indicator
                    confidence = min(100.0, float(abs(correlation) * 100))

                    nx_graph.add_edge(
                        columns[i],
                        columns[j],
                        weight=correlation,
                        confidence=confidence,
                        relation="CAUSES"
                    )
                    directed_edge_count += 1

        # Fallback to correlation network if no directed edges found
        if directed_edge_count == 0:
            logger.warning("GES Algorithm found no directed edges. Falling back to Pearson correlation graph (|r| > 0.3).")
            for i in range(num_nodes):
                for j in range(num_nodes):
                    if i == j:
                        continue
                    r = corr_matrix[i, j]
                    if abs(r) > 0.3 and not np.isnan(r):
                        src, tgt = (i, j) if r > 0 else (j, i)
                        if not nx_graph.has_edge(columns[src], columns[tgt]) and not nx_graph.has_edge(columns[tgt], columns[src]):
                            nx_graph.add_edge(
                                columns[src],
                                columns[tgt],
                                weight=round(float(r), 4),
                                confidence=round(abs(r) * 100.0, 2),
                                relation="CORRELATES"
                            )

        return GESGraphBuilder._serialize_nx(nx_graph)

    @staticmethod
    def _serialize_nx(graph: nx.DiGraph) -> dict:
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
