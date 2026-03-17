# Using Kaggle Datasets with Cortx Data Catalog

This guide shows how to download and profile datasets from Kaggle using the Cortx Data Catalog tool.

## Prerequisites

### 1. Kaggle API Setup

#### Option A: Using kaggle.json (Recommended)
1. Go to [Kaggle Account Settings](https://www.kaggle.com/settings/account)
2. Click **"Create New Token"** to download `kaggle.json`
3. Place the file in `~/.kaggle/kaggle.json`:
   ```bash
   # Linux/Mac
   mkdir -p ~/.kaggle
   mv ~/Downloads/kaggle.json ~/.kaggle/
   chmod 600 ~/.kaggle/kaggle.json
   
   # Windows
   mkdir %USERPROFILE%\.kaggle
   move %USERPROFILE%\Downloads\kaggle.json %USERPROFILE%\.kaggle\
   ```

#### Option B: Using Environment Variables
```bash
export KAGGLE_USERNAME="your_kaggle_username"
export KAGGLE_KEY="your_kaggle_api_key"
```

### 2. Install Kaggle Package

The kaggle package is already included in the project dependencies. If needed:

```bash
pip install kaggle
```

## Usage

### Using the Example Script

```bash
# Profile a Kaggle dataset with LLM annotation
python examples/kaggle_example.py --dataset ikea-product-info

# Profile without LLM (faster, no API key needed)
python examples/kaggle_example.py --dataset ikea-product-info --no-annotate

# Profile datasets with username prefix
python examples/kaggle_example.py --dataset "ahmedabbas757/fashion-product-images-small"
```

### Using CLI with Downloaded Datasets

```bash
# 1. Download dataset manually
kaggle datasets download -d ikea-product-info --unzip -p ./my_dataset

# 2. Profile with cortx-catalog-gen
cortx-catalog-gen --source csv --uri ./my_dataset/products.csv --annotate
```

## Recommended Datasets for Testing

| Dataset | Description | Columns | Rows |
|---------|-------------|---------|------|
| `ikea-product-info` | IKEA product catalog | ~10 | ~3,700 |
| `carolzhangdc/imdb-5000-movie-dataset` | IMDB movie data | ~28 | ~5,000 |
| `datasnaek/chess` | Chess game data | ~16 | ~20,000 |
| `stackoverflow/stack-overflow-developer-survey-results-2023` | Developer survey | ~80+ | ~90,000 |
| `ahmedabbas757/fashion-product-images-small` | Fashion products | ~10 | ~44,000 |

## Example Output

```
📥 Downloading dataset: ikea-product-info
✓ Downloaded to: /tmp/tmpxyz/dataset

📊 Found 1 data file(s)

🔍 Profiling: products.csv
  ✓ csv.products: 3,692 rows, 10 columns
  📌 Title: IKEA Product Catalog
  🏷️  Tags: furniture, retail, products

✅ Complete!
   Catalog: ikea-product-info_catalog.json
   Manifest: ikea-product-info_manifest.json

🔍 Try searching:
   'furniture' → csv.products (0.72)
   'price' → csv.products (0.65)
```

## Troubleshooting

### "403 Forbidden" Error
- Ensure your Kaggle account is verified with a phone number
- Check that your API token is valid (regenerate if needed)

### "Dataset not found"
- Use the full dataset path: `username/dataset-name`
- Example: `python examples/kaggle_example.py --dataset "datasnaek/chess"`

### Large Datasets
For datasets >100MB, consider:
1. Downloading manually via Kaggle website
2. Using `--no-annotate` for faster processing
3. Sampling the data first

## Advanced: Custom Kaggle Loader

You can also create a custom loader for Kaggle datasets:

```python
from cortx_catalog.catalog_builder import CatalogBuilder

# Initialize builder
builder = CatalogBuilder(annotate=True, embed=True)

# Add multiple Kaggle sources
kaggle_datasets = [
    ("csv", "./datasets/ikea/products.csv"),
    ("parquet", "./datasets/movies/movies.parquet"),
]

for source_type, path in kaggle_datasets:
    entry = builder.add_source(source_type, path)
    print(f"Added: {entry.source_id}")

# Save catalog
builder.save("my_kaggle_catalog.json")
```

## Integration with Web Demo

You can also use Kaggle datasets in the web demo:

```python
# app.py - modify init_catalog() to use Kaggle data
def init_catalog():
    global builder
    
    # Download Kaggle dataset
    from kaggle.api.kaggle_api_extended import KaggleApi
    api = KaggleApi()
    api.authenticate()
    
    demo_dir = tempfile.mkdtemp()
    api.dataset_download_files("ikea-product-info", path=demo_dir, unzip=True)
    
    # Build catalog
    builder = CatalogBuilder(annotate=True, embed=True)
    builder.add_source("csv", os.path.join(demo_dir, "products.csv"))
    
    return builder
```
