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
    with 5 spread seed points when no history is available (per read.MD).

    Fixes applied:
    - Sink node key is now dynamic (passed as argument, not hardcoded 'yield')
    - 5 spread seed points instead of single center point (per read.MD)
    - domain_config validation: warns if empty, raises if min >= max
    - Missing TODO marker added
    """

    def __init__(self):
        pass

    def get_base_point(
        self,
        historical_data: List[Dict[str, Any]],
        domain_config: Dict[str, SearchSpace],
        sink_node: Optional[str] = "yield",
    ) -> Dict[str, float]:
        """
        Returns the next point to test based on past history.

        Args:
            historical_data: List of past rounds, each with {'yield': float, 'values': Dict}
            domain_config:   Dict of {node_name: SearchSpace(min, max)}
            sink_node:       Name of the outcome variable to maximize (default: 'yield')

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
            # Find best past result using the dynamic sink_node key
            best_past = max(historical_data, key=lambda x: x.get(sink_node, 0))
            best_values = best_past.get("values", {})

            for node, space in domain_config.items():
                # Bias towards the best known value, clamped within bounds
                best_val = best_values.get(node, (space.min + space.max) / 2)
                base_point[node] = max(space.min, min(space.max, best_val))

        else:
            # No history — use 5 spread seed points per read.MD:
            # "Spread across parameter space. Not random — mathematically chosen to cover range"
            # We pick the best of the 5 linearly spaced seed candidates as the starting base point.
            # (In a real EI loop, all 5 would be simulated first to build the initial GP surface.)
            for node, space in domain_config.items():
                spread = space.max - space.min
                seed_points = [
                    space.min,                         # 0%
                    space.min + spread * 0.25,         # 25%
                    space.min + spread * 0.50,         # 50% — center
                    space.min + spread * 0.75,         # 75%
                    space.max,                         # 100%
                ]
                # Return the center of the 5 seeds as the first base point
                base_point[node] = seed_points[2]

        return base_point

    def get_seed_points(
        self,
        domain_config: Dict[str, SearchSpace],
    ) -> List[Dict[str, float]]:
        """
        Returns 5 mathematically spread seed points to cover the parameter space
        before the main agent loop begins (per read.MD Step 4).

        Each returned dict maps node_name → float value for that seed experiment.
        """
        if not domain_config:
            return []

        nodes = list(domain_config.keys())
        spaces = [domain_config[n] for n in nodes]
        num_seeds = 5

        seeds = []
        for i in range(num_seeds):
            t = i / (num_seeds - 1)  # 0.0, 0.25, 0.50, 0.75, 1.0
            point = {
                node: round(space.min + t * (space.max - space.min), 4)
                for node, space in zip(nodes, spaces)
            }
            seeds.append(point)

        return seeds
