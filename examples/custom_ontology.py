"""Example with custom ontology"""

import asyncio
from src import SundayGraph
from src.ontology import OntologyManager


async def main():
    # Initialize with custom ontology
    sg = SundayGraph(config_path="config/config.yaml")
    
    # Get ontology manager
    ontology_manager = sg.ontology_manager
    
    # Check available entity types
    print("Available entity types:")
    for entity_type in ontology_manager.get_entity_types():
        print(f"  - {entity_type}")
    
    # Check available relation types
    print("\nAvailable relation types:")
    for relation_type in ontology_manager.get_relation_types():
        print(f"  - {relation_type}")
    
    # Validate an entity
    print("\nValidating entity...")
    is_valid, errors, mapped = await sg.ontology_agent.process(
        "Person",
        {"name": "John Doe", "age": 30, "email": "john@example.com"}
    )
    print(f"Valid: {is_valid}, Errors: {errors}")
    print(f"Mapped properties: {mapped}")
    
    sg.close()


if __name__ == "__main__":
    asyncio.run(main())

