# Database Migrations

## Running Migrations

### Using the migration runner:

```bash
python migrations/run_migrations.py \
  --host localhost \
  --port 5432 \
  --database sundaygraph \
  --user postgres \
  --password password
```

Or with connection string:

```bash
python migrations/run_migrations.py \
  --connection-string "postgresql://user:pass@host:port/database"
```

### Manual execution:

```bash
psql -h localhost -U postgres -d sundaygraph -f migrations/001_create_odl_tables.sql
```

## Migration Files

- **001_create_odl_tables.sql** - Creates workspace-scoped ODL tables:
  - `ontology` - Workspace-scoped ontology definitions
  - `ontology_version` - ODL JSON payload versions
  - `compile_run` - Compilation runs to target systems
  - `eval_run` - Evaluation runs with metrics
  - `drift_event` - Schema drift detection events

## Migration Notes

- Drops old `ontology_schemas` and `schema_evolution` tables
- Replaces with ODL JSON as canonical stored form
- All tables are workspace-scoped for multi-tenancy
- Uses JSONB for efficient JSON storage and querying
