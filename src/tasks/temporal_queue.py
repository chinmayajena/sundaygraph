"""Temporal-based task queue implementation"""

from typing import Dict, Any, Optional, List
from loguru import logger
from datetime import datetime

from .base import TaskQueue, TaskStatus, TaskResult


class TemporalTaskQueue(TaskQueue):
    """
    Temporal-based task queue implementation.
    Provides workflow orchestration with built-in retries and state management.
    """
    
    def __init__(self, temporal_host: str = "localhost:7233", namespace: str = "default"):
        """
        Initialize Temporal task queue
        
        Args:
            temporal_host: Temporal server host:port
            namespace: Temporal namespace
        """
        try:
            from temporalio.client import Client
            from temporalio.worker import Worker
        except ImportError:
            raise ImportError(
                "Temporal Python SDK is not installed. Install with: pip install temporalio"
            )
        
        self.temporal_host = temporal_host
        self.namespace = namespace
        self.client: Optional[Client] = None
        self._task_storage: Dict[str, TaskResult] = {}  # In-memory storage for task status
        
        logger.info(f"Temporal task queue initialized (host: {temporal_host}, namespace: {namespace})")
    
    async def _get_client(self):
        """Get or create Temporal client"""
        if self.client is None:
            from temporalio.client import Client
            self.client = await Client.connect(
                target_host=self.temporal_host,
                namespace=self.namespace
            )
        return self.client
    
    async def enqueue(
        self,
        task_name: str,
        *args,
        **kwargs
    ) -> str:
        """Enqueue a task as Temporal workflow"""
        from temporalio.common import WorkflowIDReusePolicy
        
        client = await self._get_client()
        
        # Generate workflow ID
        import uuid
        workflow_id = f"{task_name}-{uuid.uuid4().hex[:8]}"
        
        # Start workflow based on task name
        if task_name == 'ingest_data':
            from .workflows import ingest_data_workflow
            handle = await client.start_workflow(
                ingest_data_workflow,
                args=args,
                id=workflow_id,
                task_queue="sundaygraph-tasks",
                id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE
            )
        elif task_name == 'build_ontology':
            from .workflows import build_ontology_workflow
            handle = await client.start_workflow(
                build_ontology_workflow,
                args=args,
                id=workflow_id,
                task_queue="sundaygraph-tasks",
                id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE
            )
        else:
            raise ValueError(f"Unknown task: {task_name}")
        
        # Store initial status
        self._task_storage[workflow_id] = TaskResult(
            task_id=workflow_id,
            status=TaskStatus.PENDING,
            created_at=datetime.utcnow()
        )
        
        return workflow_id
    
    async def get_status(self, task_id: str) -> TaskResult:
        """Get task status from Temporal workflow"""
        client = await self._get_client()
        
        try:
            handle = client.get_workflow_handle(task_id)
            description = await handle.describe()
            
            # Map Temporal status to our TaskStatus
            status_map = {
                'RUNNING': TaskStatus.RUNNING,
                'COMPLETED': TaskStatus.SUCCESS,
                'FAILED': TaskStatus.FAILURE,
                'CANCELED': TaskStatus.CANCELLED,
                'TERMINATED': TaskStatus.CANCELLED,
            }
            
            status = status_map.get(description.status.name, TaskStatus.PENDING)
            
            # Get result if completed
            result = None
            error = None
            if status == TaskStatus.SUCCESS:
                try:
                    result = await handle.result()
                except Exception:
                    pass
            elif status == TaskStatus.FAILURE:
                try:
                    error = str(description.failure) if hasattr(description, 'failure') else "Workflow failed"
                except Exception:
                    pass
            
            return TaskResult(
                task_id=task_id,
                status=status,
                result=result,
                error=error,
                created_at=description.start_time if hasattr(description, 'start_time') else None,
                started_at=description.start_time if hasattr(description, 'start_time') else None,
                completed_at=description.close_time if hasattr(description, 'close_time') else None
            )
        except Exception as e:
            # Fallback to stored status
            if task_id in self._task_storage:
                return self._task_storage[task_id]
            
            logger.error(f"Failed to get task status: {e}")
            return TaskResult(
                task_id=task_id,
                status=TaskStatus.PENDING,
                error=str(e)
            )
    
    async def get_result(self, task_id: str, timeout: Optional[float] = None) -> TaskResult:
        """Get task result (wait for completion)"""
        client = await self._get_client()
        
        try:
            handle = client.get_workflow_handle(task_id)
            result = await handle.result(timeout=timeout)
            
            return TaskResult(
                task_id=task_id,
                status=TaskStatus.SUCCESS,
                result=result,
                completed_at=datetime.utcnow()
            )
        except Exception as e:
            return TaskResult(
                task_id=task_id,
                status=TaskStatus.FAILURE,
                error=str(e),
                completed_at=datetime.utcnow()
            )
    
    async def cancel(self, task_id: str) -> bool:
        """Cancel a workflow"""
        client = await self._get_client()
        
        try:
            handle = client.get_workflow_handle(task_id)
            await handle.cancel()
            return True
        except Exception as e:
            logger.error(f"Failed to cancel task: {e}")
            return False
    
    async def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        limit: int = 100
    ) -> List[TaskResult]:
        """List workflows (Temporal provides workflow listing)"""
        client = await self._get_client()
        
        try:
            # List workflows
            workflows = []
            async for workflow in client.list_workflows():
                workflows.append(workflow)
                if len(workflows) >= limit:
                    break
            
            # Convert to TaskResult
            results = []
            for workflow in workflows:
                task_result = await self.get_status(workflow.id)
                if status is None or task_result.status == status:
                    results.append(task_result)
            
            return results
        except Exception as e:
            logger.error(f"Failed to list tasks: {e}")
            return []
