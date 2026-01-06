"""Base agent class"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from loguru import logger


class BaseAgent(ABC):
    """Base class for all agents"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, enabled: bool = True):
        """
        Initialize agent
        
        Args:
            config: Agent configuration
            enabled: Whether agent is enabled
        """
        self.config = config or {}
        self.enabled = enabled and self.config.get("enabled", True)
        self.name = self.__class__.__name__
        logger.info(f"Initialized {self.name} (enabled={self.enabled})")
    
    @abstractmethod
    async def process(self, *args, **kwargs) -> Any:
        """Process task - to be implemented by subclasses"""
        pass
    
    def is_enabled(self) -> bool:
        """Check if agent is enabled"""
        return self.enabled
    
    def get_status(self) -> Dict[str, Any]:
        """Get agent status"""
        return {
            "name": self.name,
            "enabled": self.enabled,
            "config": self.config
        }

