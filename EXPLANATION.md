# Cortx Data Catalog - Project Explanation

> **Complete Interview Preparation Guide**

---

## Executive Summary

### The 30-Second Pitch

> *"I built a semantic layer builder that helps AI agents understand data sources before querying them. Think of it as giving agents a 'map' of your data---they know what's in each table, how columns relate, and which source to use for what query. The tool profiles data (row counts, nulls, PII), uses LLMs to generate business descriptions, creates embeddings for semantic search, and outputs MCP manifests that agents can consume."*

### Key Result

Agents transition from **blind querying** to **intelligent data discovery**.

| Before (No Semantic Layer) | After (With Semantic Layer) |
|---------------------------|----------------------------|
| User: "Show me sales data" | User: "Show me sales data" |
| Agent: Queries random table | Agent: Searches semantic catalog |
| Result: Random rows returned | Result: Sales Orders (95% match), Order Line Items (87% match) |

---

## The Problem We Solve

### Current State (Before Our Solution)

When AI agents query data sources today, they face several critical challenges:

- **No Metadata Awareness:** Agents don't know what tables contain
- **No Business Context:** Column names like `amt` could mean "amount" or "attitude"
- **No Relationship Understanding:** Agents don't know how tables join
- **Wrong Tool Selection:** Agents pick data sources randomly

### Our Solution

We generate rich metadata including:

- **Business Descriptions:** "Sales order headers with customer references..."
- **Domain Tags:** ["sales", "revenue", "transactions"]
- **Query Hints:** "filter by orderDate", "join to customers on customerID"
- **Sensitivity Levels:** confidential, restricted, internal, public

---

## Project Architecture

### High-Level Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Loaders   │────▶│  Profiler   │────▶│  Annotator  │
│ CSV/SQLite  │     │ Stats/PII   │     │   LLM       │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                          ┌────────────────────┼────────────────────┐
                          ▼                    ▼                    ▼
                   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
                   │  Embedder   │     │   Manifest  │     │   Outputs   │
                   │   Vectors   │     │   MCP Tools │     │  catalog.json│
                   └─────────────┘     └──────┬──────┘     │tool_manifest│
                                              └────────────▶└─────────────┘
```

### Data Flow

1. **Load:** Data sources loaded (CSV, SQLite, Parquet)
2. **Profile:** Statistical analysis (cardinality, nulls, PII detection)
3. **Annotate:** LLM generates business context
4. **Embed:** Create searchable vectors
5. **Manifest:** Generate MCP tool descriptions
6. **Output:** Write JSON files for agents

---

## File-by-File Explanation

### app.py - Web Application Entry Point

**Purpose:** Flask web server for demo and visualization.

**Key Routes:**

```python
@app.route("/")              # Serves the UI
@app.route("/api/catalog")   # Returns full catalog JSON
@app.route("/api/search")    # Semantic search endpoint
@app.route("/api/manifest")  # Returns MCP manifests
@app.route("/download/<file>")  # Download JSON files
```

> **Interview Tip:** The web UI is just a visualization layer. The real output is the JSON files that agents consume. The web interface helps developers understand what's being generated.

---

### catalog.json - The Main Output

**Purpose:** Complete semantic catalog with all metadata.

**Structure:**

```json
{
  "catalog": [{
    "source_id": "csv.customers",
    "source_type": "csv",
    "connection_ref": "dataset/customers.csv",
    "profile": {
      "row_count": 91,
      "columns": [{
        "name": "customerID",
        "dtype": "string",
        "null_pct": 0.0,
        "cardinality": 91,
        "sample_values": ["ALFKI", "ANATR"],
        "is_pii": false
      }]
    },
    "semantic": {
      "title": "Customer Directory",
      "description": "B2B customer directory...",
      "domain_tags": ["customers", "sales", "contacts"],
      "sensitivity": "confidential",
      "query_hints": ["filter by country"]
    },
    "mcp_tool": {
      "name": "query_csv_customers",
      "description": "Use when user asks about...",
      "input_schema": {...}
    }
  }]
}
```

---

### src/cortx_catalog/profiler.py - Data Profiling

**Purpose:** Extract statistical metadata from data sources.

**PII Detection Patterns:**

```python
PII_PATTERNS = {
    "email": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
    "ssn": r"^\d{3}-\d{2}-\d{4}$|^\d{9}$",
    "phone": r"^\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$",
    "credit_card": r"^\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}$"
}
```

**Interview Question:** "How do you detect PII?"

**Answer:** "Two methods: (1) Regex pattern matching on sample values for emails, SSNs, phones, credit cards. (2) Column name heuristics---if column name contains `email`, `ssn`, `phone`, etc., we flag it."

---

### src/cortx_catalog/annotator.py - LLM Annotation

**Purpose:** Use LLM (Groq API) to generate business context.

**System Prompt Excerpt:**

```
You are a data catalog expert. Analyze tables and provide 
semantic metadata. Respond ONLY with JSON containing:
- title: Business title (3-5 words)
- description: Rich business description
- domain_tags: ["sales", "customers", "revenue"]
- sensitivity: "public|internal|confidential|restricted"
- query_hints: ["filter by orderDate"]
```

---

### src/cortx_catalog/embedder.py - Semantic Embeddings

**Purpose:** Create searchable embeddings for similarity search.

**What We Embed:**

```python
def create_embedding_text(self, semantic):
    parts = [
        semantic.title,              # "Sales Orders"
        semantic.description,        # "Sales order headers..."
        " ".join(semantic.query_hints)  # "filter by orderDate..."
    ]
    return " ".join(parts)
```

**Why This Matters:**
Searching "customer contact" matches "Customer Directory" even if words don't exactly match, because embeddings capture semantic meaning.

---

### src/cortx_catalog/manifest.py - MCP Manifest Generator

**Purpose:** Generate MCP (Model Context Protocol) tool manifests with agent-legible descriptions.

**Agent-Legible Description Format:**

```python
def _generate_description(self, entry):
    parts = [
        semantic.title,
        "-",
        semantic.description
    ]
    if use_cases:
        parts.append(f"Use when user asks about {use_cases}.")
    if avoid_cases:
        parts.append(f"Do not use for {avoid_cases}.")
    return " ".join(parts)
```

**Example Output:**
```
"Sales Orders - Daily sales order headers with customer references.
Use when user asks about revenue, sales transactions, or order history.
Do not use for inventory analysis or supplier information."
```

---

## Interview Q&A Preparation

### Q1: Walk me through your project

**Answer:** "I built a semantic layer builder for AI agents. The problem is agents query data sources blindly---they don't know what's in tables or which to use. My solution profiles data (cardinality, nulls, PII), uses LLMs to generate business descriptions, creates embeddings for semantic search, and outputs MCP manifests. Agents read these manifests to make informed decisions about which data source to query."

### Q2: How does PII detection work?

**Answer:** "Two-pronged approach: First, regex pattern matching on sample values detects emails, SSNs, phones, and credit cards. Second, column name heuristics---if the column name contains keywords like `email`, `ssn`, or `phone`, we flag it as PII. This catches sensitive data even if values are masked or incomplete."

### Q3: Why use embeddings?

**Answer:** "Traditional search matches exact keywords. Embeddings match meaning. If a user searches for `revenue analysis`, embeddings find `Sales Orders` because the description discusses revenue, even without keyword overlap. We use sentence-transformers, which is free, local, and creates 384-dimensional vectors. We embed the concatenation of title, description, and query hints."

### Q4: What is MCP?

**Answer:** "MCP stands for Model Context Protocol---a standard for tools that AI agents can use. In our implementation, each data source becomes an MCP tool with a name, description, and input schema. The description is critical: it's written in agent-legible language with `Use when... Do not use for...` guidance, allowing agents to intelligently select the right tool for a query."

### Q5: How would this integrate with Cortx?

**Answer:** "The tool_manifest.json can be POSTed directly to the Cortx MCP Factory. Agents would receive these tool descriptions in their context window. When a user asks about `sales`, the agent reads the manifest, sees `Sales Orders---Use when user asks about sales transactions`, and intelligently selects that tool rather than querying randomly."

### Q6: What's the architecture?

**Answer:** "Clean separation of concerns: loaders handle data ingestion, profiler extracts statistics, annotator adds business context via LLM, embedder creates vectors for search, and manifest generator creates MCP tools. All orchestrated by CatalogBuilder. We use Pydantic for type safety and validation throughout."

### Q7: What was the hardest part?

**Answer:** "Getting the LLM prompt right. Early attempts gave generic descriptions like `This is a data table`. The solution was three-fold: structured JSON output to force consistency, few-shot examples showing good versus bad outputs, and explicit requirements like `description must reference actual column names`. The second challenge was deployment---the ML models are memory-intensive, so we created a lightweight mode for cloud deployment."

---

## Key Metrics

- **7 data sources** loaded (Northwind dataset)
- **5 PII patterns** detected (email, SSN, phone, credit card, IP)
- **384-dimension** embeddings
- **~60% confidence** for top semantic search results
- **96% assessment score** (4/4 on most dimensions)

---

## Closing Statement

> *"This project demonstrates clean architecture with separation of concerns, production-ready error handling, and practical application of LLMs and embeddings. The semantic layer enables AI agents to move from blind querying to intelligent data discovery, which is exactly what Cortx needs for their agentic RAG/MCP stack."*

---

*Document prepared by Greeshma for interview preparation*
