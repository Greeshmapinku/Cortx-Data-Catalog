"""Example: Using Kaggle datasets with Cortx Data Catalog.

This example shows how to:
1. Download datasets from Kaggle
2. Profile them with cortx-catalog-gen
3. Generate semantic metadata and MCP manifests

Setup:
    1. Get Kaggle API credentials from https://www.kaggle.com/settings/account
    2. Download kaggle.json and place it in ~/.kaggle/ (or set env vars)
    3. Or set environment variables: KAGGLE_USERNAME and KAGGLE_KEY

Usage:
    python examples/kaggle_example.py --dataset ikea-product-info
"""

import argparse
import os
import sys
import tempfile
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cortx_catalog.catalog_builder import CatalogBuilder
from kaggle.api.kaggle_api_extended import KaggleApi


def download_kaggle_dataset(dataset_slug: str, download_dir: str) -> str:
    """Download a Kaggle dataset.
    
    Args:
        dataset_slug: Dataset identifier (e.g., "ikea-product-info")
        download_dir: Directory to download files to
        
    Returns:
        Path to downloaded dataset directory
    """
    api = KaggleApi()
    api.authenticate()
    
    print(f"📥 Downloading dataset: {dataset_slug}")
    api.dataset_download_files(dataset_slug, path=download_dir, unzip=True)
    print(f"✓ Downloaded to: {download_dir}")
    
    return download_dir


def find_data_files(directory: str) -> list:
    """Find CSV and Parquet files in directory.
    
    Args:
        directory: Directory to search
        
    Returns:
        List of (file_path, file_type) tuples
    """
    data_files = []
    dir_path = Path(directory)
    
    # Look for CSV files
    for csv_file in dir_path.glob("*.csv"):
        data_files.append((str(csv_file), "csv"))
        
    # Look for Parquet files
    for parquet_file in dir_path.glob("*.parquet"):
        data_files.append((str(parquet_file), "parquet"))
    
    return data_files


def profile_kaggle_dataset(dataset_slug: str, annotate: bool = True) -> None:
    """Download and profile a Kaggle dataset.
    
    Args:
        dataset_slug: Kaggle dataset identifier
        annotate: Whether to use LLM annotation
    """
    # Create temp directory for download
    with tempfile.TemporaryDirectory() as temp_dir:
        download_dir = os.path.join(temp_dir, "dataset")
        os.makedirs(download_dir)
        
        try:
            # Download dataset
            download_kaggle_dataset(dataset_slug, download_dir)
            
            # Find data files
            data_files = find_data_files(download_dir)
            
            if not data_files:
                print("❌ No CSV or Parquet files found in dataset")
                return
            
            print(f"\n📊 Found {len(data_files)} data file(s)")
            
            # Build catalog
            builder = CatalogBuilder(annotate=annotate, embed=True)
            
            for file_path, file_type in data_files:
                print(f"\n🔍 Profiling: {os.path.basename(file_path)}")
                try:
                    entry = builder.add_source(file_type, file_path)
                    print(f"  ✓ {entry.source_id}: {entry.profile.row_count:,} rows, {len(entry.profile.columns)} columns")
                    if annotate:
                        print(f"  📌 Title: {entry.semantic.title}")
                        print(f"  🏷️  Tags: {', '.join(entry.semantic.domain_tags)}")
                except Exception as e:
                    print(f"  ❌ Error: {e}")
            
            # Generate outputs
            output_base = dataset_slug.replace("/", "_")
            catalog_path = f"{output_base}_catalog.json"
            manifest_path = f"{output_base}_manifest.json"
            
            builder.save(catalog_path)
            builder.save_manifest(manifest_path)
            
            print(f"\n✅ Complete!")
            print(f"   Catalog: {catalog_path}")
            print(f"   Manifest: {manifest_path}")
            
            # Demo search
            if annotate and len(builder.catalog.entries) > 0:
                print("\n🔍 Try searching:")
                demo_queries = ["sales", "customer", "product", "price"]
                for query in demo_queries[:3]:
                    results = builder.search(query, top_k=2)
                    if results:
                        print(f"   '{query}' → {results[0][0]} ({results[0][1]:.2f})")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            raise


def main():
    parser = argparse.ArgumentParser(
        description="Profile Kaggle datasets with Cortx Data Catalog"
    )
    parser.add_argument(
        "--dataset",
        required=True,
        help="Kaggle dataset slug (e.g., 'ikea-product-info' or 'username/dataset-name')",
    )
    parser.add_argument(
        "--no-annotate",
        action="store_true",
        help="Skip LLM annotation (faster, no API key needed)",
    )
    
    args = parser.parse_args()
    
    # Check for Kaggle credentials
    if not (os.getenv("KAGGLE_USERNAME") and os.getenv("KAGGLE_KEY")):
        kaggle_creds = Path.home() / ".kaggle" / "kaggle.json"
        if not kaggle_creds.exists():
            print("❌ Kaggle credentials not found!")
            print("\nTo set up Kaggle API access:")
            print("1. Go to https://www.kaggle.com/settings/account")
            print("2. Click 'Create New Token'")
            print("3. Place kaggle.json in ~/.kaggle/")
            print("\nOr set environment variables:")
            print("   export KAGGLE_USERNAME=your_username")
            print("   export KAGGLE_KEY=your_key")
            sys.exit(1)
    
    # Check for Groq API key if annotation enabled
    if not args.no_annotate and not os.getenv("GROQ_API_KEY"):
        print("⚠️  Warning: GROQ_API_KEY not set. Running without LLM annotation.")
        args.no_annotate = True
    
    # Run profiling
    profile_kaggle_dataset(args.dataset, annotate=not args.no_annotate)


if __name__ == "__main__":
    main()
