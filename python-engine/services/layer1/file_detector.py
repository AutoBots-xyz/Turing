import io
import re
import pandas as pd
import pdfplumber
import logging

logger = logging.getLogger(__name__)

class UniversalFileDetector:
    """
    Step 1: Universal File Detector.
    Determines if a file should route to the DATA PATH or TEXT PATH.
    """

    @staticmethod
    def analyze_file(file_bytes: bytes, filename: str) -> dict:
        """
        Analyzes the file in-memory and returns the classification.
        """
        ext = filename.split('.')[-1].lower() if '.' in filename else ''
        
        result = {
            "path": "UNKNOWN",
            "confidence": 0.0,
            "sample_preview": "",
            "details": ""
        }

        try:
            if ext in ['csv']:
                result = UniversalFileDetector._analyze_tabular(file_bytes, 'csv')
            elif ext in ['xlsx', 'xls']:
                result = UniversalFileDetector._analyze_tabular(file_bytes, 'excel')
            elif ext in ['json']:
                result = UniversalFileDetector._analyze_tabular(file_bytes, 'json')
            elif ext in ['pdf']:
                result = UniversalFileDetector._analyze_pdf(file_bytes)
            elif ext in ['txt', 'md']:
                result = UniversalFileDetector._analyze_text(file_bytes)
            else:
                # Default fallback, try to read as text
                result = UniversalFileDetector._analyze_text(file_bytes)
        except Exception as e:
            logger.error(f"Error analyzing file {filename}: {e}")
            result["path"] = "TEXT"
            result["details"] = f"Failed to parse as data ({str(e)}), defaulting to text path."

        return result

    @staticmethod
    def _analyze_tabular(file_bytes: bytes, format_type: str) -> dict:
        """Analyzes structured files using pandas to check numeric density."""
        df = None
        if format_type == 'csv':
            # Read only first 100 rows for speed
            df = pd.read_csv(io.BytesIO(file_bytes), nrows=100)
        elif format_type == 'excel':
            df = pd.read_excel(io.BytesIO(file_bytes), nrows=100)
        elif format_type == 'json':
            df = pd.read_json(io.BytesIO(file_bytes))
            df = df.head(100)
        
        if df is None or df.empty:
            return {"path": "TEXT", "confidence": 0.9, "sample_preview": "Empty data", "details": "Structured file was empty."}

        # Calculate ratio of numeric columns
        numeric_cols = df.select_dtypes(include=['number']).columns
        total_cols = len(df.columns)
        
        if total_cols == 0:
             return {"path": "TEXT", "confidence": 0.9, "sample_preview": "No columns", "details": "No columns found."}
             
        numeric_ratio = len(numeric_cols) / total_cols
        
        # If > 50% of columns are numbers, it's DATA
        is_data = numeric_ratio >= 0.5
        
        sample_text = df.head(3).to_string()
        if len(sample_text) > 200:
            sample_text = sample_text[:197] + "..."

        return {
            "path": "DATA" if is_data else "TEXT",
            "confidence": round(numeric_ratio if is_data else (1 - numeric_ratio), 2),
            "sample_preview": sample_text,
            "details": f"Tabular data: {len(numeric_cols)}/{total_cols} numeric columns."
        }

    @staticmethod
    def _analyze_text(file_bytes: bytes) -> dict:
        """Analyzes raw text to check if it's actually numbers separated by spaces/tabs."""
        try:
            text = file_bytes.decode('utf-8')
        except UnicodeDecodeError:
            return {"path": "DATA", "confidence": 0.5, "sample_preview": "Binary data", "details": "Could not decode text, assuming binary data."}
            
        lines = text.splitlines()[:100]
        if not lines:
             return {"path": "TEXT", "confidence": 0.9, "sample_preview": "Empty text", "details": "Text file was empty."}

        # Count tokens
        numeric_tokens = 0
        word_tokens = 0
        
        preview_lines = []
        for line in lines:
            if len(preview_lines) < 3:
                preview_lines.append(line)
            tokens = line.split()
            for t in tokens:
                # Strip common punctuation
                clean_t = t.strip('.,;:"\'()[]{}')
                if clean_t.replace('.', '', 1).replace('-', '', 1).isdigit():
                    numeric_tokens += 1
                elif clean_t.isalpha() or len(clean_t) > 0:
                    word_tokens += 1

        total = numeric_tokens + word_tokens
        if total == 0:
             return {"path": "TEXT", "confidence": 0.9, "sample_preview": "\n".join(preview_lines), "details": "No identifiable tokens."}
             
        numeric_ratio = numeric_tokens / total
        is_data = numeric_ratio >= 0.5 # Consistent with tabular path: requires majority of tokens to be numbers
        
        sample_preview = "\n".join(preview_lines)
        if len(sample_preview) > 200:
            sample_preview = sample_preview[:197] + "..."

        return {
            "path": "DATA" if is_data else "TEXT",
            "confidence": round(numeric_ratio if is_data else (1 - numeric_ratio), 2),
            "sample_preview": sample_preview,
            "details": f"Raw text: {numeric_tokens} numbers, {word_tokens} words."
        }

    @staticmethod
    def _analyze_pdf(file_bytes: bytes) -> dict:
        """Uses pdfplumber to check for data tables vs plain text paragraphs."""
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            if len(pdf.pages) == 0:
                return {"path": "TEXT", "confidence": 0.9, "sample_preview": "Empty PDF", "details": "PDF has no pages."}
                
            # Check first 2 pages
            pages_to_check = min(2, len(pdf.pages))
            
            tables_found = 0
            text_extracted = ""
            combined_data = []
            
            for i in range(pages_to_check):
                page = pdf.pages[i]
                # Look for tables first
                tables = page.extract_tables()
                if tables:
                    tables_found += len(tables)
                    for table in tables:
                        combined_data.extend(table)
                
                # Extract text for fallback/preview
                page_text = page.extract_text()
                if page_text:
                    text_extracted += page_text + "\n"
                    
            sample_text = text_extracted[:200].replace('\n', ' ')
            
            if tables_found > 0 and len(combined_data) > 1:
                # Load table into pandas (limit to 100 rows to match spec)
                df = pd.DataFrame(combined_data[1:101], columns=combined_data[0])
                
                # Coerce columns to numeric
                for col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='ignore')
                    
                numeric_cols = df.select_dtypes(include=['number']).columns
                total_cols = len(df.columns)
                
                if total_cols > 0:
                    numeric_ratio = len(numeric_cols) / total_cols
                    is_data = numeric_ratio >= 0.5
                    
                    if is_data:
                        return {
                            "path": "DATA", 
                            "confidence": round(numeric_ratio, 2), 
                            "sample_preview": "PDF Data Table structure detected...", 
                            "details": f"Found {tables_found} tables. {len(numeric_cols)}/{total_cols} numeric columns."
                        }
                    else:
                        return {
                            "path": "TEXT",
                            "confidence": round(1 - numeric_ratio, 2),
                            "sample_preview": sample_text,
                            "details": f"Found {tables_found} tables, but only {len(numeric_cols)}/{total_cols} numeric columns. Routing as TEXT."
                        }
                        
            return {
                "path": "TEXT",
                "confidence": 0.9,
                "sample_preview": sample_text,
                "details": "No numeric tables detected. Processing as unstructured PDF text."
            }
