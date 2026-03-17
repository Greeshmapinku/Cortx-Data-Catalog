"""SQLite loader implementation."""

import os
import sqlite3
from typing import Any, Dict, List

import pandas as pd

from cortx_catalog.loaders.base import BaseLoader


class SQLiteLoader(BaseLoader):
    """Loader for SQLite databases."""
    
    def __init__(self, connection_ref: str, source_type: str = "sqlite"):
        """Initialize SQLite loader.
        
        Args:
            connection_ref: Path to SQLite database file
            source_type: Type of source (sqlite, postgresql, mysql for simulation)
        """
        super().__init__(connection_ref, source_type)
        self.table_name: str = ""
        
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection.
        
        Returns:
            SQLite connection
            
        Raises:
            ConnectionError: If database cannot be opened
        """
        try:
            conn = sqlite3.connect(self.connection_ref)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            raise ConnectionError(f"Failed to connect to {self.connection_ref}: {e}")
    
    def list_tables(self) -> List[str]:
        """List all tables in the database.
        
        Returns:
            List of table names
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            return [row[0] for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def set_table(self, table_name: str) -> "SQLiteLoader":
        """Set the table to load.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Self for chaining
        """
        self.table_name = table_name
        return self
    
    def load_data(self) -> pd.DataFrame:
        """Load data from SQLite table.
        
        Returns:
            DataFrame with table data
            
        Raises:
            ValueError: If table_name not set
            ConnectionError: If query fails
        """
        if not self.table_name:
            tables = self.list_tables()
            if not tables:
                raise ValueError("No tables found in database")
            self.table_name = tables[0]
        
        conn = self._get_connection()
        try:
            query = f"SELECT * FROM {self.table_name}"
            return pd.read_sql_query(query, conn)
        except Exception as e:
            raise ConnectionError(f"Failed to load data from {self.table_name}: {e}")
        finally:
            conn.close()
    
    def get_schema(self) -> Dict[str, str]:
        """Get schema information for the table.
        
        Returns:
            Dictionary mapping column names to SQLite types
        """
        if not self.table_name:
            tables = self.list_tables()
            if tables:
                self.table_name = tables[0]
            else:
                return {}
        
        conn = self._get_connection()
        try:
            cursor = conn.execute(f"PRAGMA table_info({self.table_name})")
            schema = {}
            for row in cursor.fetchall():
                # row: (cid, name, type, notnull, dflt_value, pk)
                schema[row[1]] = row[2]
            return schema
        finally:
            conn.close()
    
    def get_source_id(self) -> str:
        """Generate source ID.
        
        Returns:
            Source identifier in format db_name.table_name
        """
        db_name = os.path.basename(self.connection_ref).replace(".db", "").replace(".sqlite", "")
        table = self.table_name or "unknown"
        return f"{db_name}.{table}"
