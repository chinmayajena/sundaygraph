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

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from ..core.sundaygraph import SundayGraph
from ..core.config import Config
from ..core.workspace_manager import WorkspaceManager
from ..tasks.factory import create_task_queue
from ..tasks.base import TaskQueue, TaskStatus
from ..storage.odl_store import ODLStore
from ..odl.core import ODLProcessor
from ..odl.diff import ODLDiffEngine
from ..odl.evaluation import ODLEvaluator, EvaluationResult
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


class EvaluateVersionRequest(BaseModel):
    """Request model for version evaluation."""
    threshold_profile: str = "strict"  # strict or relaxed
    notes: Optional[str] = None


class CreateOntologyRequest(BaseModel):
    name: str
    description: Optional[str] = None


class CreateOntologyVersionRequest(BaseModel):
    version_number: str
    odl_json: Dict[str, Any]
    notes: Optional[str] = None


# Global instances
_sundaygraph: Optional[SundayGraph] = None
_workspace_manager: Optional[WorkspaceManager] = None
_task_queue = None
_odl_store: Optional[ODLStore] = None


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
    """Get or create WorkspaceManager instance"""
    global _workspace_manager
    if _workspace_manager is None:
        sg = get_sundaygraph()
        # Get PostgreSQL connection string from schema_store config
        connection_string = None
        if hasattr(sg.config, 'schema_store') and getattr(sg.config.schema_store, 'enabled', False):
            host = getattr(sg.config.schema_store, 'host', 'localhost')
            port = getattr(sg.config.schema_store, 'port', 5432)
            database = getattr(sg.config.schema_store, 'database', 'sundaygraph')
            user = getattr(sg.config.schema_store, 'user', 'postgres')
            password = getattr(sg.config.schema_store, 'password', 'password')
            connection_string = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        
        _workspace_manager = WorkspaceManager(connection_string=connection_string)
    return _workspace_manager


def get_odl_store() -> Optional[ODLStore]:
    """Get or create ODLStore instance"""
    global _odl_store
    if _odl_store is None:
        sg = get_sundaygraph()
        # Get PostgreSQL connection string from schema_store config
        connection_string = None
        if hasattr(sg.config, 'schema_store') and getattr(sg.config.schema_store, 'enabled', False):
            host = getattr(sg.config.schema_store, 'host', 'localhost')
            port = getattr(sg.config.schema_store, 'port', 5432)
            database = getattr(sg.config.schema_store, 'database', 'sundaygraph')
            user = getattr(sg.config.schema_store, 'user', 'postgres')
            password = getattr(sg.config.schema_store, 'password', 'password')
            connection_string = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        
        if connection_string:
            try:
                _odl_store = ODLStore(connection_string)
                if not _odl_store._connection:
                    logger.warning("ODL store connection failed, API endpoints will be limited")
                    _odl_store = None
            except Exception as e:
                logger.warning(f"Failed to initialize ODL store: {e}")
                _odl_store = None
    return _odl_store


# Create FastAPI app
app = FastAPI(
    title="SundayGraph API",
    version="1.0.0",
    description="Agentic AI System with Ontology-Backed Graph API",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check
@app.get("/health", tags=["Health"])
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


# ... existing endpoints ...

# ODL Ontology Management Endpoints

@app.post("/api/v1/workspaces/{workspace_id}/ontology", tags=["ODL"])
async def create_ontology(
    workspace_id: str,
    request: CreateOntologyRequest,
    username: str = "admin"
):
    """Create a new ontology in a workspace."""
    odl_store = get_odl_store()
    if not odl_store:
        raise HTTPException(status_code=503, detail="ODL store not available")
    
    try:
        ontology_id = odl_store.create_ontology(
            workspace_id=workspace_id,
            name=request.name,
            description=request.description
        )
        return {
            "success": True,
            "message": f"Ontology '{request.name}' created",
            "data": {"ontology_id": ontology_id}
        }
    except Exception as e:
        logger.error(f"Failed to create ontology: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/workspaces/{workspace_id}/ontology/{ontology_name}/version", tags=["ODL"])
async def create_ontology_version(
    workspace_id: str,
    ontology_name: str,
    request: CreateOntologyVersionRequest,
    username: str = "admin"
):
    """Create a new ontology version with ODL JSON."""
    odl_store = get_odl_store()
    if not odl_store:
        raise HTTPException(status_code=503, detail="ODL store not available")
    
    try:
        # Get or create ontology
        ontology = odl_store.get_ontology_by_workspace(workspace_id, ontology_name)
        if not ontology:
            ontology_id = odl_store.create_ontology(
                workspace_id=workspace_id,
                name=ontology_name
            )
        else:
            ontology_id = ontology["id"]
        
        # Create version
        version_id = odl_store.create_ontology_version(
            ontology_id=ontology_id,
            version_number=request.version_number,
            odl_json=request.odl_json,
            notes=request.notes,
            created_by=username
        )
        
        return {
            "success": True,
            "message": f"Ontology version '{request.version_number}' created",
            "data": {
                "ontology_id": ontology_id,
                "version_id": version_id,
                "version_number": request.version_number
            }
        }
    except Exception as e:
        logger.error(f"Failed to create ontology version: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/workspaces/{workspace_id}/ontology/{ontology_name}/version", tags=["ODL"])
async def get_ontology_version(
    workspace_id: str,
    ontology_name: str,
    version_number: Optional[str] = None
):
    """Get ontology version (latest if version_number not specified)."""
    odl_store = get_odl_store()
    if not odl_store:
        raise HTTPException(status_code=503, detail="ODL store not available")
    
    try:
        ontology = odl_store.get_ontology_by_workspace(workspace_id, ontology_name)
        if not ontology:
            raise HTTPException(status_code=404, detail=f"Ontology '{ontology_name}' not found")
        
        version = odl_store.get_ontology_version(ontology["id"], version_number)
        if not version:
            raise HTTPException(status_code=404, detail="Version not found")
        
        return {
            "success": True,
            "message": "Ontology version retrieved",
            "data": version
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get ontology version: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/workspaces/{workspace_id}/ontology/{ontology_name}/versions", tags=["ODL"])
async def list_ontology_versions(
    workspace_id: str,
    ontology_name: str,
    limit: int = 100
):
    """List all versions of an ontology."""
    odl_store = get_odl_store()
    if not odl_store:
        raise HTTPException(status_code=503, detail="ODL store not available")
    
    try:
        ontology = odl_store.get_ontology_by_workspace(workspace_id, ontology_name)
        if not ontology:
            raise HTTPException(status_code=404, detail=f"Ontology '{ontology_name}' not found")
        
        versions = odl_store.list_ontology_versions(ontology["id"], limit)
        
        return {
            "success": True,
            "message": f"Found {len(versions)} version(s)",
            "data": versions
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list ontology versions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/workspaces/{workspace_id}/ontology/{ontology_name}/versions/{version_id}/diff", tags=["ODL"])
async def get_ontology_version_diff(
    workspace_id: str,
    ontology_name: str,
    version_id: int,
    against: int
):
    """
    Get diff between two ontology versions.
    
    Args:
        workspace_id: Workspace ID
        ontology_name: Ontology name
        version_id: New version ID
        against: Old version ID to compare against
    """
    odl_store = get_odl_store()
    if not odl_store:
        raise HTTPException(status_code=503, detail="ODL store not available")
    
    try:
        # Get ontology
        ontology = odl_store.get_ontology_by_workspace(workspace_id, ontology_name)
        if not ontology:
            raise HTTPException(status_code=404, detail=f"Ontology '{ontology_name}' not found")
        
        # Check if diff already exists in DB
        existing_diff = odl_store.get_diff(against, version_id)
        
        if existing_diff:
            # Return cached diff
            return {
                "success": True,
                "message": "Diff retrieved from cache",
                "data": {
                    "summary": existing_diff["summary"],
                    "diff": existing_diff["diff_json"]
                }
            }
        
        # Get versions
        old_version = odl_store.get_version_by_id(against)
        new_version = odl_store.get_version_by_id(version_id)
        
        if not old_version:
            raise HTTPException(status_code=404, detail=f"Old version {against} not found")
        if not new_version:
            raise HTTPException(status_code=404, detail=f"New version {version_id} not found")
        
        # Process ODL to IR
        processor = ODLProcessor()
        old_ir, old_valid, old_errors = processor.process_from_dict(old_version["odl_json"])
        new_ir, new_valid, new_errors = processor.process_from_dict(new_version["odl_json"])
        
        if not old_valid:
            raise HTTPException(status_code=400, detail=f"Old version ODL invalid: {old_errors}")
        if not new_valid:
            raise HTTPException(status_code=400, detail=f"New version ODL invalid: {new_errors}")
        
        # Compute diff
        diff_engine = ODLDiffEngine()
        diff_result = diff_engine.diff(old_ir, new_ir)
        
        # Store diff in DB
        diff_id = odl_store.store_diff(
            ontology_id=ontology["id"],
            old_version_id=against,
            new_version_id=version_id,
            diff_json=diff_result.to_dict(),
            summary=diff_result.summary,
            created_by="api"
        )
        
        return {
            "success": True,
            "message": "Diff computed successfully",
            "data": {
                "diff_id": diff_id,
                "summary": diff_result.summary,
                "diff": diff_result.to_dict()
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to compute diff: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/workspaces/{workspace_id}/ontology/{ontology_name}/versions/{version_id}/eval", tags=["ODL"])
async def evaluate_ontology_version(
    workspace_id: str,
    ontology_name: str,
    version_id: int,
    request: EvaluateVersionRequest,
    username: str = "admin"
):
    """
    Evaluate ontology version against deployment gates.
    
    Args:
        workspace_id: Workspace ID
        ontology_name: Ontology name
        version_id: Version ID to evaluate
        request: Evaluation request with threshold profile
        username: Username for audit trail
    """
    from ..odl.evaluation import ODLEvaluator
    
    odl_store = get_odl_store()
    if not odl_store:
        raise HTTPException(status_code=503, detail="ODL store not available")
    
    try:
        # Get ontology
        ontology = odl_store.get_ontology_by_workspace(workspace_id, ontology_name)
        if not ontology:
            raise HTTPException(status_code=404, detail=f"Ontology '{ontology_name}' not found")
        
        # Get version
        version = odl_store.get_version_by_id(version_id)
        if not version:
            raise HTTPException(status_code=404, detail=f"Version {version_id} not found")
        
        # Verify version belongs to ontology
        if version["ontology_id"] != ontology["id"]:
            raise HTTPException(status_code=400, detail="Version does not belong to ontology")
        
        # Process ODL to IR
        processor = ODLProcessor()
        odl_ir, is_valid, errors = processor.process_from_dict(version["odl_json"])
        
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"ODL invalid: {errors}")
        
        # Evaluate
        evaluator = ODLEvaluator(threshold_profile=request.threshold_profile)
        eval_result = evaluator.evaluate(odl_ir, version_id, version["odl_json"])
        
        # Store eval run
        eval_run_id = odl_store.create_eval_run(
            ontology_version_id=version_id,
            threshold_profile=request.threshold_profile,
            metrics=eval_result.metrics,
            pass_fail=eval_result.overall_pass,
            notes=request.notes,
            created_by=username
        )
        
        # Format gate results with actionable messages
        gate_results = []
        for gate in eval_result.gate_results:
            gate_results.append({
                "gate_name": gate.gate_name,
                "category": gate.category.value,
                "status": gate.status.value,
                "message": gate.message,
                "details": gate.details
            })
        
        return {
            "success": True,
            "message": "Evaluation completed",
            "data": {
                "eval_run_id": eval_run_id,
                "version_id": version_id,
                "threshold_profile": request.threshold_profile,
                "overall_pass": eval_result.overall_pass,
                "summary": {
                    "total_gates": eval_result.metrics.get("total_gates", 0),
                    "passed": eval_result.metrics.get("passed", 0),
                    "failed": eval_result.metrics.get("failed", 0),
                    "warnings": eval_result.metrics.get("warnings", 0)
                },
                "gate_results": gate_results,
                "metrics": eval_result.metrics
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to evaluate version: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class DetectDriftRequest(BaseModel):
    """Request model for drift detection."""
    drift_type: str = "all"  # "mapping", "semantic_view", or "all"
    view_name: Optional[str] = None  # Required for semantic_view drift
    compiler_options: Optional[Dict[str, Any]] = None


@app.post("/api/v1/workspaces/{workspace_id}/ontology/{ontology_name}/versions/{version_id}/detect-drift", tags=["ODL"])
async def detect_ontology_drift(
    workspace_id: str,
    ontology_name: str,
    version_id: int,
    request: DetectDriftRequest,
    username: str = "admin"
):
    """
    Detect drift between ODL and Snowflake.
    
    Args:
        workspace_id: Workspace ID
        ontology_name: Ontology name
        version_id: Version ID to check
        request: Drift detection request
        username: Username for audit trail
    """
    from ..odl.drift import DriftDetector
    from ..snowflake.provider import MockSnowflakeProvider
    
    odl_store = get_odl_store()
    if not odl_store:
        raise HTTPException(status_code=503, detail="ODL store not available")
    
    try:
        # Get ontology
        ontology = odl_store.get_ontology_by_workspace(workspace_id, ontology_name)
        if not ontology:
            raise HTTPException(status_code=404, detail=f"Ontology '{ontology_name}' not found")
        
        # Get version
        version = odl_store.get_version_by_id(version_id)
        if not version:
            raise HTTPException(status_code=404, detail=f"Version {version_id} not found")
        
        # Verify version belongs to ontology
        if version["ontology_id"] != ontology["id"]:
            raise HTTPException(status_code=400, detail="Version does not belong to ontology")
        
        # Process ODL to IR
        processor = ODLProcessor()
        odl_ir, is_valid, errors = processor.process_from_dict(version["odl_json"])
        
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"ODL invalid: {errors}")
        
        # TODO: Get provider from config or use real Snowflake provider
        # For now, use mock provider (should be replaced with real provider)
        provider = MockSnowflakeProvider()
        
        # Detect drift
        detector = DriftDetector(provider)
        all_events = []
        
        if request.drift_type in ["mapping", "all"]:
            mapping_result = detector.detect_mapping_drift(odl_ir, ontology["id"])
            all_events.extend(mapping_result.drift_events)
        
        if request.drift_type in ["semantic_view", "all"]:
            if not request.view_name:
                raise HTTPException(status_code=400, detail="view_name required for semantic_view drift detection")
            
            semantic_result = detector.detect_semantic_view_drift(
                odl_ir,
                ontology["id"],
                request.view_name,
                request.compiler_options
            )
            all_events.extend(semantic_result.drift_events)
        
        # Store drift events in database
        event_ids = []
        for event in all_events:
            event_id = odl_store.create_drift_event(
                ontology_id=ontology["id"],
                event_type=event.event_type.value,
                details={
                    "drift_type": event.drift_type.value,
                    "element_name": event.element_name,
                    "message": event.message,
                    **event.details
                },
                status="OPEN",
                created_by=username
            )
            event_ids.append(event_id)
        
        return {
            "success": True,
            "message": f"Drift detection completed: {len(all_events)} event(s) found",
            "data": {
                "version_id": version_id,
                "drift_type": request.drift_type,
                "total_events": len(all_events),
                "event_ids": event_ids,
                "events": [e.to_dict() for e in all_events]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to detect drift: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/workspaces/{workspace_id}/ontology/{ontology_name}/drift-events", tags=["ODL"])
async def get_drift_events(
    workspace_id: str,
    ontology_name: str,
    status: Optional[str] = None,
    limit: int = 100
):
    """
    Get drift events for an ontology.
    
    Args:
        workspace_id: Workspace ID
        ontology_name: Ontology name
        status: Filter by status (OPEN, RESOLVED, IGNORED) or None for all
        limit: Maximum number of events to return
    """
    odl_store = get_odl_store()
    if not odl_store:
        raise HTTPException(status_code=503, detail="ODL store not available")
    
    try:
        # Get ontology
        ontology = odl_store.get_ontology_by_workspace(workspace_id, ontology_name)
        if not ontology:
            raise HTTPException(status_code=404, detail=f"Ontology '{ontology_name}' not found")
        
        # Get drift events
        events = odl_store.get_drift_events(ontology["id"], status, limit)
        
        return {
            "success": True,
            "message": f"Found {len(events)} drift event(s)",
            "data": events
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get drift events: {e}")
        raise HTTPException(status_code=500, detail=str(e))
