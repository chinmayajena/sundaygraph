# Design Decisions

## Language Choice: Python

### Why Python?

Python was chosen as the primary language for SundayGraph for several critical reasons:

1. **AI/ML Ecosystem Dominance**
   - **NLP Libraries**: spaCy, NLTK, transformers, sentence-transformers are Python-native
   - **LLM Integration**: OpenAI, Anthropic, and other LLM providers have first-class Python SDKs
   - **RAG Frameworks**: LightRAG, LangChain, and most RAG systems are built in Python
   - **Graph Libraries**: NetworkX, Neo4j Python driver, and graph ML libraries are Python-first

2. **Development Velocity**
   - Faster prototyping and iteration
   - Extensive documentation and community support
   - Easier to find developers with Python + AI/ML experience

3. **Integration Ecosystem**
   - Seamless integration with Jupyter notebooks for experimentation
   - Easy integration with data science workflows
   - Compatible with ML Ops tools (MLflow, Weights & Biases, etc.)

### Why Not Go?

**Advantages of Go:**
- Excellent concurrency model (goroutines)
- Fast compilation and execution
- Strong typing
- Great for microservices

**Disadvantages for this project:**
- Limited AI/ML libraries (would need to call Python services)
- No native NLP libraries
- Graph processing libraries are less mature
- Would require significant reimplementation of existing Python tools

**Verdict**: Go is excellent for infrastructure, but Python's AI/ML ecosystem is essential for this domain.

### Why Not Rust?

**Advantages of Rust:**
- Memory safety without garbage collection
- Excellent performance
- Growing ecosystem

**Disadvantages for this project:**
- Very limited AI/ML ecosystem
- NLP libraries are sparse or non-existent
- Would require wrapping Python libraries or significant reimplementation
- Steeper learning curve for most developers

**Verdict**: Rust is great for performance-critical systems, but the AI/ML ecosystem gap is too large for this project.

### Performance Considerations

While Python may not match Go/Rust in raw performance, this system is optimized for:

1. **Async I/O**: Using `asyncio` for non-blocking operations
2. **Batch Processing**: Efficient batch inserts and queries
3. **Graph Backend**: Heavy operations delegated to Neo4j (written in Java, highly optimized)
4. **Caching**: Entity deduplication and result caching
5. **Future Optimization**: Can use PyPy, Cython, or Numba for hot paths if needed

## Package Manager: UV

### Why UV?

[UV](https://github.com/astral-sh/uv) is a modern Python package manager written in Rust that offers:

1. **Speed**: 10-100x faster than pip
   - Parallel downloads
   - Efficient dependency resolution
   - Fast installation

2. **Better Dependency Resolution**
   - More reliable conflict resolution
   - Faster resolution algorithm
   - Better error messages

3. **Modern Standards**
   - PEP 517/518 compliant
   - Supports `pyproject.toml`
   - Works with existing pip workflows

4. **Developer Experience**
   - Fast virtual environment creation
   - Better lock file management
   - Integrated project management

### Why Not Just pip?

We support both UV and pip, both using `pyproject.toml`:

- **UV**: Recommended for development (faster, better DX) - `uv sync`
- **pip**: Still supported for compatibility - `pip install -e ".[dev]"`

### Migration Path

The project is designed to work with both:
- New users: Use UV for best experience
- Existing users: Can continue with pip
- CI/CD: Can use either based on preference

## Architecture Decisions

### Agentic Design

**Why agents?**
- **Modularity**: Each agent has a single responsibility
- **Testability**: Easy to test individual components
- **Extensibility**: Easy to add new agents
- **Parallelization**: Agents can run concurrently

### Graph Backend Abstraction

**Why abstract GraphStore?**
- **Flexibility**: Easy to switch between memory and Neo4j
- **Testing**: Memory backend for fast tests
- **Development**: Memory backend for local development
- **Production**: Neo4j for production scale

### Configuration Management

**Why YAML + Pydantic?**
- **Human-readable**: YAML is easy to edit
- **Type-safe**: Pydantic validates configuration
- **IDE Support**: Type hints enable autocomplete
- **Validation**: Catches configuration errors early

## Future Considerations

### Performance Optimization

If performance becomes a bottleneck:

1. **Hot Paths**: Use Cython or Numba for critical loops
2. **PyPy**: Use PyPy for better performance (compatible with most libraries)
3. **Rust Extensions**: Write performance-critical parts in Rust (via PyO3)
4. **Async Everywhere**: Maximize async I/O usage

### Language Migration

If we needed to migrate to Go or Rust:

1. **Microservices**: Keep Python for AI/ML, use Go/Rust for infrastructure
2. **Hybrid**: Python for processing, Go/Rust for serving
3. **Gradual**: Migrate performance-critical paths first

However, for an AI/ML system, Python's ecosystem advantage is likely to persist.

