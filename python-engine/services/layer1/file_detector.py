import os
from enum import Enum
from pathlib import Path


class InputType(str, Enum):
    CSV = "csv"
    TEXT = "text"
    PDF = "pdf"
    UNKNOWN = "unknown"


# CSV-like extensions → Data Path (PC Algorithm)
CSV_EXTENSIONS = {".csv", ".tsv", ".xlsx", ".xls"}
# Text/document extensions → Text Path (Ontology Builder + LLM)
TEXT_EXTENSIONS = {".txt", ".md", ".pdf", ".docx", ".doc"}


def detect_input_type(filepath: str) -> InputType:
    """
    Layer 1 Gate: Detects the input file type and routes to the correct path.
    - CSV/spreadsheet → Data Path (PC Algorithm for causal discovery)
    - PDF/text/doc   → Text Path (LLM for ontology building)
    """
    ext = Path(filepath).suffix.lower()

    if ext in CSV_EXTENSIONS:
        return InputType.CSV
    elif ext == ".pdf":
        return InputType.PDF
    elif ext in TEXT_EXTENSIONS:
        return InputType.TEXT
    else:
        # Attempt content sniffing for files without clear extensions
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                sample = f.read(512)
            # Heuristic: if the first line has commas and looks like headers, treat as CSV
            first_line = sample.split("\n")[0]
            if first_line.count(",") >= 2 or first_line.count("\t") >= 2:
                return InputType.CSV
            return InputType.TEXT
        except OSError:
            return InputType.UNKNOWN


def validate_file_exists(filepath: str) -> bool:
    """Checks that the file exists and is non-empty before processing."""
    path = Path(filepath)
    return path.exists() and path.is_file() and path.stat().st_size > 0
