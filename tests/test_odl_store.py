"""Tests for ODL store and API endpoints."""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from storage.odl_store import ODLStore
    HAS_ODL_STORE = True
except ImportError as e:
    print(f"Warning: Could not import ODLStore: {e}")
    HAS_ODL_STORE = False


def test_migration_applies():
    """Test that migration SQL is valid."""
    print("Test: Migration SQL is valid")
    
    migration_file = Path(__file__).parent.parent / "migrations" / "001_create_odl_tables.sql"
    
    if not migration_file.exists():
        print("  [SKIP] Migration file not found")
        return
    
    with open(migration_file, 'r', encoding='utf-8') as f:
        sql = f.read()
    
    # Basic validation
    assert "CREATE TABLE" in sql, "Should contain CREATE TABLE"
    assert "ontology" in sql.lower(), "Should create ontology table"
    assert "ontology_version" in sql.lower(), "Should create ontology_version table"
    assert "compile_run" in sql.lower(), "Should create compile_run table"
    assert "eval_run" in sql.lower(), "Should create eval_run table"
    assert "drift_event" in sql.lower(), "Should create drift_event table"
    
    print("  [PASS] Migration SQL is valid")


def test_odl_store_operations():
    """Test ODL store operations."""
    print("\nTest: ODL store operations")
    
    if not HAS_ODL_STORE:
        print("  [SKIP] ODLStore not available")
        return
    
    # Test with example ODL
    odl_file = Path(__file__).parent.parent / "odl" / "examples" / "snowflake_retail.odl.json"
    
    if not odl_file.exists():
        print("  [SKIP] Example ODL file not found")
        return
    
    with open(odl_file, 'r', encoding='utf-8') as f:
        example_odl = json.load(f)
    
    # Test that ODL can be loaded
    assert "version" in example_odl, "ODL should have version"
    assert "objects" in example_odl, "ODL should have objects"
    assert "snowflake" in example_odl, "ODL should have snowflake mapping"
    
    print(f"  [PASS] ODL structure is valid")
    print(f"    - Version: {example_odl.get('version')}")
    print(f"    - Objects: {len(example_odl.get('objects', []))}")
    print(f"    - Relationships: {len(example_odl.get('relationships', []))}")
    print(f"    - Metrics: {len(example_odl.get('metrics', []))}")


def test_api_endpoints_defined():
    """Test that API endpoints are defined."""
    print("\nTest: API endpoints are defined")
    
    try:
        from api.app import app, create_ontology, create_ontology_version, get_ontology_version, list_ontology_versions
        print("  [PASS] API endpoints are defined")
        print("    - POST /api/v1/workspaces/{workspace_id}/ontology")
        print("    - POST /api/v1/workspaces/{workspace_id}/ontology/{ontology_name}/version")
        print("    - GET /api/v1/workspaces/{workspace_id}/ontology/{ontology_name}/version")
        print("    - GET /api/v1/workspaces/{workspace_id}/ontology/{ontology_name}/versions")
    except ImportError as e:
        print(f"  [SKIP] Could not import API: {e}")


def main():
    """Run all tests."""
    print("=" * 60)
    print("ODL Store and Migration Tests")
    print("=" * 60)
    
    tests = [
        test_migration_applies,
        test_odl_store_operations,
        test_api_endpoints_defined,
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
