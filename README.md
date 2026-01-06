# SundayGraph - Agentic AI System with Ontology-Backed Graph

A production-grade Agentic AI system that transforms structured and unstructured data into an ontology-backed knowledge graph. Inspired by [LightRAG](https://github.com/HKUDS/LightRAG) and [OntoCast](https://github.com/growgraph/ontocast).

## Features

- **Multi-Format Data Ingestion**: Handles structured (JSON, CSV, XML) and unstructured (text, documents) data
- **LLM-Powered Ontology Reasoning**: Uses thinking LLMs for intelligent entity extraction, relation discovery, and ontology mapping
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
│   Ingestion   │  │   Agent       │  │   Construction│
│   Agent       │  │  (LLM-Powered)│  │   Agent       │
└───────┬───────┘  └───────┬───────┘  └───────┬───────┘
        │                  │                  │
        │                  ▼                  │
        │          ┌──────────────┐           │
        │          │  LLM Service │           │
        │          │  (Thinking)  │           │
        │          └──────────────┘           │
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

### Data Flow with LLM Reasoning

```
┌──────────────────────────────────────────────────────────────────┐
│                    Data Ingestion Flow                            │
│                  (with LLM-Powered Reasoning)                    │
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
3. LLM-Powered Entity/Relation Extraction
   ├─ LLM Service (Thinking Mode)
   │  ├─ Entity Type Inference
   │  ├─ Property Mapping
   │  └─ Relation Discovery
   ├─ Ontology Schema Context
   └─ Semantic Reasoning
   │
   ▼
4. OntologyAgent (with LLM Reasoning)
   ├─ LLM-based Validation
   ├─ Intelligent Property Mapping
   ├─ Semantic Correctness Check
   └─ Schema Validation
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
```

### LLM-Powered Features

The system uses **thinking LLMs** for:

1. **Intelligent Entity Extraction**
   - Infers entity types from unstructured data
   - Maps properties to ontology schema
   - Suggests missing properties

2. **Semantic Relation Discovery**
   - Identifies relationships between entities
   - Validates relation semantic correctness
   - Suggests appropriate relation types

3. **Ontology Reasoning**
   - Validates entities against schema with reasoning
   - Maps properties intelligently
   - Suggests ontology improvements

4. **Context-Aware Processing**
   - Uses context for better entity extraction
   - Understands domain-specific terminology
   - Adapts to different data sources

## Quick Start

### Using Docker Compose (Recommended)

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

### Configuration

Set up LLM provider in `config/config.yaml`:

```yaml
processing:
  llm:
    provider: "openai"  # or "anthropic", "local"
    model: "gpt-4"
    temperature: 0.7
    max_tokens: 2000

agents:
  ontology:
    use_llm_reasoning: true  # Enable LLM-powered reasoning
```

Set environment variables for API keys:
```bash
export OPENAI_API_KEY="your-key-here"
# or
export ANTHROPIC_API_KEY="your-key-here"
```

## Architecture Decision: Monolithic vs Microservices

### Why Monolithic for This System?

SundayGraph uses a **monolithic architecture with modular agents** because:

1. **AI/ML Ecosystem Unity**: All components (LLMs, NLP, graph processing) are Python-native
2. **Shared Context**: Agents share LLM instances, embeddings, and models efficiently
3. **Performance**: In-process communication is faster than network calls
4. **Simplicity**: Easier to develop, test, and deploy
5. **Resource Efficiency**: Models loaded once, shared across agents

### When Microservices Make Sense

Microservices are beneficial when:
- Different technology stacks are needed
- Independent scaling is required
- Team boundaries exist
- Fault isolation is critical

**See [docs/MICROSERVICES.md](docs/MICROSERVICES.md) for detailed analysis and migration guide.**

## API Usage

### Interactive API Documentation

Visit http://localhost:8000/docs for interactive API documentation.

### Example: Ingest Data with LLM Reasoning

```bash
curl -X POST "http://localhost:8000/api/v1/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "input_path": "data/input"
  }'
```

The system will automatically use LLM reasoning to:
- Extract entities intelligently
- Map properties to ontology
- Discover relations
- Validate semantic correctness

## Project Structure

```
sundaygraph/
├── src/
│   ├── api/              # FastAPI application
│   ├── agents/          # Agentic components
│   │   └── ontology_agent.py  # LLM-powered ontology agent
│   ├── core/            # Core orchestration
│   ├── data/            # Data processing
│   ├── graph/           # Graph storage
│   ├── ontology/        # Ontology management
│   └── utils/          # Utilities
│       └── llm_service.py  # LLM service for reasoning
├── config/              # Configuration files
├── docker-compose.yml   # Docker Compose setup
└── pyproject.toml       # Project dependencies
```

## Development

### Running Tests

```bash
uv run pytest
```

### Code Formatting

```bash
uv run black src/ tests/
uv run ruff check src/ tests/
```

## License

MIT License

## Documentation

- [Usage Guide](docs/USAGE.md)
- [Architecture Documentation](docs/ARCHITECTURE.md)
- [Microservices Analysis](docs/MICROSERVICES.md)
- [Design Decisions](docs/DESIGN_DECISIONS.md)
