"""Ontology schema definitions"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Property(BaseModel):
    """Property definition"""
    name: str
    type: str  # "string", "integer", "float", "date", "datetime", "text", "boolean"
    required: bool = False
    indexed: bool = False
    default: Optional[Any] = None
    description: Optional[str] = None


class Entity(BaseModel):
    """Entity type definition"""
    name: str
    description: Optional[str] = None
    properties: List[Property] = Field(default_factory=list)
    parent: Optional[str] = None  # For inheritance


class Relation(BaseModel):
    """Relation type definition"""
    name: str
    description: Optional[str] = None
    source: str | List[str]  # Entity type(s) or "*" for any
    target: str | List[str]  # Entity type(s) or "*" for any
    properties: List[Property] = Field(default_factory=list)
    directed: bool = True


class Constraint(BaseModel):
    """Constraint definition"""
    type: str  # "unique", "range", "pattern", etc.
    entity: str
    property: str
    value: Optional[Any] = None
    min: Optional[float] = None
    max: Optional[float] = None
    pattern: Optional[str] = None


class OntologySchema(BaseModel):
    """Complete ontology schema"""
    version: str = "1.0.0"
    entities: List[Entity] = Field(default_factory=list)
    relations: List[Relation] = Field(default_factory=list)
    hierarchies: List[Dict[str, Any]] = Field(default_factory=list)
    constraints: List[Constraint] = Field(default_factory=list)
    
    def get_entity(self, name: str) -> Optional[Entity]:
        """Get entity definition by name"""
        for entity in self.entities:
            if entity.name == name:
                return entity
        return None
    
    def get_relation(self, name: str) -> Optional[Relation]:
        """Get relation definition by name"""
        for relation in self.relations:
            if relation.name == name:
                return relation
        return None
    
    def validate_entity_type(self, entity_type: str) -> bool:
        """Check if entity type exists in schema"""
        return self.get_entity(entity_type) is not None
    
    def validate_relation_type(self, relation_type: str) -> bool:
        """Check if relation type exists in schema"""
        return self.get_relation(relation_type) is not None
    
    def get_allowed_source_types(self, relation_type: str) -> List[str]:
        """Get allowed source entity types for a relation"""
        relation = self.get_relation(relation_type)
        if not relation:
            return []
        
        if relation.source == "*":
            return [e.name for e in self.entities]
        elif isinstance(relation.source, str):
            return [relation.source]
        else:
            return relation.source
    
    def get_allowed_target_types(self, relation_type: str) -> List[str]:
        """Get allowed target entity types for a relation"""
        relation = self.get_relation(relation_type)
        if not relation:
            return []
        
        if relation.target == "*":
            return [e.name for e in self.entities]
        elif isinstance(relation.target, str):
            return [relation.target]
        else:
            return relation.target

