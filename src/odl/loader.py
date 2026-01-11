"""ODL JSON loader."""

import json
from pathlib import Path
from typing import Dict, Any, Union

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class ODLLoader:
    """Loads ODL JSON files."""
    
    @staticmethod
    def load(file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Load ODL JSON file.
        
        Args:
            file_path: Path to ODL JSON file
            
        Returns:
            Parsed ODL dictionary
            
        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If file is not valid JSON
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"ODL file not found: {file_path}")
        
        logger.info(f"Loading ODL file: {file_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            odl_data = json.load(f)
        
        logger.info(f"Loaded ODL: {odl_data.get('name', 'unnamed')} (version {odl_data.get('version', 'unknown')})")
        
        return odl_data
    
    @staticmethod
    def load_from_string(json_string: str) -> Dict[str, Any]:
        """
        Load ODL from JSON string.
        
        Args:
            json_string: JSON string containing ODL
            
        Returns:
            Parsed ODL dictionary
            
        Raises:
            json.JSONDecodeError: If string is not valid JSON
        """
        return json.loads(json_string)
