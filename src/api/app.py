"""FastAPI application"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from pathlib import Path
import asyncio
from loguru import logger

from ..core.sundaygraph import SundayGraph
from ..core.config import Config
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


# Global SundayGraph instance
_sundaygraph: Optional[SundayGraph] = None


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
        allow_origins=["*"],  # Configure appropriately for production
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
    
    return app


# Create default app instance
app = create_app()

