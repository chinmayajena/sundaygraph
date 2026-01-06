"""Ontology management module"""

from .ontology_manager import OntologyManager
from .schema import OntologySchema, Entity, Relation, Property

__all__ = ["OntologyManager", "OntologySchema", "Entity", "Relation", "Property"]

