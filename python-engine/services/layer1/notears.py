import logging
import networkx as nx
import numpy as np
import pandas as pd
import scipy.linalg as slin
import scipy.optimize as sopt

logger = logging.getLogger(__name__)

def notears_linear(X: np.ndarray, lambda1: float = 0.05, loss_type: str = 'l2', 
                  max_iter: int = 100, h_tol: float = 1e-8, rho_max: float = 1e+16,
                  w_threshold: float = 0.3) -> np.ndarray:
    """
    Solve eq. (1) with NOTEARS using numpy/scipy.
    Linear DAG estimation via continuous optimization.
    """
    def _loss(W):
        M = X @ W
        if loss_type == 'l2':
            R = X - M
            loss = 0.5 / X.shape[0] * (R ** 2).sum()
            G_loss = - 1.0 / X.shape[0] * X.T @ R
        return loss, G_loss

    def _h(W):
        E = slin.expm(W * W)
        h = np.trace(E) - d
        G_h = E.T * W * 2
        return h, G_h

    def _adj(w):
        return (w[:d * d] - w[d * d:]).reshape([d, d])

    def _func(w):
        W = _adj(w)
        loss, G_loss = _loss(W)
        h, G_h = _h(W)
        obj = loss + 0.5 * rho * h * h + alpha * h + lambda1 * w.sum()
        G_smooth = G_loss + (rho * h + alpha) * G_h
        g_obj = np.concatenate((G_smooth + lambda1, - G_smooth + lambda1), axis=None)
        return obj, g_obj

    n, d = X.shape
    w_est, rho, alpha, h = np.zeros(2 * d * d), 1.0, 0.0, np.inf
    bnds = [(0, 0) if i == j else (0, None) for _ in range(2) for i in range(d) for j in range(d)]

    logger.info(f"Running Numpy NOTEARS on {n} rows, {d} cols")
    
    # Scale X
    X_scaled = (X - np.mean(X, axis=0)) / (np.std(X, axis=0) + 1e-8)

    for _ in range(max_iter):
        w_new, h_new = None, None
        while rho < rho_max:
            sol = sopt.minimize(_func, w_est, method='L-BFGS-B', jac=True, bounds=bnds)
            w_new = sol.x
            h_new, _ = _h(_adj(w_new))
            if h_new > 0.25 * h:
                rho *= 10
            else:
                break
        w_est, h = w_new, h_new
        alpha += rho * h
        if h <= h_tol or rho >= rho_max:
            break
            
    W_est = _adj(w_est)
    W_est[np.abs(W_est) < w_threshold] = 0
    return W_est

class NotearsGraphBuilder:
    """
    Step 3 (DATA PATH): Converts a pristine DataFrame into a mathematical
    causal graph using the continuous optimization NOTEARS algorithm.
    """

    @staticmethod
    def build_graph(df: pd.DataFrame, alpha: float = 0.05) -> dict:
        if df.empty:
            raise ValueError("Cannot build graph from empty DataFrame.")

        columns = df.columns.tolist()
        data_matrix = df.to_numpy(dtype=float)
        
        # Add tiny noise to avoid singular matrices with perfectly correlated identical cols
        data_matrix += np.random.normal(0, 1e-4, data_matrix.shape)

        logger.info(f"Running CPU NOTEARS Algorithm on {len(df)} rows, {len(columns)} columns")
        
        # Extract weights using NOTEARS
        W = notears_linear(data_matrix, lambda1=0.05, w_threshold=0.1)

        nx_graph = nx.DiGraph()

        for i, col in enumerate(columns):
            nx_graph.add_node(col, id=col, label=col, type="variable", confidence=100.0)

        num_nodes = len(columns)
        directed_edge_count = 0
        corr_matrix = np.corrcoef(data_matrix, rowvar=False)

        for i in range(num_nodes):
            for j in range(num_nodes):
                w = W[i, j]
                if abs(w) > 0.0:
                    correlation = float(corr_matrix[i, j])
                    if np.isnan(correlation):
                        correlation = 0.0
                        
                    confidence = min(100.0, float(abs(w) * 100))
                    
                    if not nx_graph.has_edge(columns[i], columns[j]):
                        nx_graph.add_edge(
                            columns[i],
                            columns[j],
                            weight=correlation,
                            confidence=confidence,
                            relation="CAUSES"
                        )
                        directed_edge_count += 1

        if directed_edge_count == 0:
            logger.warning("NOTEARS found no directed edges. Falling back to Pearson correlation.")
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

        return NotearsGraphBuilder._serialize_nx(nx_graph)

    @staticmethod
    def _serialize_nx(graph: nx.DiGraph) -> dict:
        nodes = []
        for node, data in graph.nodes(data=True):
            nodes.append({"id": node, **data})

        edges = []
        for source, target, data in graph.edges(data=True):
            edges.append({"source": source, "target": target, **data})

        return {"nodes": nodes, "edges": edges}
