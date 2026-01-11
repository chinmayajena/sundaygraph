# GitHub Secrets Setup Guide

## Required Secrets for Semantic CI

The Semantic CI workflow uses GitHub Secrets to securely store Snowflake credentials. No credentials are hardcoded in the workflow file.

### Secrets to Configure

1. **SNOWFLAKE_ACCOUNT_URL** (optional)
   - Description: Snowflake account URL
   - Example: `https://abc12345.snowflakecomputing.com`
   - Format: Full URL to your Snowflake account

2. **SNOWFLAKE_API_KEY** (optional, if using API key auth)
   - Description: Snowflake API key for authentication
   - Example: `your_api_key_here`
   - Note: Use either API key OR session token, not both

3. **SNOWFLAKE_SESSION_TOKEN** (optional, if using session token auth)
   - Description: Snowflake session token for authentication
   - Example: `your_session_token_here`
   - Note: Use either API key OR session token, not both

4. **SNOWFLAKE_SEMANTIC_VIEW** (optional)
   - Description: Fully qualified semantic view name for regression tests
   - Example: `RETAIL_DB.PUBLIC.retail_semantic_view`
   - Format: `database.schema.view_name`

### How to Add Secrets

1. Go to your GitHub repository
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Enter the secret name and value
5. Click **Add secret**

### Workflow Behavior

#### Without Secrets

If secrets are not configured:
- ✅ **Validate ODL**: Runs (no credentials needed)
- ✅ **Diff against main**: Runs (no credentials needed)
- ✅ **Compile Snowflake**: Runs (no credentials needed)
- ✅ **Eval gates**: Runs (no credentials needed)
- ⏭️ **Verify-only**: Skipped (requires credentials)
- ⏭️ **Cortex regression**: Skipped (requires credentials)

**Result**: CI passes if validation steps succeed.

#### With Secrets

If all required secrets are configured:
- ✅ **Validate ODL**: Runs
- ✅ **Diff against main**: Runs
- ✅ **Compile Snowflake**: Runs
- ✅ **Eval gates**: Runs
- ✅ **Verify-only**: Runs (validates verify.sql generation)
- ✅ **Cortex regression**: Runs (tests semantic view with questions)

**Result**: Full CI pipeline with live Snowflake validation.

### Security Best Practices

1. **Never commit secrets** to the repository
2. **Use repository secrets** for repository-specific values
3. **Use organization secrets** for shared values across repositories
4. **Rotate secrets regularly**
5. **Use least-privilege credentials** (read-only if possible)
6. **Review secret access** in repository settings

### Testing Secrets

To test if secrets are configured correctly:

```bash
# In a GitHub Actions workflow, you can check:
if [ -n "${{ secrets.SNOWFLAKE_ACCOUNT_URL }}" ]; then
  echo "Secrets are configured"
else
  echo "Secrets are not configured"
fi
```

### Troubleshooting

#### "Snowflake credentials not available"
- Check that secrets are added in repository settings
- Verify secret names match exactly (case-sensitive)
- Ensure secrets are not empty

#### "Cortex regression skipped"
- Check that `SNOWFLAKE_SEMANTIC_VIEW` is set
- Verify semantic view exists in Snowflake
- Ensure `examples/golden_questions.yaml` exists

#### "Authentication failed"
- Verify API key or session token is valid
- Check that credentials have necessary permissions
- Ensure account URL is correct

### Example Secret Configuration

```
SNOWFLAKE_ACCOUNT_URL: https://abc12345.snowflakecomputing.com
SNOWFLAKE_API_KEY: sk_live_abc123def456...
SNOWFLAKE_SEMANTIC_VIEW: RETAIL_DB.PUBLIC.retail_semantic_view
```

### CI Status

The workflow will show:
- ✅ **Green checkmark**: All steps passed
- ⚠️ **Yellow circle**: Some optional steps skipped (no credentials)
- ❌ **Red X**: Validation steps failed

Even without credentials, the workflow provides value by validating ODL structure and detecting breaking changes.
