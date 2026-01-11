"""ODL core module - main entry point."""

from pathlib import Path
from typing import List, Tuple, Union

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from .loader import ODLLoader
from .validator import ODLValidator
from .normalizer import ODLNormalizer
from .ir import ODLIR


class ODLProcessor:
    """Main ODL processor that loads, validates, and normalizes ODL files."""
    
    def __init__(self, schema_path: Union[str, Path, None] = None):
        """
        Initialize ODL processor.
        
        Args:
            schema_path: Path to JSON Schema file (optional)
        """
        self.loader = ODLLoader()
        self.validator = ODLValidator(schema_path)
        self.normalizer = ODLNormalizer()
    
    def process(self, file_path: Union[str, Path]) -> Tuple[ODLIR, bool, List[str]]:
        """
        Load, validate, and normalize ODL file.
        
        Args:
            file_path: Path to ODL JSON file
            
        Returns:
            Tuple of (normalized_ir, is_valid, error_messages)
        """
        # Load
        odl_data = self.loader.load(file_path)
        
        # Validate
        is_valid, error_messages = self.validator.validate(odl_data)
        
        # Normalize (even if validation fails, for debugging)
        ir = self.normalizer.normalize(odl_data)
        
        return ir, is_valid, error_messages
    
    def process_from_string(self, json_string: str) -> Tuple[ODLIR, bool, List[str]]:
        """
        Load, validate, and normalize ODL from JSON string.
        
        Args:
            json_string: JSON string containing ODL
            
        Returns:
            Tuple of (normalized_ir, is_valid, error_messages)
        """
        # Load
        odl_data = self.loader.load_from_string(json_string)
        
        # Validate
        is_valid, error_messages = self.validator.validate(odl_data)
        
        # Normalize
        ir = self.normalizer.normalize(odl_data)
        
        return ir, is_valid, error_messages
    
    def process_from_dict(self, odl_dict: dict) -> Tuple[ODLIR, bool, List[str]]:
        """
        Load, validate, and normalize ODL from dictionary.
        
        Args:
            odl_dict: Dictionary containing ODL data
            
        Returns:
            Tuple of (normalized_ir, is_valid, error_messages)
        """
        # Validate
        is_valid, error_messages = self.validator.validate(odl_dict)
        
        # Normalize
        ir = self.normalizer.normalize(odl_dict)
        
        return ir, is_valid, error_messages
