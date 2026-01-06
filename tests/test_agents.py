"""Tests for agents"""

import pytest
from src.agents import DataIngestionAgent, QueryAgent
from src.graph import MemoryGraphStore
from src.ontology import OntologyManager
from pathlib import Path


@pytest.mark.asyncio
async def test_data_ingestion_agent():
    """Test data ingestion agent"""
    agent = DataIngestionAgent(config={"enabled": True, "chunk_size": 100})
    
    # Create a test file
    test_file = Path("test_data.txt")
    test_file.write_text("This is a test document with some content.")
    
    try:
        data = await agent.process(test_file)
        assert len(data) > 0
    finally:
        test_file.unlink()


def test_query_agent():
    """Test query agent"""
    store = MemoryGraphStore()
    agent = QueryAgent(store, config={"enabled": True})
    
    # Add some test data
    store.add_entity("Person", "p1", {"name": "John"})
    store.add_entity("Person", "p2", {"name": "Jane"})
    store.add_relation("KNOWS", "p1", "p2")
    
    # Query
    results = agent.graph_store.query_entities()
    assert len(results) > 0

