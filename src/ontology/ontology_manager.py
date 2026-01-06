"""Ontology manager for schema loading and validation"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from loguru import logger

from .schema import OntologySchema, Entity, Relation, Property, Constraint


class OntologyManager:
    """Manages ontology schema and validation"""
    
    def __init__(self, schema_path: str | Path, strict_mode: bool = False):
        """
        Initialize ontology manager
        
        Args:
            schema_path: Path to ontology schema YAML file
            strict_mode: If True, enforce strict validation
        """
        self.schema_path = Path(schema_path)
        self.strict_mode = strict_mode
        self.schema: Optional[OntologySchema] = None
        self._load_schema()
    
    def _load_schema(self) -> None:
        """Load ontology schema from YAML file"""
        if not self.schema_path.exists():
            logger.warning(f"Schema file not found: {self.schema_path}, using default schema")
            self.schema = OntologySchema()
            return
        
        try:
            with open(self.schema_path, "r", encoding="utf-8") as f:
                schema_dict = yaml.safe_load(f)
            
            # Parse entities
            entities = []
            for entity_dict in schema_dict.get("entities", []):
                properties = [
                    Property(**prop) for prop in entity_dict.get("properties", [])
                ]
                entities.append(Entity(
                    name=entity_dict["name"],
                    description=entity_dict.get("description"),
                    properties=properties,
                    parent=entity_dict.get("parent")
                ))
            
            # Parse relations
            relations = []
            for relation_dict in schema_dict.get("relations", []):
                properties = [
                    Property(**prop) for prop in relation_dict.get("properties", [])
                ]
                relations.append(Relation(
                    name=relation_dict["name"],
                    description=relation_dict.get("description"),
                    source=relation_dict.get("source", "*"),
                    target=relation_dict.get("target", "*"),
                    properties=properties,
                    directed=relation_dict.get("directed", True)
                ))
            
            # Parse constraints
            constraints = [
                Constraint(**constraint) for constraint in schema_dict.get("constraints", [])
            ]
            
            self.schema = OntologySchema(
                version=schema_dict.get("version", "1.0.0"),
                entities=entities,
                relations=relations,
                hierarchies=schema_dict.get("hierarchies", []),
                constraints=constraints
            )
            
            logger.info(f"Loaded ontology schema with {len(entities)} entities and {len(relations)} relations")
        
        except Exception as e:
            logger.error(f"Error loading schema: {e}")
            if self.strict_mode:
                raise
            self.schema = OntologySchema()
    
    def validate_entity(self, entity_type: str, properties: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate entity against schema
        
        Args:
            entity_type: Type of entity
            properties: Entity properties
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        if not self.schema:
            return True, []
        
        entity_def = self.schema.get_entity(entity_type)
        if not entity_def:
            if self.strict_mode:
                return False, [f"Unknown entity type: {entity_type}"]
            return True, []  # Allow custom entities in non-strict mode
        
        errors = []
        
        # Check required properties
        for prop_def in entity_def.properties:
            if prop_def.required and prop_def.name not in properties:
                errors.append(f"Missing required property: {prop_def.name}")
            
            # Type validation
            if prop_def.name in properties:
                value = properties[prop_def.name]
                if not self._validate_property_type(value, prop_def.type):
                    errors.append(
                        f"Property {prop_def.name} has wrong type. "
                        f"Expected {prop_def.type}, got {type(value).__name__}"
                    )
        
        # Check constraints
        for constraint in self.schema.constraints:
            if constraint.entity == entity_type and constraint.property in properties:
                error = self._validate_constraint(constraint, properties[constraint.property])
                if error:
                    errors.append(error)
        
        return len(errors) == 0, errors
    
    def validate_relation(
        self, 
        relation_type: str, 
        source_type: str, 
        target_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> tuple[bool, List[str]]:
        """
        Validate relation against schema
        
        Args:
            relation_type: Type of relation
            source_type: Source entity type
            target_type: Target entity type
            properties: Relation properties
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        if not self.schema:
            return True, []
        
        relation_def = self.schema.get_relation(relation_type)
        if not relation_def:
            if self.strict_mode:
                return False, [f"Unknown relation type: {relation_type}"]
            return True, []
        
        errors = []
        properties = properties or {}
        
        # Check source type
        allowed_sources = self.schema.get_allowed_source_types(relation_type)
        if source_type not in allowed_sources:
            errors.append(
                f"Source type {source_type} not allowed for relation {relation_type}. "
                f"Allowed: {allowed_sources}"
            )
        
        # Check target type
        allowed_targets = self.schema.get_allowed_target_types(relation_type)
        if target_type not in allowed_targets:
            errors.append(
                f"Target type {target_type} not allowed for relation {relation_type}. "
                f"Allowed: {allowed_targets}"
            )
        
        # Validate relation properties
        for prop_def in relation_def.properties:
            if prop_def.required and prop_def.name not in properties:
                errors.append(f"Missing required property: {prop_def.name}")
            
            if prop_def.name in properties:
                value = properties[prop_def.name]
                if not self._validate_property_type(value, prop_def.type):
                    errors.append(
                        f"Property {prop_def.name} has wrong type. "
                        f"Expected {prop_def.type}, got {type(value).__name__}"
                    )
        
        return len(errors) == 0, errors
    
    def _validate_property_type(self, value: Any, expected_type: str) -> bool:
        """Validate property value type"""
        type_mapping = {
            "string": str,
            "integer": int,
            "float": float,
            "boolean": bool,
            "text": str,
            "date": str,  # Could be more strict
            "datetime": str,
        }
        
        expected_python_type = type_mapping.get(expected_type)
        if expected_python_type is None:
            return True  # Unknown type, allow it
        
        return isinstance(value, expected_python_type)
    
    def _validate_constraint(self, constraint: Constraint, value: Any) -> Optional[str]:
        """Validate constraint"""
        if constraint.type == "unique":
            # This would need to check against existing entities
            return None  # Deferred to graph store
        
        elif constraint.type == "range":
            if isinstance(value, (int, float)):
                if constraint.min is not None and value < constraint.min:
                    return f"Value {value} below minimum {constraint.min}"
                if constraint.max is not None and value > constraint.max:
                    return f"Value {value} above maximum {constraint.max}"
        
        elif constraint.type == "pattern":
            if constraint.pattern and isinstance(value, str):
                import re
                if not re.match(constraint.pattern, value):
                    return f"Value {value} does not match pattern {constraint.pattern}"
        
        return None
    
    def get_schema(self) -> OntologySchema:
        """Get current schema"""
        return self.schema or OntologySchema()
    
    def get_entity_types(self) -> List[str]:
        """Get all entity type names"""
        if not self.schema:
            return []
        return [e.name for e in self.schema.entities]
    
    def get_relation_types(self) -> List[str]:
        """Get all relation type names"""
        if not self.schema:
            return []
        return [r.name for r in self.schema.relations]

