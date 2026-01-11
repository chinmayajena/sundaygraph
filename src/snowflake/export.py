"""Snowflake export utility - extract YAML from existing semantic views."""

from typing import Optional
from pathlib import Path


def generate_export_sql(semantic_view_fqname: str) -> str:
    """
    Generate SQL to export YAML from an existing Snowflake semantic view.
    
    Args:
        semantic_view_fqname: Fully qualified semantic view name (database.schema.view_name)
        
    Returns:
        SQL query string
    """
    sql = f"""-- Export Semantic View YAML
-- This query extracts the YAML definition from an existing semantic view
-- Run this query in Snowflake to get the YAML definition

SELECT SYSTEM$READ_YAML_FROM_SEMANTIC_VIEW('{semantic_view_fqname}') AS semantic_model_yaml;

-- Alternative: Save directly to a file (if using SnowSQL)
-- COPY INTO @~/semantic_model.yaml FROM (
--   SELECT SYSTEM$READ_YAML_FROM_SEMANTIC_VIEW('{semantic_view_fqname}')
-- ) FILE_FORMAT = (TYPE = CSV FIELD_DELIMITER = NONE RECORD_DELIMITER = NONE);
"""
    return sql


def create_placeholder_yaml(output_path: Path, semantic_view_fqname: str) -> None:
    """
    Create a placeholder YAML file with instructions.
    
    Args:
        output_path: Path to write the YAML file
        semantic_view_fqname: Fully qualified semantic view name
    """
    placeholder = f"""# Semantic Model YAML
# Exported from: {semantic_view_fqname}
#
# INSTRUCTIONS:
# 1. Run the generated SQL query in Snowflake (using SnowSQL or Python connector)
# 2. Copy the YAML content from the query result
# 3. Replace this placeholder with the actual YAML content
#
# Example using SnowSQL:
#   snowsql -c <connection> -f export_semantic_view.sql -o output_file=yaml_output.txt
#   # Then extract YAML from yaml_output.txt and replace this file
#
# Example using Python connector:
#   import snowflake.connector
#   conn = snowflake.connector.connect(...)
#   cursor = conn.cursor()
#   cursor.execute("SELECT SYSTEM$READ_YAML_FROM_SEMANTIC_VIEW('{semantic_view_fqname}')")
#   yaml_content = cursor.fetchone()[0]
#   with open('{output_path.name}', 'w') as f:
#       f.write(yaml_content)
#
# The YAML content should start below this line:
---
# PLACEHOLDER: Replace this section with actual YAML from Snowflake query result
semantic_model:
  name: placeholder
  version: "1.0.0"
  description: "Replace with actual YAML from Snowflake"
"""
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(placeholder, encoding='utf-8')


def export_semantic_view_yaml(
    semantic_view_fqname: str,
    output_path: Path,
    sql_output_path: Optional[Path] = None
) -> tuple[Path, Path]:
    """
    Generate SQL and placeholder YAML for exporting a semantic view.
    
    Args:
        semantic_view_fqname: Fully qualified semantic view name (database.schema.view_name)
        output_path: Path to write the YAML file
        sql_output_path: Optional path to write the SQL file (default: same dir as YAML with .sql extension)
        
    Returns:
        Tuple of (sql_file_path, yaml_file_path)
    """
    # Generate SQL
    sql_content = generate_export_sql(semantic_view_fqname)
    
    # Determine SQL output path
    if sql_output_path is None:
        sql_output_path = output_path.with_suffix('.sql')
    
    # Write SQL file
    sql_output_path.parent.mkdir(parents=True, exist_ok=True)
    sql_output_path.write_text(sql_content, encoding='utf-8')
    
    # Create placeholder YAML
    create_placeholder_yaml(output_path, semantic_view_fqname)
    
    return sql_output_path, output_path
