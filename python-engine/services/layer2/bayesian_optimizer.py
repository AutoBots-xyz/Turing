import warnings
import os
from typing import Dict, List, Any, Optional

import numpy as np
from scipy.stats import norm
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern, WhiteKernel

from schemas.layer2 import SearchSpace


class BayesianOptimizer:
    """
    Mock Bayesian Optimizer.
    Selects the next point to simulate based on historical performance.

    In production, this uses Expected Improvement (EI):
        EI = (predicted_mean - best_known) * Phi(Z) + predicted_std * phi(Z)
    where Phi and phi are the standard normal CDF and PDF.

    For the MVP mock, it biases towards the historically best values,
    starting from the center of the domain when no history is available.
    """

    def get_base_point(
        self,
        historical_data: List[Dict[str, Any]],
        domain_config: Dict[str, SearchSpace],
        sink_node: Optional[str] = None,
    ) -> Dict[str, float]:
        """
        Returns the next point to test based on past history.

        Args:
            historical_data: List of past rounds, each with {<sink_node>: float, 'values': Dict}
            domain_config:   Dict of {node_name: SearchSpace(min, max)}
            sink_node:       Name of the outcome variable to maximize (default: None)

        Returns:
            Dict of {node_name: float} — the recommended values for the next simulation.

        Raises:
            ValueError: if any SearchSpace has min >= max.
        """
        if not domain_config:
            warnings.warn(
                "BayesianOptimizer: domain_config is empty. "
                "No base point can be calculated — returning {}.",
                UserWarning,
                stacklevel=2,
            )
            return {}

        # Validate each search space
        for node, space in domain_config.items():
            if space.min >= space.max:
                raise ValueError(
                    f"BayesianOptimizer: SearchSpace for '{node}' is invalid — "
                    f"min ({space.min}) must be strictly less than max ({space.max})."
                )

        base_point = {}

        if not historical_data or len(historical_data) < 2:
            # No/insufficient history — use the center of the domain as the first base point.
            # In a real EI loop, we need at least 2 points to fit the GP surface.
            for node, space in domain_config.items():
                base_point[node] = (space.min + space.max) / 2
            return base_point

        if sink_node is not None and not any(sink_node in entry for entry in historical_data):
            warnings.warn(
                f"BayesianOptimizer: None of the historical entries contain the sink_node key '{sink_node}'. "
                "Optimization will fall back to center.",
                UserWarning,
                stacklevel=2,
            )
            for node, space in domain_config.items():
                base_point[node] = (space.min + space.max) / 2
            return base_point

        # 1. Prepare training data
        nodes = list(domain_config.keys())
        X_train = []
        y_train = []
        for entry in historical_data:
            vals = entry.get("values", {})
            # Only include entries that have all required node values
            if all(n in vals for n in nodes):
                X_train.append([vals[n] for n in nodes])
                y_train.append(entry.get(sink_node, 0.0) if sink_node else 0.0)

        if len(X_train) < 2:
            # Fallback to center if valid data points are less than 2
            for node, space in domain_config.items():
                base_point[node] = (space.min + space.max) / 2
            return base_point

        X = np.array(X_train)
        y = np.array(y_train)

        # 2. Fit the Gaussian Process
        x_std = float(np.std(X)) if X.size else 1.0
        y_std = float(np.std(y)) if y.size else 1.0
        init_length_scale = max(x_std, 1e-3)
        init_noise_level = max(y_std * 0.1, 1e-4)

        kernel = 1.0 * Matern(length_scale=init_length_scale, nu=2.5) + WhiteKernel(noise_level=init_noise_level)
        
        _rs_env = os.getenv("GP_RANDOM_STATE")
        random_state = int(_rs_env) if _rs_env is not None else None

        gp = GaussianProcessRegressor(
            kernel=kernel, 
            n_restarts_optimizer=5, 
            normalize_y=True, 
            random_state=random_state
        )

        try:
            gp.fit(X, y)
        except Exception as e:
            warnings.warn(f"BayesianOptimizer: GP fit failed ({e}). Falling back to best known.")
            best_past = max(historical_data, key=lambda x: x.get(sink_node, 0) if sink_node else 0)
            best_values = best_past.get("values", {})
            for node, space in domain_config.items():
                best_val = best_values.get(node, (space.min + space.max) / 2)
                base_point[node] = max(space.min, min(space.max, best_val))
            return base_point

        # 3. Optimize Expected Improvement (EI) via Random Sampling
        n_samples = 1000
        X_sample = np.zeros((n_samples, len(nodes)))
        for i, node in enumerate(nodes):
            space = domain_config[node]
            X_sample[:, i] = np.random.uniform(space.min, space.max, n_samples)

        mu, std = gp.predict(X_sample, return_std=True)

        y_best = np.max(y)
        with np.errstate(divide='warn'):
            imp = mu - y_best
            Z = np.zeros_like(imp)
            mask = std > 0
            Z[mask] = imp[mask] / std[mask]
            
            ei = np.zeros_like(imp)
            ei[mask] = imp[mask] * norm.cdf(Z[mask]) + std[mask] * norm.pdf(Z[mask])
            ei[~mask] = 0.0

        best_idx = np.argmax(ei)
        best_x = X_sample[best_idx]

        for i, node in enumerate(nodes):
            base_point[node] = float(best_x[i])

        return base_point

