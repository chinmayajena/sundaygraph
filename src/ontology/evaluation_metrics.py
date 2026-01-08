"""Ontology Evaluation Metrics

This module provides evaluation metrics for ontology quality:
- Completeness: Coverage of domain concepts
- Consistency: Logical consistency of schema
- Coherence: Semantic coherence
- Coverage: Entity and relation coverage
- Quality Score: Overall quality metric
"""

from typing import Dict, Any, List, Optional
from loguru import logger
import json

from .schema import OntologySchema, Entity, Relation, Property


class OntologyEvaluator:
    """Evaluates ontology quality using multiple metrics"""
    
    def __init__(self):
        """Initialize evaluator"""
        pass
    
    def evaluate_schema(self, schema: OntologySchema, domain_description: Optional[str] = None) -> Dict[str, Any]:
        """
        Evaluate ontology schema quality
        
        Args:
            schema: Ontology schema to evaluate
            domain_description: Optional domain description for context
        
        Returns:
            Evaluation metrics dictionary
        """
        metrics = {
            "completeness": self._evaluate_completeness(schema, domain_description),
            "consistency": self._evaluate_consistency(schema),
            "coherence": self._evaluate_coherence(schema),
            "coverage": self._evaluate_coverage(schema),
            "structure": self._evaluate_structure(schema),
        }
        
        # Calculate overall quality score (weighted average)
        weights = {
            "completeness": 0.25,
            "consistency": 0.25,
            "coherence": 0.20,
            "coverage": 0.15,
            "structure": 0.15,
        }
        
        quality_score = sum(
            metrics[key]["score"] * weights[key]
            for key in weights
        )
        
        metrics["quality_score"] = {
            "score": quality_score,
            "grade": self._get_grade(quality_score),
            "recommendations": self._generate_recommendations(metrics)
        }
        
        return metrics
    
    def _evaluate_completeness(self, schema: OntologySchema, domain_description: Optional[str] = None) -> Dict[str, Any]:
        """
        Evaluate completeness: Are all important concepts covered?
        
        Metrics:
        - Entity count and diversity
        - Relation coverage
        - Property completeness
        """
        entity_count = len(schema.entities)
        relation_count = len(schema.relations)
        
        # Check if entities have properties
        entities_with_properties = sum(1 for e in schema.entities if len(e.properties) > 0)
        property_coverage = entities_with_properties / entity_count if entity_count > 0 else 0.0
        
        # Check for required properties (id, name, etc.)
        common_properties = {"id", "name", "type", "created_at", "updated_at"}
        entities_with_common_props = sum(
            1 for e in schema.entities
            if any(p.name.lower() in common_properties for p in e.properties)
        )
        common_prop_coverage = entities_with_common_props / entity_count if entity_count > 0 else 0.0
        
        # Score based on various factors
        score = 0.0
        if entity_count >= 3:
            score += 0.3
        elif entity_count >= 1:
            score += 0.15
        
        if relation_count >= 2:
            score += 0.3
        elif relation_count >= 1:
            score += 0.15
        
        score += property_coverage * 0.2
        score += common_prop_coverage * 0.2
        
        return {
            "score": min(score, 1.0),
            "entity_count": entity_count,
            "relation_count": relation_count,
            "property_coverage": property_coverage,
            "common_property_coverage": common_prop_coverage,
        }
    
    def _evaluate_consistency(self, schema: OntologySchema) -> Dict[str, Any]:
        """
        Evaluate consistency: Are there logical inconsistencies?
        
        Metrics:
        - Duplicate entity/relation names
        - Circular dependencies
        - Invalid property types
        - Relation source/target validity
        """
        issues = []
        score = 1.0
        
        # Check for duplicate entity names
        entity_names = [e.name for e in schema.entities]
        duplicates = [name for name in entity_names if entity_names.count(name) > 1]
        if duplicates:
            issues.append(f"Duplicate entity names: {set(duplicates)}")
            score -= 0.2
        
        # Check for duplicate relation names
        relation_names = [r.name for r in schema.relations]
        duplicates = [name for name in relation_names if relation_names.count(name) > 1]
        if duplicates:
            issues.append(f"Duplicate relation names: {set(duplicates)}")
            score -= 0.2
        
        # Check relation source/target validity
        valid_entity_names = {e.name for e in schema.entities}
        invalid_relations = []
        for relation in schema.relations:
            sources = relation.source if isinstance(relation.source, list) else [relation.source]
            targets = relation.target if isinstance(relation.target, list) else [relation.target]
            
            for source in sources:
                if source != "*" and source not in valid_entity_names:
                    invalid_relations.append(f"{relation.name}: invalid source '{source}'")
            
            for target in targets:
                if target != "*" and target not in valid_entity_names:
                    invalid_relations.append(f"{relation.name}: invalid target '{target}'")
        
        if invalid_relations:
            issues.extend(invalid_relations)
            score -= min(0.3, len(invalid_relations) * 0.05)
        
        # Check property type validity
        valid_types = {"string", "integer", "float", "date", "datetime", "text", "boolean"}
        invalid_properties = []
        for entity in schema.entities:
            for prop in entity.properties:
                if prop.type not in valid_types:
                    invalid_properties.append(f"{entity.name}.{prop.name}: invalid type '{prop.type}'")
        
        for relation in schema.relations:
            for prop in relation.properties:
                if prop.type not in valid_types:
                    invalid_properties.append(f"{relation.name}.{prop.name}: invalid type '{prop.type}'")
        
        if invalid_properties:
            issues.extend(invalid_properties)
            score -= min(0.2, len(invalid_properties) * 0.02)
        
        return {
            "score": max(score, 0.0),
            "issues": issues,
            "issue_count": len(issues),
        }
    
    def _evaluate_coherence(self, schema: OntologySchema) -> Dict[str, Any]:
        """
        Evaluate coherence: Semantic coherence and logical structure
        
        Metrics:
        - Hierarchical relationships
        - Relation semantic coherence
        - Entity naming consistency
        """
        score = 0.0
        
        # Check for hierarchical relationships
        if schema.hierarchies and len(schema.hierarchies) > 0:
            score += 0.3
        
        # Check entity naming consistency (camelCase, PascalCase, etc.)
        entity_names = [e.name for e in schema.entities]
        naming_patterns = {
            "PascalCase": sum(1 for n in entity_names if n and n[0].isupper() and "_" not in n),
            "camelCase": sum(1 for n in entity_names if n and n[0].islower() and "_" not in n),
            "snake_case": sum(1 for n in entity_names if "_" in n),
        }
        dominant_pattern = max(naming_patterns, key=naming_patterns.get)
        consistency = naming_patterns[dominant_pattern] / len(entity_names) if entity_names else 0.0
        score += consistency * 0.2
        
        # Check relation naming (UPPER_CASE or camelCase)
        relation_names = [r.name for r in schema.relations]
        if relation_names:
            upper_case = sum(1 for n in relation_names if n.isupper() or "_" in n)
            relation_consistency = upper_case / len(relation_names)
            score += relation_consistency * 0.2
        
        # Check for bidirectional relations where appropriate
        bidirectional_count = sum(1 for r in schema.relations if not r.directed)
        if bidirectional_count > 0:
            score += min(0.1, bidirectional_count * 0.05)
        
        # Check entity descriptions
        entities_with_descriptions = sum(1 for e in schema.entities if e.description)
        if entities_with_descriptions > 0:
            desc_coverage = entities_with_descriptions / len(schema.entities)
            score += desc_coverage * 0.2
        
        return {
            "score": min(score, 1.0),
            "hierarchies": len(schema.hierarchies),
            "naming_consistency": consistency,
            "entities_with_descriptions": entities_with_descriptions,
        }
    
    def _evaluate_coverage(self, schema: OntologySchema) -> Dict[str, Any]:
        """
        Evaluate coverage: How well does the schema cover the domain?
        
        Metrics:
        - Entity type diversity
        - Relation type diversity
        - Property richness
        """
        entity_count = len(schema.entities)
        relation_count = len(schema.relations)
        
        # Average properties per entity
        total_properties = sum(len(e.properties) for e in schema.entities)
        avg_properties_per_entity = total_properties / entity_count if entity_count > 0 else 0.0
        
        # Average properties per relation
        total_relation_props = sum(len(r.properties) for r in schema.relations)
        avg_properties_per_relation = total_relation_props / relation_count if relation_count > 0 else 0.0
        
        # Score based on coverage
        score = 0.0
        if entity_count >= 5:
            score += 0.4
        elif entity_count >= 3:
            score += 0.3
        elif entity_count >= 1:
            score += 0.15
        
        if relation_count >= 5:
            score += 0.3
        elif relation_count >= 2:
            score += 0.2
        elif relation_count >= 1:
            score += 0.1
        
        if avg_properties_per_entity >= 3:
            score += 0.2
        elif avg_properties_per_entity >= 1:
            score += 0.1
        
        if avg_properties_per_relation >= 1:
            score += 0.1
        
        return {
            "score": min(score, 1.0),
            "entity_count": entity_count,
            "relation_count": relation_count,
            "avg_properties_per_entity": avg_properties_per_entity,
            "avg_properties_per_relation": avg_properties_per_relation,
        }
    
    def _evaluate_structure(self, schema: OntologySchema) -> Dict[str, Any]:
        """
        Evaluate structure: Schema organization and structure quality
        
        Metrics:
        - Schema organization
        - Property indexing
        - Required field coverage
        """
        score = 0.0
        
        # Check for indexed properties (important for query performance)
        total_properties = sum(len(e.properties) for e in schema.entities)
        indexed_properties = sum(
            sum(1 for p in e.properties if p.indexed)
            for e in schema.entities
        )
        indexing_rate = indexed_properties / total_properties if total_properties > 0 else 0.0
        score += indexing_rate * 0.3
        
        # Check for required properties
        required_properties = sum(
            sum(1 for p in e.properties if p.required)
            for e in schema.entities
        )
        required_rate = required_properties / total_properties if total_properties > 0 else 0.0
        score += required_rate * 0.3
        
        # Check schema version
        if schema.version:
            score += 0.2
        
        # Check for hierarchies (indicates good structure)
        if schema.hierarchies:
            score += 0.2
        
        return {
            "score": min(score, 1.0),
            "indexing_rate": indexing_rate,
            "required_property_rate": required_rate,
            "hierarchy_count": len(schema.hierarchies),
        }
    
    def _get_grade(self, score: float) -> str:
        """Convert score to letter grade"""
        if score >= 0.9:
            return "A"
        elif score >= 0.8:
            return "B"
        elif score >= 0.7:
            return "C"
        elif score >= 0.6:
            return "D"
        else:
            return "F"
    
    def _generate_recommendations(self, metrics: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on evaluation"""
        recommendations = []
        
        # Completeness recommendations
        if metrics["completeness"]["score"] < 0.7:
            if metrics["completeness"]["entity_count"] < 3:
                recommendations.append("Add more entity types to improve domain coverage")
            if metrics["completeness"]["relation_count"] < 2:
                recommendations.append("Add more relation types to connect entities")
            if metrics["completeness"]["property_coverage"] < 0.8:
                recommendations.append("Add properties to entities for better data modeling")
        
        # Consistency recommendations
        if metrics["consistency"]["score"] < 0.8:
            if metrics["consistency"]["issue_count"] > 0:
                recommendations.append(f"Fix {metrics['consistency']['issue_count']} consistency issues")
        
        # Coherence recommendations
        if metrics["coherence"]["score"] < 0.7:
            if metrics["coherence"]["hierarchies"] == 0:
                recommendations.append("Consider adding hierarchical relationships between entities")
            if metrics["coherence"]["naming_consistency"] < 0.8:
                recommendations.append("Standardize naming conventions across entities and relations")
        
        # Coverage recommendations
        if metrics["coverage"]["score"] < 0.7:
            recommendations.append("Expand schema to cover more domain concepts")
        
        # Structure recommendations
        if metrics["structure"]["score"] < 0.7:
            if metrics["structure"]["indexing_rate"] < 0.5:
                recommendations.append("Add indexes to frequently queried properties")
            if metrics["structure"]["required_property_rate"] < 0.3:
                recommendations.append("Mark essential properties as required")
        
        return recommendations if recommendations else ["Schema quality is good!"]
