"""
FILE: python-engine/services/layer1/fitter.py
PURPOSE: Step 5 - Structural Equation Fitter. Fits Gaussian Processes to the Data Path graph to learn mathematical relationships and uncertainty bounds.
"""
import logging
import uuid
import os
import joblib
import numpy as np
import pandas as pd
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Ensure the storage directory exists
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
        
        # Build an adjacency list of parents for each node
        # node_id -> list of parent_ids
        parents_map = {n["id"]: [] for n in nodes}
        for e in edges:
            target = e["target"]
            source = e["source"]
            if target in parents_map:
                parents_map[target].append(source)
                
        global_warnings = []

        # To calculate r2, we can just grab the score.
        # Let's augment the nodes with their fit metrics.
        for node in nodes:
            node_id = node["id"]
            parents = parents_map.get(node_id, [])
            
            # If node has no causes (it's a SOURCE node), we can't fit a causal equation
            if not parents:
                node["fit_metrics"] = {"r2": None, "mean_uncertainty": None, "status": "SOURCE"}
                continue
                
            # Verify parents exist in dataframe
            valid_parents = [p for p in parents if p in df.columns]
            if not valid_parents or node_id not in df.columns:
                node["fit_metrics"] = {"r2": None, "mean_uncertainty": None, "status": "MISSING_DATA"}
                continue
                
            X = df[valid_parents].values
            y = df[node_id].values
            
            # Kernel: RBF for non-linear smooth curves + WhiteKernel for noise estimation
            kernel = 1.0 * RBF(length_scale=1.0) + WhiteKernel(noise_level=1.0)
            
            # GP Regressor with normalized y to handle different scales
            gp = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=5, normalize_y=True, random_state=42)
            
            try:
                gp.fit(X, y)
                models[node_id] = {
                    "model": gp,
                    "parents": valid_parents
                }
                
                # Calculate R^2 on training data
                r2 = gp.score(X, y)
                
                # Calculate mean uncertainty (standard deviation)
                y_pred, std = gp.predict(X, return_std=True)
                mean_uncertainty = float(np.mean(std))
                
                # Format example prediction (taking the first row for illustration)
                example_parent_vals = [f"{p}={X[0][i]:.2f}" for i, p in enumerate(valid_parents)]
                example_str = f"{', '.join(example_parent_vals)} \u2192 {node_id}={y_pred[0]:.2f} \u00B1 {std[0]:.2f}"
                
                sparse_warning = False
                y_std = float(np.std(y))
                if y_std > 0 and (mean_uncertainty / y_std) > 0.2:
                    sparse_warning = True
                    warning_msg = f"Sparse data detected for {node_id}. High uncertainty relative to variance in causal relationship."
                    global_warnings.append(warning_msg)
                    if "warnings" not in node:
                        node["warnings"] = []
                    node["warnings"].append(warning_msg)
                
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
                
        # Save all models to disk using joblib
        model_path = os.path.join(MODELS_DIR, f"{session_id}.joblib")
        try:
            joblib.dump(models, model_path)
            logger.info(f"Successfully saved {len(models)} models to {model_path}")
        except Exception as e:
            logger.error(f"Failed to save models to disk: {e}")
            raise RuntimeError(f"Model serialization failed: {e}")
            
        # Augment graph data
        graph_data["is_fitted"] = True
        graph_data["session_id"] = session_id
        if global_warnings:
            if "global_warnings" not in graph_data:
                graph_data["global_warnings"] = []
            graph_data["global_warnings"].extend(global_warnings)
        
        return graph_data
