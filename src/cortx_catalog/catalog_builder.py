"""Main catalog builder orchestrating the pipeline."""

import json
import os
from typing import List, Optional

from cortx_catalog.annotator import Annotator
from cortx_catalog.embedder import Embedder
from cortx_catalog.loaders import get_loader
from cortx_catalog.manifest import ManifestGenerator
from cortx_catalog.models import Catalog, CatalogEntry
from cortx_catalog.profiler import Profiler


class CatalogBuilder:
    """Builds data catalog by orchestrating loaders, profiler, annotator, and manifest generator."""
    
    def __init__(
        self,
        annotate: bool = True,
        embed: bool = True,
        groq_api_key: Optional[str] = None,
    ):
        """Initialize catalog builder.
        
        Args:
            annotate: Whether to use LLM annotation
            embed: Whether to generate embeddings
            groq_api_key: Groq API key (defaults to env var)
        """
        self.annotate = annotate
        self.embed = embed
        
        self.profiler = Profiler()
        self.manifest_generator = ManifestGenerator()
        self.annotator: Optional[Annotator] = None
        self.embedder: Optional[Embedder] = None
        
        if annotate:
            try:
                self.annotator = Annotator(api_key=groq_api_key)
            except ValueError:
                print("Warning: GROQ_API_KEY not set, skipping annotation")
                self.annotate = False
        
        if embed:
            self.embedder = Embedder()
        
        self.catalog = Catalog()
    
    def add_source(
        self,
        source_type: str,
        connection_ref: str,
        table_name: Optional[str] = None,
    ) -> CatalogEntry:
        """Add a data source to the catalog.
        
        Args:
            source_type: Type of source (sqlite, csv, parquet, etc.)
            connection_ref: Connection string or file path
            table_name: Optional table name for databases
            
        Returns:
            Catalog entry
        """
        # Load data
        loader = get_loader(source_type, connection_ref)
        
        # Set table name if provided
        if table_name and hasattr(loader, "set_table"):
            loader.set_table(table_name)
        
        df = loader.load_data()
        schema = loader.get_schema()
        source_id = loader.get_source_id()
        
        # Profile data
        profile = self.profiler.profile(df, schema)
        
        # Annotate with LLM or use fallback
        if self.annotate and self.annotator:
            semantic = self.annotator.annotate(source_id, source_type, profile)
        else:
            # Use fallback annotation for intelligent defaults
            from cortx_catalog.annotator import Annotator
            semantic = Annotator.fallback_annotation(source_id, profile)
        
        # Generate MCP manifest
        entry = CatalogEntry(
            source_id=source_id,
            source_type=source_type,
            connection_ref=connection_ref,
            profile=profile,
            semantic=semantic,
            mcp_tool=None,  # Will be set after semantic is ready
        )
        
        # Generate manifest (needs semantic to be set first)
        mcp_tool = self.manifest_generator.generate(entry)
        entry.mcp_tool = mcp_tool
        
        # Add to catalog
        self.catalog.add_entry(entry)
        
        # Add to embedder
        if self.embed and self.embedder:
            self.embedder.add_entry(entry)
        
        return entry
    
    def search(self, query: str, top_k: int = 3) -> List[tuple]:
        """Search catalog using semantic similarity.
        
        Args:
            query: Search query
            top_k: Number of results
            
        Returns:
            Search results
        """
        if not self.embedder:
            return []
        return self.embedder.search(query, top_k)
    
    def save(self, output_path: str) -> None:
        """Save catalog to JSON file.
        
        Args:
            output_path: Path to output file
        """
        # Convert to dict for JSON serialization
        data = json.loads(self.catalog.model_dump_json())
        
        # Save entries as a list at root level for cleaner output
        output = {
            "catalog": data["entries"],
            "metadata": {
                "total_sources": len(data["entries"]),
                "embedding_stats": self.embedder.get_stats() if self.embedder else None,
            },
        }
        
        with open(output_path, "w") as f:
            json.dump(output, f, indent=2)
        
        print(f"Catalog saved to {output_path}")
    
    def save_manifest(self, output_path: str) -> None:
        """Save MCP tool manifests to separate file.
        
        Args:
            output_path: Path to output file
        """
        manifests = {}
        for entry in self.catalog.entries:
            if entry.mcp_tool:
                manifests[entry.mcp_tool.name] = {
                    "description": entry.mcp_tool.description,
                    "input_schema": entry.mcp_tool.input_schema.model_dump(),
                    "source_id": entry.source_id,
                }
        
        with open(output_path, "w") as f:
            json.dump(manifests, f, indent=2)
        
        print(f"MCP manifests saved to {output_path}")
