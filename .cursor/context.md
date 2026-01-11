# SundayGraph Project Context

This file provides additional context for Cursor IDE about the SundayGraph project.

## Project Purpose

SundayGraph is an agentic AI system that transforms structured and unstructured data into ontology-backed knowledge graphs. The key innovation is using CodeAct-style extraction where LLMs generate Python code once per file type, then execute on all rows (99%+ cost reduction vs per-row LLM calls).

## Key Architectural Decisions

1. **CodeAct Over Per-Row LLM Calls**: Never call LLM per row. Always use schema inference → code generation → execution pattern.

2. **Workspace Isolation**: All graph operations are workspace-scoped. Every function that touches the graph must accept `workspace_id`.

3. **Abstraction Layers**: Graph stores, task queues, and data loaders are abstracted behind interfaces for flexibility.

4. **Agentic Design**: Processing logic is organized into agents, each with single responsibility.

## Common Workflows

### Adding a New Feature

1. Check if it needs workspace isolation → add `workspace_id` parameter
2. Check if it's long-running → consider task queue
3. Check if it processes data → use CodeAct pattern (not per-row LLM)
4. Follow existing patterns in similar code
5. Add tests
6. Update documentation

### Debugging Tips

- Check logs in `logs/sundaygraph.log`
- Verify workspace isolation (check `workspace_id` is passed)
- For ingestion issues, check if CodeAct is being used (should see "Generating extraction code" in logs)
- For graph issues, check if Oxigraph is running (Docker) or using memory fallback

## Important Files to Know

- `src/core/sundaygraph.py` - Main orchestrator, entry point for most operations
- `src/core/config.py` - Configuration management, all settings here
- `src/agents/schema_inference_agent.py` - CodeAct code generation
- `src/data/extraction_executor.py` - Executes generated code
- `src/utils/code_executor.py` - Validates and safely executes code
- `src/api/app.py` - All API endpoints
- `config/config.yaml` - Main configuration file

## Testing Strategy

- Unit tests for agents (mock LLM calls)
- Integration tests for graph operations
- Test workspace isolation explicitly
- Test CodeAct code generation and execution
- Mock external services (Oxigraph, PostgreSQL, Redis)

## Deployment Considerations

- Docker Compose for local development
- Environment variables for secrets (never hardcode)
- Task queue optional (Celery/Temporal) for production
- Oxigraph for production graph storage
- PostgreSQL for schema metadata

## Common Issues & Solutions

**Issue**: Ingestion not creating graph
- **Check**: Is workspace_id being passed?
- **Check**: Is Oxigraph running? (check logs for connection errors)
- **Check**: Are entities/relations being extracted? (check logs)

**Issue**: LLM costs too high
- **Check**: Is CodeAct being used? (should see "Generating extraction code" in logs)
- **Check**: Is `strict_mode: false` in config? (enables CodeAct, disables per-entity validation)

**Issue**: Task queue not working
- **Check**: Is task queue enabled in config?
- **Check**: Is Redis running? (for Celery)
- **Check**: Is Temporal server running? (for Temporal)

## Code Generation Guidelines

When Cursor generates code for this project:

1. **Always include workspace_id** for graph operations
2. **Use async/await** for I/O operations
3. **Use type hints** for all functions
4. **Follow existing patterns** - look at similar code first
5. **Add error handling** with specific exceptions
6. **Log important operations** with loguru
7. **Use Pydantic models** for API request/response
8. **Validate generated code** if executing user code (use CodeExecutor)

## Technology-Specific Notes

### Python
- Use Python 3.10+ features (type hints, async/await)
- Prefer async over sync for I/O
- Use loguru for logging (not print statements)

### FastAPI
- Use Pydantic models for validation
- Use async endpoints
- Return proper HTTP status codes
- Use dependency injection for shared resources

### Next.js/TypeScript
- Use TypeScript strictly (no `any` types)
- Use shadcn/ui components
- Use Tailwind CSS for styling
- API calls through `lib/api.ts`

### Oxigraph
- Use SPARQL queries (not Cypher)
- Workspace isolation via graph URIs
- Handle connection errors gracefully (fallback to memory)

### PostgreSQL
- Use SQLAlchemy for ORM
- Parameterized queries only (no SQL injection)
- Connection pooling for performance
