"""Simple demo script for local testing."""

import os
import sys


def main():
    """Run the demo."""
    print("=" * 60)
    print("🚀 Cortx Data Catalog - Demo Runner")
    print("=" * 60)
    
    # Check environment
    if not os.getenv("GROQ_API_KEY"):
        print("\n⚠️  Warning: GROQ_API_KEY not set")
        print("Set it with: export GROQ_API_KEY='your-key'")
        print("Or run: set GROQ_API_KEY=your-key  (Windows)")
        print("\nContinuing without LLM annotation...\n")
    
    # Run CLI demo
    from cortx_catalog.cli import run_demo
    run_demo()
    
    print("\n" + "=" * 60)
    print("✅ Demo complete!")
    print("=" * 60)
    print("\nFiles created:")
    print("  - catalog.json         (full catalog with metadata)")
    print("  - tool_manifest.json   (MCP tool manifests)")
    print("  - demo_data/           (synthetic test data)")
    print("\nTo view the catalog:")
    print("  cat catalog.json | head -100")
    print("\nTo test semantic search, run:")
    print("  python -c \"from cortx_catalog.catalog_builder import CatalogBuilder; ...\"")


if __name__ == "__main__":
    main()
