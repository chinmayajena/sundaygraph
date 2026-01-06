# Usage Guide

## Installation

```bash
# Install dependencies
# Using UV (recommended)
uv sync

# Or using pip
pip install -e ".[dev]"

# Install spaCy model (optional, for NLP features)
python -m spacy download en_core_web_sm
```

## Basic Usage

### Python API

```python
from src import SundayGraph

# Initialize
sg = SundayGraph(config_path="config/config.yaml")

# Ingest data
await sg.ingest_data("data/input")

# Query
results = await sg.query("Person", query_type="entity")

# Get statistics
stats = await sg.get_stats()

# Cleanup
sg.close()
```

### Command Line Interface

```bash
# Ingest data
sundaygraph ingest data/input

# Query
sundaygraph query "Person" --type entity

# Get statistics
sundaygraph stats

# Clear graph
sundaygraph clear
```

## Configuration

Edit `config/config.yaml` to customize:

- **Graph Backend**: Choose between "memory" or "neo4j"
- **Data Processing**: Adjust chunk sizes and batch sizes
- **Ontology**: Point to custom ontology schema
- **Agents**: Enable/disable and configure agents

## Data Formats

### Supported Formats

- **JSON**: Structured data
- **CSV**: Tabular data
- **TXT/MD**: Plain text documents
- **XML**: Structured XML documents
- **PDF**: PDF documents (requires pypdf)

### Data Structure

For structured data (JSON, CSV), the system expects:

```json
{
  "type": "Person",
  "name": "John Doe",
  "email": "john@example.com",
  "relations": [
    {
      "type": "WORKS_FOR",
      "target": "org1"
    }
  ]
}
```

## Ontology Schema

Define your ontology in `config/ontology_schema.yaml`:

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
  - name: "WORKS_FOR"
    source: "Person"
    target: "Organization"
```

## Advanced Usage

### Custom Data Loader

```python
from src.data.loaders import DataLoader
from pathlib import Path

class CustomLoader(DataLoader):
    def load(self, file_path: Path):
        # Your loading logic
        return data
    
    def can_load(self, file_path: Path):
        return file_path.suffix == ".custom"

# Register
from src.data.loaders import DataLoaderRegistry
registry = DataLoaderRegistry()
registry.register(CustomLoader())
```

### Custom Agent

```python
from src.agents.base_agent import BaseAgent

class CustomAgent(BaseAgent):
    async def process(self, *args, **kwargs):
        # Your processing logic
        return result
```

## Best Practices

1. **Start with Memory Backend**: Use memory backend for development
2. **Use Neo4j for Production**: Switch to Neo4j for large-scale deployments
3. **Validate Data**: Enable strict mode for production
4. **Monitor Performance**: Use stats() to monitor graph growth
5. **Backup Regularly**: Enable backup in configuration

