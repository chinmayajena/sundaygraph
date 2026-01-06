"""Basic usage example for SundayGraph"""

import asyncio
from pathlib import Path
from src import SundayGraph


async def main():
    # Initialize SundayGraph
    sg = SundayGraph(config_path="config/config.yaml")
    
    # Example 1: Ingest data
    print("Example 1: Ingesting data...")
    result = await sg.ingest_data("data/input")
    print(f"Ingestion result: {result}")
    
    # Example 2: Query entities
    print("\nExample 2: Querying entities...")
    entities = await sg.query("Person", query_type="entity")
    print(f"Found {len(entities)} entities")
    for entity in entities[:5]:
        print(f"  - {entity}")
    
    # Example 3: Get statistics
    print("\nExample 3: Getting statistics...")
    stats = await sg.get_stats()
    print(f"Graph stats: {stats['graph']}")
    print(f"Ontology stats: {stats['ontology']}")
    
    # Cleanup
    sg.close()


if __name__ == "__main__":
    asyncio.run(main())

