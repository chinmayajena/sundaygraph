"""ODL validator with actionable error messages."""

from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import json

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class ODLValidationError(Exception):
    """ODL validation error with actionable message."""
    
    def __init__(self, message: str, path: Optional[str] = None, value: Any = None):
        super().__init__(message)
        self.message = message
        self.path = path
        self.value = value
    
    def __str__(self) -> str:
        msg = self.message
        if self.path:
            msg += f" (path: {self.path})"
        if self.value is not None:
            msg += f" (value: {self.value})"
        return msg


class ODLValidator:
    """Validates ODL structure and references."""
    
    def __init__(self, schema_path: Optional[Path] = None):
        """
        Initialize validator.
        
        Args:
            schema_path: Path to JSON Schema file (optional, for future use)
        """
        self.schema_path = schema_path or Path(__file__).parent.parent.parent / "odl" / "schema" / "odl.schema.json"
        self.errors: List[ODLValidationError] = []
    
    def validate(self, odl_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate ODL data.
        
        Args:
            odl_data: ODL dictionary to validate
            
        Returns:
            Tuple of (is_valid, list_of_error_messages)
        """
        self.errors = []
        
        # Basic structure validation
        self._validate_structure(odl_data)
        
        # Reference validation
        self._validate_references(odl_data)
        
        # Business rule validation
        self._validate_business_rules(odl_data)
        
        # Snowflake mapping validation
        self._validate_snowflake_mapping(odl_data)
        
        is_valid = len(self.errors) == 0
        error_messages = [str(e) for e in self.errors]
        
        if is_valid:
            logger.info("ODL validation passed")
        else:
            logger.warning(f"ODL validation failed with {len(self.errors)} error(s)")
        
        return is_valid, error_messages
    
    def _validate_structure(self, odl_data: Dict[str, Any]) -> None:
        """Validate basic structure."""
        if "version" not in odl_data:
            self.errors.append(ODLValidationError(
                "Missing required field: 'version'",
                path="version"
            ))
        
        if "objects" not in odl_data:
            self.errors.append(ODLValidationError(
                "Missing required field: 'objects'",
                path="objects"
            ))
        elif not isinstance(odl_data["objects"], list):
            self.errors.append(ODLValidationError(
                "Field 'objects' must be an array",
                path="objects",
                value=type(odl_data["objects"]).__name__
            ))
        elif len(odl_data["objects"]) == 0:
            self.errors.append(ODLValidationError(
                "Field 'objects' cannot be empty",
                path="objects"
            ))
    
    def _validate_references(self, odl_data: Dict[str, Any]) -> None:
        """Validate object references in relationships, metrics, and dimensions."""
        objects = odl_data.get("objects", [])
        object_names = {obj["name"] for obj in objects if "name" in obj}
        
        # Validate relationship references
        relationships = odl_data.get("relationships", [])
        for i, rel in enumerate(relationships):
            if "from" not in rel or "to" not in rel:
                continue
            
            from_obj = rel["from"]
            to_obj = rel["to"]
            
            if from_obj not in object_names:
                self.errors.append(ODLValidationError(
                    f"Relationship '{rel.get('name', f'#{i}')}' references unknown object '{from_obj}' in 'from' field. "
                    f"Available objects: {sorted(object_names)}",
                    path=f"relationships[{i}].from",
                    value=from_obj
                ))
            
            if to_obj not in object_names:
                self.errors.append(ODLValidationError(
                    f"Relationship '{rel.get('name', f'#{i}')}' references unknown object '{to_obj}' in 'to' field. "
                    f"Available objects: {sorted(object_names)}",
                    path=f"relationships[{i}].to",
                    value=to_obj
                ))
        
        # Validate metric grain references
        metrics = odl_data.get("metrics", [])
        for i, metric in enumerate(metrics):
            grain = metric.get("grain", [])
            if not isinstance(grain, list):
                continue
            
            for j, grain_obj in enumerate(grain):
                if grain_obj not in object_names:
                    self.errors.append(ODLValidationError(
                        f"Metric '{metric.get('name', f'#{i}')}' references unknown object '{grain_obj}' in grain. "
                        f"Available objects: {sorted(object_names)}",
                        path=f"metrics[{i}].grain[{j}]",
                        value=grain_obj
                    ))
        
        # Validate dimension sourceProperty references
        dimensions = odl_data.get("dimensions", [])
        for i, dim in enumerate(dimensions):
            source_prop = dim.get("sourceProperty", "")
            if "." not in source_prop:
                self.errors.append(ODLValidationError(
                    f"Dimension '{dim.get('name', f'#{i}')}' has invalid sourceProperty format '{source_prop}'. "
                    f"Expected format: 'Object.property'",
                    path=f"dimensions[{i}].sourceProperty",
                    value=source_prop
                ))
                continue
            
            obj_name, prop_name = source_prop.split(".", 1)
            if obj_name not in object_names:
                self.errors.append(ODLValidationError(
                    f"Dimension '{dim.get('name', f'#{i}')}' references unknown object '{obj_name}' in sourceProperty. "
                    f"Available objects: {sorted(object_names)}",
                    path=f"dimensions[{i}].sourceProperty",
                    value=source_prop
                ))
    
    def _validate_business_rules(self, odl_data: Dict[str, Any]) -> None:
        """Validate business rules (duplicates, invalid values, etc.)."""
        # Check for duplicate metric names
        metrics = odl_data.get("metrics", [])
        metric_names = {}
        for i, metric in enumerate(metrics):
            name = metric.get("name")
            if not name:
                continue
            
            if name in metric_names:
                self.errors.append(ODLValidationError(
                    f"Duplicate metric name '{name}' found at metrics[{i}]. "
                    f"First occurrence at metrics[{metric_names[name]}]",
                    path=f"metrics[{i}].name",
                    value=name
                ))
            else:
                metric_names[name] = i
        
        # Check for duplicate object names
        objects = odl_data.get("objects", [])
        object_names = {}
        for i, obj in enumerate(objects):
            name = obj.get("name")
            if not name:
                continue
            
            if name in object_names:
                self.errors.append(ODLValidationError(
                    f"Duplicate object name '{name}' found at objects[{i}]. "
                    f"First occurrence at objects[{object_names[name]}]",
                    path=f"objects[{i}].name",
                    value=name
                ))
            else:
                object_names[name] = i
        
        # Validate relationship cardinality
        relationships = odl_data.get("relationships", [])
        valid_cardinalities = {"one_to_one", "one_to_many", "many_to_one", "many_to_many"}
        for i, rel in enumerate(relationships):
            cardinality = rel.get("cardinality", "many_to_one")
            if cardinality not in valid_cardinalities:
                self.errors.append(ODLValidationError(
                    f"Relationship '{rel.get('name', f'#{i}')}' has invalid cardinality '{cardinality}'. "
                    f"Valid values: {sorted(valid_cardinalities)}",
                    path=f"relationships[{i}].cardinality",
                    value=cardinality
                ))
    
    def _validate_snowflake_mapping(self, odl_data: Dict[str, Any]) -> None:
        """Validate Snowflake mapping and join keys."""
        snowflake = odl_data.get("snowflake")
        if not snowflake:
            return
        
        objects = odl_data.get("objects", [])
        relationships = odl_data.get("relationships", [])
        
        # Build object property map
        object_properties: Dict[str, Dict[str, Any]] = {}
        for obj in objects:
            obj_name = obj.get("name")
            if not obj_name:
                continue
            
            object_properties[obj_name] = {
                prop.get("name"): prop
                for prop in obj.get("properties", [])
                if prop.get("name")
            }
        
        # Validate relationship join keys exist in mapped objects
        for i, rel in enumerate(relationships):
            from_obj = rel.get("from")
            to_obj = rel.get("to")
            join_keys = rel.get("joinKeys", [])
            
            if not from_obj or not to_obj:
                continue
            
            for j, join_key_pair in enumerate(join_keys):
                if not isinstance(join_key_pair, list) or len(join_key_pair) != 2:
                    continue
                
                from_prop, to_prop = join_key_pair[0], join_key_pair[1]
                
                # Check from property exists
                if from_obj not in object_properties:
                    self.errors.append(ODLValidationError(
                        f"Relationship '{rel.get('name', f'#{i}')}' join key references unknown object '{from_obj}'. "
                        f"Available objects: {sorted(object_properties.keys())}",
                        path=f"relationships[{i}].joinKeys[{j}][0]",
                        value=from_obj
                    ))
                elif from_prop not in object_properties[from_obj]:
                    available_props = sorted(object_properties[from_obj].keys())
                    self.errors.append(ODLValidationError(
                        f"Relationship '{rel.get('name', f'#{i}')}' join key references unknown property '{from_prop}' "
                        f"in object '{from_obj}'. Available properties: {available_props}",
                        path=f"relationships[{i}].joinKeys[{j}][0]",
                        value=from_prop
                    ))
                
                # Check to property exists
                if to_obj not in object_properties:
                    self.errors.append(ODLValidationError(
                        f"Relationship '{rel.get('name', f'#{i}')}' join key references unknown object '{to_obj}'. "
                        f"Available objects: {sorted(object_properties.keys())}",
                        path=f"relationships[{i}].joinKeys[{j}][1]",
                        value=to_obj
                    ))
                elif to_prop not in object_properties[to_obj]:
                    available_props = sorted(object_properties[to_obj].keys())
                    self.errors.append(ODLValidationError(
                        f"Relationship '{rel.get('name', f'#{i}')}' join key references unknown property '{to_prop}' "
                        f"in object '{to_obj}'. Available properties: {available_props}",
                        path=f"relationships[{i}].joinKeys[{j}][1]",
                        value=to_prop
                    ))
