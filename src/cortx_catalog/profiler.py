"""Data profiling module with cardinality, PII detection, and date range analysis."""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from cortx_catalog.models import ColumnProfile, ProfileData


# PII detection patterns
PII_PATTERNS = {
    "email": re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"),
    "ssn": re.compile(r"^\d{3}-\d{2}-\d{4}$|^\d{9}$"),
    "phone": re.compile(r"^\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$"),
    "credit_card": re.compile(r"^\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}$"),
    "ip_address": re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"),
}

# Column name hints for PII
PII_COLUMN_HINTS = {
    "email": ["email", "e-mail", "mail"],
    "ssn": ["ssn", "social", "social_security"],
    "phone": ["phone", "mobile", "cell", "telephone", "contact"],
    "credit_card": ["card", "cc", "credit", "payment"],
    "name": ["name", "first_name", "last_name", "fullname", "username"],
    "address": ["address", "street", "city", "zip", "postal"],
}


class Profiler:
    """Profiles data sources to extract statistical metadata."""
    
    def __init__(self, max_sample_values: int = 5):
        """Initialize profiler.
        
        Args:
            max_sample_values: Maximum number of sample values to collect per column
        """
        self.max_sample_values = max_sample_values
    
    def profile(self, df: pd.DataFrame, schema: Dict[str, str]) -> ProfileData:
        """Profile a DataFrame and return metadata.
        
        Args:
            df: DataFrame to profile
            schema: Dictionary of column names to types
            
        Returns:
            ProfileData with complete profiling information
        """
        row_count = len(df)
        columns = []
        
        for col_name in df.columns:
            col_profile = self._profile_column(df[col_name], schema.get(col_name, "unknown"), row_count)
            columns.append(col_profile)
        
        return ProfileData(row_count=row_count, columns=columns)
    
    def _profile_column(
        self, series: pd.Series, dtype: str, row_count: int
    ) -> ColumnProfile:
        """Profile a single column.
        
        Args:
            series: Pandas Series to profile
            dtype: Declared or inferred data type
            row_count: Total row count for percentage calculations
            
        Returns:
            ColumnProfile with all metrics
        """
        col_name = series.name
        
        # Calculate null percentage
        null_count = series.isna().sum()
        null_pct = null_count / row_count if row_count > 0 else 0.0
        
        # Calculate cardinality (unique non-null values)
        cardinality = series.nunique(dropna=True)
        
        # Get sample values (top N most frequent, excluding nulls)
        sample_values = self._get_sample_values(series)
        
        # Detect PII
        is_pii = self._detect_pii(col_name, series, sample_values)
        
        # Detect date range for temporal columns
        date_range = None
        if self._is_temporal_dtype(dtype) or self._looks_like_date_column(col_name):
            date_range = self._get_date_range(series)
        
        return ColumnProfile(
            name=col_name,
            dtype=dtype,
            null_pct=null_pct,
            cardinality=cardinality,
            sample_values=sample_values,
            is_pii=is_pii,
            date_range=date_range,
        )
    
    def _get_sample_values(self, series: pd.Series) -> List[Any]:
        """Get representative sample values from column.
        
        Args:
            series: Pandas Series
            
        Returns:
            List of sample values
        """
        # Get value counts, excluding nulls
        value_counts = series.value_counts(dropna=True)
        
        if len(value_counts) == 0:
            return []
        
        # Take top N most frequent values
        samples = value_counts.head(self.max_sample_values).index.tolist()
        
        # Convert to JSON-serializable types
        result = []
        for val in samples:
            if pd.isna(val):
                continue
            # Handle timestamps
            if isinstance(val, (pd.Timestamp, datetime)):
                result.append(val.isoformat())
            else:
                result.append(val)
        
        return result
    
    def _detect_pii(
        self, col_name: str, series: pd.Series, sample_values: List[Any]
    ) -> bool:
        """Detect if column contains PII.
        
        Args:
            col_name: Column name
            series: Pandas Series
            sample_values: Sample values to check
            
        Returns:
            True if column likely contains PII
        """
        col_lower = col_name.lower()
        
        # Check column name hints
        for pii_type, hints in PII_COLUMN_HINTS.items():
            for hint in hints:
                if hint in col_lower:
                    return True
        
        # Check sample values against patterns
        if len(sample_values) > 0:
            samples_to_check = [str(s) for s in sample_values[:3]]
            for pattern in PII_PATTERNS.values():
                for sample in samples_to_check:
                    if pattern.match(sample):
                        return True
        
        return False
    
    def _is_temporal_dtype(self, dtype: str) -> bool:
        """Check if dtype is temporal.
        
        Args:
            dtype: Data type string
            
        Returns:
            True if temporal type
        """
        temporal_keywords = ["datetime", "timestamp", "date", "time"]
        return any(kw in dtype.lower() for kw in temporal_keywords)
    
    def _looks_like_date_column(self, col_name: str) -> bool:
        """Check if column name suggests it's a date column.
        
        Args:
            col_name: Column name
            
        Returns:
            True if column name suggests date
        """
        date_keywords = ["date", "time", "timestamp", "created", "updated", "at"]
        return any(kw in col_name.lower() for kw in date_keywords)
    
    def _get_date_range(self, series: pd.Series) -> Optional[Tuple[str, str]]:
        """Get min and max dates for temporal columns.
        
        Args:
            series: Pandas Series
            
        Returns:
            Tuple of (min_date, max_date) as ISO strings, or None
        """
        try:
            # Try to convert to datetime
            if series.dtype == "object":
                # Try parsing
                converted = pd.to_datetime(series, errors="coerce")
            else:
                converted = series
            
            # Check if conversion worked
            if converted.isna().all():
                return None
            
            min_date = converted.min()
            max_date = converted.max()
            
            if pd.isna(min_date) or pd.isna(max_date):
                return None
            
            return (min_date.isoformat(), max_date.isoformat())
        except Exception:
            return None
    
    def get_cardinality_ratio(self, column: ColumnProfile, row_count: int) -> float:
        """Calculate cardinality ratio for identifying FKs.
        
        Args:
            column: Column profile
            row_count: Total row count
            
        Returns:
            Cardinality ratio (0.0 - 1.0)
        """
        if row_count == 0:
            return 0.0
        return column.cardinality / row_count
