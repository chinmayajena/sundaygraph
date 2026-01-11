-- Migration: Create cortex_regression_run table
-- Description: Stores Cortex Analyst regression test runs

CREATE TABLE IF NOT EXISTS cortex_regression_run (
    id SERIAL PRIMARY KEY,
    ontology_version_id INTEGER REFERENCES ontology_version(id) ON DELETE CASCADE,
    semantic_view_fqname VARCHAR(500) NOT NULL,
    questions_file_path TEXT,
    total_questions INTEGER NOT NULL,
    passed INTEGER NOT NULL,
    failed INTEGER NOT NULL,
    overall_pass BOOLEAN NOT NULL,
    total_latency_ms FLOAT,
    results_json JSONB NOT NULL,
    junit_xml_path TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    created_by VARCHAR(255)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_cortex_regression_version 
    ON cortex_regression_run(ontology_version_id);

CREATE INDEX IF NOT EXISTS idx_cortex_regression_created 
    ON cortex_regression_run(ontology_version_id, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_cortex_regression_pass 
    ON cortex_regression_run(overall_pass) WHERE overall_pass = FALSE;

-- Add comments
COMMENT ON TABLE cortex_regression_run IS 'Cortex Analyst regression test runs';
COMMENT ON COLUMN cortex_regression_run.results_json IS 'Full regression run results (JSON)';
COMMENT ON COLUMN cortex_regression_run.junit_xml_path IS 'Path to generated JUnit XML file';
