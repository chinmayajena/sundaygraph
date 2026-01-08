"""Main SundayGraph orchestration class"""

from pathlib import Path
from typing import Dict, Any, List, Optional
from loguru import logger
import sys

from .config import Config
from ..ontology.ontology_manager import OntologyManager
from ..ontology.schema_builder import OntologySchemaBuilder
from ..graph.graph_store import GraphStore, MemoryGraphStore, Neo4jGraphStore
from ..storage.schema_store import SchemaStore
from ..agents.data_ingestion_agent import DataIngestionAgent
from ..agents.ontology_agent import OntologyAgent
from ..agents.graph_construction_agent import GraphConstructionAgent
from ..agents.query_agent import QueryAgent


class SundayGraph:
    """Main orchestration class for SundayGraph system"""
    
    def __init__(self, config_path: str | Path | None = None, config: Config | None = None):
        """
        Initialize SundayGraph system
        
        Args:
            config_path: Path to configuration YAML file
            config: Optional Config object (overrides config_path)
        """
        # Load configuration
        if config:
            self.config = config
        elif config_path:
            self.config = Config.from_yaml(config_path)
        else:
            # Use default config
            self.config = Config()
        
        # Setup logging
        self._setup_logging()
        
        # Initialize LLM service (required for schema building)
        llm_service = None
        if self.config.processing.llm.provider:
            try:
                from ..utils.llm_service import LLMService
                import os
                api_key = os.getenv("OPENAI_API_KEY") if self.config.processing.llm.provider == "openai" else None
                
                # Get cost optimization settings from config
                enable_cache = getattr(self.config.processing.llm, 'enable_cache', True)
                cache_ttl = getattr(self.config.processing.llm, 'cache_ttl', 3600)
                
                llm_service = LLMService(
                    provider=self.config.processing.llm.provider,
                    model=self.config.processing.llm.model,
                    temperature=self.config.processing.llm.temperature,
                    max_tokens=self.config.processing.llm.max_tokens,
                    enable_cache=enable_cache,
                    cache_ttl=cache_ttl
                )
                logger.info(
                    f"LLM service initialized: {self.config.processing.llm.provider}/{self.config.processing.llm.model} "
                    f"(cache: {enable_cache}, TTL: {cache_ttl}s)"
                )
                self.llm_service = llm_service
            except Exception as e:
                logger.warning(f"Failed to initialize LLM service: {e}")
                self.llm_service = None
        else:
            self.llm_service = None
        
        # Initialize schema store (PostgreSQL) if enabled
        self.schema_store = None
        if hasattr(self.config, 'schema_store') and getattr(self.config.schema_store, 'enabled', False):
            try:
                connection_string = getattr(self.config.schema_store, 'connection_string', None)
                if not connection_string:
                    # Build from individual parameters
                    host = getattr(self.config.schema_store, 'host', 'localhost')
                    port = getattr(self.config.schema_store, 'port', 5432)
                    database = getattr(self.config.schema_store, 'database', 'sundaygraph')
                    user = getattr(self.config.schema_store, 'user', 'postgres')
                    password = getattr(self.config.schema_store, 'password', 'password')
                    connection_string = f"postgresql://{user}:{password}@{host}:{port}/{database}"
                
                self.schema_store = SchemaStore(connection_string)
                logger.info("Schema store (PostgreSQL) initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize schema store: {e}")
        
        # Initialize schema builder (LLM-powered) with evaluation enabled
        self.schema_builder = None
        if self.llm_service and self.config.ontology.build_with_llm:
            enable_evaluation = getattr(self.config.ontology, 'enable_evaluation', True)
            self.schema_builder = OntologySchemaBuilder(
                self.llm_service,
                enable_evaluation=enable_evaluation
            )
            logger.info(f"Schema builder (LLM-powered) initialized (evaluation: {enable_evaluation})")
        
        # Load or build ontology schema
        self.ontology_manager = self._initialize_ontology()
        
        # Initialize lightweight graph store for data (like LightRAG)
        self.graph_store = self._create_graph_store()
        
        # Initialize agents
        self.data_ingestion_agent = DataIngestionAgent(
            config=self.config.agents.data_ingestion.model_dump()
        )
        
        # Merge LLM config into ontology agent config
        ontology_config = self.config.agents.ontology.model_dump()
        ontology_config["llm"] = self.config.processing.llm.model_dump()
        
        self.ontology_agent = OntologyAgent(
            ontology_manager=self.ontology_manager,
            config=ontology_config,
            llm_service=llm_service
        )
        
        self.graph_construction_agent = GraphConstructionAgent(
            graph_store=self.graph_store,
            config=self.config.agents.graph_construction.model_dump()
        )
        
        self.query_agent = QueryAgent(
            graph_store=self.graph_store,
            config=self.config.agents.query.model_dump()
        )
        
        logger.info("SundayGraph system initialized")
        logger.info(f"  - Schema: {'LLM-built' if self.schema_builder else 'YAML-based'}")
        logger.info(f"  - Schema Store: {'PostgreSQL' if self.schema_store else 'File-based'}")
        logger.info(f"  - Graph Store: {self.config.graph.backend}")
    
    def _setup_logging(self) -> None:
        """Setup logging configuration"""
        log_level = self.config.system.log_level
        log_file = self.config.system.log_file
        
        # Create log directory
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        
        # Configure loguru
        logger.remove()  # Remove default handler
        logger.add(
            sys.stderr,
            level=log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
        )
        logger.add(
            log_file,
            level=log_level,
            rotation="10 MB",
            retention="7 days",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}"
        )
    
    def _initialize_ontology(self) -> OntologyManager:
        """Initialize ontology manager, loading from PostgreSQL or YAML"""
        # Try to load from PostgreSQL first
        if self.schema_store:
            schema_data = self.schema_store.get_active_schema()
            if schema_data:
                logger.info(f"Loaded schema from PostgreSQL: {schema_data.get('version', 'unknown')}")
                # Create temporary YAML file or load directly
                # For now, use the schema_path as fallback
                # TODO: Load schema directly from dict
        
        # Fallback to YAML file
        return OntologyManager(
            schema_path=self.config.ontology.schema_path,
            strict_mode=self.config.ontology.strict_mode
        )
    
    async def build_schema_from_domain(self, domain_description: str) -> Dict[str, Any]:
        """
        Build ontology schema from domain description using LLM reasoning
        
        Args:
            domain_description: Description of the domain
            
        Returns:
            Schema information
        """
        if not self.schema_builder:
            raise ValueError("Schema builder not initialized. Enable LLM and build_with_llm in config.")
        
        logger.info("Building ontology schema from domain description")
        
        # Build schema using LLM
        schema = await self.schema_builder.build_schema_from_domain(
            domain_description,
            existing_schema=self.ontology_manager.get_schema()
        )
        
        # Save to PostgreSQL if enabled
        if self.schema_store:
            schema_dict = self.schema_builder._schema_to_dict(schema)
            schema_id = self.schema_store.save_schema(
                schema_dict,
                version=schema.version,
                name="Auto-generated Schema",
                description=f"Built from domain: {domain_description[:100]}"
            )
            logger.info(f"Saved schema to PostgreSQL with ID: {schema_id}")
        
        # Update ontology manager
        self.ontology_manager.schema = schema
        
        return {
            "status": "success",
            "entities": len(schema.entities),
            "relations": len(schema.relations),
            "version": schema.version
        }
    
    async def evolve_schema(self, data_sample: Dict[str, Any], feedback: Optional[str] = None) -> Dict[str, Any]:
        """
        Evolve schema based on new data
        
        Args:
            data_sample: Sample of new data
            feedback: Optional feedback
            
        Returns:
            Evolution result
        """
        if not self.schema_builder:
            raise ValueError("Schema builder not initialized")
        
        if not self.config.ontology.evolve_automatically:
            logger.warning("Schema evolution is disabled in config")
            return {"status": "disabled"}
        
        current_schema = self.ontology_manager.get_schema()
        previous_schema_dict = self.schema_builder._schema_to_dict(current_schema)
        
        # Evolve schema
        evolved_schema = await self.schema_builder.evolve_schema(
            current_schema,
            data_sample,
            feedback
        )
        
        # Record evolution in PostgreSQL
        if self.schema_store:
            new_schema_dict = self.schema_builder._schema_to_dict(evolved_schema)
            schema_id = self.schema_store.save_schema(
                new_schema_dict,
                version=evolved_schema.version
            )
            
            self.schema_store.record_evolution(
                schema_id,
                "auto_evolution",
                feedback or "Automatic evolution based on new data",
                previous_schema_dict,
                new_schema_dict
            )
        
        # Update ontology manager
        self.ontology_manager.schema = evolved_schema
        
        return {
            "status": "evolved",
            "entities": len(evolved_schema.entities),
            "relations": len(evolved_schema.relations)
        }
    
    def _create_graph_store(self) -> GraphStore:
        """Create graph store based on configuration"""
        backend = self.config.graph.backend
        
        if backend == "neo4j":
            neo4j_config = self.config.graph.neo4j
            return Neo4jGraphStore(
                uri=neo4j_config.uri,
                user=neo4j_config.user,
                password=neo4j_config.password,
                database=neo4j_config.database
            )
        else:  # memory
            memory_config = self.config.graph.memory
            return MemoryGraphStore(
                directed=memory_config.directed,
                multigraph=memory_config.multigraph
            )
    
    async def ingest_data(self, input_path: str | Path) -> Dict[str, Any]:
        """
        Ingest data from file or directory
        
        Args:
            input_path: Path to file or directory
            
        Returns:
            Statistics about ingestion
        """
        logger.info(f"Ingesting data from: {input_path}")
        
        # Step 1: Data ingestion
        raw_data = await self.data_ingestion_agent.process(input_path)
        if not raw_data:
            logger.warning("No data was ingested")
            return {"status": "no_data", "entities": 0, "relations": 0}
        
        # Step 2: Extract entities and relations
        entities = []
        relations = []
        
        for item in raw_data:
            # Extract entities from data
            entity = self._extract_entity_from_data(item)
            if entity:
                # Validate with ontology agent
                is_valid, errors, mapped_props = await self.ontology_agent.process(
                    entity["type"], entity.get("properties", {})
                )
                if is_valid or not self.config.ontology.strict_mode:
                    entity["properties"] = mapped_props
                    entities.append(entity)
            
            # Extract relations from data
            item_relations = self._extract_relations_from_data(item)
            for rel in item_relations:
                # Validate relation
                is_valid, errors = await self.ontology_agent.validate_relation(
                    rel["type"],
                    rel.get("source_type", "Entity"),
                    rel.get("target_type", "Entity"),
                    rel.get("properties")
                )
                if is_valid or not self.config.ontology.strict_mode:
                    relations.append(rel)
        
        # Step 3: Construct graph
        stats = await self.graph_construction_agent.process(entities, relations)
        
        logger.info(f"Ingestion complete: {stats}")
        return {
            "status": "success",
            "raw_items": len(raw_data),
            **stats
        }
    
    def _extract_entity_from_data(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract entity from data item
        
        Args:
            data: Data item
            
        Returns:
            Entity dict or None
        """
        # Try to infer entity type
        entity_type = self.ontology_agent.suggest_entity_type(data) or "Entity"
        
        # Extract properties
        properties = {k: v for k, v in data.items() if k not in ["type", "id"]}
        
        # Generate ID if not present
        entity_id = data.get("id")
        if not entity_id:
            # Try to use a unique identifier
            for key in ["name", "title", "email", "url"]:
                if key in data:
                    entity_id = f"{entity_type}:{data[key]}"
                    break
        
        if not entity_id:
            return None
        
        return {
            "type": entity_type,
            "id": entity_id,
            "properties": properties
        }
    
    def _extract_relations_from_data(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract relations from data item
        
        Args:
            data: Data item
            
        Returns:
            List of relations
        """
        relations = []
        
        # Look for relation-like structures
        # This is a simple implementation - can be enhanced with NLP
        
        # Check for explicit relations
        if "relations" in data and isinstance(data["relations"], list):
            for rel in data["relations"]:
                if isinstance(rel, dict):
                    relations.append({
                        "type": rel.get("type", "RELATED_TO"),
                        "source_id": rel.get("source_id") or rel.get("source"),
                        "target_id": rel.get("target_id") or rel.get("target"),
                        "properties": {k: v for k, v in rel.items() 
                                     if k not in ["type", "source_id", "source", "target_id", "target"]}
                    })
        
        # Check for document mentions (if content exists)
        if "content" in data and isinstance(data["content"], str):
            # Simple relation: document mentions entities
            # In production, use NLP to extract entities and create relations
            doc_id = data.get("id") or data.get("source", "unknown")
            relations.append({
                "type": "MENTIONS",
                "source_id": f"Document:{doc_id}",
                "target_id": "Entity:extracted",  # Placeholder
                "properties": {"context": data["content"][:200]}
            })
        
        return relations
    
    async def query(self, query: str, query_type: str = "entity") -> List[Dict[str, Any]]:
        """
        Query the knowledge graph
        
        Args:
            query: Query string
            query_type: Type of query
            
        Returns:
            Query results
        """
        return await self.query_agent.process(query, query_type)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        graph_stats = await self.query_agent.get_graph_stats()
        
        return {
            "graph": graph_stats,
            "ontology": {
                "entities": len(self.ontology_manager.get_entity_types()),
                "relations": len(self.ontology_manager.get_relation_types())
            },
            "agents": {
                "data_ingestion": self.data_ingestion_agent.get_status(),
                "ontology": self.ontology_agent.get_status(),
                "graph_construction": self.graph_construction_agent.get_status(),
                "query": self.query_agent.get_status()
            }
        }
    
    def clear(self) -> None:
        """Clear all data from the graph"""
        self.graph_store.clear()
        logger.info("Graph cleared")
    
    def close(self) -> None:
        """Close connections and cleanup"""
        if hasattr(self.graph_store, "close"):
            self.graph_store.close()
        logger.info("SundayGraph closed")

