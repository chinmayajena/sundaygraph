"""Data ingestion agent"""

from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger

from .base_agent import BaseAgent
from ..data.data_processor import DataProcessor


class DataIngestionAgent(BaseAgent):
    """Agent responsible for ingesting and processing data"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize data ingestion agent"""
        super().__init__(config)
        self.processor = DataProcessor(
            chunk_size=self.config.get("chunk_size", 1000),
            overlap=self.config.get("overlap", 200)
        )
        self.batch_size = self.config.get("batch_size", 100)
        self.max_workers = self.config.get("max_workers", 4)
    
    async def process(self, input_path: str | Path) -> List[Dict[str, Any]]:
        """
        Process data from input path
        
        Args:
            input_path: Path to file or directory
            
        Returns:
            List of processed data items
        """
        if not self.is_enabled():
            logger.warning(f"{self.name} is disabled, skipping")
            return []
        
        input_path = Path(input_path)
        
        if not input_path.exists():
            logger.error(f"Input path does not exist: {input_path}")
            return []
        
        logger.info(f"{self.name} processing: {input_path}")
        
        if input_path.is_file():
            data = self.processor.process_file(input_path)
        elif input_path.is_dir():
            data = self.processor.process_directory(input_path)
        else:
            logger.error(f"Invalid input path: {input_path}")
            return []
        
        logger.info(f"{self.name} processed {len(data)} items")
        return data
    
    async def process_batch(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process a batch of data items
        
        Args:
            items: List of data items
            
        Returns:
            Processed items with metadata
        """
        processed = []
        
        for item in items:
            metadata = self.processor.extract_metadata(item)
            processed.append({
                **item,
                "metadata": metadata
            })
        
        return processed

