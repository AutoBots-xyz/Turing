"""
services/layer1/classifier.py — Input Classifier

Fixes Error 5 (Batch 4): This file was completely empty.
Classifies the parsed input into one of two pipeline paths:
  - Data Path:  tabular CSV data → PC Algorithm causal discovery
  - Text Path:  document/text → LLM ontology building
"""
from services.layer1.file_detector import InputType


def classify_path(input_type: InputType) -> str:
    """
    Determines which Layer 1 processing path to use based on file type.

    Returns
    -------
    str
        "DATA_PATH" — for CSV/XLSX files (uses PC Algorithm)
        "TEXT_PATH" — for PDF/TXT/DOCX files (uses LLM ontology builder)

    Raises
    ------
    ValueError
        If the input_type is UNKNOWN and cannot be classified.
    """
    if input_type == InputType.CSV:
        return "DATA_PATH"
    elif input_type in (InputType.PDF, InputType.TEXT):
        return "TEXT_PATH"
    else:
        raise ValueError(
            f"Cannot classify InputType '{input_type.value}'. "
            "Ensure the file is a supported format (CSV, PDF, TXT, DOCX, XLSX)."
        )


def classify_parsed_content(content: dict) -> str:
    """
    Alternative classifier that works from parsed content metadata
    when the original file extension is unavailable.

    Parameters
    ----------
    content : dict
        The output of universal_parser.parse_file() — must contain a "type" key.

    Returns
    -------
    str
        "DATA_PATH" or "TEXT_PATH"
    """
    content_type = content.get("type", "")
    if content_type == "tabular":
        return "DATA_PATH"
    elif content_type == "text":
        return "TEXT_PATH"
    else:
        raise ValueError(f"Unknown content type: '{content_type}'")
