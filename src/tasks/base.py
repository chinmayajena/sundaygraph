"""Base task queue interface"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime


class TaskStatus(str, Enum):
    """Task status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


@dataclass
class TaskResult:
    """Task execution result"""
    task_id: str
    status: TaskStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    progress: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class TaskQueue(ABC):
    """
    Abstract base class for task queue implementations.
    Supports both Celery and Temporal backends.
    """
    
    @abstractmethod
    async def enqueue(
        self,
        task_name: str,
        *args,
        **kwargs
    ) -> str:
        """
        Enqueue a task for async execution
        
        Args:
            task_name: Name of the task to execute
            *args: Positional arguments for the task
            **kwargs: Keyword arguments for the task
            
        Returns:
            Task ID
        """
        pass
    
    @abstractmethod
    async def get_status(self, task_id: str) -> TaskResult:
        """
        Get task status
        
        Args:
            task_id: Task identifier
            
        Returns:
            TaskResult with current status
        """
        pass
    
    @abstractmethod
    async def get_result(self, task_id: str, timeout: Optional[float] = None) -> TaskResult:
        """
        Get task result (wait for completion if needed)
        
        Args:
            task_id: Task identifier
            timeout: Maximum time to wait (None = wait indefinitely)
            
        Returns:
            TaskResult with final status and result
        """
        pass
    
    @abstractmethod
    async def cancel(self, task_id: str) -> bool:
        """
        Cancel a running task
        
        Args:
            task_id: Task identifier
            
        Returns:
            True if cancelled successfully
        """
        pass
    
    @abstractmethod
    async def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        limit: int = 100
    ) -> List[TaskResult]:
        """
        List tasks
        
        Args:
            status: Filter by status (None = all)
            limit: Maximum number of tasks to return
            
        Returns:
            List of TaskResult objects
        """
        pass
