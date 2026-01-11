# Quick Start Guide

**SemanticOps for Snowflake Semantic Views + Cortex Analyst reliability**

This guide will help you get started with SundayGraph and deploy your first Snowflake semantic view in minutes.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Start Services](#start-services)
5. [Quickstart: Deploy Your First Semantic View](#quickstart-deploy-your-first-semantic-view)
6. [Using the Web UI](#using-the-web-ui)
7. [Using the CLI](#using-the-cli)
8. [Using the API](#using-the-api)
9. [Troubleshooting](#troubleshooting)
10. [Next Steps](#next-steps)

## Prerequisites

### Required

- **Python 3.10+** (check with `python --version`)
- **PostgreSQL 12+** (or use Docker)
- **OpenAI API Key** (for LLM-powered ODL generation)
- **Git** (for cloning the repository)

### Optional (for Snowflake Integration)

- **Snowflake Account** with Cortex Analyst enabled
- **Snowflake Connection Credentials**:
  - Account URL
  - User credentials
  - Warehouse, Database, Schema
  - Role (optional)

### Optional (for Development)

- **Docker and Docker Compose** (for containerized deployment)
- **Node.js 18+** (for frontend development)

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd sundaygraph
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Install the package with development dependencies
pip install -e ".[dev]"
```

### 4. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your settings
# Required:
#   OPENAI_API_KEY=your-openai-api-key-here
#   DATABASE_URL=postgresql://user:password@localhost:5432/sundaygraph
# Optional (for Snowflake):
#   SNOWFLAKE_ACCOUNT_URL=your-account.snowflakecomputing.com
#   SNOWFLAKE_USER=your-user
#   SNOWFLAKE_PASSWORD=your-password
#   SNOWFLAKE_WAREHOUSE=your-warehouse
#   SNOWFLAKE_DATABASE=your-database
#   SNOWFLAKE_SCHEMA=your-schema
```

### 5. Database Setup

**Option A: Using Docker (Recommended)**

```bash
# Start PostgreSQL container
docker-compose up -d postgres

# Wait a few seconds for PostgreSQL to initialize
sleep 5
```

**Option B: Using Local PostgreSQL**

```bash
# Create database
createdb sundaygraph
# Or using psql:
# psql -U postgres -c "CREATE DATABASE sundaygraph;"
```

**Run Migrations**

```bash
# Apply database migrations
python migrations/run_migrations.py
```

This creates the following tables:
- `workspace`
- `ontology`
- `ontology_version`
- `compile_run`
- `eval_run`
- `drift_event`
- `cortex_regression_run`
- `ontology_diff`

## Configuration

### Environment Variables (.env)

The `.env` file supports the following variables:

```bash
# LLM Configuration (Required)
OPENAI_API_KEY=sk-...

# Database Configuration (Required)
DATABASE_URL=postgresql://user:password@localhost:5432/sundaygraph

# Snowflake Configuration (Optional)
SNOWFLAKE_ACCOUNT_URL=your-account.snowflakecomputing.com
SNOWFLAKE_USER=your-user
SNOWFLAKE_PASSWORD=your-password
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=MY_DB
SNOWFLAKE_SCHEMA=MY_SCHEMA
SNOWFLAKE_ROLE=MY_ROLE  # Optional

# Task Queue Configuration (Optional)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Application Configuration (Optional)
API_PORT=8000
LOG_LEVEL=INFO
```

### Application Configuration (config/config.yaml)

For advanced configuration, edit `config/config.yaml`:

```yaml
# Graph backend (optional, not required for Snowflake)
graph:
  backend: "memory"  # or "oxigraph"
  oxigraph:
    sparql_endpoint: "http://localhost:7878/query"
    update_endpoint: "http://localhost:7878/update"

# LLM Configuration
llm:
  provider: "openai"
  model: "gpt-4"
  temperature: 0.7
  max_tokens: 2000

# Task Queue (optional)
task_queue:
  enabled: false
  backend: "celery"  # or "temporal"
```

## Start Services

### Option A: Docker Compose (Recommended for Production)

```bash
# Start all services (backend, frontend, PostgreSQL, Oxigraph)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

Services will be available at:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### Option B: Local Development

**Terminal 1: Start Backend**

```bash
# Activate virtual environment (if not already active)
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Start backend server
python run_local.py
```

**Terminal 2: Start Frontend (Optional)**

```bash
cd frontend
npm install
npm run dev
```

Access the application:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Quickstart: Deploy Your First Semantic View

This section walks you through creating and deploying a Snowflake semantic view from scratch.

### Step 1: Create ODL (Ontology Definition Language)

**Option A: Generate ODL from Domain Description (LLM-Powered)**

```bash
curl -X POST "http://localhost:8000/api/v1/workspaces/standard/build-ontology?username=admin" \
  -H "Content-Type: application/json" \
  -d '{
    "domain_description": "E-commerce system with customers, orders, products, and order items. Customers place orders. Orders contain order items. Each order item references a product."
  }'
```

**Option B: Create ODL Manually**

Create a file `my_domain.odl.json`:

```json
{
  "version": "1.0",
  "name": "E-commerce Domain",
  "description": "E-commerce semantic model",
  "objects": [
    {
      "name": "Customer",
      "description": "Customer entity",
      "identifiers": ["customer_id"],
      "properties": [
        {"name": "customer_id", "type": "string", "description": "Unique customer identifier"},
        {"name": "name", "type": "string", "description": "Customer name"},
        {"name": "email", "type": "string", "description": "Customer email"}
      ]
    },
    {
      "name": "Order",
      "description": "Order entity",
      "identifiers": ["order_id"],
      "properties": [
        {"name": "order_id", "type": "string", "description": "Unique order identifier"},
        {"name": "customer_id", "type": "string", "description": "Customer identifier"},
        {"name": "order_date", "type": "date", "description": "Order date"},
        {"name": "total_amount", "type": "decimal", "description": "Order total"}
      ]
    }
  ],
  "relationships": [
    {
      "name": "placed_by",
      "from": "Order",
      "to": "Customer",
      "join_keys": {
        "Order": ["customer_id"],
        "Customer": ["customer_id"]
      },
      "cardinality": "many_to_one"
    }
  ],
  "metrics": [
    {
      "name": "total_revenue",
      "expression": "SUM(Order.total_amount)",
      "grain": ["Order"],
      "description": "Total revenue from orders"
    }
  ],
  "snowflake": {
    "database": "MY_DB",
    "schema": "MY_SCHEMA",
    "warehouse": "COMPUTE_WH",
    "mappings": {
      "Customer": {"table": "customers"},
      "Order": {"table": "orders"}
    }
  }
}
```

Then upload it via API:

```bash
curl -X POST "http://localhost:8000/api/v1/workspaces/standard/ontology/ecommerce" \
  -H "Content-Type: application/json" \
  -d @my_domain.odl.json
```

**Option C: Upload Data Files and Generate ODL**

```bash
# 1. Upload files to workspace
curl -X POST "http://localhost:8000/api/v1/workspaces/standard/files/upload" \
  -F "file=@customers.csv" \
  -F "file=@orders.csv"

# 2. Build ontology from files
curl -X POST "http://localhost:8000/api/v1/workspaces/standard/build-ontology?username=admin" \
  -H "Content-Type: application/json" \
  -d '{
    "filenames": ["customers.csv", "orders.csv"]
  }'
```

### Step 2: Evaluate ODL

Before compiling, evaluate the ODL for issues:

```bash
curl -X POST "http://localhost:8000/api/v1/workspaces/standard/ontology/ecommerce/versions/{version_id}/eval" \
  -H "Content-Type: application/json" \
  -d '{
    "threshold_profile": "strict"
  }'
```

Response:
```json
{
  "passed": true,
  "metrics": {
    "structural": {"passed": true, "errors": []},
    "semantic": {"passed": true, "errors": []},
    "deployability": {"passed": true, "errors": []}
  }
}
```

### Step 3: Compile to Snowflake Semantic Model

Compile the ODL to Snowflake semantic model YAML:

```bash
curl -X POST "http://localhost:8000/api/v1/workspaces/standard/ontology/ecommerce/versions/{version_id}/compile" \
  -H "Content-Type: application/json" \
  -d '{
    "target": "SNOWFLAKE",
    "options": {}
  }'
```

Response:
```json
{
  "compile_run_id": "123",
  "status": "completed",
  "artifact_path": "/path/to/artifact-bundle.zip",
  "files": [
    {"path": "semantic_model.yaml", "content": "..."},
    {"path": "verify.sql", "content": "..."},
    {"path": "deploy.sql", "content": "..."}
  ]
}
```

### Step 4: Verify Semantic Model

Verify the generated semantic model with Snowflake (dry-run):

```bash
# The verify.sql is generated in Step 3
# Execute it in Snowflake:
# CALL SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML(
#   'MY_DB.MY_SCHEMA',
#   $$<semantic_model_yaml>$$,
#   verify_only => TRUE
# );
```

Or use the API (if Snowflake credentials are configured):

```bash
curl -X POST "http://localhost:8000/api/v1/snowflake/verify" \
  -H "Content-Type: application/json" \
  -d '{
    "semantic_model_yaml": "...",
    "workspace_id": "standard"
  }'
```

### Step 5: Deploy to Snowflake

If verification passes, deploy the semantic view:

```bash
# Execute deploy.sql from the artifact bundle
# Or use the API:
curl -X POST "http://localhost:8000/api/v1/snowflake/deploy" \
  -H "Content-Type: application/json" \
  -d '{
    "semantic_model_yaml": "...",
    "view_name": "ecommerce_semantic",
    "workspace_id": "standard"
  }'
```

This creates the semantic view in Snowflake:
```sql
CALL SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML(
  'MY_DB.MY_SCHEMA.ecommerce_semantic',
  $$<semantic_model_yaml>$$
);
```

### Step 6: Run Cortex Analyst Regression Tests

Test the semantic view with Cortex Analyst:

```bash
# Create golden_questions.yaml
cat > golden_questions.yaml << EOF
questions:
  - question: "What are the top 10 customers by order value?"
    expected_tables: ["Customer", "Order"]
    expected_sql_patterns: ["SUM", "ORDER BY", "LIMIT"]
  - question: "Show me customers who haven't placed orders in the last 30 days"
    expected_tables: ["Customer", "Order"]
EOF

# Run regression tests
sundaygraph snowflake cortex-regress \
  --semantic-view MY_DB.MY_SCHEMA.ecommerce_semantic \
  --questions golden_questions.yaml
```

Or via API:

```bash
curl -X POST "http://localhost:8000/api/v1/workspaces/standard/ontology/ecommerce/versions/{version_id}/cortex-regress" \
  -H "Content-Type: application/json" \
  -d '{
    "semantic_view": "MY_DB.MY_SCHEMA.ecommerce_semantic",
    "questions_file": "golden_questions.yaml"
  }'
```

### Step 7: Monitor Drift (Continuous)

Detect schema drift and semantic view drift:

```bash
curl -X POST "http://localhost:8000/api/v1/workspaces/standard/ontology/ecommerce/versions/{version_id}/detect-drift" \
  -H "Content-Type: application/json"
```

Response:
```json
{
  "mapping_drift": [
    {
      "type": "column_renamed",
      "object": "Customer",
      "old_column": "customer_name",
      "new_column": "name",
      "status": "detected"
    }
  ],
  "semantic_view_drift": []
}
```

## Using the Web UI

### 1. Access the Web UI

Navigate to http://localhost:3000 in your browser.

### 2. Create a Workspace

- Click "Create Workspace" or use the default workspace
- Workspace ID: `standard` (or create a custom one)

### 3. Upload Files

- Navigate to the Files page
- Click "Upload Files"
- Select CSV, JSON, PDF, or text files
- Files are stored in `data/workspaces/{workspace_id}/files/`

### 4. Ingest Files

- Select files to ingest
- Click "Ingest All Files"
- The system will:
  - Analyze file structure
  - Generate extraction code (CodeAct approach)
  - Extract entities and relationships
  - Build graph (optional)

### 5. Build Ontology

- Click "Build Ontology from Files"
- The system will:
  - Analyze file contents
  - Generate ODL using LLM
  - Store ODL in database

### 6. Compile and Deploy

- Navigate to Ontology page
- Select an ontology version
- Click "Compile" to generate Snowflake artifacts
- Click "Deploy" to deploy to Snowflake (if configured)

## Using the CLI

### Install CLI

The CLI is installed automatically with the package:

```bash
# Verify installation
sundaygraph --help
```

### ODL Commands

```bash
# Validate ODL file
sundaygraph odl validate odl/examples/snowflake_retail.odl.json

# Normalize ODL
sundaygraph odl normalize odl/examples/snowflake_retail.odl.json
```

### Snowflake Commands

```bash
# Export YAML from existing semantic view
sundaygraph snowflake export-yaml \
  --semantic-view MY_DB.MY_SCHEMA.my_semantic_view \
  --out exported.yaml

# Run Cortex Analyst regression tests
sundaygraph snowflake cortex-regress \
  --semantic-view MY_DB.MY_SCHEMA.my_semantic_view \
  --questions golden_questions.yaml

# Generate promotion bundle
sundaygraph snowflake promotion-bundle \
  --odl-file my_domain.odl.json \
  --environments examples/environments.json \
  --out promotion-bundle.zip
```

## Using the API

### Interactive API Documentation

Visit http://localhost:8000/docs for interactive Swagger UI documentation.

### Common API Endpoints

**Workspace Management**

```bash
# List workspaces
curl http://localhost:8000/api/v1/workspaces

# Get workspace details
curl http://localhost:8000/api/v1/workspaces/standard
```

**File Management**

```bash
# Upload file
curl -X POST "http://localhost:8000/api/v1/workspaces/standard/files/upload" \
  -F "file=@data.csv"

# List files
curl http://localhost:8000/api/v1/workspaces/standard/files

# Get file content
curl http://localhost:8000/api/v1/workspaces/standard/files/data.csv
```

**ODL Management**

```bash
# Create ontology
curl -X POST "http://localhost:8000/api/v1/workspaces/standard/ontology/ecommerce" \
  -H "Content-Type: application/json" \
  -d @my_domain.odl.json

# List ontology versions
curl http://localhost:8000/api/v1/workspaces/standard/ontology/ecommerce/versions

# Get ODL diff
curl "http://localhost:8000/api/v1/workspaces/standard/ontology/ecommerce/versions/{vid}/diff?against={old_vid}"
```

**Task Status**

```bash
# Get task status
curl http://localhost:8000/api/v1/tasks/{task_id}
```

## Troubleshooting

### Database Connection Issues

**Problem**: Cannot connect to PostgreSQL

**Solutions**:
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Verify DATABASE_URL in .env
echo $DATABASE_URL

# Test connection
psql $DATABASE_URL -c "SELECT 1;"

# Re-run migrations
python migrations/run_migrations.py
```

### Port Already in Use

**Problem**: Port 8000 or 3000 is already in use

**Solutions**:
```bash
# Find process using port 8000
# On Linux/Mac:
lsof -i :8000
# On Windows:
netstat -ano | findstr :8000

# Kill process (replace PID)
# On Linux/Mac:
kill -9 <PID>
# On Windows:
taskkill /PID <PID> /F

# Or change port in .env
API_PORT=8001
```

### Missing Dependencies

**Problem**: Import errors or missing modules

**Solutions**:
```bash
# Reinstall dependencies
pip install -e ".[dev]"

# Check Python version
python --version  # Should be 3.10+

# Verify virtual environment is activated
which python  # Should point to venv/bin/python
```

### LLM API Errors

**Problem**: OpenAI API errors

**Solutions**:
```bash
# Verify API key in .env
grep OPENAI_API_KEY .env

# Check API quota/limits
# Visit https://platform.openai.com/usage

# Review logs
tail -f logs/*.log
```

### Snowflake Connection Issues

**Problem**: Cannot connect to Snowflake

**Solutions**:
```bash
# Verify Snowflake credentials in .env
grep SNOWFLAKE .env

# Test connection manually
snowsql -a <account> -u <user> -w <warehouse> -d <database> -s <schema>

# Check network connectivity
ping <account>.snowflakecomputing.com
```

### Migration Errors

**Problem**: Database migration fails

**Solutions**:
```bash
# Check database exists
psql $DATABASE_URL -c "\l"

# Check existing tables
psql $DATABASE_URL -c "\dt"

# Re-run migrations (idempotent)
python migrations/run_migrations.py
```

## Next Steps

### Learn More

- **README.md**: Complete project documentation (includes architecture diagrams)
- **docs/PROMOTION_BUNDLE.md**: Multi-environment deployment
- **docs/SNOWFLAKE_EXPORT.md**: Exporting from Snowflake
- **docs/README.md**: Documentation index
- **odl/README.md**: ODL specification
- **examples/README.md**: Example files and configurations

### Advanced Features

1. **Task Queue**: Enable Celery or Temporal for async processing
   ```yaml
   # config/config.yaml
   task_queue:
     enabled: true
     backend: "celery"
   ```

2. **Graph Storage**: Enable Oxigraph for graph exploration
   ```yaml
   # config/config.yaml
   graph:
     backend: "oxigraph"
   ```

3. **CI/CD Integration**: Use GitHub Actions workflow
   - See `.github/workflows/semantic-ci.yml`
   - Configure secrets for Snowflake credentials

4. **Promotion Bundles**: Generate environment-specific deployment packages
   ```bash
   sundaygraph snowflake promotion-bundle \
     --odl-file my_domain.odl.json \
     --environments examples/environments.json \
     --out promotion-bundle.zip
   ```

### Development

- **Code Style**: Follow `.cursorrules` for development guidelines
- **Testing**: Run tests with `pytest`
- **Contributing**: Check project structure in `README.md`

### Support

- **Issues**: Report issues on GitHub
- **Documentation**: Check `docs/` directory
- **Examples**: See `odl/examples/` for ODL examples

---

**Congratulations!** You've successfully set up SundayGraph and deployed your first Snowflake semantic view. 🎉
