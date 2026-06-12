import warnings
from typing import Dict, List, Any, Optional
from schemas.layer2 import SearchSpace

# TODO: REPLACE WITH REAL EI — When Layer 1 GP training is complete, replace
# get_base_point() with a proper Expected Improvement (EI) calculation using
# scikit-learn or BoTorch. The interface (signature + return type) must remain identical.


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

        if historical_data:
            if sink_node is not None and not any(sink_node in entry for entry in historical_data):
                warnings.warn(
                    f"BayesianOptimizer: None of the historical entries contain the sink_node key '{sink_node}'. "
                    "Optimization will fall back to arbitrary entry.",
                    UserWarning,
                    stacklevel=2,
                )
            # Find best past result using the dynamic sink_node key
            best_past = max(historical_data, key=lambda x: x.get(sink_node, 0) if sink_node else 0)
            best_values = best_past.get("values", {})

            for node, space in domain_config.items():
                # Bias towards the best known value, clamped within bounds
                best_val = best_values.get(node, (space.min + space.max) / 2)
                base_point[node] = max(space.min, min(space.max, best_val))

        else:
            # No history — use the center of the domain as the first base point.
            # (In a real EI loop, 5 spread seed points would be simulated first to build the initial GP surface.)
            for node, space in domain_config.items():
                base_point[node] = (space.min + space.max) / 2

        return base_point

