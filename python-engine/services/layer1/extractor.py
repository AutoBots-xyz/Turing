"""
FILE: python-engine/services/layer1/extractor.py
PURPOSE: Universal Data Extractor. Takes a file payload and standardizes it into either a clean DataFrame (DATA path) or a normalized string (TEXT path).
"""
import io
import json
import logging
import pandas as pd
import pdfplumber
from typing import Dict, Any, Tuple, List

logger = logging.getLogger(__name__)

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
                # Fallback, try reading as CSV
                df = pd.read_csv(io.BytesIO(file_bytes))
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
        import re
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
        final_len = len(numeric_df)
        if final_len < 30:
            warnings.append(f"LOW_DATA_WARNING: Dataset has only {final_len} rows. Causal discovery confidence may be low. Minimum 30 rows recommended.")

        return numeric_df, warnings


# ─── AmbiguityDetector (Steps 7 & 8) ─────────────────────────────────────────
# Consolidated from services/layer1/ambiguity.py to match folder-structure.md.
# Gatekeeper for Layer 1: evaluates graph confidence and decides if Layer 2
# agent swarm is required.

class AmbiguityDetector:
    """
    Steps 7 & 8: Gatekeeper for Layer 1. Evaluates graph confidence.
    """

    @staticmethod
    def analyze_graph(graph_data: dict) -> dict:
        """
        Calculates edge confidences and ranks node urgency.
        """
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])

        if not nodes or not edges:
            graph_data["requires_layer2"] = False
            graph_data["overall_graph_confidence"] = 100
            graph_data["urgent_nodes"] = []
            return graph_data

        logger.info(f"Running Ambiguity Detector on {len(edges)} edges...")

        total_confidence = 0
        node_confidences: Dict[str, List[float]] = {n["id"]: [] for n in nodes}

        # Step 7a: Score every edge
        for edge in edges:
            raw_val = edge.get("confidence")
            if raw_val is None:
                raw_val = edge.get("weight", 0.5)

            abs_val = min(abs(float(raw_val)), 1.0)
            pct_val = round(abs_val * 100)
            edge["confidence_score"] = pct_val
            total_confidence += pct_val

            if pct_val > 85:
                edge["confidence_flag"] = "✅"
            elif pct_val >= 50:
                edge["confidence_flag"] = "⚠️"
            else:
                edge["confidence_flag"] = "❌"

            source = edge.get("source", "?")
            target = edge.get("target", "?")
            edge["confidence_label"] = f"{source} → {target} {pct_val}% {edge['confidence_flag']}"

            if source in node_confidences:
                node_confidences[source].append(pct_val)
            if target in node_confidences:
                node_confidences[target].append(pct_val)

        # Step 7b: Find unknown nodes and rank by urgency
        urgent_nodes = []
        for node in nodes:
            node_id = node["id"]
            confs = node_confidences.get(node_id, [])
            min_conf = min(confs) if confs else 0
            node["urgency_score"] = min_conf

            if min_conf < 85:
                urgent_nodes.append({
                    "node_id": node_id,
                    "urgency_score": min_conf,
                    "label": f"Node {node_id} {min_conf}%"
                })

        urgent_nodes.sort(key=lambda x: x["urgency_score"])
        graph_data["urgent_nodes"] = urgent_nodes

        overall_conf = round(total_confidence / len(edges)) if edges else 100
        graph_data["overall_graph_confidence"] = overall_conf

        logger.info(f"Ambiguity Detector finished. Ranked {len(urgent_nodes)} nodes by urgency.")
        return graph_data
