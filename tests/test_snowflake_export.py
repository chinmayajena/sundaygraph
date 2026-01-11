"""Tests for Snowflake export utility."""

import sys
from pathlib import Path
import tempfile

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.snowflake.export import (
    generate_export_sql,
    create_placeholder_yaml,
    export_semantic_view_yaml
)


def test_generate_export_sql():
    """Test SQL generation."""
    print("Test: Generate export SQL")
    
    semantic_view = "RETAIL_DB.PUBLIC.retail_semantic_view"
    sql = generate_export_sql(semantic_view)
    
    # Check required elements
    assert "SYSTEM$READ_YAML_FROM_SEMANTIC_VIEW" in sql, \
        "Should call SYSTEM$READ_YAML_FROM_SEMANTIC_VIEW"
    assert semantic_view in sql, "Should include semantic view name"
    assert "SELECT" in sql.upper(), "Should be a SELECT query"
    assert "semantic_model_yaml" in sql, "Should alias the result"
    
    print("  [PASS] SQL generation is correct")
    print(f"    - SQL length: {len(sql)} chars")
    return True


def test_create_placeholder_yaml():
    """Test placeholder YAML creation."""
    print("\nTest: Create placeholder YAML")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "test_semantic_model.yaml"
        semantic_view = "RETAIL_DB.PUBLIC.retail_semantic_view"
        
        create_placeholder_yaml(output_path, semantic_view)
        
        assert output_path.exists(), "YAML file should be created"
        
        content = output_path.read_text(encoding='utf-8')
        
        # Check required elements
        assert semantic_view in content, "Should include semantic view name"
        assert "INSTRUCTIONS" in content, "Should have instructions"
        assert "SnowSQL" in content or "snowsql" in content, "Should mention SnowSQL"
        assert "Python connector" in content or "python" in content.lower(), \
            "Should mention Python connector"
        assert "semantic_model:" in content, "Should have semantic_model placeholder"
        
        print("  [PASS] Placeholder YAML is correct")
        print(f"    - File size: {len(content)} chars")
        return True


def test_export_semantic_view_yaml():
    """Test full export function."""
    print("\nTest: Export semantic view YAML")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "semantic_model.yaml"
        semantic_view = "RETAIL_DB.PUBLIC.retail_semantic_view"
        
        sql_path, yaml_path = export_semantic_view_yaml(
            semantic_view_fqname=semantic_view,
            output_path=output_path
        )
        
        # Check files exist
        assert sql_path.exists(), "SQL file should be created"
        assert yaml_path.exists(), "YAML file should be created"
        
        # Check SQL content
        sql_content = sql_path.read_text(encoding='utf-8')
        assert "SYSTEM$READ_YAML_FROM_SEMANTIC_VIEW" in sql_content, \
            "SQL should call SYSTEM$READ_YAML_FROM_SEMANTIC_VIEW"
        assert semantic_view in sql_content, "SQL should include semantic view name"
        
        # Check YAML content
        yaml_content = yaml_path.read_text(encoding='utf-8')
        assert semantic_view in yaml_content, "YAML should include semantic view name"
        assert "INSTRUCTIONS" in yaml_content, "YAML should have instructions"
        
        # Check file paths
        assert sql_path.suffix == ".sql", "SQL file should have .sql extension"
        assert yaml_path.suffix in [".yaml", ".yml"], "YAML file should have .yaml/.yml extension"
        
        print("  [PASS] Export function works correctly")
        print(f"    - SQL file: {sql_path.name}")
        print(f"    - YAML file: {yaml_path.name}")
        return True


def test_export_with_custom_sql_path():
    """Test export with custom SQL path."""
    print("\nTest: Export with custom SQL path")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        yaml_path = Path(tmpdir) / "semantic_model.yaml"
        sql_path = Path(tmpdir) / "custom_export.sql"
        semantic_view = "RETAIL_DB.PUBLIC.retail_semantic_view"
        
        result_sql_path, result_yaml_path = export_semantic_view_yaml(
            semantic_view_fqname=semantic_view,
            output_path=yaml_path,
            sql_output_path=sql_path
        )
        
        assert result_sql_path == sql_path, "Should use custom SQL path"
        assert result_yaml_path == yaml_path, "Should use specified YAML path"
        assert sql_path.exists(), "Custom SQL file should exist"
        
        print("  [PASS] Custom SQL path works correctly")
        return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Snowflake Export Utility Tests")
    print("=" * 60)
    
    tests = [
        test_generate_export_sql,
        test_create_placeholder_yaml,
        test_export_semantic_view_yaml,
        test_export_with_custom_sql_path,
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
