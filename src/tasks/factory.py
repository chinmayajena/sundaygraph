"""Task queue factory"""

from typing import Optional
from loguru import logger

from .base import TaskQueue
from .celery_queue import CeleryTaskQueue
from .temporal_queue import TemporalTaskQueue
from ..core.config import TaskQueueConfig


def create_task_queue(config: TaskQueueConfig) -> Optional[TaskQueue]:
    """
    Create task queue instance based on configuration
    
    Args:
        config: Task queue configuration
        
    Returns:
        TaskQueue instance or None if disabled
    """
    if not config.enabled:
        logger.info("Task queue is disabled")
        return None
    
    backend = config.backend.lower()
    
    if backend == "celery":
        try:
            return CeleryTaskQueue(
                broker_url=config.celery_broker_url,
                backend_url=config.celery_backend_url
            )
        except ImportError:
            logger.error("Celery is not installed. Install with: pip install celery[redis]")
            return None
        except Exception as e:
            logger.error(f"Failed to initialize Celery: {e}")
            return None
    
    elif backend == "temporal":
        try:
            return TemporalTaskQueue(
                temporal_host=config.temporal_host,
                namespace=config.temporal_namespace
            )
        except ImportError:
            logger.error("Temporal Python SDK is not installed. Install with: pip install temporalio")
            return None
        except Exception as e:
            logger.error(f"Failed to initialize Temporal: {e}")
            return None
    
    elif backend == "none":
        logger.info("Task queue backend set to 'none', running synchronously")
        return None
    
    else:
        logger.warning(f"Unknown task queue backend: {backend}. Running synchronously.")
        return None
