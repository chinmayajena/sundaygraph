"""Tests for promotion bundle generator."""

import sys
from pathlib import Path
import tempfile
import zipfile
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.snowflake.promotion_bundle import PromotionBundleGenerator
from src.odl.core import ODLProcessor


def test_promotion_bundle_generation():
    """Test promotion bundle generation."""
    print("Test 1: Generate promotion bundle")
    
    # Load ODL
    odl_file = project_root / "odl" / "examples" / "snowflake_retail.odl.json"
    if not odl_file.exists():
        print("  [SKIP] ODL file not found")
        return
    
    processor = ODLProcessor()
    odl_ir, is_valid, errors = processor.process(str(odl_file))
    
    if not is_valid:
        print(f"  [FAIL] ODL validation failed: {errors}")
        return
    
    # Generate bundle
    generator = PromotionBundleGenerator()
    environments = {
        "dev": {
            "database": "DEV_DB",
            "schema": "PUBLIC",
            "view_name": "dev_semantic_view"
        },
        "prod": {
            "database": "PROD_DB",
            "schema": "PUBLIC",
            "view_name": "prod_semantic_view"
        }
    }
    
    bundle = generator.generate_promotion_bundle(
        odl_ir=odl_ir,
        environments=environments,
        options={"version_id": "test-v1"}
    )
    
    # Check bundle structure
    assert bundle is not None, "Bundle should be created"
    
    # Check required files
    required_files = [
        "semantic_model.yaml",
        "instructions.md",
        "rollback.md",
        "metadata.json",
        "dev/verify.sql",
        "dev/deploy.sql",
        "dev/rollback.sql",
        "prod/verify.sql",
        "prod/deploy.sql",
        "prod/rollback.sql"
    ]
    
    for required_file in required_files:
        file = bundle.get_file(required_file)
        assert file is not None, f"Missing required file: {required_file}"
        assert len(file.content) > 0, f"File {required_file} is empty"
    
    print("  [PASS] Promotion bundle generated with all required files")


def test_zip_bundle_creation():
    """Test ZIP bundle creation."""
    print("\nTest 2: Create ZIP bundle")
    
    # Load ODL
    odl_file = project_root / "odl" / "examples" / "snowflake_retail.odl.json"
    if not odl_file.exists():
        print("  [SKIP] ODL file not found")
        return
    
    processor = ODLProcessor()
    odl_ir, is_valid, errors = processor.process(str(odl_file))
    
    if not is_valid:
        print(f"  [FAIL] ODL validation failed: {errors}")
        return
    
    # Generate bundle
    generator = PromotionBundleGenerator()
    environments = {
        "dev": {
            "database": "DEV_DB",
            "schema": "PUBLIC",
            "view_name": "dev_semantic_view"
        }
    }
    
    bundle = generator.generate_promotion_bundle(
        odl_ir=odl_ir,
        environments=environments
    )
    
    # Create ZIP
    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as f:
        zip_path = Path(f.name)
    
    try:
        generator.create_zip_bundle(bundle, zip_path)
        
        assert zip_path.exists(), "ZIP file should be created"
        
        # Verify ZIP contents
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            files = zipf.namelist()
            
            assert "semantic_model.yaml" in files
            assert "dev/verify.sql" in files
            assert "dev/deploy.sql" in files
            assert "dev/rollback.sql" in files
        
        print("  [PASS] ZIP bundle created with correct structure")
    finally:
        if zip_path.exists():
            zip_path.unlink()


def test_rollback_sql_generation():
    """Test rollback SQL generation."""
    print("\nTest 3: Rollback SQL generation")
    
    generator = PromotionBundleGenerator()
    
    # Test without existing view (no provider)
    rollback_sql, rollback_yaml = generator._generate_rollback_sql(
        semantic_view_fqname="TEST_DB.PUBLIC.test_view",
        database="TEST_DB",
        schema="PUBLIC",
        view_name="test_view",
        new_yaml="test: yaml"
    )
    
    assert rollback_sql is not None
    assert "DROP VIEW" in rollback_sql
    assert rollback_yaml is None  # No provider, so no YAML
    
    print("  [PASS] Rollback SQL generated correctly")


def test_metadata_includes_environments():
    """Test that metadata includes environment information."""
    print("\nTest 4: Metadata includes environments")
    
    odl_file = project_root / "odl" / "examples" / "snowflake_retail.odl.json"
    if not odl_file.exists():
        print("  [SKIP] ODL file not found")
        return
    
    processor = ODLProcessor()
    odl_ir, is_valid, errors = processor.process(str(odl_file))
    
    if not is_valid:
        print(f"  [FAIL] ODL validation failed: {errors}")
        return
    
    generator = PromotionBundleGenerator()
    environments = {
        "dev": {"database": "DEV_DB", "schema": "PUBLIC", "view_name": "dev_view"},
        "prod": {"database": "PROD_DB", "schema": "PUBLIC", "view_name": "prod_view"}
    }
    
    bundle = generator.generate_promotion_bundle(odl_ir, environments)
    metadata = bundle.get_metadata()
    
    assert metadata.get("promotion_bundle") is True
    assert "environments" in metadata
    assert set(metadata["environments"]) == {"dev", "prod"}
    
    print("  [PASS] Metadata includes environment information")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Promotion Bundle Tests")
    print("=" * 60)
    
    tests = [
        test_promotion_bundle_generation,
        test_zip_bundle_creation,
        test_rollback_sql_generation,
        test_metadata_includes_environments,
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
