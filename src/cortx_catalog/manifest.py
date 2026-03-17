"""MCP manifest generator."""

import re
from typing import Any, Dict, List

from cortx_catalog.models import CatalogEntry, MCPTool, MCPInputSchema, ProfileData, SemanticData


class ManifestGenerator:
    """Generates MCP tool manifests from catalog entries."""
    
    def generate(self, entry: CatalogEntry) -> MCPTool:
        """Generate MCP tool manifest from catalog entry.
        
        Creates agent-legible descriptions with use/avoid guidance.
        
        Args:
            entry: Catalog entry
            
        Returns:
            MCP tool manifest
        """
        name = self._generate_tool_name(entry)
        description = self._generate_description(entry)
        input_schema = self._generate_input_schema(entry)
        
        return MCPTool(
            name=name,
            description=description,
            input_schema=input_schema,
        )
    
    def _generate_tool_name(self, entry: CatalogEntry) -> str:
        """Generate tool name from source.
        
        Args:
            entry: Catalog entry
            
        Returns:
            Tool name in snake_case
        """
        # Convert source_id to tool name
        source_id = entry.source_id.replace(".", "_")
        
        # Clean up and ensure it starts with query_
        if not source_id.startswith("query_"):
            source_id = f"query_{source_id}"
        
        # Convert to valid Python identifier
        name = re.sub(r"[^a-zA-Z0-9_]", "_", source_id).lower()
        name = re.sub(r"_+", "_", name)  # Collapse multiple underscores
        name = name.strip("_")
        
        return name
    
    def _generate_description(self, entry: CatalogEntry) -> str:
        """Generate agent-legible description with specific use/avoid guidance.
        
        The description is what agents read to decide whether to call the tool.
        Must include specific domain guidance per project requirements.
        
        Args:
            entry: Catalog entry
            
        Returns:
            Description string in format: "Title - Description. Use when... Do not use for..."
        """
        semantic = entry.semantic
        
        # Build specific use cases from domain tags
        use_cases = self._build_specific_use_cases(semantic)
        
        # Build avoid cases (complementary domains)
        avoid_cases = self._build_avoid_cases(semantic)
        
        # Construct description
        parts = [
            semantic.title,
            "-",
            semantic.description,
        ]
        
        # Add specific use guidance
        if use_cases:
            parts.append(f"Use when user asks about {use_cases}.")
        
        # Add specific avoid guidance
        if avoid_cases:
            parts.append(f"Do not use for {avoid_cases}.")
        
        # Add sensitivity warning for restricted data
        if semantic.sensitivity == "restricted":
            parts.append("Requires elevated permissions.")
        
        return " ".join(parts)
    
    def _build_specific_use_cases(self, semantic: SemanticData) -> str:
        """Build specific use cases from domain tags.
        
        Args:
            semantic: Semantic data
            
        Returns:
            Comma-separated use cases with specific business context
        """
        domain_use_cases = {
            "sales": "sales transactions, revenue metrics, or order history",
            "orders": "order details, purchase history, or transaction records",
            "customers": "customer information, contact details, or client profiles",
            "products": "product details, inventory levels, or catalog information",
            "inventory": "stock levels, warehouse data, or product availability",
            "employees": "employee records, staff information, or HR data",
            "hr": "human resources, employee analytics, or organizational data",
            "shipping": "shipping methods, freight costs, or delivery logistics",
            "logistics": "supply chain, transportation, or fulfillment data",
            "finance": "financial analysis, budgeting, or fiscal reporting",
            "transactions": "payment records, financial transactions, or purchase history",
            "categories": "product categories, classification, or taxonomy",
            "b2b": "business customers, corporate accounts, or wholesale data",
            "contacts": "contact information, addresses, or communication details",
            "geography": "regional analysis, location data, or geographic distribution",
            "revenue": "revenue analysis, sales performance, or income tracking",
            "order-items": "line items, order details, or product sales breakdown",
        }
        
        cases = []
        for tag in semantic.domain_tags:
            if tag in domain_use_cases and domain_use_cases[tag] not in cases:
                cases.append(domain_use_cases[tag])
        
        # Add primary entity if not already covered
        if semantic.primary_entity and semantic.primary_entity not in ["record", "data"]:
            entity_case = f"{semantic.primary_entity} information"
            if entity_case not in cases:
                cases.append(entity_case)
        
        # Format with proper grammar
        if len(cases) == 0:
            return "data queries"
        elif len(cases) == 1:
            return cases[0]
        elif len(cases) == 2:
            return f"{cases[0]} or {cases[1]}"
        else:
            return ", ".join(cases[:-1]) + f", or {cases[-1]}"
    
    def _build_avoid_cases(self, semantic: SemanticData) -> str:
        """Build complementary avoid cases based on domain.
        
        Args:
            semantic: Semantic data
            
        Returns:
            Avoid guidance string
        """
        domain_complements = {
            "sales": "unrelated business domains like HR or inventory",
            "customers": "product details, inventory, or non-customer data",
            "products": "customer profiles, sales transactions, or HR data",
            "employees": "customer data, sales metrics, or product information",
            "orders": "employee records, product catalogs without sales context",
            "inventory": "customer information, sales analytics, or HR records",
            "shipping": "product details, customer profiles, or financial analysis",
            "categories": "transaction data, customer information, or revenue metrics",
        }
        
        # Find complementary domain
        for tag in semantic.domain_tags:
            if tag in domain_complements:
                return domain_complements[tag]
        
        # Default avoid case
        return "unrelated business domains"
    
    def _generate_input_schema(self, entry: CatalogEntry) -> MCPInputSchema:
        """Generate input schema for MCP tool.
        
        Args:
            entry: Catalog entry
            
        Returns:
            Input schema
        """
        properties: Dict[str, Any] = {}
        required: List[str] = []
        
        # For database sources, include SQL parameter
        if entry.source_type in ("sqlite", "postgresql", "mysql"):
            properties["sql"] = {
                "type": "string",
                "description": "SQL query to execute",
            }
            required.append("sql")
            
            # Add filter parameters for common columns
            for col in entry.profile.columns:
                if col.name.endswith("_id") or col.name in ["date", "timestamp", "created_at"]:
                    properties[col.name] = {
                        "type": "string" if col.dtype == "string" else col.dtype,
                        "description": f"Filter by {col.name}",
                    }
        
        # For file sources, include filter parameters
        elif entry.source_type in ("csv", "parquet"):
            properties["filters"] = {
                "type": "object",
                "description": "Filter conditions as key-value pairs",
            }
            properties["columns"] = {
                "type": "array",
                "items": {"type": "string"},
                "description": "Columns to return (default: all)",
            }
        
        return MCPInputSchema(
            type="object",
            properties=properties,
            required=required,
        )
