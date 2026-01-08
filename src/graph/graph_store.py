"""Graph storage backends"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger


class GraphStore(ABC):
    """Abstract base class for graph storage"""
    
    @abstractmethod
    def add_entity(
        self, 
        entity_type: str, 
        entity_id: str, 
        properties: Dict[str, Any],
        workspace_id: Optional[str] = None
    ) -> bool:
        """Add or update an entity"""
        pass
    
    @abstractmethod
    def add_relation(
        self,
        relation_type: str,
        source_id: str,
        target_id: str,
        properties: Optional[Dict[str, Any]] = None,
        workspace_id: Optional[str] = None
    ) -> bool:
        """Add or update a relation"""
        pass
    
    @abstractmethod
    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get entity by ID"""
        pass
    
    @abstractmethod
    def query_entities(
        self,
        entity_type: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        workspace_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Query entities"""
        pass
    
    @abstractmethod
    def query_relations(
        self,
        relation_type: Optional[str] = None,
        source_id: Optional[str] = None,
        target_id: Optional[str] = None,
        limit: int = 100,
        workspace_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Query relations"""
        pass
    
    @abstractmethod
    def get_neighbors(
        self,
        entity_id: str,
        relation_types: Optional[List[str]] = None,
        direction: str = "both",
        workspace_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get neighboring entities"""
        pass
    
    @abstractmethod
    def delete_entity(self, entity_id: str) -> bool:
        """Delete an entity"""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all data"""
        pass
    
    @abstractmethod
    def get_stats(self, workspace_id: Optional[str] = None) -> Dict[str, Any]:
        """Get graph statistics"""
        pass


class MemoryGraphStore(GraphStore):
    """In-memory graph store using NetworkX with workspace namespace support"""
    
    def __init__(self, directed: bool = True, multigraph: bool = False):
        """
        Initialize memory graph store
        
        Args:
            directed: Whether graph is directed
            multigraph: Whether to allow multiple edges between nodes
        """
        try:
            import networkx as nx
        except ImportError:
            raise ImportError("NetworkX is required for memory graph store. Install with: pip install networkx")
        
        self.directed = directed
        self.multigraph = multigraph
        # Store graphs per workspace: {workspace_id: graph}
        self.graphs: Dict[str, Any] = {}
        # Store entity properties per workspace: {workspace_id: {entity_id: properties}}
        self.entity_properties: Dict[str, Dict[str, Dict[str, Any]]] = {}
        # Store relation properties per workspace: {workspace_id: {(source, target, type): properties}}
        self.relation_properties: Dict[str, Dict[Tuple[str, str, str], Dict[str, Any]]] = {}
        logger.info("Initialized memory graph store with workspace namespace support")
    
    def _get_graph(self, workspace_id: Optional[str] = None) -> Any:
        """Get or create graph for workspace"""
        workspace_key = workspace_id or "default"
        if workspace_key not in self.graphs:
            import networkx as nx
            self.graphs[workspace_key] = nx.DiGraph() if self.directed else nx.Graph()
            self.entity_properties[workspace_key] = {}
            self.relation_properties[workspace_key] = {}
        return self.graphs[workspace_key]
    
    def _get_workspace_key(self, workspace_id: Optional[str] = None) -> str:
        """Get workspace key for storage"""
        return workspace_id or "default"
    
    def add_entity(
        self, 
        entity_type: str, 
        entity_id: str, 
        properties: Dict[str, Any],
        workspace_id: Optional[str] = None
    ) -> bool:
        """Add or update an entity"""
        try:
            workspace_key = self._get_workspace_key(workspace_id)
            graph = self._get_graph(workspace_id)
            
            # Store entity properties
            full_properties = {
                "type": entity_type,
                "id": entity_id,
                "workspace_id": workspace_id,
                **properties
            }
            self.entity_properties[workspace_key][entity_id] = full_properties
            
            # Add node to graph if not exists
            if not graph.has_node(entity_id):
                graph.add_node(entity_id)
            
            # Update node attributes
            graph.nodes[entity_id].update(full_properties)
            
            return True
        except Exception as e:
            logger.error(f"Error adding entity {entity_id} to workspace {workspace_id}: {e}")
            return False
    
    def add_relation(
        self,
        relation_type: str,
        source_id: str,
        target_id: str,
        properties: Optional[Dict[str, Any]] = None,
        workspace_id: Optional[str] = None
    ) -> bool:
        """Add or update a relation"""
        try:
            workspace_key = self._get_workspace_key(workspace_id)
            graph = self._get_graph(workspace_id)
            
            # Ensure nodes exist
            if not graph.has_node(source_id):
                graph.add_node(source_id)
            if not graph.has_node(target_id):
                graph.add_node(target_id)
            
            # Store relation properties
            properties = properties or {}
            properties["workspace_id"] = workspace_id
            relation_key = (source_id, target_id, relation_type)
            self.relation_properties[workspace_key][relation_key] = properties
            
            # Add edge
            edge_data = {"type": relation_type, "workspace_id": workspace_id, **properties}
            graph.add_edge(source_id, target_id, **edge_data)
            
            return True
        except Exception as e:
            logger.error(f"Error adding relation {relation_type} from {source_id} to {target_id} in workspace {workspace_id}: {e}")
            return False
    
    def get_entity(self, entity_id: str, workspace_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get entity by ID"""
        workspace_key = self._get_workspace_key(workspace_id)
        if workspace_key not in self.entity_properties:
            return None
        if entity_id not in self.entity_properties[workspace_key]:
            return None
        return self.entity_properties[workspace_key][entity_id].copy()
    
    def query_entities(
        self,
        entity_type: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        workspace_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Query entities"""
        workspace_key = self._get_workspace_key(workspace_id)
        if workspace_key not in self.entity_properties:
            return []
        
        results = []
        filters = filters or {}
        
        for entity_id, properties in self.entity_properties[workspace_key].items():
            # Filter by type
            if entity_type and properties.get("type") != entity_type:
                continue
            
            # Apply filters
            match = True
            for key, value in filters.items():
                if properties.get(key) != value:
                    match = False
                    break
            
            if match:
                results.append(properties.copy())
                if len(results) >= limit:
                    break
        
        return results
    
    def query_relations(
        self,
        relation_type: Optional[str] = None,
        source_id: Optional[str] = None,
        target_id: Optional[str] = None,
        limit: int = 100,
        workspace_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Query relations"""
        workspace_key = self._get_workspace_key(workspace_id)
        if workspace_key not in self.relation_properties:
            return []
        
        results = []
        count = 0
        
        for (src, tgt, rel_type), props in self.relation_properties[workspace_key].items():
            # Apply filters
            if relation_type and rel_type != relation_type:
                continue
            if source_id and src != source_id:
                continue
            if target_id and tgt != target_id:
                continue
            
            results.append({
                "type": rel_type,
                "source": src,
                "target": tgt,
                **props
            })
            
            count += 1
            if count >= limit:
                break
        
        return results
    
    def get_neighbors(
        self,
        entity_id: str,
        relation_types: Optional[List[str]] = None,
        direction: str = "both",
        workspace_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get neighboring entities"""
        workspace_key = self._get_workspace_key(workspace_id)
        graph = self._get_graph(workspace_id)
        
        if not graph.has_node(entity_id):
            return []
        
        neighbors = []
        
        if direction in ["out", "both"]:
            for target_id in graph.successors(entity_id):
                for edge_data in graph[entity_id][target_id].values():
                    rel_type = edge_data.get("type", "")
                    if not relation_types or rel_type in relation_types:
                        neighbor = self.get_entity(target_id, workspace_id)
                        if neighbor:
                            neighbor["relation"] = rel_type
                            neighbor["direction"] = "out"
                            neighbors.append(neighbor)
        
        if direction in ["in", "both"]:
            for source_id in graph.predecessors(entity_id):
                for edge_data in graph[source_id][entity_id].values():
                    rel_type = edge_data.get("type", "")
                    if not relation_types or rel_type in relation_types:
                        neighbor = self.get_entity(source_id, workspace_id)
                        if neighbor:
                            neighbor["relation"] = rel_type
                            neighbor["direction"] = "in"
                            neighbors.append(neighbor)
        
        return neighbors
    
    def delete_entity(self, entity_id: str) -> bool:
        """Delete an entity"""
        try:
            if entity_id in self.entity_properties:
                del self.entity_properties[entity_id]
            
            if self.graph.has_node(entity_id):
                self.graph.remove_node(entity_id)
            
            # Remove related relation properties
            keys_to_remove = [
                key for key in self.relation_properties.keys()
                if key[0] == entity_id or key[1] == entity_id
            ]
            for key in keys_to_remove:
                del self.relation_properties[key]
            
            return True
        except Exception as e:
            logger.error(f"Error deleting entity {entity_id}: {e}")
            return False
    
    def clear(self) -> None:
        """Clear all data"""
        self.graph.clear()
        self.entity_properties.clear()
        self.relation_properties.clear()
        logger.info("Cleared graph store")
    
    def get_stats(self, workspace_id: Optional[str] = None) -> Dict[str, Any]:
        """Get graph statistics"""
        workspace_key = self._get_workspace_key(workspace_id)
        graph = self._get_graph(workspace_id)
        
        entity_props = self.entity_properties.get(workspace_key, {})
        relation_props = self.relation_properties.get(workspace_key, {})
        
        return {
            "nodes": graph.number_of_nodes(),
            "edges": graph.number_of_edges(),
            "entity_types": len(set(
                props.get("type") for props in entity_props.values()
            )),
            "relation_types": len(set(
                key[2] for key in relation_props.keys()
            )),
            "workspace_id": workspace_id,
            "backend": "memory"
        }


class Neo4jGraphStore(GraphStore):
    """Neo4j graph store"""
    
    def __init__(self, uri: str, user: str, password: str, database: str = "neo4j"):
        """
        Initialize Neo4j graph store
        
        Args:
            uri: Neo4j connection URI
            user: Username
            password: Password
            database: Database name
        """
        try:
            from neo4j import GraphDatabase
        except ImportError:
            raise ImportError("Neo4j driver is required. Install with: pip install neo4j")
        
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.database = database
        
        # Test connection
        with self.driver.session(database=database) as session:
            session.run("RETURN 1")
        
        logger.info(f"Connected to Neo4j at {uri}")
    
    def _execute_write(self, query: str, parameters: Dict[str, Any]) -> bool:
        """Execute write query"""
        try:
            with self.driver.session(database=self.database) as session:
                session.run(query, parameters)
            return True
        except Exception as e:
            logger.error(f"Error executing write query: {e}")
            return False
    
    def _execute_read(self, query: str, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute read query"""
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(query, parameters)
                return [dict(record) for record in result]
        except Exception as e:
            logger.error(f"Error executing read query: {e}")
            return []
    
    def add_entity(
        self, 
        entity_type: str, 
        entity_id: str, 
        properties: Dict[str, Any]
    ) -> bool:
        """Add or update an entity"""
        props_str = ", ".join([f"`{k}`: ${k}" for k in properties.keys()])
        query = f"""
        MERGE (n:{entity_type} {{id: $id}})
        SET n += {{{props_str}}}
        RETURN n
        """
        params = {"id": entity_id, **properties}
        return self._execute_write(query, params)
    
    def add_relation(
        self,
        relation_type: str,
        source_id: str,
        target_id: str,
        properties: Optional[Dict[str, Any]] = None,
        workspace_id: Optional[str] = None
    ) -> bool:
        """Add or update a relation"""
        properties = properties or {}
        if workspace_id:
            properties["workspace_id"] = workspace_id
        props_str = ", ".join([f"`{k}`: ${k}" for k in properties.keys()]) if properties else ""
        props_set = f" SET r += {{{props_str}}}" if props_str else ""
        
        query = f"""
        MATCH (a {{id: $source_id}}), (b {{id: $target_id}})
        MERGE (a)-[r:{relation_type}]->(b)
        {props_set}
        RETURN r
        """
        params = {"source_id": source_id, "target_id": target_id, **properties}
        return self._execute_write(query, params)
    
    def get_entity(self, entity_id: str, workspace_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get entity by ID"""
        if workspace_id:
            query = "MATCH (n {id: $id, workspace_id: $workspace_id}) RETURN n"
            results = self._execute_read(query, {"id": entity_id, "workspace_id": workspace_id})
        else:
            query = "MATCH (n {id: $id}) RETURN n"
            results = self._execute_read(query, {"id": entity_id})
        if results:
            node = results[0]["n"]
            return dict(node)
        return None
    
    def query_entities(
        self,
        entity_type: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        workspace_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Query entities"""
        label = f":{entity_type}" if entity_type else ""
        filter_clauses = []
        params = {"limit": limit}
        
        if workspace_id:
            filter_clauses.append("n.workspace_id = $workspace_id")
            params["workspace_id"] = workspace_id
        
        if filters:
            for key, value in filters.items():
                filter_clauses.append(f"n.`{key}` = ${key}")
                params[key] = value
        
        where_clause = " WHERE " + " AND ".join(filter_clauses) if filter_clauses else ""
        query = f"MATCH (n{label}){where_clause} RETURN n LIMIT $limit"
        
        results = self._execute_read(query, params)
        return [dict(record["n"]) for record in results]
    
    def query_relations(
        self,
        relation_type: Optional[str] = None,
        source_id: Optional[str] = None,
        target_id: Optional[str] = None,
        limit: int = 100,
        workspace_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Query relations"""
        rel_type = f":{relation_type}" if relation_type else ""
        match_clauses = []
        params = {"limit": limit}
        where_clauses = []
        
        if source_id:
            match_clauses.append("(a {id: $source_id})")
            params["source_id"] = source_id
        else:
            match_clauses.append("(a)")
        
        if target_id:
            match_clauses.append("(b {id: $target_id})")
            params["target_id"] = target_id
        else:
            match_clauses.append("(b)")
        
        if workspace_id:
            where_clauses.append("r.workspace_id = $workspace_id")
            params["workspace_id"] = workspace_id
        
        where_clause = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        query = f"""
        MATCH {match_clauses[0]}-[r{rel_type}]->{match_clauses[1]}
        {where_clause}
        RETURN a, r, b
        LIMIT $limit
        """
        
        results = self._execute_read(query, params)
        return [
            {
                "source": dict(record["a"]).get("id", ""),
                "target": dict(record["b"]).get("id", ""),
                "type": list(record["r"].types())[0] if record["r"].types() else "",
                **dict(record["r"])
            }
            for record in results
        ]
    
    def get_neighbors(
        self,
        entity_id: str,
        relation_types: Optional[List[str]] = None,
        direction: str = "both",
        workspace_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get neighboring entities"""
        rel_types = "|".join(relation_types) if relation_types else ""
        rel_pattern = f":{rel_types}" if rel_types else ""
        
        if direction == "out":
            query = f"""
            MATCH (n {{id: $id}})-[r{rel_pattern}]->(m)
            RETURN m, type(r) as relation, 'out' as direction
            """
        elif direction == "in":
            query = f"""
            MATCH (n {{id: $id}})<-[r{rel_pattern}]-(m)
            RETURN m, type(r) as relation, 'in' as direction
            """
        else:  # both
            query = f"""
            MATCH (n {{id: $id}})-[r{rel_pattern}]-(m)
            RETURN m, type(r) as relation,
                   CASE WHEN startNode(r) = n THEN 'out' ELSE 'in' END as direction
            """
        
        results = self._execute_read(query, {"id": entity_id})
        return [
            {
                **dict(record["m"]),
                "relation": record["relation"],
                "direction": record["direction"]
            }
            for record in results
        ]
    
    def delete_entity(self, entity_id: str) -> bool:
        """Delete an entity"""
        query = "MATCH (n {id: $id}) DETACH DELETE n"
        return self._execute_write(query, {"id": entity_id})
    
    def clear(self) -> None:
        """Clear all data"""
        query = "MATCH (n) DETACH DELETE n"
        self._execute_write(query, {})
        logger.info("Cleared Neo4j database")
    
    def get_stats(self, workspace_id: Optional[str] = None) -> Dict[str, Any]:
        """Get graph statistics"""
        if workspace_id:
            query = """
            MATCH (n {workspace_id: $workspace_id})
            WITH count(n) as node_count
            MATCH ()-[r]->()
            WHERE r.workspace_id = $workspace_id
            WITH node_count, count(r) as edge_count
            RETURN node_count as nodes, edge_count as edges
            """
            results = self._execute_read(query, {"workspace_id": workspace_id})
        else:
            query = """
            MATCH (n)
            WITH count(n) as node_count
            MATCH ()-[r]->()
            WITH node_count, count(r) as edge_count
            RETURN node_count as nodes, edge_count as edges
            """
            results = self._execute_read(query, {})
        
        if results:
            return {
                "nodes": results[0]["nodes"],
                "edges": results[0]["edges"],
                "workspace_id": workspace_id,
                "backend": "neo4j"
            }
        return {"nodes": 0, "edges": 0, "workspace_id": workspace_id, "backend": "neo4j"}
    
    def close(self) -> None:
        """Close database connection"""
        self.driver.close()

