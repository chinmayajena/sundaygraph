"""Main entry point for FastAPI application"""

import uvicorn
from pathlib import Path
import os

# Load environment variables from .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv not installed, skip
    pass

# Import app factory
from src.api.app import create_app

# Create app instance for uvicorn
config_path = os.getenv("CONFIG_PATH", "config/config.yaml")
config_path = Path(config_path)
app = create_app(config_path=str(config_path) if config_path.exists() else None)

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        log_level=os.getenv("LOG_LEVEL", "info")
    )

