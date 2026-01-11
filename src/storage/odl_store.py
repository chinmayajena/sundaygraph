"""PostgreSQL storage for ODL-based ontology management."""

from typing import Dict, Any, List, Optional
from datetime import datetime
import json

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class ODLStore:
    """Stores ODL-based ontologies in PostgreSQL with workspace scoping."""
    
    def __init__(self, connection_string: str):
        """
        Initialize ODL store.
        
        Args:
            connection_string: PostgreSQL connection string
        """
        self.connection_string = connection_string
        self._connection = None
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize database tables."""
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            
            self._connection = psycopg2.connect(self.connection_string)
            cursor = self._connection.cursor()
            
            # Read and execute migration
            migration_file = __file__.replace("odl_store.py", "../../migrations/001_create_odl_tables.sql")
            import os
            migration_path = os.path.join(os.path.dirname(__file__), "..", "..", "migrations", "001_create_odl_tables.sql")
            
            if os.path.exists(migration_path):
                with open(migration_path, 'r', encoding='utf-8') as f:
                    migration_sql = f.read()
                cursor.execute(migration_sql)
                self._connection.commit()
                logger.info("ODL store database initialized")
            else:
                # Fallback: create tables directly
                self._create_tables_direct(cursor)
                self._connection.commit()
                logger.info("ODL store database initialized (direct)")
        
        except ImportError:
            logger.warning("psycopg2 not installed. Install with: pip install psycopg2-binary")
            self._connection = None
        except Exception as e:
            logger.warning(f"Could not connect to PostgreSQL ODL store: {e}")
            self._connection = None
    
    def _create_tables_direct(self, cursor):
        """Create tables directly if migration file not found."""
        # This is a fallback - migration file is preferred
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ontology (
                id SERIAL PRIMARY KEY,
                workspace_id VARCHAR(255) NOT NULL,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                UNIQUE(workspace_id, name)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ontology_version (
                id SERIAL PRIMARY KEY,
                ontology_id INTEGER NOT NULL REFERENCES ontology(id) ON DELETE CASCADE,
                version_number VARCHAR(50) NOT NULL,
                odl_json JSONB NOT NULL,
                notes TEXT,
                created_by VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(ontology_id, version_number)
            )
        """)
        
        cursor.execute("""
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
            )
        """)
        
        cursor.execute("""
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
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS drift_event (
                id SERIAL PRIMARY KEY,
                ontology_id INTEGER NOT NULL REFERENCES ontology(id) ON DELETE CASCADE,
                event_type VARCHAR(50) NOT NULL,
                details JSONB,
                status VARCHAR(50) NOT NULL DEFAULT 'OPEN',
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP,
                created_by VARCHAR(255)
            )
        """)
    
    def create_ontology(
        self,
        workspace_id: str,
        name: str,
        description: Optional[str] = None
    ) -> int:
        """
        Create a new ontology.
        
        Args:
            workspace_id: Workspace identifier
            name: Ontology name
            description: Optional description
            
        Returns:
            Ontology ID
        """
        if not self._connection:
            raise RuntimeError("Database connection not available")
        
        cursor = self._connection.cursor()
        cursor.execute("""
            INSERT INTO ontology (workspace_id, name, description)
            VALUES (%s, %s, %s)
            ON CONFLICT (workspace_id, name) DO UPDATE
            SET description = EXCLUDED.description,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id
        """, (workspace_id, name, description))
        
        ontology_id = cursor.fetchone()[0]
        self._connection.commit()
        logger.info(f"Created ontology '{name}' for workspace '{workspace_id}' (id: {ontology_id})")
        return ontology_id
    
    def create_ontology_version(
        self,
        ontology_id: int,
        version_number: str,
        odl_json: Dict[str, Any],
        notes: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> int:
        """
        Create a new ontology version with ODL JSON.
        
        Args:
            ontology_id: Ontology ID
            version_number: Version number (e.g., "1.0.0")
            odl_json: ODL JSON payload
            notes: Optional notes
            created_by: User who created the version
            
        Returns:
            Version ID
        """
        if not self._connection:
            raise RuntimeError("Database connection not available")
        
        cursor = self._connection.cursor()
        cursor.execute("""
            INSERT INTO ontology_version (ontology_id, version_number, odl_json, notes, created_by)
            VALUES (%s, %s, %s::jsonb, %s, %s)
            ON CONFLICT (ontology_id, version_number) DO UPDATE
            SET odl_json = EXCLUDED.odl_json,
                notes = EXCLUDED.notes,
                created_by = EXCLUDED.created_by
            RETURNING id
        """, (ontology_id, version_number, json.dumps(odl_json), notes, created_by))
        
        version_id = cursor.fetchone()[0]
        self._connection.commit()
        logger.info(f"Created ontology version '{version_number}' (id: {version_id})")
        return version_id
    
    def get_ontology_version(
        self,
        ontology_id: int,
        version_number: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get ontology version by ID or version number.
        
        Args:
            ontology_id: Ontology ID
            version_number: Version number (if None, gets latest)
            
        Returns:
            Version data with ODL JSON or None
        """
        if not self._connection:
            return None
        
        cursor = self._connection.cursor()
        
        if version_number:
            cursor.execute("""
                SELECT id, version_number, odl_json, notes, created_by, created_at
                FROM ontology_version
                WHERE ontology_id = %s AND version_number = %s
            """, (ontology_id, version_number))
        else:
            cursor.execute("""
                SELECT id, version_number, odl_json, notes, created_by, created_at
                FROM ontology_version
                WHERE ontology_id = %s
                ORDER BY created_at DESC
                LIMIT 1
            """, (ontology_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return {
            "id": row[0],
            "version_number": row[1],
            "odl_json": row[2],
            "notes": row[3],
            "created_by": row[4],
            "created_at": row[5].isoformat() if row[5] else None
        }
    
    def list_ontology_versions(
        self,
        ontology_id: int,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List all versions of an ontology.
        
        Args:
            ontology_id: Ontology ID
            limit: Maximum number of versions to return
            
        Returns:
            List of version data
        """
        if not self._connection:
            return []
        
        cursor = self._connection.cursor()
        cursor.execute("""
            SELECT id, version_number, odl_json, notes, created_by, created_at
            FROM ontology_version
            WHERE ontology_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """, (ontology_id, limit))
        
        versions = []
        for row in cursor.fetchall():
            versions.append({
                "id": row[0],
                "version_number": row[1],
                "odl_json": row[2],
                "notes": row[3],
                "created_by": row[4],
                "created_at": row[5].isoformat() if row[5] else None
            })
        
        return versions
    
    def store_diff(
        self,
        ontology_id: int,
        old_version_id: int,
        new_version_id: int,
        diff_json: Dict[str, Any],
        summary: Dict[str, Any],
        created_by: Optional[str] = None
    ) -> int:
        """
        Store a diff between two ontology versions.
        
        Args:
            ontology_id: Ontology ID
            old_version_id: Old version ID
            new_version_id: New version ID
            diff_json: Detailed diff JSON
            summary: Summary of changes
            created_by: User who created the diff
            
        Returns:
            Diff ID
        """
        if not self._connection:
            raise RuntimeError("Database connection not available")
        
        cursor = self._connection.cursor()
        cursor.execute("""
            INSERT INTO ontology_diff (ontology_id, old_version_id, new_version_id, diff_json, summary, created_by)
            VALUES (%s, %s, %s, %s::jsonb, %s::jsonb, %s)
            ON CONFLICT (old_version_id, new_version_id) DO UPDATE
            SET diff_json = EXCLUDED.diff_json,
                summary = EXCLUDED.summary,
                created_by = EXCLUDED.created_by
            RETURNING id
        """, (
            ontology_id,
            old_version_id,
            new_version_id,
            json.dumps(diff_json),
            json.dumps(summary),
            created_by
        ))
        
        diff_id = cursor.fetchone()[0]
        self._connection.commit()
        logger.info(f"Stored diff between versions {old_version_id} and {new_version_id} (id: {diff_id})")
        return diff_id
    
    def get_diff(
        self,
        old_version_id: int,
        new_version_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get a diff between two ontology versions.
        
        Args:
            old_version_id: Old version ID
            new_version_id: New version ID
            
        Returns:
            Diff data or None
        """
        if not self._connection:
            return None
        
        cursor = self._connection.cursor()
        cursor.execute("""
            SELECT id, ontology_id, old_version_id, new_version_id, diff_json, summary, created_at, created_by
            FROM ontology_diff
            WHERE old_version_id = %s AND new_version_id = %s
        """, (old_version_id, new_version_id))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return {
            "id": row[0],
            "ontology_id": row[1],
            "old_version_id": row[2],
            "new_version_id": row[3],
            "diff_json": row[4],
            "summary": row[5],
            "created_at": row[6].isoformat() if row[6] else None,
            "created_by": row[7]
        }
    
    def create_eval_run(
        self,
        ontology_version_id: int,
        threshold_profile: str,
        metrics: Dict[str, Any],
        pass_fail: bool,
        notes: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> int:
        """
        Create an evaluation run record.
        
        Args:
            ontology_version_id: Version ID
            threshold_profile: Threshold profile name
            metrics: Evaluation metrics JSON
            pass_fail: Whether evaluation passed
            notes: Optional notes
            created_by: User who created the eval run
            
        Returns:
            Eval run ID
        """
        if not self._connection:
            raise RuntimeError("Database connection not available")
        
        cursor = self._connection.cursor()
        cursor.execute("""
            INSERT INTO eval_run (ontology_version_id, threshold_profile, metrics, pass_fail, notes, created_by)
            VALUES (%s, %s, %s::jsonb, %s, %s, %s)
            RETURNING id
        """, (
            ontology_version_id,
            threshold_profile,
            json.dumps(metrics),
            pass_fail,
            notes,
            created_by
        ))
        
        eval_id = cursor.fetchone()[0]
        self._connection.commit()
        logger.info(f"Created eval run (id: {eval_id}) for version {ontology_version_id}: {'PASS' if pass_fail else 'FAIL'}")
        return eval_id
    
    def get_eval_runs(
        self,
        ontology_version_id: int,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get evaluation runs for a version.
        
        Args:
            ontology_version_id: Version ID
            limit: Maximum number of runs to return
            
        Returns:
            List of eval run data
        """
        if not self._connection:
            return []
        
        cursor = self._connection.cursor()
        cursor.execute("""
            SELECT id, threshold_profile, metrics, pass_fail, notes, started_at, completed_at, created_by
            FROM eval_run
            WHERE ontology_version_id = %s
            ORDER BY started_at DESC
            LIMIT %s
        """, (ontology_version_id, limit))
        
        runs = []
        for row in cursor.fetchall():
            runs.append({
                "id": row[0],
                "threshold_profile": row[1],
                "metrics": row[2],
                "pass_fail": row[3],
                "notes": row[4],
                "started_at": row[5].isoformat() if row[5] else None,
                "completed_at": row[6].isoformat() if row[6] else None,
                "created_by": row[7]
            })
        
        return runs
    
    def create_drift_event(
        self,
        ontology_id: int,
        event_type: str,
        details: Dict[str, Any],
        status: str = "OPEN",
        created_by: Optional[str] = None
    ) -> int:
        """
        Create a drift event.
        
        Args:
            ontology_id: Ontology ID
            event_type: Event type (e.g., "COLUMN_MISSING", "YAML_DIVERGENCE")
            details: Event details JSON
            status: Event status (OPEN, RESOLVED, IGNORED)
            created_by: User who created the event
            
        Returns:
            Drift event ID
        """
        if not self._connection:
            raise RuntimeError("Database connection not available")
        
        cursor = self._connection.cursor()
        cursor.execute("""
            INSERT INTO drift_event (ontology_id, event_type, details, status, created_by)
            VALUES (%s, %s, %s::jsonb, %s, %s)
            RETURNING id
        """, (
            ontology_id,
            event_type,
            json.dumps(details),
            status,
            created_by
        ))
        
        event_id = cursor.fetchone()[0]
        self._connection.commit()
        logger.info(f"Created drift event (id: {event_id}) for ontology {ontology_id}: {event_type}")
        return event_id
    
    def get_drift_events(
        self,
        ontology_id: int,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get drift events for an ontology.
        
        Args:
            ontology_id: Ontology ID
            status: Filter by status (OPEN, RESOLVED, IGNORED) or None for all
            limit: Maximum number of events to return
            
        Returns:
            List of drift event data
        """
        if not self._connection:
            return []
        
        cursor = self._connection.cursor()
        
        if status:
            cursor.execute("""
                SELECT id, event_type, details, status, detected_at, resolved_at, created_by
                FROM drift_event
                WHERE ontology_id = %s AND status = %s
                ORDER BY detected_at DESC
                LIMIT %s
            """, (ontology_id, status, limit))
        else:
            cursor.execute("""
                SELECT id, event_type, details, status, detected_at, resolved_at, created_by
                FROM drift_event
                WHERE ontology_id = %s
                ORDER BY detected_at DESC
                LIMIT %s
            """, (ontology_id, limit))
        
        events = []
        for row in cursor.fetchall():
            events.append({
                "id": row[0],
                "event_type": row[1],
                "details": row[2],
                "status": row[3],
                "detected_at": row[4].isoformat() if row[4] else None,
                "resolved_at": row[5].isoformat() if row[5] else None,
                "created_by": row[6]
            })
        
        return events
    
    def create_cortex_regression_run(
        self,
        ontology_version_id: Optional[int],
        semantic_view_fqname: str,
        questions_file_path: Optional[str],
        total_questions: int,
        passed: int,
        failed: int,
        overall_pass: bool,
        total_latency_ms: float,
        results_json: Dict[str, Any],
        junit_xml_path: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> int:
        """
        Create a Cortex Analyst regression run record.
        
        Args:
            ontology_version_id: Optional version ID
            semantic_view_fqname: Fully qualified semantic view name
            questions_file_path: Path to questions YAML file
            total_questions: Total number of questions
            passed: Number of passed tests
            failed: Number of failed tests
            overall_pass: Whether overall run passed
            total_latency_ms: Total latency in milliseconds
            results_json: Full results JSON
            junit_xml_path: Path to generated JUnit XML
            created_by: User who created the run
            
        Returns:
            Regression run ID
        """
        if not self._connection:
            raise RuntimeError("Database connection not available")
        
        cursor = self._connection.cursor()
        cursor.execute("""
            INSERT INTO cortex_regression_run (
                ontology_version_id, semantic_view_fqname, questions_file_path,
                total_questions, passed, failed, overall_pass, total_latency_ms,
                results_json, junit_xml_path, created_by, completed_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, CURRENT_TIMESTAMP)
            RETURNING id
        """, (
            ontology_version_id,
            semantic_view_fqname,
            questions_file_path,
            total_questions,
            passed,
            failed,
            overall_pass,
            total_latency_ms,
            json.dumps(results_json),
            junit_xml_path,
            created_by
        ))
        
        run_id = cursor.fetchone()[0]
        self._connection.commit()
        logger.info(f"Created Cortex regression run (id: {run_id}): {passed}/{total_questions} passed")
        return run_id
    
    def get_cortex_regression_runs(
        self,
        ontology_version_id: Optional[int] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get Cortex regression runs.
        
        Args:
            ontology_version_id: Optional version ID filter
            limit: Maximum number of runs to return
            
        Returns:
            List of regression run data
        """
        if not self._connection:
            return []
        
        cursor = self._connection.cursor()
        
        if ontology_version_id:
            cursor.execute("""
                SELECT id, ontology_version_id, semantic_view_fqname, questions_file_path,
                       total_questions, passed, failed, overall_pass, total_latency_ms,
                       results_json, junit_xml_path, started_at, completed_at, created_by
                FROM cortex_regression_run
                WHERE ontology_version_id = %s
                ORDER BY started_at DESC
                LIMIT %s
            """, (ontology_version_id, limit))
        else:
            cursor.execute("""
                SELECT id, ontology_version_id, semantic_view_fqname, questions_file_path,
                       total_questions, passed, failed, overall_pass, total_latency_ms,
                       results_json, junit_xml_path, started_at, completed_at, created_by
                FROM cortex_regression_run
                ORDER BY started_at DESC
                LIMIT %s
            """, (limit,))
        
        runs = []
        for row in cursor.fetchall():
            runs.append({
                "id": row[0],
                "ontology_version_id": row[1],
                "semantic_view_fqname": row[2],
                "questions_file_path": row[3],
                "total_questions": row[4],
                "passed": row[5],
                "failed": row[6],
                "overall_pass": row[7],
                "total_latency_ms": row[8],
                "results_json": row[9],
                "junit_xml_path": row[10],
                "started_at": row[11].isoformat() if row[11] else None,
                "completed_at": row[12].isoformat() if row[12] else None,
                "created_by": row[13]
            })
        
        return runs
    
    def get_version_by_id(self, version_id: int) -> Optional[Dict[str, Any]]:
        """
        Get ontology version by ID.
        
        Args:
            version_id: Version ID
            
        Returns:
            Version data or None
        """
        if not self._connection:
            return None
        
        cursor = self._connection.cursor()
        cursor.execute("""
            SELECT id, ontology_id, version_number, odl_json, notes, created_by, created_at
            FROM ontology_version
            WHERE id = %s
        """, (version_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return {
            "id": row[0],
            "ontology_id": row[1],
            "version_number": row[2],
            "odl_json": row[3],
            "notes": row[4],
            "created_by": row[5],
            "created_at": row[6].isoformat() if row[6] else None
        }
    
    def get_ontology_by_workspace(
        self,
        workspace_id: str,
        name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get ontology by workspace and optionally name.
        
        Args:
            workspace_id: Workspace identifier
            name: Ontology name (if None, gets first active)
            
        Returns:
            Ontology data or None
        """
        if not self._connection:
            return None
        
        cursor = self._connection.cursor()
        
        if name:
            cursor.execute("""
                SELECT id, workspace_id, name, description, created_at, updated_at, is_active
                FROM ontology
                WHERE workspace_id = %s AND name = %s AND is_active = TRUE
            """, (workspace_id, name))
        else:
            cursor.execute("""
                SELECT id, workspace_id, name, description, created_at, updated_at, is_active
                FROM ontology
                WHERE workspace_id = %s AND is_active = TRUE
                ORDER BY created_at DESC
                LIMIT 1
            """, (workspace_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return {
            "id": row[0],
            "workspace_id": row[1],
            "name": row[2],
            "description": row[3],
            "created_at": row[4].isoformat() if row[4] else None,
            "updated_at": row[5].isoformat() if row[5] else None,
            "is_active": row[6]
        }
