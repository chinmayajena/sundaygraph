# Examples

This directory contains example files and configurations for SemanticOps for Snowflake.

## Files

### `environments.json`

Configuration file for multi-environment deployment. Defines Snowflake environments (dev, staging, prod) with their database, schema, and view name mappings.

**Usage:**
```bash
sundaygraph snowflake promotion-bundle \
  --odl-file my_domain.odl.json \
  --environments examples/environments.json \
  --out promotion-bundle.zip
```

**Structure:**
```json
{
  "environments": {
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
}
```

### `golden_questions.yaml`

Golden questions for Cortex Analyst regression testing. Defines natural language questions and expected outcomes (tables, SQL patterns, answer snippets) for validating semantic views.

**Usage:**
```bash
sundaygraph snowflake cortex-regress \
  --semantic-view MY_DB.MY_SCHEMA.my_semantic_view \
  --questions examples/golden_questions.yaml
```

**Structure:**
```yaml
questions:
  - question: "What is the total revenue?"
    expected_tables:
      - "OrderItem"
      - "Order"
    expected_sql_patterns:
      - "SUM"
      - "OrderItem"
    expected_answer_snippet: "total revenue"
```

## ODL Examples

For ODL (Ontology Definition Language) examples, see:
- **[odl/examples/snowflake_retail.odl.json](../odl/examples/snowflake_retail.odl.json)** - Complete retail e-commerce semantic model example

## Creating Your Own Examples

### Environment Configuration

1. Copy `environments.json` to your project
2. Update database, schema, and view names for your environments
3. Add additional environments as needed (staging, qa, etc.)

### Golden Questions

1. Copy `golden_questions.yaml` to your project
2. Add questions relevant to your semantic model
3. Define expected tables, SQL patterns, and answer snippets
4. Use for regression testing after deployments

### ODL Files

1. See [odl/README.md](../odl/README.md) for ODL specification
2. Use [odl/examples/snowflake_retail.odl.json](../odl/examples/snowflake_retail.odl.json) as a template
3. Define your domain objects, relationships, metrics, and dimensions
4. Add Snowflake mapping block with table mappings

## Best Practices

1. **Version Control**: Keep example files in version control
2. **Documentation**: Document any custom configurations
3. **Testing**: Use examples in your CI/CD pipeline
4. **Updates**: Keep examples synchronized with code changes
