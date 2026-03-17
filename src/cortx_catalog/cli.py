"""CLI entry point for cortx-catalog-gen."""

import os
import sys
from typing import Optional

import click
from dotenv import load_dotenv

from cortx_catalog.catalog_builder import CatalogBuilder

# Load environment variables
load_dotenv()


@click.command()
@click.option(
    "--source",
    "-s",
    type=click.Choice(["sqlite", "csv", "parquet", "postgresql", "mysql"], case_sensitive=False),
    required=True,
    help="Type of data source",
)
@click.option(
    "--uri",
    "-u",
    required=True,
    help="Connection string or file path",
)
@click.option(
    "--table",
    "-t",
    help="Table name (for database sources)",
)
@click.option(
    "--output",
    "-o",
    default="catalog.json",
    help="Output file path (default: catalog.json)",
)
@click.option(
    "--manifest",
    "-m",
    help="Separate MCP manifest output file",
)
@click.option(
    "--annotate/--no-annotate",
    default=True,
    help="Enable/disable LLM annotation (requires GROQ_API_KEY)",
)
@click.option(
    "--embed/--no-embed",
    default=True,
    help="Enable/disable embedding generation",
)
@click.option(
    "--search",
    help="Search query to test semantic search after building catalog",
)
@click.option(
    "--demo",
    is_flag=True,
    help="Run demo mode with synthetic data",
)
def main(
    source: str,
    uri: str,
    table: Optional[str],
    output: str,
    manifest: Optional[str],
    annotate: bool,
    embed: bool,
    search: Optional[str],
    demo: bool,
) -> None:
    """Cortx Data Catalog & Semantic Layer Builder.
    
    Generates semantic metadata for data sources and creates MCP tool manifests.
    
    Examples:
    
        \b
        # Profile a SQLite database
        cortx-catalog-gen --source sqlite --uri data/trading.db --table positions
        
        \b
        # Profile a CSV file
        cortx-catalog-gen --source csv --uri data/customers.csv
        
        \b
        # Run demo with synthetic data
        cortx-catalog-gen --demo
        
        \b
        # Skip LLM annotation (faster, no API key needed)
        cortx-catalog-gen --source sqlite --uri data.db --no-annotate
    """
    if demo:
        run_demo()
        return
    
    # Check for API key if annotation enabled
    if annotate and not os.getenv("GROQ_API_KEY"):
        click.echo("Warning: GROQ_API_KEY not set. Set it or use --no-annotate", err=True)
        annotate = False
    
    # Build catalog
    click.echo(f"Building catalog for {source} source: {uri}")
    
    builder = CatalogBuilder(
        annotate=annotate,
        embed=embed,
    )
    
    try:
        entry = builder.add_source(source, uri, table)
        click.echo(f"✓ Processed: {entry.source_id}")
        click.echo(f"  Rows: {entry.profile.row_count:,}")
        click.echo(f"  Columns: {len(entry.profile.columns)}")
        if annotate:
            click.echo(f"  Title: {entry.semantic.title}")
            click.echo(f"  Domain: {', '.join(entry.semantic.domain_tags)}")
        click.echo(f"  MCP Tool: {entry.mcp_tool.name}")
    except Exception as e:
        click.echo(f"Error processing source: {e}", err=True)
        sys.exit(1)
    
    # Save catalog
    builder.save(output)
    
    # Save manifest if requested
    if manifest:
        builder.save_manifest(manifest)
    
    # Test search if requested
    if search and embed:
        click.echo(f"\nSearching for: '{search}'")
        results = builder.search(search, top_k=3)
        for source_id, score, meta in results:
            click.echo(f"  {source_id}: {score:.3f} - {meta.get('title', '')}")


def run_demo() -> None:
    """Run demo mode with synthetic data."""
    from cortx_catalog.demo import create_demo_data
    
    click.echo("🚀 Running Cortx Catalog Demo\n")
    
    # Create demo data
    demo_dir = create_demo_data()
    click.echo(f"✓ Created demo data in: {demo_dir}\n")
    
    # Build catalog
    builder = CatalogBuilder(annotate=True, embed=True)
    
    sources = [
        ("sqlite", os.path.join(demo_dir, "trading.db"), "positions"),
        ("sqlite", os.path.join(demo_dir, "trading.db"), "trades"),
        ("csv", os.path.join(demo_dir, "customers.csv"), None),
        ("parquet", os.path.join(demo_dir, "products.parquet"), None),
    ]
    
    click.echo("Processing sources...")
    for source_type, uri, table in sources:
        try:
            entry = builder.add_source(source_type, uri, table)
            click.echo(f"  ✓ {entry.source_id}: {entry.profile.row_count:,} rows")
        except Exception as e:
            click.echo(f"  ✗ Error with {uri}: {e}", err=True)
    
    # Save outputs
    click.echo("\nSaving outputs...")
    builder.save("catalog.json")
    builder.save_manifest("tool_manifest.json")
    
    # Demonstrate search
    click.echo("\n🔍 Semantic Search Demo:")
    queries = [
        "trading positions and risk",
        "customer contact information",
        "product inventory",
    ]
    
    for query in queries:
        click.echo(f"\n  Query: '{query}'")
        results = builder.search(query, top_k=2)
        for source_id, score, meta in results:
            click.echo(f"    → {source_id} ({score:.3f}): {meta.get('title', '')}")
    
    click.echo("\n✅ Demo complete! Check catalog.json and tool_manifest.json")


if __name__ == "__main__":
    main()
