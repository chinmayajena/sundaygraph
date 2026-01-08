#!/usr/bin/env python3
"""Script to ingest seed data into SundayGraph"""

import asyncio
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.sundaygraph import SundayGraph
from loguru import logger

async def ingest_seed_data():
    """Ingest seed data files"""
    logger.info("Initializing SundayGraph...")
    
    # Initialize SundayGraph
    sg = SundayGraph()
    
    # Seed data directory
    seed_dir = Path("data/seed")
    
    if not seed_dir.exists():
        logger.error(f"Seed directory not found: {seed_dir}")
        return
    
    # List of seed files to ingest
    seed_files = [
        seed_dir / "employees.json",
        seed_dir / "projects.json",
        seed_dir / "relationships.txt",
    ]
    
    logger.info(f"Found {len(seed_files)} seed files to ingest")
    
    # Ingest each file
    for seed_file in seed_files:
        if not seed_file.exists():
            logger.warning(f"Seed file not found: {seed_file}")
            continue
        
        logger.info(f"Ingesting {seed_file.name}...")
        try:
            result = await sg.ingest_data(str(seed_file))
            logger.info(f"✓ Successfully ingested {seed_file.name}")
            logger.info(f"  Entities added: {result.get('entities_added', 0)}")
            logger.info(f"  Relations added: {result.get('relations_added', 0)}")
        except Exception as e:
            logger.error(f"✗ Failed to ingest {seed_file.name}: {e}")
    
    # Get statistics
    logger.info("\nGetting graph statistics...")
    stats = await sg.get_stats()
    
    logger.info("\n=== Graph Statistics ===")
    logger.info(f"Nodes: {stats.get('graph', {}).get('nodes', 0)}")
    logger.info(f"Edges: {stats.get('graph', {}).get('edges', 0)}")
    logger.info(f"Entity Types: {stats.get('ontology', {}).get('entities', 0)}")
    logger.info(f"Relation Types: {stats.get('ontology', {}).get('relations', 0)}")
    
    # Close connections
    sg.close()
    logger.info("\n✓ Seed data ingestion complete!")

if __name__ == "__main__":
    asyncio.run(ingest_seed_data())

