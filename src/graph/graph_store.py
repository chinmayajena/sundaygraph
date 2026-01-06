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
        properties: Dict[str, Any]
    ) -> bool:
        """Add or update an entity"""
        pass
    
    @abstractmethod
    def add_relation(
        self,
        relation_type: str,
        source_id: str,
        target_id: str,
        properties: Optional[Dict[str, Any]] = None
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
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query entities"""
        pass
    
    @abstractmethod
    def query_relations(
        self,
        relation_type: Optional[str] = None,
        source_id: Optional[str] = None,
        target_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query relations"""
        pass
    
    @abstractmethod
    def get_neighbors(
        self,
        entity_id: str,
        relation_types: Optional[List[str]] = None,
        direction: str = "both"
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
    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics"""
        pass


class MemoryGraphStore(GraphStore):
    """In-memory graph store using NetworkX"""
    
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
        self.graph = nx.DiGraph() if directed else nx.Graph()
        self.entity_properties: Dict[str, Dict[str, Any]] = {}
        self.relation_properties: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
        logger.info("Initialized memory graph store")
    
    def add_entity(
        self, 
        entity_type: str, 
        entity_id: str, 
        properties: Dict[str, Any]
    ) -> bool:
        """Add or update an entity"""
        try:
            # Store entity properties
            full_properties = {
                "type": entity_type,
                "id": entity_id,
                **properties
            }
            self.entity_properties[entity_id] = full_properties
            
            # Add node to graph if not exists
            if not self.graph.has_node(entity_id):
                self.graph.add_node(entity_id)
            
            # Update node attributes
            self.graph.nodes[entity_id].update(full_properties)
            
            return True
        except Exception as e:
            logger.error(f"Error adding entity {entity_id}: {e}")
            return False
    
    def add_relation(
        self,
        relation_type: str,
        source_id: str,
        target_id: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Add or update a relation"""
        try:
            # Ensure nodes exist
            if not self.graph.has_node(source_id):
                self.graph.add_node(source_id)
            if not self.graph.has_node(target_id):
                self.graph.add_node(target_id)
            
            # Store relation properties
            properties = properties or {}
            relation_key = (source_id, target_id, relation_type)
            self.relation_properties[relation_key] = properties
            
            # Add edge
            edge_data = {"type": relation_type, **properties}
            self.graph.add_edge(source_id, target_id, **edge_data)
            
            return True
        except Exception as e:
            logger.error(f"Error adding relation {relation_type} from {source_id} to {target_id}: {e}")
            return False
    
    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get entity by ID"""
        if entity_id not in self.entity_properties:
            return None
        return self.entity_properties[entity_id].copy()
    
    def query_entities(
        self,
        entity_type: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query entities"""
        results = []
        filters = filters or {}
        
        for entity_id, properties in self.entity_properties.items():
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
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query relations"""
        results = []
        count = 0
        
        for (src, tgt, rel_type), props in self.relation_properties.items():
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
        direction: str = "both"
    ) -> List[Dict[str, Any]]:
        """Get neighboring entities"""
        if not self.graph.has_node(entity_id):
            return []
        
        neighbors = []
        
        if direction in ["out", "both"]:
            for target_id in self.graph.successors(entity_id):
                for edge_data in self.graph[entity_id][target_id].values():
                    rel_type = edge_data.get("type", "")
                    if not relation_types or rel_type in relation_types:
                        neighbor = self.get_entity(target_id)
                        if neighbor:
                            neighbor["relation"] = rel_type
                            neighbor["direction"] = "out"
                            neighbors.append(neighbor)
        
        if direction in ["in", "both"]:
            for source_id in self.graph.predecessors(entity_id):
                for edge_data in self.graph[source_id][entity_id].values():
                    rel_type = edge_data.get("type", "")
                    if not relation_types or rel_type in relation_types:
                        neighbor = self.get_entity(source_id)
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
    
    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics"""
        return {
            "nodes": self.graph.number_of_nodes(),
            "edges": self.graph.number_of_edges(),
            "entity_types": len(set(
                props.get("type") for props in self.entity_properties.values()
            )),
            "relation_types": len(set(
                key[2] for key in self.relation_properties.keys()
            ))
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
        properties: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Add or update a relation"""
        properties = properties or {}
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
    
    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get entity by ID"""
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
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query entities"""
        label = f":{entity_type}" if entity_type else ""
        filter_clauses = []
        params = {"limit": limit}
        
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
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query relations"""
        rel_type = f":{relation_type}" if relation_type else ""
        match_clauses = []
        params = {"limit": limit}
        
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
        
        query = f"""
        MATCH {match_clauses[0]}-[r{rel_type}]->{match_clauses[1]}
        RETURN a, r, b
        LIMIT $limit
        """
        
        results = self._execute_read(query, params)
        return [
            {
                "source": dict(record["a"]),
                "target": dict(record["b"]),
                "type": list(record["r"].types())[0],
                **dict(record["r"])
            }
            for record in results
        ]
    
    def get_neighbors(
        self,
        entity_id: str,
        relation_types: Optional[List[str]] = None,
        direction: str = "both"
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
    
    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics"""
        query = """
        MATCH (n)
        WITH count(n) as node_count
        MATCH ()-[r]->()
        WITH node_count, count(r) as edge_count
        RETURN node_count as nodes, edge_count as edges
        """
        results = self._execute_read(query, {})
        if results:
            return dict(results[0])
        return {"nodes": 0, "edges": 0}
    
    def close(self) -> None:
        """Close database connection"""
        self.driver.close()

