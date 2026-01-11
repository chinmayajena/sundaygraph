"""Compiler interface for ODL to target system compilation."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
import hashlib
import json

from ..odl.ir import ODLIR


@dataclass
class ArtifactFile:
    """A single file in the artifact bundle."""
    path: str
    content: str


@dataclass
class ArtifactBundle:
    """Bundle of compiled artifacts with metadata."""
    files: List[ArtifactFile] = field(default_factory=list)
    instructions_md: str = ""
    rollback_md: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate and ensure required files exist."""
        # Ensure instructions.md exists
        if not any(f.path == "instructions.md" for f in self.files):
            self.files.append(ArtifactFile(
                path="instructions.md",
                content=self.instructions_md
            ))
        
        # Ensure rollback.md exists
        if not any(f.path == "rollback.md" for f in self.files):
            self.files.append(ArtifactFile(
                path="rollback.md",
                content=self.rollback_md
            ))
        
        # Ensure metadata.json exists
        if not any(f.path == "metadata.json" for f in self.files):
            metadata_content = json.dumps(self.metadata, indent=2)
            self.files.append(ArtifactFile(
                path="metadata.json",
                content=metadata_content
            ))
    
    def get_file(self, path: str) -> Optional[ArtifactFile]:
        """Get a file by path."""
        for f in self.files:
            if f.path == path:
                return f
        return None
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get metadata from metadata.json file."""
        metadata_file = self.get_file("metadata.json")
        if metadata_file:
            return json.loads(metadata_file.content)
        return self.metadata
    
    def calculate_checksum(self) -> str:
        """Calculate checksum of all files."""
        # Sort files by path for consistent checksum
        sorted_files = sorted(self.files, key=lambda f: f.path)
        content = "\n".join(f"{f.path}:{f.content}" for f in sorted_files)
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def validate_structure(self) -> List[str]:
        """
        Validate artifact bundle structure.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check required files
        required_files = ["instructions.md", "rollback.md", "metadata.json"]
        for required_file in required_files:
            if not any(f.path == required_file for f in self.files):
                errors.append(f"Missing required file: {required_file}")
        
        # Validate metadata.json structure
        metadata_file = self.get_file("metadata.json")
        if metadata_file:
            try:
                metadata = json.loads(metadata_file.content)
                required_fields = ["target", "timestamp", "version_id", "checksum"]
                for field in required_fields:
                    if field not in metadata:
                        errors.append(f"Missing required metadata field: {field}")
            except json.JSONDecodeError as e:
                errors.append(f"Invalid JSON in metadata.json: {e}")
        
        return errors


class Compiler(ABC):
    """Abstract compiler interface for ODL to target system compilation."""
    
    @abstractmethod
    def compile(
        self,
        odl_ir: ODLIR,
        options: Optional[Dict[str, Any]] = None
    ) -> ArtifactBundle:
        """
        Compile ODL IR to target system artifacts.
        
        Args:
            odl_ir: Normalized ODL intermediate representation
            options: Compilation options (target-specific)
            
        Returns:
            ArtifactBundle with compiled files and metadata
        """
        pass
    
    @abstractmethod
    def get_target(self) -> str:
        """
        Get the target system name.
        
        Returns:
            Target system identifier (e.g., "SNOWFLAKE", "MOCK")
        """
        pass
    
    def _create_metadata(
        self,
        version_id: Optional[str] = None,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create standard metadata for artifact bundle.
        
        Args:
            version_id: Optional version identifier
            additional_metadata: Additional metadata to include
            
        Returns:
            Metadata dictionary
        """
        metadata = {
            "target": self.get_target(),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "version_id": version_id or "unknown",
            "checksum": ""  # Will be calculated after bundle creation
        }
        
        if additional_metadata:
            metadata.update(additional_metadata)
        
        return metadata
    
    def _create_instructions(
        self,
        steps: List[str],
        prerequisites: Optional[List[str]] = None
    ) -> str:
        """
        Create instructions.md content.
        
        Args:
            steps: List of application steps
            prerequisites: Optional prerequisites
            
        Returns:
            Markdown content for instructions.md
        """
        lines = ["# Deployment Instructions", ""]
        
        if prerequisites:
            lines.append("## Prerequisites")
            lines.append("")
            for prereq in prerequisites:
                lines.append(f"- {prereq}")
            lines.append("")
        
        lines.append("## Apply Steps")
        lines.append("")
        for i, step in enumerate(steps, 1):
            lines.append(f"{i}. {step}")
        
        return "\n".join(lines)
    
    def _create_rollback(
        self,
        steps: List[str]
    ) -> str:
        """
        Create rollback.md content.
        
        Args:
            steps: List of rollback steps
            
        Returns:
            Markdown content for rollback.md
        """
        lines = ["# Rollback Instructions", ""]
        lines.append("## Rollback Steps")
        lines.append("")
        for i, step in enumerate(steps, 1):
            lines.append(f"{i}. {step}")
        
        return "\n".join(lines)
