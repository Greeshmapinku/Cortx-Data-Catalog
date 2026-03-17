"""Parquet loader implementation."""

import os
from typing import Any, Dict, List

import pandas as pd
import pyarrow.parquet as pq

from cortx_catalog.loaders.base import BaseLoader


class ParquetLoader(BaseLoader):
    """Loader for Parquet files."""
    
    def __init__(self, connection_ref: str):
        """Initialize Parquet loader.
        
        Args:
            connection_ref: Path to Parquet file
        """
        super().__init__(connection_ref, "parquet")
    
    def load_data(self) -> pd.DataFrame:
        """Load data from Parquet file.
        
        Returns:
            DataFrame with Parquet data
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        if not os.path.exists(self.connection_ref):
            raise FileNotFoundError(f"Parquet file not found: {self.connection_ref}")
        
        try:
            return pd.read_parquet(self.connection_ref)
        except Exception as e:
            raise ValueError(f"Failed to read Parquet file: {e}") from e
    
    def get_schema(self) -> Dict[str, str]:
        """Get schema from Parquet metadata.
        
        Returns:
            Dictionary mapping column names to Parquet types
        """
        if not os.path.exists(self.connection_ref):
            raise FileNotFoundError(f"Parquet file not found: {self.connection_ref}")
        
        try:
            schema = pq.read_schema(self.connection_ref)
            return {field.name: str(field.type) for field in schema}
        except Exception as e:
            # Fallback to pandas inference
            df = self.load_data()
            return {col: str(df[col].dtype) for col in df.columns}
    
    def get_source_id(self) -> str:
        """Generate source ID from filename.
        
        Returns:
            Source identifier in format parquet.filename
        """
        filename = os.path.basename(self.connection_ref).replace(".parquet", "").replace(".pq", "")
        return f"parquet.{filename}"
