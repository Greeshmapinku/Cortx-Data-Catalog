"""Lightweight Flask app for Render deployment - NO package dependencies."""

import json
import os
from pathlib import Path
from flask import Flask, jsonify, render_template_string, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Global catalog
catalog_entries = []


def load_catalog():
    """Load catalog from pre-generated JSON."""
    global catalog_entries
    
    print("=" * 50)
    print("STARTING CORTX DATA CATALOG - RENDER MODE")
    print("=" * 50)
    
    catalog_path = "catalog.json"
    if not Path(catalog_path).exists():
        print(f"ERROR: {catalog_path} not found!")
        return []
    
    print(f"Loading catalog from {catalog_path}...")
    with open(catalog_path, "r") as f:
        data = json.load(f)
    
    catalog_entries = data.get("catalog", [])
    print(f"✓ Loaded {len(catalog_entries)} sources")
    print("=" * 50)
    
    return catalog_entries


def simple_search(query, top_k=3):
    """Simple keyword search (no embeddings)."""
    query_lower = query.lower()
    results = []
    
    for entry in catalog_entries:
        score = 0
        semantic = entry.get("semantic", {})
        text = f"{semantic.get('title', '')} {semantic.get('description', '')} {' '.join(semantic.get('domain_tags', []))}"
        text_lower = text.lower()
        
        # Simple keyword matching
        query_words = [w for w in query_lower.split() if len(w) > 2]
        for word in query_words:
            if word in text_lower:
                score += 1
        
        if score > 0:
            results.append({
                "source_id": entry.get("source_id"),
                "confidence": min(score / len(query_words), 1.0) if query_words else 0,
                "metadata": {
                    "source_id": entry.get("source_id"),
                    "source_type": entry.get("source_type"),
                    "title": semantic.get("title"),
                    "domain_tags": semantic.get("domain_tags", [])
                }
            })
    
    results.sort(key=lambda x: x["confidence"], reverse=True)
    return results[:top_k]


@app.route("/")
def index():
    """Serve the main UI."""
    total_rows = sum(e.get("profile", {}).get("row_count", 0) for e in catalog_entries)
    total_cols = sum(len(e.get("profile", {}).get("columns", [])) for e in catalog_entries)
    
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
                        <div class="stat-value">{len(catalog_entries)}</div>
                        <div class="stat-label">Data Sources</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">{total_rows:,}</div>
                        <div class="stat-label">Total Rows</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">{total_cols}</div>
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
    
    for entry in catalog_entries:
        semantic = entry.get("semantic", {})
        profile = entry.get("profile", {})
        tags = semantic.get("domain_tags", [])
        tags_html = ''.join(f'<span class="tag">{tag}</span>' for tag in tags)
        
        html += f"""
            <div class="entry">
                <div class="entry-header">
                    <h3 class="entry-title">{semantic.get('title', 'Untitled')}</h3>
                    <span class="entry-type">{entry.get('source_type', 'unknown')}</span>
                </div>
                <p class="entry-desc">{semantic.get('description', 'No description')}</p>
                <div class="tags">{tags_html}</div>
                <p style="color: #666; font-size: 0.9em;">
                    📊 {profile.get('row_count', 0):,} rows • 
                    {len(profile.get('columns', []))} columns • 
                    Sensitivity: {semantic.get('sensitivity', 'unknown')}
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
        "catalog_loaded": len(catalog_entries) > 0,
        "sources_count": len(catalog_entries),
        "mode": "render-standalone"
    })


@app.route("/api/catalog")
def get_catalog():
    """Return full catalog."""
    return jsonify({"catalog": catalog_entries})


@app.route("/api/manifest")
def get_manifest():
    """Return MCP tool manifests."""
    manifest_path = "tool_manifest.json"
    if not Path(manifest_path).exists():
        return jsonify({"error": "Manifest not found"}), 404
    
    with open(manifest_path, "r") as f:
        return jsonify(json.load(f))


@app.route("/api/search")
def search():
    """Search catalog."""
    query = request.args.get("q", "")
    if not query:
        return jsonify({"query": "", "results": []})
    
    results = simple_search(query)
    return jsonify({"query": query, "results": results})


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


# Load catalog on startup
load_catalog()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
