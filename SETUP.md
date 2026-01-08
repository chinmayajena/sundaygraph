# Setup and Run Instructions

## Quick Start

### Option 1: Using Docker (Recommended)

**Prerequisites:** Docker Desktop must be running

```bash
# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f sundaygraph

# Stop services
docker-compose down
```

**Access:**
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Neo4j Browser: http://localhost:7474

### Option 2: Local Development (No Docker)

**Prerequisites:** Python 3.10+ installed

#### Step 1: Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate
```

#### Step 2: Install Dependencies

```bash
# Install all dependencies
pip install -e .

# Or install minimal dependencies
pip install fastapi uvicorn[standard] pydantic pydantic-settings pyyaml loguru networkx click
```

#### Step 3: Run the Server

```bash
# Using the run script
python run_local.py

# Or directly
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

**Note:** The config is set to use `memory` backend by default for local runs (no Neo4j needed).

## Configuration

### LLM Setup (Optional)

If you want to use LLM-powered ontology reasoning:

1. Set API key as environment variable:
   ```bash
   export OPENAI_API_KEY="your-key-here"
   # or
   export ANTHROPIC_API_KEY="your-key-here"
   ```

2. Or edit `config/config.yaml`:
   ```yaml
   processing:
     llm:
       provider: "openai"  # or "anthropic"
       model: "gpt-4"
   ```

## Troubleshooting

### Docker Issues

- **Docker Desktop not running**: Start Docker Desktop application
- **Port already in use**: Change ports in `docker-compose.yml`
- **Permission errors**: Run with appropriate permissions

### Python Issues

- **Module not found**: Install dependencies with `pip install -e .`
- **Python version**: Requires Python 3.10 or higher
- **Virtual environment**: Always use a virtual environment

### API Issues

- **Connection refused**: Check if server is running on port 8000
- **Health check fails**: Check logs for errors
- **Neo4j connection**: If using Neo4j backend, ensure it's running

## Testing the API

Once the server is running:

```bash
# Health check
curl http://localhost:8000/health

# Get stats
curl http://localhost:8000/api/v1/stats

# View API docs
# Open http://localhost:8000/docs in browser
```

