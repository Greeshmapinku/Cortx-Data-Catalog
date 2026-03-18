# Cortx Data Catalog - Technical Design Document

> **Architecture, Implementation & Engineering Decisions**

**Document Version:** 1.0  
**Status:** Final  
**Author:** Greeshma

---

## Table of Contents

1. [Introduction](#introduction)
2. [System Architecture](#system-architecture)
3. [Data Models](#data-models)
4. [Algorithms & Implementation](#algorithms--implementation)
5. [API Specification](#api-specification)
6. [Deployment Architecture](#deployment-architecture)
7. [Engineering Decisions](#engineering-decisions)
8. [Performance Considerations](#performance-considerations)
9. [Security Considerations](#security-considerations)
10. [Appendix](#appendix)

---

## Introduction

### Document Purpose

This design document serves as the authoritative technical specification for the Cortx Data Catalog & Semantic Layer Builder. It captures:

- System architecture and component interactions
- Data models and schema definitions
- API specifications and endpoints
- Algorithmic approaches (PII detection, embeddings, LLM integration)
- Engineering decisions and trade-offs
- Deployment considerations

### System Overview

The Cortx Data Catalog is a Python-based CLI tool and web service that generates semantic metadata for data sources. It bridges the gap between raw data storage and AI agent comprehension by creating a rich metadata layer.

| Attribute | Value |
|-----------|-------|
| Language | Python 3.11+ |
| Architecture | Modular, pipeline-based |
| Primary Interface | CLI (cortx-catalog-gen) |
| Secondary Interface | Flask Web API |
| LLM Provider | Groq API (Llama 3.3 70B) |
| Embedding Model | sentence-transformers/all-MiniLM-L6-v2 |
| Output Format | JSON (catalog.json, tool_manifest.json) |

---

## System Architecture

### Architectural Pattern

The system follows a **Pipeline Architecture** with **Strategy Pattern** for data source loaders. This provides:

- **Separation of Concerns:** Each component has a single responsibility
- **Extensibility:** New data sources can be added by implementing the loader interface
- **Testability:** Components can be tested in isolation
- **Composability:** Pipeline stages can be rearranged or skipped

### Component Diagram

```
                    Data Flow
    ┌──────────────┐
    │  Raw Data    │
    │   Sources    │
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐     DataFrame
    │   Loaders    │──────────────────┐
    │Data Ingestion│                   │
    └──────┬───────┘                   │
           │                           │
           ▼                           │
    ┌──────────────┐     ProfileData   │
    │   Profiler   │──────────────────┤
    │   Stats/PII  │                   │
    └──────┬───────┘                   │
           │                           │
           ▼                           │
    ┌──────────────┐     SemanticData  │
    │  Annotator   │──────┬────────────┤
    │   LLM/Desc   │      │            │
    └──────┬───────┘      │            │
           │              │            │
           ▼              ▼            ▼
    ┌──────────────┐  ┌──────────┐  ┌─────────┐
    │   Embedder   │  │ Manifest │  │ Outputs │
    │   Vectors    │  │MCP Tools │  │catalog  │
    └──────────────┘  └────┬─────┘  │tool_    │
                           │        │manifest │
                           ▼        └─────────┘
                      ┌──────────┐
                      │  JSON    │
                      │  Files   │
                      └──────────┘
```

### Component Responsibilities

| Component | Responsibility | Output |
|-----------|---------------|--------|
| Loaders | Data source abstraction | pandas DataFrame |
| Profiler | Statistical analysis | ProfileData (cardinality, nulls, PII) |
| Annotator | Business context generation | SemanticData (descriptions, tags) |
| Embedder | Vector representation | Embedding vectors (384-dim) |
| Manifest Generator | MCP tool creation | MCPTool (name, description, schema) |

---

## Data Models

### Core Models (Pydantic)

All data models use Pydantic v2 for validation, serialization, and type safety.

#### ColumnProfile

Represents statistical metadata for a single column.

```python
class ColumnProfile(BaseModel):
    name: str
    dtype: str
    null_pct: float = Field(ge=0.0, le=1.0)
    cardinality: int
    sample_values: List[Any]
    is_pii: bool = False
    date_range: Optional[Tuple[str, str]] = None
```

**Validation:** `null_pct` constrained to [0.0, 1.0] range.

#### SemanticData

Contains LLM-generated business context.

```python
class SemanticData(BaseModel):
    title: str
    description: str
    domain_tags: List[str]
    sensitivity: str = Field(
        pattern=r"^(public|internal|confidential|restricted)$"
    )
    primary_entity: str
    query_hints: List[str]
    likely_join_keys: List[str]
```

#### CatalogEntry

Top-level container for a data source.

```python
class CatalogEntry(BaseModel):
    source_id: str
    source_type: str
    connection_ref: str
    profile: ProfileData
    semantic: SemanticData
    mcp_tool: Optional[MCPTool] = None
```

---

## Algorithms & Implementation

### PII Detection Algorithm

#### Approach
Two-pronged detection strategy:

1. **Pattern Matching:** Regex on sample values
2. **Heuristic Analysis:** Column name keyword matching

#### Regex Patterns

```python
PII_PATTERNS = {
    "email": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
    "ssn": r"^\d{3}-\d{2}-\d{4}$|^\d{9}$",
    "phone": r"^\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$",
    "credit_card": r"^\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}$",
    "ip_address": r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
}
```

#### Column Name Hints

```python
PII_COLUMN_HINTS = {
    "email": ["email", "e-mail", "mail"],
    "ssn": ["ssn", "social", "social_security"],
    "phone": ["phone", "mobile", "cell", "telephone"],
    "name": ["name", "first_name", "last_name", "fullname"],
    "address": ["address", "street", "city", "zip", "postal"]
}
```

### Semantic Embedding Algorithm

#### Model Selection

- **Model:** sentence-transformers/all-MiniLM-L6-v2
- **Dimensions:** 384
- **Size:** ~80MB
- **Runtime:** Local (no API calls)

#### Text Construction

```python
def create_embedding_text(self, semantic: SemanticData) -> str:
    parts = [
        semantic.title,
        semantic.description,
        " ".join(semantic.query_hints)
    ]
    return " ".join(parts)
```

#### Similarity Metric

Cosine similarity between query vector and catalog entry vectors:

```
similarity = (a · b) / (||a|| × ||b||)
```

### LLM Annotation Algorithm

#### Prompt Engineering

**System Prompt Structure:**

1. Role definition ("You are a data catalog expert")
2. Output format specification (JSON schema)
3. Few-shot examples (3 detailed examples)
4. Quality constraints ("MUST reference actual columns")

#### Fallback Strategy

When LLM unavailable (no API key), use pattern matching:

```python
# Example: Detect customer table
if "customer" in source_id and "customerid" in columns:
    return SemanticData(
        title="Customer Directory",
        domain_tags=["customers", "sales", "contacts"],
        sensitivity="confidential"
    )
```

---

## API Specification

### REST API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serve web UI |
| `/api/catalog` | GET | Return full catalog JSON |
| `/api/manifest` | GET | Return MCP tool manifests |
| `/api/search` | GET | Semantic search (query param: q) |
| `/api/health` | GET | Health check |
| `/download/{file}` | GET | Download JSON file |

### CLI Interface

```bash
# Profile CSV file
cortx-catalog-gen --source csv --uri data.csv

# Profile SQLite with specific table
cortx-catalog-gen --source sqlite --uri db.db --table users

# Run demo mode
cortx-catalog-gen --demo

# Skip LLM annotation (faster)
cortx-catalog-gen --source csv --uri data.csv --no-annotate
```

---

## Running the Application

### Local Development Mode

For local development, the application runs with full features:

- All ML models loaded (sentence-transformers)
- Full semantic search with embeddings
- LLM annotation enabled (requires GROQ_API_KEY)
- Live data processing from sources

### Starting the Application

```bash
# CLI mode
cortx-catalog-gen --demo

# Web dashboard
python app.py
# Then open http://localhost:5000
```

### Environment Variables

```bash
# Optional: Enable LLM annotation
export GROQ_API_KEY="your-key-here"

# Optional: Change port
export PORT=5001
```

---

## Engineering Decisions

### Why Pydantic?

- **Type Safety:** Runtime validation prevents data corruption
- **Serialization:** Easy JSON import/export
- **Documentation:** Self-documenting models
- **IDE Support:** Autocompletion and type hints

### Why sentence-transformers?

- **Free:** No API costs
- **Local:** No network dependencies
- **Fast:** Optimized for inference
- **Small:** 80MB vs 500MB+ for larger models

### Why Groq API?

- **Structured Output:** Native JSON mode
- **Fast:** Sub-second response times
- **Free Tier:** Generous limits for development
- **Fallback:** Works without API key

---

## Performance Considerations

### Memory Usage

| Component | Memory |
|-----------|--------|
| Base Application | 50MB |
| Embedding Model | 150MB |
| Pandas/Data | 100MB |
| PyTorch | 300MB |
| **Total** | **~600MB** |

### Startup Time

- **First run:** 10-15 seconds (model download)
- **Subsequent runs:** 3-5 seconds

---

## Security Considerations

### PII Handling

- PII columns flagged but not redacted in output
- Sample values exposed (first 5 most frequent)
- Sensitivity classification guides agent behavior

### API Key Management

- GROQ_API_KEY from environment variable
- Never hardcoded in source
- GitHub Secret Scanning enabled

---

## Appendix

### File Structure

```
cortx-catalog-gen/
├── app.py                      # Flask web application
├── catalog.json                # Generated catalog output
├── tool_manifest.json          # MCP tool manifests
├── pyproject.toml              # Package configuration
├── requirements.txt            # Dependencies
├── src/
│   └── cortx_catalog/
│       ├── __init__.py
│       ├── cli.py              # CLI entry point
│       ├── models.py           # Pydantic data models
│       ├── profiler.py         # Data profiling logic
│       ├── annotator.py        # LLM annotation
│       ├── embedder.py         # Semantic embeddings
│       ├── manifest.py         # MCP manifest generator
│       ├── catalog_builder.py  # Main orchestrator
│       └── loaders/            # Data source loaders
│           ├── base.py
│           ├── csv_loader.py
│           ├── sqlite_loader.py
│           └── parquet.py
├── tests/                      # Unit tests
├── examples/                   # Example scripts
└── dataset/                    # Sample data (Northwind)
```

### Technology Stack

- **Language:** Python 3.11+
- **Web Framework:** Flask 3.0+
- **Data Processing:** Pandas 2.0+, PyArrow
- **ML/NLP:** sentence-transformers, transformers
- **LLM:** Groq API (Llama 3.3 70B)
- **Validation:** Pydantic 2.0+
- **CLI:** Click 8.0+
- **Testing:** pytest 7.0+

### Future Enhancements

#### Stretch Goals

1. **Incremental Refresh:** Detect schema drift between runs
2. **FK Inference:** Match column names + cardinality across sources
3. **Cortx Integration:** POST directly to MCP Factory
4. **Row-Level Security:** Auto-inject filters for PII columns
5. **Multi-Model Support:** Add support for Ollama, OpenAI, etc.

---

*Document prepared by Greeshma - Technical Design Specification*
