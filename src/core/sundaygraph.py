"""Main SundayGraph orchestration class"""

from pathlib import Path
from typing import Dict, Any, List, Optional
from loguru import logger
import sys

from .config import Config
from ..ontology.ontology_manager import OntologyManager
from ..ontology.schema_builder import OntologySchemaBuilder
from ..graph.graph_store import GraphStore, MemoryGraphStore
from ..storage.schema_store import SchemaStore
from ..agents.data_ingestion_agent import DataIngestionAgent
from ..agents.ontology_agent import OntologyAgent
from ..agents.graph_construction_agent import GraphConstructionAgent
from ..agents.query_agent import QueryAgent
from ..agents.schema_inference_agent import SchemaInferenceAgent
from ..data.extraction_executor import ExtractionExecutor
from ..utils.code_executor import CodeExecutor


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
        try:
            self.graph_store = self._create_graph_store()
        except Exception as e:
            logger.warning(f"Failed to initialize graph store: {e}. Falling back to memory store.")
            from ..graph.graph_store import MemoryGraphStore
            memory_config = self.config.graph.memory
            self.graph_store = MemoryGraphStore(
                directed=memory_config.directed,
                multigraph=memory_config.multigraph
            )
        
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
        
        # Initialize schema inference agent (for efficient extraction)
        self.schema_inference_agent = None
        if self.llm_service:
            self.schema_inference_agent = SchemaInferenceAgent(
                llm_service=self.llm_service,
                config={"sample_size": 20, "max_sample_chars": 10000}
            )
            logger.info("Schema inference agent initialized (will use LLM once per file type)")
        
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
        
        if backend == "oxigraph":
            from ..graph.oxigraph_store import OxigraphGraphStore
            oxigraph_config = self.config.graph.oxigraph
            try:
                return OxigraphGraphStore(
                    sparql_endpoint=oxigraph_config.sparql_endpoint,
                    update_endpoint=oxigraph_config.update_endpoint,
                    default_graph_uri=oxigraph_config.default_graph_uri,
                    timeout=oxigraph_config.timeout
                )
            except Exception as e:
                logger.warning(f"Failed to connect to Oxigraph: {e}. Falling back to memory store.")
                # Fallback to memory store if Oxigraph is not available
                memory_config = self.config.graph.memory
                return MemoryGraphStore(
                    directed=memory_config.directed,
                    multigraph=memory_config.multigraph
                )
        else:  # memory
            memory_config = self.config.graph.memory
            return MemoryGraphStore(
                directed=memory_config.directed,
                multigraph=memory_config.multigraph
            )
    
    async def ingest_data(self, input_path: str | Path, workspace_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Ingest data from file or directory using intelligent schema inference.
        Uses LLM once to analyze data structure, then executes extraction rules on all rows.
        
        Args:
            input_path: Path to file or directory
            workspace_id: Optional workspace ID for namespace isolation
            
        Returns:
            Statistics about ingestion
        """
        logger.info(f"Ingesting data from: {input_path} to workspace: {workspace_id}")
        
        # Step 1: Data ingestion
        raw_data = await self.data_ingestion_agent.process(input_path)
        if not raw_data:
            logger.warning(f"No data was ingested from {input_path}")
            return {"status": "no_data", "entities_added": 0, "relations_added": 0}
        
        logger.info(f"Loaded {len(raw_data)} raw data items from {input_path}")
        
        # Step 2: Intelligent extraction using schema inference
        # Use LLM once to generate extraction rules, then execute on all rows
        entities = []
        relations = []
        
        # Determine file type
        file_path = Path(input_path)
        file_type = file_path.suffix.lower().lstrip('.') if file_path.suffix else "unknown"
        if not file_type or file_type == "unknown":
            # Try to infer from data structure
            if raw_data and isinstance(raw_data[0], dict):
                if "content" in raw_data[0]:
                    file_type = "text"
                else:
                    file_type = "structured"
        
        # Use schema inference if LLM is available
        if self.schema_inference_agent and len(raw_data) > 0:
            try:
                # Get ontology schema for mapping
                ontology_schema = None
                if self.ontology_manager:
                    ontology_schema = self.ontology_agent._get_ontology_schema_dict()
                
                # Take sample for analysis (first N rows)
                sample_size = min(20, len(raw_data))
                data_sample = raw_data[:sample_size]
                
                logger.info(f"Analyzing {sample_size} sample rows with LLM to generate extraction code (CodeAct)...")
                
                # Generate extraction code using LLM (CodeAct approach - ONE CALL)
                extraction_code = await self.schema_inference_agent.generate_extraction_code(
                    data_sample=data_sample,
                    file_type=file_type,
                    ontology_schema=ontology_schema
                )
                
                # Also generate rules for fallback/configuration
                extraction_rules = await self.schema_inference_agent.infer_extraction_rules(
                    data_sample=data_sample,
                    file_type=file_type,
                    ontology_schema=ontology_schema
                )
                
                logger.info(f"Generated extraction code ({len(extraction_code)} chars), processing all {len(raw_data)} rows without LLM calls...")
                
                # Execute generated code on all rows (NO LLM CALLS)
                executor = ExtractionExecutor(rules=extraction_rules, code=extraction_code)
                entities, relations = executor.extract_from_batch(raw_data)
                
                logger.info(f"Extracted {len(entities)} entities and {len(relations)} relations using generated rules")
                
            except Exception as e:
                logger.warning(f"Schema inference failed: {e}. Falling back to rule-based extraction.")
                # Fallback to original method
                entities, relations = await self._extract_entities_relations_fallback(raw_data)
        else:
            # Fallback: use rule-based extraction without LLM
            logger.info("Using rule-based extraction (no LLM available or schema inference disabled)")
            entities, relations = await self._extract_entities_relations_fallback(raw_data)
        
        # Step 3: Optional validation (without LLM calls if strict_mode is off)
        # Only validate if strict_mode is enabled
        if self.config.ontology.strict_mode:
            validated_entities = []
            validated_relations = []
            
            for entity in entities:
                is_valid, errors, mapped_props = await self.ontology_agent.process(
                    entity["type"], entity.get("properties", {}), use_llm=False
                )
                if is_valid:
                    entity["properties"] = mapped_props
                    validated_entities.append(entity)
            
            for rel in relations:
                is_valid, errors = await self.ontology_agent.validate_relation(
                    rel["type"],
                    rel.get("source_type", "Entity"),
                    rel.get("target_type", "Entity"),
                    rel.get("properties"),
                    use_llm=False
                )
                if is_valid:
                    validated_relations.append(rel)
            
            entities = validated_entities
            relations = validated_relations
        
        logger.info(f"Final: {len(entities)} entities and {len(relations)} relations ready for graph construction")
        
        # Step 4: Construct graph with workspace namespace
        stats = await self.graph_construction_agent.process(entities, relations, workspace_id)
        
        logger.info(f"Ingestion complete for workspace {workspace_id}: {stats['entities_added']} entities, {stats['relations_added']} relations added")
        return {
            "status": "success",
            "raw_items": len(raw_data),
            "entities_added": stats.get("entities_added", 0),
            "relations_added": stats.get("relations_added", 0),
            "entities_skipped": stats.get("entities_skipped", 0),
            "relations_skipped": stats.get("relations_skipped", 0)
        }
    
    async def _extract_entities_relations_fallback(self, raw_data: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Fallback extraction method (original per-row approach, but without LLM calls)
        
        Args:
            raw_data: List of raw data items
            
        Returns:
            Tuple of (entities, relations) lists
        """
        entities = []
        relations = []
        
        for item in raw_data:
            # Extract entities from data (rule-based, no LLM)
            entity = self._extract_entity_from_data(item)
            if entity:
                # Only validate against schema (no LLM)
                is_valid, errors, mapped_props = await self.ontology_agent.process(
                    entity["type"], entity.get("properties", {}), use_llm=False
                )
                if is_valid or not self.config.ontology.strict_mode:
                    entity["properties"] = mapped_props
                    entities.append(entity)
            
            # Extract relations from data (rule-based, no LLM)
            item_relations = self._extract_relations_from_data(item)
            for rel in item_relations:
                # Only validate against schema (no LLM)
                is_valid, errors = await self.ontology_agent.validate_relation(
                    rel["type"],
                    rel.get("source_type", "Entity"),
                    rel.get("target_type", "Entity"),
                    rel.get("properties"),
                    use_llm=False
                )
                if is_valid or not self.config.ontology.strict_mode:
                    relations.append(rel)
        
        return entities, relations
    
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
        
        # Extract properties (exclude metadata fields)
        properties = {k: v for k, v in data.items() if k not in ["type", "id", "source", "chunk_index", "total_chunks", "metadata"]}
        
        # Generate ID if not present
        entity_id = data.get("id")
        if not entity_id:
            # Try to use a unique identifier from common fields
            for key in ["name", "title", "email", "url", "id", "customer_id", "product_id", "employee_id", "project_id"]:
                if key in data and data[key]:
                    entity_id = f"{entity_type}:{data[key]}"
                    break
        
        # If still no ID, generate one from properties or use row index
        if not entity_id:
            # For CSV/structured data, create ID from first property value
            if properties:
                first_key = list(properties.keys())[0]
                first_value = str(properties[first_key])[:50]  # Limit length
                entity_id = f"{entity_type}:{first_key}_{first_value}"
            else:
                # Last resort: use hash of all properties
                import hashlib
                prop_str = str(sorted(data.items()))
                prop_hash = hashlib.md5(prop_str.encode()).hexdigest()[:8]
                entity_id = f"{entity_type}:{prop_hash}"
        
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
        
        # For CSV/structured data, look for foreign key-like relationships
        # Check for columns that might indicate relationships (e.g., "project_id", "manager_id", etc.)
        entity_id = data.get("id")
        if not entity_id:
            # Try to generate entity ID same way as in _extract_entity_from_data
            entity_type = self.ontology_agent.suggest_entity_type(data) or "Entity"
            for key in ["name", "title", "email", "url", "id", "customer_id", "product_id", "employee_id", "project_id"]:
                if key in data and data[key]:
                    entity_id = f"{entity_type}:{data[key]}"
                    break
            # If still no ID, use first property
            if not entity_id and data:
                first_key = list(data.keys())[0]
                if first_key not in ["type", "id", "source", "chunk_index", "total_chunks", "metadata"]:
                    first_value = str(data[first_key])[:50]
                    entity_id = f"{entity_type}:{first_key}_{first_value}"
        
        if entity_id:
            # Look for foreign key columns (ending in _id or containing "id")
            for key, value in data.items():
                if key.endswith("_id") or (key != "id" and "id" in key.lower() and value and key not in ["chunk_index", "total_chunks"]):
                    # Create a relation to the referenced entity
                    target_type = key.replace("_id", "").replace("Id", "").title()
                    if not target_type:
                        target_type = "Entity"
                    relations.append({
                        "type": "HAS_" + key.upper().replace("_", ""),
                        "source_id": entity_id,
                        "target_id": f"{target_type}:{value}",
                        "properties": {}
                    })
        
        # Check for document mentions (if content exists)
        if "content" in data and isinstance(data["content"], str):
            # Simple relation: document mentions entities
            # In production, use NLP to extract entities and create relations
            doc_id = data.get("id") or data.get("source", "unknown")
            if not doc_id.startswith("Document:"):
                doc_id = f"Document:{doc_id}"
            relations.append({
                "type": "MENTIONS",
                "source_id": doc_id,
                "target_id": "Entity:extracted",  # Placeholder - could be enhanced with NLP
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
    
    async def get_stats(self, workspace_id: Optional[str] = None) -> Dict[str, Any]:
        """Get system statistics"""
        graph_stats = self.graph_store.get_stats(workspace_id=workspace_id)
        
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

