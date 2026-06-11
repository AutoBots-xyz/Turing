"""
FILE: python-engine/services/layer1/extractor.py
PURPOSE: Universal Data Extractor. Takes a file payload and standardizes it into either a clean DataFrame (DATA path) or a normalized string (TEXT path).
"""
import io
import json
import logging
import pandas as pd
import pdfplumber
from typing import Dict, Any, Tuple

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
