
import io
import json
import logging
import os
import statistics
import re
from typing import Dict, Any, Tuple, List

import pandas as pd
import pdfplumber

logger = logging.getLogger(__name__)

# ==============================================================================
# 1. SIMPLE MATRIX EXTRACTION (Mayank)
# ==============================================================================

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
    columns: List[str] = content.get("columns", [])
    rows: List[list] = content.get("rows", [])

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


# ==============================================================================
# 2. PANDAS EXTRACTION & AMBIGUITY DETECTOR (Harsh)
# ==============================================================================

class UniversalExtractor:
    """
    Step 2: Universal Data Extractor.
    Takes a file payload and standardizes it into either a clean DataFrame
    (DATA path) or a normalized string (TEXT path).
    """

    @staticmethod
    def extract_data(file_bytes: bytes, filename: str) -> Tuple[pd.DataFrame, list]:
        """
        Rips numbers out of files (CSV, Excel, JSON, PDF tables) and forces them
        into a clean pandas DataFrame. Applies strict mathematical validation.
        """
        ext = filename.split('.')[-1].lower() if '.' in filename else ''
        df = pd.DataFrame()
        
        try:
            if ext in ['csv']:
                df = pd.read_csv(io.BytesIO(file_bytes))
            elif ext in ['xlsx', 'xls']:
                df = pd.read_excel(io.BytesIO(file_bytes))
            elif ext in ['json']:
                df = pd.read_json(io.BytesIO(file_bytes))
            elif ext in ['pdf']:
                df = UniversalExtractor._extract_tables_from_pdf(file_bytes)
            else:
                # ERR-B10 fix: raise immediately for unsupported extensions rather
                # than blindly trying pd.read_csv() and confusing the error trail.
                raise ValueError(
                    f"Unsupported file extension '.{ext}'. "
                    "Supported data formats: csv, xlsx, xls, json, pdf."
                )
        except Exception as e:
            logger.error(f"Failed to parse {filename} as data: {e}")
            raise ValueError(f"Could not parse file as tabular data. Error: {e}")

        # Standardize and Validate
        return UniversalExtractor.validate_data(df)

    @staticmethod
    def extract_text(file_bytes: bytes, filename: str) -> str:
        """
        Extracts unstructured text from files (PDF, TXT, MD) into a single clean string.
        Applies basic cleaning to normalize whitespace. (Note: chunking is handled in Step 3).
        """
        ext = filename.split('.')[-1].lower() if '.' in filename else ''
        
        def _clean(raw_text: str) -> str:
            # Replace multiple newlines with a single newline
            cleaned = re.sub(r'\n{2,}', '\n', raw_text)
            # Replace multiple spaces with a single space
            cleaned = re.sub(r'[ \t]+', ' ', cleaned)
            return cleaned.strip()

        if ext in ['pdf']:
            text = ""
            try:
                with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                return _clean(text)
            except Exception as e:
                logger.error(f"Failed to extract text from PDF: {e}")
                raise ValueError("Could not extract text from PDF.")
        else:
            try:
                raw_text = file_bytes.decode('utf-8')
                return _clean(raw_text)
            except UnicodeDecodeError:
                raise ValueError("File is not a valid UTF-8 text file.")

    @staticmethod
    def _extract_tables_from_pdf(file_bytes: bytes) -> pd.DataFrame:
        """
        Combines all tables from a PDF into a single DataFrame.
        """
        combined_data = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    combined_data.extend(table)
                    
        if not combined_data:
            raise ValueError("No tables found in PDF.")
            
        # Treat first row as header
        df = pd.DataFrame(combined_data[1:], columns=combined_data[0])
        
        # Coerce columns to numeric where possible
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='ignore')
            
        return df

    @staticmethod
    def validate_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, list]:
        """
        Applies mathematical constraints to the tabular data.
        Returns the cleaned DataFrame and a list of warnings.
        """
        warnings = []
        
        if df.empty:
            raise ValueError("The extracted dataset is completely empty.")

        # 1. Drop rows with any missing values to ensure pristine math for PC Algorithm
        initial_len = len(df)
        df = df.dropna()
        dropped = initial_len - len(df)
        if dropped > 0:
            warnings.append(f"Dropped {dropped} rows containing missing values (NaN) to maintain mathematical integrity.")

        # 2. Keep only numeric columns
        numeric_df = df.select_dtypes(include=['number'])
        if numeric_df.empty:
            raise ValueError("No numeric columns found after processing. Mathematical simulation impossible.")

        # 3. Check for low data warning
        # ERR-B11 fix: threshold is configurable via MIN_DATA_ROWS env var
        min_rows = int(os.getenv("MIN_DATA_ROWS", "30"))
        final_len = len(numeric_df)
        if final_len < min_rows:
            warnings.append(
                f"LOW_DATA_WARNING: Dataset has only {final_len} rows. "
                f"Causal discovery confidence may be low. "
                f"Minimum {min_rows} rows recommended."
            )

        return numeric_df, warnings


# NOTE: AmbiguityDetector was previously duplicated here.
# The canonical implementation now lives in services/layer1/ambiguity.py.
# Import from there if you need AmbiguityDetector in this module:
# from services.layer1.ambiguity import AmbiguityDetector