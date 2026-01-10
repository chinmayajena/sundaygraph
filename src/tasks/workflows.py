"""Temporal workflows for ingestion tasks"""

from temporalio import workflow
from temporalio.common import RetryPolicy
from typing import Dict, Any, Optional
from loguru import logger


@workflow.defn
class IngestDataWorkflow:
    """Temporal workflow for data ingestion"""
    
    @workflow.run
    async def run(
        self,
        config_path: Optional[str],
        input_path: str,
        workspace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute ingestion workflow
        
        Args:
            config_path: Path to config file
            input_path: Path to data file/directory
            workspace_id: Optional workspace ID
            
        Returns:
            Ingestion result
        """
        from pathlib import Path
        from ..core.sundaygraph import SundayGraph
        
        # Update workflow state
        workflow.logger.info(f"Starting ingestion: {input_path}")
        
        # Initialize SundayGraph
        sg = SundayGraph(config_path=Path(config_path) if config_path else None)
        
        # Execute ingestion
        result = await sg.ingest_data(input_path, workspace_id)
        
        workflow.logger.info(f"Ingestion complete: {result.get('entities_added', 0)} entities")
        
        return result


@workflow.defn
class BuildOntologyWorkflow:
    """Temporal workflow for ontology building"""
    
    @workflow.run
    async def run(
        self,
        config_path: Optional[str],
        domain_description: str
    ) -> Dict[str, Any]:
        """
        Execute ontology building workflow
        
        Args:
            config_path: Path to config file
            domain_description: Domain description text
            
        Returns:
            Schema building result
        """
        from pathlib import Path
        from ..core.sundaygraph import SundayGraph
        
        workflow.logger.info("Starting ontology building")
        
        # Initialize SundayGraph
        sg = SundayGraph(config_path=Path(config_path) if config_path else None)
        
        # Build schema
        result = await sg.build_schema_from_domain(domain_description)
        
        workflow.logger.info(f"Ontology built: {result.get('entities', 0)} entities")
        
        return result


# Export workflow functions for Temporal
ingest_data_workflow = IngestDataWorkflow.run
build_ontology_workflow = BuildOntologyWorkflow.run
