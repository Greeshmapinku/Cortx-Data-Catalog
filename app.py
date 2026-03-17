"""Web application for live demo hosting."""

import json
import os
import tempfile
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file, make_response
from flask_cors import CORS

from cortx_catalog.catalog_builder import CatalogBuilder
from cortx_catalog.demo import create_demo_data

app = Flask(__name__)
CORS(app)

# Global catalog builder
builder = None


def init_catalog():
    """Initialize catalog with Northwind dataset."""
    global builder
    
    # Check if pre-generated catalog exists (for deployment)
    if Path("catalog.json").exists() and os.getenv("RENDER"):
        print("Loading pre-generated catalog...")
        builder = CatalogBuilder(annotate=False, embed=False)
        
        # Load from JSON
        with open("catalog.json", "r") as f:
            data = json.load(f)
        
        # Reconstruct entries
        from cortx_catalog.models import CatalogEntry, ProfileData, SemanticData, MCPTool, ColumnProfile, MCPInputSchema
        
        for entry_data in data.get("catalog", []):
            # Parse profile
            profile = ProfileData(
                row_count=entry_data["profile"]["row_count"],
                columns=[ColumnProfile(**col) for col in entry_data["profile"]["columns"]]
            )
            
            # Parse semantic
            semantic = SemanticData(**entry_data["semantic"])
            
            # Parse MCP tool
            mcp_data = entry_data["mcp_tool"]
            mcp_tool = MCPTool(
                name=mcp_data["name"],
                description=mcp_data["description"],
                input_schema=MCPInputSchema(**mcp_data["input_schema"])
            )
            
            # Create entry
            entry = CatalogEntry(
                source_id=entry_data["source_id"],
                source_type=entry_data["source_type"],
                connection_ref=entry_data["connection_ref"],
                profile=profile,
                semantic=semantic,
                mcp_tool=mcp_tool
            )
            
            builder.catalog.add_entry(entry)
        
        print(f"✓ Loaded {len(builder.catalog.entries)} sources from catalog.json")
        return builder
    
    # Build catalog from scratch (for local development)
    builder = CatalogBuilder(annotate=True, embed=True)
    
    # Northwind dataset
    dataset_dir = "dataset/Northwind_Traders"
    sources = [
        ("csv", os.path.join(dataset_dir, "categories.csv"), None),
        ("csv", os.path.join(dataset_dir, "customers.csv"), None),
        ("csv", os.path.join(dataset_dir, "employees.csv"), None),
        ("csv", os.path.join(dataset_dir, "orders.csv"), None),
        ("csv", os.path.join(dataset_dir, "order_details.csv"), None),
        ("csv", os.path.join(dataset_dir, "products.csv"), None),
        ("csv", os.path.join(dataset_dir, "shippers.csv"), None),
    ]
    
    print("Loading Northwind Traders dataset...")
    for source_type, uri, table in sources:
        try:
            entry = builder.add_source(source_type, uri, table)
            print(f"  ✓ {entry.source_id}: {entry.profile.row_count:,} rows")
        except Exception as e:
            print(f"Warning: Could not load {uri}: {e}")
    
    return builder


@app.route("/")
def index():
    """Render main page."""
    return render_template("index.html")


@app.route("/api/catalog")
def get_catalog():
    """Get full catalog."""
    if builder is None:
        return jsonify({"error": "Catalog not initialized"}), 500
    
    data = json.loads(builder.catalog.model_dump_json())
    return jsonify({
        "catalog": data["entries"],
        "metadata": {
            "total_sources": len(data["entries"]),
            "embedding_stats": builder.embedder.get_stats() if builder.embedder else None,
        },
    })


@app.route("/api/manifest")
def get_manifest():
    """Get MCP tool manifests."""
    if builder is None:
        return jsonify({"error": "Catalog not initialized"}), 500
    
    manifests = {}
    for entry in builder.catalog.entries:
        manifests[entry.mcp_tool.name] = {
            "description": entry.mcp_tool.description,
            "input_schema": entry.mcp_tool.input_schema.model_dump(),
            "source_id": entry.source_id,
        }
    
    return jsonify(manifests)


@app.route("/api/search")
def search():
    """Search catalog."""
    if builder is None:
        return jsonify({"error": "Catalog not initialized"}), 500
    
    query = request.args.get("q", "")
    top_k = int(request.args.get("k", 3))
    
    if not query:
        return jsonify({"error": "Query parameter 'q' required"}), 400
    
    results = builder.search(query, top_k)
    
    return jsonify({
        "query": query,
        "results": [
            {
                "source_id": source_id,
                "confidence": round(score, 3),
                "metadata": meta,
            }
            for source_id, score, meta in results
        ],
    })


@app.route("/api/sources/<source_id>")
def get_source(source_id):
    """Get specific source details."""
    if builder is None:
        return jsonify({"error": "Catalog not initialized"}), 500
    
    for entry in builder.catalog.entries:
        if entry.source_id == source_id:
            return jsonify(json.loads(entry.model_dump_json()))
    
    return jsonify({"error": "Source not found"}), 404


@app.route("/api/health")
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "catalog_loaded": builder is not None,
        "sources_count": len(builder.catalog.entries) if builder else 0,
    })


@app.route("/download/<filename>")
def download_file(filename):
    """Download catalog.json or tool_manifest.json."""
    if filename not in ['catalog.json', 'tool_manifest.json']:
        return jsonify({"error": "Invalid filename"}), 400
    
    file_path = Path(filename)
    if not file_path.exists():
        return jsonify({"error": "File not found"}), 404
    
    # Read file content
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Create response with proper headers
    response = make_response(content)
    response.headers['Content-Type'] = 'application/json'
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.headers['Content-Length'] = len(content)
    return response


def create_templates():
    """Create HTML templates directory and files."""
    templates_dir = Path(__file__).parent / "templates"
    templates_dir.mkdir(exist_ok=True)
    
    html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cortx Data Catalog</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #ffffff;
            color: #000000;
            line-height: 1.6;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }
        
        .container { 
            max-width: 1200px; 
            margin: 0 auto; 
            padding: 4rem 2rem; 
        }
        
        header { 
            text-align: center; 
            margin-bottom: 4rem;
            opacity: 0;
            animation: fadeInUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }
        
        header h1 { 
            color: #000000; 
            font-size: 2.5rem; 
            font-weight: 300;
            letter-spacing: -0.02em;
            margin-bottom: 0.5rem; 
        }
        
        header .subtitle { 
            color: #666666; 
            font-size: 1rem;
            font-weight: 400;
            margin-bottom: 0.25rem;
        }
        
        header .author {
            color: #999999;
            font-size: 0.75rem;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }
        
        .grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); 
            gap: 2rem; 
        }
        
        .card {
            background: #ffffff;
            border-radius: 4px;
            padding: 2rem;
            border: 1px solid #e5e5e5;
            opacity: 0;
            animation: fadeInUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
            animation-delay: calc(var(--index, 0) * 0.1s);
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        }
        
        .card:hover {
            border-color: #000000;
            transform: translateY(-2px);
            box-shadow: 0 10px 40px -10px rgba(0,0,0,0.1);
        }
        
        .card:nth-child(1) { --index: 1; }
        .card:nth-child(2) { --index: 2; }
        .card:nth-child(3) { --index: 3; }
        .card:nth-child(4) { --index: 4; }
        
        .card h2 { 
            color: #000000; 
            margin-bottom: 1.5rem; 
            font-size: 0.875rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        
        .search-box {
            width: 100%;
            padding: 1rem 1.25rem;
            border: 1px solid #e5e5e5;
            border-radius: 0;
            background: #ffffff;
            color: #000000;
            font-size: 0.9375rem;
            margin-bottom: 1rem;
            transition: all 0.2s ease;
            outline: none;
        }
        
        .search-box:focus {
            border-color: #000000;
        }
        
        .search-box::placeholder {
            color: #999999;
        }
        
        .btn {
            background: #000000;
            color: #ffffff;
            border: none;
            padding: 1rem 2rem;
            font-size: 0.8125rem;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        }
        
        .btn:hover { 
            background: #333333;
            transform: translateY(-1px);
        }
        
        .btn:active {
            transform: translateY(0);
        }
        
        .result {
            background: #fafafa;
            padding: 1.25rem;
            margin-bottom: 0.75rem;
            border-left: 2px solid #000000;
            opacity: 0;
            animation: slideIn 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards;
            transition: all 0.2s ease;
        }
        
        .result:hover {
            background: #f5f5f5;
        }
        
        .result h4 { 
            color: #000000; 
            margin-bottom: 0.375rem;
            font-size: 0.9375rem;
            font-weight: 500;
        }
        
        .result p { 
            color: #666666; 
            font-size: 0.8125rem;
        }
        
        .result .score { 
            color: #000000; 
            font-weight: 600;
        }
        
        .tag {
            display: inline-block;
            background: #f5f5f5;
            color: #666666;
            padding: 0.375rem 0.75rem;
            font-size: 0.6875rem;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            margin-right: 0.5rem;
            margin-bottom: 0.5rem;
            transition: all 0.2s ease;
        }
        
        .tag:hover {
            background: #eeeeee;
        }
        
        .source-card {
            background: #fafafa;
            padding: 1.25rem;
            margin-bottom: 0.75rem;
            opacity: 0;
            animation: slideIn 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards;
            transition: all 0.2s ease;
        }
        
        .source-card:hover {
            background: #f5f5f5;
        }
        
        .source-card h4 { 
            color: #000000; 
            margin-bottom: 0.5rem;
            font-size: 0.9375rem;
            font-weight: 500;
        }
        
        .source-card p { 
            color: #666666; 
            font-size: 0.8125rem;
            margin-bottom: 0.75rem;
            line-height: 1.5;
        }
        
        .stats { 
            display: flex; 
            gap: 1.5rem; 
            margin-top: 0.75rem;
            padding-top: 0.75rem;
            border-top: 1px solid #e5e5e5;
        }
        
        .stat { 
            color: #999999; 
            font-size: 0.75rem;
            font-weight: 500;
        }
        
        .loading { 
            color: #666666;
            font-size: 0.8125rem;
        }
        
        .error { 
            color: #cc0000;
            font-size: 0.8125rem;
        }
        
        pre {
            background: #fafafa;
            padding: 1rem;
            overflow-x: auto;
            font-size: 0.8125rem;
            border: 1px solid #e5e5e5;
        }
        
        .endpoint {
            background: #fafafa;
            padding: 0.75rem 1rem;
            font-family: 'SF Mono', Monaco, monospace;
            font-size: 0.8125rem;
            color: #000000;
            border: 1px solid #e5e5e5;
            transition: all 0.2s ease;
        }
        
        .endpoint:hover {
            background: #f5f5f5;
            border-color: #000000;
        }
        
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateX(-10px);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }
        
        .sensitivity-public { background: #f0f0f0; color: #333; }
        .sensitivity-internal { background: #f5f5f5; color: #555; }
        .sensitivity-confidential { background: #eeeeee; color: #333; }
        .sensitivity-restricted { background: #e8e8e8; color: #333; }
        
        .manifest-card {
            cursor: pointer;
            user-select: none;
        }
        
        .manifest-card.expanded {
            background: #ffffff;
            border: 1px solid #000000;
        }
        
        .manifest-card .expand-hint {
            color: #999;
            font-size: 0.6875rem;
            margin-top: 0.5rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        
        .manifest-card.expanded .expand-hint {
            display: none;
        }
        
        .manifest-card .full-desc {
            display: none;
            margin-top: 0.75rem;
            padding-top: 0.75rem;
            border-top: 1px solid #e5e5e5;
        }
        
        .manifest-card.expanded .full-desc {
            display: block;
            animation: fadeIn 0.3s ease;
        }
        
        .manifest-card .short-desc {
            display: block;
        }
        
        .manifest-card.expanded .short-desc {
            display: none;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
    </style>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
</head>
<body>
    <div class="container">
        <header>
            <h1>Cortx Data Catalog</h1>
            <p class="subtitle">Semantic Layer Builder</p>
            <p class="author">by Greeshma</p>
        </header>
        
        <div class="grid">
            <div class="card">
                <h2>Semantic Search</h2>
                <input type="text" class="search-box" id="searchInput" 
                       placeholder="Search for data sources...">
                <button class="btn" onclick="search()">Search</button>
                <div id="searchResults" style="margin-top: 1.5rem;"></div>
            </div>
            
            <div class="card">
                <h2>Data Sources</h2>
                <div id="sourcesList"></div>
            </div>
            
            <div class="card">
                <h2>API Endpoints</h2>
                <p style="margin-bottom: 1.5rem; color: #666; font-size: 0.8125rem;">Available endpoints:</p>
                <div class="endpoint">GET /api/catalog</div>
                <div class="endpoint" style="margin-top: 0.5rem;">GET /api/manifest</div>
                <div class="endpoint" style="margin-top: 0.5rem;">GET /api/search?q=query</div>
                <div class="endpoint" style="margin-top: 0.5rem;">GET /api/health</div>
            </div>
            
            <div class="card">
                <h2>MCP Tool Manifests</h2>
                <div id="manifestList"></div>
            </div>
            
            <div class="card" style="grid-column: 1 / -1;">
                <h2>Raw JSON Outputs</h2>
                <p style="margin-bottom: 1rem; color: #666; font-size: 0.8125rem;">These JSON files are generated by the CLI tool for Cortx agent consumption:</p>
                <div style="display: flex; gap: 1rem; margin-bottom: 1rem; flex-wrap: wrap;">
                    <button class="btn" onclick="showRawJson('catalog')">View catalog.json</button>
                    <button class="btn" onclick="showRawJson('manifest')" style="background: #fff; color: #000; border: 1px solid #000;">View tool_manifest.json</button>
                    <a href="/download/catalog.json" download="catalog.json" class="btn" style="background: #333; text-decoration: none; display: inline-flex; align-items: center;">Download catalog.json</a>
                    <a href="/download/tool_manifest.json" download="tool_manifest.json" class="btn" style="background: #555; text-decoration: none; display: inline-flex; align-items: center;">Download tool_manifest.json</a>
                </div>
                <div id="rawJsonContainer" style="display: none;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                        <span id="jsonFilename" style="font-size: 0.75rem; color: #666; font-family: monospace;"></span>
                        <span style="font-size: 0.75rem; color: #999;">This is what the CLI generates</span>
                    </div>
                    <pre id="rawJsonDisplay" style="background: #fafafa; border: 1px solid #e5e5e5; padding: 1rem; overflow-x: auto; font-size: 0.75rem; max-height: 400px; overflow-y: auto;"></pre>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        async function loadSources() {
            try {
                const response = await fetch('/api/catalog');
                const data = await response.json();
                
                const container = document.getElementById('sourcesList');
                container.innerHTML = data.catalog.map((source, index) => `
                    <div class="source-card" style="animation-delay: ${index * 0.05}s">
                        <h4>${source.semantic.title}</h4>
                        <p>${source.semantic.description}</p>
                        <div>
                            ${source.semantic.domain_tags.map(t => `<span class="tag">${t}</span>`).join('')}
                            <span class="tag sensitivity-${source.semantic.sensitivity}">
                                ${source.semantic.sensitivity}
                            </span>
                        </div>
                        <div class="stats">
                            <span class="stat">${source.profile.row_count.toLocaleString()} rows</span>
                            <span class="stat">${source.source_type}</span>
                        </div>
                    </div>
                `).join('');
            } catch (error) {
                document.getElementById('sourcesList').innerHTML = '<p class="error">Failed to load sources</p>';
            }
        }
        
        async function search() {
            const query = document.getElementById('searchInput').value;
            if (!query) return;
            
            const container = document.getElementById('searchResults');
            container.innerHTML = '<p class="loading">Searching...</p>';
            
            try {
                const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
                const data = await response.json();
                
                if (data.results.length === 0) {
                    container.innerHTML = '<p style="color: #666; font-size: 0.8125rem;">No results found</p>';
                    return;
                }
                
                container.innerHTML = data.results.map((r, index) => `
                    <div class="result" style="animation-delay: ${index * 0.05}s">
                        <h4>${r.metadata.title}</h4>
                        <p>${r.metadata.source_id} | Confidence: <span class="score">${(r.confidence * 100).toFixed(1)}%</span></p>
                    </div>
                `).join('');
            } catch (error) {
                container.innerHTML = '<p class="error">Search failed</p>';
            }
        }
        
        async function loadManifests() {
            try {
                const response = await fetch('/api/manifest');
                const data = await response.json();
                
                const container = document.getElementById('manifestList');
                const tools = Object.entries(data);
                
                container.innerHTML = tools.map(([name, manifest], index) => `
                    <div class="source-card manifest-card" onclick="toggleManifest(this)" style="animation-delay: ${index * 0.05}s">
                        <h4>${name}</h4>
                        <p class="short-desc" style="font-size: 0.8125rem; color: #666;">${manifest.description.substring(0, 100)}...</p>
                        <p class="expand-hint">Click to expand</p>
                        <div class="full-desc">
                            <p style="font-size: 0.8125rem; color: #333; line-height: 1.6;">${manifest.description}</p>
                            <div style="margin-top: 1rem;">
                                <p style="font-size: 0.6875rem; color: #999; margin-bottom: 0.5rem;">INPUT SCHEMA:</p>
                                <pre style="font-size: 0.75rem;">${JSON.stringify(manifest.input_schema, null, 2)}</pre>
                            </div>
                        </div>
                    </div>
                `).join('');
            } catch (error) {
                document.getElementById('manifestList').innerHTML = '<p class="error">Failed to load manifests</p>';
            }
        }
        
        function toggleManifest(card) {
            const wasExpanded = card.classList.contains('expanded');
            
            // Collapse all other cards
            document.querySelectorAll('.manifest-card').forEach(c => c.classList.remove('expanded'));
            
            // Toggle this card
            if (!wasExpanded) {
                card.classList.add('expanded');
            }
        }
        
        let currentJsonData = null;
        let currentJsonType = null;
        
        async function showRawJson(type) {
            const container = document.getElementById('rawJsonContainer');
            const display = document.getElementById('rawJsonDisplay');
            const filename = document.getElementById('jsonFilename');
            
            try {
                if (type === 'catalog') {
                    const response = await fetch('/api/catalog');
                    currentJsonData = await response.json();
                    filename.textContent = 'catalog.json';
                    display.textContent = JSON.stringify(currentJsonData, null, 2);
                    currentJsonType = 'catalog';
                } else {
                    const response = await fetch('/api/manifest');
                    currentJsonData = await response.json();
                    filename.textContent = 'tool_manifest.json';
                    display.textContent = JSON.stringify(currentJsonData, null, 2);
                    currentJsonType = 'manifest';
                }
                container.style.display = 'block';
                container.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            } catch (error) {
                display.textContent = 'Error loading JSON: ' + error.message;
                container.style.display = 'block';
            }
        }
        
        document.getElementById('searchInput')?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') search();
        });
        
        loadSources();
        loadManifests();
    </script>
</body>
</html>'''
    
    (templates_dir / "index.html").write_text(html_content, encoding='utf-8')


if __name__ == "__main__":
    # Create templates
    create_templates()
    
    # Initialize catalog
    print("Initializing catalog with demo data...")
    init_catalog()
    print(f"✓ Loaded {len(builder.catalog.entries)} sources")
    
    # Get port from environment
    port = int(os.getenv("PORT", 5000))
    
    # Run app
    app.run(host="0.0.0.0", port=port, debug=True)
