"""PostgreSQL storage for user workspaces and user data"""

from typing import Dict, Any, List, Optional
from loguru import logger
import json
from datetime import datetime


class UserWorkspaceStore:
    """Stores user workspaces and user data in PostgreSQL"""
    
    def __init__(self, connection_string: str):
        """
        Initialize user workspace store
        
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
            
            # Create users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(255) UNIQUE NOT NULL,
                    email VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)
            
            # Create workspaces table (user-specific)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workspaces (
                    id SERIAL PRIMARY KEY,
                    workspace_id VARCHAR(255) NOT NULL,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    path TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    UNIQUE(user_id, workspace_id)
                )
            """)
            
            # Create workspace files metadata table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workspace_files (
                    id SERIAL PRIMARY KEY,
                    workspace_id INTEGER REFERENCES workspaces(id) ON DELETE CASCADE,
                    filename VARCHAR(255) NOT NULL,
                    file_path TEXT NOT NULL,
                    subdir VARCHAR(50) NOT NULL DEFAULT 'input',
                    file_size BIGINT,
                    file_type VARCHAR(50),
                    mime_type VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(workspace_id, filename, subdir)
                )
            """)
            
            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_workspaces_user 
                ON workspaces(user_id) WHERE is_active = TRUE
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_workspaces_workspace_id 
                ON workspaces(workspace_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_workspace_files_workspace 
                ON workspace_files(workspace_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_username 
                ON users(username) WHERE is_active = TRUE
            """)
            
            self._connection.commit()
            
            # Ensure default 'admin' user exists
            self._ensure_default_user()
            
            logger.info("User workspace store database initialized")
        
        except ImportError:
            logger.warning("psycopg2 not installed. Install with: pip install psycopg2-binary")
            self._connection = None
        except Exception as e:
            logger.warning(f"Could not connect to PostgreSQL user workspace store: {e}")
            logger.info("Continuing without PostgreSQL workspace storage (using file-based)")
            self._connection = None
    
    def _ensure_default_user(self):
        """Ensure default 'admin' user exists"""
        if not self._connection:
            return
        
        try:
            cursor = self._connection.cursor()
            cursor.execute("""
                INSERT INTO users (username, email, is_active)
                VALUES ('admin', 'admin@sundaygraph.local', TRUE)
                ON CONFLICT (username) DO NOTHING
            """)
            self._connection.commit()
            logger.info("Default 'admin' user ensured")
        except Exception as e:
            logger.warning(f"Failed to ensure default user: {e}")
    
    def get_or_create_user(self, username: str, email: Optional[str] = None) -> Optional[int]:
        """
        Get or create a user
        
        Args:
            username: Username
            email: Optional email
            
        Returns:
            User ID or None if connection failed
        """
        if not self._connection:
            return None
        
        try:
            from psycopg2.extras import RealDictCursor
            
            cursor = self._connection.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                INSERT INTO users (username, email, is_active)
                VALUES (%s, %s, TRUE)
                ON CONFLICT (username) DO UPDATE
                SET updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """, (username, email))
            
            result = cursor.fetchone()
            if result:
                user_id = result["id"]
                self._connection.commit()
                return user_id
            
            # If no result, try to get existing user
            cursor.execute("""
                SELECT id FROM users WHERE username = %s AND is_active = TRUE
            """, (username,))
            result = cursor.fetchone()
            if result:
                return result["id"]
            
            return None
        except Exception as e:
            logger.error(f"Error getting/creating user: {e}")
            self._connection.rollback()
            return None
    
    def create_workspace(
        self,
        user_id: int,
        workspace_id: str,
        name: str,
        description: Optional[str] = None,
        path: str = ""
    ) -> Optional[int]:
        """
        Create a workspace for a user
        
        Args:
            user_id: User ID
            workspace_id: Workspace identifier
            name: Workspace name
            description: Optional description
            path: Workspace file system path
            
        Returns:
            Workspace database ID or None
        """
        if not self._connection:
            return None
        
        try:
            cursor = self._connection.cursor()
            cursor.execute("""
                INSERT INTO workspaces (workspace_id, user_id, name, description, path, is_active)
                VALUES (%s, %s, %s, %s, %s, TRUE)
                ON CONFLICT (user_id, workspace_id) DO UPDATE
                SET name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """, (workspace_id, user_id, name, description or "", path))
            
            result = cursor.fetchone()
            if result:
                workspace_db_id = result[0]
                self._connection.commit()
                logger.info(f"Created workspace {workspace_id} for user {user_id}")
                return workspace_db_id
            return None
        except Exception as e:
            logger.error(f"Error creating workspace: {e}")
            self._connection.rollback()
            return None
    
    def get_workspace(self, user_id: int, workspace_id: str) -> Optional[Dict[str, Any]]:
        """Get workspace for a user"""
        if not self._connection:
            return None
        
        try:
            from psycopg2.extras import RealDictCursor
            
            cursor = self._connection.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT w.id, w.workspace_id, w.name, w.description, w.path,
                       w.created_at, w.updated_at
                FROM workspaces w
                WHERE w.user_id = %s AND w.workspace_id = %s AND w.is_active = TRUE
            """, (user_id, workspace_id))
            
            result = cursor.fetchone()
            if result:
                return dict(result)
            return None
        except Exception as e:
            logger.error(f"Error getting workspace: {e}")
            return None
    
    def list_workspaces(self, user_id: int) -> List[Dict[str, Any]]:
        """List all workspaces for a user"""
        if not self._connection:
            return []
        
        try:
            from psycopg2.extras import RealDictCursor
            
            cursor = self._connection.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT w.id, w.workspace_id, w.name, w.description, w.path,
                       w.created_at, w.updated_at
                FROM workspaces w
                WHERE w.user_id = %s AND w.is_active = TRUE
                ORDER BY w.created_at DESC
            """, (user_id,))
            
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error listing workspaces: {e}")
            return []
    
    def delete_workspace(self, user_id: int, workspace_id: str) -> bool:
        """Delete a workspace (soft delete)"""
        if not self._connection:
            return False
        
        try:
            cursor = self._connection.cursor()
            cursor.execute("""
                UPDATE workspaces
                SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s AND workspace_id = %s AND is_active = TRUE
            """, (user_id, workspace_id))
            
            deleted = cursor.rowcount > 0
            self._connection.commit()
            return deleted
        except Exception as e:
            logger.error(f"Error deleting workspace: {e}")
            self._connection.rollback()
            return False
    
    def record_file(
        self,
        workspace_db_id: int,
        filename: str,
        file_path: str,
        subdir: str = "input",
        file_size: Optional[int] = None,
        file_type: Optional[str] = None,
        mime_type: Optional[str] = None
    ) -> Optional[int]:
        """Record a file in workspace"""
        if not self._connection:
            return None
        
        try:
            cursor = self._connection.cursor()
            cursor.execute("""
                INSERT INTO workspace_files 
                (workspace_id, filename, file_path, subdir, file_size, file_type, mime_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (workspace_id, filename, subdir) DO UPDATE
                SET file_path = EXCLUDED.file_path,
                    file_size = EXCLUDED.file_size,
                    file_type = EXCLUDED.file_type,
                    mime_type = EXCLUDED.mime_type,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """, (workspace_db_id, filename, file_path, subdir, file_size, file_type, mime_type))
            
            result = cursor.fetchone()
            if result:
                file_id = result[0]
                self._connection.commit()
                return file_id
            return None
        except Exception as e:
            logger.error(f"Error recording file: {e}")
            self._connection.rollback()
            return None
    
    def list_files(self, workspace_db_id: int, subdir: str = "input") -> List[Dict[str, Any]]:
        """List files in workspace"""
        if not self._connection:
            return []
        
        try:
            from psycopg2.extras import RealDictCursor
            
            cursor = self._connection.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT filename, file_path, file_size, file_type, mime_type,
                       created_at, updated_at
                FROM workspace_files
                WHERE workspace_id = %s AND subdir = %s
                ORDER BY updated_at DESC
            """, (workspace_db_id, subdir))
            
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return []
    
    def close(self):
        """Close database connection"""
        if self._connection:
            self._connection.close()
            self._connection = None
