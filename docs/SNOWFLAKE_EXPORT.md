# Snowflake Export Utility

Export YAML definitions from existing Snowflake semantic views.

## Overview

The Snowflake export utility generates SQL queries to extract YAML definitions from existing semantic views in Snowflake. This is useful for:

- Reverse engineering semantic models
- Version control and documentation
- Migrating semantic views between environments
- Auditing and compliance

## CLI Usage

### Basic Command

```bash
sundaygraph snowflake export-yaml \
    --semantic-view <database>.<schema>.<view_name> \
    --out <output_file.yaml>
```

### Example

```bash
# Export from a retail semantic view
sundaygraph snowflake export-yaml \
    --semantic-view RETAIL_DB.PUBLIC.retail_semantic_view \
    --out semantic_model.yaml
```

This command generates two files:

1. **`semantic_model.sql`** - SQL query to run in Snowflake
2. **`semantic_model.yaml`** - Placeholder YAML file with instructions

### Options

- `--semantic-view` (required): Fully qualified semantic view name
  - Format: `database.schema.view_name`
  - Example: `RETAIL_DB.PUBLIC.retail_semantic_view`

- `--out` (required): Output file path for YAML
  - The SQL file will be created in the same directory with `.sql` extension

- `--sql-out` (optional): Custom path for SQL file
  - Default: Same as `--out` but with `.sql` extension

## Generated SQL

The utility generates SQL that calls Snowflake's `SYSTEM$READ_YAML_FROM_SEMANTIC_VIEW` function:

```sql
-- Export Semantic View YAML
-- This query extracts the YAML definition from an existing semantic view
-- Run this query in Snowflake to get the YAML definition

SELECT SYSTEM$READ_YAML_FROM_SEMANTIC_VIEW('RETAIL_DB.PUBLIC.retail_semantic_view') AS semantic_model_yaml;
```

## Running the SQL

### Option 1: Using SnowSQL

**Prerequisites:**
- Install [SnowSQL](https://docs.snowflake.com/en/user-guide/snowsql-install-config.html)
- Configure connection (see [SnowSQL Configuration](https://docs.snowflake.com/en/user-guide/snowsql-config.html))

**Steps:**

1. Run the generated SQL file:
   ```bash
   snowsql -c <connection_name> -f semantic_model.sql -o output_file=yaml_output.txt
   ```

2. Extract YAML from the output file:
   ```bash
   # The YAML will be in yaml_output.txt
   # Extract the YAML content (between quotes or as-is)
   ```

3. Replace the placeholder in the generated YAML file with the actual content.

**Example SnowSQL command:**
```bash
snowsql -c my_connection -f semantic_model.sql -o output_file=result.txt -o quiet=true
```

### Option 2: Using Python Connector

**Prerequisites:**
- Install `snowflake-connector-python`:
  ```bash
  pip install snowflake-connector-python
  ```

**Python Script:**

```python
import snowflake.connector
from pathlib import Path

# Connect to Snowflake
conn = snowflake.connector.connect(
    user='<username>',
    password='<password>',
    account='<account_identifier>',
    warehouse='<warehouse>',
    database='<database>',
    schema='<schema>'
)

# Execute the export query
cursor = conn.cursor()
semantic_view_fqname = 'RETAIL_DB.PUBLIC.retail_semantic_view'
cursor.execute(
    f"SELECT SYSTEM$READ_YAML_FROM_SEMANTIC_VIEW('{semantic_view_fqname}')"
)

# Get the YAML content
result = cursor.fetchone()
yaml_content = result[0] if result else None

# Write to file
if yaml_content:
    output_path = Path('semantic_model.yaml')
    output_path.write_text(yaml_content, encoding='utf-8')
    print(f"✓ YAML exported to {output_path}")
else:
    print("✗ No YAML content returned")

# Close connection
cursor.close()
conn.close()
```

**Using Environment Variables (Recommended):**

```python
import snowflake.connector
import os
from pathlib import Path

# Get credentials from environment
conn = snowflake.connector.connect(
    user=os.getenv('SNOWFLAKE_USER'),
    password=os.getenv('SNOWFLAKE_PASSWORD'),
    account=os.getenv('SNOWFLAKE_ACCOUNT'),
    warehouse=os.getenv('SNOWFLAKE_WAREHOUSE', 'COMPUTE_WH'),
    database=os.getenv('SNOWFLAKE_DATABASE'),
    schema=os.getenv('SNOWFLAKE_SCHEMA', 'PUBLIC')
)

# Export YAML
semantic_view_fqname = os.getenv('SNOWFLAKE_SEMANTIC_VIEW', 'RETAIL_DB.PUBLIC.retail_semantic_view')
cursor = conn.cursor()
cursor.execute(f"SELECT SYSTEM$READ_YAML_FROM_SEMANTIC_VIEW('{semantic_view_fqname}')")
result = cursor.fetchone()

if result and result[0]:
    Path('semantic_model.yaml').write_text(result[0], encoding='utf-8')
    print("✓ YAML exported successfully")
else:
    print("✗ No YAML content returned")

cursor.close()
conn.close()
```

### Option 3: Using Snowflake Web UI

1. Open Snowflake Web UI
2. Navigate to Worksheets
3. Copy the SQL from `semantic_model.sql`
4. Paste and execute in the worksheet
5. Copy the YAML result from the query output
6. Replace the placeholder in `semantic_model.yaml`

## Generated YAML File

The generated YAML file is a placeholder with detailed instructions:

```yaml
# Semantic Model YAML
# Exported from: RETAIL_DB.PUBLIC.retail_semantic_view
#
# INSTRUCTIONS:
# 1. Run the generated SQL query in Snowflake (using SnowSQL or Python connector)
# 2. Copy the YAML content from the query result
# 3. Replace this placeholder with the actual YAML content
#
# ... (detailed instructions)
---
# PLACEHOLDER: Replace this section with actual YAML from Snowflake query result
semantic_model:
  name: placeholder
  version: "1.0.0"
  description: "Replace with actual YAML from Snowflake"
```

After running the SQL and extracting the YAML, replace the placeholder section with the actual content.

## Python API

You can also use the export utility programmatically:

```python
from pathlib import Path
from src.snowflake.export import export_semantic_view_yaml, generate_export_sql

# Generate SQL and placeholder YAML
sql_path, yaml_path = export_semantic_view_yaml(
    semantic_view_fqname="RETAIL_DB.PUBLIC.retail_semantic_view",
    output_path=Path("semantic_model.yaml")
)

print(f"SQL file: {sql_path}")
print(f"YAML file: {yaml_path}")

# Or just generate SQL
sql = generate_export_sql("RETAIL_DB.PUBLIC.retail_semantic_view")
print(sql)
```

## Troubleshooting

### Error: "Semantic view not found"

- Verify the semantic view name is correct
- Check that you have access to the database/schema
- Ensure the semantic view exists in Snowflake

### Error: "Permission denied"

- Verify you have `USAGE` privilege on the database and schema
- Ensure you have `SELECT` privilege on the semantic view
- Check that your role has access to system functions

### YAML content is empty

- Verify the semantic view was created successfully
- Check that the semantic view has a valid YAML definition
- Ensure you're using the correct fully qualified name

## Best Practices

1. **Version Control**: Commit both the SQL and YAML files to version control
2. **Documentation**: Add comments to the YAML file describing the semantic model
3. **Validation**: Validate the exported YAML against the ODL schema
4. **Automation**: Use Python connector in CI/CD pipelines for automated exports
5. **Security**: Store Snowflake credentials securely (environment variables, secrets manager)

## Related Documentation

- [Snowflake Semantic Views](https://docs.snowflake.com/en/user-guide/semantic-views)
- [SnowSQL Documentation](https://docs.snowflake.com/en/user-guide/snowsql.html)
- [Python Connector](https://docs.snowflake.com/en/developer-guide/python-connector/python-connector)
- [ODL Documentation](../odl/README.md)
- [SnowflakeCompiler Documentation](SNOWFLAKE_COMPILER_IMPLEMENTATION.md)
