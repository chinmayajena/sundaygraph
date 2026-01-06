"""Tests for ontology management"""

import pytest
from pathlib import Path
from src.ontology import OntologyManager


def test_ontology_manager_initialization():
    """Test ontology manager initialization"""
    schema_path = Path("config/ontology_schema.yaml")
    manager = OntologyManager(schema_path=schema_path)
    assert manager.schema is not None


def test_entity_validation():
    """Test entity validation"""
    schema_path = Path("config/ontology_schema.yaml")
    manager = OntologyManager(schema_path=schema_path, strict_mode=False)
    
    is_valid, errors, _ = manager.validate_entity(
        "Person",
        {"name": "John Doe", "age": 30}
    )
    assert is_valid or len(errors) == 0  # Should be valid or have minor errors


def test_relation_validation():
    """Test relation validation"""
    schema_path = Path("config/ontology_schema.yaml")
    manager = OntologyManager(schema_path=schema_path, strict_mode=False)
    
    is_valid, errors = manager.validate_relation(
        "WORKS_FOR",
        "Person",
        "Organization"
    )
    assert is_valid or len(errors) == 0

