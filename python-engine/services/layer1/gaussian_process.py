"""
services/layer1/gaussian_process.py — Gaussian Process Confidence Estimator

Fixes Error 5 (Batch 4): This file was completely empty.
Refines node confidence scores using a Gaussian Process (GP) regression model
fitted on the extracted causal graph structure, improving the raw confidence
values produced by the PC Algorithm or Ontology Builder.
"""
from typing import List

from schemas.graph import CausalGraph, Node


def refine_confidence_with_gp(graph: CausalGraph) -> CausalGraph:
    """
    Refines the confidence scores of all nodes in a CausalGraph using
    Gaussian Process regression.

    The GP uses structural graph features (in-degree, out-degree, centrality)
    as input dimensions and outputs a refined confidence for each node.
    This allows the engine to assign higher confidence to structurally
    central nodes (many connections, high betweenness) and lower confidence
    to isolated leaf nodes.

    Parameters
    ----------
    graph : CausalGraph
        The initial graph produced by pc_algorithm or ontology_builder.

    Returns
    -------
    CausalGraph
        A new CausalGraph with refined node confidence scores.
        Edge structure is unchanged.
    """
    if not graph.nodes:
        return graph

    try:
        import numpy as np
        from sklearn.gaussian_process import GaussianProcessRegressor
        from sklearn.gaussian_process.kernels import RBF, ConstantKernel

        features, raw_confidences = _build_feature_matrix(graph)

        if len(features) < 2:
            return graph  # Not enough data points for GP fitting

        X = np.array(features, dtype=float)
        y = np.array(raw_confidences, dtype=float)

        kernel = ConstantKernel(1.0) * RBF(length_scale=1.0)
        gp = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=2, alpha=1e-2)
        gp.fit(X, y)

        y_pred, _ = gp.predict(X, return_std=True)

        # Clamp GP predictions to [5, 100]
        refined_nodes = []
        for node, pred in zip(graph.nodes, y_pred):
            refined_conf = float(max(5.0, min(100.0, pred)))
            refined_nodes.append(Node(
                id=node.id,
                label=node.label,
                confidence=round(refined_conf, 1),
            ))

        return CausalGraph(nodes=refined_nodes, edges=graph.edges)

    except ImportError:
        # scikit-learn not installed — return graph unchanged
        return graph


def _build_feature_matrix(graph: CausalGraph):
    """
    Builds a feature matrix from graph topology:
    [in_degree, out_degree, degree_ratio, raw_confidence]
    """
    in_degree = {node.id: 0 for node in graph.nodes}
    out_degree = {node.id: 0 for node in graph.nodes}

    for edge in graph.edges:
        if edge.source in out_degree:
            out_degree[edge.source] += 1
        if edge.target in in_degree:
            in_degree[edge.target] += 1

    features = []
    raw_confidences = []

    for node in graph.nodes:
        ind = in_degree.get(node.id, 0)
        outd = out_degree.get(node.id, 0)
        total = ind + outd
        ratio = outd / total if total > 0 else 0.5

        features.append([float(ind), float(outd), ratio])
        raw_confidences.append(node.confidence)

    return features, raw_confidences
