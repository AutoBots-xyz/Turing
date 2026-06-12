import math
import warnings
from typing import List, Dict, Optional

# TODO: REPLACE WITH REAL GP — When Layer 1 is complete, swap this mock for
# scikit-learn's GaussianProcessRegressor or BoTorch fitted on the actual CSV data.
# The interface (predict_child signature) must remain identical so Layer 2 needs no changes.

class GPEngine:
    """
    Mock Gaussian Process Engine.
    In a real scenario, this would wrap scikit-learn's GaussianProcessRegressor or BoTorch.
    For this architectural demonstration, it simulates mathematical prediction and uncertainty
    compounding using a weighted-sum mean and quadrature uncertainty propagation.
    """
    def __init__(self, base_noise: float = 0.02):
        # Base noise added at each edge traversal.
        # Increase for high-variance domains; decrease for tightly-controlled lab conditions.
        self.base_noise = base_noise

    def predict_child(self, parent_predictions: List[Dict[str, float]], edge_weights: List[Optional[float]]) -> Dict[str, float]:
        """
        Takes a list of parent predictions (each having 'mean' and 'std_dev')
        and the corresponding edge weights.
        Returns the combined prediction for the child node.

        Args:
            parent_predictions: list of {'mean': float, 'std_dev': float}
            edge_weights:        list of floats (one per parent); must be same length

        Raises:
            ValueError: if parent_predictions and edge_weights are different lengths
        """
        if not parent_predictions:
            warnings.warn(
                "GPEngine.predict_child: called with no parents. Returning base noise fallback.",
                UserWarning,
                stacklevel=2
            )
            return {"mean": 0.0, "std_dev": self.base_noise}

        # Guard: mismatched list lengths would cause silent truncation via zip()
        if len(parent_predictions) != len(edge_weights):
            raise ValueError(
                f"GPEngine.predict_child: parent_predictions length ({len(parent_predictions)}) "
                f"does not match edge_weights length ({len(edge_weights)}). "
                "Every parent must have a corresponding edge weight."
            )

        # Sanitize None weights — warn instead of silently using 0.5
        sanitized_weights = []
        for i, w in enumerate(edge_weights):
            if w is None:
                warnings.warn(
                    f"GPEngine: edge_weights[{i}] is None — defaulting to 0.5. "
                    "Provide explicit weights for accurate predictions.",
                    UserWarning,
                    stacklevel=2
                )
                sanitized_weights.append(0.5)
            else:
                sanitized_weights.append(w)

        # Mean prediction: weighted sum of parents
        child_mean = sum(
            p["mean"] * w
            for p, w in zip(parent_predictions, sanitized_weights)
        )

        # Floor at 0.0 — yield (or any physical quantity) cannot be negative
        child_mean = max(0.0, child_mean)

        # Uncertainty compounding: sqrt(sum(parent_var) + base_noise^2)
        # Uses quadrature (root-sum-of-squares) which is standard for independent error sources
        variances = [p["std_dev"] ** 2 for p in parent_predictions]
        child_std = math.sqrt(sum(variances) + self.base_noise ** 2)

        return {"mean": round(child_mean, 4), "std_dev": round(child_std, 4)}
