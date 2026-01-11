"""ODL normalizer - converts ODL to stable internal representation."""

from typing import Dict, Any, List

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from .ir import (
    ODLIR, ObjectIR, PropertyIR, RelationshipIR, MetricIR, DimensionIR,
    SnowflakeMappingIR
)


class ODLNormalizer:
    """Normalizes ODL to stable internal representation."""
    
    def normalize(self, odl_data: Dict[str, Any]) -> ODLIR:
        """
        Normalize ODL data to internal representation.
        
        Args:
            odl_data: ODL dictionary
            
        Returns:
            Normalized ODLIR
        """
        logger.info("Normalizing ODL to internal representation")
        
        # Normalize objects (sorted by name)
        objects = self._normalize_objects(odl_data.get("objects", []))
        objects.sort(key=lambda o: o.name)
        
        # Normalize relationships (sorted by name)
        relationships = self._normalize_relationships(odl_data.get("relationships", []))
        relationships.sort(key=lambda r: r.name)
        
        # Normalize metrics (sorted by name)
        metrics = self._normalize_metrics(odl_data.get("metrics", []))
        metrics.sort(key=lambda m: m.name)
        
        # Normalize dimensions (sorted by name)
        dimensions = self._normalize_dimensions(odl_data.get("dimensions", []))
        dimensions.sort(key=lambda d: d.name)
        
        # Normalize Snowflake mapping
        snowflake = None
        if "snowflake" in odl_data:
            snowflake = self._normalize_snowflake_mapping(
                odl_data["snowflake"],
                objects
            )
        
        ir = ODLIR(
            version=odl_data.get("version", "1.0.0"),
            name=odl_data.get("name"),
            description=odl_data.get("description"),
            objects=objects,
            relationships=relationships,
            metrics=metrics,
            dimensions=dimensions,
            snowflake=snowflake
        )
        
        logger.info(f"Normalized ODL: {len(objects)} objects, {len(relationships)} relationships, "
                   f"{len(metrics)} metrics, {len(dimensions)} dimensions")
        
        return ir
    
    def _normalize_objects(self, objects: List[Dict[str, Any]]) -> List[ObjectIR]:
        """Normalize objects."""
        normalized = []
        
        for obj in objects:
            # Normalize properties (sorted by name)
            properties = self._normalize_properties(obj.get("properties", []))
            properties.sort(key=lambda p: p.name)
            
            # Get Snowflake mapping
            snowflake_obj = obj.get("snowflake", {})
            
            normalized_obj = ObjectIR(
                name=obj["name"],
                description=obj.get("description"),
                identifiers=sorted(obj.get("identifiers", [])),  # Sorted
                properties=properties,
                snowflake_table=snowflake_obj.get("table"),
                snowflake_schema=snowflake_obj.get("schema"),
                snowflake_database=snowflake_obj.get("database")
            )
            normalized.append(normalized_obj)
        
        return normalized
    
    def _normalize_properties(self, properties: List[Dict[str, Any]]) -> List[PropertyIR]:
        """Normalize properties."""
        normalized = []
        
        for prop in properties:
            normalized_prop = PropertyIR(
                name=prop["name"],
                type=prop["type"],
                description=prop.get("description"),
                nullable=prop.get("nullable", True),
                required=prop.get("required", False)
            )
            normalized.append(normalized_prop)
        
        return normalized
    
    def _normalize_relationships(self, relationships: List[Dict[str, Any]]) -> List[RelationshipIR]:
        """Normalize relationships."""
        normalized = []
        
        for rel in relationships:
            # Normalize join keys to tuples (sorted)
            join_keys = [
                tuple(pair) if isinstance(pair, list) and len(pair) == 2 else tuple(pair)
                for pair in rel.get("joinKeys", [])
            ]
            join_keys.sort()  # Sort for stability
            
            normalized_rel = RelationshipIR(
                name=rel["name"],
                from_object=rel["from"],
                to_object=rel["to"],
                join_keys=join_keys,
                cardinality=rel.get("cardinality", "many_to_one"),
                description=rel.get("description")
            )
            normalized.append(normalized_rel)
        
        return normalized
    
    def _normalize_metrics(self, metrics: List[Dict[str, Any]]) -> List[MetricIR]:
        """Normalize metrics."""
        normalized = []
        
        for metric in metrics:
            # Normalize grain (sorted)
            grain = sorted(metric.get("grain", []))
            
            normalized_metric = MetricIR(
                name=metric["name"],
                expression=metric["expression"],
                grain=grain,
                type=metric.get("type", "custom"),
                format=metric.get("format"),
                description=metric.get("description")
            )
            normalized.append(normalized_metric)
        
        return normalized
    
    def _normalize_dimensions(self, dimensions: List[Dict[str, Any]]) -> List[DimensionIR]:
        """Normalize dimensions."""
        normalized = []
        
        for dim in dimensions:
            normalized_dim = DimensionIR(
                name=dim["name"],
                source_property=dim["sourceProperty"],
                type=dim.get("type", "categorical"),
                description=dim.get("description")
            )
            normalized.append(normalized_dim)
        
        return normalized
    
    def _normalize_snowflake_mapping(
        self,
        snowflake: Dict[str, Any],
        objects: List[ObjectIR]
    ) -> SnowflakeMappingIR:
        """Normalize Snowflake mapping."""
        # Build table mappings from objects if not explicitly provided
        table_mappings = snowflake.get("tableMappings", {}).copy()
        
        # Add per-object table mappings
        for obj in objects:
            if obj.snowflake_table and obj.name not in table_mappings:
                table_mappings[obj.name] = obj.snowflake_table
        
        # Sort table mappings for stability
        sorted_mappings = dict(sorted(table_mappings.items()))
        
        return SnowflakeMappingIR(
            database=snowflake["database"],
            schema=snowflake["schema"],
            warehouse=snowflake.get("warehouse"),
            table_mappings=sorted_mappings
        )
