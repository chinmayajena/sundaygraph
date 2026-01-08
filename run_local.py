#!/usr/bin/env python3
"""Quick start script for local development"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_dependencies():
    """Check if required dependencies are installed"""
    missing = []
    try:
        import fastapi
    except ImportError:
        missing.append("fastapi")
    
    try:
        import uvicorn
    except ImportError:
        missing.append("uvicorn")
    
    try:
        import yaml
    except ImportError:
        missing.append("pyyaml")
    
    try:
        import pydantic
    except ImportError:
        missing.append("pydantic")
    
    try:
        import networkx
    except ImportError:
        missing.append("networkx")
    
    try:
        import loguru
    except ImportError:
        missing.append("loguru")
    
    if missing:
        print("Missing dependencies:", ", ".join(missing))
        print("\nInstall with one of these methods:")
        print("\n1. Using pip (recommended):")
        print(f"   pip install {' '.join(missing)}")
        print("\n2. Using pip with virtual environment:")
        print("   python -m venv venv")
        print("   source venv/bin/activate  # On Windows: venv\\Scripts\\activate")
        print(f"   pip install {' '.join(missing)}")
        print("\n3. Install all dependencies from pyproject.toml:")
        print("   pip install -e .")
        return False
    
    print("All dependencies installed")
    return True

if __name__ == "__main__":
    print("SundayGraph - Starting API Server")
    print("=" * 50)
    
    if not check_dependencies():
        sys.exit(1)
    
    print("\nStarting server...")
    print("   API: http://localhost:8000")
    print("   Docs: http://localhost:8000/docs")
    print("   Health: http://localhost:8000/health")
    print("\nNote: Using memory graph backend (no Neo4j required)")
    print("   Press Ctrl+C to stop\n")
    
    try:
        import uvicorn
        from src.api.main import app
        
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n\nServer stopped")
    except Exception as e:
        print(f"\nError starting server: {e}")
        sys.exit(1)
