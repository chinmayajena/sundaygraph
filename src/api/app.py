"""FastAPI application"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from pathlib import Path
import asyncio
import os
import shutil
from loguru import logger

from ..core.sundaygraph import SundayGraph
from ..core.config import Config
from ..core.workspace_manager import WorkspaceManager
from ..tasks.factory import create_task_queue
from ..tasks.base import TaskQueue, TaskStatus
import os


# Request/Response models
class IngestRequest(BaseModel):
    input_path: str
    config_path: Optional[str] = None


class QueryRequest(BaseModel):
    query: str
    query_type: str = "entity"


class EntityRequest(BaseModel):
    entity_type: str
    properties: Dict[str, Any]


class RelationRequest(BaseModel):
    relation_type: str
    source_id: str
    target_id: str
    properties: Optional[Dict[str, Any]] = None


class Response(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None


class WorkspaceRequest(BaseModel):
    workspace_id: str
    name: str
    description: Optional[str] = None
    username: str = "admin"  # Default user


class WorkspaceFileRequest(BaseModel):
    workspace_id: str
    subdir: Optional[str] = "input"


class IngestWorkspaceFilesRequest(BaseModel):
    filenames: List[str] = []


class BuildOntologyFromFilesRequest(BaseModel):
    filenames: List[str] = []


# Global instances
_sundaygraph: Optional[SundayGraph] = None
_workspace_manager: Optional[WorkspaceManager] = None
_task_queue = None


def get_sundaygraph() -> SundayGraph:
    """Get or create SundayGraph instance"""
    global _sundaygraph
    if _sundaygraph is None:
        # Check for config path from environment or default
        config_path = os.getenv("CONFIG_PATH", "config/config.yaml")
        config_path = Path(config_path)
        if config_path.exists():
            _sundaygraph = SundayGraph(config_path=config_path)
        else:
            _sundaygraph = SundayGraph()
    return _sundaygraph


def get_task_queue() -> Optional[TaskQueue]:
    """Get or create task queue instance"""
    global _task_queue
    if _task_queue is None:
        sg = get_sundaygraph()
        _task_queue = create_task_queue(sg.config.task_queue)
    return _task_queue


def get_workspace_manager() -> WorkspaceManager:
    """Get or create WorkspaceManager instance with PostgreSQL support"""
    global _workspace_manager
    if _workspace_manager is None:
        try:
            sg = get_sundaygraph()
            # Get base data directory from config
            if hasattr(sg.config, 'data') and hasattr(sg.config.data, 'input_dir'):
                input_dir = Path(sg.config.data.input_dir)
                base_dir = input_dir.parent if input_dir else Path("./data")
            else:
                base_dir = Path("./data")
            
            # Get PostgreSQL connection string from schema_store config
            connection_string = None
            if hasattr(sg.config, 'schema_store') and getattr(sg.config.schema_store, 'enabled', False):
                host = getattr(sg.config.schema_store, 'host', 'localhost')
                port = getattr(sg.config.schema_store, 'port', 5432)
                database = getattr(sg.config.schema_store, 'database', 'sundaygraph')
                user = getattr(sg.config.schema_store, 'user', 'postgres')
                password = getattr(sg.config.schema_store, 'password', 'password')
                connection_string = f"postgresql://{user}:{password}@{host}:{port}/{database}"
            
            _workspace_manager = WorkspaceManager(
                base_data_dir=str(base_dir),
                connection_string=connection_string
            )
            logger.info(f"WorkspaceManager initialized with base_dir: {base_dir}, PostgreSQL: {connection_string is not None}")
        except Exception as e:
            logger.error(f"Failed to initialize WorkspaceManager: {e}")
            # Fallback to default
            _workspace_manager = WorkspaceManager(base_data_dir="./data")
    return _workspace_manager


def create_app(config_path: Optional[str] = None) -> FastAPI:
    """Create and configure FastAPI application"""
    app = FastAPI(
        title="SundayGraph API",
        description="Agentic AI System with Ontology-Backed Graph API",
        version="1.0.0",
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://frontend:3000",
            "http://localhost:8000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.on_event("startup")
    async def startup_event():
        """Initialize SundayGraph on startup"""
        global _sundaygraph
        if config_path:
            _sundaygraph = SundayGraph(config_path=config_path)
        else:
            config_file = os.getenv("CONFIG_PATH", "config/config.yaml")
            config_file = Path(config_file)
            if config_file.exists():
                _sundaygraph = SundayGraph(config_path=config_file)
            else:
                _sundaygraph = SundayGraph()
        logger.info("SundayGraph API started")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """Cleanup on shutdown"""
        global _sundaygraph
        if _sundaygraph:
            _sundaygraph.close()
        logger.info("SundayGraph API stopped")
    
    @app.get("/", tags=["Health"])
    async def root():
        """Root endpoint"""
        return {
            "name": "SundayGraph API",
            "version": "1.0.0",
            "status": "running"
        }
    
    @app.get("/health", tags=["Health"])
    async def health():
        """Health check endpoint"""
        try:
            sg = get_sundaygraph()
            stats = await sg.get_stats()
            return {
                "status": "healthy",
                "graph": stats.get("graph", {}),
                "ontology": stats.get("ontology", {})
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")
    
    @app.post("/api/v1/upload", tags=["Data"])
    async def upload_files(files: List[UploadFile] = File(...)):
        """
        Upload files for ingestion
        
        - **files**: List of files to upload
        """
        try:
            sg = get_sundaygraph()
            upload_dir = Path(sg.config.data.input_dir)
            upload_dir.mkdir(parents=True, exist_ok=True)
            
            uploaded_paths = []
            for file in files:
                file_path = upload_dir / file.filename
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                uploaded_paths.append(str(file_path))
                logger.info(f"Uploaded file: {file.filename}")
            
            return Response(
                success=True,
                message=f"Uploaded {len(uploaded_paths)} file(s)",
                data={"paths": uploaded_paths}
            )
        except Exception as e:
            logger.error(f"File upload failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/v1/ingest", response_model=Response, tags=["Data"])
    async def ingest_data(request: IngestRequest, background_tasks: BackgroundTasks):
        """
        Ingest data from a file or directory
        
        - **input_path**: Path to file or directory to ingest
        - **config_path**: Optional path to custom config file
        """
        try:
            sg = get_sundaygraph()
            if request.config_path:
                sg = SundayGraph(config_path=request.config_path)
            
            result = await sg.ingest_data(request.input_path)
            return Response(
                success=True,
                message="Data ingestion started",
                data=result
            )
        except Exception as e:
            logger.error(f"Ingestion failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/v1/workspaces/{workspace_id}/ingest", response_model=Response, tags=["Data"])
    async def ingest_workspace_files(
        workspace_id: str,
        request: IngestWorkspaceFilesRequest,
        username: str = "admin"
    ):
        """
        Ingest files from workspace into knowledge graph
        
        - **workspace_id**: Workspace identifier
        - **filenames**: List of filenames to ingest (empty = all files)
        - **username**: Username (default: "admin")
        """
        try:
            wm = get_workspace_manager()
            workspace = wm.get_workspace(workspace_id, username=username)
            if not workspace:
                raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found")
            
            input_dir = wm.get_workspace_path(workspace_id, "input", username=username)
            
            # Get files to ingest
            if not request.filenames:
                # Ingest all files in input directory
                files_to_ingest = [f for f in input_dir.iterdir() if f.is_file()]
            else:
                files_to_ingest = [input_dir / f for f in request.filenames if (input_dir / f).exists()]
            
            if not files_to_ingest:
                raise HTTPException(status_code=400, detail="No files found to ingest")
            
            task_queue = get_task_queue()
            sg = get_sundaygraph()
            config_path = os.getenv("CONFIG_PATH", "config/config.yaml")
            
            # Use task queue if enabled
            if task_queue:
                task_ids = []
                for file_path in files_to_ingest:
                    task_id = await task_queue.enqueue(
                        "ingest_data",
                        config_path=config_path,
                        input_path=str(file_path),
                        workspace_id=workspace_id
                    )
                    task_ids.append({"file": file_path.name, "task_id": task_id})
                
                return Response(
                    success=True,
                    message=f"Queued {len(task_ids)} ingestion task(s)",
                    data={
                        "tasks": task_ids,
                        "status_endpoint": "/api/v1/tasks/{task_id}"
                    }
                )
            
            # Synchronous processing (no task queue)
            results = []
            total_entities = 0
            total_relations = 0
            
            for file_path in files_to_ingest:
                try:
                    result = await sg.ingest_data(str(file_path), workspace_id=workspace_id)
                    results.append({
                        "file": file_path.name,
                        "status": result.get("status", "success"),
                        "entities": result.get("entities_added", 0),
                        "relations": result.get("relations_added", 0)
                    })
                    total_entities += result.get("entities_added", 0)
                    total_relations += result.get("relations_added", 0)
                except Exception as e:
                    logger.error(f"Failed to ingest {file_path.name}: {e}")
                    results.append({
                        "file": file_path.name,
                        "status": "error",
                        "error": str(e)
                    })
            
            return Response(
                success=True,
                message=f"Ingested {len(files_to_ingest)} file(s): {total_entities} entities, {total_relations} relations",
                data={
                    "files_processed": len(files_to_ingest),
                    "total_entities": total_entities,
                    "total_relations": total_relations,
                    "results": results
                }
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Workspace ingestion failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/v1/workspaces/{workspace_id}/build-ontology", response_model=Response, tags=["Ontology"])
    async def build_ontology_from_files(
        workspace_id: str,
        request: BuildOntologyFromFilesRequest,
        username: str = "admin"
    ):
        """
        Build ontology schema from files in workspace
        
        - **workspace_id**: Workspace identifier
        - **filenames**: List of filenames to use (empty = all files)
        - **username**: Username (default: "admin")
        """
        try:
            wm = get_workspace_manager()
            workspace = wm.get_workspace(workspace_id, username=username)
            if not workspace:
                raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found")
            
            input_dir = wm.get_workspace_path(workspace_id, "input", username=username)
            
            # Get files to use for ontology building
            if not request.filenames:
                # Use all files in input directory
                files_to_use = [f for f in input_dir.iterdir() if f.is_file()]
            else:
                files_to_use = [input_dir / f for f in request.filenames if (input_dir / f).exists()]
            
            if not files_to_use:
                raise HTTPException(status_code=400, detail="No files found to build ontology from")
            
            sg = get_sundaygraph()
            
            # Read file contents and combine for domain description
            file_contents = []
            for file_path in files_to_use:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        # Limit content size for LLM prompt
                        file_contents.append(f"File: {file_path.name}\n{content[:2000]}")
                except Exception as e:
                    logger.warning(f"Could not read {file_path.name}: {e}")
            
            if not file_contents:
                raise HTTPException(status_code=400, detail="Could not read any file contents")
            
            # Create domain description from file contents
            domain_description = f"Build an ontology schema based on the following data files:\n\n" + "\n\n---\n\n".join(file_contents)
            
            # Build schema using LLM
            schema_result = await sg.build_schema_from_domain(domain_description)
            
            return Response(
                success=True,
                message=f"Ontology built from {len(files_to_use)} file(s)",
                data={
                    "entities": schema_result.get("entities", 0),  # Already a count, not a list
                    "relations": schema_result.get("relations", 0),  # Already a count, not a list
                    "version": schema_result.get("version", 1),
                    "status": schema_result.get("status", "success")
                }
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Ontology building from files failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/v1/ingest/text", response_model=Response, tags=["Data"])
    async def ingest_text(request: Dict[str, Any]):
        """
        Ingest text data directly
        
        - **text**: Text content to ingest
        - **filename**: Optional filename for the text
        """
        try:
            sg = get_sundaygraph()
            text = request.get("text", "")
            filename = request.get("filename", "text_input.txt")
            
            if not text:
                raise HTTPException(status_code=400, detail="Text content is required")
            
            # Save text to temporary file
            input_dir = Path(sg.config.data.input_dir)
            input_dir.mkdir(parents=True, exist_ok=True)
            temp_file = input_dir / filename
            
            with open(temp_file, "w", encoding="utf-8") as f:
                f.write(text)
            
            result = await sg.ingest_data(str(temp_file))
            
            # Optionally clean up temp file
            # temp_file.unlink()
            
            return Response(
                success=True,
                message="Text data ingested",
                data=result
            )
        except Exception as e:
            logger.error(f"Text ingestion failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/v1/query", response_model=Response, tags=["Query"])
    async def query(request: QueryRequest):
        """
        Query the knowledge graph
        
        - **query**: Query string
        - **query_type**: Type of query (entity, relation, neighbor, path)
        """
        try:
            sg = get_sundaygraph()
            results = await sg.query(request.query, query_type=request.query_type)
            return Response(
                success=True,
                message=f"Found {len(results)} results",
                data=results
            )
        except Exception as e:
            logger.error(f"Query failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/v1/ontology/evaluate", response_model=Response, tags=["Ontology"])
    async def evaluate_ontology(domain_description: Optional[str] = None):
        """
        Evaluate ontology schema quality
        
        - **domain_description**: Optional domain description for context
        """
        try:
            sg = get_sundaygraph()
            schema = sg.ontology_manager.get_schema()
            
            from ..ontology.evaluation_metrics import OntologyEvaluator
            evaluator = OntologyEvaluator()
            evaluation = evaluator.evaluate_schema(schema, domain_description)
            
            return Response(
                success=True,
                message="Ontology evaluation completed",
                data=evaluation
            )
        except Exception as e:
            logger.error(f"Ontology evaluation failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/v1/llm/cost-stats", response_model=Response, tags=["LLM"])
    async def get_llm_cost_stats():
        """Get LLM cost and usage statistics"""
        try:
            sg = get_sundaygraph()
            if not sg.llm_service or not sg.llm_service.cost_optimizer:
                return Response(
                    success=False,
                    message="LLM cost tracking not available",
                    data=None
                )
            
            stats = sg.llm_service.cost_optimizer.get_stats()
            return Response(
                success=True,
                message="LLM cost statistics",
                data=stats
            )
        except Exception as e:
            logger.error(f"Failed to get LLM cost stats: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/v1/llm/reset-stats", response_model=Response, tags=["LLM"])
    async def reset_llm_stats():
        """Reset LLM cost statistics"""
        try:
            sg = get_sundaygraph()
            if sg.llm_service and sg.llm_service.cost_optimizer:
                sg.llm_service.cost_optimizer.reset_stats()
                return Response(
                    success=True,
                    message="LLM cost statistics reset"
                )
            else:
                return Response(
                    success=False,
                    message="LLM cost tracking not available"
                )
        except Exception as e:
            logger.error(f"Failed to reset LLM stats: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/v1/stats", response_model=Response, tags=["Stats"])
    async def get_stats(workspace_id: Optional[str] = None):
        """Get system statistics"""
        try:
            sg = get_sundaygraph()
            stats = await sg.get_stats(workspace_id=workspace_id)
            return Response(
                success=True,
                message="Statistics retrieved",
                data=stats
            )
        except Exception as e:
            logger.error(f"Stats retrieval failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/v1/entities", response_model=Response, tags=["Entities"])
    async def add_entity(request: EntityRequest):
        """
        Add an entity to the graph
        
        - **entity_type**: Type of entity
        - **properties**: Entity properties
        """
        try:
            sg = get_sundaygraph()
            # Validate with ontology agent
            is_valid, errors, mapped_props = await sg.ontology_agent.process(
                request.entity_type, request.properties
            )
            if not is_valid and sg.config.ontology.strict_mode:
                raise HTTPException(
                    status_code=400,
                    detail=f"Entity validation failed: {errors}"
                )
            
            # Add to graph
            entity = {
                "type": request.entity_type,
                "properties": mapped_props
            }
            stats = await sg.graph_construction_agent.process([entity], [])
            
            return Response(
                success=True,
                message="Entity added",
                data={"entity": entity, "stats": stats}
            )
        except Exception as e:
            logger.error(f"Entity addition failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/v1/relations", response_model=Response, tags=["Relations"])
    async def add_relation(request: RelationRequest):
        """
        Add a relation to the graph
        
        - **relation_type**: Type of relation
        - **source_id**: Source entity ID
        - **target_id**: Target entity ID
        - **properties**: Optional relation properties
        """
        try:
            sg = get_sundaygraph()
            # Get entity types for validation
            source_entity = sg.graph_store.get_entity(request.source_id)
            target_entity = sg.graph_store.get_entity(request.target_id)
            
            if not source_entity or not target_entity:
                raise HTTPException(
                    status_code=404,
                    detail="Source or target entity not found"
                )
            
            source_type = source_entity.get("type", "Entity")
            target_type = target_entity.get("type", "Entity")
            
            # Validate relation
            is_valid, errors = await sg.ontology_agent.validate_relation(
                request.relation_type, source_type, target_type, request.properties
            )
            if not is_valid and sg.config.ontology.strict_mode:
                raise HTTPException(
                    status_code=400,
                    detail=f"Relation validation failed: {errors}"
                )
            
            # Add relation
            relation = {
                "type": request.relation_type,
                "source_id": request.source_id,
                "target_id": request.target_id,
                "properties": request.properties or {}
            }
            stats = await sg.graph_construction_agent.process([], [relation])
            
            return Response(
                success=True,
                message="Relation added",
                data={"relation": relation, "stats": stats}
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Relation addition failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.delete("/api/v1/clear", response_model=Response, tags=["Data"])
    async def clear_graph():
        """Clear all data from the graph"""
        try:
            sg = get_sundaygraph()
            sg.clear()
            return Response(
                success=True,
                message="Graph cleared"
            )
        except Exception as e:
            logger.error(f"Clear failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/v1/graph/nodes", response_model=Response, tags=["Graph"])
    async def get_graph_nodes(
        workspace_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        limit: int = 100
    ):
        """Get graph nodes (entities) for a workspace"""
        try:
            sg = get_sundaygraph()
            entities = sg.graph_store.query_entities(
                entity_type=entity_type,
                limit=limit,
                workspace_id=workspace_id
            )
            return Response(
                success=True,
                message=f"Retrieved {len(entities)} entities",
                data=entities
            )
        except Exception as e:
            logger.error(f"Failed to get graph nodes: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/v1/graph/edges", response_model=Response, tags=["Graph"])
    async def get_graph_edges(
        workspace_id: Optional[str] = None,
        relation_type: Optional[str] = None,
        limit: int = 100
    ):
        """Get graph edges (relations) for a workspace"""
        try:
            sg = get_sundaygraph()
            relations = sg.graph_store.query_relations(
                relation_type=relation_type,
                limit=limit,
                workspace_id=workspace_id
            )
            return Response(
                success=True,
                message=f"Retrieved {len(relations)} relations",
                data=relations
            )
        except Exception as e:
            logger.error(f"Failed to get graph edges: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/v1/ontology/entities", tags=["Ontology"])
    async def get_entity_types():
        """Get all entity types from ontology"""
        try:
            sg = get_sundaygraph()
            entity_types = sg.ontology_manager.get_entity_types()
            return Response(
                success=True,
                message=f"Found {len(entity_types)} entity types",
                data=entity_types
            )
        except Exception as e:
            logger.error(f"Failed to get entity types: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/v1/ontology/relations", tags=["Ontology"])
    async def get_relation_types():
        """Get all relation types from ontology"""
        try:
            sg = get_sundaygraph()
            relation_types = sg.ontology_manager.get_relation_types()
            return Response(
                success=True,
                message=f"Found {len(relation_types)} relation types",
                data=relation_types
            )
        except Exception as e:
            logger.error(f"Failed to get relation types: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/v1/ontology/build", response_model=Response, tags=["Ontology"])
    async def build_schema(request: Dict[str, Any]):
        """
        Build ontology schema from domain description using LLM reasoning
        
        - **domain_description**: Description of the domain
        """
        try:
            sg = get_sundaygraph()
            domain_description = request.get("domain_description", "")
            if not domain_description:
                raise HTTPException(status_code=400, detail="domain_description is required")
            
            result = await sg.build_schema_from_domain(domain_description)
            return Response(
                success=True,
                message="Schema built successfully",
                data=result
            )
        except Exception as e:
            logger.error(f"Schema building failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/v1/ontology/evolve", response_model=Response, tags=["Ontology"])
    async def evolve_schema(request: Dict[str, Any]):
        """
        Evolve schema based on new data
        
        - **data_sample**: Sample of new data
        - **feedback**: Optional feedback
        """
        try:
            sg = get_sundaygraph()
            data_sample = request.get("data_sample", {})
            feedback = request.get("feedback")
            
            result = await sg.evolve_schema(data_sample, feedback)
            return Response(
                success=True,
                message="Schema evolved successfully",
                data=result
            )
        except Exception as e:
            logger.error(f"Schema evolution failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # Workspace endpoints
    @app.post("/api/v1/workspaces", response_model=Response, tags=["Workspaces"])
    async def create_workspace(request: WorkspaceRequest):
        """
        Create a new workspace
        
        - **workspace_id**: Unique workspace identifier
        - **name**: Workspace name
        - **description**: Optional description
        - **username**: Username (default: "admin")
        """
        try:
            wm = get_workspace_manager()
            workspace = wm.create_workspace(
                workspace_id=request.workspace_id,
                name=request.name,
                description=request.description,
                username=request.username
            )
            return Response(
                success=True,
                message="Workspace created successfully",
                data=workspace
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Workspace creation failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/v1/workspaces", response_model=Response, tags=["Workspaces"])
    async def list_workspaces(username: str = "admin"):
        """
        List all workspaces for a user
        
        - **username**: Username (default: "admin")
        """
        try:
            wm = get_workspace_manager()
            workspaces = wm.list_workspaces(username=username)
            return Response(
                success=True,
                message=f"Found {len(workspaces)} workspace(s) for user {username}",
                data=workspaces
            )
        except Exception as e:
            logger.error(f"Failed to list workspaces: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/v1/workspaces/{workspace_id}", response_model=Response, tags=["Workspaces"])
    async def get_workspace(workspace_id: str, username: str = "admin"):
        """
        Get workspace information
        
        - **workspace_id**: Workspace identifier
        - **username**: Username (default: "admin")
        """
        try:
            wm = get_workspace_manager()
            workspace = wm.get_workspace(workspace_id, username=username)
            if not workspace:
                raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found for user {username}")
            return Response(
                success=True,
                message="Workspace retrieved",
                data=workspace
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get workspace: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.delete("/api/v1/workspaces/{workspace_id}", response_model=Response, tags=["Workspaces"])
    async def delete_workspace(workspace_id: str, username: str = "admin"):
        """
        Delete a workspace
        
        - **workspace_id**: Workspace identifier
        - **username**: Username (default: "admin")
        """
        try:
            wm = get_workspace_manager()
            success = wm.delete_workspace(workspace_id, username=username)
            if not success:
                raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found")
            return Response(
                success=True,
                message="Workspace deleted successfully"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to delete workspace: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # File management endpoints
    @app.get("/api/v1/workspaces/{workspace_id}/files", response_model=Response, tags=["Files"])
    async def list_workspace_files(workspace_id: str, subdir: str = "input", username: str = "admin"):
        """
        List files in workspace directory
        
        - **workspace_id**: Workspace identifier
        - **subdir**: Subdirectory (input, output, cache, graphs)
        - **username**: Username (default: "admin")
        """
        try:
            wm = get_workspace_manager()
            files = wm.list_files(workspace_id, subdir, username=username)
            return Response(
                success=True,
                message=f"Found {len(files)} file(s)",
                data=files
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Failed to list files: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/v1/workspaces/{workspace_id}/files/{filename}/preview", response_model=Response, tags=["Files"])
    async def get_file_preview(
        workspace_id: str,
        filename: str,
        subdir: str = "input",
        max_lines: int = 1000,  # Increased for better preview
        username: str = "admin"
    ):
        """
        Get file preview
        
        - **workspace_id**: Workspace identifier
        - **filename**: File name
        - **subdir**: Subdirectory (input, output, cache, graphs)
        - **max_lines**: Maximum lines to preview (default: 1000)
        - **username**: Username (default: "admin")
        """
        try:
            wm = get_workspace_manager()
            preview = wm.get_file_preview(workspace_id, filename, subdir, max_lines, username=username)
            return Response(
                success=True,
                message="File preview retrieved",
                data=preview
            )
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Failed to get file preview: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/v1/workspaces/{workspace_id}/files/{filename}/download", tags=["Files"])
    async def download_file(
        workspace_id: str,
        filename: str,
        subdir: str = "input",
        username: str = "admin"
    ):
        """
        Download/serve file for preview (PDF, images, etc.)
        
        - **workspace_id**: Workspace identifier
        - **filename**: File name
        - **subdir**: Subdirectory (input, output, cache, graphs)
        - **username**: Username (default: "admin")
        """
        try:
            from fastapi.responses import FileResponse
            wm = get_workspace_manager()
            workspace_path = wm.get_workspace_path(workspace_id, subdir, username=username)
            file_path = workspace_path / filename
            
            if not file_path.exists():
                raise HTTPException(status_code=404, detail="File not found")
            
            # Determine media type
            media_type = None
            if filename.lower().endswith('.pdf'):
                media_type = "application/pdf"
            elif filename.lower().endswith('.json'):
                media_type = "application/json"
            elif filename.lower().endswith('.csv'):
                media_type = "text/csv"
            elif filename.lower().endswith('.txt'):
                media_type = "text/plain"
            
            return FileResponse(
                str(file_path),
                media_type=media_type,
                filename=filename
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to serve file: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/v1/workspaces/{workspace_id}/upload", tags=["Files"])
    async def upload_workspace_files(
        workspace_id: str,
        files: List[UploadFile] = File(...),
        username: str = "admin"
    ):
        """
        Upload files to workspace (database-backed)
        
        - **workspace_id**: Workspace identifier
        - **files**: List of files to upload
        - **username**: Username (default: "admin")
        """
        try:
            wm = get_workspace_manager()
            workspace = wm.get_workspace(workspace_id, username=username)
            if not workspace:
                raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found for user {username}")
            
            upload_dir = wm.get_workspace_path(workspace_id, "input", username=username)
            upload_dir.mkdir(parents=True, exist_ok=True)
            
            uploaded_files = []
            for file in files:
                file_path = upload_dir / file.filename
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                
                file_size = file_path.stat().st_size
                file_type = file_path.suffix.lower()
                mime_type = file.content_type if hasattr(file, 'content_type') else None
                
                uploaded_files.append({
                    "name": file.filename,
                    "path": str(file_path),
                    "size": file_size
                })
                
                # Save file metadata to PostgreSQL if database storage is available
                if wm.db_store and wm.db_store._connection:
                    user_id = wm._get_user_id(username)
                    if user_id:
                        workspace_db = wm.db_store.get_workspace(user_id, workspace_id)
                        if workspace_db:
                            workspace_db_id = workspace_db.get("id")
                            if workspace_db_id:
                                file_id = wm.db_store.record_file(
                                    workspace_db_id=workspace_db_id,
                                    filename=file.filename,
                                    file_path=str(file_path),
                                    subdir="input",
                                    file_size=file_size,
                                    file_type=file_type,
                                    mime_type=mime_type
                                )
                                if file_id:
                                    logger.info(f"Recorded file {file.filename} in database (ID: {file_id})")
                
                logger.info(f"Uploaded file to workspace {workspace_id}: {file.filename}")
            
            return Response(
                success=True,
                message=f"Uploaded {len(uploaded_files)} file(s)",
                data={"files": uploaded_files}
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"File upload failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # Task queue endpoints
    @app.get("/api/v1/tasks/{task_id}", tags=["Tasks"])
    async def get_task_status(task_id: str):
        """Get task status"""
        task_queue = get_task_queue()
        if not task_queue:
            raise HTTPException(status_code=400, detail="Task queue is not enabled")
        
        result = await task_queue.get_status(task_id)
        return {
            "task_id": result.task_id,
            "status": result.status.value,
            "result": result.result,
            "error": result.error,
            "progress": result.progress,
            "created_at": result.created_at.isoformat() if result.created_at else None,
            "started_at": result.started_at.isoformat() if result.started_at else None,
            "completed_at": result.completed_at.isoformat() if result.completed_at else None
        }
    
    @app.get("/api/v1/tasks/{task_id}/result", tags=["Tasks"])
    async def get_task_result(task_id: str, timeout: Optional[float] = None):
        """Get task result (wait for completion)"""
        task_queue = get_task_queue()
        if not task_queue:
            raise HTTPException(status_code=400, detail="Task queue is not enabled")
        
        result = await task_queue.get_result(task_id, timeout=timeout)
        return {
            "task_id": result.task_id,
            "status": result.status.value,
            "result": result.result,
            "error": result.error,
            "progress": result.progress,
            "completed_at": result.completed_at.isoformat() if result.completed_at else None
        }
    
    @app.post("/api/v1/tasks/{task_id}/cancel", tags=["Tasks"])
    async def cancel_task(task_id: str):
        """Cancel a running task"""
        task_queue = get_task_queue()
        if not task_queue:
            raise HTTPException(status_code=400, detail="Task queue is not enabled")
        
        success = await task_queue.cancel(task_id)
        return {"success": success, "task_id": task_id}
    
    @app.get("/api/v1/tasks", tags=["Tasks"])
    async def list_tasks(status: Optional[str] = None, limit: int = 100):
        """List tasks"""
        task_queue = get_task_queue()
        if not task_queue:
            raise HTTPException(status_code=400, detail="Task queue is not enabled")
        
        task_status = TaskStatus(status) if status else None
        tasks = await task_queue.list_tasks(status=task_status, limit=limit)
        
        return {
            "tasks": [
                {
                    "task_id": t.task_id,
                    "status": t.status.value,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                    "completed_at": t.completed_at.isoformat() if t.completed_at else None
                }
                for t in tasks
            ],
            "count": len(tasks)
        }
    
    return app


# Create default app instance
app = create_app()

