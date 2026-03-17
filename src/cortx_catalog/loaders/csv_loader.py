"""CSV loader implementation."""

import os
from typing import Any, Dict, List

import pandas as pd

from cortx_catalog.loaders.base import BaseLoader


class CSVLoader(BaseLoader):
    """Loader for CSV files."""
    
    def __init__(self, connection_ref: str):
        """Initialize CSV loader.
        
        Args:
            connection_ref: Path to CSV file
        """
        super().__init__(connection_ref, "csv")
    
    def load_data(self) -> pd.DataFrame:
        """Load data from CSV file.
        
        Returns:
            DataFrame with CSV data
            
        Raises:
            FileNotFoundError: If CSV doesn't exist
            pd.errors.EmptyDataError: If CSV is empty
        """
        if not os.path.exists(self.connection_ref):
            raise FileNotFoundError(f"CSV file not found: {self.connection_ref}")
        
        # Try different encodings
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
        for encoding in encodings:
            try:
                return pd.read_csv(self.connection_ref, encoding=encoding)
            except UnicodeDecodeError:
                continue
        
        # Fallback with error replacement
        try:
            return pd.read_csv(self.connection_ref, encoding='utf-8', errors='replace')
        except pd.errors.EmptyDataError as e:
            raise ValueError(f"CSV file is empty: {self.connection_ref}") from e
    
    def get_schema(self) -> Dict[str, str]:
        """Get schema by inferring types from data.
        
        Returns:
            Dictionary mapping column names to inferred types
        """
        df = self.load_data()
        schema = {}
        for col in df.columns:
            dtype = str(df[col].dtype)
            # Map pandas dtypes to standard types
            if dtype.startswith("int"):
                schema[col] = "integer"
            elif dtype.startswith("float"):
                schema[col] = "float"
            elif dtype == "bool":
                schema[col] = "boolean"
            elif "datetime" in dtype:
                schema[col] = "datetime"
            else:
                schema[col] = "string"
        return schema
    
    def get_source_id(self) -> str:
        """Generate source ID from filename.
        
        Returns:
            Source identifier in format csv.filename
        """
        filename = os.path.basename(self.connection_ref).replace(".csv", "")
        return f"csv.{filename}"
