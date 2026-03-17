"""LLM annotation module using Groq API."""

import json
import os
from typing import Any, Dict, List, Optional

from groq import Groq

from cortx_catalog.models import ProfileData, SemanticData


# Few-shot examples for the LLM - MUST BE SPECIFIC AND BUSINESS-ORIENTED
FEW_SHOT_EXAMPLES = """
Example 1 - Customer Data:
Input: Table "customers" with columns: customerID (string), companyName (string), contactName (string), city (string), country (string)
Output: {
    "title": "Customer Directory",
    "description": "Core customer records containing company information, contact details, and geographic locations. Represents B2B customer relationships across global markets. Use for customer segmentation, regional analysis, and contact lookup.",
    "domain_tags": ["customers", "sales", "b2b", "contacts", "geography"],
    "sensitivity": "confidential",
    "primary_entity": "customer",
    "query_hints": ["filter by country for regional sales analysis", "use companyName for exact customer lookup", "group by city for geographic distribution", "contactName contains PII - handle securely"],
    "likely_join_keys": ["customerID"]
}

Example 2 - Sales Orders:
Input: Table "orders" with columns: orderID (integer), customerID (string), employeeID (integer), orderDate (date), freight (float)
Output: {
    "title": "Sales Orders",
    "description": "Sales transaction records capturing customer purchases with order dates, responsible employees, and shipping costs. Central to revenue analysis and sales performance tracking.",
    "domain_tags": ["sales", "orders", "revenue", "transactions"],
    "sensitivity": "internal",
    "primary_entity": "order",
    "query_hints": ["filter by orderDate for time-based analysis", "join to customers on customerID for customer insights", "join to employees on employeeID for sales rep performance", "sum freight for shipping cost analysis"],
    "likely_join_keys": ["customerID", "employeeID", "orderID"]
}

Example 3 - Products:
Input: Table "products" with columns: productID (integer), productName (string), unitPrice (float), categoryID (integer), discontinued (integer)
Output: {
    "title": "Product Catalog",
    "description": "Master product inventory with pricing, categorization, and availability status. Use for product lookups, pricing analysis, and inventory management.",
    "domain_tags": ["products", "inventory", "pricing", "catalog"],
    "sensitivity": "internal",
    "primary_entity": "product",
    "query_hints": ["filter by discontinued=0 for active products only", "join to categories on categoryID", "analyze unitPrice for pricing trends", "group by categoryID for category performance"],
    "likely_join_keys": ["productID", "categoryID"]
}
"""

SYSTEM_PROMPT = f"""You are a data catalog expert. Analyze database tables and provide rich semantic metadata for AI agent consumption.

CRITICAL: Your descriptions must be SPECIFIC and BUSINESS-ORIENTED. Generic descriptions like "Data source with X records" will fail.

{FEW_SHOT_EXAMPLES}

Respond ONLY with a JSON object containing these exact keys:
- "title": A concise, business-oriented title (3-5 words). Example: "Sales Transactions" not "Orders Table"
- "description": Rich business description (2-3 sentences). MUST include:
  * What business process this data represents
  * Key business concepts/entities included
  * Example: "Sales order records capturing customer purchases. Contains line-item details with pricing, quantities, and product information. Use for revenue analysis, sales reporting, and customer purchase history."
- "domain_tags": Array of 3-5 specific domain categories. Examples: ["sales", "revenue", "customers", "transactions"] not ["data"]
- "sensitivity": One of "public", "internal", "confidential", or "restricted"
- "primary_entity": The main business entity (single word). Examples: "order", "customer", "product", "employee"
- "query_hints": Array of 3-4 actionable, specific hints:
  * What filters to use (e.g., "filter by orderDate for time-based analysis")
  * What joins are common (e.g., "join to customers on customerID")
  * What aggregations make sense (e.g., "sum unitPrice * quantity for revenue")
  * Performance tips (e.g., "always filter by date range for large tables")
- "likely_join_keys": Array of column names that link to other tables (columns ending in _id, or named id/key)

REQUIREMENTS:
1. "description" MUST be specific to the table content - mention actual column purposes
2. "domain_tags" MUST be business domains, not generic "data"
3. "query_hints" MUST reference actual column names from the input
4. If you see columns like "customer_id", "order_date", "amount" - describe the business process (sales, orders, transactions)
5. If columns contain PII (email, name, phone), set sensitivity to "confidential"
6. If columns contain financial data (amount, price, cost), set sensitivity to "restricted"

BAD example: "Data source csv.customers with 91 records."
GOOD example: "Customer directory with contact information and demographics. Use when user asks about customer profiles, contact details, or geographic distribution."
"""


class Annotator:
    """Annotates data sources using LLM."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "llama-3.3-70b-versatile"):
        """Initialize annotator.
        
        Args:
            api_key: Groq API key (defaults to GROQ_API_KEY env var)
            model: Groq model to use
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("Groq API key required. Set GROQ_API_KEY env var.")
        
        self.client = Groq(api_key=self.api_key)
        self.model = model
    
    def annotate(
        self, source_id: str, source_type: str, profile: ProfileData
    ) -> SemanticData:
        """Annotate a data source using LLM.
        
        Args:
            source_id: Source identifier
            source_type: Type of source
            profile: Profile data from profiler
            
        Returns:
            SemanticData with LLM-generated annotations
        """
        # Build context for the LLM
        context = self._build_context(source_id, source_type, profile)
        
        # Call LLM
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": context},
                ],
                temperature=0.3,
                max_tokens=800,
                response_format={"type": "json_object"},
            )
            
            # Parse response
            content = response.choices[0].message.content
            result = json.loads(content)
            
            # Create SemanticData
            return SemanticData(
                title=result.get("title", source_id),
                description=result.get("description", ""),
                domain_tags=result.get("domain_tags", []),
                sensitivity=result.get("sensitivity", "internal"),
                primary_entity=result.get("primary_entity", "record"),
                query_hints=result.get("query_hints", []),
                likely_join_keys=result.get("likely_join_keys", []),
            )
            
        except Exception as e:
            # Fallback to basic annotation on error
            return Annotator.fallback_annotation(source_id, profile)
    
    def _build_context(
        self, source_id: str, source_type: str, profile: ProfileData
    ) -> str:
        """Build context string for LLM.
        
        Args:
            source_id: Source identifier
            source_type: Type of source
            profile: Profile data
            
        Returns:
            Context string
        """
        lines = [
            f"Source: {source_id}",
            f"Type: {source_type}",
            f"Row count: {profile.row_count:,}",
            "",
            "Columns:",
        ]
        
        for col in profile.columns:
            pii_flag = " [PII]" if col.is_pii else ""
            null_info = f", {col.null_pct*100:.1f}% null"
            card_info = f", {col.cardinality} unique"
            samples = f", samples: {col.sample_values[:3]}" if col.sample_values else ""
            lines.append(f"  - {col.name} ({col.dtype}){pii_flag}{null_info}{card_info}{samples}")
        
        return "\n".join(lines)
    
    @staticmethod
    def fallback_annotation(source_id: str, profile: ProfileData) -> SemanticData:
        """Create intelligent fallback annotation based on column analysis.
        
        Uses exact column name matching to infer business context.
        
        Args:
            source_id: Source identifier
            profile: Profile data
            
        Returns:
            SemanticData with inferred business context
        """
        # Analyze columns to infer business context (case-insensitive)
        col_names_lower = [col.name.lower() for col in profile.columns]
        has_pii = any(col.is_pii for col in profile.columns)
        
        # Infer business domain from column names - check source_id first for better matching
        source_lower = source_id.lower()
        domain_tags = ["data"]
        primary_entity = "record"
        title_base = source_id.replace(".", " ").replace("_", " ").title()
        description = f"Business data table containing {profile.row_count:,} records."
        query_hints = []
        
        # Helper to check if any column matches pattern (case-insensitive)
        def has_col(pattern):
            return any(pattern in c for c in col_names_lower)
        
        # Check source_id name for strong hints
        # Categories - check for category-specific columns (must be before products check)
        if ("categories" in source_lower or "category" in source_lower) and has_col("category"):
            domain_tags = ["products", "categories", "classification"]
            primary_entity = "category"
            title_base = "Product Categories"
            description = f"Product category taxonomy with descriptions. Contains {profile.row_count:,} product categories. Use for product classification and category-based reporting."
            query_hints = ["join to products on categoryID", "filter by categoryName for specific types"]
        
        # Order details - must check before orders (more specific)
        elif "order_detail" in source_lower or (has_col("orderid") and has_col("productid") and has_col("quantity")):
            domain_tags = ["sales", "order-items", "revenue"]
            primary_entity = "order_line"
            title_base = "Order Line Items"
            description = f"Sales order line items with product quantities, unit prices, and discounts. {profile.row_count:,} line items. Use for revenue analysis and product sales breakdown."
            query_hints = ["join to orders on orderID", "join to products on productID", "calculate line total as unitPrice * quantity * (1 - discount)"]
        
        # Orders table - check for order-specific columns
        elif ("order" in source_lower and has_col("customerid")) or (has_col("orderid") and has_col("orderdate")):
            domain_tags = ["sales", "orders", "transactions"]
            primary_entity = "order"
            title_base = "Sales Orders"
            description = f"Sales order headers with customer references, order dates, shipping details, and freight costs. {profile.row_count:,} orders. Use for sales tracking and revenue analysis."
            query_hints = ["filter by orderDate for time-based analysis", "join to customers on customerID", "join to employees on employeeID for sales rep performance"]
        
        # Customers - check for customer-specific columns
        elif "customer" in source_lower and has_col("customerid"):
            domain_tags = ["customers", "sales", "contacts"]
            primary_entity = "customer"
            title_base = "Customer Directory"
            description = f"B2B customer directory with company names, contact persons, and geographic locations (city, country). {profile.row_count:,} customers across global markets. Use for customer lookup and regional analysis."
            query_hints = ["filter by country for regional sales analysis", "use companyName for exact customer lookup", "contactName and phone contain PII - handle securely"]
        
        # Employees
        elif "employee" in source_lower and has_col("employeeid"):
            domain_tags = ["hr", "employees", "organization"]
            primary_entity = "employee"
            title_base = "Employee Directory"
            description = f"Employee records with names, job titles, and reporting structure (reportsTo). {profile.row_count:,} employees. Use for HR analytics and organizational hierarchy."
            query_hints = ["filter by title for role-based analysis", "use reportsTo for manager/subordinate relationships", "employeeName contains PII - handle securely"]
        
        # Products - check for product-specific columns (has productID but not categoryID as primary)
        elif "product" in source_lower and has_col("productid") and has_col("productname"):
            domain_tags = ["products", "inventory", "catalog"]
            primary_entity = "product"
            title_base = "Product Catalog"
            description = f"Product master catalog with names, unit prices, packaging details, and category assignments. {profile.row_count:,} products. Use for product lookup and pricing."
            query_hints = ["filter by discontinued=0 for active products only", "join to categories on categoryID", "analyze unitPrice for pricing trends"]
        
        # Shippers
        elif "shipper" in source_lower and has_col("shipperid"):
            domain_tags = ["shipping", "logistics", "delivery"]
            primary_entity = "shipper"
            title_base = "Shipping Companies"
            description = f"Shipping carriers and freight companies with contact information. {profile.row_count:,} shipping providers. Use for logistics analysis and shipping method selection."
            query_hints = ["join to orders on shipperID", "use companyName for carrier lookup"]
        
        # Generic fallback based on column patterns
        else:
            # Check for date columns
            date_cols = [c for c in col_names_lower if "date" in c or "time" in c]
            if date_cols:
                query_hints.append(f"filter by {date_cols[0]} for time-based analysis")
            
            # Check for ID columns that might be join keys
            id_cols = [c for c in col_names_lower if c.endswith("id") or c.endswith("_id")]
            if id_cols:
                query_hints.append(f"use {id_cols[0]} for joining to related tables")
            
            if not query_hints:
                query_hints = ["filter by relevant columns for best performance"]
        
        # Guess sensitivity
        if has_pii:
            sensitivity = "confidential"
        elif any(c in col_names_lower for c in ["price", "amount", "cost", "revenue", "salary", "freight"]):
            sensitivity = "restricted"
        else:
            sensitivity = "internal"
        
        # Guess likely join keys
        join_keys = [
            col.name for col in profile.columns
            if col.name.lower().endswith("id") and col.name.lower() not in ["id"]
        ]
        
        return SemanticData(
            title=title_base,
            description=description,
            domain_tags=domain_tags,
            sensitivity=sensitivity,
            primary_entity=primary_entity,
            query_hints=query_hints,
            likely_join_keys=join_keys,
        )
