from typing import List
from schemas.layer2 import HeatmapPoint

class CliffDetector:
    """
    Detects cliffs (sharp drop-offs) in the parameter space.
    """
    
    @staticmethod
    def detect_cliffs(data_points: List[HeatmapPoint], cliff_sigma: float) -> None:
        """
        Flags points as cliffs if their z_val is significantly lower than the mean.
        Modifies data_points in place.
        """
        if not data_points:
            return

        z_vals = [pt.z_val for pt in data_points]
        mean_z = sum(z_vals) / len(z_vals)
        
        if len(z_vals) > 1:
            variance = sum((z - mean_z) ** 2 for z in z_vals) / (len(z_vals) - 1)
        else:
            variance = 0.0
            
        std_z = variance ** 0.5
        
        if std_z < 1e-9:
            for pt in data_points:
                pt.is_cliff = False
        else:
            cliff_threshold = mean_z - cliff_sigma * std_z
            for pt in data_points:
                pt.is_cliff = pt.z_val < cliff_threshold
