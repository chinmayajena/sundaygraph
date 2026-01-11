"""Comprehensive tests for ODL diff engine."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.odl.diff import (
    ODLDiffEngine, DiffResult, Change, ChangeType, ChangeCategory
)
from src.odl.ir import (
    ODLIR, ObjectIR, PropertyIR, RelationshipIR, MetricIR, DimensionIR,
    SnowflakeMappingIR
)


def create_minimal_odl_ir(name: str = "Test", version: str = "1.0.0") -> ODLIR:
    """Create a minimal ODL IR for testing."""
    return ODLIR(
        version=version,
        name=name,
        objects=[],
        relationships=[],
        metrics=[],
        dimensions=[]
    )


def test_object_removed_breaking():
    """Test: Object removal is breaking."""
    print("Test 1: Object removal is breaking")
    
    old_ir = create_minimal_odl_ir("v1", "1.0.0")
    old_ir.objects = [
        ObjectIR(name="Customer", identifiers=["customer_id"])
    ]
    
    new_ir = create_minimal_odl_ir("v2", "2.0.0")
    
    engine = ODLDiffEngine()
    result = engine.diff(old_ir, new_ir)
    
    assert len(result.breaking_changes) == 1, "Should have 1 breaking change"
    assert result.breaking_changes[0].category == ChangeCategory.OBJECT_REMOVED
    assert result.breaking_changes[0].element_name == "Customer"
    assert result.breaking_changes[0].change_type == ChangeType.BREAKING
    
    print("  [PASS] Object removal correctly identified as breaking")


def test_object_added_non_breaking():
    """Test: Object addition is non-breaking."""
    print("\nTest 2: Object addition is non-breaking")
    
    old_ir = create_minimal_odl_ir("v1", "1.0.0")
    
    new_ir = create_minimal_odl_ir("v2", "2.0.0")
    new_ir.objects = [
        ObjectIR(name="Customer", identifiers=["customer_id"])
    ]
    
    engine = ODLDiffEngine()
    result = engine.diff(old_ir, new_ir)
    
    assert len(result.non_breaking_changes) == 1, "Should have 1 non-breaking change"
    assert result.non_breaking_changes[0].category == ChangeCategory.OBJECT_ADDED
    assert result.non_breaking_changes[0].element_name == "Customer"
    assert result.non_breaking_changes[0].change_type == ChangeType.NON_BREAKING
    
    print("  [PASS] Object addition correctly identified as non-breaking")


def test_identifier_changed_breaking():
    """Test: Identifier change is breaking."""
    print("\nTest 3: Identifier change is breaking")
    
    old_ir = create_minimal_odl_ir("v1", "1.0.0")
    old_ir.objects = [
        ObjectIR(name="Customer", identifiers=["customer_id"])
    ]
    
    new_ir = create_minimal_odl_ir("v2", "2.0.0")
    new_ir.objects = [
        ObjectIR(name="Customer", identifiers=["id"])
    ]
    
    engine = ODLDiffEngine()
    result = engine.diff(old_ir, new_ir)
    
    assert len(result.breaking_changes) >= 1, "Should have at least 1 breaking change"
    identifier_changes = [c for c in result.breaking_changes 
                         if c.category == ChangeCategory.IDENTIFIER_CHANGED]
    assert len(identifier_changes) > 0, "Should have identifier change"
    
    print("  [PASS] Identifier change correctly identified as breaking")


def test_relationship_join_keys_changed_breaking():
    """Test: Relationship join keys change is breaking."""
    print("\nTest 4: Relationship join keys change is breaking")
    
    old_ir = create_minimal_odl_ir("v1", "1.0.0")
    old_ir.objects = [
        ObjectIR(name="Order", identifiers=["order_id"]),
        ObjectIR(name="Customer", identifiers=["customer_id"])
    ]
    old_ir.relationships = [
        RelationshipIR(
            name="placed_by",
            from_object="Order",
            to_object="Customer",
            join_keys=[("customer_id", "customer_id")]
        )
    ]
    
    new_ir = create_minimal_odl_ir("v2", "2.0.0")
    new_ir.objects = [
        ObjectIR(name="Order", identifiers=["order_id"]),
        ObjectIR(name="Customer", identifiers=["customer_id"])
    ]
    new_ir.relationships = [
        RelationshipIR(
            name="placed_by",
            from_object="Order",
            to_object="Customer",
            join_keys=[("order_customer_id", "customer_id")]
        )
    ]
    
    engine = ODLDiffEngine()
    result = engine.diff(old_ir, new_ir)
    
    assert len(result.breaking_changes) >= 1, "Should have at least 1 breaking change"
    join_key_changes = [c for c in result.breaking_changes 
                       if c.category == ChangeCategory.RELATIONSHIP_JOIN_KEYS_CHANGED]
    assert len(join_key_changes) > 0, "Should have join keys change"
    
    print("  [PASS] Join keys change correctly identified as breaking")


def test_cardinality_tightened_breaking():
    """Test: Cardinality tightening is breaking."""
    print("\nTest 5: Cardinality tightening is breaking")
    
    old_ir = create_minimal_odl_ir("v1", "1.0.0")
    old_ir.objects = [
        ObjectIR(name="Order", identifiers=["order_id"]),
        ObjectIR(name="Customer", identifiers=["customer_id"])
    ]
    old_ir.relationships = [
        RelationshipIR(
            name="placed_by",
            from_object="Order",
            to_object="Customer",
            cardinality="many_to_one"
        )
    ]
    
    new_ir = create_minimal_odl_ir("v2", "2.0.0")
    new_ir.objects = [
        ObjectIR(name="Order", identifiers=["order_id"]),
        ObjectIR(name="Customer", identifiers=["customer_id"])
    ]
    new_ir.relationships = [
        RelationshipIR(
            name="placed_by",
            from_object="Order",
            to_object="Customer",
            cardinality="one_to_one"
        )
    ]
    
    engine = ODLDiffEngine()
    result = engine.diff(old_ir, new_ir)
    
    assert len(result.breaking_changes) >= 1, "Should have at least 1 breaking change"
    cardinality_changes = [c for c in result.breaking_changes 
                          if c.category == ChangeCategory.RELATIONSHIP_CARDINALITY_TIGHTENED]
    assert len(cardinality_changes) > 0, "Should have cardinality tightening"
    
    print("  [PASS] Cardinality tightening correctly identified as breaking")


def test_cardinality_relaxed_non_breaking():
    """Test: Cardinality relaxation is non-breaking."""
    print("\nTest 6: Cardinality relaxation is non-breaking")
    
    old_ir = create_minimal_odl_ir("v1", "1.0.0")
    old_ir.objects = [
        ObjectIR(name="Order", identifiers=["order_id"]),
        ObjectIR(name="Customer", identifiers=["customer_id"])
    ]
    old_ir.relationships = [
        RelationshipIR(
            name="placed_by",
            from_object="Order",
            to_object="Customer",
            cardinality="one_to_one"
        )
    ]
    
    new_ir = create_minimal_odl_ir("v2", "2.0.0")
    new_ir.objects = [
        ObjectIR(name="Order", identifiers=["order_id"]),
        ObjectIR(name="Customer", identifiers=["customer_id"])
    ]
    new_ir.relationships = [
        RelationshipIR(
            name="placed_by",
            from_object="Order",
            to_object="Customer",
            cardinality="many_to_one"
        )
    ]
    
    engine = ODLDiffEngine()
    result = engine.diff(old_ir, new_ir)
    
    assert len(result.non_breaking_changes) >= 1, "Should have at least 1 non-breaking change"
    cardinality_changes = [c for c in result.non_breaking_changes 
                          if c.category == ChangeCategory.RELATIONSHIP_CARDINALITY_RELAXED]
    assert len(cardinality_changes) > 0, "Should have cardinality relaxation"
    
    print("  [PASS] Cardinality relaxation correctly identified as non-breaking")


def test_metric_expression_changed_breaking():
    """Test: Metric expression change is breaking."""
    print("\nTest 7: Metric expression change is breaking")
    
    old_ir = create_minimal_odl_ir("v1", "1.0.0")
    old_ir.metrics = [
        MetricIR(
            name="TotalRevenue",
            expression="SUM(amount)",
            grain=["Order"]
        )
    ]
    
    new_ir = create_minimal_odl_ir("v2", "2.0.0")
    new_ir.metrics = [
        MetricIR(
            name="TotalRevenue",
            expression="SUM(amount * quantity)",
            grain=["Order"]
        )
    ]
    
    engine = ODLDiffEngine()
    result = engine.diff(old_ir, new_ir)
    
    assert len(result.breaking_changes) >= 1, "Should have at least 1 breaking change"
    expression_changes = [c for c in result.breaking_changes 
                         if c.category == ChangeCategory.METRIC_EXPRESSION_CHANGED]
    assert len(expression_changes) > 0, "Should have expression change"
    
    print("  [PASS] Metric expression change correctly identified as breaking")


def test_metric_grain_changed_breaking():
    """Test: Metric grain change is breaking."""
    print("\nTest 8: Metric grain change is breaking")
    
    old_ir = create_minimal_odl_ir("v1", "1.0.0")
    old_ir.metrics = [
        MetricIR(
            name="TotalRevenue",
            expression="SUM(amount)",
            grain=["Order"]
        )
    ]
    
    new_ir = create_minimal_odl_ir("v2", "2.0.0")
    new_ir.metrics = [
        MetricIR(
            name="TotalRevenue",
            expression="SUM(amount)",
            grain=["OrderItem"]
        )
    ]
    
    engine = ODLDiffEngine()
    result = engine.diff(old_ir, new_ir)
    
    assert len(result.breaking_changes) >= 1, "Should have at least 1 breaking change"
    grain_changes = [c for c in result.breaking_changes 
                    if c.category == ChangeCategory.METRIC_GRAIN_CHANGED]
    assert len(grain_changes) > 0, "Should have grain change"
    
    print("  [PASS] Metric grain change correctly identified as breaking")


def test_metric_added_non_breaking():
    """Test: Metric addition is non-breaking."""
    print("\nTest 9: Metric addition is non-breaking")
    
    old_ir = create_minimal_odl_ir("v1", "1.0.0")
    old_ir.metrics = [
        MetricIR(name="TotalRevenue", expression="SUM(amount)", grain=["Order"])
    ]
    
    new_ir = create_minimal_odl_ir("v2", "2.0.0")
    new_ir.metrics = [
        MetricIR(name="TotalRevenue", expression="SUM(amount)", grain=["Order"]),
        MetricIR(name="OrderCount", expression="COUNT(*)", grain=["Order"])
    ]
    
    engine = ODLDiffEngine()
    result = engine.diff(old_ir, new_ir)
    
    assert len(result.non_breaking_changes) >= 1, "Should have at least 1 non-breaking change"
    metric_additions = [c for c in result.non_breaking_changes 
                      if c.category == ChangeCategory.METRIC_ADDED]
    assert len(metric_additions) > 0, "Should have metric addition"
    
    print("  [PASS] Metric addition correctly identified as non-breaking")


def test_dimension_added_non_breaking():
    """Test: Dimension addition is non-breaking."""
    print("\nTest 10: Dimension addition is non-breaking")
    
    old_ir = create_minimal_odl_ir("v1", "1.0.0")
    old_ir.dimensions = [
        DimensionIR(name="CustomerName", source_property="Customer.name")
    ]
    
    new_ir = create_minimal_odl_ir("v2", "2.0.0")
    new_ir.dimensions = [
        DimensionIR(name="CustomerName", source_property="Customer.name"),
        DimensionIR(name="OrderDate", source_property="Order.order_date")
    ]
    
    engine = ODLDiffEngine()
    result = engine.diff(old_ir, new_ir)
    
    assert len(result.non_breaking_changes) >= 1, "Should have at least 1 non-breaking change"
    dimension_additions = [c for c in result.non_breaking_changes 
                         if c.category == ChangeCategory.DIMENSION_ADDED]
    assert len(dimension_additions) > 0, "Should have dimension addition"
    
    print("  [PASS] Dimension addition correctly identified as non-breaking")


def test_description_changes_non_breaking():
    """Test: Description changes are non-breaking."""
    print("\nTest 11: Description changes are non-breaking")
    
    old_ir = create_minimal_odl_ir("v1", "1.0.0")
    old_ir.objects = [
        ObjectIR(name="Customer", description="Old description")
    ]
    
    new_ir = create_minimal_odl_ir("v2", "2.0.0")
    new_ir.objects = [
        ObjectIR(name="Customer", description="New description")
    ]
    
    engine = ODLDiffEngine()
    result = engine.diff(old_ir, new_ir)
    
    assert len(result.non_breaking_changes) >= 1, "Should have at least 1 non-breaking change"
    desc_changes = [c for c in result.non_breaking_changes 
                   if c.category == ChangeCategory.OBJECT_DESCRIPTION_CHANGED]
    assert len(desc_changes) > 0, "Should have description change"
    
    print("  [PASS] Description change correctly identified as non-breaking")


def test_property_type_changed_breaking():
    """Test: Property type change is breaking."""
    print("\nTest 12: Property type change is breaking")
    
    old_ir = create_minimal_odl_ir("v1", "1.0.0")
    old_ir.objects = [
        ObjectIR(
            name="Customer",
            identifiers=["customer_id"],
            properties=[PropertyIR(name="age", type="integer")]
        )
    ]
    
    new_ir = create_minimal_odl_ir("v2", "2.0.0")
    new_ir.objects = [
        ObjectIR(
            name="Customer",
            identifiers=["customer_id"],
            properties=[PropertyIR(name="age", type="string")]
        )
    ]
    
    engine = ODLDiffEngine()
    result = engine.diff(old_ir, new_ir)
    
    assert len(result.breaking_changes) >= 1, "Should have at least 1 breaking change"
    type_changes = [c for c in result.breaking_changes 
                   if c.category == ChangeCategory.PROPERTY_TYPE_CHANGED]
    assert len(type_changes) > 0, "Should have property type change"
    
    print("  [PASS] Property type change correctly identified as breaking")


def test_complex_diff():
    """Test: Complex diff with multiple changes."""
    print("\nTest 13: Complex diff with multiple changes")
    
    old_ir = create_minimal_odl_ir("v1", "1.0.0")
    old_ir.objects = [
        ObjectIR(name="Customer", identifiers=["customer_id"]),
        ObjectIR(name="Order", identifiers=["order_id"])
    ]
    old_ir.relationships = [
        RelationshipIR(
            name="placed_by",
            from_object="Order",
            to_object="Customer",
            cardinality="many_to_one"
        )
    ]
    old_ir.metrics = [
        MetricIR(name="TotalRevenue", expression="SUM(amount)", grain=["Order"])
    ]
    
    new_ir = create_minimal_odl_ir("v2", "2.0.0")
    new_ir.objects = [
        ObjectIR(name="Customer", identifiers=["customer_id"]),
        ObjectIR(name="Order", identifiers=["order_id"]),
        ObjectIR(name="Product", identifiers=["product_id"])  # Added
    ]
    new_ir.relationships = [
        RelationshipIR(
            name="placed_by",
            from_object="Order",
            to_object="Customer",
            cardinality="one_to_one"  # Tightened
        )
    ]
    new_ir.metrics = [
        MetricIR(name="TotalRevenue", expression="SUM(amount * quantity)", grain=["Order"]),  # Changed
        MetricIR(name="OrderCount", expression="COUNT(*)", grain=["Order"])  # Added
    ]
    
    engine = ODLDiffEngine()
    result = engine.diff(old_ir, new_ir)
    
    # Should have breaking changes
    assert len(result.breaking_changes) >= 2, "Should have multiple breaking changes"
    
    # Should have non-breaking changes
    assert len(result.non_breaking_changes) >= 2, "Should have multiple non-breaking changes"
    
    # Check summary
    assert result.summary["total_breaking"] > 0
    assert result.summary["total_non_breaking"] > 0
    assert result.summary["total_changes"] == len(result.breaking_changes) + len(result.non_breaking_changes)
    
    print("  [PASS] Complex diff correctly computed")
    print(f"    - Breaking: {result.summary['total_breaking']}")
    print(f"    - Non-breaking: {result.summary['total_non_breaking']}")


def main():
    """Run all tests."""
    print("=" * 60)
    print("ODL Diff Engine Tests")
    print("=" * 60)
    
    tests = [
        test_object_removed_breaking,
        test_object_added_non_breaking,
        test_identifier_changed_breaking,
        test_relationship_join_keys_changed_breaking,
        test_cardinality_tightened_breaking,
        test_cardinality_relaxed_non_breaking,
        test_metric_expression_changed_breaking,
        test_metric_grain_changed_breaking,
        test_metric_added_non_breaking,
        test_dimension_added_non_breaking,
        test_description_changes_non_breaking,
        test_property_type_changed_breaking,
        test_complex_diff,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  [FAIL] {e}")
            failed += 1
        except Exception as e:
            print(f"  [ERROR] {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
