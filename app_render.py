"""Lightweight Flask app for Render deployment - NO ML dependencies."""

import json
import os
from pathlib import Path
from flask import Flask, jsonify, render_template_string, request
from flask_cors import CORS

# Only import Pydantic models (lightweight)
from cortx_catalog.models import (
    Catalog, CatalogEntry, ProfileData, SemanticData, 
    MCPTool, ColumnProfile, MCPInputSchema
)

app = Flask(__name__)
CORS(app)

# Global catalog
builder = None


class SimpleCatalogBuilder:
    """Minimal catalog builder for Render (no ML dependencies)."""
    
    def __init__(self):
        self.catalog = Catalog()
        self.embedder = None
    
    def load_from_json(self, filepath):
        """Load catalog from pre-generated JSON."""
        with open(filepath, "r") as f:
            data = json.load(f)
        
        for entry_data in data.get("catalog", []):
            profile = ProfileData(
                row_count=entry_data["profile"]["row_count"],
                columns=[ColumnProfile(**col) for col in entry_data["profile"]["columns"]]
            )
            
            semantic = SemanticData(**entry_data["semantic"])
            
            mcp_data = entry_data["mcp_tool"]
            mcp_tool = MCPTool(
                name=mcp_data["name"],
                description=mcp_data["description"],
                input_schema=MCPInputSchema(**mcp_data["input_schema"])
            )
            
            entry = CatalogEntry(
                source_id=entry_data["source_id"],
                source_type=entry_data["source_type"],
                connection_ref=entry_data["connection_ref"],
                profile=profile,
                semantic=semantic,
                mcp_tool=mcp_tool
            )
            
            self.catalog.add_entry(entry)
    
    def search(self, query, top_k=3):
        """Simple keyword search (no embeddings)."""
        query_lower = query.lower()
        results = []
        
        for entry in self.catalog.entries:
            score = 0
            text = f"{entry.semantic.title} {entry.semantic.description} {' '.join(entry.semantic.domain_tags)}"
            text_lower = text.lower()
            
            # Simple keyword matching
            for word in query_lower.split():
                if word in text_lower:
                    score += 1
            
            if score > 0:
                results.append({
                    "source_id": entry.source_id,
                    "confidence": min(score / len(query_lower.split()), 1.0),
                    "metadata": {
                        "source_id": entry.source_id,
                        "source_type": entry.source_type,
                        "title": entry.semantic.title,
                        "domain_tags": entry.semantic.domain_tags
                    }
                })
        
        results.sort(key=lambda x: x["confidence"], reverse=True)
        return results[:top_k]


def init_catalog():
    """Initialize catalog from pre-generated JSON."""
    global builder
    print("=" * 50)
    print("STARTING CORTX DATA CATALOG - RENDER MODE")
    print("=" * 50)
    
    builder = SimpleCatalogBuilder()
    
    # Try to load catalog.json
    catalog_path = "catalog.json"
    if not Path(catalog_path).exists():
        print(f"ERROR: {catalog_path} not found!")
        print("Creating empty catalog...")
        return builder
    
    print(f"Loading catalog from {catalog_path}...")
    builder.load_from_json(catalog_path)
    print(f"✓ Loaded {len(builder.catalog.entries)} sources")
    print("=" * 50)
    
    return builder


@app.route("/")
def index():
    """Serve the main UI."""
    entries = builder.catalog.entries if builder else []
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Cortx Data Catalog</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #0a0a0a;
                color: #fff;
                line-height: 1.6;
            }}
            .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
            header {{
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                padding: 40px 0;
                text-align: center;
                border-bottom: 1px solid #333;
            }}
            h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
            .subtitle {{ color: #888; font-size: 1.1em; }}
            .byline {{ color: #666; font-size: 0.9em; margin-top: 10px; }}
            .stats {{
                display: flex;
                justify-content: center;
                gap: 40px;
                margin-top: 30px;
                flex-wrap: wrap;
            }}
            .stat {{
                text-align: center;
                padding: 20px 30px;
                background: rgba(255,255,255,0.05);
                border-radius: 12px;
                border: 1px solid #333;
            }}
            .stat-value {{ font-size: 2em; font-weight: bold; color: #4CAF50; }}
            .stat-label {{ color: #888; font-size: 0.9em; }}
            .content {{ padding: 40px 0; }}
            .entry {{
                background: #1a1a1a;
                border: 1px solid #333;
                border-radius: 12px;
                padding: 25px;
                margin-bottom: 20px;
            }}
            .entry-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
                flex-wrap: wrap;
                gap: 10px;
            }}
            .entry-title {{ font-size: 1.3em; color: #fff; }}
            .entry-type {{
                background: #333;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 0.8em;
                color: #aaa;
            }}
            .entry-desc {{ color: #aaa; margin-bottom: 15px; }}
            .tags {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 15px; }}
            .tag {{
                background: rgba(76, 175, 80, 0.2);
                color: #4CAF50;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 0.8em;
            }}
            .search-box {{
                width: 100%;
                max-width: 600px;
                margin: 0 auto 40px;
                display: flex;
                gap: 10px;
            }}
            .search-input {{
                flex: 1;
                padding: 15px 20px;
                border: 1px solid #333;
                border-radius: 8px;
                background: #1a1a1a;
                color: #fff;
                font-size: 1em;
            }}
            .search-btn {{
                padding: 15px 30px;
                background: #4CAF50;
                color: #fff;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-size: 1em;
            }}
            .search-btn:hover {{ background: #45a049; }}
            .download-links {{
                text-align: center;
                margin: 30px 0;
            }}
            .download-links a {{
                color: #4CAF50;
                text-decoration: none;
                margin: 0 15px;
            }}
            footer {{
                text-align: center;
                padding: 40px 0;
                color: #666;
                border-top: 1px solid #333;
            }}
        </style>
    </head>
    <body>
        <header>
            <div class="container">
                <h1>🗂️ Cortx Data Catalog</h1>
                <p class="subtitle">Semantic Layer for AI Agents</p>
                <p class="byline">by Greeshma</p>
                
                <div class="stats">
                    <div class="stat">
                        <div class="stat-value">{len(entries)}</div>
                        <div class="stat-label">Data Sources</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">{sum(e.profile.row_count for e in entries):,}</div>
                        <div class="stat-label">Total Rows</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">{sum(len(e.profile.columns) for e in entries)}</div>
                        <div class="stat-label">Columns</div>
                    </div>
                </div>
            </div>
        </header>
        
        <div class="container content">
            <div class="search-box">
                <input type="text" class="search-input" id="searchInput" 
                       placeholder="Search data sources (e.g., 'customer sales')...">
                <button class="search-btn" onclick="search()">Search</button>
            </div>
            
            <div class="download-links">
                <a href="/download/catalog.json" download>📥 Download catalog.json</a>
                <a href="/download/tool_manifest.json" download>📥 Download tool_manifest.json</a>
            </div>
            
            <div id="results"></div>
            
            <h2 style="margin: 40px 0 20px;">All Data Sources</h2>
    """
    
    for entry in entries:
        tags_html = ''.join(f'<span class="tag">{tag}</span>' for tag in entry.semantic.domain_tags)
        html += f"""
            <div class="entry">
                <div class="entry-header">
                    <h3 class="entry-title">{entry.semantic.title}</h3>
                    <span class="entry-type">{entry.source_type}</span>
                </div>
                <p class="entry-desc">{entry.semantic.description}</p>
                <div class="tags">{tags_html}</div>
                <p style="color: #666; font-size: 0.9em;">
                    📊 {entry.profile.row_count:,} rows • 
                    {len(entry.profile.columns)} columns • 
                    Sensitivity: {entry.semantic.sensitivity}
                </p>
            </div>
        """
    
    html += """
        </div>
        
        <footer>
            <div class="container">
                <p>Cortx Data Catalog &copy; 2025 | Built by Greeshma</p>
                <p style="margin-top: 10px; font-size: 0.9em;">
                    Semantic layer enabling intelligent data discovery for AI agents
                </p>
            </div>
        </footer>
        
        <script>
            async function search() {
                const query = document.getElementById('searchInput').value;
                if (!query) return;
                
                const response = await fetch('/api/search?q=' + encodeURIComponent(query));
                const data = await response.json();
                
                let html = '<h2 style="margin: 40px 0 20px;">Search Results</h2>';
                
                if (data.results.length === 0) {
                    html += '<p style="color: #888;">No results found.</p>';
                } else {
                    data.results.forEach(r => {
                        html += `
                            <div class="entry">
                                <div class="entry-header">
                                    <h3 class="entry-title">${r.metadata.title}</h3>
                                    <span class="entry-type">${(r.confidence * 100).toFixed(1)}% match</span>
                                </div>
                                <p style="color: #888;">Source: ${r.source_id}</p>
                                <div class="tags">
                                    ${r.metadata.domain_tags.map(t => `<span class="tag">${t}</span>`).join('')}
                                </div>
                            </div>
                        `;
                    });
                }
                
                document.getElementById('results').innerHTML = html;
            }
            
            document.getElementById('searchInput').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') search();
            });
        </script>
    </body>
    </html>
    """
    
    return render_template_string(html)


@app.route("/api/health")
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "catalog_loaded": builder is not None and len(builder.catalog.entries) > 0,
        "sources_count": len(builder.catalog.entries) if builder else 0,
        "mode": "render-lightweight"
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
    """Search catalog."""
    query = request.args.get("q", "")
    if not query:
        return jsonify({"query": "", "results": []})
    
    results = builder.search(query) if builder else []
    return jsonify({"query": query, "results": results})


@app.route("/download/<filename>")
def download(filename):
    """Download JSON files."""
    if filename not in ["catalog.json", "tool_manifest.json"]:
        return jsonify({"error": "File not found"}), 404
    
    filepath = Path(filename)
    if not filepath.exists():
        return jsonify({"error": "File not found"}), 404
    
    return jsonify(json.loads(filepath.read_text()))


if __name__ == "__main__":
    init_catalog()
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
