"""Tests for graph store"""

import pytest
from src.graph import MemoryGraphStore


def test_memory_graph_store():
    """Test memory graph store"""
    store = MemoryGraphStore()
    
    # Add entity
    success = store.add_entity("Person", "person1", {"name": "John", "age": 30})
    assert success
    
    # Get entity
    entity = store.get_entity("person1")
    assert entity is not None
    assert entity["name"] == "John"
    
    # Add relation
    success = store.add_relation("KNOWS", "person1", "person2", {"since": "2020"})
    assert success
    
    # Query entities
    entities = store.query_entities(entity_type="Person")
    assert len(entities) > 0
    
    # Get neighbors
    neighbors = store.get_neighbors("person1")
    assert len(neighbors) > 0
    
    # Get stats
    stats = store.get_stats()
    assert stats["nodes"] > 0
    
    # Clear
    store.clear()
    stats = store.get_stats()
    assert stats["nodes"] == 0

