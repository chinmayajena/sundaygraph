"""Configuration management for SundayGraph"""

import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class SystemConfig(BaseModel):
    """System configuration"""
    name: str = "sundaygraph"
    version: str = "1.0.0"
    log_level: str = "INFO"
    log_file: str = "logs/sundaygraph.log"


class DataConfig(BaseModel):
    """Data processing configuration"""
    input_dir: str = "./data/input"
    output_dir: str = "./data/output"
    cache_dir: str = "./data/cache"
    supported_formats: list[str] = Field(default_factory=lambda: ["json", "csv", "txt", "xml", "pdf", "docx"])
    max_file_size_mb: int = 100


class OntologyConfig(BaseModel):
    """Ontology configuration"""
    schema_path: str = "./config/ontology_schema.yaml"
    auto_validate: bool = True
    strict_mode: bool = False
    allow_custom_properties: bool = True


class Neo4jConfig(BaseModel):
    """Neo4j database configuration"""
    uri: str = "bolt://localhost:7687"
    user: str = "neo4j"
    password: str = "password"
    database: str = "neo4j"
    max_connection_lifetime: int = 3600
    max_connection_pool_size: int = 50


class MemoryGraphConfig(BaseModel):
    """In-memory graph configuration"""
    directed: bool = True
    multigraph: bool = False


class GraphConfig(BaseModel):
    """Graph storage configuration"""
    backend: str = "memory"  # "memory" or "neo4j"
    memory: MemoryGraphConfig = Field(default_factory=MemoryGraphConfig)
    neo4j: Neo4jConfig = Field(default_factory=Neo4jConfig)


class AgentConfig(BaseModel):
    """Base agent configuration"""
    enabled: bool = True


class DataIngestionAgentConfig(AgentConfig):
    """Data ingestion agent configuration"""
    batch_size: int = 100
    max_workers: int = 4
    chunk_size: int = 1000
    overlap: int = 200
    extract_entities: bool = True
    extract_relations: bool = True


class OntologyAgentConfig(AgentConfig):
    """Ontology agent configuration"""
    strict_mode: bool = False
    auto_map_properties: bool = True
    validation_level: str = "medium"  # "strict", "medium", "loose"


class GraphConstructionAgentConfig(AgentConfig):
    """Graph construction agent configuration"""
    batch_insert_size: int = 1000
    create_indexes: bool = True
    deduplicate_entities: bool = True
    merge_relations: bool = True


class QueryAgentConfig(AgentConfig):
    """Query agent configuration"""
    max_results: int = 100
    similarity_threshold: float = 0.7
    use_semantic_search: bool = True


class AgentsConfig(BaseModel):
    """All agents configuration"""
    data_ingestion: DataIngestionAgentConfig = Field(default_factory=DataIngestionAgentConfig)
    ontology: OntologyAgentConfig = Field(default_factory=OntologyAgentConfig)
    graph_construction: GraphConstructionAgentConfig = Field(default_factory=GraphConstructionAgentConfig)
    query: QueryAgentConfig = Field(default_factory=QueryAgentConfig)


class NLPConfig(BaseModel):
    """NLP processing configuration"""
    model: str = "en_core_web_sm"
    use_gpu: bool = False
    batch_size: int = 32


class EmbeddingConfig(BaseModel):
    """Embedding configuration"""
    model: str = "sentence-transformers/all-MiniLM-L6-v2"
    dimension: int = 384
    device: str = "cpu"


class LLMConfig(BaseModel):
    """LLM configuration"""
    provider: str = "openai"  # "openai", "anthropic", "local"
    model: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 2000


class ProcessingConfig(BaseModel):
    """Processing configuration"""
    nlp: NLPConfig = Field(default_factory=NLPConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)


class StorageConfig(BaseModel):
    """Storage configuration"""
    persist_graph: bool = True
    graph_file: str = "./data/graph.pkl"
    backup_enabled: bool = True
    backup_interval_hours: int = 24


class Config(BaseSettings):
    """Main configuration class"""
    system: SystemConfig = Field(default_factory=SystemConfig)
    data: DataConfig = Field(default_factory=DataConfig)
    ontology: OntologyConfig = Field(default_factory=OntologyConfig)
    graph: GraphConfig = Field(default_factory=GraphConfig)
    agents: AgentsConfig = Field(default_factory=AgentsConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)

    @classmethod
    def from_yaml(cls, config_path: str | Path) -> "Config":
        """Load configuration from YAML file"""
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, "r", encoding="utf-8") as f:
            config_dict = yaml.safe_load(f)
        
        return cls(**config_dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return self.model_dump()
    
    def save_yaml(self, output_path: str | Path) -> None:
        """Save configuration to YAML file"""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, sort_keys=False)

