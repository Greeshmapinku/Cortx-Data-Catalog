"""Web application for LOCAL development - FULL features with Northwind dataset."""

import json
import os
from pathlib import Path
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

# Full imports for local development
from cortx_catalog.catalog_builder import CatalogBuilder
from cortx_catalog.embedder import Embedder

app = Flask(__name__)
CORS(app)

# Global catalog builder with full ML features
builder = None


def init_catalog():
    """Initialize catalog with Northwind dataset (full pipeline)."""
    global builder
    
    print("=" * 60)
    print("🚀 CORTX DATA CATALOG - LOCAL MODE (Full Features)")
    print("=" * 60)
    
    # Check for API key
    has_api_key = os.getenv("GROQ_API_KEY") is not None
    if not has_api_key:
        print("⚠️  Warning: GROQ_API_KEY not set. Using fallback annotations.")
        print("   Set GROQ_API_KEY for LLM-generated descriptions.")
    else:
        print("✓ GROQ_API_KEY found - LLM annotation enabled")
    
    # Create full CatalogBuilder with ML features
    print("\n📦 Initializing CatalogBuilder...")
    builder = CatalogBuilder(annotate=True, embed=True)
    
    # Load Northwind dataset
    dataset_dir = Path("dataset/Northwind_Traders")
    if not dataset_dir.exists():
        print(f"❌ Error: Dataset not found at {dataset_dir}")
        print("   Run from project root directory")
        return None
    
    sources = [
        ("csv", str(dataset_dir / "categories.csv"), None),
        ("csv", str(dataset_dir / "customers.csv"), None),
        ("csv", str(dataset_dir / "employees.csv"), None),
        ("csv", str(dataset_dir / "orders.csv"), None),
        ("csv", str(dataset_dir / "order_details.csv"), None),
        ("csv", str(dataset_dir / "products.csv"), None),
        ("csv", str(dataset_dir / "shippers.csv"), None),
    ]
    
    print(f"\n📊 Loading Northwind Traders dataset...")
    print("-" * 60)
    
    for source_type, uri, table in sources:
        try:
            entry = builder.add_source(source_type, uri, table)
            print(f"  ✓ {entry.source_id:<25} | {entry.profile.row_count:>5,} rows | {len(entry.profile.columns):>2} cols")
        except Exception as e:
            print(f"  ❌ Error loading {uri}: {e}")
    
    print("-" * 60)
    print(f"✅ Loaded {len(builder.catalog.entries)} sources")
    print(f"📈 Total rows: {sum(e.profile.row_count for e in builder.catalog.entries):,}")
    print(f"📊 Total columns: {sum(len(e.profile.columns) for e in builder.catalog.entries)}")
    
    # Save outputs
    print("\n💾 Saving outputs...")
    builder.save("catalog.json")
    builder.save_manifest("tool_manifest.json")
    print("  ✓ catalog.json")
    print("  ✓ tool_manifest.json")
    
    print("=" * 60)
    return builder


@app.route("/")
def index():
    """Serve the main UI using templates/index.html."""
    return render_template("index.html")


@app.route("/api/health")
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "catalog_loaded": builder is not None and len(builder.catalog.entries) > 0,
        "sources_count": len(builder.catalog.entries) if builder else 0,
        "mode": "local-full",
        "has_embeddings": builder.embedder is not None if builder else False
    })


@app.route("/api/catalog")
def get_catalog():
    """Return full catalog."""
    if not builder:
        return jsonify({"error": "Catalog not loaded"}), 500
    return jsonify({"catalog": [e.model_dump() for e in builder.catalog.entries]})


@app.route("/api/manifest")
def get_manifest():
    """Return MCP tool manifests."""
    if not builder:
        return jsonify({"error": "Catalog not loaded"}), 500
    
    manifest = {}
    for entry in builder.catalog.entries:
        if entry.mcp_tool:
            manifest[entry.mcp_tool.name] = {
                "description": entry.mcp_tool.description,
                "input_schema": entry.mcp_tool.input_schema.model_dump(),
                "source_id": entry.source_id
            }
    return jsonify(manifest)


@app.route("/api/search")
def search():
    """Search catalog using embeddings."""
    query = request.args.get("q", "")
    if not query:
        return jsonify({"query": "", "results": []})
    
    if not builder:
        return jsonify({"query": query, "results": [], "error": "Catalog not loaded"})
    
    try:
        results = []
        
        # Try semantic search first
        if builder.embedder and builder.embedder.embeddings:
            raw_results = builder.search(query, top_k=3)
            # Convert tuple format to object format expected by template
            for source_id, confidence, metadata in raw_results:
                # Get the entry to find the filename
                entry = next((e for e in builder.catalog.entries if e.source_id == source_id), None)
                filename = entry.connection_ref.split('/')[-1] if entry else source_id
                results.append({
                    "source_id": source_id,
                    "confidence": confidence,
                    "filename": filename,
                    "metadata": metadata
                })
        
        # Fallback to keyword search if no results
        if not results:
            query_lower = query.lower()
            for entry in builder.catalog.entries:
                semantic = entry.semantic
                text = f"{semantic.title} {semantic.description} {' '.join(semantic.domain_tags)}".lower()
                if query_lower in text:
                    results.append({
                        "source_id": entry.source_id,
                        "confidence": 0.8,
                        "metadata": {
                            "source_id": entry.source_id,
                            "source_type": entry.source_type,
                            "title": semantic.title,
                            "domain_tags": semantic.domain_tags
                        }
                    })
        
        return jsonify({"query": query, "results": results[:3]})
    except Exception as e:
        return jsonify({"query": query, "results": [], "error": str(e)})


@app.route("/download/<filename>")
def download(filename):
    """Download JSON files."""
    if filename not in ["catalog.json", "tool_manifest.json"]:
        return jsonify({"error": "File not found"}), 404
    
    filepath = Path(filename)
    if not filepath.exists():
        return jsonify({"error": "File not found"}), 404
    
    with open(filepath, "r") as f:
        return jsonify(json.load(f))


if __name__ == "__main__":
    init_catalog()
    port = int(os.getenv("PORT", 5000))
    print(f"\n🌐 Starting server on http://127.0.0.1:{port}")
    print("   Press CTRL+C to stop\n")
    app.run(host="0.0.0.0", port=port, debug=False)
