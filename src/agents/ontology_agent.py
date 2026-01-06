"""Ontology agent for validation and mapping"""

from typing import Dict, Any, List, Optional
from loguru import logger

from .base_agent import BaseAgent
from ..ontology.ontology_manager import OntologyManager


class OntologyAgent(BaseAgent):
    """Agent responsible for ontology validation and mapping"""
    
    def __init__(self, ontology_manager: OntologyManager, config: Optional[Dict[str, Any]] = None):
        """
        Initialize ontology agent
        
        Args:
            ontology_manager: Ontology manager instance
            config: Agent configuration
        """
        super().__init__(config)
        self.ontology_manager = ontology_manager
        self.strict_mode = self.config.get("strict_mode", False)
        self.auto_map = self.config.get("auto_map_properties", True)
    
    async def process(self, entity_type: str, properties: Dict[str, Any]) -> tuple[bool, List[str], Dict[str, Any]]:
        """
        Validate and map entity against ontology
        
        Args:
            entity_type: Type of entity
            properties: Entity properties
            
        Returns:
            Tuple of (is_valid, errors, mapped_properties)
        """
        if not self.is_enabled():
            return True, [], properties
        
        # Validate entity
        is_valid, errors = self.ontology_manager.validate_entity(entity_type, properties)
        
        if not is_valid and self.strict_mode:
            logger.warning(f"Entity validation failed: {errors}")
            return False, errors, properties
        
        # Auto-map properties if enabled
        mapped_properties = properties
        if self.auto_map:
            mapped_properties = self._map_properties(entity_type, properties)
        
        return is_valid, errors, mapped_properties
    
    async def validate_relation(
        self,
        relation_type: str,
        source_type: str,
        target_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> tuple[bool, List[str]]:
        """
        Validate relation
        
        Args:
            relation_type: Type of relation
            source_type: Source entity type
            target_type: Target entity type
            properties: Relation properties
            
        Returns:
            Tuple of (is_valid, errors)
        """
        if not self.is_enabled():
            return True, []
        
        return self.ontology_manager.validate_relation(
            relation_type, source_type, target_type, properties
        )
    
    def _map_properties(self, entity_type: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map properties to ontology schema
        
        Args:
            entity_type: Entity type
            properties: Properties to map
            
        Returns:
            Mapped properties
        """
        entity_def = self.ontology_manager.get_schema().get_entity(entity_type)
        if not entity_def:
            return properties
        
        mapped = {}
        schema_props = {prop.name: prop for prop in entity_def.properties}
        
        # Map known properties
        for key, value in properties.items():
            if key in schema_props:
                mapped[key] = value
            else:
                # Try to find similar property (simple case-insensitive match)
                matched = False
                for schema_key in schema_props.keys():
                    if key.lower() == schema_key.lower():
                        mapped[schema_key] = value
                        matched = True
                        break
                
                if not matched:
                    # Keep unknown properties if allowed
                    if self.ontology_manager.get_schema().get_entity(entity_type) or not self.strict_mode:
                        mapped[key] = value
        
        return mapped
    
    def suggest_entity_type(self, properties: Dict[str, Any]) -> Optional[str]:
        """
        Suggest entity type based on properties
        
        Args:
            properties: Entity properties
            
        Returns:
            Suggested entity type or None
        """
        schema = self.ontology_manager.get_schema()
        best_match = None
        best_score = 0
        
        for entity in schema.entities:
            score = 0
            entity_props = {prop.name for prop in entity.properties}
            
            # Score based on matching properties
            for prop_name in properties.keys():
                if prop_name in entity_props:
                    score += 1
            
            if score > best_score:
                best_score = score
                best_match = entity.name
        
        return best_match if best_score > 0 else None

