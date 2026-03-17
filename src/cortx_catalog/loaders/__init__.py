"""Data source loaders."""

from cortx_catalog.loaders.base import BaseLoader
from cortx_catalog.loaders.csv_loader import CSVLoader
from cortx_catalog.loaders.parquet import ParquetLoader
from cortx_catalog.loaders.sqlite_loader import SQLiteLoader

__all__ = ["BaseLoader", "CSVLoader", "ParquetLoader", "SQLiteLoader"]


def get_loader(source_type: str, connection_ref: str) -> BaseLoader:
    """Factory function to get appropriate loader.
    
    Args:
        source_type: Type of source (sqlite, csv, parquet, postgresql, mysql)
        connection_ref: Connection string or file path
        
    Returns:
        Appropriate loader instance
    """
    source_type = source_type.lower()
    
    if source_type in ("sqlite", "postgresql", "mysql"):
        return SQLiteLoader(connection_ref, source_type)
    elif source_type == "csv":
        return CSVLoader(connection_ref)
    elif source_type == "parquet":
        return ParquetLoader(connection_ref)
    else:
        raise ValueError(f"Unsupported source type: {source_type}")
