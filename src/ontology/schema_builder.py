"""LLM-powered ontology schema builder"""

from typing import Dict, Any, List, Optional
from loguru import logger
import json

from .schema import OntologySchema, Entity, Relation, Property
from .evaluation_metrics import OntologyEvaluator
from ..utils.llm_service import LLMService


class OntologySchemaBuilder:
    """Builds ontology schema using LLM reasoning"""
    
    def __init__(self, llm_service: LLMService, enable_evaluation: bool = True):
        """
        Initialize schema builder
        
        Args:
            llm_service: LLM service for reasoning
            enable_evaluation: Whether to enable quality evaluation
        """
        self.llm_service = llm_service
        self.evaluator = OntologyEvaluator() if enable_evaluation else None
    
    async def build_schema_from_domain(
        self,
        domain_description: str,
        existing_schema: Optional[OntologySchema] = None
    ) -> OntologySchema:
        """
        Build ontology schema from domain description using LLM reasoning
        
        Args:
            domain_description: Description of the domain
            existing_schema: Optional existing schema to extend
            
        Returns:
            Built ontology schema
        """
        logger.info("Building ontology schema from domain description using LLM reasoning")
        
        system_prompt = """You are an expert ontology engineer. Your task is to design a comprehensive ontology schema based on domain descriptions.

Create a well-structured ontology with:
1. Entity types with their properties
2. Relations between entities
3. Property types and constraints
4. Hierarchical relationships

Think step by step about:
- What are the main concepts in this domain?
- What properties do these concepts have?
- How are concepts related to each other?
- What constraints should be applied?

Format your response as JSON matching this structure:
{
  "entities": [
    {
      "name": "EntityName",
      "description": "Description",
      "properties": [
        {"name": "prop_name", "type": "string|integer|float|date|datetime|text|boolean", "required": true/false, "indexed": true/false}
      ]
    }
  ],
  "relations": [
    {
      "name": "RELATION_NAME",
      "description": "Description",
      "source": "EntityType" or ["EntityType1", "EntityType2"],
      "target": "EntityType" or ["EntityType1", "EntityType2"],
      "directed": true,
      "properties": [
        {"name": "prop_name", "type": "string|integer|float|date|datetime|text|boolean", "required": true/false}
      ]
    }
  ],
  "hierarchies": [
    {"parent": "ParentEntity", "children": ["Child1", "Child2"]}
  ]
}"""
        
        context = f"Domain Description: {domain_description}"
        if existing_schema:
            context += f"\n\nExisting Schema:\n{json.dumps(self._schema_to_dict(existing_schema), indent=2)}"
            context += "\n\nExtend and improve the existing schema based on the domain description."
        
        prompt = f"""Based on the following domain description, create or extend an ontology schema:

{context}

Provide a complete ontology schema in JSON format."""
        
        # Use medium complexity for schema building (can use cheaper models)
        response = await self.llm_service.think(
            prompt,
            system_prompt=system_prompt,
            task_complexity="medium",
            use_cache=True
        )
        
        # Parse LLM response
        schema_dict = self._parse_llm_response(response)
        
        # Convert to OntologySchema
        schema = self._dict_to_schema(schema_dict, existing_schema)
        
        # Evaluate schema quality
        if self.evaluator:
            evaluation = self.evaluator.evaluate_schema(schema, domain_description)
            quality_score = evaluation.get("quality_score", {}).get("score", 0.0)
            grade = evaluation.get("quality_score", {}).get("grade", "N/A")
            logger.info(
                f"Built schema with {len(schema.entities)} entities and {len(schema.relations)} relations | "
                f"Quality: {grade} ({quality_score:.2%})"
            )
            
            # Log recommendations if quality is low
            if quality_score < 0.7:
                recommendations = evaluation.get("quality_score", {}).get("recommendations", [])
                if recommendations:
                    logger.warning(f"Schema quality recommendations: {recommendations[:3]}")
        else:
            logger.info(f"Built schema with {len(schema.entities)} entities and {len(schema.relations)} relations")
        
        return schema
    
    async def evolve_schema(
        self,
        current_schema: OntologySchema,
        new_data_sample: Dict[str, Any],
        feedback: Optional[str] = None
    ) -> OntologySchema:
        """
        Evolve schema based on new data and feedback
        
        Args:
            current_schema: Current ontology schema
            new_data_sample: Sample of new data
            feedback: Optional feedback on schema issues
            
        Returns:
            Evolved schema
        """
        logger.info("Evolving ontology schema based on new data")
        
        system_prompt = """You are an expert at evolving ontologies. Analyze new data and feedback to improve the ontology schema.

Consider:
1. Missing entity types
2. Missing properties
3. Missing relations
4. Incorrect constraints
5. Better property types

Provide an improved schema in JSON format."""
        
        prompt = f"""Current Schema:
{json.dumps(self._schema_to_dict(current_schema), indent=2)}

New Data Sample:
{json.dumps(new_data_sample, indent=2)}

Feedback: {feedback or "None"}

Evolve the schema to better accommodate this data. Provide the complete evolved schema in JSON format."""
        
        # Use medium complexity for schema evolution
        response = await self.llm_service.think(
            prompt,
            system_prompt=system_prompt,
            task_complexity="medium",
            use_cache=False  # Don't cache evolution requests
        )
        schema_dict = self._parse_llm_response(response)
        
        evolved_schema = self._dict_to_schema(schema_dict, current_schema)
        
        # Evaluate evolved schema
        if self.evaluator:
            evaluation = self.evaluator.evaluate_schema(evolved_schema)
            quality_score = evaluation.get("quality_score", {}).get("score", 0.0)
            logger.info(f"Evolved schema quality: {quality_score:.2%}")
        
        return evolved_schema
    
    async def suggest_improvements(
        self,
        schema: OntologySchema,
        usage_stats: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Suggest improvements to the schema
        
        Args:
            schema: Current schema
            usage_stats: Optional usage statistics
            
        Returns:
            List of improvement suggestions
        """
        system_prompt = """You are an ontology expert. Analyze schemas and suggest improvements."""
        
        prompt = f"""Schema:
{json.dumps(self._schema_to_dict(schema), indent=2)}

Usage Stats: {json.dumps(usage_stats or {}, indent=2)}

Suggest improvements to this ontology schema. Provide a list of actionable suggestions."""
        
        response = await self.llm_service.think(prompt, system_prompt=system_prompt)
        
        # Extract suggestions (could be a list or text)
        suggestions = []
        if "```json" in response:
            try:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                suggestions = json.loads(response[json_start:json_end].strip())
            except:
                pass
        
        if not suggestions:
            # Parse as text list
            lines = response.split("\n")
            for line in lines:
                if line.strip() and (line.strip().startswith("-") or line.strip()[0].isdigit()):
                    suggestions.append(line.strip().lstrip("- ").lstrip("0123456789. "))
        
        return suggestions if suggestions else [response]
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM JSON response"""
        try:
            # Extract JSON from markdown code blocks
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                response = response[json_start:json_end].strip()
            elif "```" in response:
                json_start = response.find("```") + 3
                json_end = response.find("```", json_start)
                response = response[json_start:json_end].strip()
            
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.debug(f"Response: {response}")
            # Return minimal schema
            return {"entities": [], "relations": [], "hierarchies": []}
    
    def _schema_to_dict(self, schema: OntologySchema) -> Dict[str, Any]:
        """Convert schema to dictionary"""
        return {
            "entities": [
                {
                    "name": e.name,
                    "description": e.description,
                    "properties": [
                        {
                            "name": p.name,
                            "type": p.type,
                            "required": p.required,
                            "indexed": p.indexed
                        }
                        for p in e.properties
                    ]
                }
                for e in schema.entities
            ],
            "relations": [
                {
                    "name": r.name,
                    "description": r.description,
                    "source": r.source,
                    "target": r.target,
                    "directed": r.directed,
                    "properties": [
                        {
                            "name": p.name,
                            "type": p.type,
                            "required": p.required
                        }
                        for p in r.properties
                    ]
                }
                for r in schema.relations
            ],
            "hierarchies": schema.hierarchies
        }
    
    def _dict_to_schema(
        self,
        schema_dict: Dict[str, Any],
        existing_schema: Optional[OntologySchema] = None
    ) -> OntologySchema:
        """Convert dictionary to OntologySchema"""
        entities = []
        for entity_dict in schema_dict.get("entities", []):
            properties = [
                Property(
                    name=p["name"],
                    type=p.get("type", "string"),
                    required=p.get("required", False),
                    indexed=p.get("indexed", False)
                )
                for p in entity_dict.get("properties", [])
            ]
            entities.append(Entity(
                name=entity_dict["name"],
                description=entity_dict.get("description"),
                properties=properties
            ))
        
        relations = []
        for relation_dict in schema_dict.get("relations", []):
            properties = [
                Property(
                    name=p["name"],
                    type=p.get("type", "string"),
                    required=p.get("required", False)
                )
                for p in relation_dict.get("properties", [])
            ]
            relations.append(Relation(
                name=relation_dict["name"],
                description=relation_dict.get("description"),
                source=relation_dict.get("source", "*"),
                target=relation_dict.get("target", "*"),
                properties=properties,
                directed=relation_dict.get("directed", True)
            ))
        
        return OntologySchema(
            version=existing_schema.version if existing_schema else "1.0.0",
            entities=entities,
            relations=relations,
            hierarchies=schema_dict.get("hierarchies", [])
        )

