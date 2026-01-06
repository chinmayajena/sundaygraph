# Architecture Documentation

## System Overview

SundayGraph is an Agentic AI system that transforms structured and unstructured data into an ontology-backed knowledge graph. The system is designed with a modular, agent-based architecture for maintainability and scalability.

## Core Components

### 1. Configuration Management (`src/core/config.py`)

- Centralized configuration using Pydantic models
- YAML-based configuration files
- Type-safe configuration with validation
- Environment variable support

### 2. Ontology Management (`src/ontology/`)

- **OntologyManager**: Loads and validates ontology schemas
- **Schema Definition**: YAML-based ontology schema with entities, relations, and constraints
- **Validation**: Entity and relation validation against schema
- **Property Mapping**: Automatic property mapping to schema

### 3. Graph Storage (`src/graph/`)

- **Abstract GraphStore**: Interface for graph operations
- **MemoryGraphStore**: In-memory graph using NetworkX
- **Neo4jGraphStore**: Neo4j database backend
- Supports entity and relation operations
- Query capabilities for entities, relations, and paths

### 4. Data Processing (`src/data/`)

- **DataLoader**: Abstract base for file loaders
- **Format Support**: JSON, CSV, TXT, XML, PDF
- **DataProcessor**: Chunking and metadata extraction
- **Extensible**: Easy to add new loaders

### 5. Agentic Framework (`src/agents/`)

#### DataIngestionAgent
- Processes files and directories
- Handles multiple data formats
- Chunks large documents
- Extracts metadata

#### OntologyAgent
- Validates entities and relations
- Maps properties to schema
- Suggests entity types
- Enforces ontology constraints

#### GraphConstructionAgent
- Adds entities to graph
- Creates relations
- Handles deduplication
- Batch processing

#### QueryAgent
- Entity queries
- Relation queries
- Neighbor queries
- Path finding

### 6. Main Orchestration (`src/core/sundaygraph.py`)

- **SundayGraph**: Main class that orchestrates all components
- Coordinates agents
- Manages data flow
- Provides high-level API

## Data Flow

```
Input Data
    ↓
DataIngestionAgent (chunking, processing)
    ↓
Entity/Relation Extraction
    ↓
OntologyAgent (validation, mapping)
    ↓
GraphConstructionAgent (graph building)
    ↓
GraphStore (persistence)
    ↓
QueryAgent (retrieval)
```

## Extension Points

### Adding New Data Loaders

1. Create a class inheriting from `DataLoader`
2. Implement `load()` and `can_load()` methods
3. Register with `DataLoaderRegistry`

### Adding New Graph Backends

1. Create a class inheriting from `GraphStore`
2. Implement all abstract methods
3. Add configuration in `Config` class
4. Update `_create_graph_store()` in `SundayGraph`

### Adding New Agents

1. Create a class inheriting from `BaseAgent`
2. Implement `process()` method
3. Add configuration in `Config` class
4. Initialize in `SundayGraph.__init__()`

## Performance Considerations

- **Async Processing**: Agents use async/await for concurrent operations
- **Batch Processing**: Graph construction supports batch inserts
- **Caching**: Entity deduplication uses caching
- **Lazy Loading**: Components initialized on demand

## Scalability

- **Horizontal Scaling**: Stateless agents can run in parallel
- **Graph Backend**: Neo4j supports distributed deployments
- **Chunking**: Large documents are processed in chunks
- **Streaming**: Can be extended for streaming data ingestion

