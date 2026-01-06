# Contributing to SundayGraph

Thank you for your interest in contributing to SundayGraph!

## Development Setup

### Using UV (Recommended)

1. **Install UV**:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   # Or: pip install uv
   ```

2. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd sundaygraph
   ```

3. **Install dependencies**:
   ```bash
   uv sync --dev
   ```

4. **Activate virtual environment**:
   ```bash
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

### Using pip (Traditional)

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

## Code Style

- Follow PEP 8 style guide
- Use type hints for all functions
- Format code with Black: `black src/ tests/` or `uv run black src/ tests/`
- Check types with mypy: `mypy src/` or `uv run mypy src/`
- Lint with ruff: `ruff check src/` or `uv run ruff check src/`

## Testing

Run tests with:
```bash
# With UV
uv run pytest tests/

# With pip
pytest tests/
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new features
5. Ensure all tests pass
6. Submit a pull request

## Code Structure

- `src/` - Main source code
- `tests/` - Test files
- `config/` - Configuration files
- `examples/` - Example scripts
- `docs/` - Documentation

## Package Management

This project uses `pyproject.toml` for dependency management:

- **UV**: Modern, fast package manager (recommended) - `uv sync`
- **pip**: Traditional Python package manager - `pip install -e ".[dev]"`

## Questions?

Open an issue for questions or discussions.
