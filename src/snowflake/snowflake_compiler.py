"""Snowflake compiler v0 - generates semantic model YAML and SQL."""

from typing import Dict, Any, Optional
import yaml
import json

from .compiler import Compiler, ArtifactBundle, ArtifactFile
from ..odl.ir import ODLIR


class SnowflakeCompiler(Compiler):
    """Snowflake compiler v0 - generates semantic model YAML and deployment SQL."""
    
    def get_target(self) -> str:
        """Get target system name."""
        return "SNOWFLAKE"
    
    def compile(
        self,
        odl_ir: ODLIR,
        options: Optional[Dict[str, Any]] = None
    ) -> ArtifactBundle:
        """
        Compile ODL IR to Snowflake semantic model artifacts.
        
        Args:
            odl_ir: Normalized ODL intermediate representation
            options: Compilation options (view_name, database, schema, etc.)
            
        Returns:
            ArtifactBundle with semantic_model.yaml, verify.sql, deploy.sql
        """
        options = options or {}
        version_id = options.get("version_id", "unknown")
        view_name = options.get("view_name", "semantic_view")
        database = options.get("database") or (odl_ir.snowflake.database if odl_ir.snowflake else "DATABASE")
        schema = options.get("schema") or (odl_ir.snowflake.schema if odl_ir.snowflake else "SCHEMA")
        
        # Generate semantic model YAML
        semantic_model_yaml = self._generate_semantic_model_yaml(odl_ir, options)
        
        # Generate verify.sql
        verify_sql = self._generate_verify_sql(database, schema, semantic_model_yaml)
        
        # Generate deploy.sql
        deploy_sql = self._generate_deploy_sql(database, schema, semantic_model_yaml, view_name)
        
        # Create files
        files = [
            ArtifactFile(
                path="semantic_model.yaml",
                content=semantic_model_yaml
            ),
            ArtifactFile(
                path="verify.sql",
                content=verify_sql
            ),
            ArtifactFile(
                path="deploy.sql",
                content=deploy_sql
            )
        ]
        
        # Create instructions
        instructions = self._create_instructions(
            steps=[
                f"Review semantic_model.yaml in {database}.{schema}",
                "Run verify.sql to validate the semantic model",
                "If verification passes, run deploy.sql to create the semantic view",
                f"Verify deployment: SELECT * FROM {database}.{schema}.INFORMATION_SCHEMA.VIEWS WHERE VIEW_NAME = '{view_name}'"
            ],
            prerequisites=[
                f"Snowflake account with access to {database}.{schema}",
                "Appropriate permissions to create semantic views",
                "Cortex Analyst enabled (for semantic view functionality)"
            ]
        )
        
        # Create rollback
        rollback = self._create_rollback(
            steps=[
                f"Drop semantic view: DROP VIEW IF EXISTS {database}.{schema}.{view_name}",
                f"Verify removal: SELECT * FROM {database}.{schema}.INFORMATION_SCHEMA.VIEWS WHERE VIEW_NAME = '{view_name}'"
            ]
        )
        
        # Create metadata
        metadata = self._create_metadata(
            version_id=version_id,
            additional_metadata={
                "odl_version": odl_ir.version,
                "odl_name": odl_ir.name,
                "view_name": view_name,
                "database": database,
                "schema": schema,
                "objects_count": len(odl_ir.objects),
                "relationships_count": len(odl_ir.relationships),
                "metrics_count": len(odl_ir.metrics),
                "dimensions_count": len(odl_ir.dimensions)
            }
        )
        
        # Create bundle
        bundle = ArtifactBundle(
            files=files,
            instructions_md=instructions,
            rollback_md=rollback,
            metadata=metadata
        )
        
        # Calculate and set checksum
        checksum = bundle.calculate_checksum()
        metadata["checksum"] = checksum
        
        # Update metadata.json file
        metadata_file = bundle.get_file("metadata.json")
        if metadata_file:
            metadata_file.content = json.dumps(metadata, indent=2)
        
        return bundle
    
    def _generate_semantic_model_yaml(self, odl_ir: ODLIR, options: Dict[str, Any]) -> str:
        """Generate Snowflake semantic model YAML."""
        model_name = options.get("model_name") or odl_ir.name or "semantic_model"
        
        # Build semantic model structure
        semantic_model = {
            "semantic_model": {
                "name": model_name,
                "version": odl_ir.version or "1.0.0",
                "description": odl_ir.description or f"Semantic model generated from ODL: {odl_ir.name}"
            }
        }
        
        # Logical tables (from objects)
        logical_tables = []
        for obj in odl_ir.objects:
            # Get physical table name
            physical_table = obj.snowflake_table
            if not physical_table and odl_ir.snowflake:
                physical_table = odl_ir.snowflake.table_mappings.get(obj.name, obj.name.lower())
            if not physical_table:
                physical_table = obj.name.lower()
            
            # Build logical table
            logical_table = {
                "name": obj.name,
                "description": obj.description or f"Logical table for {obj.name}",
                "physical_table": {
                    "database": odl_ir.snowflake.database if odl_ir.snowflake else "DATABASE",
                    "schema": odl_ir.snowflake.schema if odl_ir.snowflake else "SCHEMA",
                    "table": physical_table
                }
            }
            
            # Add dimensions (properties that are not identifiers)
            dimensions = []
            for prop in obj.properties:
                if prop.name not in obj.identifiers:
                    dimensions.append({
                        "name": prop.name,
                        "type": self._map_odl_type_to_snowflake(prop.type),
                        "description": prop.description or f"{prop.name} dimension"
                    })
            
            if dimensions:
                logical_table["dimensions"] = dimensions
            
            # Add primary key
            if obj.identifiers:
                logical_table["primary_key"] = obj.identifiers[0] if len(obj.identifiers) == 1 else obj.identifiers
            
            logical_tables.append(logical_table)
        
        if logical_tables:
            semantic_model["semantic_model"]["logical_tables"] = logical_tables
        
        # Relationships (join paths)
        relationships = []
        for rel in odl_ir.relationships:
            relationship = {
                "name": rel.name,
                "description": rel.description or f"Relationship from {rel.from_object} to {rel.to_object}",
                "from_table": rel.from_object,
                "to_table": rel.to_object,
                "join_type": self._map_cardinality_to_join_type(rel.cardinality)
            }
            
            # Add join keys
            join_keys = []
            for from_key, to_key in rel.join_keys:
                join_keys.append({
                    "from_column": from_key,
                    "to_column": to_key
                })
            
            if join_keys:
                relationship["join_keys"] = join_keys
            
            relationships.append(relationship)
        
        if relationships:
            semantic_model["semantic_model"]["relationships"] = relationships
        
        # Facts/Metrics
        facts = []
        for metric in odl_ir.metrics:
            fact = {
                "name": metric.name,
                "description": metric.description or f"Metric: {metric.name}",
                "expression": metric.expression,
                "grain": metric.grain,
                "aggregation_type": self._map_metric_type_to_aggregation(metric.type)
            }
            
            if metric.format:
                fact["format"] = metric.format
            
            facts.append(fact)
        
        if facts:
            semantic_model["semantic_model"]["facts"] = facts
        
        # Dimensions (from dimensions list)
        if odl_ir.dimensions:
            dimensions_list = []
            for dim in odl_ir.dimensions:
                dimension = {
                    "name": dim.name,
                    "description": dim.description or f"Dimension: {dim.name}",
                    "source_property": dim.source_property,
                    "type": dim.type
                }
                dimensions_list.append(dimension)
            
            semantic_model["semantic_model"]["dimensions"] = dimensions_list
        
        # Convert to YAML
        yaml_content = yaml.dump(semantic_model, default_flow_style=False, sort_keys=False, allow_unicode=True)
        return yaml_content
    
    def _generate_verify_sql(self, database: str, schema: str, yaml_content: str) -> str:
        """Generate verify.sql with verify_only => TRUE."""
        # Escape YAML for SQL (use $$ delimiters)
        sql = f"""-- Verify Semantic Model
-- This script validates the semantic model without creating the view
-- Run this before deploying to ensure the model is correct

CALL SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML(
  '{database}.{schema}',
  $${yaml_content}$$,
  verify_only => TRUE
);
"""
        return sql
    
    def _generate_deploy_sql(self, database: str, schema: str, yaml_content: str, view_name: str) -> str:
        """Generate deploy.sql with verify_only => FALSE."""
        sql = f"""-- Deploy Semantic View
-- This script creates the semantic view in Snowflake
-- Run verify.sql first to validate the model

CALL SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML(
  '{database}.{schema}',
  $${yaml_content}$$,
  verify_only => FALSE
);

-- Verify deployment
SELECT * FROM {database}.{schema}.INFORMATION_SCHEMA.VIEWS 
WHERE TABLE_SCHEMA = '{schema}' AND TABLE_NAME = '{view_name}';
"""
        return sql
    
    def _map_odl_type_to_snowflake(self, odl_type: str) -> str:
        """Map ODL type to Snowflake type."""
        type_mapping = {
            "string": "VARCHAR",
            "number": "NUMBER",
            "integer": "INTEGER",
            "decimal": "DECIMAL",
            "boolean": "BOOLEAN",
            "date": "DATE",
            "timestamp": "TIMESTAMP_NTZ",
            "time": "TIME"
        }
        return type_mapping.get(odl_type, "VARCHAR")
    
    def _map_cardinality_to_join_type(self, cardinality: str) -> str:
        """Map ODL cardinality to Snowflake join type."""
        mapping = {
            "one_to_one": "INNER",
            "one_to_many": "LEFT",
            "many_to_one": "LEFT",
            "many_to_many": "LEFT"
        }
        return mapping.get(cardinality, "LEFT")
    
    def _map_metric_type_to_aggregation(self, metric_type: str) -> str:
        """Map metric type to Snowflake aggregation."""
        mapping = {
            "sum": "SUM",
            "count": "COUNT",
            "average": "AVG",
            "min": "MIN",
            "max": "MAX",
            "distinct_count": "COUNT_DISTINCT",
            "custom": "CUSTOM"
        }
        return mapping.get(metric_type, "CUSTOM")
