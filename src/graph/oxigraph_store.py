"""Oxigraph SPARQL graph store implementation"""

from typing import Dict, Any, List, Optional
from loguru import logger
from urllib.parse import quote
import requests
from requests.exceptions import ConnectionError as RequestsConnectionError
from .graph_store import GraphStore


class OxigraphGraphStore(GraphStore):
    """Oxigraph SPARQL graph store with workspace namespace support"""
    
    def __init__(self, sparql_endpoint: str, update_endpoint: str, default_graph_uri: str = "http://sundaygraph.org/graph", timeout: int = 30):
        """
        Initialize Oxigraph graph store
        
        Args:
            sparql_endpoint: SPARQL query endpoint URL
            update_endpoint: SPARQL update endpoint URL
            default_graph_uri: Default graph URI for data
            timeout: Request timeout in seconds
        """
        self.sparql_endpoint = sparql_endpoint
        self.update_endpoint = update_endpoint
        self.default_graph_uri = default_graph_uri
        self.timeout = timeout
        
        # Test connection (non-blocking, allow graceful degradation)
        try:
            response = requests.get(f"{sparql_endpoint}?query={quote('SELECT * WHERE { ?s ?p ?o } LIMIT 1')}", timeout=5)
            response.raise_for_status()
            logger.info(f"Connected to Oxigraph at {sparql_endpoint}")
        except Exception as e:
            logger.warning(f"Could not verify Oxigraph connection: {e}. Will attempt connection on first use.")
    
    def _get_graph_uri(self, workspace_id: Optional[str] = None) -> str:
        """Get graph URI for workspace"""
        if workspace_id:
            return f"{self.default_graph_uri}/workspace/{workspace_id}"
        return self.default_graph_uri
    
    def _uri_encode(self, value: str) -> str:
        """Encode value as URI"""
        return quote(value, safe='')
    
    def _entity_to_uri(self, entity_id: str) -> str:
        """Convert entity ID to URI"""
        return f"http://sundaygraph.org/entity/{self._uri_encode(entity_id)}"
    
    def _type_to_uri(self, entity_type: str) -> str:
        """Convert entity type to URI"""
        return f"http://sundaygraph.org/type/{self._uri_encode(entity_type)}"
    
    def _relation_to_uri(self, relation_type: str) -> str:
        """Convert relation type to URI"""
        return f"http://sundaygraph.org/relation/{self._uri_encode(relation_type)}"
    
    def _execute_sparql_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute SPARQL SELECT query"""
        try:
            response = requests.get(
                self.sparql_endpoint,
                params={"query": query},
                headers={"Accept": "application/sparql-results+json"},
                timeout=self.timeout
            )
            response.raise_for_status()
            result = response.json()
            
            if "results" in result and "bindings" in result["results"]:
                return result["results"]["bindings"]
            return []
        except RequestsConnectionError as e:
            logger.warning(f"Oxigraph connection failed: {e}. Is Oxigraph running? Returning empty results.")
            return []
        except Exception as e:
            logger.error(f"SPARQL query error: {e}")
            return []
    
    def _execute_sparql_update(self, update: str) -> bool:
        """Execute SPARQL UPDATE query"""
        try:
            response = requests.post(
                self.update_endpoint,
                data={"update": update},
                headers={"Content-Type": "application/sparql-update"},
                timeout=self.timeout
            )
            response.raise_for_status()
            return True
        except RequestsConnectionError as e:
            logger.warning(f"Oxigraph connection failed: {e}. Is Oxigraph running? Update operation failed.")
            return False
        except Exception as e:
            logger.error(f"SPARQL update error: {e}")
            return False
    
    def add_entity(
        self, 
        entity_type: str, 
        entity_id: str, 
        properties: Dict[str, Any],
        workspace_id: Optional[str] = None
    ) -> bool:
        """Add or update an entity"""
        graph_uri = self._get_graph_uri(workspace_id)
        entity_uri = self._entity_to_uri(entity_id)
        type_uri = self._type_to_uri(entity_type)
        
        # Build SPARQL UPDATE to insert entity
        triples = [
            f"<{entity_uri}> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <{type_uri}>",
            f"<{entity_uri}> <http://sundaygraph.org/property/id> \"{entity_id}\"",
            f"<{entity_uri}> <http://sundaygraph.org/property/type> \"{entity_type}\""
        ]
        
        if workspace_id:
            triples.append(f"<{entity_uri}> <http://sundaygraph.org/property/workspace_id> \"{workspace_id}\"")
        
        # Add properties as RDF triples
        for key, value in properties.items():
            if isinstance(value, str):
                # Escape quotes in string values
                value_escaped = value.replace('"', '\\"')
                triples.append(f"<{entity_uri}> <http://sundaygraph.org/property/{self._uri_encode(key)}> \"{value_escaped}\"")
            elif isinstance(value, (int, float, bool)):
                triples.append(f"<{entity_uri}> <http://sundaygraph.org/property/{self._uri_encode(key)}> \"{value}\"^^<http://www.w3.org/2001/XMLSchema#string>")
            else:
                triples.append(f"<{entity_uri}> <http://sundaygraph.org/property/{self._uri_encode(key)}> \"{str(value)}\"")
        
        update_query = f"""
        INSERT DATA {{
            GRAPH <{graph_uri}> {{
                {' . '.join(triples)}
            }}
        }}
        """
        
        return self._execute_sparql_update(update_query)
    
    def add_relation(
        self,
        relation_type: str,
        source_id: str,
        target_id: str,
        properties: Optional[Dict[str, Any]] = None,
        workspace_id: Optional[str] = None
    ) -> bool:
        """Add or update a relation"""
        graph_uri = self._get_graph_uri(workspace_id)
        source_uri = self._entity_to_uri(source_id)
        target_uri = self._entity_to_uri(target_id)
        relation_uri = self._relation_to_uri(relation_type)
        
        triples = [
            f"<{source_uri}> <{relation_uri}> <{target_uri}>"
        ]
        
        if workspace_id:
            # Store workspace_id as a property of the relation (using reification)
            relation_node = f"<http://sundaygraph.org/relation/{self._uri_encode(f'{source_id}_{target_id}_{relation_type}')}>"
            triples.extend([
                f"<{source_uri}> <{relation_uri}> <{target_uri}>",
                f"{relation_node} <http://sundaygraph.org/property/workspace_id> \"{workspace_id}\"",
                f"{relation_node} <http://sundaygraph.org/property/type> \"{relation_type}\""
            ])
        
        if properties:
            for key, value in properties.items():
                if isinstance(value, str):
                    value_escaped = value.replace('"', '\\"')
                    triples.append(f"<{source_uri}> <http://sundaygraph.org/relation/{self._uri_encode(relation_type)}/{self._uri_encode(key)}> \"{value_escaped}\"")
                else:
                    triples.append(f"<{source_uri}> <http://sundaygraph.org/relation/{self._uri_encode(relation_type)}/{self._uri_encode(key)}> \"{str(value)}\"")
        
        update_query = f"""
        INSERT DATA {{
            GRAPH <{graph_uri}> {{
                {' . '.join(triples)}
            }}
        }}
        """
        
        return self._execute_sparql_update(update_query)
    
    def get_entity(self, entity_id: str, workspace_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get entity by ID"""
        graph_uri = self._get_graph_uri(workspace_id)
        entity_uri = self._entity_to_uri(entity_id)
        
        query = f"""
        SELECT ?p ?o WHERE {{
            GRAPH <{graph_uri}> {{
                <{entity_uri}> ?p ?o
            }}
        }}
        """
        
        results = self._execute_sparql_query(query)
        if not results:
            return None
        
        entity = {"id": entity_id}
        for binding in results:
            pred = binding.get("p", {}).get("value", "")
            obj = binding.get("o", {}).get("value", "")
            
            # Extract property name from URI
            if "property/" in pred:
                prop_name = pred.split("property/")[-1]
                entity[prop_name] = obj
            elif "type" in pred:
                entity["type"] = obj.split("/")[-1] if "/" in obj else obj
        
        return entity
    
    def query_entities(
        self,
        entity_type: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        workspace_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Query entities"""
        graph_uri = self._get_graph_uri(workspace_id)
        
        where_clauses = ["?s ?p ?o"]
        if entity_type:
            type_uri = self._type_to_uri(entity_type)
            where_clauses.append(f"?s <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <{type_uri}>")
        
        if workspace_id:
            where_clauses.append(f"?s <http://sundaygraph.org/property/workspace_id> \"{workspace_id}\"")
        
        if filters:
            for key, value in filters.items():
                where_clauses.append(f"?s <http://sundaygraph.org/property/{self._uri_encode(key)}> \"{value}\"")
        
        query = f"""
        SELECT DISTINCT ?s WHERE {{
            GRAPH <{graph_uri}> {{
                {' . '.join(where_clauses)}
            }}
        }} LIMIT {limit}
        """
        
        results = self._execute_sparql_query(query)
        entities = []
        
        for binding in results:
            entity_uri = binding.get("s", {}).get("value", "")
            if entity_uri:
                # Extract entity ID from URI
                entity_id = entity_uri.split("/")[-1] if "/" in entity_uri else entity_uri
                entity = self.get_entity(entity_id, workspace_id)
                if entity:
                    entities.append(entity)
        
        return entities
    
    def query_relations(
        self,
        relation_type: Optional[str] = None,
        source_id: Optional[str] = None,
        target_id: Optional[str] = None,
        limit: int = 100,
        workspace_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Query relations"""
        graph_uri = self._get_graph_uri(workspace_id)
        
        where_clauses = []
        if source_id:
            source_uri = self._entity_to_uri(source_id)
            where_clauses.append(f"<{source_uri}> ?p ?o")
        else:
            where_clauses.append("?s ?p ?o")
        
        if target_id:
            target_uri = self._entity_to_uri(target_id)
            where_clauses.append(f"?s ?p <{target_uri}>")
        
        if relation_type:
            relation_uri = self._relation_to_uri(relation_type)
            where_clauses.append(f"?s <{relation_uri}> ?o")
        
        if workspace_id:
            where_clauses.append(f"?s <http://sundaygraph.org/property/workspace_id> \"{workspace_id}\"")
        
        query = f"""
        SELECT ?s ?p ?o WHERE {{
            GRAPH <{graph_uri}> {{
                {' . '.join(where_clauses)}
            }}
        }} LIMIT {limit}
        """
        
        results = self._execute_sparql_query(query)
        relations = []
        
        for binding in results:
            source_uri = binding.get("s", {}).get("value", "")
            pred_uri = binding.get("p", {}).get("value", "")
            target_uri = binding.get("o", {}).get("value", "")
            
            if source_uri and target_uri and "relation/" in pred_uri:
                source_id = source_uri.split("/")[-1] if "/" in source_uri else source_uri
                target_id = target_uri.split("/")[-1] if "/" in target_uri else target_uri
                rel_type = pred_uri.split("relation/")[-1] if "relation/" in pred_uri else "RELATED_TO"
                
                relations.append({
                    "source": source_id,
                    "target": target_id,
                    "type": rel_type
                })
        
        return relations
    
    def get_neighbors(
        self,
        entity_id: str,
        relation_types: Optional[List[str]] = None,
        direction: str = "both",
        workspace_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get neighboring entities"""
        graph_uri = self._get_graph_uri(workspace_id)
        entity_uri = self._entity_to_uri(entity_id)
        
        if direction == "out":
            query = f"""
            SELECT ?p ?o WHERE {{
                GRAPH <{graph_uri}> {{
                    <{entity_uri}> ?p ?o
                }}
            }}
            """
        elif direction == "in":
            query = f"""
            SELECT ?s ?p WHERE {{
                GRAPH <{graph_uri}> {{
                    ?s ?p <{entity_uri}>
                }}
            }}
            """
        else:  # both
            query = f"""
            SELECT ?s ?p ?o WHERE {{
                GRAPH <{graph_uri}> {{
                    {{
                        <{entity_uri}> ?p ?o
                    }} UNION {{
                        ?s ?p <{entity_uri}>
                    }}
                }}
            }}
            """
        
        results = self._execute_sparql_query(query)
        neighbors = []
        
        for binding in results:
            if direction == "out":
                neighbor_uri = binding.get("o", {}).get("value", "")
            elif direction == "in":
                neighbor_uri = binding.get("s", {}).get("value", "")
            else:
                neighbor_uri = binding.get("o", {}).get("value") or binding.get("s", {}).get("value", "")
            
            if neighbor_uri and neighbor_uri != entity_uri:
                neighbor_id = neighbor_uri.split("/")[-1] if "/" in neighbor_uri else neighbor_uri
                neighbor = self.get_entity(neighbor_id, workspace_id)
                if neighbor:
                    neighbors.append(neighbor)
        
        return neighbors
    
    def delete_entity(self, entity_id: str) -> bool:
        """Delete an entity"""
        entity_uri = self._entity_to_uri(entity_id)
        
        update_query = f"""
        DELETE WHERE {{
            ?s ?p ?o .
            FILTER (?s = <{entity_uri}> || ?o = <{entity_uri}>)
        }}
        """
        
        return self._execute_sparql_update(update_query)
    
    def clear(self) -> None:
        """Clear all data"""
        update_query = "DELETE WHERE { ?s ?p ?o }"
        self._execute_sparql_update(update_query)
        logger.info("Cleared Oxigraph database")
    
    def get_stats(self, workspace_id: Optional[str] = None) -> Dict[str, Any]:
        """Get graph statistics"""
        graph_uri = self._get_graph_uri(workspace_id)
        
        query = f"""
        SELECT (COUNT(DISTINCT ?s) AS ?nodes) (COUNT(?p) AS ?edges) WHERE {{
            GRAPH <{graph_uri}> {{
                ?s ?p ?o
            }}
        }}
        """
        
        results = self._execute_sparql_query(query)
        if results:
            binding = results[0]
            return {
                "nodes": int(binding.get("nodes", {}).get("value", 0)),
                "edges": int(binding.get("edges", {}).get("value", 0)),
                "workspace_id": workspace_id,
                "backend": "oxigraph"
            }
        
        return {"nodes": 0, "edges": 0, "workspace_id": workspace_id, "backend": "oxigraph"}
