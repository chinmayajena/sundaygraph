# Promotion Bundle for Multi-Environment Deployment

## Overview

The promotion bundle generator creates deployment artifacts for multiple Snowflake environments (dev, staging, prod) with forward and rollback paths. This enables safe dev→prod promotion workflows.

## What is a Promotion Bundle?

A promotion bundle is a ZIP file containing:

```
promotion-bundle.zip
├── semantic_model.yaml          # Shared semantic model definition
├── instructions.md              # Deployment instructions
├── rollback.md                  # Rollback procedures
├── metadata.json                # Bundle metadata
├── dev/
│   ├── verify.sql              # Verify semantic model (dev)
│   ├── deploy.sql              # Deploy semantic view (dev)
│   ├── rollback.sql            # Rollback deployment (dev)
│   └── rollback_semantic_model.yaml  # Previous view YAML (if exists)
└── prod/
    ├── verify.sql              # Verify semantic model (prod)
    ├── deploy.sql              # Deploy semantic view (prod)
    ├── rollback.sql            # Rollback deployment (prod)
    └── rollback_semantic_model.yaml  # Previous view YAML (if exists)
```

## Rollback Strategy

### Automatic Rollback Generation

If a semantic view already exists in an environment:

1. **Export current YAML**: The generator attempts to export the current semantic view YAML using `SYSTEM$READ_YAML_FROM_SEMANTIC_VIEW`
2. **Store as artifact**: The exported YAML is stored as `{env}/rollback_semantic_model.yaml`
3. **Generate rollback SQL**: `rollback.sql` is generated to:
   - Drop the new view
   - Recreate the previous view from the exported YAML

### Manual Rollback

If the view doesn't exist or export fails:

- `rollback.sql` simply drops the newly created view
- Manual rollback instructions are provided in `rollback.md`

## CLI Usage

### Basic Usage

```bash
sundaygraph snowflake promotion-bundle \
    --odl-file odl/examples/snowflake_retail.odl.json \
    --output promotion-bundle.zip \
    --env dev:DEV_DB:PUBLIC:dev_semantic_view \
    --env prod:PROD_DB:PUBLIC:prod_semantic_view
```

### Using Environment Config File

Create `environments.json`:

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

Then run:

```bash
sundaygraph snowflake promotion-bundle \
    --odl-file odl/examples/snowflake_retail.odl.json \
    --output promotion-bundle.zip \
    --env-config environments.json \
    --version-id v1.2.3
```

## Dev→Prod Promotion Workflow

### Step 1: Generate Promotion Bundle

```bash
# Generate bundle from ODL
sundaygraph snowflake promotion-bundle \
    --odl-file odl/examples/snowflake_retail.odl.json \
    --output promotion-bundle.zip \
    --env dev:DEV_DB:PUBLIC:dev_semantic_view \
    --env prod:PROD_DB:PUBLIC:prod_semantic_view
```

### Step 2: Extract and Review

```bash
unzip promotion-bundle.zip
cd promotion-bundle
cat instructions.md
```

### Step 3: Deploy to Dev

```bash
# Verify semantic model
snowsql -c dev_connection -f dev/verify.sql

# Deploy to dev
snowsql -c dev_connection -f dev/deploy.sql

# Test with Cortex Analyst
sundaygraph snowflake cortex-regress \
    --semantic-view DEV_DB.PUBLIC.dev_semantic_view \
    --questions examples/golden_questions.yaml
```

### Step 4: Promote to Prod (After Dev Validation)

```bash
# Verify semantic model in prod
snowsql -c prod_connection -f prod/verify.sql

# Deploy to prod
snowsql -c prod_connection -f prod/deploy.sql

# Verify deployment
snowsql -c prod_connection -q "SELECT * FROM PROD_DB.PUBLIC.INFORMATION_SCHEMA.VIEWS WHERE TABLE_NAME = 'prod_semantic_view'"
```

### Step 5: Rollback (If Needed)

```bash
# Rollback prod deployment
snowsql -c prod_connection -f prod/rollback.sql

# Or manually:
# 1. Drop current view
# 2. Recreate from rollback_semantic_model.yaml
```

## GitHub Actions Integration

### Generate Bundle in CI

Add to `.github/workflows/semantic-ci.yml`:

```yaml
- name: Generate promotion bundle
  run: |
    sundaygraph snowflake promotion-bundle \
      --odl-file odl/examples/snowflake_retail.odl.json \
      --output promotion-bundle.zip \
      --env dev:DEV_DB:PUBLIC:dev_semantic_view \
      --env prod:PROD_DB:PUBLIC:prod_semantic_view \
      --version-id ${{ github.sha }}

- name: Upload promotion bundle
  uses: actions/upload-artifact@v4
  with:
    name: promotion-bundle
    path: promotion-bundle.zip
```

### Download from PR Artifacts

1. Go to PR → Actions → Artifacts
2. Download `promotion-bundle.zip`
3. Extract and deploy to dev/prod

## Rollback Scenarios

### Scenario 1: View Exists (Automatic Rollback)

If a semantic view already exists:

1. **Before deployment**: Export current YAML → stored in `rollback_semantic_model.yaml`
2. **Deploy new version**: Run `deploy.sql`
3. **If rollback needed**: Run `rollback.sql` → restores previous view

### Scenario 2: New View (Simple Rollback)

If no view exists:

1. **Deploy**: Run `deploy.sql` → creates new view
2. **If rollback needed**: Run `rollback.sql` → drops the view

### Scenario 3: Manual Rollback

If automatic export fails:

1. **Before deployment**: Manually export current YAML:
   ```sql
   SELECT SYSTEM$READ_YAML_FROM_SEMANTIC_VIEW('DB.SCHEMA.view_name');
   ```
2. **Store YAML**: Save to `rollback_semantic_model.yaml`
3. **Deploy**: Run `deploy.sql`
4. **Rollback**: Manually recreate from stored YAML

## Best Practices

1. **Always verify before deploying**:
   ```bash
   snowsql -c connection -f {env}/verify.sql
   ```

2. **Test in dev first**:
   - Deploy to dev
   - Run Cortex regression tests
   - Validate with business users

3. **Export before prod deployment**:
   - If view exists, ensure rollback YAML is captured
   - Store rollback artifacts securely

4. **Use version IDs**:
   ```bash
   --version-id v1.2.3
   ```
   - Track bundle versions
   - Link to git commits/tags

5. **Review rollback procedures**:
   - Read `rollback.md` before deploying
   - Understand rollback steps
   - Test rollback in dev first

## Bundle Contents

### verify.sql

Validates semantic model without creating view:

```sql
CALL SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML(
  'DATABASE.SCHEMA',
  $$<yaml>$$,
  verify_only => TRUE
);
```

### deploy.sql

Creates semantic view:

```sql
CALL SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML(
  'DATABASE.SCHEMA',
  $$<yaml>$$,
  verify_only => FALSE
);
```

### rollback.sql

Rolls back deployment:

- **If previous view exists**: Drops new view, recreates previous view
- **If new view**: Simply drops the view

### rollback_semantic_model.yaml

Exported YAML from previous semantic view (if exists). Used by `rollback.sql` to restore previous state.

## Troubleshooting

### "Rollback YAML not available"

- View doesn't exist (first deployment)
- Provider can't access Snowflake
- Export failed

**Solution**: Manual rollback (see `rollback.md`)

### "Environment config invalid"

- Check format: `name:database:schema:view_name`
- Or use JSON config file

### "ODL validation failed"

- Fix ODL file errors
- Re-run validation: `python odl/validate_odl.py <file>`

## Example: Complete Workflow

```bash
# 1. Generate bundle
sundaygraph snowflake promotion-bundle \
    --odl-file odl/examples/snowflake_retail.odl.json \
    --output promotion-bundle.zip \
    --env dev:DEV_DB:PUBLIC:dev_semantic_view \
    --env prod:PROD_DB:PUBLIC:prod_semantic_view \
    --version-id v1.0.0

# 2. Extract
unzip promotion-bundle.zip -d deployment/

# 3. Deploy to dev
cd deployment/
snowsql -c dev -f dev/verify.sql
snowsql -c dev -f dev/deploy.sql

# 4. Test in dev
sundaygraph snowflake cortex-regress \
    --semantic-view DEV_DB.PUBLIC.dev_semantic_view \
    --questions examples/golden_questions.yaml

# 5. Promote to prod (after dev validation)
snowsql -c prod -f prod/verify.sql
snowsql -c prod -f prod/deploy.sql

# 6. Verify prod
snowsql -c prod -q "SELECT COUNT(*) FROM PROD_DB.PUBLIC.prod_semantic_view"
```

## Next Steps

- Add environment-specific configurations (warehouse, role)
- Support for staging environment
- Automated rollback triggers
- Integration with deployment pipelines (Terraform, etc.)
