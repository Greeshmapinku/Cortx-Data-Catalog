# Cortx Data Catalog - Complete Project Explanation
## For Interview Preparation

---

## 📌 EXECUTIVE SUMMARY (30-Second Pitch)

> "I built a semantic layer builder that helps AI agents understand data sources before querying them. Think of it like giving agents a 'map' of your data - they know what's in each table, how columns relate, and which source to use for what query. The tool profiles data (row counts, nulls, PII), uses LLMs to generate business descriptions, creates embeddings for semantic search, and outputs MCP manifests that agents can consume."

**Key Result:** Agents go from blind querying to intelligent data discovery.

---

## 🎯 THE PROBLEM WE SOLVE

### Current State (Before Our Solution)
```
User: "Show me sales data"
Agent: *Queries random table* "Here are some rows..."
```
Agent has NO idea:
- Which table contains sales data
- What columns mean
- How tables relate
- What queries make sense

### Our Solution (After)
```
User: "Show me sales data"
Agent: *Searches semantic catalog* 
       → "Sales Orders" (95% match)
       → "Order Line Items" (87% match)
       → "Querying Sales Orders..."
       → "Here are 830 orders with customer details..."
```

**How?** We generate rich metadata:
- Business descriptions ("Sales order headers with customer references...")
- Domain tags (["sales", "revenue", "transactions"])
- Query hints ("filter by orderDate", "join to customers on customerID")
- Sensitivity levels (confidential, restricted)

---

## 🏗️ PROJECT ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────┐
│                        CORTX DATA CATALOG                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │   LOADERS   │───▶│  PROFILER   │───▶│  ANNOTATOR  │         │
│  │             │    │             │    │             │         │
│  │ CSV/SQLite/ │    │ Row counts  │    │ LLM generates│         │
│  │ Parquet     │    │ Cardinality │    │ descriptions │         │
│  │             │    │ PII detect  │    │ domain_tags  │         │
│  └─────────────┘    │ Null %      │    │ sensitivity  │         │
│                     └─────────────┘    └──────┬──────┘         │
│                                                │                │
│                     ┌─────────────┐    ┌──────▼──────┐         │
│                     │   OUTPUTS   │◀───│   EMBEDDER  │         │
│                     │             │    │             │         │
│                     │ catalog.json│    │ Creates     │         │
│                     │ tool_manifest│   │ embeddings  │         │
│                     │ .json       │    │ for search  │         │
│                     └─────────────┘    └─────────────┘         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📁 FILE-BY-FILE EXPLANATION

### 1. `app.py` - Web Application Entry Point

**Purpose:** Flask web server for demo/visualization

**Key Components:**
```python
# Routes
@app.route("/")              → Serves the UI
@app.route("/api/catalog")   → Returns full catalog JSON
@app.route("/api/search")    → Semantic search endpoint
@app.route("/api/manifest")  → Returns MCP manifests
@app.route("/download/<file>") → Download JSON files
```

**How it works:**
1. On startup: `init_catalog()` loads/generates the catalog
2. Creates HTML templates dynamically
3. Serves API endpoints for the frontend

**Interview Tip:** "The web UI is just a visualization layer. The real output is the JSON files that agents consume."

---

### 2. `catalog.json` - The Main Output

**Purpose:** Complete semantic catalog with all metadata

**Structure:**
```json
{
  "catalog": [
    {
      "source_id": "csv.customers",
      "source_type": "csv",
      "connection_ref": "dataset/customers.csv",
      "profile": {
        "row_count": 91,
        "columns": [
          {
            "name": "customerID",
            "dtype": "string",
            "null_pct": 0.0,
            "cardinality": 91,
            "sample_values": ["ALFKI", "ANATR"],
            "is_pii": false
          }
        ]
      },
      "semantic": {
        "title": "Customer Directory",
        "description": "B2B customer directory with company names...",
        "domain_tags": ["customers", "sales", "contacts"],
        "sensitivity": "confidential",
        "primary_entity": "customer",
        "query_hints": ["filter by country", "join on customerID"],
        "likely_join_keys": ["customerID"]
      },
      "mcp_tool": {
        "name": "query_csv_customers",
        "description": "Customer Directory - ... Use when user asks about...",
        "input_schema": {...}
      }
    }
  ]
}
```

**Key Sections:**
- `profile`: Statistical metadata (cardinality, nulls, samples)
- `semantic`: Business context (descriptions, tags, hints)
- `mcp_tool`: Agent-ready tool manifest

---

### 3. `tool_manifest.json` - MCP Tool Manifests

**Purpose:** Ready-to-register MCP tools for agents

**Structure:**
```json
{
  "query_csv_customers": {
    "description": "Customer Directory - B2B customer directory... Use when user asks about customer information... Do not use for product details...",
    "input_schema": {
      "type": "object",
      "properties": {
        "columns": {"type": "array"},
        "filters": {"type": "object"}
      }
    },
    "source_id": "csv.customers"
  }
}
```

**Critical Feature:** The `description` field is what agents READ to decide whether to use this tool. It's written in agent-legible language with "Use when... Do not use for..." patterns.

**Example:**
```
"Use when user asks about customer information, contact details, 
or client profiles. Do not use for product details, inventory, 
or non-customer data."
```

---

### 4. `src/cortx_catalog/cli.py` - Command Line Interface

**Purpose:** Main entry point for the tool

**Commands:**
```bash
# Profile a CSV file
cortx-catalog-gen --source csv --uri data.csv

# Profile SQLite database
cortx-catalog-gen --source sqlite --uri db.db --table users

# Run demo with synthetic data
cortx-catalog-gen --demo

# Skip LLM annotation (faster)
cortx-catalog-gen --source csv --uri data.csv --no-annotate
```

**Key Code:**
```python
@click.command()
@click.option("--source", type=click.Choice(["sqlite", "csv", "parquet"]))
@click.option("--uri", required=True)
@click.option("--output", default="catalog.json")
def main(source, uri, output):
    builder = CatalogBuilder()
    entry = builder.add_source(source, uri)
    builder.save(output)
```

---

### 5. `src/cortx_catalog/catalog_builder.py` - Main Orchestrator

**Purpose:** Coordinates all components (profiler, annotator, embedder)

**Key Method:**
```python
def add_source(self, source_type, connection_ref, table_name=None):
    # 1. Load data
    loader = get_loader(source_type, connection_ref)
    df = loader.load_data()
    schema = loader.get_schema()
    
    # 2. Profile data
    profile = self.profiler.profile(df, schema)
    
    # 3. Annotate with LLM (or fallback)
    if self.annotate:
        semantic = self.annotator.annotate(source_id, source_type, profile)
    else:
        semantic = Annotator.fallback_annotation(source_id, profile)
    
    # 4. Generate MCP manifest
    mcp_tool = self.manifest_generator.generate(entry)
    
    # 5. Add to catalog
    self.catalog.add_entry(entry)
    
    # 6. Add embedding for search
    if self.embed:
        self.embedder.add_entry(entry)
```

**Interview Question:** "How does the pipeline work?"
**Answer:** "Data flows through loaders → profiler → annotator → embedder → manifest generator. Each stage adds a layer of metadata."

---

### 6. `src/cortx_catalog/profiler.py` - Data Profiling

**Purpose:** Extract statistical metadata from data

**What it profiles:**
```python
class ColumnProfile:
    name: str           # Column name
    dtype: str          # Data type (integer, string, etc.)
    null_pct: float     # % of null values (0.0 - 1.0)
    cardinality: int    # Number of unique values
    sample_values: list # Top 5 most frequent values
    is_pii: bool        # Contains PII?
    date_range: tuple   # (min_date, max_date) for dates
```

**PII Detection:**
```python
PII_PATTERNS = {
    "email": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
    "ssn": r"^\d{3}-\d{2}-\d{4}$|^\d{9}$",
    "phone": r"^\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$",
    "credit_card": r"^\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}$"
}
```

**Example Output:**
```python
{
    "name": "email",
    "dtype": "string",
    "null_pct": 0.05,  # 5% nulls
    "cardinality": 850,  # 850 unique emails
    "sample_values": ["john@example.com", "jane@example.com"],
    "is_pii": true  # ← Flagged because name contains "email"
}
```

**Interview Question:** "How do you detect PII?"
**Answer:** "Two methods: (1) Regex pattern matching on sample values for emails, SSNs, phones, credit cards. (2) Column name heuristics - if column name contains 'email', 'ssn', 'phone', etc., we flag it."

---

### 7. `src/cortx_catalog/annotator.py` - LLM Annotation

**Purpose:** Use LLM (Groq API) to generate business context

**How it works:**
```python
def annotate(self, source_id, source_type, profile):
    # Build context about the table
    context = self._build_context(source_id, source_type, profile)
    
    # Call LLM with structured output
    response = self.client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": context}
        ],
        response_format={"type": "json_object"}  # ← Forces JSON output
    )
    
    # Parse structured response
    result = json.loads(response.choices[0].message.content)
    return SemanticData(
        title=result["title"],
        description=result["description"],
        domain_tags=result["domain_tags"],
        sensitivity=result["sensitivity"],
        query_hints=result["query_hints"]
    )
```

**System Prompt (Key Parts):**
```python
SYSTEM_PROMPT = """
You are a data catalog expert. Analyze tables and provide semantic metadata.

Respond ONLY with a JSON object containing:
- title: Business title (3-5 words)
- description: Rich business description (2-3 sentences)
- domain_tags: ["sales", "customers", "revenue"]  
- sensitivity: "public" | "internal" | "confidential" | "restricted"
- primary_entity: Main business entity (customer, order, product)
- query_hints: ["filter by orderDate", "join to customers"]
- likely_join_keys: ["customerID", "orderID"]

Few-shot examples included for guidance.
"""
```

**Fallback when LLM unavailable:**
```python
@staticmethod
def fallback_annotation(source_id, profile):
    # Pattern matching based on column names
    if "customer" in source_id and "customerid" in col_names:
        return SemanticData(
            title="Customer Directory",
            domain_tags=["customers", "sales", "contacts"],
            sensitivity="confidential"
        )
```

**Interview Question:** "Why use LLM?"
**Answer:** "LLMs understand business context. A column named 'amt' could be 'amount' or 'attitude' - the LLM infers from surrounding columns. They also generate useful query hints like 'filter by date range for large tables'."

---

### 8. `src/cortx_catalog/embedder.py` - Semantic Embeddings

**Purpose:** Create searchable embeddings for semantic similarity

**Key Concept:**
```
Embedding text → Vector of 384 numbers
"Sales Orders" → [0.23, -0.45, 0.89, ...]
```

**What we embed:**
```python
def create_embedding_text(self, semantic):
    parts = [
        semantic.title,              # "Sales Orders"
        semantic.description,        # "Sales order headers with..."
        " ".join(semantic.query_hints)  # "filter by orderDate join to..."
    ]
    return " ".join(parts)
```

**Why this matters:**
- Searching "customer contact" matches "Customer Directory" (not just column names)
- Uses `sentence-transformers/all-MiniLM-L6-v2` (free, local, 384-dim)

**Similarity Search:**
```python
def search(self, query, top_k=3):
    # Encode query
    query_embedding = self.model.encode(query)
    
    # Cosine similarity with all entries
    for source_id, embedding in self.embeddings.items():
        similarity = cosine_similarity(query_embedding, embedding)
        results.append((source_id, similarity))
    
    # Return top-k
    return sorted(results, key=lambda x: x[1], reverse=True)[:top_k]
```

**Example:**
```python
Query: "revenue analysis"
Results:
  1. Sales Orders (59.1%)
  2. Order Line Items (48.9%)
  3. Product Catalog (20.9%)
```

**Interview Question:** "How does semantic search work?"
**Answer:** "We convert titles, descriptions, and query hints into vectors using sentence-transformers. When user searches, we convert their query to a vector too, then find closest matches using cosine similarity. This finds 'Sales Orders' for 'revenue analysis' even if words don't match."

---

### 9. `src/cortx_catalog/manifest.py` - MCP Manifest Generator

**Purpose:** Generate agent-legible tool descriptions

**Key Method:**
```python
def _generate_description(self, entry):
    semantic = entry.semantic
    
    # Build specific use cases from domain tags
    use_cases = self._build_specific_use_cases(semantic)
    # → "customer information, contact details, or client profiles"
    
    # Build avoid cases (complementary domains)
    avoid_cases = self._build_avoid_cases(semantic)
    # → "product details, inventory, or non-customer data"
    
    return f"""
    {semantic.title} - {semantic.description}
    Use when user asks about {use_cases}.
    Do not use for {avoid_cases}.
    """
```

**Output Example:**
```
Customer Directory - B2B customer directory with company names, 
contact persons, and geographic locations. Use for customer lookup 
and regional analysis. 

Use when user asks about customer information, contact details, 
or client profiles, sales transactions, revenue metrics, or order 
history, contact information, addresses, or communication details.

Do not use for product details, inventory, or non-customer data.
```

**Why this format?**
- Agents READ this to decide which tool to use
- "Use when" tells them when to pick this tool
- "Do not use" prevents wrong tool selection

---

### 10. `src/cortx_catalog/loaders/` - Data Source Loaders

**Base Loader:**
```python
class BaseLoader(ABC):
    @abstractmethod
    def load_data(self) -> pd.DataFrame:
        pass
    
    @abstractmethod
    def get_schema(self) -> Dict[str, str]:
        pass
```

**CSV Loader:**
```python
class CSVLoader(BaseLoader):
    def load_data(self):
        # Try multiple encodings
        for encoding in ['utf-8', 'latin-1', 'iso-8859-1']:
            try:
                return pd.read_csv(self.connection_ref, encoding=encoding)
            except UnicodeDecodeError:
                continue
```

**SQLite Loader:**
```python
class SQLiteLoader(BaseLoader):
    def load_data(self):
        conn = sqlite3.connect(self.connection_ref)
        return pd.read_sql(f"SELECT * FROM {self.table_name}", conn)
    
    def get_schema(self):
        cursor = conn.execute(f"PRAGMA table_info({self.table_name})")
        # Returns column names and types
```

**Interview Question:** "How do you handle different data sources?"
**Answer:** "We use the Strategy pattern. BaseLoader defines the interface, each source (CSV, SQLite, Parquet) implements load_data() and get_schema(). This makes adding new sources easy - just implement the interface."

---

### 11. `src/cortx_catalog/models.py` - Data Models

**Pydantic Models:**
```python
class ColumnProfile(BaseModel):
    name: str
    dtype: str
    null_pct: float = Field(ge=0.0, le=1.0)
    cardinality: int
    sample_values: List[Any]
    is_pii: bool = False
    date_range: Optional[Tuple[str, str]] = None

class SemanticData(BaseModel):
    title: str
    description: str
    domain_tags: List[str]
    sensitivity: str = Field(pattern=r"^(public|internal|confidential|restricted)$")
    primary_entity: str
    query_hints: List[str]
    likely_join_keys: List[str]

class CatalogEntry(BaseModel):
    source_id: str
    source_type: str
    connection_ref: str
    profile: ProfileData
    semantic: SemanticData
    mcp_tool: Optional[MCPTool] = None
```

**Why Pydantic?**
- Type validation
- JSON serialization
- Auto-generated docs

---

## 🎤 INTERVIEW Q&A PREPARATION

### Q1: "Walk me through your project"
**A:** 
"I built a semantic layer builder for AI agents. The problem is agents query data sources blindly - they don't know what's in tables or which to use. My solution profiles data (cardinality, nulls, PII), uses LLMs to generate business descriptions, creates embeddings for semantic search, and outputs MCP manifests. Agents read these manifests to make informed decisions."

### Q2: "How does PII detection work?"
**A:**
"Two-pronged approach: (1) Regex patterns on sample values detect emails, SSNs, phones, credit cards. (2) Column name heuristics - if name contains 'email', 'ssn', etc., we flag it. This catches PII even if values are masked."

### Q3: "Why use embeddings?"
**A:**
"Traditional search matches keywords. Embeddings match meaning. If user searches 'revenue analysis', embeddings find 'Sales Orders' because the description talks about revenue, even without keyword match. We use sentence-transformers (free, local) and embed title + description + query_hints."

### Q4: "What is MCP?"
**A:**
"Model Context Protocol - a standard for tools that agents can use. Our manifest describes each data source as an MCP tool with name, description, and input schema. The description is critical - it's written in agent-legible language with 'Use when... Do not use for...' guidance."

### Q5: "How does the LLM annotation work?"
**A:**
"We send column metadata to Groq API with a system prompt that forces structured JSON output. The prompt includes few-shot examples. LLM returns business title, description, domain tags, sensitivity, query hints. If LLM fails, we have intelligent fallback based on column name patterns."

### Q6: "How would this integrate with Cortx?"
**A:**
"The tool_manifest.json can POST to Cortx MCP Factory. Agents would receive these tool descriptions in their context. When user asks about 'sales', agent reads manifest descriptions, sees 'Sales Orders - Use when user asks about sales transactions', and picks the right tool."

### Q7: "What's the architecture?"
**A:**
"Clean separation: loaders handle data sources, profiler extracts stats, annotator adds business context via LLM, embedder creates vectors for search, manifest generator creates MCP tools. All orchestrated by CatalogBuilder. Uses Pydantic for type safety."

### Q8: "How do you handle errors?"
**A:**
"Each layer has try/except. If LLM fails, fallback annotation kicks in. If a CSV fails to load, we log warning and continue. For deployment, we pre-generate catalog so Render doesn't timeout downloading models."

### Q9: "What was the hardest part?"
**A:**
"Getting the LLM prompt right. Early attempts gave generic descriptions. Solution: (1) Structured JSON output, (2) Few-shot examples showing good vs bad, (3) Clear requirements like 'description must mention actual column names'. Also deployment - had to pre-download embedding model to avoid timeouts."

### Q10: "What's next for this project?"
**A:**
"Stretch goals: (1) Incremental refresh - detect schema changes instead of re-profiling. (2) FK relationship inference - match column names + cardinality across tables. (3) Direct Cortx integration - POST to MCP Factory. (4) Sensitivity enforcement - auto-inject filters for PII columns."

---

## 💡 KEY CONCEPTS TO KNOW

### 1. Semantic Layer
**What:** Business context layer on top of raw data
**Why:** Agents need to understand "what does this column mean?" not just "what's the column name?"
**Example:** `amt` → "Transaction amount in USD"

### 2. MCP (Model Context Protocol)
**What:** Standard for agent tools
**Our use:** Each data source = one MCP tool
**Key field:** `description` - agents read this to pick tools

### 3. Embeddings
**What:** Text → Vector of numbers
**Why:** Enables semantic similarity search
**Tool:** sentence-transformers (free, local)

### 4. Cardinality
**What:** Number of unique values in a column
**Why:** High cardinality often means ID/FK column
**Example:** `customer_id` in orders table has high cardinality

### 5. PII (Personally Identifiable Information)
**What:** Data that identifies individuals (emails, SSNs, etc.)
**Detection:** Regex + column name heuristics
**Importance:** Agents need to know what data is sensitive

---

## 📊 METRICS TO MENTION

- **7 data sources** loaded (Northwind dataset)
- **5 PII patterns** detected
- **384-dimension** embeddings
- **~60% confidence** for top semantic search results
- **96% assessment score** (4/4 on most dimensions)

---

## ✅ PRE-INTERVIEW CHECKLIST

- [ ] Read this entire document
- [ ] Run `python app.py` locally and play with it
- [ ] Try semantic search: "sales orders", "customer contact"
- [ ] Open `catalog.json` and understand its structure
- [ ] Be ready to explain: profiler → annotator → embedder → manifest flow
- [ ] Practice the 30-second pitch
- [ ] Have your live demo URL ready (if deployed)

---

## 🎯 CLOSING STATEMENT

> "This project demonstrates clean architecture with separation of concerns, production-ready error handling, and practical application of LLMs and embeddings. The semantic layer enables AI agents to move from blind querying to intelligent data discovery, which is exactly what Cortx needs for their agentic RAG/MCP stack."

**Good luck! You've got this! 💪**
