"""Celery-based task queue implementation"""

from typing import Dict, Any, Optional, List
from loguru import logger
from datetime import datetime

from .base import TaskQueue, TaskStatus, TaskResult


class CeleryTaskQueue(TaskQueue):
    """
    Celery-based task queue implementation.
    Requires Redis or RabbitMQ as message broker.
    """
    
    def __init__(self, broker_url: str = "redis://localhost:6379/0", backend_url: Optional[str] = None):
        """
        Initialize Celery task queue
        
        Args:
            broker_url: Celery broker URL (Redis/RabbitMQ)
            backend_url: Result backend URL (optional, defaults to broker_url)
        """
        try:
            from celery import Celery
            from celery.result import AsyncResult
        except ImportError:
            raise ImportError(
                "Celery is not installed. Install with: pip install celery[redis]"
            )
        
        self.broker_url = broker_url
        self.backend_url = backend_url or broker_url
        
        # Initialize Celery app
        self.celery_app = Celery(
            'sundaygraph',
            broker=broker_url,
            backend=self.backend_url
        )
        
        # Configure Celery
        self.celery_app.conf.update(
            task_serializer='json',
            accept_content=['json'],
            result_serializer='json',
            timezone='UTC',
            enable_utc=True,
            task_track_started=True,
            task_time_limit=3600,  # 1 hour max
            task_soft_time_limit=3300,  # 55 minutes soft limit
        )
        
        # Register tasks
        self._register_tasks()
        
        logger.info(f"Celery task queue initialized (broker: {broker_url})")
    
    def _register_tasks(self):
        """Register ingestion tasks with Celery"""
        from ..core.sundaygraph import SundayGraph
        from pathlib import Path
        
        @self.celery_app.task(name='ingest_data', bind=True)
        def ingest_data_task(self, config_path: str, input_path: str, workspace_id: Optional[str] = None):
            """Celery task for data ingestion"""
            try:
                # Update task state
                self.update_state(state='RUNNING', meta={'progress': 0, 'stage': 'initializing'})
                
                # Initialize SundayGraph
                sg = SundayGraph(config_path=Path(config_path) if config_path else None)
                
                # Run ingestion (sync wrapper for async)
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(sg.ingest_data(input_path, workspace_id))
                loop.close()
                
                return {
                    'status': 'success',
                    'result': result,
                    'progress': 100
                }
            except Exception as e:
                logger.error(f"Ingestion task failed: {e}")
                raise
        
        @self.celery_app.task(name='build_ontology', bind=True)
        def build_ontology_task(self, config_path: str, domain_description: str):
            """Celery task for ontology building"""
            try:
                self.update_state(state='RUNNING', meta={'progress': 0, 'stage': 'building'})
                
                sg = SundayGraph(config_path=Path(config_path) if config_path else None)
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(sg.build_schema_from_domain(domain_description))
                loop.close()
                
                return {
                    'status': 'success',
                    'result': result,
                    'progress': 100
                }
            except Exception as e:
                logger.error(f"Ontology building task failed: {e}")
                raise
        
        self.ingest_data_task = ingest_data_task
        self.build_ontology_task = build_ontology_task
    
    async def enqueue(
        self,
        task_name: str,
        *args,
        **kwargs
    ) -> str:
        """Enqueue a task"""
        if task_name == 'ingest_data':
            task = self.ingest_data_task.delay(*args, **kwargs)
        elif task_name == 'build_ontology':
            task = self.build_ontology_task.delay(*args, **kwargs)
        else:
            raise ValueError(f"Unknown task: {task_name}")
        
        return task.id
    
    async def get_status(self, task_id: str) -> TaskResult:
        """Get task status"""
        from celery.result import AsyncResult
        
        result = AsyncResult(task_id, app=self.celery_app)
        
        # Map Celery states to our TaskStatus
        state_map = {
            'PENDING': TaskStatus.PENDING,
            'STARTED': TaskStatus.RUNNING,
            'SUCCESS': TaskStatus.SUCCESS,
            'FAILURE': TaskStatus.FAILURE,
            'RETRY': TaskStatus.RETRYING,
            'REVOKED': TaskStatus.CANCELLED,
        }
        
        status = state_map.get(result.state, TaskStatus.PENDING)
        
        # Get result data
        result_data = None
        error = None
        progress = None
        
        if result.ready():
            if result.successful():
                result_data = result.result.get('result') if isinstance(result.result, dict) else result.result
                progress = result.result.get('progress') if isinstance(result.result, dict) else None
            else:
                error = str(result.info) if result.info else "Task failed"
        elif result.info:
            # Task is running, get progress
            if isinstance(result.info, dict):
                progress = result.info.get('progress')
        
        return TaskResult(
            task_id=task_id,
            status=status,
            result=result_data,
            error=error,
            progress=progress,
            created_at=datetime.utcnow() if result.date_created else None,
            started_at=datetime.utcnow() if result.date_started else None,
            completed_at=datetime.utcnow() if result.date_done else None
        )
    
    async def get_result(self, task_id: str, timeout: Optional[float] = None) -> TaskResult:
        """Get task result (wait if needed)"""
        from celery.result import AsyncResult
        
        result = AsyncResult(task_id, app=self.celery_app)
        
        # Wait for result
        try:
            result_data = result.get(timeout=timeout)
            
            # Parse result
            if isinstance(result_data, dict):
                return TaskResult(
                    task_id=task_id,
                    status=TaskStatus.SUCCESS if result_data.get('status') == 'success' else TaskStatus.FAILURE,
                    result=result_data.get('result'),
                    error=result_data.get('error'),
                    progress=result_data.get('progress'),
                    completed_at=datetime.utcnow()
                )
            else:
                return TaskResult(
                    task_id=task_id,
                    status=TaskStatus.SUCCESS,
                    result=result_data,
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
        """Cancel a task"""
        self.celery_app.control.revoke(task_id, terminate=True)
        return True
    
    async def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        limit: int = 100
    ) -> List[TaskResult]:
        """List tasks (Celery doesn't have built-in task listing, would need custom storage)"""
        # Note: Celery doesn't provide a built-in way to list all tasks
        # This would require storing task IDs in Redis/database
        logger.warning("Celery doesn't support listing all tasks without custom storage")
        return []
