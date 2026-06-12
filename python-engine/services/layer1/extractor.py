"""
services/layer1/extractor.py — Feature Extractor

Fixes Error 5 (Batch 4): This file was completely empty.
Extracts numeric features and column metadata from tabular data
for downstream use by the PC Algorithm causal discovery engine.
"""
from typing import Dict, List, Tuple
import statistics


def extract_numeric_features(content: dict) -> Tuple[List[str], List[List[float]]]:
    """
    Extracts only the numeric columns from a parsed tabular content dict
    and returns them as a list of column names and a 2D list of float values.

    Non-numeric columns (strings, dates) are silently dropped.

    Parameters
    ----------
    content : dict
        Output of universal_parser._parse_tabular(), with keys:
        "columns", "rows", "row_count".

    Returns
    -------
    Tuple[List[str], List[List[float]]]
        (numeric_columns, data_matrix)
        where data_matrix is rows × columns, indexed as data_matrix[row][col].
    """
    columns: List[str] = content["columns"]
    rows: List[list] = content["rows"]

    if not rows:
        return [], []

    # Identify numeric column indices
    numeric_col_indices = []
    for col_idx, col_name in enumerate(columns):
        # Test the first non-None value in this column
        for row in rows:
            val = row[col_idx] if col_idx < len(row) else None
            if val is not None:
                try:
                    float(val)
                    numeric_col_indices.append(col_idx)
                except (TypeError, ValueError):
                    pass  # Skip non-numeric columns
                break

    if not numeric_col_indices:
        return [], []

    numeric_columns = [columns[i] for i in numeric_col_indices]

    # Build data matrix — replace None/non-numeric with column mean
    raw_columns: List[List[float]] = []
    for col_idx in numeric_col_indices:
        vals = []
        for row in rows:
            val = row[col_idx] if col_idx < len(row) else None
            try:
                vals.append(float(val))
            except (TypeError, ValueError):
                vals.append(None)
        # Fill missing values with column mean
        valid = [v for v in vals if v is not None]
        col_mean = statistics.mean(valid) if valid else 0.0
        raw_columns.append([v if v is not None else col_mean for v in vals])

    # Transpose to row-major order: data_matrix[row][col]
    num_rows = len(rows)
    data_matrix = [
        [raw_columns[col_i][row_i] for col_i in range(len(numeric_col_indices))]
        for row_i in range(num_rows)
    ]

    return numeric_columns, data_matrix


def extract_summary_statistics(content: dict) -> Dict[str, dict]:
    """
    Computes basic summary statistics for each numeric column.

    Returns
    -------
    Dict[str, dict]
        Maps column name → {"mean": float, "std": float, "min": float, "max": float}
    """
    columns, matrix = extract_numeric_features(content)

    if not columns:
        return {}

    stats: Dict[str, dict] = {}
    for col_idx, col_name in enumerate(columns):
        col_vals = [matrix[row_i][col_idx] for row_i in range(len(matrix))]
        if not col_vals:
            continue
        stats[col_name] = {
            "mean": round(statistics.mean(col_vals), 4),
            "std": round(statistics.stdev(col_vals) if len(col_vals) > 1 else 0.0, 4),
            "min": round(min(col_vals), 4),
            "max": round(max(col_vals), 4),
        }

    return stats
