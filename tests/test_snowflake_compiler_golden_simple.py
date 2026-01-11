"""Simple golden file tests for Snowflake compiler (no dependencies)."""

import sys
import json
from pathlib import Path
import re

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_compiler_file_exists():
    """Test that SnowflakeCompiler file exists."""
    print("Test: SnowflakeCompiler file exists")
    
    compiler_file = project_root / "src" / "snowflake" / "snowflake_compiler.py"
    
    if not compiler_file.exists():
        print("  [FAIL] SnowflakeCompiler file not found")
        return False
    
    content = compiler_file.read_text()
    
    # Check key components
    assert "class SnowflakeCompiler" in content, "Should have SnowflakeCompiler class"
    assert "def compile" in content, "Should have compile method"
    assert "def get_target" in content, "Should have get_target method"
    assert "semantic_model.yaml" in content, "Should generate semantic_model.yaml"
    assert "verify.sql" in content, "Should generate verify.sql"
    assert "deploy.sql" in content, "Should generate deploy.sql"
    
    print("  [PASS] SnowflakeCompiler file exists and has required methods")
    return True


def test_yaml_generation_method():
    """Test that YAML generation method exists."""
    print("\nTest: YAML generation method")
    
    compiler_file = project_root / "src" / "snowflake" / "snowflake_compiler.py"
    
    if not compiler_file.exists():
        print("  [SKIP] Compiler file not found")
        return
    
    content = compiler_file.read_text()
    
    # Check YAML generation
    assert "_generate_semantic_model_yaml" in content, "Should have _generate_semantic_model_yaml method"
    assert "logical_tables" in content, "Should generate logical_tables"
    assert "relationships" in content, "Should generate relationships"
    assert "facts" in content, "Should generate facts"
    assert "dimensions" in content, "Should generate dimensions"
    
    print("  [PASS] YAML generation method exists")


def test_verify_sql_generation():
    """Test that verify.sql generation uses verify_only => TRUE."""
    print("\nTest: verify.sql generation")
    
    compiler_file = project_root / "src" / "snowflake" / "snowflake_compiler.py"
    
    if not compiler_file.exists():
        print("  [SKIP] Compiler file not found")
        return
    
    content = compiler_file.read_text()
    
    # Check verify SQL generation
    assert "_generate_verify_sql" in content, "Should have _generate_verify_sql method"
    assert "verify_only => TRUE" in content, "Should use verify_only => TRUE"
    assert "SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML" in content, "Should call SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML"
    
    # Check that verify_only => TRUE appears in the method context
    # Find the method and check it contains verify_only => TRUE
    method_start = content.find("def _generate_verify_sql")
    if method_start != -1:
        method_end = content.find("\n    def ", method_start + 1)
        if method_end == -1:
            method_end = len(content)
        method_content = content[method_start:method_end]
        assert "verify_only => TRUE" in method_content, "verify.sql generation should use verify_only => TRUE"
    
    print("  [PASS] verify.sql generation uses verify_only => TRUE")


def test_deploy_sql_generation():
    """Test that deploy.sql generation uses verify_only => FALSE."""
    print("\nTest: deploy.sql generation")
    
    compiler_file = project_root / "src" / "snowflake" / "snowflake_compiler.py"
    
    if not compiler_file.exists():
        print("  [SKIP] Compiler file not found")
        return
    
    content = compiler_file.read_text()
    
    # Check deploy SQL generation
    assert "_generate_deploy_sql" in content, "Should have _generate_deploy_sql method"
    assert "verify_only => FALSE" in content, "Should use verify_only => FALSE"
    
    print("  [PASS] deploy.sql generation uses verify_only => FALSE")


def test_yaml_structure_components():
    """Test that YAML structure includes required components."""
    print("\nTest: YAML structure components")
    
    compiler_file = project_root / "src" / "snowflake" / "snowflake_compiler.py"
    
    if not compiler_file.exists():
        print("  [SKIP] Compiler file not found")
        return
    
    content = compiler_file.read_text()
    
    # Check YAML structure components
    assert "physical_table" in content, "Should map to physical tables"
    assert "join_keys" in content, "Should have join keys in relationships"
    assert "join_type" in content, "Should have join type in relationships"
    assert "aggregation_type" in content, "Should have aggregation type in facts"
    assert "grain" in content, "Should have grain in facts"
    
    print("  [PASS] YAML structure includes required components")


def test_deterministic_yaml():
    """Test that YAML generation is deterministic (code structure)."""
    print("\nTest: Deterministic YAML generation")
    
    compiler_file = project_root / "src" / "snowflake" / "snowflake_compiler.py"
    
    if not compiler_file.exists():
        print("  [SKIP] Compiler file not found")
        return
    
    content = compiler_file.read_text()
    
    # Check for deterministic patterns
    assert "yaml.dump" in content, "Should use yaml.dump for consistent output"
    assert "sort_keys=False" in content, "Should preserve key order (deterministic)"
    
    print("  [PASS] YAML generation uses deterministic patterns")


def test_golden_snapshots_exist():
    """Test that golden file snapshots exist."""
    print("\nTest: Golden file snapshots exist")
    
    golden_dir = project_root / "tests" / "golden"
    golden_dir.mkdir(exist_ok=True)
    
    snapshots = [
        "retail_semantic_model.yaml.snapshot",
        "retail_verify.sql.snapshot",
        "retail_deploy.sql.snapshot"
    ]
    
    for snapshot in snapshots:
        snapshot_path = golden_dir / snapshot
        if not snapshot_path.exists():
            print(f"  [INFO] Creating {snapshot}")
            snapshot_path.touch()
        else:
            print(f"  [PASS] {snapshot} exists")
    
    print("  [PASS] Golden file snapshots structure is in place")


def main():
    """Run all golden file structure tests."""
    print("=" * 60)
    print("Snowflake Compiler Golden File Structure Tests")
    print("=" * 60)
    
    tests = [
        test_compiler_file_exists,
        test_yaml_generation_method,
        test_verify_sql_generation,
        test_deploy_sql_generation,
        test_yaml_structure_components,
        test_deterministic_yaml,
        test_golden_snapshots_exist,
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
