"""Tests for loader modules."""

import os
import tempfile

import pandas as pd
import pytest

from cortx_catalog.loaders.csv_loader import CSVLoader
from cortx_catalog.loaders.parquet import ParquetLoader
from cortx_catalog.loaders.sqlite_loader import SQLiteLoader


class TestCSVLoader:
    """Test cases for CSVLoader."""
    
    def test_load_csv(self):
        """Test loading a CSV file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("id,name,score\n")
            f.write("1,Alice,95\n")
            f.write("2,Bob,87\n")
            temp_path = f.name
        
        try:
            loader = CSVLoader(temp_path)
            df = loader.load_data()
            
            assert len(df) == 2
            assert list(df.columns) == ["id", "name", "score"]
            assert df.iloc[0]["name"] == "Alice"
        finally:
            os.unlink(temp_path)
    
    def test_get_schema(self):
        """Test schema inference from CSV."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("id,name,score,active\n")
            f.write("1,Alice,95.5,True\n")
            f.write("2,Bob,87.2,False\n")
            temp_path = f.name
        
        try:
            loader = CSVLoader(temp_path)
            schema = loader.get_schema()
            
            assert schema["id"] in ["integer", "int64"]
            assert schema["name"] == "string"
            assert schema["score"] == "float"
        finally:
            os.unlink(temp_path)
    
    def test_file_not_found(self):
        """Test error handling for missing file."""
        loader = CSVLoader("/nonexistent/path/file.csv")
        
        with pytest.raises(FileNotFoundError):
            loader.load_data()


class TestParquetLoader:
    """Test cases for ParquetLoader."""
    
    def test_load_parquet(self):
        """Test loading a Parquet file."""
        df_original = pd.DataFrame({
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
            "score": [95.5, 87.2, 92.1],
        })
        
        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as f:
            temp_path = f.name
            df_original.to_parquet(temp_path, index=False)
        
        try:
            loader = ParquetLoader(temp_path)
            df_loaded = loader.load_data()
            
            assert len(df_loaded) == 3
            assert list(df_loaded.columns) == ["id", "name", "score"]
        finally:
            os.unlink(temp_path)
    
    def test_get_schema(self):
        """Test schema extraction from Parquet."""
        df_original = pd.DataFrame({
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
        })
        
        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as f:
            temp_path = f.name
            df_original.to_parquet(temp_path, index=False)
        
        try:
            loader = ParquetLoader(temp_path)
            schema = loader.get_schema()
            
            assert "id" in schema
            assert "name" in schema
        finally:
            os.unlink(temp_path)


class TestSQLiteLoader:
    """Test cases for SQLiteLoader."""
    
    def test_load_sqlite(self):
        """Test loading data from SQLite."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            temp_path = f.name
        
        try:
            # Create test database
            import sqlite3
            conn = sqlite3.connect(temp_path)
            conn.execute("CREATE TABLE test (id INTEGER, name TEXT)")
            conn.execute("INSERT INTO test VALUES (1, 'Alice')")
            conn.execute("INSERT INTO test VALUES (2, 'Bob')")
            conn.commit()
            conn.close()
            
            loader = SQLiteLoader(temp_path)
            loader.set_table("test")
            df = loader.load_data()
            
            assert len(df) == 2
            assert list(df.columns) == ["id", "name"]
        finally:
            os.unlink(temp_path)
    
    def test_list_tables(self):
        """Test listing tables in database."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            temp_path = f.name
        
        try:
            import sqlite3
            conn = sqlite3.connect(temp_path)
            conn.execute("CREATE TABLE users (id INTEGER)")
            conn.execute("CREATE TABLE orders (id INTEGER)")
            conn.commit()
            conn.close()
            
            loader = SQLiteLoader(temp_path)
            tables = loader.list_tables()
            
            assert "users" in tables
            assert "orders" in tables
        finally:
            os.unlink(temp_path)
    
    def test_get_schema(self):
        """Test schema extraction from SQLite."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            temp_path = f.name
        
        try:
            import sqlite3
            conn = sqlite3.connect(temp_path)
            conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT, score REAL)")
            conn.commit()
            conn.close()
            
            loader = SQLiteLoader(temp_path)
            loader.set_table("test")
            schema = loader.get_schema()
            
            assert schema["id"] == "INTEGER"
            assert schema["name"] == "TEXT"
            assert schema["score"] == "REAL"
        finally:
            os.unlink(temp_path)
