"""
services/layer1/fitter.py

Re-exports StructuralFitter from validator.py where the canonical
implementation lives (Step 5 of Layer 1 pipeline).

Previously this file was an empty stub ('# teammate's file').
The real implementation is in validator.py to avoid splitting the tightly
coupled GP fitting logic across multiple files at this stage.
"""
from services.layer1.validator import StructuralFitter  # noqa: F401
