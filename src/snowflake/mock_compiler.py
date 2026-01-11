"""Mock compiler for testing."""

from typing import Dict, Any, Optional
import json

from .compiler import Compiler, ArtifactBundle, ArtifactFile
from ..odl.ir import ODLIR


class MockCompiler(Compiler):
    """Mock compiler for testing - generates sample artifacts."""
    
    def __init__(self, target: str = "MOCK"):
        """
        Initialize mock compiler.
        
        Args:
            target: Target system name (default: "MOCK")
        """
        self._target = target
    
    def get_target(self) -> str:
        """Get target system name."""
        return self._target
    
    def compile(
        self,
        odl_ir: ODLIR,
        options: Optional[Dict[str, Any]] = None
    ) -> ArtifactBundle:
        """
        Compile ODL IR to mock artifacts.
        
        Args:
            odl_ir: Normalized ODL intermediate representation
            options: Compilation options
            
        Returns:
            ArtifactBundle with mock compiled files
        """
        options = options or {}
        version_id = options.get("version_id", "test-version-1")
        
        # Generate mock semantic model YAML
        semantic_model = self._generate_mock_semantic_model(odl_ir)
        
        # Create files
        files = [
            ArtifactFile(
                path="semantic_model.yaml",
                content=semantic_model
            ),
            ArtifactFile(
                path="deployment.sql",
                content=self._generate_mock_deployment_sql(odl_ir)
            )
        ]
        
        # Create instructions
        instructions = self._create_instructions(
            steps=[
                "Review semantic_model.yaml",
                "Execute deployment.sql in target system",
                "Verify deployment with: SELECT SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML(..., verify_only=>TRUE)",
                "Deploy with: SELECT SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML(...)"
            ],
            prerequisites=[
                "Snowflake account with appropriate permissions",
                "Target database and schema created"
            ]
        )
        
        # Create rollback
        rollback = self._create_rollback(
            steps=[
                "Drop semantic view: DROP VIEW IF EXISTS <view_name>",
                "Verify removal: SELECT * FROM INFORMATION_SCHEMA.VIEWS WHERE VIEW_NAME = '<view_name>'"
            ]
        )
        
        # Create metadata
        metadata = self._create_metadata(
            version_id=version_id,
            additional_metadata={
                "odl_version": odl_ir.version,
                "odl_name": odl_ir.name,
                "objects_count": len(odl_ir.objects),
                "relationships_count": len(odl_ir.relationships),
                "metrics_count": len(odl_ir.metrics)
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
    
    def _generate_mock_semantic_model(self, odl_ir: ODLIR) -> str:
        """Generate mock Snowflake semantic model YAML."""
        lines = [
            "# Snowflake Semantic Model",
            f"# Generated from ODL: {odl_ir.name or 'Unnamed'}",
            "",
            "semantic_model:",
            "  name: mock_semantic_model",
            "  version: 1.0.0",
            "",
            "entities:"
        ]
        
        for obj in odl_ir.objects:
            lines.append(f"  - name: {obj.name}")
            lines.append(f"    table: {obj.snowflake_table or obj.name.lower()}")
            lines.append("    properties:")
            for prop in obj.properties:
                lines.append(f"      - name: {prop.name}")
                lines.append(f"        type: {prop.type}")
        
        if odl_ir.relationships:
            lines.append("")
            lines.append("relationships:")
            for rel in odl_ir.relationships:
                lines.append(f"  - name: {rel.name}")
                lines.append(f"    from: {rel.from_object}")
                lines.append(f"    to: {rel.to_object}")
                lines.append("    join_keys:")
                for from_key, to_key in rel.join_keys:
                    lines.append(f"      - [{from_key}, {to_key}]")
        
        if odl_ir.metrics:
            lines.append("")
            lines.append("measures:")
            for metric in odl_ir.metrics:
                lines.append(f"  - name: {metric.name}")
                lines.append(f"    expression: {metric.expression}")
                lines.append(f"    grain: {metric.grain}")
        
        return "\n".join(lines)
    
    def _generate_mock_deployment_sql(self, odl_ir: ODLIR) -> str:
        """Generate mock deployment SQL."""
        lines = [
            "-- Mock Deployment SQL",
            f"-- Generated from ODL: {odl_ir.name or 'Unnamed'}",
            "",
            "-- Step 1: Verify semantic model",
            "SELECT SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML(",
            "  'mock_semantic_view',",
            "  '<semantic_model_yaml>',",
            "  verify_only => TRUE",
            ");",
            "",
            "-- Step 2: Deploy semantic view",
            "SELECT SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML(",
            "  'mock_semantic_view',",
            "  '<semantic_model_yaml>'",
            ");"
        ]
        
        return "\n".join(lines)
