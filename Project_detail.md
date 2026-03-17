Hi Greeshma,

Please acknowledge receipt of the attached, and you can do both (2 different projects) or either one of them is ok to schedule a demo with me. Circle back when you are ready I expect each one take a day and you will have to talk through in detail once we meet.

Here's a full 1-day intern project — scoped tight enough to finish, deep enough to matter for Cortx's agentic RAG/MCP stack.

---

**Project: Cortx Data Catalog & Semantic Layer Builder**

**Context for intern:** Cortx agents (RAG, MCP tools) currently discover data sources at runtime with no metadata about what they contain, how they're structured, or what business concepts they represent. This means agents query blindly, return poor results, and can't reason about *which* data source to use. Your job today is to build the semantic layer that fixes this.

---

**Deliverable**

A Python CLI tool: `cortx-catalog-gen` that ingests one or more data sources, profiles them, sends metadata to an LLM for annotation, and outputs a `catalog.json` \+ a ready-to-register MCP tool manifest.

---

**Timeline (8 hours)---**  
**Minimum Viable `catalog.json` Schema**  
`{`  
  `"source_id": "pico_trades_db.positions",`  
  `"source_type": "postgresql",`  
  `"connection_ref": "env:PICO_DB_URL",`  
  `"profile": {`  
    `"row_count": 142000,`  
    `"columns": [`  
      `{`  
        `"name": "ticker",`  
        `"type": "varchar",`  
        `"null_pct": 0.0,`  
        `"cardinality": 312,`  
        `"sample_values": ["AAPL","MSFT","GOOG"]`  
      `}`  
    `]`  
  `},`  
  `"semantic": {`  
    `"title": "PICO Trading Positions",`  
    `"description": "Daily position records for all active equity portfolios.",`  
    `"domain_tags": ["trading","risk","equities"],`  
    `"sensitivity": "confidential",`  
    `"primary_entity": "position",`  
    `"query_hints": ["filter by portfolio_id", "always join to trades on trade_id"],`  
    `"embedding_model": "text-embedding-3-small"`  
  `},`  
  `"mcp_tool": {`  
    `"name": "query_pico_positions",`  
    `"description": "Query equity position records. Use when user asks about holdings, exposure, or P&L.",`  
    `"input_schema": { "type": "object", "properties": { "sql": { "type": "string" } } }`  
  `}`  
`}`

---

**Technical Depth Expected**

The intern should go beyond a basic schema dump. Specifically:

**Profiler** — cardinality ratio (high cardinality \= likely FK or ID), null rate, type inference for untyped sources (CSV), detection of PII patterns (email, SSN regex), date range detection on temporal columns.

**LLM annotation prompt** — structured output, not freeform. Force JSON response with defined keys. Include few-shot examples in the system prompt. Ask the model to identify: primary business entity, likely join keys, query anti-patterns to avoid.

**Embedding** — embed the full semantic block (`title + description + query_hints` concatenated), not just the column names. Store source\_id as metadata. Similarity search should return top-3 candidates with a confidence score.

**MCP manifest** — the `description` field is what agents read to decide whether to call the tool. It must be written in agent-legible language: *"Use when the user asks about X. Do not use for Y."* This is the most critical field — a bad description means agents pick the wrong tool.

---

**Assessment Rubric**

| Dimension | Weight | Excellent (4) | Good (3) | Acceptable (2) | Incomplete (1) |
| ----- | ----- | ----- | ----- | ----- | ----- |
| **Source coverage** | 15% | All 4 source types work cleanly with error handling and connection timeout | 3 of 4 working, basic errors caught | 2 working, no error handling | Only 1 source or placeholder stubs |
| **Profile depth** | 15% | Cardinality, null %, type inference, PII flag, date range, sample values | Cardinality \+ nulls \+ samples | Column names \+ types only | Raw schema dump only |
| **LLM annotation quality** | 20% | Structured JSON output, query hints are precise and actionable, sensitivity correctly classified | Structured output but hints are generic | Freeform text output, key fields present | Missing description or domain tags |
| **Embedding design** | 10% | Correct semantic block concatenated, metadata stored, similarity search returns ranked results | Embeddings generated and searchable | Embeddings stored but no search | No embedding or placeholder |
| **MCP manifest correctness** | 20% | Tool description written in agent-legible language with use/avoid guidance; input schema typed | Good description, schema present | Description present but vague | Missing or generic placeholder |
| **Code quality** | 10% | Clean separation of concerns (loader / profiler / annotator / exporter), typed dataclasses, docstrings | Mostly clean, some mixing | Works but monolithic | Hard to follow or broken |
| **Demo \+ explanation** | 10% | Live query routed correctly by agent using catalog; intern explains design decisions clearly | Demo works, explanation is surface-level | Demo partially works | No working demo |

**Scoring:** 28–32 \= Hire signal. 20–27 \= Strong with guidance. Below 20 \= Needs more fundamentals work.

---

**Stretch Goals (for fast interns)**

If they finish early, these push into real Cortx architecture:

1. **Incremental refresh** — detect schema drift between catalog runs and flag changed columns rather than re-profiling everything  
2. **Relationship inference** — detect likely FK relationships between tables across sources by matching column names \+ cardinality patterns (e.g. `positions.portfolio_id` → [`portfolios.id`](http://portfolios.id/))  
3. **Cortx integration** — instead of writing `tool_manifest.json` to disk, POST it directly to the Cortx MCP Factory registration endpoint and verify the tool appears in the agent's tool list  
4. **Sensitivity enforcement** — if a column is flagged `PII`, auto-inject a row-level filter guardrail into the generated MCP tool's SQL wrapper

