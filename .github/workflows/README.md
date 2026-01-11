# GitHub Actions Workflows

## Semantic CI Workflow

The `semantic-ci.yml` workflow runs on pull requests and performs comprehensive validation and testing of ODL files and Snowflake semantic models.

### Triggers

- **Pull requests** to `main` or `master` branches
- **Paths**: Triggers on changes to:
  - `odl/**/*.json`, `odl/**/*.yaml`, `odl/**/*.yml`
  - `src/odl/**`
  - `src/snowflake/**`
  - `.github/workflows/semantic-ci.yml`

### Steps

1. **Validate ODL**: Validates all ODL files using the ODL processor
2. **Diff against main**: Computes diff between PR and main branch (if ODL changed)
3. **Compile Snowflake**: Generates Snowflake artifact bundle (YAML, verify.sql, deploy.sql)
4. **Eval gates**: Runs evaluation gates (structural, semantic, deployability)
5. **Verify-only** (optional): Validates that verify.sql can be generated (requires Snowflake creds)
6. **Cortex regression** (optional): Runs Cortex Analyst regression tests (requires Snowflake creds)

### Required Secrets

For full CI execution (including live Snowflake steps):

- `SNOWFLAKE_ACCOUNT_URL`: Snowflake account URL (e.g., `https://abc12345.snowflakecomputing.com`)
- `SNOWFLAKE_API_KEY` or `SNOWFLAKE_SESSION_TOKEN`: Authentication credentials
- `SNOWFLAKE_SEMANTIC_VIEW`: Fully qualified semantic view name (e.g., `RETAIL_DB.PUBLIC.retail_semantic_view`)

### Behavior Without Credentials

If Snowflake credentials are not available:
- ✅ All validation steps run (validate-odl, diff, compile, eval gates)
- ⏭️ Verify-only step is skipped
- ⏭️ Cortex regression step is skipped
- ✅ CI still passes if validation steps succeed

### Setting Up Secrets

1. Go to your GitHub repository
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Add the following secrets:
   - `SNOWFLAKE_ACCOUNT_URL`
   - `SNOWFLAKE_API_KEY` (or `SNOWFLAKE_SESSION_TOKEN`)
   - `SNOWFLAKE_SEMANTIC_VIEW`

### Example Workflow Run

```yaml
# Without credentials
- Validate ODL: ✅ Passed
- Diff against main: ✅ Passed (no breaking changes)
- Compile Snowflake: ✅ Passed
- Eval gates: ✅ Passed (7/7 gates)
- Verify-only: ⏭️ Skipped (no credentials)
- Cortex regression: ⏭️ Skipped (no credentials)

# With credentials
- Validate ODL: ✅ Passed
- Diff against main: ✅ Passed
- Compile Snowflake: ✅ Passed
- Eval gates: ✅ Passed
- Verify-only: ✅ Passed (verify.sql generated)
- Cortex regression: ✅ Passed (5/5 questions passed)
```

### Artifacts

- **test-results.xml**: JUnit XML report from Cortex regression tests (if run)
- Uploaded as artifact: `cortex-regression-results`

### Troubleshooting

#### "No ODL files found"
- Ensure ODL files are in `odl/` directory
- Check that file extensions are `.json`, `.yaml`, or `.yml`

#### "Validation failed"
- Check ODL file structure against schema
- Run validation locally: `python odl/validate_odl.py odl/examples/snowflake_retail.odl.json`

#### "Diff computation failed"
- Ensure ODL file exists in both PR and main branch
- Check that file is valid JSON/YAML

#### "Evaluation gates failed"
- Review gate results in CI output
- Fix breaking issues (missing references, incomplete mappings, etc.)

#### "Cortex regression skipped"
- Check that `SNOWFLAKE_SEMANTIC_VIEW` secret is set
- Verify `examples/golden_questions.yaml` exists
- Ensure Snowflake credentials are valid
