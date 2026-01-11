"""Promotion bundle generator for multi-environment Snowflake deployments."""

from typing import Dict, Any, List, Optional
from pathlib import Path
import zipfile
import io
import json
from datetime import datetime

from .compiler import ArtifactBundle, ArtifactFile
from .snowflake_compiler import SnowflakeCompiler
from .export import generate_export_sql
from ..odl.ir import ODLIR
from .provider import SnowflakeProvider


class PromotionBundleGenerator:
    """Generates promotion bundles for multi-environment deployments."""
    
    def __init__(
        self,
        compiler: Optional[SnowflakeCompiler] = None,
        provider: Optional[SnowflakeProvider] = None
    ):
        """
        Initialize promotion bundle generator.
        
        Args:
            compiler: Snowflake compiler instance (default: creates new)
            provider: Snowflake provider for checking existing views (optional)
        """
        self.compiler = compiler or SnowflakeCompiler()
        self.provider = provider
    
    def generate_promotion_bundle(
        self,
        odl_ir: ODLIR,
        environments: Dict[str, Dict[str, Any]],
        options: Optional[Dict[str, Any]] = None
    ) -> ArtifactBundle:
        """
        Generate promotion bundle with per-environment artifacts.
        
        Args:
            odl_ir: Normalized ODL intermediate representation
            environments: Environment configurations
                Example: {
                    "dev": {
                        "database": "DEV_DB",
                        "schema": "PUBLIC",
                        "view_name": "dev_semantic_view"
                    },
                    "prod": {
                        "database": "PROD_DB",
                        "schema": "PUBLIC",
                        "view_name": "prod_semantic_view"
                    }
                }
            options: Additional compilation options
            
        Returns:
            ArtifactBundle with per-environment folders
        """
        options = options or {}
        version_id = options.get("version_id", "unknown")
        
        # Generate base semantic model YAML
        semantic_model_yaml = self.compiler._generate_semantic_model_yaml(odl_ir, options)
        
        files: List[ArtifactFile] = []
        
        # Generate artifacts for each environment
        for env_name, env_config in environments.items():
            database = env_config.get("database", "DATABASE")
            schema = env_config.get("schema", "SCHEMA")
            view_name = env_config.get("view_name", f"{env_name}_semantic_view")
            semantic_view_fqname = f"{database}.{schema}.{view_name}"
            
            # Generate verify.sql
            verify_sql = self.compiler._generate_verify_sql(database, schema, semantic_model_yaml)
            files.append(ArtifactFile(
                path=f"{env_name}/verify.sql",
                content=verify_sql
            ))
            
            # Generate deploy.sql
            deploy_sql = self.compiler._generate_deploy_sql(database, schema, semantic_model_yaml, view_name)
            files.append(ArtifactFile(
                path=f"{env_name}/deploy.sql",
                content=deploy_sql
            ))
            
            # Generate rollback.sql
            rollback_sql, rollback_yaml = self._generate_rollback_sql(
                semantic_view_fqname=semantic_view_fqname,
                database=database,
                schema=schema,
                view_name=view_name,
                new_yaml=semantic_model_yaml
            )
            files.append(ArtifactFile(
                path=f"{env_name}/rollback.sql",
                content=rollback_sql
            ))
            
            # Store rollback YAML if available
            if rollback_yaml:
                files.append(ArtifactFile(
                    path=f"{env_name}/rollback_semantic_model.yaml",
                    content=rollback_yaml
                ))
        
        # Add shared semantic model YAML
        files.append(ArtifactFile(
            path="semantic_model.yaml",
            content=semantic_model_yaml
        ))
        
        # Create promotion instructions
        instructions = self._create_promotion_instructions(environments)
        
        # Create rollback instructions
        rollback_instructions = self._create_promotion_rollback_instructions(environments)
        
        # Create metadata
        metadata = self.compiler._create_metadata(
            version_id=version_id,
            additional_metadata={
                "odl_version": odl_ir.version,
                "odl_name": odl_ir.name,
                "promotion_bundle": True,
                "environments": list(environments.keys()),
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
            rollback_md=rollback_instructions,
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
    
    def _generate_rollback_sql(
        self,
        semantic_view_fqname: str,
        database: str,
        schema: str,
        view_name: str,
        new_yaml: str
    ) -> Tuple[str, Optional[str]]:
        """
        Generate rollback SQL and export current YAML if view exists.
        
        Args:
            semantic_view_fqname: Fully qualified semantic view name
            database: Database name
            schema: Schema name
            view_name: View name
            new_yaml: New semantic model YAML (for comparison)
            
        Returns:
            Tuple of (rollback_sql, rollback_yaml)
        """
        rollback_yaml = None
        
        # Try to get current YAML if provider is available
        if self.provider:
            try:
                current_yaml = self.provider.get_semantic_view_yaml(semantic_view_fqname)
                if current_yaml and current_yaml.yaml_content:
                    rollback_yaml = current_yaml.yaml_content
            except Exception:
                # View doesn't exist or provider can't access it
                pass
        
        # Generate rollback SQL
        if rollback_yaml:
            # View exists - create rollback that restores it
            rollback_sql = f"""-- Rollback Semantic View
-- This script restores the previous semantic view from exported YAML
-- The previous view definition is stored in rollback_semantic_model.yaml

-- Step 1: Drop the current view
DROP VIEW IF EXISTS {database}.{schema}.{view_name};

-- Step 2: Recreate the previous view from exported YAML
CALL SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML(
  '{database}.{schema}',
  $$ROLLBACK_YAML_PLACEHOLDER$$,
  verify_only => FALSE
);

-- Note: Replace ROLLBACK_YAML_PLACEHOLDER with the content from rollback_semantic_model.yaml
-- Or use the export SQL to get the current YAML before deploying the new version
"""
            # Replace placeholder with actual YAML (escaped)
            rollback_sql = rollback_sql.replace(
                "$$ROLLBACK_YAML_PLACEHOLDER$$",
                f"$${rollback_yaml}$$"
            )
        else:
            # View doesn't exist - rollback is just dropping the new view
            rollback_sql = f"""-- Rollback Semantic View
-- This script removes the semantic view if deployment needs to be rolled back
-- Since no previous view exists, this simply drops the newly created view

DROP VIEW IF EXISTS {database}.{schema}.{view_name};

-- Verify removal
SELECT * FROM {database}.{schema}.INFORMATION_SCHEMA.VIEWS 
WHERE TABLE_SCHEMA = '{schema}' AND TABLE_NAME = '{view_name}';
"""
        
        return rollback_sql, rollback_yaml
    
    def _create_promotion_instructions(self, environments: Dict[str, Dict[str, Any]]) -> str:
        """Create promotion instructions for multi-environment deployment."""
        lines = [
            "# Promotion Bundle Deployment Instructions",
            "",
            "This bundle contains deployment artifacts for multiple environments.",
            "",
            "## Environments"
            ""
        ]
        
        for env_name, env_config in environments.items():
            database = env_config.get("database", "DATABASE")
            schema = env_config.get("schema", "SCHEMA")
            view_name = env_config.get("view_name", f"{env_name}_semantic_view")
            
            lines.append(f"### {env_name.upper()}")
            lines.append("")
            lines.append(f"- **Database**: `{database}`")
            lines.append(f"- **Schema**: `{schema}`")
            lines.append(f"- **View Name**: `{view_name}`")
            lines.append("")
            lines.append(f"**Deployment Steps:**")
            lines.append("")
            lines.append(f"1. Review `{env_name}/verify.sql`")
            lines.append(f"2. Run `{env_name}/verify.sql` to validate the semantic model")
            lines.append(f"3. If verification passes, run `{env_name}/deploy.sql` to create the semantic view")
            lines.append(f"4. Verify deployment:")
            lines.append(f"   ```sql")
            lines.append(f"   SELECT * FROM {database}.{schema}.INFORMATION_SCHEMA.VIEWS")
            lines.append(f"   WHERE TABLE_SCHEMA = '{schema}' AND TABLE_NAME = '{view_name}';")
            lines.append(f"   ```")
            lines.append("")
        
        lines.append("## Promotion Workflow")
        lines.append("")
        lines.append("### Dev → Prod Promotion")
        lines.append("")
        lines.append("1. **Deploy to Dev**:")
        lines.append("   - Run `dev/verify.sql`")
        lines.append("   - Run `dev/deploy.sql`")
        lines.append("   - Test with Cortex Analyst")
        lines.append("")
        lines.append("2. **Promote to Prod** (after Dev validation):")
        lines.append("   - Review `prod/verify.sql`")
        lines.append("   - Run `prod/verify.sql`")
        lines.append("   - Run `prod/deploy.sql`")
        lines.append("   - Verify production deployment")
        lines.append("")
        lines.append("3. **Rollback** (if needed):")
        lines.append("   - Run `{env}/rollback.sql` for the environment")
        lines.append("   - See `rollback.md` for detailed rollback instructions")
        lines.append("")
        
        return "\n".join(lines)
    
    def _create_promotion_rollback_instructions(self, environments: Dict[str, Dict[str, Any]]) -> str:
        """Create rollback instructions for promotion bundle."""
        lines = [
            "# Rollback Instructions",
            "",
            "This document describes how to rollback deployments for each environment.",
            ""
        ]
        
        for env_name, env_config in environments.items():
            database = env_config.get("database", "DATABASE")
            schema = env_config.get("schema", "SCHEMA")
            view_name = env_config.get("view_name", f"{env_name}_semantic_view")
            
            lines.append(f"## {env_name.upper()} Environment Rollback")
            lines.append("")
            
            # Check if rollback YAML exists
            lines.append(f"### Option 1: Use Pre-generated Rollback SQL")
            lines.append("")
            lines.append(f"If `{env_name}/rollback_semantic_model.yaml` exists:")
            lines.append("")
            lines.append(f"1. Run `{env_name}/rollback.sql`")
            lines.append(f"   - This will drop the current view and restore the previous version")
            lines.append("")
            
            lines.append(f"### Option 2: Manual Rollback")
            lines.append("")
            lines.append(f"If rollback YAML is not available:")
            lines.append("")
            lines.append(f"1. **Export current view** (before deploying new version):")
            lines.append(f"   ```sql")
            export_sql = generate_export_sql(f"{database}.{schema}.{view_name}")
            # Extract just the SELECT statement
            export_line = [l for l in export_sql.split('\n') if 'SELECT SYSTEM$READ_YAML' in l][0]
            lines.append(f"   {export_line.strip()}")
            lines.append(f"   ```")
            lines.append("")
            lines.append(f"2. **Store the exported YAML** for rollback")
            lines.append("")
            lines.append(f"3. **Drop the current view**:")
            lines.append(f"   ```sql")
            lines.append(f"   DROP VIEW IF EXISTS {database}.{schema}.{view_name};")
            lines.append(f"   ```")
            lines.append("")
            lines.append(f"4. **Recreate previous view** (if needed):")
            lines.append(f"   ```sql")
            lines.append(f"   CALL SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML(")
            lines.append(f"     '{database}.{schema}',")
            lines.append(f"     $$<previous_yaml>$$,")
            lines.append(f"     verify_only => FALSE")
            lines.append(f"   );")
            lines.append(f"   ```")
            lines.append("")
        
        return "\n".join(lines)
    
    def create_zip_bundle(
        self,
        bundle: ArtifactBundle,
        output_path: Path
    ) -> Path:
        """
        Create a ZIP file from the artifact bundle.
        
        Args:
            bundle: Artifact bundle
            output_path: Path to write ZIP file
            
        Returns:
            Path to created ZIP file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in bundle.files:
                zipf.writestr(file.path, file.content)
        
        return output_path
