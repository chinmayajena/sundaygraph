-- Migration: Create ODL-based ontology tables
-- Description: Replaces ontology_schemas with workspace-scoped ODL JSON storage

-- Drop old tables if they exist (migration from old schema)
DROP TABLE IF EXISTS schema_evolution CASCADE;
DROP TABLE IF EXISTS ontology_schemas CASCADE;

-- Create ontology table (workspace-scoped)
CREATE TABLE IF NOT EXISTS ontology (
    id SERIAL PRIMARY KEY,
    workspace_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(workspace_id, name)
);

-- Create ontology_version table (stores ODL JSON payload)
CREATE TABLE IF NOT EXISTS ontology_version (
    id SERIAL PRIMARY KEY,
    ontology_id INTEGER NOT NULL REFERENCES ontology(id) ON DELETE CASCADE,
    version_number VARCHAR(50) NOT NULL,
    odl_json JSONB NOT NULL,
    notes TEXT,
    created_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ontology_id, version_number)
);

-- Create compile_run table (tracks compilation to Snowflake)
CREATE TABLE IF NOT EXISTS compile_run (
    id SERIAL PRIMARY KEY,
    ontology_version_id INTEGER NOT NULL REFERENCES ontology_version(id) ON DELETE CASCADE,
    target VARCHAR(50) NOT NULL DEFAULT 'SNOWFLAKE',
    options JSONB,
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    artifact_path TEXT,
    error_message TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    created_by VARCHAR(255)
);

-- Create eval_run table (evaluation runs with metrics)
CREATE TABLE IF NOT EXISTS eval_run (
    id SERIAL PRIMARY KEY,
    ontology_version_id INTEGER NOT NULL REFERENCES ontology_version(id) ON DELETE CASCADE,
    threshold_profile VARCHAR(255),
    metrics JSONB,
    pass_fail BOOLEAN,
    notes TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    created_by VARCHAR(255)
);

-- Create drift_event table (tracks schema drift)
CREATE TABLE IF NOT EXISTS drift_event (
    id SERIAL PRIMARY KEY,
    ontology_id INTEGER NOT NULL REFERENCES ontology(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    details JSONB,
    status VARCHAR(50) NOT NULL DEFAULT 'OPEN',
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    created_by VARCHAR(255)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_ontology_workspace 
    ON ontology(workspace_id) WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_ontology_version_ontology 
    ON ontology_version(ontology_id);

CREATE INDEX IF NOT EXISTS idx_ontology_version_created 
    ON ontology_version(ontology_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_compile_run_version 
    ON compile_run(ontology_version_id);

CREATE INDEX IF NOT EXISTS idx_compile_run_status 
    ON compile_run(status) WHERE status IN ('PENDING', 'RUNNING');

CREATE INDEX IF NOT EXISTS idx_eval_run_version 
    ON eval_run(ontology_version_id);

CREATE INDEX IF NOT EXISTS idx_drift_event_ontology 
    ON drift_event(ontology_id);

CREATE INDEX IF NOT EXISTS idx_drift_event_status 
    ON drift_event(status) WHERE status = 'OPEN';

-- Add comments for documentation
COMMENT ON TABLE ontology IS 'Workspace-scoped ontology definitions';
COMMENT ON TABLE ontology_version IS 'Version history of ODL JSON payloads';
COMMENT ON TABLE compile_run IS 'Compilation runs to target systems (e.g., Snowflake)';
COMMENT ON TABLE eval_run IS 'Evaluation runs with metrics and pass/fail status';
COMMENT ON TABLE drift_event IS 'Schema drift detection events';

COMMENT ON COLUMN ontology_version.odl_json IS 'Canonical ODL JSON payload';
COMMENT ON COLUMN compile_run.target IS 'Target system (SNOWFLAKE, etc.)';
COMMENT ON COLUMN compile_run.status IS 'PENDING, RUNNING, SUCCESS, FAILED';
COMMENT ON COLUMN drift_event.event_type IS 'Type of drift (SCHEMA_CHANGE, DATA_DRIFT, etc.)';
COMMENT ON COLUMN drift_event.status IS 'OPEN, RESOLVED, IGNORED';
