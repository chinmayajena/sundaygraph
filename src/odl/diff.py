"""ODL diff engine - compares two ODL versions and identifies breaking/non-breaking changes."""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

from .ir import ODLIR, ObjectIR, RelationshipIR, MetricIR, DimensionIR, PropertyIR


class ChangeType(Enum):
    """Type of change."""
    BREAKING = "breaking"
    NON_BREAKING = "non_breaking"


class ChangeCategory(Enum):
    """Category of change."""
    OBJECT_ADDED = "object_added"
    OBJECT_REMOVED = "object_removed"
    OBJECT_RENAMED = "object_renamed"
    OBJECT_DESCRIPTION_CHANGED = "object_description_changed"
    
    IDENTIFIER_CHANGED = "identifier_changed"
    IDENTIFIER_ADDED = "identifier_added"
    IDENTIFIER_REMOVED = "identifier_removed"
    
    PROPERTY_ADDED = "property_added"
    PROPERTY_REMOVED = "property_removed"
    PROPERTY_TYPE_CHANGED = "property_type_changed"
    PROPERTY_DESCRIPTION_CHANGED = "property_description_changed"
    
    RELATIONSHIP_ADDED = "relationship_added"
    RELATIONSHIP_REMOVED = "relationship_removed"
    RELATIONSHIP_JOIN_KEYS_CHANGED = "relationship_join_keys_changed"
    RELATIONSHIP_CARDINALITY_TIGHTENED = "relationship_cardinality_tightened"
    RELATIONSHIP_CARDINALITY_RELAXED = "relationship_cardinality_relaxed"
    RELATIONSHIP_DESCRIPTION_CHANGED = "relationship_description_changed"
    
    METRIC_ADDED = "metric_added"
    METRIC_REMOVED = "metric_removed"
    METRIC_EXPRESSION_CHANGED = "metric_expression_changed"
    METRIC_GRAIN_CHANGED = "metric_grain_changed"
    METRIC_DESCRIPTION_CHANGED = "metric_description_changed"
    
    DIMENSION_ADDED = "dimension_added"
    DIMENSION_REMOVED = "dimension_removed"
    DIMENSION_DESCRIPTION_CHANGED = "dimension_description_changed"


@dataclass
class Change:
    """Represents a single change."""
    category: ChangeCategory
    change_type: ChangeType
    element_name: str
    old_value: Any = None
    new_value: Any = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "category": self.category.value,
            "change_type": self.change_type.value,
            "element_name": self.element_name,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "details": self.details
        }


@dataclass
class DiffResult:
    """Result of comparing two ODL versions."""
    old_version: str
    new_version: str
    breaking_changes: List[Change] = field(default_factory=list)
    non_breaking_changes: List[Change] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "old_version": self.old_version,
            "new_version": self.new_version,
            "breaking_changes": [c.to_dict() for c in self.breaking_changes],
            "non_breaking_changes": [c.to_dict() for c in self.non_breaking_changes],
            "summary": {
                "total_breaking": len(self.breaking_changes),
                "total_non_breaking": len(self.non_breaking_changes),
                "total_changes": len(self.breaking_changes) + len(self.non_breaking_changes)
            }
        }


class ODLDiffEngine:
    """Engine for comparing ODL versions."""
    
    def diff(self, old_ir: ODLIR, new_ir: ODLIR) -> DiffResult:
        """
        Compare two ODL IRs and generate diff.
        
        Args:
            old_ir: Old ODL IR
            new_ir: New ODL IR
            
        Returns:
            DiffResult with breaking and non-breaking changes
        """
        result = DiffResult(
            old_version=old_ir.version,
            new_version=new_ir.version
        )
        
        # Compare objects
        self._diff_objects(old_ir, new_ir, result)
        
        # Compare relationships
        self._diff_relationships(old_ir, new_ir, result)
        
        # Compare metrics
        self._diff_metrics(old_ir, new_ir, result)
        
        # Compare dimensions
        self._diff_dimensions(old_ir, new_ir, result)
        
        # Calculate summary
        result.summary = {
            "total_breaking": len(result.breaking_changes),
            "total_non_breaking": len(result.non_breaking_changes),
            "total_changes": len(result.breaking_changes) + len(result.non_breaking_changes)
        }
        
        return result
    
    def _diff_objects(self, old_ir: ODLIR, new_ir: ODLIR, result: DiffResult):
        """Compare objects between two ODL IRs."""
        old_objects = {obj.name: obj for obj in old_ir.objects}
        new_objects = {obj.name: obj for obj in new_ir.objects}
        
        # Find added objects (non-breaking)
        for name, obj in new_objects.items():
            if name not in old_objects:
                result.non_breaking_changes.append(Change(
                    category=ChangeCategory.OBJECT_ADDED,
                    change_type=ChangeType.NON_BREAKING,
                    element_name=name,
                    new_value=obj.name
                ))
        
        # Find removed objects (breaking)
        for name, obj in old_objects.items():
            if name not in new_objects:
                result.breaking_changes.append(Change(
                    category=ChangeCategory.OBJECT_REMOVED,
                    change_type=ChangeType.BREAKING,
                    element_name=name,
                    old_value=name
                ))
        
        # Compare existing objects
        for name in set(old_objects.keys()) & set(new_objects.keys()):
            old_obj = old_objects[name]
            new_obj = new_objects[name]
            self._diff_object_details(old_obj, new_obj, result)
    
    def _diff_object_details(self, old_obj: ObjectIR, new_obj: ObjectIR, result: DiffResult):
        """Compare details of a single object."""
        # Description changes (non-breaking)
        if old_obj.description != new_obj.description:
            result.non_breaking_changes.append(Change(
                category=ChangeCategory.OBJECT_DESCRIPTION_CHANGED,
                change_type=ChangeType.NON_BREAKING,
                element_name=old_obj.name,
                old_value=old_obj.description,
                new_value=new_obj.description
            ))
        
        # Identifier changes (breaking)
        old_identifiers = set(old_obj.identifiers)
        new_identifiers = set(new_obj.identifiers)
        
        if old_identifiers != new_identifiers:
            removed = old_identifiers - new_identifiers
            added = new_identifiers - old_identifiers
            
            if removed:
                result.breaking_changes.append(Change(
                    category=ChangeCategory.IDENTIFIER_REMOVED,
                    change_type=ChangeType.BREAKING,
                    element_name=old_obj.name,
                    old_value=list(removed),
                    details={"removed_identifiers": list(removed)}
                ))
            
            if added:
                # Adding identifiers is non-breaking if old ones still exist
                if old_identifiers & new_identifiers:
                    result.non_breaking_changes.append(Change(
                        category=ChangeCategory.IDENTIFIER_ADDED,
                        change_type=ChangeType.NON_BREAKING,
                        element_name=old_obj.name,
                        new_value=list(added),
                        details={"added_identifiers": list(added)}
                    ))
                else:
                    # Complete replacement is breaking
                    result.breaking_changes.append(Change(
                        category=ChangeCategory.IDENTIFIER_CHANGED,
                        change_type=ChangeType.BREAKING,
                        element_name=old_obj.name,
                        old_value=list(old_identifiers),
                        new_value=list(new_identifiers)
                    ))
        
        # Property changes
        self._diff_properties(old_obj, new_obj, result)
    
    def _diff_properties(self, old_obj: ObjectIR, new_obj: ObjectIR, result: DiffResult):
        """Compare properties of an object."""
        old_props = {prop.name: prop for prop in old_obj.properties}
        new_props = {prop.name: prop for prop in new_obj.properties}
        
        # Added properties (non-breaking)
        for name, prop in new_props.items():
            if name not in old_props:
                result.non_breaking_changes.append(Change(
                    category=ChangeCategory.PROPERTY_ADDED,
                    change_type=ChangeType.NON_BREAKING,
                    element_name=f"{old_obj.name}.{name}",
                    new_value=prop.name
                ))
        
        # Removed properties (breaking)
        for name, prop in old_props.items():
            if name not in new_props:
                result.breaking_changes.append(Change(
                    category=ChangeCategory.PROPERTY_REMOVED,
                    change_type=ChangeType.BREAKING,
                    element_name=f"{old_obj.name}.{name}",
                    old_value=prop.name
                ))
        
        # Changed properties
        for name in set(old_props.keys()) & set(new_props.keys()):
            old_prop = old_props[name]
            new_prop = new_props[name]
            
            # Type changes (breaking)
            if old_prop.type != new_prop.type:
                result.breaking_changes.append(Change(
                    category=ChangeCategory.PROPERTY_TYPE_CHANGED,
                    change_type=ChangeType.BREAKING,
                    element_name=f"{old_obj.name}.{name}",
                    old_value=old_prop.type,
                    new_value=new_prop.type
                ))
            
            # Description changes (non-breaking)
            if old_prop.description != new_prop.description:
                result.non_breaking_changes.append(Change(
                    category=ChangeCategory.PROPERTY_DESCRIPTION_CHANGED,
                    change_type=ChangeType.NON_BREAKING,
                    element_name=f"{old_obj.name}.{name}",
                    old_value=old_prop.description,
                    new_value=new_prop.description
                ))
    
    def _diff_relationships(self, old_ir: ODLIR, new_ir: ODLIR, result: DiffResult):
        """Compare relationships between two ODL IRs."""
        old_rels = {rel.name: rel for rel in old_ir.relationships}
        new_rels = {rel.name: rel for rel in new_ir.relationships}
        
        # Added relationships (non-breaking)
        for name, rel in new_rels.items():
            if name not in old_rels:
                result.non_breaking_changes.append(Change(
                    category=ChangeCategory.RELATIONSHIP_ADDED,
                    change_type=ChangeType.NON_BREAKING,
                    element_name=name,
                    new_value=name
                ))
        
        # Removed relationships (breaking)
        for name, rel in old_rels.items():
            if name not in new_rels:
                result.breaking_changes.append(Change(
                    category=ChangeCategory.RELATIONSHIP_REMOVED,
                    change_type=ChangeType.BREAKING,
                    element_name=name,
                    old_value=name
                ))
        
        # Compare existing relationships
        for name in set(old_rels.keys()) & set(new_rels.keys()):
            old_rel = old_rels[name]
            new_rel = new_rels[name]
            
            # Join keys changes (breaking)
            old_join_keys = set(old_rel.join_keys)
            new_join_keys = set(new_rel.join_keys)
            
            if old_join_keys != new_join_keys:
                result.breaking_changes.append(Change(
                    category=ChangeCategory.RELATIONSHIP_JOIN_KEYS_CHANGED,
                    change_type=ChangeType.BREAKING,
                    element_name=name,
                    old_value=list(old_join_keys),
                    new_value=list(new_join_keys)
                ))
            
            # Cardinality changes
            cardinality_order = {
                "many_to_many": 0,
                "many_to_one": 1,
                "one_to_many": 1,
                "one_to_one": 2
            }
            
            old_card = cardinality_order.get(old_rel.cardinality, 0)
            new_card = cardinality_order.get(new_rel.cardinality, 0)
            
            if old_card < new_card:
                # Tightened (breaking)
                result.breaking_changes.append(Change(
                    category=ChangeCategory.RELATIONSHIP_CARDINALITY_TIGHTENED,
                    change_type=ChangeType.BREAKING,
                    element_name=name,
                    old_value=old_rel.cardinality,
                    new_value=new_rel.cardinality
                ))
            elif old_card > new_card:
                # Relaxed (non-breaking)
                result.non_breaking_changes.append(Change(
                    category=ChangeCategory.RELATIONSHIP_CARDINALITY_RELAXED,
                    change_type=ChangeType.NON_BREAKING,
                    element_name=name,
                    old_value=old_rel.cardinality,
                    new_value=new_rel.cardinality
                ))
            
            # Description changes (non-breaking)
            if old_rel.description != new_rel.description:
                result.non_breaking_changes.append(Change(
                    category=ChangeCategory.RELATIONSHIP_DESCRIPTION_CHANGED,
                    change_type=ChangeType.NON_BREAKING,
                    element_name=name,
                    old_value=old_rel.description,
                    new_value=new_rel.description
                ))
    
    def _diff_metrics(self, old_ir: ODLIR, new_ir: ODLIR, result: DiffResult):
        """Compare metrics between two ODL IRs."""
        old_metrics = {m.name: m for m in old_ir.metrics}
        new_metrics = {m.name: m for m in new_ir.metrics}
        
        # Added metrics (non-breaking)
        for name, metric in new_metrics.items():
            if name not in old_metrics:
                result.non_breaking_changes.append(Change(
                    category=ChangeCategory.METRIC_ADDED,
                    change_type=ChangeType.NON_BREAKING,
                    element_name=name,
                    new_value=name
                ))
        
        # Removed metrics (breaking)
        for name, metric in old_metrics.items():
            if name not in new_metrics:
                result.breaking_changes.append(Change(
                    category=ChangeCategory.METRIC_REMOVED,
                    change_type=ChangeType.BREAKING,
                    element_name=name,
                    old_value=name
                ))
        
        # Compare existing metrics
        for name in set(old_metrics.keys()) & set(new_metrics.keys()):
            old_metric = old_metrics[name]
            new_metric = new_metrics[name]
            
            # Expression changes (breaking)
            if old_metric.expression != new_metric.expression:
                result.breaking_changes.append(Change(
                    category=ChangeCategory.METRIC_EXPRESSION_CHANGED,
                    change_type=ChangeType.BREAKING,
                    element_name=name,
                    old_value=old_metric.expression,
                    new_value=new_metric.expression
                ))
            
            # Grain changes (breaking)
            if set(old_metric.grain) != set(new_metric.grain):
                result.breaking_changes.append(Change(
                    category=ChangeCategory.METRIC_GRAIN_CHANGED,
                    change_type=ChangeType.BREAKING,
                    element_name=name,
                    old_value=old_metric.grain,
                    new_value=new_metric.grain
                ))
            
            # Description changes (non-breaking)
            if old_metric.description != new_metric.description:
                result.non_breaking_changes.append(Change(
                    category=ChangeCategory.METRIC_DESCRIPTION_CHANGED,
                    change_type=ChangeType.NON_BREAKING,
                    element_name=name,
                    old_value=old_metric.description,
                    new_value=new_metric.description
                ))
    
    def _diff_dimensions(self, old_ir: ODLIR, new_ir: ODLIR, result: DiffResult):
        """Compare dimensions between two ODL IRs."""
        old_dims = {d.name: d for d in old_ir.dimensions}
        new_dims = {d.name: d for d in new_ir.dimensions}
        
        # Added dimensions (non-breaking)
        for name, dim in new_dims.items():
            if name not in old_dims:
                result.non_breaking_changes.append(Change(
                    category=ChangeCategory.DIMENSION_ADDED,
                    change_type=ChangeType.NON_BREAKING,
                    element_name=name,
                    new_value=name
                ))
        
        # Removed dimensions (breaking)
        for name, dim in old_dims.items():
            if name not in new_dims:
                result.breaking_changes.append(Change(
                    category=ChangeCategory.DIMENSION_REMOVED,
                    change_type=ChangeType.BREAKING,
                    element_name=name,
                    old_value=name
                ))
        
        # Compare existing dimensions (only description changes are non-breaking)
        for name in set(old_dims.keys()) & set(new_dims.keys()):
            old_dim = old_dims[name]
            new_dim = new_dims[name]
            
            # Source property changes (breaking)
            if old_dim.source_property != new_dim.source_property:
                result.breaking_changes.append(Change(
                    category=ChangeCategory.DIMENSION_REMOVED,  # Treat as removal + addition
                    change_type=ChangeType.BREAKING,
                    element_name=name,
                    old_value=old_dim.source_property,
                    new_value=new_dim.source_property,
                    details={"source_property_changed": True}
                ))
            
            # Description changes (non-breaking)
            if old_dim.description != new_dim.description:
                result.non_breaking_changes.append(Change(
                    category=ChangeCategory.DIMENSION_DESCRIPTION_CHANGED,
                    change_type=ChangeType.NON_BREAKING,
                    element_name=name,
                    old_value=old_dim.description,
                    new_value=new_dim.description
                ))
