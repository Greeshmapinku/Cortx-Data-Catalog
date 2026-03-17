"""Abstract base class for data source loaders."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple

import pandas as pd


class BaseLoader(ABC):
    """Abstract base class for data source loaders."""
    
    def __init__(self, connection_ref: str, source_type: str = ""):
        """Initialize loader.
        
        Args:
            connection_ref: Connection string or file path
            source_type: Type of data source
        """
        self.connection_ref = connection_ref
        self.source_type = source_type
    
    @abstractmethod
    def load_data(self) -> pd.DataFrame:
        """Load data from source.
        
        Returns:
            DataFrame with source data
            
        Raises:
            ConnectionError: If unable to connect to data source
            FileNotFoundError: If file doesn't exist
        """
        raise NotImplementedError
    
    @abstractmethod
    def get_schema(self) -> Dict[str, str]:
        """Get schema information.
        
        Returns:
            Dictionary mapping column names to data types
        """
        raise NotImplementedError
    
    def get_source_id(self) -> str:
        """Generate source ID from connection ref.
        
        Returns:
            Source identifier string
        """
        # Extract table name or filename from connection ref
        if "." in self.connection_ref:
            parts = self.connection_ref.rsplit("/", 1)
            if len(parts) > 1:
                return f"{self.source_type}.{parts[-1].replace('.', '_')}"
        return f"{self.source_type}.{self.connection_ref.replace('/', '_').replace('.', '_')}"
