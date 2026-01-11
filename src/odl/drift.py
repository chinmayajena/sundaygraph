"""ODL drift detection - mapping drift and semantic view drift."""

from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import yaml
from pathlib import Path

from .ir import ODLIR, ObjectIR
from ..snowflake.provider import SnowflakeProvider, TableSchema, SemanticViewYAML


class DriftType(Enum):
    """Type of drift detected."""
    MAPPING_DRIFT = "mapping_drift"
    SEMANTIC_VIEW_DRIFT = "semantic_view_drift"


class DriftEventType(Enum):
    """Specific drift event type."""
    COLUMN_MISSING = "column_missing"
    COLUMN_RENAMED = "column_renamed"
    COLUMN_ADDED = "column_added"
    TABLE_MISSING = "table_missing"
    YAML_DIVERGENCE = "yaml_divergence"
    MANUAL_EDIT_DETECTED = "manual_edit_detected"


@dataclass
class DriftEvent:
    """A single drift event."""
    event_type: DriftEventType
    drift_type: DriftType
    element_name: str  # Object name, table name, or view name
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_type": self.event_type.value,
            "drift_type": self.drift_type.value,
            "element_name": self.element_name,
            "message": self.message,
            "details": self.details
        }


@dataclass
class DriftDetectionResult:
    """Result of drift detection."""
    ontology_id: int
    drift_events: List[DriftEvent] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "ontology_id": self.ontology_id,
            "total_events": len(self.drift_events),
            "events": [e.to_dict() for e in self.drift_events]
        }


class DriftDetector:
    """Detects drift between ODL and Snowflake."""
    
    def __init__(self, provider: SnowflakeProvider):
        """
        Initialize drift detector.
        
        Args:
            provider: Snowflake provider for schema information
        """
        self.provider = provider
    
    def detect_mapping_drift(self, odl_ir: ODLIR, ontology_id: int) -> DriftDetectionResult:
        """
        Detect mapping drift (schema drift) between ODL and Snowflake.
        
        Args:
            odl_ir: ODL IR to check
            ontology_id: Ontology ID
            
        Returns:
            DriftDetectionResult with mapping drift events
        """
        result = DriftDetectionResult(ontology_id=ontology_id)
        
        if not odl_ir.snowflake:
            return result
        
        database = odl_ir.snowflake.database
        schema = odl_ir.snowflake.schema
        
        # Check each object's table mapping
        for obj in odl_ir.objects:
            # Get table name
            table_name = (
                obj.snowflake_table or
                odl_ir.snowflake.table_mappings.get(obj.name) or
                obj.name.lower()
            )
            
            # Get actual table schema from Snowflake
            table_schema = self.provider.get_table_schema(database, schema, table_name)
            
            if not table_schema:
                # Table doesn't exist
                result.drift_events.append(DriftEvent(
                    event_type=DriftEventType.TABLE_MISSING,
                    drift_type=DriftType.MAPPING_DRIFT,
                    element_name=obj.name,
                    message=f"Table '{table_name}' not found in {database}.{schema}",
                    details={
                        "expected_table": table_name,
                        "database": database,
                        "schema": schema,
                        "object_name": obj.name
                    }
                ))
                continue
            
            # Compare columns
            self._compare_columns(obj, table_schema, result)
        
        return result
    
    def _compare_columns(self, obj: ObjectIR, table_schema: TableSchema, result: DriftDetectionResult):
        """Compare ODL object properties with table columns."""
        # Get expected columns from ODL
        expected_columns = {prop.name: prop for prop in obj.properties}
        
        # Get actual columns from Snowflake
        actual_columns = {col["name"]: col for col in table_schema.columns}
        
        # Find missing columns (in ODL but not in Snowflake)
        for prop_name, prop in expected_columns.items():
            if prop_name not in actual_columns:
                result.drift_events.append(DriftEvent(
                    event_type=DriftEventType.COLUMN_MISSING,
                    drift_type=DriftType.MAPPING_DRIFT,
                    element_name=obj.name,
                    message=f"Column '{prop_name}' missing in table '{table_schema.table}'",
                    details={
                        "object_name": obj.name,
                        "table": table_schema.table,
                        "missing_column": prop_name,
                        "column_type": prop.type
                    }
                ))
        
        # Find added columns (in Snowflake but not in ODL)
        for col_name, col_info in actual_columns.items():
            if col_name not in expected_columns:
                result.drift_events.append(DriftEvent(
                    event_type=DriftEventType.COLUMN_ADDED,
                    drift_type=DriftType.MAPPING_DRIFT,
                    element_name=obj.name,
                    message=f"Column '{col_name}' added in table '{table_schema.table}' (not in ODL)",
                    details={
                        "object_name": obj.name,
                        "table": table_schema.table,
                        "added_column": col_name,
                        "column_type": col_info.get("type", "unknown")
                    }
                ))
        
        # Check for renamed columns (heuristic: similar names or type matches)
        # This is a simplified check - in reality, you might use more sophisticated matching
        for prop_name, prop in expected_columns.items():
            if prop_name not in actual_columns:
                # Look for potential rename candidates
                candidates = []
                for col_name, col_info in actual_columns.items():
                    if col_name not in expected_columns:
                        # Check if types match (simplified)
                        if self._types_match(prop.type, col_info.get("type", "")):
                            candidates.append(col_name)
                
                if len(candidates) == 1:
                    # Likely a rename
                    result.drift_events.append(DriftEvent(
                        event_type=DriftEventType.COLUMN_RENAMED,
                        drift_type=DriftType.MAPPING_DRIFT,
                        element_name=obj.name,
                        message=f"Column '{prop_name}' possibly renamed to '{candidates[0]}' in table '{table_schema.table}'",
                        details={
                            "object_name": obj.name,
                            "table": table_schema.table,
                            "old_column": prop_name,
                            "new_column": candidates[0],
                            "column_type": prop.type
                        }
                    ))
    
    def _types_match(self, odl_type: str, snowflake_type: str) -> bool:
        """Check if ODL type matches Snowflake type (simplified)."""
        type_mapping = {
            "string": ["VARCHAR", "TEXT", "STRING"],
            "integer": ["INTEGER", "INT", "BIGINT"],
            "number": ["NUMBER", "DECIMAL", "FLOAT", "DOUBLE"],
            "decimal": ["DECIMAL", "NUMBER"],
            "boolean": ["BOOLEAN", "BOOL"],
            "date": ["DATE"],
            "timestamp": ["TIMESTAMP", "TIMESTAMP_NTZ", "TIMESTAMP_LTZ"],
            "time": ["TIME"]
        }
        
        snowflake_upper = snowflake_type.upper()
        odl_mappings = type_mapping.get(odl_type.lower(), [])
        
        return any(snowflake_upper.startswith(m) for m in odl_mappings)
    
    def detect_semantic_view_drift(
        self,
        odl_ir: ODLIR,
        ontology_id: int,
        view_name: str,
        compiler_options: Optional[Dict[str, Any]] = None
    ) -> DriftDetectionResult:
        """
        Detect semantic view drift by comparing exported YAML with compiler-generated YAML.
        
        Args:
            odl_ir: ODL IR to check
            ontology_id: Ontology ID
            view_name: Semantic view name
            compiler_options: Options for compiler
            
        Returns:
            DriftDetectionResult with semantic view drift events
        """
        result = DriftDetectionResult(ontology_id=ontology_id)
        
        if not odl_ir.snowflake:
            return result
        
        database = odl_ir.snowflake.database
        schema = odl_ir.snowflake.schema
        
        # Get YAML from existing semantic view
        semantic_view = self.provider.get_semantic_view_yaml(database, schema, view_name)
        
        if not semantic_view:
            # View doesn't exist - not a drift, just not deployed
            return result
        
        # Generate YAML from ODL using compiler
        try:
            from ..snowflake.snowflake_compiler import SnowflakeCompiler
            
            compiler = SnowflakeCompiler()
            options = compiler_options or {
                "version_id": f"drift-check-{odl_ir.version}",
                "view_name": view_name,
                "database": database,
                "schema": schema
            }
            
            bundle = compiler.compile(odl_ir, options)
            generated_yaml_file = bundle.get_file("semantic_model.yaml")
            
            if not generated_yaml_file:
                result.drift_events.append(DriftEvent(
                    event_type=DriftEventType.YAML_DIVERGENCE,
                    drift_type=DriftType.SEMANTIC_VIEW_DRIFT,
                    element_name=view_name,
                    message="Failed to generate YAML from ODL",
                    details={"view_name": view_name}
                ))
                return result
            
            # Compare YAMLs
            self._compare_yamls(
                semantic_view.yaml_content,
                generated_yaml_file.content,
                view_name,
                result
            )
        except Exception as e:
            result.drift_events.append(DriftEvent(
                event_type=DriftEventType.YAML_DIVERGENCE,
                drift_type=DriftType.SEMANTIC_VIEW_DRIFT,
                element_name=view_name,
                message=f"Error comparing YAMLs: {str(e)}",
                details={"view_name": view_name, "error": str(e)}
            ))
        
        return result
    
    def _compare_yamls(self, actual_yaml: str, expected_yaml: str, view_name: str, result: DriftDetectionResult):
        """Compare two YAML strings and detect differences."""
        try:
            actual_data = yaml.safe_load(actual_yaml)
            expected_data = yaml.safe_load(expected_yaml)
        except yaml.YAMLError as e:
            result.drift_events.append(DriftEvent(
                event_type=DriftEventType.YAML_DIVERGENCE,
                drift_type=DriftType.SEMANTIC_VIEW_DRIFT,
                element_name=view_name,
                message=f"Error parsing YAML: {str(e)}",
                details={"view_name": view_name, "error": str(e)}
            ))
            return
        
        # Compare semantic model structures
        actual_sm = actual_data.get("semantic_model", {})
        expected_sm = expected_data.get("semantic_model", {})
        
        # Compare logical tables
        self._compare_logical_tables(actual_sm, expected_sm, view_name, result)
        
        # Compare relationships
        self._compare_relationships(actual_sm, expected_sm, view_name, result)
        
        # Compare facts/metrics
        self._compare_facts(actual_sm, expected_sm, view_name, result)
        
        # If there are differences, flag as manual edit or divergence
        if result.drift_events:
            # Check if it's a complete divergence (many differences) vs minor edits
            if len(result.drift_events) > 5:
                result.drift_events.append(DriftEvent(
                    event_type=DriftEventType.MANUAL_EDIT_DETECTED,
                    drift_type=DriftType.SEMANTIC_VIEW_DRIFT,
                    element_name=view_name,
                    message=f"Significant divergence detected: {len(result.drift_events)} differences found",
                    details={
                        "view_name": view_name,
                        "total_differences": len(result.drift_events)
                    }
                ))
    
    def _compare_logical_tables(self, actual_sm: Dict, expected_sm: Dict, view_name: str, result: DriftDetectionResult):
        """Compare logical tables between actual and expected YAML."""
        actual_tables = {t["name"]: t for t in actual_sm.get("logical_tables", [])}
        expected_tables = {t["name"]: t for t in expected_sm.get("logical_tables", [])}
        
        # Find missing tables
        for name, table in expected_tables.items():
            if name not in actual_tables:
                result.drift_events.append(DriftEvent(
                    event_type=DriftEventType.YAML_DIVERGENCE,
                    drift_type=DriftType.SEMANTIC_VIEW_DRIFT,
                    element_name=view_name,
                    message=f"Logical table '{name}' missing in deployed view",
                    details={"table_name": name, "view_name": view_name}
                ))
        
        # Find added tables
        for name, table in actual_tables.items():
            if name not in expected_tables:
                result.drift_events.append(DriftEvent(
                    event_type=DriftEventType.MANUAL_EDIT_DETECTED,
                    drift_type=DriftType.SEMANTIC_VIEW_DRIFT,
                    element_name=view_name,
                    message=f"Logical table '{name}' added in deployed view (not in ODL)",
                    details={"table_name": name, "view_name": view_name}
                ))
    
    def _compare_relationships(self, actual_sm: Dict, expected_sm: Dict, view_name: str, result: DriftDetectionResult):
        """Compare relationships between actual and expected YAML."""
        actual_rels = {r["name"]: r for r in actual_sm.get("relationships", [])}
        expected_rels = {r["name"]: r for r in expected_sm.get("relationships", [])}
        
        # Find missing relationships
        for name, rel in expected_rels.items():
            if name not in actual_rels:
                result.drift_events.append(DriftEvent(
                    event_type=DriftEventType.YAML_DIVERGENCE,
                    drift_type=DriftType.SEMANTIC_VIEW_DRIFT,
                    element_name=view_name,
                    message=f"Relationship '{name}' missing in deployed view",
                    details={"relationship_name": name, "view_name": view_name}
                ))
            else:
                # Compare join keys
                actual_keys = set(tuple(k.items()) if isinstance(k, dict) else k for k in actual_rels[name].get("join_keys", []))
                expected_keys = set(tuple(k.items()) if isinstance(k, dict) else k for k in expected_rels[name].get("join_keys", []))
                
                if actual_keys != expected_keys:
                    result.drift_events.append(DriftEvent(
                        event_type=DriftEventType.YAML_DIVERGENCE,
                        drift_type=DriftType.SEMANTIC_VIEW_DRIFT,
                        element_name=view_name,
                        message=f"Relationship '{name}' join keys differ in deployed view",
                        details={
                            "relationship_name": name,
                            "view_name": view_name,
                            "actual_keys": list(actual_keys),
                            "expected_keys": list(expected_keys)
                        }
                    ))
    
    def _compare_facts(self, actual_sm: Dict, expected_sm: Dict, view_name: str, result: DriftDetectionResult):
        """Compare facts/metrics between actual and expected YAML."""
        actual_facts = {f["name"]: f for f in actual_sm.get("facts", [])}
        expected_facts = {f["name"]: f for f in expected_sm.get("facts", [])}
        
        # Find missing facts
        for name, fact in expected_facts.items():
            if name not in actual_facts:
                result.drift_events.append(DriftEvent(
                    event_type=DriftEventType.YAML_DIVERGENCE,
                    drift_type=DriftType.SEMANTIC_VIEW_DRIFT,
                    element_name=view_name,
                    message=f"Fact '{name}' missing in deployed view",
                    details={"fact_name": name, "view_name": view_name}
                ))
            else:
                # Compare expressions
                if actual_facts[name].get("expression") != fact.get("expression"):
                    result.drift_events.append(DriftEvent(
                        event_type=DriftEventType.MANUAL_EDIT_DETECTED,
                        drift_type=DriftType.SEMANTIC_VIEW_DRIFT,
                        element_name=view_name,
                        message=f"Fact '{name}' expression differs in deployed view",
                        details={
                            "fact_name": name,
                            "view_name": view_name,
                            "actual_expression": actual_facts[name].get("expression"),
                            "expected_expression": fact.get("expression")
                        }
                    ))
