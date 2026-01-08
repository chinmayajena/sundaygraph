# SundayGraph - Agentic AI System with Ontology-Backed Graph

A production-grade Agentic AI system that transforms structured and unstructured data into an ontology-backed knowledge graph. Inspired by [LightRAG](https://github.com/HKUDS/LightRAG) and [OntoCast](https://github.com/growgraph/ontocast).

## Features

- **LLM-Powered Schema Building**: Automatically builds ontology schema from domain descriptions using OpenAI reasoning (OntoCast-inspired)
- **PostgreSQL Schema Storage**: Stores ontology schema metadata in PostgreSQL for versioning and evolution tracking
- **Lightweight Graph DB**: Uses in-memory/NetworkX graph for fast data hydration (LightRAG-inspired)
- **Dynamic Schema Evolution**: Automatically evolves schema based on new data patterns
- **Multi-Format Data Ingestion**: Handles structured (JSON, CSV, XML) and unstructured (text, documents) data
- **LLM-Powered Reasoning**: Uses OpenAI for intelligent entity extraction, relation discovery, and ontology mapping
- **Agentic Architecture**: Modular agents for specialized tasks
- **RESTful API**: FastAPI-based API for easy integration
- **Modern Web UI**: Next.js frontend with Tailwind CSS and shadcn/ui
- **Docker Support**: Complete Docker Compose setup with Frontend, API, PostgreSQL and Neo4j
- **Production-Ready**: Configurable, maintainable, and scalable design

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

## Technical Flow

### 1. Request Flow (API → Processing)

```
Client Request (HTTP/REST)
    │
    ▼
FastAPI Endpoint (src/api/app.py)
    ├─ Request Validation (Pydantic models)
    ├─ Authentication/Authorization (if enabled)
    └─ Route to Handler
    │
    ▼
SundayGraph Instance (src/core/sundaygraph.py)
    ├─ Load Configuration (config/config.yaml)
    ├─ Initialize Components:
    │   ├─ LLMService (if OpenAI API key set)
    │   ├─ SchemaStore (PostgreSQL, if enabled)
    │   ├─ OntologyManager (load schema from YAML/PostgreSQL)
    │   ├─ GraphStore (Memory/Neo4j based on config)
    │   └─ Agents (DataIngestion, Ontology, GraphConstruction, Query)
    └─ Execute Requested Operation
```

### 2. Schema Building Flow (OntoCast-inspired)

```
POST /api/v1/ontology/build
    │
    ▼
SundayGraph.build_schema_from_domain()
    │
    ▼
OntologySchemaBuilder.build_schema_from_domain()
    ├─ Prepare LLM Prompt with:
    │   ├─ Domain description
    │   ├─ Existing schema (if any)
    │   └─ Schema building instructions
    │
    ▼
LLMService.reason_about_ontology()
    ├─ Call OpenAI API (gpt-4)
    ├─ Generate reasoning about:
    │   ├─ Entity types needed
    │   ├─ Relations between entities
    │   ├─ Properties for each entity
    │   └─ Constraints and validations
    │
    ▼
Parse LLM Response → Ontology Schema Object
    │
    ▼
SchemaStore.save_schema() (if PostgreSQL enabled)
    ├─ Save schema to PostgreSQL
    ├─ Version tracking
    ├─ Evolution history
    └─ Return schema_id
    │
    ▼
Update OntologyManager with new schema
    │
    ▼
Return schema statistics (entities, relations, version)
```

### 3. Data Ingestion Flow (LightRAG-inspired)

```
POST /api/v1/ingest
    │
    ▼
SundayGraph.ingest_data(input_path)
    │
    ▼
[Step 1] DataIngestionAgent.process(input_path)
    ├─ Detect file format (JSON, CSV, TXT, XML, PDF)
    ├─ Load file using appropriate DataLoader
    ├─ Process directory (if path is directory)
    ├─ Chunk large documents (chunk_size, overlap)
    ├─ Extract metadata (filename, size, type)
    └─ Return: List[Dict[str, Any]] (raw_data)
    │
    ▼
[Step 2] Entity & Relation Extraction
    For each item in raw_data:
    │
    ├─ Extract Entity:
    │   ├─ SundayGraph._extract_entity_from_data()
    │   │   ├─ Infer entity type (OntologyAgent.suggest_entity_type())
    │   │   ├─ Extract properties
    │   │   └─ Generate entity ID
    │   │
    │   └─ OntologyAgent.process(entity_type, properties)
    │       ├─ [If LLM enabled] LLMService.reason_about_ontology()
    │       │   ├─ Validate entity type against schema
    │       │   ├─ Suggest property mappings
    │       │   └─ Return reasoning result
    │       │
    │       ├─ OntologyManager.validate_entity()
    │       │   ├─ Check entity type exists in schema
    │       │   ├─ Validate required properties
    │       │   └─ Check property types
    │       │
    │       └─ Map properties to schema
    │           └─ Return: (is_valid, errors, mapped_properties)
    │
    └─ Extract Relations:
        ├─ SundayGraph._extract_relations_from_data()
        │   ├─ Check for explicit relations in data
        │   ├─ Extract from content (if unstructured)
        │   └─ Generate relation objects
        │
        └─ OntologyAgent.validate_relation()
            ├─ [If LLM enabled] LLM semantic validation
            └─ OntologyManager.validate_relation()
    │
    ▼
[Step 3] GraphConstructionAgent.process(entities, relations)
    For each entity:
    │   ├─ Generate entity ID (if not provided)
    │   ├─ Check for duplicates (if deduplication enabled)
    │   │   └─ Hash properties → check cache
    │   └─ GraphStore.add_entity(entity_type, entity_id, properties)
    │
    For each relation:
    │   ├─ Validate source_id and target_id exist
    │   ├─ Check for existing relation (if merge enabled)
    │   └─ GraphStore.add_relation(relation_type, source_id, target_id, properties)
    │
    ▼
Return Statistics
    ├─ entities_added
    ├─ relations_added
    ├─ entities_skipped (duplicates)
    └─ relations_skipped
```

### 4. Query Flow

```
POST /api/v1/query
    │
    ▼
SundayGraph.query(query, query_type)
    │
    ▼
QueryAgent.process(query, query_type)
    ├─ Parse query type (entity, relation, neighbor, path)
    │
    ├─ Entity Query:
    │   └─ GraphStore.query_entities()
    │       ├─ Filter by type (if specified)
    │       ├─ Filter by properties
    │       └─ Return matching entities
    │
    ├─ Relation Query:
    │   └─ GraphStore.query_relations()
    │       ├─ Filter by relation type
    │       ├─ Filter by source/target
    │       └─ Return matching relations
    │
    ├─ Neighbor Query:
    │   └─ GraphStore.get_neighbors()
    │       ├─ Get entity neighbors
    │       ├─ Filter by relation type
    │       └─ Return neighbor entities
    │
    └─ Path Query:
        └─ GraphStore.find_path()
            ├─ Find shortest path between entities
            └─ Return path with relations
    │
    ▼
Return Query Results (List[Dict[str, Any]])
```

### 5. Component Interactions

```
┌─────────────────────────────────────────────────────────────┐
│                    Component Dependencies                    │
└─────────────────────────────────────────────────────────────┘

SundayGraph (Orchestrator)
    ├─ Config (YAML → Pydantic models)
    ├─ LLMService (OpenAI API client)
    ├─ SchemaStore (PostgreSQL connection)
    ├─ OntologyManager (Schema validation)
    ├─ GraphStore (Memory/Neo4j abstraction)
    │
    └─ Agents:
        ├─ DataIngestionAgent
        │   └─ DataProcessor
        │       └─ DataLoaders (JSON, CSV, TXT, XML, PDF)
        │
        ├─ OntologyAgent
        │   ├─ OntologyManager
        │   └─ LLMService (for reasoning)
        │
        ├─ GraphConstructionAgent
        │   └─ GraphStore
        │
        └─ QueryAgent
            └─ GraphStore

Data Flow:
    File → DataLoader → DataProcessor → DataIngestionAgent
    → Entity Extraction → OntologyAgent (validation + LLM reasoning)
    → GraphConstructionAgent → GraphStore → Persistence
```

### 6. LLM Integration Points

The system uses LLM reasoning at three key points:

1. **Schema Building** (`OntologySchemaBuilder`)
   - Input: Domain description
   - Output: Complete ontology schema (entities, relations, properties)
   - LLM: Generates schema from scratch or evolves existing schema

2. **Entity Validation** (`OntologyAgent.process()`)
   - Input: Entity type + properties
   - Output: Validated entity with mapped properties
   - LLM: Reasons about correct entity type, property mapping, semantic correctness

3. **Relation Validation** (`OntologyAgent.validate_relation()`)
   - Input: Relation type, source type, target type
   - Output: Validation result with semantic checks
   - LLM: Validates semantic correctness of relations

### 7. Storage Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Storage Layers                            │
└─────────────────────────────────────────────────────────────┘

1. Schema Storage (PostgreSQL - optional)
   ├─ Schema versions
   ├─ Evolution history
   ├─ Metadata
   └─ Used by: SchemaStore, OntologyManager

2. Graph Storage (Memory or Neo4j)
   ├─ Memory (NetworkX):
   │   ├─ Fast for development/testing
   │   ├─ In-memory only
   │   └─ No persistence (unless pickled)
   │
   └─ Neo4j (Production):
       ├─ Persistent graph database
       ├─ Scalable
       ├─ ACID transactions
       └─ Cypher query support

3. File System
   ├─ Input data: data/input/
   ├─ Output/cache: data/output/, data/cache/
   └─ Logs: logs/
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

**Prerequisites:** Docker Desktop must be running

```bash
# Start all services (Frontend + API + PostgreSQL + Neo4j)
docker-compose up -d

# Check logs
docker-compose logs -f frontend
docker-compose logs -f sundaygraph

# Stop services
docker-compose down
```

Services will be available at:
- **Frontend**: http://localhost:3000 (Next.js UI)
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432 (schema metadata)
- **Neo4j Browser**: http://localhost:7474 (optional, for large graphs)

### Local Development (No Docker)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# Run server
python run_local.py
# Or: python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

**Note:** Local runs use memory backend by default (no Neo4j needed).

See [SETUP.md](SETUP.md) for detailed setup instructions.

### Configuration

1. **Set OpenAI API Key** (required for schema building):
   
   Create a `.env` file in the project root:
   ```bash
   # .env
   OPENAI_API_KEY=your-openai-api-key-here
   ANTHROPIC_API_KEY=your-anthropic-key-here  # Optional
   ```
   
   The application will automatically load environment variables from `.env` file.
   See `.env.example` for template.

2. **Configure in `config/config.yaml`**:
```yaml
processing:
  llm:
    provider: "openai"  # Using OpenAI for all reasoning
    model: "gpt-4"
    temperature: 0.7
    max_tokens: 2000

ontology:
  build_with_llm: true  # Build schema using LLM reasoning
  store_in_postgres: true  # Store schema in PostgreSQL
  evolve_automatically: true  # Evolve schema based on data

schema_store:
  enabled: true
  host: "postgres"  # "localhost" for local dev
  database: "sundaygraph"
  user: "postgres"
  password: "password"
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

### Example: Build Schema from Domain

```bash
curl -X POST "http://localhost:8000/api/v1/ontology/build" \
  -H "Content-Type: application/json" \
  -d '{
    "domain_description": "A knowledge graph for a software company with employees, projects, and technologies"
  }'
```

### Example: Ingest Data with LLM Reasoning

```bash
curl -X POST "http://localhost:8000/api/v1/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "input_path": "data/input"
  }'
```

### Example: Evolve Schema

```bash
curl -X POST "http://localhost:8000/api/v1/ontology/evolve" \
  -H "Content-Type: application/json" \
  -d '{
    "data_sample": {"type": "Skill", "name": "Python", "level": "expert"},
    "feedback": "Need to add Skill entity type"
  }'
```

The system will automatically use LLM reasoning to:
- Extract entities intelligently
- Map properties to ontology
- Discover relations
- Validate semantic correctness

## Project Structure

### Core Source Files

```
sundaygraph/
├── src/                          # Main source code
│   ├── api/                      # FastAPI REST API
│   │   ├── app.py               # API endpoints and routes
│   │   └── main.py              # API entry point
│   │
│   ├── agents/                   # Agentic components
│   │   ├── base_agent.py        # Base agent class
│   │   ├── data_ingestion_agent.py    # Data loading & processing
│   │   ├── ontology_agent.py          # Schema validation & LLM reasoning
│   │   ├── graph_construction_agent.py # Graph building
│   │   └── query_agent.py             # Graph queries
│   │
│   ├── core/                     # Core orchestration
│   │   ├── config.py             # Configuration management (Pydantic)
│   │   └── sundaygraph.py        # Main orchestrator class
│   │
│   ├── data/                     # Data processing
│   │   ├── data_processor.py     # Chunking, metadata extraction
│   │   └── loaders.py            # File format loaders (JSON, CSV, etc.)
│   │
│   ├── graph/                     # Graph storage abstraction
│   │   └── graph_store.py        # GraphStore interface & implementations
│   │
│   ├── ontology/                  # Ontology management
│   │   ├── ontology_manager.py   # Schema loading & validation
│   │   ├── schema_builder.py     # LLM-powered schema generation
│   │   └── schema.py             # Schema data models
│   │
│   ├── storage/                   # PostgreSQL schema storage
│   │   └── schema_store.py        # Schema versioning & persistence
│   │
│   └── utils/                     # Utilities
│       ├── llm_service.py         # OpenAI/LLM integration
│       └── nlp_utils.py          # NLP helpers
│
├── config/                        # Configuration files
│   ├── config.yaml                # Main configuration
│   └── ontology_schema.yaml       # Default ontology schema
│
├── frontend/                      # Next.js frontend
│   ├── app/                       # Next.js app directory
│   ├── components/                # React components
│   └── lib/                       # API client
│
├── tests/                         # Test suite
│   ├── test_agents.py
│   ├── test_graph_store.py
│   └── test_ontology.py
│
├── data/                          # Data directories
│   ├── input/                     # Input data files
│   ├── output/                    # Output files
│   ├── cache/                     # Cache directory
│   └── seed/                      # Seed data for testing
│
├── docs/                          # Documentation
│   ├── ARCHITECTURE.md            # Architecture details
│   ├── DESIGN_DECISIONS.md        # Design rationale
│   ├── MICROSERVICES.md           # Microservices analysis
│   └── USAGE.md                   # Usage guide
│
├── docker-compose.yml             # Docker Compose setup
├── Dockerfile                     # Backend Docker image
├── pyproject.toml                 # Python dependencies
├── run_local.py                   # Local development server script
├── ingest_seed_data.py            # Seed data ingestion script
├── SETUP.md                       # Setup instructions
└── README.md                      # This file
```

### File Relevance Guide

**Essential Files (Core Functionality):**
- `src/core/sundaygraph.py` - Main orchestrator
- `src/core/config.py` - Configuration management
- `src/agents/*.py` - All agent implementations
- `src/graph/graph_store.py` - Graph storage abstraction
- `src/ontology/*.py` - Ontology management
- `src/api/app.py` - API endpoints
- `config/config.yaml` - Main configuration

**Important Files (Key Features):**
- `src/utils/llm_service.py` - LLM integration (required for schema building)
- `src/storage/schema_store.py` - PostgreSQL schema storage (optional)
- `src/data/*.py` - Data processing (required for ingestion)

**Supporting Files:**
- `run_local.py` - Development server script
- `ingest_seed_data.py` - Seed data ingestion utility
- `docker-compose.yml` - Docker setup
- `pyproject.toml` - Dependencies

**Documentation:**
- `README.md` - Main documentation (this file)
- `docs/*.md` - Detailed documentation
- `SETUP.md` - Setup instructions

**Files to Ignore (Generated/Runtime):**
- `__pycache__/` - Python bytecode (should be in .gitignore)
- `venv/` - Virtual environment (should be in .gitignore)
- `logs/` - Runtime logs (should be in .gitignore)
- `*.pyc` - Compiled Python files

**Optional/Utility Files:**
- `frontend/` - Web UI (optional, can run API-only)

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
