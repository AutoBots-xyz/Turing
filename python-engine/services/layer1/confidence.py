"""
services/layer1/confidence.py

Re-exports ConfidenceChecker from validator.py where the canonical
implementation lives (Step 8 of Layer 1 pipeline).

Previously this file was an empty stub ('# teammate's file').
The real implementation is in validator.py to avoid splitting the tightly
coupled confidence routing logic across multiple files at this stage.
"""
from services.layer1.validator import ConfidenceChecker  # noqa: F401
