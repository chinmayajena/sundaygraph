"""Integration test for SnowflakeCompiler with actual compilation."""

import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import yaml
    from src.snowflake.snowflake_compiler import SnowflakeCompiler
    from src.odl.core import ODLProcessor
    HAS_DEPS = True
except ImportError as e:
    print(f"Warning: Missing dependencies: {e}")
    HAS_DEPS = False


def test_compile_retail_odl_to_yaml():
    """Test compiling retail ODL to semantic model YAML."""
    print("Test: Compile retail ODL to YAML")
    
    if not HAS_DEPS:
        print("  [SKIP] Missing dependencies")
        return
    
    # Load ODL
    odl_file = project_root / "odl" / "examples" / "snowflake_retail.odl.json"
    if not odl_file.exists():
        print("  [SKIP] Retail ODL example not found")
        return
    
    processor = ODLProcessor()
    odl_ir, is_valid, errors = processor.process(odl_file)
    
    if not is_valid:
        print(f"  [FAIL] ODL validation failed: {errors}")
        return False
    
    # Compile
    compiler = SnowflakeCompiler()
    options = {
        "version_id": "test-v1",
        "view_name": "retail_semantic_view",
        "database": "RETAIL_DB",
        "schema": "PUBLIC"
    }
    
    bundle = compiler.compile(odl_ir, options)
    
    # Get YAML
    yaml_file = bundle.get_file("semantic_model.yaml")
    assert yaml_file is not None, "Should have semantic_model.yaml"
    
    # Parse YAML
    yaml_data = yaml.safe_load(yaml_file.content)
    
    # Verify structure
    assert "semantic_model" in yaml_data, "Should have semantic_model root"
    sm = yaml_data["semantic_model"]
    
    assert "name" in sm, "Should have name"
    assert "version" in sm, "Should have version"
    assert "logical_tables" in sm, "Should have logical_tables"
    assert "relationships" in sm, "Should have relationships"
    assert "facts" in sm, "Should have facts"
    assert "dimensions" in sm, "Should have dimensions"
    
    # Verify logical tables
    logical_tables = sm["logical_tables"]
    assert len(logical_tables) >= 4, "Should have at least 4 logical tables"
    
    table_names = [t["name"] for t in logical_tables]
    assert "Customer" in table_names, "Should have Customer table"
    assert "Order" in table_names, "Should have Order table"
    assert "Product" in table_names, "Should have Product table"
    assert "OrderItem" in table_names, "Should have OrderItem table"
    
    # Verify Customer table structure
    customer_table = next(t for t in logical_tables if t["name"] == "Customer")
    assert "physical_table" in customer_table, "Should have physical_table"
    assert customer_table["physical_table"]["table"] == "customers", "Should map to customers table"
    assert "primary_key" in customer_table, "Should have primary_key"
    assert customer_table["primary_key"] == "customer_id", "Should have customer_id as primary key"
    
    # Verify relationships
    relationships = sm["relationships"]
    assert len(relationships) >= 1, "Should have at least 1 relationship"
    
    rel_names = [r["name"] for r in relationships]
    assert "placed_by" in rel_names, "Should have placed_by relationship"
    
    placed_by = next(r for r in relationships if r["name"] == "placed_by")
    assert placed_by["from_table"] == "Order", "placed_by should be from Order"
    assert placed_by["to_table"] == "Customer", "placed_by should be to Customer"
    assert "join_keys" in placed_by, "Should have join_keys"
    assert len(placed_by["join_keys"]) > 0, "Should have at least one join key"
    
    # Verify facts/metrics
    facts = sm["facts"]
    assert len(facts) >= 3, "Should have at least 3 facts"
    
    fact_names = [f["name"] for f in facts]
    assert "TotalRevenue" in fact_names, "Should have TotalRevenue fact"
    assert "OrderCount" in fact_names, "Should have OrderCount fact"
    
    total_revenue = next(f for f in facts if f["name"] == "TotalRevenue")
    assert "expression" in total_revenue, "Should have expression"
    assert "grain" in total_revenue, "Should have grain"
    assert "aggregation_type" in total_revenue, "Should have aggregation_type"
    
    # Verify dimensions
    dimensions = sm["dimensions"]
    assert len(dimensions) >= 1, "Should have at least 1 dimension"
    
    dim_names = [d["name"] for d in dimensions]
    assert "CustomerName" in dim_names, "Should have CustomerName dimension"
    
    print("  [PASS] YAML structure is correct")
    return True


def test_verify_sql_content():
    """Test verify.sql content."""
    print("\nTest: verify.sql content")
    
    if not HAS_DEPS:
        print("  [SKIP] Missing dependencies")
        return
    
    # Load and compile
    odl_file = project_root / "odl" / "examples" / "snowflake_retail.odl.json"
    if not odl_file.exists():
        print("  [SKIP] Retail ODL example not found")
        return
    
    processor = ODLProcessor()
    odl_ir, is_valid, errors = processor.process(odl_file)
    
    if not is_valid:
        print("  [SKIP] ODL validation failed")
        return
    
    compiler = SnowflakeCompiler()
    options = {
        "version_id": "test-v1",
        "view_name": "retail_semantic_view",
        "database": "RETAIL_DB",
        "schema": "PUBLIC"
    }
    
    bundle = compiler.compile(odl_ir, options)
    
    verify_file = bundle.get_file("verify.sql")
    assert verify_file is not None, "Should have verify.sql"
    
    verify_content = verify_file.content
    
    # Check required elements
    assert "CALL SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML" in verify_content, \
        "Should call SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML"
    assert "verify_only => TRUE" in verify_content, "Should use verify_only => TRUE"
    assert "RETAIL_DB.PUBLIC" in verify_content, "Should reference database.schema"
    assert "$$" in verify_content, "Should use $$ delimiters"
    
    # Should NOT have FALSE
    assert "verify_only => FALSE" not in verify_content, \
        "verify.sql should not have verify_only => FALSE"
    
    print("  [PASS] verify.sql content is correct")


def test_deploy_sql_content():
    """Test deploy.sql content."""
    print("\nTest: deploy.sql content")
    
    if not HAS_DEPS:
        print("  [SKIP] Missing dependencies")
        return
    
    # Load and compile
    odl_file = project_root / "odl" / "examples" / "snowflake_retail.odl.json"
    if not odl_file.exists():
        print("  [SKIP] Retail ODL example not found")
        return
    
    processor = ODLProcessor()
    odl_ir, is_valid, errors = processor.process(odl_file)
    
    if not is_valid:
        print("  [SKIP] ODL validation failed")
        return
    
    compiler = SnowflakeCompiler()
    options = {
        "version_id": "test-v1",
        "view_name": "retail_semantic_view",
        "database": "RETAIL_DB",
        "schema": "PUBLIC"
    }
    
    bundle = compiler.compile(odl_ir, options)
    
    deploy_file = bundle.get_file("deploy.sql")
    assert deploy_file is not None, "Should have deploy.sql"
    
    deploy_content = deploy_file.content
    
    # Check required elements
    assert "CALL SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML" in deploy_content, \
        "Should call SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML"
    assert "verify_only => FALSE" in deploy_content, "Should use verify_only => FALSE"
    assert "RETAIL_DB.PUBLIC" in deploy_content, "Should reference database.schema"
    assert "$$" in deploy_content, "Should use $$ delimiters"
    assert "retail_semantic_view" in deploy_content, "Should include view name"
    
    # Should NOT have TRUE
    assert "verify_only => TRUE" not in deploy_content, \
        "deploy.sql should not have verify_only => TRUE"
    
    print("  [PASS] deploy.sql content is correct")


def test_deterministic_compilation():
    """Test that compilation is deterministic."""
    print("\nTest: Deterministic compilation")
    
    if not HAS_DEPS:
        print("  [SKIP] Missing dependencies")
        return
    
    # Load ODL
    odl_file = project_root / "odl" / "examples" / "snowflake_retail.odl.json"
    if not odl_file.exists():
        print("  [SKIP] Retail ODL example not found")
        return
    
    processor = ODLProcessor()
    odl_ir, is_valid, errors = processor.process(odl_file)
    
    if not is_valid:
        print("  [SKIP] ODL validation failed")
        return
    
    compiler = SnowflakeCompiler()
    options = {
        "version_id": "test-v1",
        "view_name": "retail_semantic_view",
        "database": "RETAIL_DB",
        "schema": "PUBLIC"
    }
    
    # Compile twice
    bundle1 = compiler.compile(odl_ir, options)
    bundle2 = compiler.compile(odl_ir, options)
    
    # Compare checksums
    checksum1 = bundle1.calculate_checksum()
    checksum2 = bundle2.calculate_checksum()
    
    assert checksum1 == checksum2, "Compilation should be deterministic (same checksum)"
    
    # Compare YAML content
    yaml1 = bundle1.get_file("semantic_model.yaml").content
    yaml2 = bundle2.get_file("semantic_model.yaml").content
    
    assert yaml1 == yaml2, "YAML should be identical across compilations"
    
    # Compare SQL content
    verify1 = bundle1.get_file("verify.sql").content
    verify2 = bundle2.get_file("verify.sql").content
    
    assert verify1 == verify2, "verify.sql should be identical across compilations"
    
    deploy1 = bundle1.get_file("deploy.sql").content
    deploy2 = bundle2.get_file("deploy.sql").content
    
    assert deploy1 == deploy2, "deploy.sql should be identical across compilations"
    
    print("  [PASS] Compilation is deterministic")
    print(f"    - Checksum: {checksum1[:16]}...")


def main():
    """Run all integration tests."""
    print("=" * 60)
    print("Snowflake Compiler Integration Tests")
    print("=" * 60)
    
    tests = [
        test_compile_retail_odl_to_yaml,
        test_verify_sql_content,
        test_deploy_sql_content,
        test_deterministic_compilation,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            result = test()
            if result is False:
                failed += 1
            else:
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
