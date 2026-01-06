# SundayGraph - Agentic AI System with Ontology-Backed Graph

A production-grade Agentic AI system that transforms structured and unstructured data into an ontology-backed knowledge graph. Inspired by [LightRAG](https://github.com/HKUDS/LightRAG) and [OntoCast](https://github.com/growgraph/ontocast).

## Features

- **Multi-Format Data Ingestion**: Handles structured (JSON, CSV, XML) and unstructured (text, documents) data
- **Ontology-Driven**: Flexible ontology management with schema validation
- **Graph-Based Storage**: Efficient knowledge graph construction and querying
- **Agentic Architecture**: Modular agents for specialized tasks
- **RESTful API**: FastAPI-based API for easy integration
- **Docker Support**: Complete Docker Compose setup with Neo4j
- **Production-Ready**: Configurable, maintainable, and scalable design
- **High Performance**: Async processing and optimized graph operations

## Technical Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Layer                             │
│  (Web UI, Mobile App, CLI, External Services)                  │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP/REST
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Layer                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  REST API Endpoints                                        │  │
│  │  - /api/v1/ingest    - Data ingestion                      │  │
│  │  - /api/v1/query     - Graph queries                       │  │
│  │  - /api/v1/entities  - Entity management                   │  │
│  │  - /api/v1/relations - Relation management                │  │
│  │  - /api/v1/stats     - System statistics                  │  │
│  │  - /health          - Health checks                        │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Orchestration Layer                            │
│                      (SundayGraph)                               │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Configuration Manager                                     │  │
│  │  - YAML-based config                                       │  │
│  │  - Environment variables                                   │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│   Data        │  │   Ontology    │  │   Graph       │
│   Ingestion   │  │   Management  │  │   Construction│
│   Agent       │  │   Agent       │  │   Agent       │
└───────┬───────┘  └───────┬───────┘  └───────┬───────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
                           ▼
                ┌──────────────────────┐
                │    Graph Store        │
                │  (Abstraction Layer)   │
                └───────────┬───────────┘
                            │
            ┌───────────────┴───────────────┐
            │                               │
            ▼                               ▼
    ┌───────────────┐              ┌───────────────┐
    │  Memory       │              │  Neo4j         │
    │  Graph Store  │              │  Graph Store    │
    │  (NetworkX)   │              │  (Production)   │
    └───────────────┘              └───────────────┘
```

### Data Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                         Data Ingestion Flow                       │
└──────────────────────────────────────────────────────────────────┘

1. Input Data (Structured/Unstructured)
   │
   ▼
2. DataIngestionAgent
   ├─ Format Detection (JSON, CSV, TXT, XML, PDF)
   ├─ File Loading
   ├─ Text Chunking (for large documents)
   └─ Metadata Extraction
   │
   ▼
3. Entity/Relation Extraction
   ├─ Entity Type Inference
   ├─ Property Extraction
   └─ Relation Discovery
   │
   ▼
4. OntologyAgent
   ├─ Schema Validation
   ├─ Property Mapping
   └─ Type Checking
   │
   ▼
5. GraphConstructionAgent
   ├─ Entity Deduplication
   ├─ Batch Insertion
   └─ Relation Creation
   │
   ▼
6. Graph Store (Memory/Neo4j)
   └─ Persistent Storage

┌──────────────────────────────────────────────────────────────────┐
│                          Query Flow                               │
└──────────────────────────────────────────────────────────────────┘

1. Query Request (REST API)
   │
   ▼
2. QueryAgent
   ├─ Query Parsing
   ├─ Query Type Detection
   └─ Query Execution
   │
   ▼
3. Graph Store
   ├─ Entity Queries
   ├─ Relation Queries
   ├─ Path Finding
   └─ Neighbor Queries
   │
   ▼
4. Result Processing
   ├─ Filtering
   ├─ Ranking
   └─ Formatting
   │
   ▼
5. Response (JSON)
```

### Component Architecture

#### 1. FastAPI Layer (`src/api/`)
- **RESTful API**: Standard HTTP endpoints for all operations
- **Request Validation**: Pydantic models for type safety
- **Error Handling**: Comprehensive error responses
- **Health Checks**: System health monitoring
- **CORS Support**: Cross-origin resource sharing
- **Auto Documentation**: OpenAPI/Swagger UI at `/docs`

#### 2. Orchestration Layer (`src/core/`)
- **SundayGraph**: Main orchestration class
- **Configuration**: Centralized config management
- **Lifecycle Management**: Startup/shutdown handling
- **Agent Coordination**: Manages all agents

#### 3. Agentic Framework (`src/agents/`)
- **DataIngestionAgent**: Handles data loading and processing
- **OntologyAgent**: Validates and maps data to ontology
- **GraphConstructionAgent**: Builds the knowledge graph
- **QueryAgent**: Executes graph queries

#### 4. Data Processing (`src/data/`)
- **Loaders**: Format-specific data loaders
- **Processor**: Text chunking and metadata extraction
- **Registry**: Extensible loader system

#### 5. Ontology Management (`src/ontology/`)
- **Schema Definition**: YAML-based ontology schemas
- **Validation**: Entity and relation validation
- **Property Mapping**: Automatic property mapping

#### 6. Graph Storage (`src/graph/`)
- **Abstraction**: Unified interface for graph operations
- **Memory Backend**: NetworkX for development/testing
- **Neo4j Backend**: Production-grade graph database

## Quick Start

### Using Docker Compose (Recommended)

The easiest way to get started is using Docker Compose:

```bash
# Start all services (API + Neo4j)
docker-compose up -d

# Check logs
docker-compose logs -f sundaygraph

# Stop services
docker-compose down
```

The API will be available at:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Neo4j Browser**: http://localhost:7474

### Local Development

#### Using UV (Recommended)

```bash
# Install UV (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate

# Start Neo4j (if using Neo4j backend)
docker-compose up -d neo4j

# Run API server
uv run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

#### Using pip

```bash
# Install dependencies
pip install -e ".[dev]"

# Start Neo4j (if using Neo4j backend)
docker-compose up -d neo4j

# Run API server
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

## API Usage

### Interactive API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Example API Calls

#### Ingest Data

```bash
curl -X POST "http://localhost:8000/api/v1/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "input_path": "data/input"
  }'
```

#### Query Entities

```bash
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Person",
    "query_type": "entity"
  }'
```

#### Add Entity

```bash
curl -X POST "http://localhost:8000/api/v1/entities" \
  -H "Content-Type: application/json" \
  -d '{
    "entity_type": "Person",
    "properties": {
      "name": "John Doe",
      "email": "john@example.com",
      "age": 30
    }
  }'
```

#### Get Statistics

```bash
curl "http://localhost:8000/api/v1/stats"
```

#### Health Check

```bash
curl "http://localhost:8000/health"
```

## Configuration

### Environment Variables

You can configure the system using environment variables:

```bash
# Graph backend
GRAPH_BACKEND=neo4j  # or "memory"

# Neo4j connection
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Logging
LOG_LEVEL=INFO
```

### Configuration File

Edit `config/config.yaml` to customize:

```yaml
graph:
  backend: "neo4j"  # or "memory"
  neo4j:
    uri: "bolt://neo4j:7687"
    user: "neo4j"
    password: "password"

agents:
  data_ingestion:
    batch_size: 100
    chunk_size: 1000
```

## Project Structure

```
sundaygraph/
├── src/
│   ├── api/              # FastAPI application
│   │   ├── app.py       # Main API application
│   │   └── main.py      # Entry point
│   ├── agents/          # Agentic components
│   ├── core/            # Core orchestration
│   ├── data/            # Data processing
│   ├── graph/           # Graph storage
│   ├── ontology/        # Ontology management
│   └── utils/           # Utilities
├── config/              # Configuration files
├── tests/               # Test suite
├── examples/            # Example scripts
├── docs/                # Documentation
├── docker-compose.yml   # Docker Compose setup
├── Dockerfile           # Application container
└── pyproject.toml       # Project dependencies
```

## Development

### Running Tests

```bash
# With UV
uv run pytest

# With pip
pytest tests/
```

### Code Formatting

```bash
# With UV
uv run black src/ tests/
uv run ruff check src/ tests/

# With pip
black src/ tests/
ruff check src/ tests/
```

### Type Checking

```bash
# With UV
uv run mypy src/

# With pip
mypy src/
```

## Deployment

### Docker Compose (Production)

```bash
# Build and start
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Docker (Standalone)

```bash
# Build image
docker build -t sundaygraph .

# Run container
docker run -p 8000:8000 \
  -v $(pwd)/config:/app/config:ro \
  -v $(pwd)/data:/app/data \
  sundaygraph
```

## Performance Considerations

- **Async I/O**: All operations use async/await for non-blocking I/O
- **Batch Processing**: Graph operations are batched for efficiency
- **Caching**: Entity deduplication and result caching
- **Graph Backend**: Neo4j handles heavy graph operations efficiently
- **Connection Pooling**: Neo4j connection pooling for better performance

## Monitoring

- **Health Endpoint**: `/health` for health checks
- **Stats Endpoint**: `/api/v1/stats` for system statistics
- **Logging**: Structured logging with loguru
- **Metrics**: Can be extended with Prometheus metrics

## License

MIT License

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

## Documentation

- [Quick Start Guide](QUICKSTART.md)
- [Usage Guide](docs/USAGE.md)
- [Architecture Documentation](docs/ARCHITECTURE.md)
- [Design Decisions](docs/DESIGN_DECISIONS.md)
