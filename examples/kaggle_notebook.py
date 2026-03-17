"""
# Kaggle Dataset Integration - Interactive Example
# 
# Run this in Jupyter or as a Python script to explore Kaggle datasets
# with semantic search and MCP manifest generation.

## Setup
"""

# %% [markdown]
# # 🚀 Cortx Data Catalog + Kaggle
# 
# This notebook demonstrates profiling Kaggle datasets with semantic metadata.

# %%
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path.cwd().parent / "src"))

# Check Kaggle credentials
if not (os.getenv("KAGGLE_USERNAME") and os.getenv("KAGGLE_KEY")):
    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
    if not kaggle_json.exists():
        print("⚠️  Kaggle credentials not found!")
        print("Please set up Kaggle API first (see KAGGLE_DATASETS.md)")
    else:
        print("✓ Kaggle credentials found")
else:
    print("✓ Kaggle environment variables set")

# %% [markdown]
# ## 1. Download a Dataset

# %%
from kaggle.api.kaggle_api_extended import KaggleApi

# Initialize API
api = KaggleApi()
api.authenticate()

# Choose a dataset
dataset_slug = "ikea-product-info"  # Try: "carolzhangdc/imdb-5000-movie-dataset"

print(f"📥 Downloading: {dataset_slug}")

import tempfile
download_dir = tempfile.mkdtemp()
api.dataset_download_files(dataset_slug, path=download_dir, unzip=True)

# List downloaded files
print("\n📁 Downloaded files:")
for f in Path(download_dir).glob("*"):
    print(f"  - {f.name} ({f.stat().st_size:,} bytes)")

# %% [markdown]
# ## 2. Profile the Dataset

# %%
from cortx_catalog.catalog_builder import CatalogBuilder

# Initialize builder with LLM annotation
builder = CatalogBuilder(annotate=True, embed=True)

# Find and profile data files
data_files = list(Path(download_dir).glob("*.csv")) + list(Path(download_dir).glob("*.parquet"))

for file_path in data_files:
    file_type = file_path.suffix[1:]  # csv or parquet
    print(f"\n🔍 Profiling: {file_path.name}")
    
    entry = builder.add_source(file_type, str(file_path))
    
    print(f"  📊 {entry.profile.row_count:,} rows × {len(entry.profile.columns)} columns")
    print(f"  📌 {entry.semantic.title}")
    print(f"  📝 {entry.semantic.description[:100]}...")
    print(f"  🏷️  Tags: {', '.join(entry.semantic.domain_tags)}")
    print(f"  🔐 Sensitivity: {entry.semantic.sensitivity}")

# %% [markdown]
# ## 3. Explore Column Profiles

# %%
# Show detailed column info for first source
if builder.catalog.entries:
    entry = builder.catalog.entries[0]
    print(f"\n📋 Column Profiles for '{entry.source_id}':\n")
    
    for col in entry.profile.columns:
        pii_indicator = " 🔴 PII" if col.is_pii else ""
        print(f"  {col.name:20} | {col.dtype:10} | {col.null_pct*100:5.1f}% null | {col.cardinality:,} unique{pii_indicator}")
        if col.sample_values:
            samples = str(col.sample_values[:3])[:50]
            print(f"    └─ Samples: {samples}...")

# %% [markdown]
# ## 4. Test Semantic Search

# %%
test_queries = [
    "product catalog",
    "pricing information",
    "customer data",
    "inventory management",
]

print("🔍 Semantic Search Results:\n")
for query in test_queries:
    results = builder.search(query, top_k=2)
    print(f"Query: '{query}'")
    for source_id, score, meta in results:
        print(f"  → {source_id} ({score:.2f}): {meta.get('title', '')}")
    print()

# %% [markdown]
# ## 5. View MCP Tool Manifest

# %%
if builder.catalog.entries:
    entry = builder.catalog.entries[0]
    tool = entry.mcp_tool
    
    print(f"🛠️  MCP Tool: {tool.name}\n")
    print(f"Description:\n{tool.description}\n")
    print(f"Input Schema:")
    import json
    print(json.dumps(tool.input_schema.model_dump(), indent=2))

# %% [markdown]
# ## 6. Save Outputs

# %%
output_name = dataset_slug.replace("/", "_")

catalog_file = f"{output_name}_catalog.json"
manifest_file = f"{output_name}_manifest.json"

builder.save(catalog_file)
builder.save_manifest(manifest_file)

print(f"✅ Saved:")
print(f"   Catalog: {catalog_file}")
print(f"   Manifest: {manifest_file}")

# %% [markdown]
# ## 7. Export for Analysis

# %%
import pandas as pd

# Create summary DataFrame
summary_data = []
for entry in builder.catalog.entries:
    summary_data.append({
        "source_id": entry.source_id,
        "title": entry.semantic.title,
        "rows": entry.profile.row_count,
        "columns": len(entry.profile.columns),
        "sensitivity": entry.semantic.sensitivity,
        "domain_tags": ", ".join(entry.semantic.domain_tags),
    })

df_summary = pd.DataFrame(summary_data)
print("\n📊 Dataset Summary:")
print(df_summary.to_string(index=False))

# %% [markdown]
# ## Next Steps
# 
# - Explore other datasets: [Kaggle Datasets](https://www.kaggle.com/datasets)
# - Try the web demo: `python app.py`
# - Use the CLI: `cortx-catalog-gen --help`
