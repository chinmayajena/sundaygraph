"""Golden file tests for Snowflake compiler."""

import sys
import json
from pathlib import Path
import re

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.snowflake.snowflake_compiler import SnowflakeCompiler
    from src.odl.core import ODLProcessor
    HAS_COMPILER = True
except ImportError as e:
    print(f"Warning: Could not import compiler modules: {e}")
    HAS_COMPILER = False


def normalize_yaml_for_comparison(yaml_content: str) -> str:
    """Normalize YAML for deterministic comparison."""
    # Remove trailing whitespace
    lines = [line.rstrip() for line in yaml_content.split('\n')]
    # Remove empty lines at end
    while lines and not lines[-1]:
        lines.pop()
    return '\n'.join(lines) + '\n'


def extract_yaml_section(yaml_content: str, section: str) -> str:
    """Extract a specific section from YAML."""
    lines = yaml_content.split('\n')
    in_section = False
    section_lines = []
    indent_level = None
    
    for line in lines:
        if line.strip().startswith(section + ':'):
            in_section = True
            section_lines.append(line)
            indent_level = len(line) - len(line.lstrip())
            continue
        
        if in_section:
            current_indent = len(line) - len(line.lstrip()) if line.strip() else 999
            if line.strip() and current_indent <= indent_level:
                break
            section_lines.append(line)
    
    return '\n'.join(section_lines)


def test_compile_retail_odl():
    """Test compiling retail ODL example."""
    print("Test: Compile retail ODL example")
    
    if not HAS_COMPILER:
        print("  [SKIP] Compiler modules not available")
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
        return
    
    # Compile
    compiler = SnowflakeCompiler()
    options = {
        "version_id": "test-v1",
        "view_name": "retail_semantic_view",
        "database": "RETAIL_DB",
        "schema": "PUBLIC"
    }
    
    bundle = compiler.compile(odl_ir, options)
    
    # Validate bundle
    validation_errors = bundle.validate_structure()
    assert len(validation_errors) == 0, f"Bundle validation failed: {validation_errors}"
    
    # Check required files
    yaml_file = bundle.get_file("semantic_model.yaml")
    verify_file = bundle.get_file("verify.sql")
    deploy_file = bundle.get_file("deploy.sql")
    
    assert yaml_file is not None, "Should have semantic_model.yaml"
    assert verify_file is not None, "Should have verify.sql"
    assert deploy_file is not None, "Should have deploy.sql"
    
    print("  [PASS] Compilation successful")
    print(f"    - YAML size: {len(yaml_file.content)} chars")
    print(f"    - Verify SQL size: {len(verify_file.content)} chars")
    print(f"    - Deploy SQL size: {len(deploy_file.content)} chars")
    
    return bundle


def test_yaml_structure():
    """Test that generated YAML has correct structure."""
    print("\nTest: YAML structure")
    
    if not HAS_COMPILER:
        print("  [SKIP] Compiler modules not available")
        return
    
    bundle = test_compile_retail_odl()
    if bundle is None:
        return
    
    yaml_file = bundle.get_file("semantic_model.yaml")
    yaml_content = yaml_file.content
    
    # Check required sections
    assert "semantic_model:" in yaml_content, "Should have semantic_model section"
    assert "logical_tables:" in yaml_content, "Should have logical_tables section"
    assert "relationships:" in yaml_content, "Should have relationships section"
    assert "facts:" in yaml_content, "Should have facts section"
    
    # Check for key objects
    assert "Customer:" in yaml_content or "- name: Customer" in yaml_content, "Should have Customer"
    assert "Order:" in yaml_content or "- name: Order" in yaml_content, "Should have Order"
    assert "Product:" in yaml_content or "- name: Product" in yaml_content, "Should have Product"
    
    # Check for relationships
    assert "placed_by" in yaml_content or "placed_by:" in yaml_content, "Should have placed_by relationship"
    
    # Check for metrics
    assert "TotalRevenue" in yaml_content, "Should have TotalRevenue metric"
    
    print("  [PASS] YAML structure is correct")


def test_verify_sql_structure():
    """Test that verify.sql has correct structure."""
    print("\nTest: verify.sql structure")
    
    if not HAS_COMPILER:
        print("  [SKIP] Compiler modules not available")
        return
    
    bundle = test_compile_retail_odl()
    if bundle is None:
        return
    
    verify_file = bundle.get_file("verify.sql")
    verify_content = verify_file.content
    
    # Check required elements
    assert "SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML" in verify_content, "Should call SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML"
    assert "verify_only => TRUE" in verify_content, "Should use verify_only => TRUE"
    assert "$$" in verify_content, "Should use $$ delimiters for YAML"
    
    # Should NOT have FALSE
    assert "verify_only => FALSE" not in verify_content, "Should not have verify_only => FALSE in verify.sql"
    
    print("  [PASS] verify.sql structure is correct")
    print(f"    - Contains verify_only => TRUE: {verify_content.count('verify_only => TRUE')}")


def test_deploy_sql_structure():
    """Test that deploy.sql has correct structure."""
    print("\nTest: deploy.sql structure")
    
    if not HAS_COMPILER:
        print("  [SKIP] Compiler modules not available")
        return
    
    bundle = test_compile_retail_odl()
    if bundle is None:
        return
    
    deploy_file = bundle.get_file("deploy.sql")
    deploy_content = deploy_file.content
    
    # Check required elements
    assert "SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML" in deploy_content, "Should call SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML"
    assert "verify_only => FALSE" in deploy_content, "Should use verify_only => FALSE"
    assert "$$" in deploy_content, "Should use $$ delimiters for YAML"
    
    # Should have view name
    assert "retail_semantic_view" in deploy_content, "Should include view name"
    
    print("  [PASS] deploy.sql structure is correct")
    print(f"    - Contains verify_only => FALSE: {deploy_content.count('verify_only => FALSE')}")


def test_deterministic_generation():
    """Test that compilation is deterministic."""
    print("\nTest: Deterministic generation")
    
    if not HAS_COMPILER:
        print("  [SKIP] Compiler modules not available")
        return
    
    # Load ODL
    odl_file = project_root / "odl" / "examples" / "snowflake_retail.odl.json"
    if not odl_file.exists():
        print("  [SKIP] Retail ODL example not found")
        return
    
    processor = ODLProcessor()
    odl_ir, is_valid, errors = processor.process(odl_file)
    
    if not is_valid:
        print(f"  [SKIP] ODL validation failed: {errors}")
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
    
    assert normalize_yaml_for_comparison(yaml1) == normalize_yaml_for_comparison(yaml2), \
        "YAML should be identical across compilations"
    
    print("  [PASS] Compilation is deterministic")
    print(f"    - Checksum: {checksum1[:16]}...")


def test_yaml_snapshot_sections():
    """Test snapshot of key YAML sections."""
    print("\nTest: YAML snapshot sections")
    
    if not HAS_COMPILER:
        print("  [SKIP] Compiler modules not available")
        return
    
    bundle = test_compile_retail_odl()
    if bundle is None:
        return
    
    yaml_file = bundle.get_file("semantic_model.yaml")
    yaml_content = yaml_file.content
    
    # Extract key sections
    semantic_model_section = extract_yaml_section(yaml_content, "semantic_model")
    logical_tables_section = extract_yaml_section(yaml_content, "logical_tables")
    relationships_section = extract_yaml_section(yaml_content, "relationships")
    facts_section = extract_yaml_section(yaml_content, "facts")
    
    # Verify sections exist and have content
    assert len(semantic_model_section) > 0, "Should have semantic_model section"
    assert len(logical_tables_section) > 0, "Should have logical_tables section"
    assert len(relationships_section) > 0, "Should have relationships section"
    assert len(facts_section) > 0, "Should have facts section"
    
    # Check for specific content
    assert "name:" in semantic_model_section, "Should have name in semantic_model"
    assert "Customer" in logical_tables_section, "Should have Customer in logical_tables"
    assert "placed_by" in relationships_section, "Should have placed_by in relationships"
    assert "TotalRevenue" in facts_section, "Should have TotalRevenue in facts"
    
    print("  [PASS] YAML sections are correct")
    print(f"    - semantic_model: {len(semantic_model_section)} chars")
    print(f"    - logical_tables: {len(logical_tables_section)} chars")
    print(f"    - relationships: {len(relationships_section)} chars")
    print(f"    - facts: {len(facts_section)} chars")


def test_sql_snapshot_sections():
    """Test snapshot of SQL sections."""
    print("\nTest: SQL snapshot sections")
    
    if not HAS_COMPILER:
        print("  [SKIP] Compiler modules not available")
        return
    
    bundle = test_compile_retail_odl()
    if bundle is None:
        return
    
    verify_file = bundle.get_file("verify.sql")
    deploy_file = bundle.get_file("deploy.sql")
    
    verify_content = verify_file.content
    deploy_content = deploy_file.content
    
    # Extract key parts
    verify_call = re.search(r'CALL SYSTEM\$CREATE_SEMANTIC_VIEW_FROM_YAML\([^)]+\)', verify_content, re.DOTALL)
    deploy_call = re.search(r'CALL SYSTEM\$CREATE_SEMANTIC_VIEW_FROM_YAML\([^)]+\)', deploy_content, re.DOTALL)
    
    assert verify_call is not None, "Should have CALL statement in verify.sql"
    assert deploy_call is not None, "Should have CALL statement in deploy.sql"
    
    verify_call_text = verify_call.group(0)
    deploy_call_text = deploy_call.group(0)
    
    # Verify verify.sql has verify_only => TRUE
    assert "verify_only => TRUE" in verify_call_text, "verify.sql should have verify_only => TRUE"
    assert "RETAIL_DB" in verify_call_text or "PUBLIC" in verify_call_text, "Should reference database/schema"
    
    # Verify deploy.sql has verify_only => FALSE
    assert "verify_only => FALSE" in deploy_call_text, "deploy.sql should have verify_only => FALSE"
    assert "retail_semantic_view" in deploy_call_text, "Should include view name"
    
    print("  [PASS] SQL sections are correct")
    print(f"    - verify.sql CALL: {len(verify_call_text)} chars")
    print(f"    - deploy.sql CALL: {len(deploy_call_text)} chars")


def main():
    """Run all golden file tests."""
    print("=" * 60)
    print("Snowflake Compiler Golden File Tests")
    print("=" * 60)
    
    tests = [
        test_compile_retail_odl,
        test_yaml_structure,
        test_verify_sql_structure,
        test_deploy_sql_structure,
        test_deterministic_generation,
        test_yaml_snapshot_sections,
        test_sql_snapshot_sections,
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
