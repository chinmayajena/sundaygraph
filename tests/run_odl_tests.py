#!/usr/bin/env python3
"""Simple test runner for ODL tests (without pytest)."""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from odl.core import ODLProcessor
from odl.validator import ODLValidator
from odl.loader import ODLLoader
from odl.normalizer import ODLNormalizer


def test_missing_object_reference():
    """Test validation error for missing object reference in relationship."""
    print("Test: Missing object reference")
    
    validator = ODLValidator()
    
    odl_data = {
        "version": "1.0.0",
        "objects": [
            {"name": "Customer", "identifiers": ["id"], "properties": []}
        ],
        "relationships": [
            {
                "name": "placed_by",
                "from": "Order",  # Order doesn't exist
                "to": "Customer",
                "joinKeys": [["order_id", "id"]]
            }
        ]
    }
    
    is_valid, errors = validator.validate(odl_data)
    
    assert not is_valid, "Should fail validation"
    assert len(errors) > 0, "Should have errors"
    assert any("Order" in error and "unknown object" in error.lower() for error in errors), "Should mention unknown object"
    assert any("Available objects" in error for error in errors), "Should list available objects"
    
    print(f"  [PASS] Found {len(errors)} error(s)")
    print(f"    Error: {errors[0][:100]}...")


def test_duplicate_metric_name():
    """Test validation error for duplicate metric names."""
    print("\nTest: Duplicate metric name")
    
    validator = ODLValidator()
    
    odl_data = {
        "version": "1.0.0",
        "objects": [
            {"name": "Order", "identifiers": ["id"], "properties": []}
        ],
        "metrics": [
            {
                "name": "TotalRevenue",
                "expression": "SUM(amount)",
                "grain": ["Order"]
            },
            {
                "name": "TotalRevenue",  # Duplicate
                "expression": "SUM(total)",
                "grain": ["Order"]
            }
        ]
    }
    
    is_valid, errors = validator.validate(odl_data)
    
    assert not is_valid, "Should fail validation"
    assert len(errors) > 0, "Should have errors"
    assert any("Duplicate metric name" in error and "TotalRevenue" in error for error in errors), "Should mention duplicate"
    assert any("First occurrence" in error for error in errors), "Should mention first occurrence"
    
    print(f"  [PASS] Found {len(errors)} error(s)")
    print(f"    Error: {errors[0][:100]}...")


def test_invalid_relationship_cardinality():
    """Test validation error for invalid relationship cardinality."""
    print("\nTest: Invalid relationship cardinality")
    
    validator = ODLValidator()
    
    odl_data = {
        "version": "1.0.0",
        "objects": [
            {"name": "Order", "identifiers": ["id"], "properties": []},
            {"name": "Customer", "identifiers": ["id"], "properties": []}
        ],
        "relationships": [
            {
                "name": "placed_by",
                "from": "Order",
                "to": "Customer",
                "joinKeys": [["customer_id", "id"]],
                "cardinality": "invalid_cardinality"  # Invalid
            }
        ]
    }
    
    is_valid, errors = validator.validate(odl_data)
    
    assert not is_valid, "Should fail validation"
    assert len(errors) > 0, "Should have errors"
    assert any("invalid cardinality" in error.lower() for error in errors), "Should mention invalid cardinality"
    assert any("Valid values" in error for error in errors), "Should list valid values"
    
    print(f"  [PASS] Found {len(errors)} error(s)")
    print(f"    Error: {errors[0][:100]}...")


def test_relationship_join_key_missing():
    """Test validation error when relationship join key references missing property."""
    print("\nTest: Relationship join key missing from mapped tables")
    
    validator = ODLValidator()
    
    odl_data = {
        "version": "1.0.0",
        "objects": [
            {
                "name": "Order",
                "identifiers": ["id"],
                "properties": [
                    {"name": "id", "type": "string"},
                    {"name": "order_date", "type": "date"}
                    # Missing customer_id property
                ]
            },
            {
                "name": "Customer",
                "identifiers": ["id"],
                "properties": [
                    {"name": "id", "type": "string"}
                ]
            }
        ],
        "relationships": [
            {
                "name": "placed_by",
                "from": "Order",
                "to": "Customer",
                "joinKeys": [
                    ["customer_id", "id"]  # customer_id doesn't exist in Order
                ]
            }
        ],
        "snowflake": {
            "database": "TEST_DB",
            "schema": "PUBLIC"
        }
    }
    
    is_valid, errors = validator.validate(odl_data)
    
    assert not is_valid, "Should fail validation"
    assert len(errors) > 0, "Should have errors"
    # Should find error about missing property
    assert any("customer_id" in error.lower() and "unknown property" in error.lower() for error in errors), "Should mention missing property"
    assert any("Available properties" in error for error in errors), "Should list available properties"
    
    print(f"  [PASS] Found {len(errors)} error(s)")
    print(f"    Error: {errors[0][:100]}...")


def test_valid_odl_passes():
    """Test that valid ODL passes validation."""
    print("\nTest: Valid ODL passes validation")
    
    validator = ODLValidator()
    
    odl_data = {
        "version": "1.0.0",
        "objects": [
            {
                "name": "Order",
                "identifiers": ["id"],
                "properties": [
                    {"name": "id", "type": "string"},
                    {"name": "customer_id", "type": "string"}
                ]
            },
            {
                "name": "Customer",
                "identifiers": ["id"],
                "properties": [
                    {"name": "id", "type": "string"}
                ]
            }
        ],
        "relationships": [
            {
                "name": "placed_by",
                "from": "Order",
                "to": "Customer",
                "joinKeys": [["customer_id", "id"]]
            }
        ],
        "snowflake": {
            "database": "TEST_DB",
            "schema": "PUBLIC"
        }
    }
    
    is_valid, errors = validator.validate(odl_data)
    
    assert is_valid, "Should pass validation"
    assert len(errors) == 0, "Should have no errors"
    
    print(f"  [PASS] Validation successful")


def test_normalize_sorts_lists():
    """Test that normalization sorts lists for stability."""
    print("\nTest: Normalization sorts lists")
    
    normalizer = ODLNormalizer()
    
    odl_data = {
        "version": "1.0.0",
        "objects": [
            {"name": "Zebra", "identifiers": ["id"], "properties": []},
            {"name": "Alpha", "identifiers": ["id"], "properties": []},
            {"name": "Beta", "identifiers": ["id"], "properties": []}
        ],
        "metrics": [
            {"name": "MetricB", "expression": "SUM(x)", "grain": ["Alpha"]},
            {"name": "MetricA", "expression": "SUM(y)", "grain": ["Alpha"]}
        ]
    }
    
    ir = normalizer.normalize(odl_data)
    
    # Objects should be sorted
    assert [o.name for o in ir.objects] == ["Alpha", "Beta", "Zebra"], "Objects should be sorted"
    
    # Metrics should be sorted
    assert [m.name for m in ir.metrics] == ["MetricA", "MetricB"], "Metrics should be sorted"
    
    print(f"  [PASS] Lists are sorted correctly")


def main():
    """Run all tests."""
    print("=" * 60)
    print("ODL Core Module Tests")
    print("=" * 60)
    
    tests = [
        test_missing_object_reference,
        test_duplicate_metric_name,
        test_invalid_relationship_cardinality,
        test_relationship_join_key_missing,
        test_valid_odl_passes,
        test_normalize_sorts_lists,
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
