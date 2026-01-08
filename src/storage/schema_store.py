"""PostgreSQL storage for ontology schema metadata"""

from typing import Dict, Any, List, Optional
from loguru import logger
import json
from datetime import datetime


class SchemaStore:
    """Stores ontology schema metadata in PostgreSQL"""
    
    def __init__(self, connection_string: str):
        """
        Initialize schema store
        
        Args:
            connection_string: PostgreSQL connection string
        """
        self.connection_string = connection_string
        self._connection = None
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize database tables"""
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            
            self._connection = psycopg2.connect(self.connection_string)
            cursor = self._connection.cursor()
            
            # Create schema metadata table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ontology_schemas (
                    id SERIAL PRIMARY KEY,
                    version VARCHAR(50) NOT NULL,
                    name VARCHAR(255),
                    description TEXT,
                    schema_data JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)
            
            # Create schema evolution history
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_evolution (
                    id SERIAL PRIMARY KEY,
                    schema_id INTEGER REFERENCES ontology_schemas(id),
                    change_type VARCHAR(50),
                    change_description TEXT,
                    previous_schema JSONB,
                    new_schema JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_schemas_active 
                ON ontology_schemas(is_active) WHERE is_active = TRUE
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_schemas_version 
                ON ontology_schemas(version)
            """)
            
            self._connection.commit()
            logger.info("Schema store database initialized")
        
        except ImportError:
            logger.warning("psycopg2 not installed. Install with: pip install psycopg2-binary")
            self._connection = None
        except Exception as e:
            logger.warning(f"Could not connect to PostgreSQL schema store: {e}")
            logger.info("Continuing without PostgreSQL schema storage (using file-based schema)")
            self._connection = None
    
    def save_schema(
        self,
        schema_data: Dict[str, Any],
        version: str = "1.0.0",
        name: Optional[str] = None,
        description: Optional[str] = None
    ) -> int:
        """
        Save schema to database
        
        Args:
            schema_data: Schema data as dictionary
            version: Schema version
            name: Schema name
            description: Schema description
            
        Returns:
            Schema ID
        """
        if not self._connection:
            logger.warning("Database connection not available")
            return -1
        
        try:
            from psycopg2.extras import RealDictCursor
            
            cursor = self._connection.cursor(cursor_factory=RealDictCursor)
            
            # Deactivate old schemas
            cursor.execute("""
                UPDATE ontology_schemas 
                SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                WHERE is_active = TRUE
            """)
            
            # Insert new schema
            cursor.execute("""
                INSERT INTO ontology_schemas (version, name, description, schema_data, is_active)
                VALUES (%s, %s, %s, %s, TRUE)
                RETURNING id
            """, (version, name, description, json.dumps(schema_data)))
            
            schema_id = cursor.fetchone()["id"]
            self._connection.commit()
            
            logger.info(f"Saved schema version {version} with ID {schema_id}")
            return schema_id
        
        except Exception as e:
            logger.error(f"Error saving schema: {e}")
            self._connection.rollback()
            return -1
    
    def get_active_schema(self) -> Optional[Dict[str, Any]]:
        """Get active schema"""
        if not self._connection:
            return None
        
        try:
            from psycopg2.extras import RealDictCursor
            
            cursor = self._connection.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT schema_data, version, name, description
                FROM ontology_schemas
                WHERE is_active = TRUE
                ORDER BY created_at DESC
                LIMIT 1
            """)
            
            result = cursor.fetchone()
            if result:
                return {
                    "schema": json.loads(result["schema_data"]),
                    "version": result["version"],
                    "name": result["name"],
                    "description": result["description"]
                }
            return None
        
        except Exception as e:
            logger.error(f"Error getting active schema: {e}")
            return None
    
    def record_evolution(
        self,
        schema_id: int,
        change_type: str,
        change_description: str,
        previous_schema: Dict[str, Any],
        new_schema: Dict[str, Any]
    ):
        """Record schema evolution"""
        if not self._connection:
            return
        
        try:
            cursor = self._connection.cursor()
            cursor.execute("""
                INSERT INTO schema_evolution 
                (schema_id, change_type, change_description, previous_schema, new_schema)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                schema_id,
                change_type,
                change_description,
                json.dumps(previous_schema),
                json.dumps(new_schema)
            ))
            
            self._connection.commit()
            logger.info(f"Recorded schema evolution: {change_type}")
        
        except Exception as e:
            logger.error(f"Error recording evolution: {e}")
            self._connection.rollback()
    
    def get_evolution_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get schema evolution history"""
        if not self._connection:
            return []
        
        try:
            from psycopg2.extras import RealDictCursor
            
            cursor = self._connection.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT change_type, change_description, created_at
                FROM schema_evolution
                ORDER BY created_at DESC
                LIMIT %s
            """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
        
        except Exception as e:
            logger.error(f"Error getting evolution history: {e}")
            return []
    
    def close(self):
        """Close database connection"""
        if self._connection:
            self._connection.close()
            self._connection = None

