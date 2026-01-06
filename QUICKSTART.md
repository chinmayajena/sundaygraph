# Quick Start Guide

## Installation

### Option 1: Using UV (Recommended - Fast & Modern)

[UV](https://github.com/astral-sh/uv) is a blazing-fast Python package manager written in Rust. It's 10-100x faster than pip and provides better dependency resolution.

1. **Install UV** (if not already installed):
   ```bash
   # macOS/Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # Windows (PowerShell)
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   
   # Or via pip
   pip install uv
   ```

2. **Install dependencies**:
   ```bash
   uv sync
   ```

3. **Activate virtual environment**:
   ```bash
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

### Option 2: Using pip (Alternative)

1. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```

### Additional Setup

Install spaCy model (optional, for NLP features):
```bash
python -m spacy download en_core_web_sm
```

## Basic Usage

### 1. Prepare Your Data

Place your data files in `data/input/`. Supported formats:
- JSON files
- CSV files
- Text files (.txt, .md)
- XML files
- PDF files

Example JSON file (`data/input/sample.json`):
```json
[
  {
    "type": "Person",
    "name": "John Doe",
    "email": "john@example.com",
    "age": 30
  }
]
```

### 2. Run the System

**Using Python:**
```python
import asyncio
from src import SundayGraph

async def main():
    # Initialize
    sg = SundayGraph(config_path="config/config.yaml")
    
    # Ingest data
    result = await sg.ingest_data("data/input")
    print(f"Ingested: {result}")
    
    # Query
    results = await sg.query("Person", query_type="entity")
    print(f"Found {len(results)} entities")
    
    # Get stats
    stats = await sg.get_stats()
    print(f"Graph stats: {stats['graph']}")
    
    sg.close()

asyncio.run(main())
```

**Using CLI with UV:**
```bash
# Ingest data
uv run sundaygraph ingest data/input

# Query
uv run sundaygraph query "Person" --type entity

# Get statistics
uv run sundaygraph stats
```

**Using CLI with pip:**
```bash
# Activate venv first
source .venv/bin/activate

# Then run commands
sundaygraph ingest data/input
sundaygraph query "Person" --type entity
sundaygraph stats
```

### 3. Configure the System

Edit `config/config.yaml` to customize:

- **Graph Backend**: Change `graph.backend` to `"neo4j"` for production
- **Data Processing**: Adjust chunk sizes in `agents.data_ingestion`
- **Ontology**: Point to your custom ontology schema

### 4. Customize Ontology

Edit `config/ontology_schema.yaml` to define your domain:

```yaml
entities:
  - name: "Person"
    properties:
      - name: "name"
        type: "string"
        required: true
      - name: "age"
        type: "integer"

relations:
  - name: "KNOWS"
    source: "Person"
    target: "Person"
```

## Why UV?

UV offers several advantages:
- **Speed**: 10-100x faster than pip
- **Better Resolution**: More reliable dependency resolution
- **Rust-Powered**: Written in Rust for performance
- **Modern**: Follows modern Python packaging standards
- **Compatible**: Works with existing pip workflows via pyproject.toml

## Next Steps

- Read [USAGE.md](docs/USAGE.md) for detailed usage
- Check [ARCHITECTURE.md](docs/ARCHITECTURE.md) for system design
- See [examples/](examples/) for more examples

## Troubleshooting

**Issue**: Import errors
- Solution: Make sure all dependencies are installed
  - With UV: `uv sync`
  - With pip: `pip install -e ".[dev]"`

**Issue**: Neo4j connection errors
- Solution: Use memory backend for development: Set `graph.backend: "memory"` in config

**Issue**: No data ingested
- Solution: Check file formats are supported and data structure matches expectations

**Issue**: UV command not found
- Solution: Install UV using the commands above, or use pip instead
