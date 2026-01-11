"""ODL Intermediate Representation (IR)."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class PropertyIR:
    """Normalized property representation."""
    name: str
    type: str
    description: Optional[str] = None
    nullable: bool = True
    required: bool = False


@dataclass
class ObjectIR:
    """Normalized object representation."""
    name: str
    description: Optional[str] = None
    identifiers: List[str] = field(default_factory=list)
    properties: List[PropertyIR] = field(default_factory=list)
    snowflake_table: Optional[str] = None
    snowflake_schema: Optional[str] = None
    snowflake_database: Optional[str] = None


@dataclass
class RelationshipIR:
    """Normalized relationship representation."""
    name: str
    from_object: str
    to_object: str
    join_keys: List[tuple] = field(default_factory=list)  # List of (from_property, to_property) tuples
    cardinality: str = "many_to_one"
    description: Optional[str] = None


@dataclass
class MetricIR:
    """Normalized metric representation."""
    name: str
    expression: str
    grain: List[str] = field(default_factory=list)
    type: str = "custom"
    format: Optional[str] = None
    description: Optional[str] = None


@dataclass
class DimensionIR:
    """Normalized dimension representation."""
    name: str
    source_property: str  # Format: "Object.property"
    type: str = "categorical"
    description: Optional[str] = None


@dataclass
class SnowflakeMappingIR:
    """Normalized Snowflake mapping representation."""
    database: str
    schema: str
    warehouse: Optional[str] = None
    table_mappings: Dict[str, str] = field(default_factory=dict)  # object_name -> table_name


@dataclass
class ODLIR:
    """Normalized ODL Intermediate Representation."""
    version: str
    name: Optional[str] = None
    description: Optional[str] = None
    objects: List[ObjectIR] = field(default_factory=list)
    relationships: List[RelationshipIR] = field(default_factory=list)
    metrics: List[MetricIR] = field(default_factory=list)
    dimensions: List[DimensionIR] = field(default_factory=list)
    snowflake: Optional[SnowflakeMappingIR] = None
