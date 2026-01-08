"""Graph construction agent"""

from typing import Dict, Any, List, Optional
from loguru import logger
import hashlib

from .base_agent import BaseAgent
from ..graph.graph_store import GraphStore


class GraphConstructionAgent(BaseAgent):
    """Agent responsible for constructing the knowledge graph"""
    
    def __init__(self, graph_store: GraphStore, config: Optional[Dict[str, Any]] = None):
        """
        Initialize graph construction agent
        
        Args:
            graph_store: Graph store instance
            config: Agent configuration
        """
        super().__init__(config)
        self.graph_store = graph_store
        self.batch_size = self.config.get("batch_insert_size", 1000)
        self.deduplicate = self.config.get("deduplicate_entities", True)
        self.merge_relations = self.config.get("merge_relations", True)
        self._entity_cache: Dict[str, str] = {}  # property_hash -> entity_id
    
    async def process(self, entities: List[Dict[str, Any]], relations: List[Dict[str, Any]], workspace_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Add entities and relations to graph
        
        Args:
            entities: List of entities to add
            relations: List of relations to add
            workspace_id: Optional workspace ID for namespace isolation
            
        Returns:
            Statistics about the operation
        """
        if not self.is_enabled():
            logger.warning(f"{self.name} is disabled, skipping")
            return {"entities_added": 0, "relations_added": 0}
        
        stats = {"entities_added": 0, "relations_added": 0, "entities_skipped": 0, "relations_skipped": 0}
        
        # Process entities
        for entity in entities:
            entity_id = await self._add_entity(entity, workspace_id)
            if entity_id:
                stats["entities_added"] += 1
            else:
                stats["entities_skipped"] += 1
        
        # Process relations
        for relation in relations:
            success = await self._add_relation(relation, workspace_id)
            if success:
                stats["relations_added"] += 1
            else:
                stats["relations_skipped"] += 1
        
        logger.info(f"{self.name} added {stats['entities_added']} entities and {stats['relations_added']} relations to workspace {workspace_id}")
        return stats
    
    async def _add_entity(self, entity: Dict[str, Any], workspace_id: Optional[str] = None) -> Optional[str]:
        """
        Add entity to graph
        
        Args:
            entity: Entity data
            workspace_id: Optional workspace ID for namespace isolation
            
        Returns:
            Entity ID if successful, None otherwise
        """
        entity_type = entity.get("type", "Entity")
        properties = {k: v for k, v in entity.items() if k not in ["type", "id"]}
        
        # Generate entity ID
        entity_id = entity.get("id")
        if not entity_id:
            entity_id = self._generate_entity_id(entity_type, properties)
        
        # Check for duplicates
        if self.deduplicate:
            prop_hash = self._hash_properties(properties)
            cache_key = f"{workspace_id or 'default'}:{prop_hash}"
            if cache_key in self._entity_cache:
                existing_id = self._entity_cache[cache_key]
                logger.debug(f"Duplicate entity found, using existing: {existing_id}")
                return existing_id
            self._entity_cache[cache_key] = entity_id
        
        # Add to graph with workspace namespace
        success = self.graph_store.add_entity(entity_type, entity_id, properties, workspace_id=workspace_id)
        if success:
            return entity_id
        return None
    
    async def _add_relation(self, relation: Dict[str, Any], workspace_id: Optional[str] = None) -> bool:
        """
        Add relation to graph
        
        Args:
            relation: Relation data
            workspace_id: Optional workspace ID for namespace isolation
            
        Returns:
            True if successful
        """
        relation_type = relation.get("type", "RELATED_TO")
        source_id = relation.get("source_id") or relation.get("source")
        target_id = relation.get("target_id") or relation.get("target")
        
        if not source_id or not target_id:
            logger.warning(f"Missing source or target ID in relation: {relation}")
            return False
        
        properties = {k: v for k, v in relation.items() 
                     if k not in ["type", "source_id", "source", "target_id", "target"]}
        
        # Check for existing relation if merge is enabled
        if self.merge_relations:
            existing = self.graph_store.query_relations(
                relation_type=relation_type,
                source_id=source_id,
                target_id=target_id,
                limit=1,
                workspace_id=workspace_id
            )
            if existing:
                logger.debug(f"Relation already exists, skipping: {relation_type} from {source_id} to {target_id}")
                return True
        
        return self.graph_store.add_relation(relation_type, source_id, target_id, properties, workspace_id)
    
    def _generate_entity_id(self, entity_type: str, properties: Dict[str, Any]) -> str:
        """
        Generate unique entity ID
        
        Args:
            entity_type: Entity type
            properties: Entity properties
            
        Returns:
            Generated entity ID
        """
        # Try to use a unique identifier property
        for key in ["id", "name", "title", "email", "url"]:
            if key in properties and properties[key]:
                value = str(properties[key])
                return f"{entity_type}:{value}"
        
        # Fallback to hash
        prop_str = str(sorted(properties.items()))
        prop_hash = hashlib.md5(prop_str.encode()).hexdigest()[:8]
        return f"{entity_type}:{prop_hash}"
    
    def _hash_properties(self, properties: Dict[str, Any]) -> str:
        """Hash properties for deduplication"""
        # Normalize properties
        normalized = {}
        for k, v in sorted(properties.items()):
            if isinstance(v, str):
                normalized[k] = v.lower().strip()
            else:
                normalized[k] = str(v).lower().strip()
        prop_str = str(sorted(normalized.items()))
        return hashlib.md5(prop_str.encode()).hexdigest()

