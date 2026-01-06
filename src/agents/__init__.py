"""Agentic components"""

from .base_agent import BaseAgent
from .data_ingestion_agent import DataIngestionAgent
from .ontology_agent import OntologyAgent
from .graph_construction_agent import GraphConstructionAgent
from .query_agent import QueryAgent

__all__ = [
    "BaseAgent",
    "DataIngestionAgent",
    "OntologyAgent",
    "GraphConstructionAgent",
    "QueryAgent"
]

