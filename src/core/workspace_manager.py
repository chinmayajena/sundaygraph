"""Workspace manager for multi-tenant data organization"""

from pathlib import Path
from typing import Dict, Any, List, Optional
from loguru import logger
import json
import os
from datetime import datetime
from ..storage.user_workspace_store import UserWorkspaceStore


class WorkspaceManager:
    """Manages workspace-based data organization with PostgreSQL backend"""
    
    def __init__(self, base_data_dir: str = "./data", connection_string: Optional[str] = None):
        """
        Initialize workspace manager
        
        Args:
            base_data_dir: Base directory for all workspace data
            connection_string: PostgreSQL connection string (optional)
        """
        self.base_dir = Path(base_data_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize PostgreSQL store if connection string provided
        self.db_store = None
        if connection_string:
            try:
                self.db_store = UserWorkspaceStore(connection_string)
                if self.db_store._connection:
                    logger.info("WorkspaceManager using PostgreSQL backend")
                else:
                    logger.warning("PostgreSQL connection failed, using file-based storage")
                    self.db_store = None
            except Exception as e:
                logger.warning(f"Failed to initialize PostgreSQL store: {e}")
                self.db_store = None
        
        # Fallback to file-based storage
        if not self.db_store or not self.db_store._connection:
            self._workspaces_file = self.base_dir / "workspaces.json"
            self._load_workspaces()
            logger.info("WorkspaceManager using file-based storage")
    
    def _load_workspaces(self):
        """Load workspace metadata (file-based fallback)"""
        if self._workspaces_file.exists():
            try:
                with open(self._workspaces_file) as f:
                    self.workspaces = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load workspaces: {e}")
                self.workspaces = {}
        else:
            self.workspaces = {}
    
    def _save_workspaces(self):
        """Save workspace metadata (file-based fallback)"""
        try:
            with open(self._workspaces_file, 'w') as f:
                json.dump(self.workspaces, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save workspaces: {e}")
    
    def _get_user_id(self, username: str = "admin") -> Optional[int]:
        """Get user ID, defaulting to 'admin'"""
        if self.db_store:
            return self.db_store.get_or_create_user(username)
        return None
    
    def create_workspace(
        self, 
        workspace_id: str, 
        name: str, 
        description: Optional[str] = None,
        username: str = "admin"
    ) -> Dict[str, Any]:
        """
        Create a new workspace
        
        Args:
            workspace_id: Unique workspace identifier
            name: Workspace name
            description: Optional description
            username: Username (default: "admin")
            
        Returns:
            Workspace information
        """
        workspace_dir = self.base_dir / "workspaces" / workspace_id
        workspace_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (workspace_dir / "input").mkdir(exist_ok=True)
        (workspace_dir / "output").mkdir(exist_ok=True)
        (workspace_dir / "cache").mkdir(exist_ok=True)
        (workspace_dir / "graphs").mkdir(exist_ok=True)
        
        workspace_info = {
            "id": workspace_id,
            "name": name,
            "description": description or "",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "path": str(workspace_dir)
        }
        
        # Store in PostgreSQL if available
        if self.db_store and self.db_store._connection:
            user_id = self._get_user_id(username)
            if user_id:
                # Check if workspace already exists for this user
                existing = self.db_store.get_workspace(user_id, workspace_id)
                if existing:
                    raise ValueError(f"Workspace {workspace_id} already exists for user {username}")
                
                workspace_db_id = self.db_store.create_workspace(
                    user_id=user_id,
                    workspace_id=workspace_id,
                    name=name,
                    description=description,
                    path=str(workspace_dir)
                )
                if workspace_db_id:
                    logger.info(f"Created workspace {workspace_id} in PostgreSQL for user {username}")
        else:
            # Fallback to file-based storage
            if workspace_id in self.workspaces:
                raise ValueError(f"Workspace {workspace_id} already exists")
            self.workspaces[workspace_id] = workspace_info
            self._save_workspaces()
        
        logger.info(f"Created workspace: {workspace_id}")
        return workspace_info
    
    def get_workspace(self, workspace_id: str, username: str = "admin") -> Optional[Dict[str, Any]]:
        """Get workspace information"""
        # Try PostgreSQL first
        if self.db_store and self.db_store._connection:
            user_id = self._get_user_id(username)
            if user_id:
                workspace = self.db_store.get_workspace(user_id, workspace_id)
                if workspace:
                    # Convert to expected format
                    return {
                        "id": workspace["workspace_id"],
                        "name": workspace["name"],
                        "description": workspace.get("description", ""),
                        "created_at": workspace["created_at"].isoformat() if hasattr(workspace["created_at"], 'isoformat') else str(workspace["created_at"]),
                        "updated_at": workspace["updated_at"].isoformat() if hasattr(workspace["updated_at"], 'isoformat') else str(workspace["updated_at"]),
                        "path": workspace["path"]
                    }
        
        # Fallback to file-based
        return self.workspaces.get(workspace_id)
    
    def list_workspaces(self, username: str = "admin") -> List[Dict[str, Any]]:
        """List all workspaces for a user"""
        # Try PostgreSQL first
        if self.db_store and self.db_store._connection:
            user_id = self._get_user_id(username)
            if user_id:
                workspaces = self.db_store.list_workspaces(user_id)
                # Convert to expected format
                return [
                    {
                        "id": w["workspace_id"],
                        "name": w["name"],
                        "description": w.get("description", ""),
                        "created_at": w["created_at"].isoformat() if hasattr(w["created_at"], 'isoformat') else str(w["created_at"]),
                        "updated_at": w["updated_at"].isoformat() if hasattr(w["updated_at"], 'isoformat') else str(w["updated_at"]),
                        "path": w["path"]
                    }
                    for w in workspaces
                ]
        
        # Fallback to file-based
        return list(self.workspaces.values())
    
    def delete_workspace(self, workspace_id: str, username: str = "admin") -> bool:
        """
        Delete a workspace
        
        Args:
            workspace_id: Workspace identifier
            username: Username (default: "admin")
            
        Returns:
            True if deleted successfully
        """
        # Try PostgreSQL first
        if self.db_store and self.db_store._connection:
            user_id = self._get_user_id(username)
            if user_id:
                deleted = self.db_store.delete_workspace(user_id, workspace_id)
                if deleted:
                    # Also delete file system directory
                    workspace_dir = self.base_dir / "workspaces" / workspace_id
                    if workspace_dir.exists():
                        import shutil
                        shutil.rmtree(workspace_dir)
                    logger.info(f"Deleted workspace: {workspace_id} from PostgreSQL")
                    return True
        
        # Fallback to file-based
        if workspace_id not in self.workspaces:
            return False
        
        workspace_dir = self.base_dir / "workspaces" / workspace_id
        if workspace_dir.exists():
            import shutil
            shutil.rmtree(workspace_dir)
        
        del self.workspaces[workspace_id]
        self._save_workspaces()
        
        logger.info(f"Deleted workspace: {workspace_id}")
        return True
    
    def get_workspace_path(self, workspace_id: str, subdir: str = "input", username: str = "admin") -> Path:
        """
        Get path for workspace subdirectory
        
        Args:
            workspace_id: Workspace identifier
            subdir: Subdirectory name (input, output, cache, graphs)
            username: Username (default: "admin")
            
        Returns:
            Path to workspace subdirectory
        """
        # Try to get workspace from PostgreSQL or file-based
        workspace = self.get_workspace(workspace_id, username)
        if not workspace:
            raise ValueError(f"Workspace {workspace_id} does not exist for user {username}")
        
        workspace_dir = Path(workspace["path"])
        return workspace_dir / subdir
    
    def list_files(self, workspace_id: str, subdir: str = "input", username: str = "admin") -> List[Dict[str, Any]]:
        """
        List files in workspace directory (database-backed if available)
        
        Args:
            workspace_id: Workspace identifier
            subdir: Subdirectory name
            username: Username (default: "admin")
            
        Returns:
            List of file information
        """
        # Try to get files from PostgreSQL first
        if self.db_store and self.db_store._connection:
            user_id = self._get_user_id(username)
            if user_id:
                workspace_db = self.db_store.get_workspace(user_id, workspace_id)
                if workspace_db:
                    workspace_db_id = workspace_db.get("id")
                    if workspace_db_id:
                        db_files = self.db_store.list_files(workspace_db_id, subdir)
                        if db_files:
                            # Convert database records to file info format
                            files = []
                            for db_file in db_files:
                                file_path = Path(db_file.get("file_path", ""))
                                if file_path.exists():  # Verify file still exists on disk
                                    files.append({
                                        "name": db_file.get("filename", ""),
                                        "path": str(file_path),
                                        "size": db_file.get("file_size", 0),
                                        "modified": db_file.get("created_at", "").isoformat() if db_file.get("created_at") else "",
                                        "extension": file_path.suffix.lower(),
                                        "type": self._get_file_type(file_path.suffix)
                                    })
                            
                            # Sort by modified time (newest first)
                            files.sort(key=lambda x: x["modified"], reverse=True)
                            logger.debug(f"Retrieved {len(files)} files from database for workspace {workspace_id}")
                            return files
        
        # Fallback to filesystem-based listing
        workspace_path = self.get_workspace_path(workspace_id, subdir, username=username)
        
        if not workspace_path.exists():
            return []
        
        files = []
        for file_path in workspace_path.iterdir():
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    "name": file_path.name,
                    "path": str(file_path),
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "extension": file_path.suffix.lower(),
                    "type": self._get_file_type(file_path.suffix)
                })
        
        # Sort by modified time (newest first)
        files.sort(key=lambda x: x["modified"], reverse=True)
        logger.debug(f"Retrieved {len(files)} files from filesystem for workspace {workspace_id}")
        return files
    
    def get_file_preview(self, workspace_id: str, filename: str, subdir: str = "input", max_lines: int = 50, username: str = "admin") -> Dict[str, Any]:
        """
        Get file preview
        
        Args:
            workspace_id: Workspace identifier
            filename: File name
            subdir: Subdirectory name
            max_lines: Maximum lines to preview
            username: Username (default: "admin")
            
        Returns:
            File preview information
        """
        workspace_path = self.get_workspace_path(workspace_id, subdir, username=username)
        file_path = workspace_path / filename
        
        if not file_path.exists():
            raise FileNotFoundError(f"File {filename} not found")
        
        stat = file_path.stat()
        file_info = {
            "name": filename,
            "path": str(file_path),
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "extension": file_path.suffix.lower(),
            "type": self._get_file_type(file_path.suffix)
        }
        
        # Read preview based on file type
        try:
            if file_path.suffix.lower() in ['.json']:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    file_info["preview"] = json.dumps(data, indent=2)[:5000]  # First 5000 chars
                    file_info["preview_type"] = "json"
            elif file_path.suffix.lower() == '.csv':
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()[:max_lines]
                    file_info["preview"] = ''.join(lines)
                    file_info["preview_type"] = "csv"
            elif file_path.suffix.lower() in ['.txt', '.xml']:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()[:max_lines]
                    file_info["preview"] = ''.join(lines)
                    file_info["preview_type"] = "text"
            elif file_path.suffix.lower() == '.pdf':
                file_info["preview"] = "[PDF file - use PDF viewer]"
                file_info["preview_type"] = "pdf"
                file_info["file_path"] = str(file_path)  # Include file path for PDF viewer
            else:
                # Try to read as text
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()[:max_lines]
                        file_info["preview"] = ''.join(lines)
                        file_info["preview_type"] = "text"
                except:
                    file_info["preview"] = f"[Binary file: {file_path.suffix}]"
                    file_info["preview_type"] = "binary"
        except Exception as e:
            logger.warning(f"Failed to read file preview: {e}")
            file_info["preview"] = f"[Error reading file: {str(e)}]"
            file_info["preview_type"] = "error"
        
        return file_info
    
    def _get_file_type(self, extension: str) -> str:
        """Get file type from extension"""
        extension = extension.lower()
        type_map = {
            '.json': 'json',
            '.csv': 'csv',
            '.txt': 'text',
            '.xml': 'xml',
            '.pdf': 'pdf',
            '.docx': 'document',
            '.xlsx': 'spreadsheet',
            '.xls': 'spreadsheet',
        }
        return type_map.get(extension, 'unknown')
