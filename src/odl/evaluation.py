"""ODL evaluation gates - structural, semantic, and deployability checks."""

from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .ir import ODLIR, ObjectIR, RelationshipIR, MetricIR, DimensionIR


class GateCategory(Enum):
    """Evaluation gate category."""
    STRUCTURAL = "structural"
    SEMANTIC = "semantic"
    DEPLOYABILITY = "deployability"


class GateStatus(Enum):
    """Gate evaluation status."""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    SKIP = "skip"


@dataclass
class GateResult:
    """Result of a single gate evaluation."""
    gate_name: str
    category: GateCategory
    status: GateStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "gate_name": self.gate_name,
            "category": self.category.value,
            "status": self.status.value,
            "message": self.message,
            "details": self.details
        }


@dataclass
class EvaluationResult:
    """Result of full evaluation."""
    version_id: int
    threshold_profile: str
    overall_pass: bool
    gate_results: List[GateResult] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "version_id": self.version_id,
            "threshold_profile": self.threshold_profile,
            "overall_pass": self.overall_pass,
            "gate_results": [g.to_dict() for g in self.gate_results],
            "metrics": self.metrics
        }


class ThresholdProfile:
    """Threshold profile for evaluation gates."""
    
    STRICT = {
        "structural": {
            "odl_validity": "required",
            "references_resolved": "required",
            "mapping_complete": "required"
        },
        "semantic": {
            "connected_join_graph": "required",
            "no_ambiguous_joins": "required",
            "metric_grains_consistent": "required"
        },
        "deployability": {
            "yaml_verify_passes": "required"
        }
    }
    
    RELAXED = {
        "structural": {
            "odl_validity": "required",
            "references_resolved": "warning",
            "mapping_complete": "warning"
        },
        "semantic": {
            "connected_join_graph": "required",
            "no_ambiguous_joins": "warning",
            "metric_grains_consistent": "required"
        },
        "deployability": {
            "yaml_verify_passes": "required"
        }
    }
    
    @classmethod
    def get_profile(cls, profile_name: str) -> Dict[str, Dict[str, str]]:
        """Get threshold profile by name."""
        profiles = {
            "strict": cls.STRICT,
            "relaxed": cls.RELAXED
        }
        return profiles.get(profile_name.lower(), cls.STRICT)


class ODLEvaluator:
    """Evaluates ODL against gates before deployment."""
    
    def __init__(self, threshold_profile: str = "strict"):
        """
        Initialize evaluator.
        
        Args:
            threshold_profile: Threshold profile name (strict, relaxed)
        """
        self.threshold_profile = ThresholdProfile.get_profile(threshold_profile)
    
    def evaluate(self, odl_ir: ODLIR, version_id: int, odl_json: Optional[Dict[str, Any]] = None) -> EvaluationResult:
        """
        Evaluate ODL against all gates.
        
        Args:
            odl_ir: Normalized ODL IR
            version_id: Version ID
            odl_json: Optional raw ODL JSON for additional checks
            
        Returns:
            EvaluationResult with gate results
        """
        result = EvaluationResult(
            version_id=version_id,
            threshold_profile="strict" if self.threshold_profile == ThresholdProfile.STRICT else "relaxed",
            overall_pass=True,
            gate_results=[]
        )
        
        # Structural gates
        result.gate_results.extend(self._evaluate_structural_gates(odl_ir, odl_json))
        
        # Semantic gates
        result.gate_results.extend(self._evaluate_semantic_gates(odl_ir))
        
        # Deployability gates
        result.gate_results.extend(self._evaluate_deployability_gates(odl_ir))
        
        # Determine overall pass based on threshold profile
        result.overall_pass = self._determine_overall_pass(result.gate_results)
        
        # Calculate metrics
        result.metrics = self._calculate_metrics(result.gate_results)
        
        return result
    
    def _evaluate_structural_gates(self, odl_ir: ODLIR, odl_json: Optional[Dict[str, Any]]) -> List[GateResult]:
        """Evaluate structural gates."""
        results = []
        
        # Gate: ODL Validity (assumed valid if we have IR)
        gate_name = "odl_validity"
        threshold = self.threshold_profile.get("structural", {}).get(gate_name, "required")
        
        if threshold == "skip":
            results.append(GateResult(
                gate_name=gate_name,
                category=GateCategory.STRUCTURAL,
                status=GateStatus.SKIP,
                message="ODL validity check skipped"
            ))
        else:
            # If we have IR, ODL is valid (validation happens before normalization)
            results.append(GateResult(
                gate_name=gate_name,
                category=GateCategory.STRUCTURAL,
                status=GateStatus.PASS,
                message="ODL is valid"
            ))
        
        # Gate: References Resolved
        gate_name = "references_resolved"
        threshold = self.threshold_profile.get("structural", {}).get(gate_name, "required")
        
        if threshold == "skip":
            results.append(GateResult(
                gate_name=gate_name,
                category=GateCategory.STRUCTURAL,
                status=GateStatus.SKIP,
                message="References check skipped"
            ))
        else:
            unresolved = self._check_unresolved_references(odl_ir)
            if unresolved:
                status = GateStatus.FAIL if threshold == "required" else GateStatus.WARNING
                results.append(GateResult(
                    gate_name=gate_name,
                    category=GateCategory.STRUCTURAL,
                    status=status,
                    message=f"Unresolved references: {', '.join(unresolved)}",
                    details={"unresolved_references": unresolved}
                ))
            else:
                results.append(GateResult(
                    gate_name=gate_name,
                    category=GateCategory.STRUCTURAL,
                    status=GateStatus.PASS,
                    message="All references resolved"
                ))
        
        # Gate: Mapping Complete
        gate_name = "mapping_complete"
        threshold = self.threshold_profile.get("structural", {}).get(gate_name, "required")
        
        if threshold == "skip":
            results.append(GateResult(
                gate_name=gate_name,
                category=GateCategory.STRUCTURAL,
                status=GateStatus.SKIP,
                message="Mapping check skipped"
            ))
        else:
            incomplete = self._check_mapping_completeness(odl_ir)
            if incomplete:
                status = GateStatus.FAIL if threshold == "required" else GateStatus.WARNING
                results.append(GateResult(
                    gate_name=gate_name,
                    category=GateCategory.STRUCTURAL,
                    status=status,
                    message=f"Incomplete mappings: {', '.join(incomplete)}",
                    details={"incomplete_mappings": incomplete}
                ))
            else:
                results.append(GateResult(
                    gate_name=gate_name,
                    category=GateCategory.STRUCTURAL,
                    status=GateStatus.PASS,
                    message="All mappings complete"
                ))
        
        return results
    
    def _evaluate_semantic_gates(self, odl_ir: ODLIR) -> List[GateResult]:
        """Evaluate semantic gates."""
        results = []
        
        # Gate: Connected Join Graph
        gate_name = "connected_join_graph"
        threshold = self.threshold_profile.get("semantic", {}).get(gate_name, "required")
        
        if threshold == "skip":
            results.append(GateResult(
                gate_name=gate_name,
                category=GateCategory.SEMANTIC,
                status=GateStatus.SKIP,
                message="Join graph check skipped"
            ))
        else:
            is_connected, disconnected = self._check_connected_join_graph(odl_ir)
            if not is_connected:
                status = GateStatus.FAIL if threshold == "required" else GateStatus.WARNING
                results.append(GateResult(
                    gate_name=gate_name,
                    category=GateCategory.SEMANTIC,
                    status=status,
                    message=f"Disconnected objects: {', '.join(disconnected)}",
                    details={"disconnected_objects": disconnected}
                ))
            else:
                results.append(GateResult(
                    gate_name=gate_name,
                    category=GateCategory.SEMANTIC,
                    status=GateStatus.PASS,
                    message="All objects connected via relationships"
                ))
        
        # Gate: No Ambiguous Join Paths
        gate_name = "no_ambiguous_joins"
        threshold = self.threshold_profile.get("semantic", {}).get(gate_name, "required")
        
        if threshold == "skip":
            results.append(GateResult(
                gate_name=gate_name,
                category=GateCategory.SEMANTIC,
                status=GateStatus.SKIP,
                message="Ambiguous joins check skipped"
            ))
        else:
            ambiguous = self._check_ambiguous_join_paths(odl_ir)
            join_key_mismatches = self._check_relationship_join_keys_mismatch(odl_ir)
            
            if join_key_mismatches:
                status = GateStatus.FAIL if threshold == "required" else GateStatus.WARNING
                results.append(GateResult(
                    gate_name=gate_name,
                    category=GateCategory.SEMANTIC,
                    status=status,
                    message=f"Join key mismatches: {'; '.join(join_key_mismatches)}",
                    details={"join_key_mismatches": join_key_mismatches}
                ))
            elif ambiguous:
                status = GateStatus.FAIL if threshold == "required" else GateStatus.WARNING
                messages = []
                for obj1, obj2, paths in ambiguous:
                    messages.append(f"{obj1}->{obj2}: {len(paths)} paths")
                results.append(GateResult(
                    gate_name=gate_name,
                    category=GateCategory.SEMANTIC,
                    status=status,
                    message=f"Ambiguous join paths: {'; '.join(messages)}",
                    details={"ambiguous_paths": ambiguous}
                ))
            else:
                results.append(GateResult(
                    gate_name=gate_name,
                    category=GateCategory.SEMANTIC,
                    status=GateStatus.PASS,
                    message="No ambiguous join paths and all join keys valid"
                ))
        
        # Gate: Metric Grains Consistent
        gate_name = "metric_grains_consistent"
        threshold = self.threshold_profile.get("semantic", {}).get(gate_name, "required")
        
        if threshold == "skip":
            results.append(GateResult(
                gate_name=gate_name,
                category=GateCategory.SEMANTIC,
                status=GateStatus.SKIP,
                message="Metric grains check skipped"
            ))
        else:
            inconsistent = self._check_metric_grains_consistent(odl_ir)
            if inconsistent:
                status = GateStatus.FAIL if threshold == "required" else GateStatus.WARNING
                messages = []
                for metric, grain, issue in inconsistent:
                    messages.append(f"{metric}: {issue}")
                results.append(GateResult(
                    gate_name=gate_name,
                    category=GateCategory.SEMANTIC,
                    status=status,
                    message=f"Inconsistent metric grains: {'; '.join(messages)}",
                    details={"inconsistent_grains": inconsistent}
                ))
            else:
                results.append(GateResult(
                    gate_name=gate_name,
                    category=GateCategory.SEMANTIC,
                    status=GateStatus.PASS,
                    message="All metric grains consistent"
                ))
        
        return results
    
    def _evaluate_deployability_gates(self, odl_ir: ODLIR) -> List[GateResult]:
        """Evaluate deployability gates."""
        results = []
        
        # Gate: YAML Verify Passes
        gate_name = "yaml_verify_passes"
        threshold = self.threshold_profile.get("deployability", {}).get(gate_name, "required")
        
        if threshold == "skip":
            results.append(GateResult(
                gate_name=gate_name,
                category=GateCategory.DEPLOYABILITY,
                status=GateStatus.SKIP,
                message="YAML verify check skipped"
            ))
        else:
            # This gate prepares verify.sql but doesn't actually run it
            # Actual verification would require Snowflake connection
            # For now, we check that YAML can be generated
            try:
                from ..snowflake.snowflake_compiler import SnowflakeCompiler
                compiler = SnowflakeCompiler()
                options = {
                    "version_id": f"eval-{odl_ir.version}",
                    "view_name": "eval_view",
                    "database": odl_ir.snowflake.database if odl_ir.snowflake else "DATABASE",
                    "schema": odl_ir.snowflake.schema if odl_ir.snowflake else "SCHEMA"
                }
                bundle = compiler.compile(odl_ir, options)
                verify_file = bundle.get_file("verify.sql")
                
                if verify_file:
                    results.append(GateResult(
                        gate_name=gate_name,
                        category=GateCategory.DEPLOYABILITY,
                        status=GateStatus.PASS,
                        message="verify.sql generated successfully (run in Snowflake to verify)",
                        details={"verify_sql_generated": True}
                    ))
                else:
                    status = GateStatus.FAIL if threshold == "required" else GateStatus.WARNING
                    results.append(GateResult(
                        gate_name=gate_name,
                        category=GateCategory.DEPLOYABILITY,
                        status=status,
                        message="Failed to generate verify.sql"
                    ))
            except Exception as e:
                status = GateStatus.FAIL if threshold == "required" else GateStatus.WARNING
                results.append(GateResult(
                    gate_name=gate_name,
                    category=GateCategory.DEPLOYABILITY,
                    status=status,
                    message=f"Error generating verify.sql: {str(e)}",
                    details={"error": str(e)}
                ))
        
        return results
    
    def _check_unresolved_references(self, odl_ir: ODLIR) -> List[str]:
        """Check for unresolved object references in relationships and metrics."""
        unresolved = []
        object_names = {obj.name for obj in odl_ir.objects}
        
        # Check relationship references
        for rel in odl_ir.relationships:
            if rel.from_object not in object_names:
                unresolved.append(f"Relationship '{rel.name}': from_object '{rel.from_object}' not found")
            if rel.to_object not in object_names:
                unresolved.append(f"Relationship '{rel.name}': to_object '{rel.to_object}' not found")
        
        # Check metric grain references
        for metric in odl_ir.metrics:
            for grain_obj in metric.grain:
                if grain_obj not in object_names:
                    unresolved.append(f"Metric '{metric.name}': grain object '{grain_obj}' not found")
        
        # Check dimension source property references
        for dim in odl_ir.dimensions:
            parts = dim.source_property.split(".")
            if len(parts) == 2:
                obj_name, prop_name = parts
                if obj_name not in object_names:
                    unresolved.append(f"Dimension '{dim.name}': source object '{obj_name}' not found")
                else:
                    # Check property exists
                    obj = next((o for o in odl_ir.objects if o.name == obj_name), None)
                    if obj:
                        prop_names = {p.name for p in obj.properties}
                        if prop_name not in prop_names:
                            unresolved.append(f"Dimension '{dim.name}': property '{prop_name}' not found in '{obj_name}'")
        
        return unresolved
    
    def _check_mapping_completeness(self, odl_ir: ODLIR) -> List[str]:
        """Check that all objects have Snowflake table mappings."""
        incomplete = []
        
        if not odl_ir.snowflake:
            incomplete.append("No Snowflake mapping block defined")
            return incomplete
        
        for obj in odl_ir.objects:
            # Check if object has table mapping
            has_mapping = (
                obj.snowflake_table or
                odl_ir.snowflake.table_mappings.get(obj.name) or
                obj.name.lower()  # Default fallback
            )
            
            if not has_mapping:
                incomplete.append(f"Object '{obj.name}': no table mapping")
        
        return incomplete
    
    def _check_connected_join_graph(self, odl_ir: ODLIR) -> Tuple[bool, List[str]]:
        """Check that relationships form a connected graph."""
        if not odl_ir.objects:
            return True, []
        
        if not odl_ir.relationships:
            # No relationships means disconnected
            return False, [obj.name for obj in odl_ir.objects]
        
        # Build adjacency list
        graph: Dict[str, Set[str]] = {obj.name: set() for obj in odl_ir.objects}
        
        for rel in odl_ir.relationships:
            if rel.from_object in graph and rel.to_object in graph:
                graph[rel.from_object].add(rel.to_object)
                graph[rel.to_object].add(rel.from_object)
        
        # BFS to find connected components
        visited = set()
        components = []
        
        for obj_name in graph:
            if obj_name not in visited:
                component = []
                queue = [obj_name]
                visited.add(obj_name)
                
                while queue:
                    current = queue.pop(0)
                    component.append(current)
                    
                    for neighbor in graph[current]:
                        if neighbor not in visited:
                            visited.add(neighbor)
                            queue.append(neighbor)
                
                components.append(component)
        
        if len(components) == 1:
            return True, []
        else:
            # Return objects in disconnected components (excluding largest)
            largest_size = max(len(c) for c in components)
            disconnected = []
            for component in components:
                if len(component) < largest_size:
                    disconnected.extend(component)
            return False, disconnected
    
    def _check_ambiguous_join_paths(self, odl_ir: ODLIR) -> List[Tuple[str, str, List[List[str]]]]:
        """Check for ambiguous join paths between objects."""
        ambiguous = []
        
        if not odl_ir.relationships:
            return ambiguous
        
        # Build graph
        graph: Dict[str, List[Tuple[str, str]]] = {obj.name: [] for obj in odl_ir.objects}
        
        for rel in odl_ir.relationships:
            if rel.from_object in graph and rel.to_object in graph:
                graph[rel.from_object].append((rel.to_object, rel.name))
                graph[rel.to_object].append((rel.from_object, rel.name))
        
        # Find all paths between each pair of objects
        object_names = list(graph.keys())
        
        for i, obj1 in enumerate(object_names):
            for obj2 in object_names[i+1:]:
                paths = self._find_all_paths(graph, obj1, obj2, max_depth=5)
                if len(paths) > 1:
                    ambiguous.append((obj1, obj2, paths))
        
        return ambiguous
    
    def _check_relationship_join_keys_mismatch(self, odl_ir: ODLIR) -> List[str]:
        """Check for join key mismatches in relationships."""
        mismatches = []
        
        for rel in odl_ir.relationships:
            # Find from object
            from_obj = next((o for o in odl_ir.objects if o.name == rel.from_object), None)
            to_obj = next((o for o in odl_ir.objects if o.name == rel.to_object), None)
            
            if not from_obj or not to_obj:
                continue
            
            # Check each join key pair
            for from_key, to_key in rel.join_keys:
                # Check from_key exists in from_obj
                from_props = {p.name for p in from_obj.properties}
                if from_key not in from_props:
                    mismatches.append(
                        f"Relationship '{rel.name}': join key '{from_key}' not found in '{rel.from_object}'"
                    )
                
                # Check to_key exists in to_obj
                to_props = {p.name for p in to_obj.properties}
                if to_key not in to_props:
                    mismatches.append(
                        f"Relationship '{rel.name}': join key '{to_key}' not found in '{rel.to_object}'"
                    )
        
        return mismatches
    
    def _find_all_paths(self, graph: Dict[str, List[Tuple[str, str]]], start: str, end: str, max_depth: int = 5) -> List[List[str]]:
        """Find all paths between two nodes."""
        if start == end:
            return [[start]]
        
        if max_depth == 0:
            return []
        
        paths = []
        visited = {start}
        
        def dfs(current: str, path: List[str]):
            if current == end:
                paths.append(path[:])
                return
            
            if len(path) >= max_depth:
                return
            
            for neighbor, _ in graph.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    path.append(neighbor)
                    dfs(neighbor, path)
                    path.pop()
                    visited.remove(neighbor)
        
        dfs(start, [start])
        return paths
    
    def _check_metric_grains_consistent(self, odl_ir: ODLIR) -> List[Tuple[str, List[str], str]]:
        """Check that metric grains reference valid objects and are consistent."""
        inconsistent = []
        object_names = {obj.name for obj in odl_ir.objects}
        
        for metric in odl_ir.metrics:
            # Check all grain objects exist
            for grain_obj in metric.grain:
                if grain_obj not in object_names:
                    inconsistent.append((metric.name, metric.grain, f"Grain object '{grain_obj}' not found"))
            
            # Check grain is not empty
            if not metric.grain:
                inconsistent.append((metric.name, metric.grain, "Grain is empty"))
        
        return inconsistent
    
    def _determine_overall_pass(self, gate_results: List[GateResult]) -> bool:
        """Determine overall pass based on threshold profile."""
        for result in gate_results:
            threshold = self._get_threshold_for_gate(result.gate_name, result.category)
            
            if threshold == "required" and result.status == GateStatus.FAIL:
                return False
            elif threshold == "required" and result.status == GateStatus.WARNING:
                # Warnings in required gates fail in strict mode
                if self.threshold_profile == ThresholdProfile.STRICT:
                    return False
        
        return True
    
    def _get_threshold_for_gate(self, gate_name: str, category: GateCategory) -> str:
        """Get threshold for a specific gate."""
        category_key = category.value
        return self.threshold_profile.get(category_key, {}).get(gate_name, "required")
    
    def _calculate_metrics(self, gate_results: List[GateResult]) -> Dict[str, Any]:
        """Calculate evaluation metrics."""
        total = len(gate_results)
        passed = sum(1 for r in gate_results if r.status == GateStatus.PASS)
        failed = sum(1 for r in gate_results if r.status == GateStatus.FAIL)
        warnings = sum(1 for r in gate_results if r.status == GateStatus.WARNING)
        skipped = sum(1 for r in gate_results if r.status == GateStatus.SKIP)
        
        by_category = {}
        for category in GateCategory:
            category_results = [r for r in gate_results if r.category == category]
            by_category[category.value] = {
                "total": len(category_results),
                "passed": sum(1 for r in category_results if r.status == GateStatus.PASS),
                "failed": sum(1 for r in category_results if r.status == GateStatus.FAIL),
                "warnings": sum(1 for r in category_results if r.status == GateStatus.WARNING)
            }
        
        return {
            "total_gates": total,
            "passed": passed,
            "failed": failed,
            "warnings": warnings,
            "skipped": skipped,
            "by_category": by_category
        }
