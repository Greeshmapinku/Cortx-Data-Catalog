"""Tests for profiler module."""

import pandas as pd
import pytest

from cortx_catalog.profiler import Profiler, PII_PATTERNS


class TestProfiler:
    """Test cases for Profiler."""
    
    def test_basic_profiling(self):
        """Test basic column profiling."""
        df = pd.DataFrame({
            "id": [1, 2, 3, 4, 5],
            "name": ["Alice", "Bob", "Charlie", None, "Eve"],
            "score": [95.5, 87.2, 92.1, 78.9, 88.0],
        })
        
        schema = {"id": "integer", "name": "string", "score": "float"}
        
        profiler = Profiler()
        profile = profiler.profile(df, schema)
        
        assert profile.row_count == 5
        assert len(profile.columns) == 3
        
        # Check id column
        id_col = next(c for c in profile.columns if c.name == "id")
        assert id_col.null_pct == 0.0
        assert id_col.cardinality == 5
        assert id_col.dtype == "integer"
        
        # Check name column (has null)
        name_col = next(c for c in profile.columns if c.name == "name")
        assert name_col.null_pct == 0.2  # 1 out of 5
        assert name_col.cardinality == 4  # Alice, Bob, Charlie, Eve
    
    def test_pii_detection_email(self):
        """Test PII detection for email addresses."""
        df = pd.DataFrame({
            "user_id": [1, 2, 3],
            "email": ["alice@test.com", "bob@example.org", "charlie@demo.net"],
        })
        
        schema = {"user_id": "integer", "email": "string"}
        
        profiler = Profiler()
        profile = profiler.profile(df, schema)
        
        email_col = next(c for c in profile.columns if c.name == "email")
        assert email_col.is_pii is True
    
    def test_pii_detection_column_name(self):
        """Test PII detection based on column name hints."""
        df = pd.DataFrame({
            "ssn": ["123-45-6789", "987-65-4321", "555-55-5555"],
            "phone": ["555-1234", "555-5678", "555-9999"],
            "regular_data": ["a", "b", "c"],
        })
        
        schema = {"ssn": "string", "phone": "string", "regular_data": "string"}
        
        profiler = Profiler()
        profile = profiler.profile(df, schema)
        
        ssn_col = next(c for c in profile.columns if c.name == "ssn")
        phone_col = next(c for c in profile.columns if c.name == "phone")
        regular_col = next(c for c in profile.columns if c.name == "regular_data")
        
        assert ssn_col.is_pii is True
        assert phone_col.is_pii is True
        assert regular_col.is_pii is False
    
    def test_date_range_detection(self):
        """Test date range detection for temporal columns."""
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "created_at": pd.to_datetime(["2024-01-01", "2024-06-15", "2024-12-31"]),
            "name": ["A", "B", "C"],
        })
        
        schema = {"id": "integer", "created_at": "datetime", "name": "string"}
        
        profiler = Profiler()
        profile = profiler.profile(df, schema)
        
        date_col = next(c for c in profile.columns if c.name == "created_at")
        assert date_col.date_range is not None
        assert "2024-01-01" in date_col.date_range[0]
        assert "2024-12-31" in date_col.date_range[1]
    
    def test_cardinality_ratio(self):
        """Test cardinality ratio calculation."""
        df = pd.DataFrame({
            "id": range(100),  # High cardinality (100 unique)
            "category": ["A", "B"] * 50,  # Low cardinality (2 unique)
        })
        
        schema = {"id": "integer", "category": "string"}
        
        profiler = Profiler()
        profile = profiler.profile(df, schema)
        
        id_col = next(c for c in profile.columns if c.name == "id")
        cat_col = next(c for c in profile.columns if c.name == "category")
        
        id_ratio = profiler.get_cardinality_ratio(id_col, profile.row_count)
        cat_ratio = profiler.get_cardinality_ratio(cat_col, profile.row_count)
        
        assert id_ratio == 1.0  # All unique
        assert cat_ratio == 0.02  # 2 out of 100
    
    def test_sample_values(self):
        """Test sample value extraction."""
        df = pd.DataFrame({
            "category": ["A"] * 50 + ["B"] * 30 + ["C"] * 20,
        })
        
        schema = {"category": "string"}
        
        profiler = Profiler(max_sample_values=3)
        profile = profiler.profile(df, schema)
        
        cat_col = profile.columns[0]
        assert len(cat_col.sample_values) <= 3
        assert "A" in cat_col.sample_values  # Most frequent


class TestPIIPatterns:
    """Test PII regex patterns."""
    
    def test_email_pattern(self):
        """Test email regex pattern."""
        pattern = PII_PATTERNS["email"]
        
        assert pattern.match("user@example.com")
        assert pattern.match("first.last@company.co.uk")
        assert pattern.match("user+tag@example.org")
        assert not pattern.match("not-an-email")
    
    def test_ssn_pattern(self):
        """Test SSN regex pattern."""
        pattern = PII_PATTERNS["ssn"]
        
        assert pattern.match("123-45-6789")
        assert pattern.match("000000000")
        assert not pattern.match("123-45-678")  # Too short
