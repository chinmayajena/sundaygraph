"""Tests for drift detection with mock provider."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.odl.drift import DriftDetector, DriftEventType, DriftType
from src.odl.ir import (
    ODLIR, ObjectIR, PropertyIR, RelationshipIR, MetricIR, DimensionIR,
    SnowflakeMappingIR
)
from src.snowflake.provider import MockSnowflakeProvider


def create_test_odl_ir() -> ODLIR:
    """Create a test ODL IR."""
    return ODLIR(
        version="1.0.0",
        name="Test Ontology",
        objects=[
            ObjectIR(
                name="Customer",
                identifiers=["customer_id"],
                properties=[
                    PropertyIR(name="customer_id", type="string"),
                    PropertyIR(name="name", type="string"),
                    PropertyIR(name="email", type="string"),
                    PropertyIR(name="age", type="integer")
                ],
                snowflake_table="customers"
            ),
            ObjectIR(
                name="Order",
                identifiers=["order_id"],
                properties=[
                    PropertyIR(name="order_id", type="string"),
                    PropertyIR(name="customer_id", type="string"),
                    PropertyIR(name="amount", type="decimal")
                ],
                snowflake_table="orders"
            )
        ],
        relationships=[],
        metrics=[],
        dimensions=[],
        snowflake=SnowflakeMappingIR(
            database="TEST_DB",
            schema="PUBLIC",
            table_mappings={
                "Customer": "customers",
                "Order": "orders"
            }
        )
    )


def test_column_missing():
    """Test: Detect missing column."""
    print("Test 1: Column missing")
    
    odl_ir = create_test_odl_ir()
    provider = MockSnowflakeProvider()
    
    # Add table schema with missing column
    provider.add_table_schema(
        "TEST_DB", "PUBLIC", "customers",
        [
            {"name": "customer_id", "type": "VARCHAR", "nullable": False},
            {"name": "name", "type": "VARCHAR", "nullable": True},
            # email is missing
            {"name": "age", "type": "INTEGER", "nullable": True}
        ]
    )
    
    detector = DriftDetector(provider)
    result = detector.detect_mapping_drift(odl_ir, ontology_id=1)
    
    assert len(result.drift_events) >= 1, "Should detect missing column"
    missing_events = [e for e in result.drift_events if e.event_type == DriftEventType.COLUMN_MISSING]
    assert len(missing_events) > 0, "Should have COLUMN_MISSING event"
    assert "email" in missing_events[0].message, "Should mention missing column"
    
    print("  [PASS] Missing column detected")


def test_column_added():
    """Test: Detect added column."""
    print("\nTest 2: Column added")
    
    odl_ir = create_test_odl_ir()
    provider = MockSnowflakeProvider()
    
    # Add table schema with extra column
    provider.add_table_schema(
        "TEST_DB", "PUBLIC", "customers",
        [
            {"name": "customer_id", "type": "VARCHAR", "nullable": False},
            {"name": "name", "type": "VARCHAR", "nullable": True},
            {"name": "email", "type": "VARCHAR", "nullable": True},
            {"name": "age", "type": "INTEGER", "nullable": True},
            {"name": "phone", "type": "VARCHAR", "nullable": True}  # Added
        ]
    )
    
    detector = DriftDetector(provider)
    result = detector.detect_mapping_drift(odl_ir, ontology_id=1)
    
    assert len(result.drift_events) >= 1, "Should detect added column"
    added_events = [e for e in result.drift_events if e.event_type == DriftEventType.COLUMN_ADDED]
    assert len(added_events) > 0, "Should have COLUMN_ADDED event"
    assert "phone" in added_events[0].message, "Should mention added column"
    
    print("  [PASS] Added column detected")


def test_column_renamed():
    """Test: Detect renamed column."""
    print("\nTest 3: Column renamed")
    
    odl_ir = create_test_odl_ir()
    provider = MockSnowflakeProvider()
    
    # Add table schema with renamed column
    provider.add_table_schema(
        "TEST_DB", "PUBLIC", "customers",
        [
            {"name": "customer_id", "type": "VARCHAR", "nullable": False},
            {"name": "name", "type": "VARCHAR", "nullable": True},
            {"name": "email_address", "type": "VARCHAR", "nullable": True},  # Renamed from email
            {"name": "age", "type": "INTEGER", "nullable": True}
        ]
    )
    
    detector = DriftDetector(provider)
    result = detector.detect_mapping_drift(odl_ir, ontology_id=1)
    
    # Should detect both missing and potentially renamed
    missing_events = [e for e in result.drift_events if e.event_type == DriftEventType.COLUMN_MISSING]
    renamed_events = [e for e in result.drift_events if e.event_type == DriftEventType.COLUMN_RENAMED]
    
    assert len(missing_events) > 0 or len(renamed_events) > 0, "Should detect column change"
    
    print("  [PASS] Column rename detected")


def test_table_missing():
    """Test: Detect missing table."""
    print("\nTest 4: Table missing")
    
    odl_ir = create_test_odl_ir()
    provider = MockSnowflakeProvider()
    
    # Don't add any table schemas
    
    detector = DriftDetector(provider)
    result = detector.detect_mapping_drift(odl_ir, ontology_id=1)
    
    assert len(result.drift_events) >= 2, "Should detect missing tables"
    missing_table_events = [e for e in result.drift_events if e.event_type == DriftEventType.TABLE_MISSING]
    assert len(missing_table_events) >= 2, "Should have TABLE_MISSING events for both tables"
    
    print("  [PASS] Missing table detected")


def test_column_dropped():
    """Test: Detect dropped column using provider method."""
    print("\nTest 5: Column dropped")
    
    odl_ir = create_test_odl_ir()
    provider = MockSnowflakeProvider()
    
    # Add complete table schema
    provider.add_table_schema(
        "TEST_DB", "PUBLIC", "customers",
        [
            {"name": "customer_id", "type": "VARCHAR", "nullable": False},
            {"name": "name", "type": "VARCHAR", "nullable": True},
            {"name": "email", "type": "VARCHAR", "nullable": True},
            {"name": "age", "type": "INTEGER", "nullable": True}
        ]
    )
    
    # Drop a column
    provider.remove_table_column("TEST_DB", "PUBLIC", "customers", "email")
    
    detector = DriftDetector(provider)
    result = detector.detect_mapping_drift(odl_ir, ontology_id=1)
    
    assert len(result.drift_events) >= 1, "Should detect dropped column"
    missing_events = [e for e in result.drift_events if e.event_type == DriftEventType.COLUMN_MISSING]
    assert len(missing_events) > 0, "Should have COLUMN_MISSING event for dropped column"
    
    print("  [PASS] Dropped column detected")


def test_semantic_view_yaml_divergence():
    """Test: Detect semantic view YAML divergence."""
    print("\nTest 6: Semantic view YAML divergence")
    
    odl_ir = create_test_odl_ir()
    provider = MockSnowflakeProvider()
    
    # Add semantic view with different YAML
    provider.add_semantic_view(
        "TEST_DB", "PUBLIC", "test_view",
        """
semantic_model:
  name: Test Model
  version: 1.0.0
  logical_tables:
    - name: Customer
      physical_table:
        database: TEST_DB
        schema: PUBLIC
        table: customers
  relationships: []
  facts: []
"""
    )
    
    detector = DriftDetector(provider)
    result = detector.detect_semantic_view_drift(odl_ir, ontology_id=1, view_name="test_view")
    
    # Should detect some differences (missing Order table, etc.)
    assert len(result.drift_events) >= 1, "Should detect YAML divergence"
    divergence_events = [e for e in result.drift_events if e.event_type == DriftEventType.YAML_DIVERGENCE]
    assert len(divergence_events) > 0, "Should have YAML_DIVERGENCE events"
    
    print("  [PASS] Semantic view YAML divergence detected")


def test_semantic_view_manual_edit():
    """Test: Detect manual edits in semantic view."""
    print("\nTest 7: Manual edit detected")
    
    odl_ir = create_test_odl_ir()
    provider = MockSnowflakeProvider()
    
    # Add semantic view with significantly different structure
    provider.add_semantic_view(
        "TEST_DB", "PUBLIC", "test_view",
        """
semantic_model:
  name: Test Model
  version: 1.0.0
  logical_tables:
    - name: Customer
      physical_table:
        database: TEST_DB
        schema: PUBLIC
        table: customers
    - name: Product
      physical_table:
        database: TEST_DB
        schema: PUBLIC
        table: products
  relationships:
    - name: custom_rel
      from_table: Customer
      to_table: Product
  facts:
    - name: CustomMetric
      expression: SUM(amount)
"""
    )
    
    detector = DriftDetector(provider)
    result = detector.detect_semantic_view_drift(odl_ir, ontology_id=1, view_name="test_view")
    
    # Should detect manual edits (added tables, relationships, facts)
    manual_edit_events = [e for e in result.drift_events if e.event_type == DriftEventType.MANUAL_EDIT_DETECTED]
    assert len(manual_edit_events) > 0, "Should detect manual edits"
    
    print("  [PASS] Manual edit detected")


def test_no_drift():
    """Test: No drift when schemas match."""
    print("\nTest 8: No drift when schemas match")
    
    odl_ir = create_test_odl_ir()
    provider = MockSnowflakeProvider()
    
    # Add matching table schemas
    provider.add_table_schema(
        "TEST_DB", "PUBLIC", "customers",
        [
            {"name": "customer_id", "type": "VARCHAR", "nullable": False},
            {"name": "name", "type": "VARCHAR", "nullable": True},
            {"name": "email", "type": "VARCHAR", "nullable": True},
            {"name": "age", "type": "INTEGER", "nullable": True}
        ]
    )
    provider.add_table_schema(
        "TEST_DB", "PUBLIC", "orders",
        [
            {"name": "order_id", "type": "VARCHAR", "nullable": False},
            {"name": "customer_id", "type": "VARCHAR", "nullable": True},
            {"name": "amount", "type": "DECIMAL", "nullable": True}
        ]
    )
    
    detector = DriftDetector(provider)
    result = detector.detect_mapping_drift(odl_ir, ontology_id=1)
    
    # Should have minimal or no drift events (maybe some added columns if Snowflake has extras)
    # But no missing columns
    missing_events = [e for e in result.drift_events if e.event_type == DriftEventType.COLUMN_MISSING]
    assert len(missing_events) == 0, "Should not detect missing columns when schemas match"
    
    print("  [PASS] No drift detected when schemas match")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Drift Detection Tests")
    print("=" * 60)
    
    tests = [
        test_column_missing,
        test_column_added,
        test_column_renamed,
        test_table_missing,
        test_column_dropped,
        test_semantic_view_yaml_divergence,
        test_semantic_view_manual_edit,
        test_no_drift,
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
