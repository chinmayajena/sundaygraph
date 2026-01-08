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


# Global instances
_sundaygraph: Optional[SundayGraph] = None
_workspace_manager: Optional[WorkspaceManager] = None


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
    
    @app.get("/api/v1/stats", response_model=Response, tags=["Stats"])
    async def get_stats():
        """Get system statistics"""
        try:
            sg = get_sundaygraph()
            stats = await sg.get_stats()
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
    async def get_file_preview(workspace_id: str, filename: str, subdir: str = "input", max_lines: int = 50):
        """
        Get file preview
        
        - **workspace_id**: Workspace identifier
        - **filename**: File name
        - **subdir**: Subdirectory (input, output, cache, graphs)
        - **max_lines**: Maximum lines to preview
        """
        try:
            wm = get_workspace_manager()
            preview = wm.get_file_preview(workspace_id, filename, subdir, max_lines)
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
    
    @app.post("/api/v1/workspaces/{workspace_id}/upload", tags=["Files"])
    async def upload_workspace_files(workspace_id: str, files: List[UploadFile] = File(...)):
        """
        Upload files to workspace
        
        - **workspace_id**: Workspace identifier
        - **files**: List of files to upload
        """
        try:
            wm = get_workspace_manager()
            workspace = wm.get_workspace(workspace_id)
            if not workspace:
                raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found")
            
            upload_dir = wm.get_workspace_path(workspace_id, "input")
            upload_dir.mkdir(parents=True, exist_ok=True)
            
            uploaded_files = []
            for file in files:
                file_path = upload_dir / file.filename
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                uploaded_files.append({
                    "name": file.filename,
                    "path": str(file_path),
                    "size": file_path.stat().st_size
                })
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
    
    return app


# Create default app instance
app = create_app()

