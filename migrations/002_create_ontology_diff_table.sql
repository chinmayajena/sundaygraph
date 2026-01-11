-- Migration: Create ontology_diff table
-- Description: Stores diffs between ODL versions

CREATE TABLE IF NOT EXISTS ontology_diff (
    id SERIAL PRIMARY KEY,
    ontology_id INTEGER NOT NULL REFERENCES ontology(id) ON DELETE CASCADE,
    old_version_id INTEGER NOT NULL REFERENCES ontology_version(id) ON DELETE CASCADE,
    new_version_id INTEGER NOT NULL REFERENCES ontology_version(id) ON DELETE CASCADE,
    diff_json JSONB NOT NULL,
    summary JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    UNIQUE(old_version_id, new_version_id)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_ontology_diff_ontology 
    ON ontology_diff(ontology_id);

CREATE INDEX IF NOT EXISTS idx_ontology_diff_versions 
    ON ontology_diff(old_version_id, new_version_id);

CREATE INDEX IF NOT EXISTS idx_ontology_diff_created 
    ON ontology_diff(ontology_id, created_at DESC);

-- Add comments
COMMENT ON TABLE ontology_diff IS 'Stores diffs between ODL versions';
COMMENT ON COLUMN ontology_diff.diff_json IS 'Detailed diff JSON with breaking and non-breaking changes';
COMMENT ON COLUMN ontology_diff.summary IS 'Summary of changes (counts, etc.)';
