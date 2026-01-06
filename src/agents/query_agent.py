"""Query agent for graph queries"""

from typing import Dict, Any, List, Optional
from loguru import logger

from .base_agent import BaseAgent
from ..graph.graph_store import GraphStore


class QueryAgent(BaseAgent):
    """Agent responsible for querying the knowledge graph"""
    
    def __init__(self, graph_store: GraphStore, config: Optional[Dict[str, Any]] = None):
        """
        Initialize query agent
        
        Args:
            graph_store: Graph store instance
            config: Agent configuration
        """
        super().__init__(config)
        self.graph_store = graph_store
        self.max_results = self.config.get("max_results", 100)
        self.similarity_threshold = self.config.get("similarity_threshold", 0.7)
        self.use_semantic_search = self.config.get("use_semantic_search", True)
    
    async def process(self, query: str, query_type: str = "entity") -> List[Dict[str, Any]]:
        """
        Process a query
        
        Args:
            query: Query string
            query_type: Type of query ("entity", "relation", "neighbor", "path")
            
        Returns:
            Query results
        """
        if not self.is_enabled():
            logger.warning(f"{self.name} is disabled, skipping")
            return []
        
        logger.info(f"{self.name} processing query: {query}")
        
        if query_type == "entity":
            return await self.query_entities(query)
        elif query_type == "relation":
            return await self.query_relations(query)
        elif query_type == "neighbor":
            return await self.query_neighbors(query)
        elif query_type == "path":
            return await self.query_path(query)
        else:
            logger.warning(f"Unknown query type: {query_type}")
            return []
    
    async def query_entities(self, query: str) -> List[Dict[str, Any]]:
        """
        Query entities
        
        Args:
            query: Query string (can be entity ID, type, or property value)
            
        Returns:
            List of matching entities
        """
        # Try as entity ID first
        entity = self.graph_store.get_entity(query)
        if entity:
            return [entity]
        
        # Try as property search
        # Simple implementation - in production, use proper search
        results = self.graph_store.query_entities(limit=self.max_results)
        
        # Filter by query (simple text matching)
        filtered = []
        query_lower = query.lower()
        for result in results:
            # Check if query matches any property value
            for value in result.values():
                if isinstance(value, str) and query_lower in value.lower():
                    filtered.append(result)
                    break
        
        return filtered[:self.max_results]
    
    async def query_relations(
        self,
        query: str,
        source_id: Optional[str] = None,
        target_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query relations
        
        Args:
            query: Relation type or query string
            source_id: Optional source entity ID
            target_id: Optional target entity ID
            
        Returns:
            List of matching relations
        """
        return self.graph_store.query_relations(
            relation_type=query if source_id is None and target_id is None else None,
            source_id=source_id,
            target_id=target_id,
            limit=self.max_results
        )
    
    async def query_neighbors(
        self,
        entity_id: str,
        relation_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Query neighboring entities
        
        Args:
            entity_id: Entity ID
            relation_types: Optional list of relation types to filter
            
        Returns:
            List of neighboring entities
        """
        return self.graph_store.get_neighbors(
            entity_id,
            relation_types=relation_types,
            direction="both"
        )
    
    async def query_path(
        self,
        source_id: str,
        target_id: Optional[str] = None,
        max_depth: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Query paths between entities
        
        Args:
            source_id: Source entity ID
            target_id: Optional target entity ID
            max_depth: Maximum path depth
            
        Returns:
            List of paths
        """
        # Simple BFS implementation
        if target_id:
            return self._find_path(source_id, target_id, max_depth)
        else:
            return self._find_all_paths(source_id, max_depth)
    
    def _find_path(self, source_id: str, target_id: str, max_depth: int) -> List[Dict[str, Any]]:
        """Find path between two entities"""
        from collections import deque
        
        queue = deque([(source_id, [source_id])])
        visited = {source_id}
        
        while queue:
            current_id, path = queue.popleft()
            
            if len(path) > max_depth:
                continue
            
            if current_id == target_id:
                return [{"path": path, "length": len(path) - 1}]
            
            neighbors = self.graph_store.get_neighbors(current_id, direction="out")
            for neighbor in neighbors:
                neighbor_id = neighbor.get("id") or neighbor.get("name")
                if neighbor_id and neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, path + [neighbor_id]))
        
        return []
    
    def _find_all_paths(self, source_id: str, max_depth: int) -> List[Dict[str, Any]]:
        """Find all paths from source entity"""
        from collections import deque
        
        paths = []
        queue = deque([(source_id, [source_id])])
        
        while queue:
            current_id, path = queue.popleft()
            
            if len(path) > max_depth:
                continue
            
            if len(path) > 1:
                paths.append({"path": path.copy(), "length": len(path) - 1})
            
            neighbors = self.graph_store.get_neighbors(current_id, direction="out")
            for neighbor in neighbors:
                neighbor_id = neighbor.get("id") or neighbor.get("name")
                if neighbor_id and neighbor_id not in path:
                    queue.append((neighbor_id, path + [neighbor_id]))
        
        return paths[:self.max_results]
    
    async def get_graph_stats(self) -> Dict[str, Any]:
        """Get graph statistics"""
        return self.graph_store.get_stats()

