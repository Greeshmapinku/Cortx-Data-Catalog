"""Pydantic models for catalog schema."""

from typing import Any, List, Optional
from pydantic import BaseModel, Field


class ColumnProfile(BaseModel):
    """Profile metadata for a single column.
    
    Attributes:
        name: Column name
        dtype: Data type (inferred or declared)
        null_pct: Percentage of null values (0.0 - 1.0)
        cardinality: Number of unique values
        sample_values: Sample of actual values
        is_pii: Whether column contains PII
        date_range: Optional tuple of (min_date, max_date) for temporal columns
    """
    name: str
    dtype: str
    null_pct: float
    cardinality: int
    sample_values: List[Any]
    is_pii: bool = False
    date_range: Optional[tuple] = None


class ProfileData(BaseModel):
    """Profile data for a data source.
    
    Attributes:
        row_count: Total number of rows
        columns: List of column profiles
    """
    row_count: int
    columns: List[ColumnProfile]


class SemanticData(BaseModel):
    """Semantic annotation for a data source.
    
    Attributes:
        title: Human-readable source title
        description: Business description
        domain_tags: List of domain categories
        sensitivity: Sensitivity level (public/internal/confidential/restricted)
        primary_entity: Main business entity
        query_hints: Actionable query guidance
        likely_join_keys: Identified foreign key candidates
        embedding_model: Model used for embeddings
    """
    title: str
    description: str
    domain_tags: List[str]
    sensitivity: str = Field(..., pattern="^(public|internal|confidential|restricted)$")
    primary_entity: str
    query_hints: List[str]
    likely_join_keys: List[str] = Field(default_factory=list)
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"


class MCPInputSchema(BaseModel):
    """Input schema for MCP tool."""
    type: str = "object"
    properties: dict = Field(default_factory=dict)
    required: List[str] = Field(default_factory=list)


class MCPTool(BaseModel):
    """MCP tool manifest.
    
    Attributes:
        name: Tool name
        description: Agent-legible description with use/avoid guidance
        input_schema: JSON schema for tool inputs
    """
    name: str
    description: str
    input_schema: MCPInputSchema


class CatalogEntry(BaseModel):
    """Complete catalog entry for a data source.
    
    Attributes:
        source_id: Unique identifier for the source
        source_type: Type of source (postgresql, mysql, csv, parquet)
        connection_ref: Connection reference (env var or path)
        profile: Statistical profiling data
        semantic: LLM-annotated semantic metadata
        mcp_tool: MCP tool manifest
    """
    source_id: str
    source_type: str
    connection_ref: str
    profile: ProfileData
    semantic: SemanticData
    mcp_tool: Optional[MCPTool] = None


class Catalog(BaseModel):
    """Complete catalog with multiple entries."""
    entries: List[CatalogEntry] = Field(default_factory=list)
    
    def add_entry(self, entry: CatalogEntry) -> None:
        """Add a catalog entry."""
        self.entries.append(entry)
    
    def to_json(self) -> str:
        """Export catalog to JSON string."""
        return self.model_dump_json(indent=2)
