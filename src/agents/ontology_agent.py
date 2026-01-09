"""Ontology agent for validation and mapping with LLM reasoning"""

from typing import Dict, Any, List, Optional
from loguru import logger
import json

from .base_agent import BaseAgent
from ..ontology.ontology_manager import OntologyManager
from ..utils.llm_service import LLMService


class OntologyAgent(BaseAgent):
    """Agent responsible for ontology validation and mapping with LLM reasoning"""
    
    def __init__(
        self, 
        ontology_manager: OntologyManager, 
        config: Optional[Dict[str, Any]] = None,
        llm_service: Optional[LLMService] = None
    ):
        """
        Initialize ontology agent
        
        Args:
            ontology_manager: Ontology manager instance
            config: Agent configuration
            llm_service: Optional LLM service for reasoning
        """
        super().__init__(config)
        self.ontology_manager = ontology_manager
        self.strict_mode = self.config.get("strict_mode", False)
        self.auto_map = self.config.get("auto_map_properties", True)
        self.use_llm_reasoning = self.config.get("use_llm_reasoning", True)
        
        # Initialize LLM service if enabled
        self.llm_service = llm_service
        if self.use_llm_reasoning and not self.llm_service:
            llm_config = self.config.get("llm", {})
            if llm_config:
                self.llm_service = LLMService(
                    provider=llm_config.get("provider", "openai"),
                    model=llm_config.get("model", "gpt-4"),
                    temperature=llm_config.get("temperature", 0.7),
                    max_tokens=llm_config.get("max_tokens", 2000)
                )
    
    async def process(self, entity_type: str, properties: Dict[str, Any], use_llm: bool = True) -> tuple[bool, List[str], Dict[str, Any]]:
        """
        Validate and map entity against ontology with optional LLM reasoning
        
        Args:
            entity_type: Type of entity
            properties: Entity properties
            use_llm: Whether to use LLM reasoning (default: True)
            
        Returns:
            Tuple of (is_valid, errors, mapped_properties)
        """
        if not self.is_enabled():
            return True, [], properties
        
        # Use LLM reasoning if enabled and requested
        if use_llm and self.use_llm_reasoning and self.llm_service:
            try:
                ontology_schema = self._get_ontology_schema_dict()
                reasoning_result = await self.llm_service.reason_about_ontology(
                    context=f"Entity type: {entity_type}, Properties: {json.dumps(properties)}",
                    question="What is the correct entity type and how should properties be mapped?",
                    ontology_schema=ontology_schema
                )
                
                # Use LLM suggestions if available
                if reasoning_result.get("entity_type"):
                    entity_type = reasoning_result["entity_type"]
                
                if reasoning_result.get("properties"):
                    # Merge LLM-suggested properties with original
                    properties = {**properties, **reasoning_result["properties"]}
                
                logger.debug(f"LLM reasoning result: {reasoning_result.get('reasoning', '')}")
            
            except Exception as e:
                logger.warning(f"LLM reasoning failed, falling back to rule-based: {e}")
        
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
        properties: Optional[Dict[str, Any]] = None,
        use_llm: bool = True
    ) -> tuple[bool, List[str]]:
        """
        Validate relation with optional LLM reasoning
        
        Args:
            relation_type: Type of relation
            source_type: Source entity type
            target_type: Target entity type
            properties: Relation properties
            use_llm: Whether to use LLM reasoning (default: True)
            
        Returns:
            Tuple of (is_valid, errors)
        """
        if not self.is_enabled():
            return True, []
        
        # Use LLM to validate semantic correctness if enabled and requested
        if use_llm and self.use_llm_reasoning and self.llm_service:
            try:
                ontology_schema = self._get_ontology_schema_dict()
                reasoning_result = await self.llm_service.reason_about_ontology(
                    context=f"Relation: {relation_type} from {source_type} to {target_type}",
                    question="Is this relation semantically correct?",
                    ontology_schema=ontology_schema
                )
                
                validation = reasoning_result.get("validation", {})
                if validation.get("is_valid") is False:
                    errors = validation.get("errors", ["LLM determined relation is semantically incorrect"])
                    return False, errors
            
            except Exception as e:
                logger.warning(f"LLM relation validation failed: {e}")
        
        return self.ontology_manager.validate_relation(
            relation_type, source_type, target_type, properties
        )
    
    async def suggest_entity_type_with_reasoning(self, properties: Dict[str, Any], context: Optional[str] = None) -> Optional[str]:
        """
        Suggest entity type using LLM reasoning
        
        Args:
            properties: Entity properties
            context: Optional context
            
        Returns:
            Suggested entity type or None
        """
        if self.use_llm_reasoning and self.llm_service:
            try:
                ontology_schema = self._get_ontology_schema_dict()
                reasoning_result = await self.llm_service.reason_about_ontology(
                    context=f"Properties: {json.dumps(properties)}. Context: {context or 'None'}",
                    question="What entity type best matches these properties?",
                    ontology_schema=ontology_schema
                )
                
                suggested_type = reasoning_result.get("entity_type")
                if suggested_type:
                    # Validate the suggestion
                    if self.ontology_manager.get_schema().get_entity(suggested_type):
                        return suggested_type
            
            except Exception as e:
                logger.warning(f"LLM entity type suggestion failed: {e}")
        
        # Fallback to rule-based suggestion
        return self.suggest_entity_type(properties)
    
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
        Suggest entity type based on properties (rule-based fallback)
        
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
    
    def _get_ontology_schema_dict(self) -> Dict[str, Any]:
        """Get ontology schema as dictionary for LLM"""
        schema = self.ontology_manager.get_schema()
        return {
            "entities": [
                {
                    "name": e.name,
                    "description": e.description,
                    "properties": [{"name": p.name, "type": p.type, "required": p.required} for p in e.properties]
                }
                for e in schema.entities
            ],
            "relations": [
                {
                    "name": r.name,
                    "description": r.description,
                    "source": r.source,
                    "target": r.target,
                    "properties": [{"name": p.name, "type": p.type} for p in r.properties]
                }
                for r in schema.relations
            ]
        }
