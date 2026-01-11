"""Snowflake CLI commands."""

import click
import os
from pathlib import Path
from typing import Optional

from ..snowflake.export import export_semantic_view_yaml, generate_export_sql
from ..snowflake.cortex_analyst import (
    CortexAnalystClient, CortexRegressionRunner,
    load_questions_from_yaml, generate_junit_xml
)
from ..snowflake.promotion_bundle import PromotionBundleGenerator
from ..odl.core import ODLProcessor


@click.group()
def snowflake_group():
    """Snowflake semantic view operations."""
    pass


@snowflake_group.command("export-yaml")
@click.option(
    "--semantic-view",
    required=True,
    help="Fully qualified semantic view name (e.g., RETAIL_DB.PUBLIC.retail_semantic_view)"
)
@click.option(
    "--out",
    type=click.Path(path_type=Path),
    required=True,
    help="Output file path for YAML (SQL file will be created with .sql extension)"
)
@click.option(
    "--sql-out",
    type=click.Path(path_type=Path),
    help="Optional: Custom path for SQL file (default: same as --out with .sql extension)"
)
def export_yaml(semantic_view: str, out: Path, sql_out: Path):
    """
    Export YAML from an existing Snowflake semantic view.
    
    Generates SQL to extract YAML from a semantic view and creates a placeholder YAML file.
    
    Example:
        sundaygraph snowflake export-yaml \\
            --semantic-view RETAIL_DB.PUBLIC.retail_semantic_view \\
            --out semantic_model.yaml
    
    This will create:
        - semantic_model.sql (SQL query to run in Snowflake)
        - semantic_model.yaml (placeholder with instructions)
    
    See the generated YAML file for instructions on how to run the SQL and extract the actual YAML.
    """
    try:
        sql_path, yaml_path = export_semantic_view_yaml(
            semantic_view_fqname=semantic_view,
            output_path=out,
            sql_output_path=sql_out
        )
        
        click.echo(f"✓ Generated SQL file: {sql_path}")
        click.echo(f"✓ Generated placeholder YAML file: {yaml_path}")
        click.echo("")
        click.echo("Next steps:")
        click.echo(f"  1. Run the SQL in Snowflake: {sql_path}")
        click.echo(f"  2. Copy the YAML result and replace the placeholder in: {yaml_path}")
        click.echo("")
        click.echo("See the YAML file for detailed instructions on using SnowSQL or Python connector.")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@snowflake_group.command("cortex-regress")
@click.option(
    "--semantic-view",
    required=True,
    help="Fully qualified semantic view name (e.g., RETAIL_DB.PUBLIC.retail_semantic_view)"
)
@click.option(
    "--questions",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to golden_questions.yaml file"
)
@click.option(
    "--account-url",
    help="Snowflake account URL (e.g., https://abc12345.snowflakecomputing.com)"
)
@click.option(
    "--api-key",
    help="Snowflake API key for authentication"
)
@click.option(
    "--session-token",
    help="Snowflake session token for authentication"
)
@click.option(
    "--junit-xml",
    type=click.Path(path_type=Path),
    help="Path to write JUnit XML report (default: junit.xml)"
)
@click.option(
    "--store-results",
    is_flag=True,
    help="Store results in database"
)
def cortex_regress(
    semantic_view: str,
    questions: Path,
    account_url: Optional[str],
    api_key: Optional[str],
    session_token: Optional[str],
    junit_xml: Optional[Path],
    store_results: bool
):
    """
    Run Cortex Analyst regression tests.
    
    Example:
        sundaygraph snowflake cortex-regress \\
            --semantic-view RETAIL_DB.PUBLIC.retail_semantic_view \\
            --questions golden_questions.yaml \\
            --account-url https://abc12345.snowflakecomputing.com \\
            --api-key <key> \\
            --junit-xml test-results.xml
    """
    try:
        # Parse semantic view FQN
        parts = semantic_view.split(".")
        if len(parts) != 3:
            raise click.BadParameter("Semantic view must be in format: database.schema.view_name")
        
        database, schema, view_name = parts
        
        # Get account URL from environment if not provided
        if not account_url:
            account_url = os.getenv("SNOWFLAKE_ACCOUNT_URL")
            if not account_url:
                raise click.BadParameter("--account-url required or set SNOWFLAKE_ACCOUNT_URL environment variable")
        
        # Get API key or session token from environment if not provided
        if not api_key and not session_token:
            api_key = os.getenv("SNOWFLAKE_API_KEY")
            session_token = os.getenv("SNOWFLAKE_SESSION_TOKEN")
            if not api_key and not session_token:
                raise click.BadParameter("--api-key or --session-token required, or set SNOWFLAKE_API_KEY/SESSION_TOKEN")
        
        # Load questions
        click.echo(f"Loading questions from: {questions}")
        question_expectations = load_questions_from_yaml(str(questions))
        click.echo(f"Loaded {len(question_expectations)} question(s)")
        
        # Create client
        client = CortexAnalystClient(
            account_url=account_url,
            database=database,
            schema=schema,
            semantic_view_name=view_name,
            api_key=api_key,
            session_token=session_token
        )
        
        # Run regression tests
        click.echo(f"Running regression tests against: {semantic_view}")
        runner = CortexRegressionRunner(client, question_expectations)
        result = runner.run()
        
        # Display results
        click.echo("")
        click.echo("=" * 60)
        click.echo("Regression Test Results")
        click.echo("=" * 60)
        click.echo(f"Total questions: {result.total_questions}")
        click.echo(f"Passed: {result.passed}")
        click.echo(f"Failed: {result.failed}")
        click.echo(f"Total latency: {result.total_latency_ms:.2f}ms")
        click.echo(f"Overall: {'PASS' if result.overall_pass else 'FAIL'}")
        click.echo("")
        
        # Show failed tests
        if result.failed > 0:
            click.echo("Failed tests:")
            for i, qr in enumerate(result.question_results, 1):
                if not qr.passed:
                    click.echo(f"  {i}. {qr.question}")
                    if qr.failure_reason:
                        click.echo(f"     Reason: {qr.failure_reason}")
            click.echo("")
        
        # Generate JUnit XML
        junit_path = junit_xml or Path("junit.xml")
        generate_junit_xml(result, str(junit_path))
        click.echo(f"✓ Generated JUnit XML: {junit_path}")
        
        # Store results in database if requested
        if store_results:
            try:
                from ..storage.odl_store import ODLStore
                from ..api.app import get_odl_store
                
                odl_store = get_odl_store()
                if odl_store:
                    run_id = odl_store.create_cortex_regression_run(
                        ontology_version_id=None,  # Could be passed as option
                        semantic_view_fqname=semantic_view,
                        questions_file_path=str(questions),
                        total_questions=result.total_questions,
                        passed=result.passed,
                        failed=result.failed,
                        overall_pass=result.overall_pass,
                        total_latency_ms=result.total_latency_ms,
                        results_json=result.to_dict(),
                        junit_xml_path=str(junit_path),
                        created_by="cli"
                    )
                    click.echo(f"✓ Stored results in database (run_id: {run_id})")
                else:
                    click.echo("⚠ Database not available, skipping storage")
            except Exception as e:
                click.echo(f"⚠ Failed to store results: {e}", err=True)
        
        # Exit with non-zero on failures
        if not result.overall_pass:
            click.echo("", err=True)
            click.echo("Regression tests FAILED", err=True)
            raise click.Abort(code=1)
        
        click.echo("")
        click.echo("✓ All regression tests passed")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort(code=1)


@snowflake_group.command("promotion-bundle")
@click.option(
    "--odl-file",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to ODL JSON file"
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    required=True,
    help="Output path for ZIP bundle (e.g., promotion-bundle.zip)"
)
@click.option(
    "--env",
    "environments",
    multiple=True,
    help="Environment configuration in format: name:database:schema:view_name (can specify multiple)"
)
@click.option(
    "--env-config",
    type=click.Path(exists=True, path_type=Path),
    help="Path to JSON file with environment configurations"
)
@click.option(
    "--version-id",
    help="Version identifier for the bundle"
)
def promotion_bundle(
    odl_file: Path,
    output: Path,
    environments: tuple,
    env_config: Optional[Path],
    version_id: Optional[str]
):
    """
    Generate promotion bundle for multi-environment Snowflake deployment.
    
    Creates a ZIP bundle with per-environment folders containing:
    - verify.sql
    - deploy.sql
    - rollback.sql
    - rollback_semantic_model.yaml (if previous view exists)
    
    Example:
        sundaygraph snowflake promotion-bundle \\
            --odl-file odl/examples/snowflake_retail.odl.json \\
            --output promotion-bundle.zip \\
            --env dev:DEV_DB:PUBLIC:dev_semantic_view \\
            --env prod:PROD_DB:PUBLIC:prod_semantic_view
    
    Or use a config file:
        sundaygraph snowflake promotion-bundle \\
            --odl-file odl/examples/snowflake_retail.odl.json \\
            --output promotion-bundle.zip \\
            --env-config environments.json
    """
    try:
        # Load environment configurations
        env_configs = {}
        
        if env_config:
            # Load from JSON file
            with open(env_config, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                env_configs = config_data.get("environments", {})
        elif environments:
            # Parse from command line arguments
            for env_str in environments:
                parts = env_str.split(":")
                if len(parts) != 4:
                    raise click.BadParameter(
                        f"Environment format must be 'name:database:schema:view_name', got: {env_str}"
                    )
                env_name, database, schema, view_name = parts
                env_configs[env_name] = {
                    "database": database,
                    "schema": schema,
                    "view_name": view_name
                }
        else:
            raise click.BadParameter(
                "Either --env or --env-config must be provided"
            )
        
        if not env_configs:
            raise click.BadParameter("No environments configured")
        
        click.echo(f"Loading ODL from: {odl_file}")
        
        # Load and process ODL
        processor = ODLProcessor()
        odl_ir, is_valid, errors = processor.process(str(odl_file))
        
        if not is_valid:
            click.echo("ODL validation failed:", err=True)
            for error in errors:
                click.echo(f"  - {error}", err=True)
            raise click.Abort(code=1)
        
        click.echo(f"✓ ODL loaded: {odl_ir.name} (v{odl_ir.version})")
        click.echo(f"Environments: {', '.join(env_configs.keys())}")
        
        # Generate promotion bundle
        click.echo("Generating promotion bundle...")
        generator = PromotionBundleGenerator()
        
        options = {}
        if version_id:
            options["version_id"] = version_id
        
        bundle = generator.generate_promotion_bundle(
            odl_ir=odl_ir,
            environments=env_configs,
            options=options
        )
        
        # Create ZIP bundle
        zip_path = generator.create_zip_bundle(bundle, output)
        
        click.echo(f"✓ Promotion bundle created: {zip_path}")
        click.echo("")
        click.echo("Bundle contents:")
        
        # List bundle contents
        for file in sorted(bundle.files, key=lambda f: f.path):
            click.echo(f"  - {file.path}")
        
        click.echo("")
        click.echo("Next steps:")
        click.echo(f"  1. Extract the bundle: unzip {output.name}")
        click.echo("  2. Review instructions.md for deployment steps")
        click.echo("  3. Deploy to dev first: run dev/verify.sql, then dev/deploy.sql")
        click.echo("  4. After dev validation, promote to prod")
        click.echo("  5. See rollback.md for rollback procedures")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        import traceback
        traceback.print_exc()
        raise click.Abort(code=1)
