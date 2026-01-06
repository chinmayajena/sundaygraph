# SundayGraph - Agentic AI System with Ontology-Backed Graph

A production-grade Agentic AI system that transforms structured and unstructured data into an ontology-backed knowledge graph. Inspired by [LightRAG](https://github.com/HKUDS/LightRAG) and [OntoCast](https://github.com/growgraph/ontocast).

## Features

- **Multi-Format Data Ingestion**: Handles structured (JSON, CSV, XML) and unstructured (text, documents) data
- **Ontology-Driven**: Flexible ontology management with schema validation
- **Graph-Based Storage**: Efficient knowledge graph construction and querying
- **Agentic Architecture**: Modular agents for specialized tasks
- **Production-Ready**: Configurable, maintainable, and scalable design
- **High Performance**: Async processing and optimized graph operations

## Why Python?

Python was chosen for this project because:
- **AI/ML Ecosystem**: Native support for NLP libraries (spaCy, NLTK, transformers)
- **Graph Libraries**: Excellent graph processing tools (NetworkX, Neo4j drivers)
- **LLM Integration**: Seamless integration with OpenAI, Anthropic, and other LLM APIs
- **RAG Ecosystem**: Most RAG frameworks (including LightRAG) are Python-native
- **Rapid Development**: Faster prototyping and iteration for AI/ML projects
- **Community**: Largest ecosystem for AI/ML and data processing

While Go and Rust offer better performance, Python's ecosystem for AI/ML, NLP, and graph processing is unmatched, making it the pragmatic choice for this domain.

## Installation

### Using UV (Recommended)

[UV](https://github.com/astral-sh/uv) is a fast, modern Python package manager written in Rust. It's significantly faster than pip and provides better dependency resolution.

```bash
# Install UV (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh
# Or: pip install uv

# Install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### Using pip (Alternative)

```bash
# Install from pyproject.toml
pip install -e .
# Or for production
pip install .
```

### Additional Setup

Install spaCy model (optional, for NLP features):
```bash
python -m spacy download en_core_web_sm
```

## Quick Start

### Configuration

Create a `config.yaml` file:

```yaml
system:
  name: "sundaygraph"
  log_level: "INFO"
  
data:
  input_dir: "./data/input"
  output_dir: "./data/output"
  supported_formats: ["json", "csv", "txt", "xml", "pdf"]
  
ontology:
  schema_path: "./config/ontology_schema.yaml"
  auto_validate: true
  
graph:
  backend: "neo4j"  # or "memory"
  neo4j:
    uri: "bolt://localhost:7687"
    user: "neo4j"
    password: "password"
  
agents:
  data_ingestion:
    batch_size: 100
    max_workers: 4
  ontology:
    strict_mode: false
  graph_construction:
    chunk_size: 1000
    overlap: 200
```

### Basic Usage

```python
from sundaygraph import SundayGraph

# Initialize system
sg = SundayGraph(config_path="config.yaml")

# Ingest data
sg.ingest_data("path/to/data")

# Query the graph
results = sg.query("What are the main entities?")
```

### CLI Usage

```bash
# Using UV
uv run sundaygraph ingest data/input
uv run sundaygraph query "Person" --type entity

# Or activate venv first
source .venv/bin/activate
sundaygraph ingest data/input
```

## Project Structure

```
sundaygraph/
├── src/
│   ├── agents/          # Agentic components
│   ├── core/            # Core functionality
│   ├── graph/           # Graph operations
│   ├── ontology/        # Ontology management
│   └── utils/           # Utilities
├── config/              # Configuration files
├── tests/               # Test suite
├── examples/            # Example scripts
└── docs/                # Documentation
```

## Development

### With UV

```bash
# Install with dev dependencies
uv sync --dev

# Run tests
uv run pytest

# Format code
uv run black src/ tests/

# Type check
uv run mypy src/
```

### With pip

```bash
pip install -e ".[dev]"
pytest tests/
black src/ tests/
mypy src/
```

## Performance Notes

While Python may not match Go/Rust in raw performance, this system is optimized for:
- **Async I/O**: Non-blocking operations for data processing
- **Batch Processing**: Efficient batch inserts and queries
- **Caching**: Entity deduplication and result caching
- **Graph Backend**: Neo4j handles heavy graph operations efficiently

For maximum performance in production:
- Use Neo4j backend (not in-memory)
- Enable batch processing
- Use async operations
- Consider using PyPy or Cython for hot paths (if needed)

## License

MIT License
