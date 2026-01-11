"""Tests for compiler interface and artifact bundle structure."""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

HAS_COMPILER = False
Compiler = None
ArtifactBundle = None
ArtifactFile = None
MockCompiler = None
ODLIR = None
ObjectIR = None
PropertyIR = None
RelationshipIR = None
MetricIR = None
SnowflakeMappingIR = None

try:
    from src.snowflake.compiler import Compiler, ArtifactBundle, ArtifactFile
    from src.snowflake.mock_compiler import MockCompiler
    from src.odl.ir import ODLIR, ObjectIR, PropertyIR, RelationshipIR, MetricIR, SnowflakeMappingIR
    HAS_COMPILER = True
except ImportError as e:
    print(f"Warning: Could not import compiler modules: {e}")
    HAS_COMPILER = False


def create_test_odl_ir():
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
                    PropertyIR(name="name", type="string")
                ],
                snowflake_table="customers"
            )
        ],
        relationships=[
            RelationshipIR(
                name="placed_by",
                from_object="Order",
                to_object="Customer",
                join_keys=[("customer_id", "customer_id")]
            )
        ],
        metrics=[
            MetricIR(
                name="TotalRevenue",
                expression="SUM(amount)",
                grain=["Order"]
            )
        ],
        snowflake=SnowflakeMappingIR(
            database="TEST_DB",
            schema="PUBLIC"
        )
    )


def test_artifact_bundle_structure():
    """Test that artifact bundle enforces required structure."""
    print("Test: Artifact bundle structure enforcement")
    
    if not HAS_COMPILER:
        print("  [SKIP] Compiler modules not available")
        return
    
    # Create bundle with required files
    bundle = ArtifactBundle(
        files=[],
        instructions_md="# Instructions\nStep 1: Deploy",
        rollback_md="# Rollback\nStep 1: Remove",
        metadata={
            "target": "MOCK",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "version_id": "test-1",
            "checksum": "abc123"
        }
    )
    
    # Check required files exist
    assert bundle.get_file("instructions.md") is not None, "Should have instructions.md"
    assert bundle.get_file("rollback.md") is not None, "Should have rollback.md"
    assert bundle.get_file("metadata.json") is not None, "Should have metadata.json"
    
    # Validate structure
    errors = bundle.validate_structure()
    assert len(errors) == 0, f"Should have no validation errors, got: {errors}"
    
    print("  [PASS] Artifact bundle structure is enforced")


def test_artifact_bundle_metadata_required_fields():
    """Test that metadata.json has all required fields."""
    print("\nTest: Metadata required fields")
    
    if not HAS_COMPILER:
        print("  [SKIP] Compiler modules not available")
        return
    
    bundle = ArtifactBundle(
        files=[],
        instructions_md="# Instructions",
        rollback_md="# Rollback",
        metadata={
            "target": "MOCK",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "version_id": "test-1",
            "checksum": "abc123"
        }
    )
    
    metadata = bundle.get_metadata()
    
    required_fields = ["target", "timestamp", "version_id", "checksum"]
    for field in required_fields:
        assert field in metadata, f"Metadata should have '{field}' field"
    
    print("  [PASS] Metadata has all required fields")
    print(f"    - Target: {metadata['target']}")
    print(f"    - Version ID: {metadata['version_id']}")
    print(f"    - Checksum: {metadata['checksum'][:16]}...")


def test_artifact_bundle_validation_errors():
    """Test that validation catches missing fields."""
    print("\nTest: Validation error detection")
    
    if not HAS_COMPILER:
        print("  [SKIP] Compiler modules not available")
        return
    
    # Create bundle with missing metadata field
    bundle = ArtifactBundle(
        files=[],
        instructions_md="# Instructions",
        rollback_md="# Rollback",
        metadata={
            "target": "MOCK",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            # Missing version_id and checksum
        }
    )
    
    errors = bundle.validate_structure()
    assert len(errors) > 0, "Should have validation errors for missing fields"
    assert any("version_id" in error.lower() or "checksum" in error.lower() for error in errors), \
        "Should detect missing required metadata fields"
    
    print(f"  [PASS] Validation detects missing fields ({len(errors)} error(s))")


def test_mock_compiler_interface():
    """Test that mock compiler implements the interface."""
    print("\nTest: Mock compiler interface")
    
    if not HAS_COMPILER:
        print("  [SKIP] Compiler modules not available")
        return
    
    compiler = MockCompiler()
    
    # Check it's a Compiler
    assert isinstance(compiler, Compiler), "MockCompiler should be a Compiler"
    
    # Check get_target
    target = compiler.get_target()
    assert target == "MOCK", f"Target should be 'MOCK', got '{target}'"
    
    print("  [PASS] Mock compiler implements interface")


def test_mock_compiler_compile():
    """Test that mock compiler produces valid artifact bundle."""
    print("\nTest: Mock compiler compilation")
    
    if not HAS_COMPILER:
        print("  [SKIP] Compiler modules not available")
        return
    
    compiler = MockCompiler()
    odl_ir = create_test_odl_ir()
    
    bundle = compiler.compile(odl_ir, options={"version_id": "test-version-1"})
    
    # Check bundle structure
    assert isinstance(bundle, ArtifactBundle), "Should return ArtifactBundle"
    
    # Validate structure
    errors = bundle.validate_structure()
    assert len(errors) == 0, f"Bundle should be valid, got errors: {errors}"
    
    # Check required files
    assert bundle.get_file("instructions.md") is not None, "Should have instructions.md"
    assert bundle.get_file("rollback.md") is not None, "Should have rollback.md"
    assert bundle.get_file("metadata.json") is not None, "Should have metadata.json"
    
    # Check metadata
    metadata = bundle.get_metadata()
    assert metadata["target"] == "MOCK", "Target should be MOCK"
    assert metadata["version_id"] == "test-version-1", "Version ID should match"
    assert "checksum" in metadata and metadata["checksum"], "Should have checksum"
    assert "timestamp" in metadata, "Should have timestamp"
    
    # Check generated files
    assert bundle.get_file("semantic_model.yaml") is not None, "Should have semantic_model.yaml"
    assert bundle.get_file("deployment.sql") is not None, "Should have deployment.sql"
    
    print("  [PASS] Mock compiler produces valid artifact bundle")
    print(f"    - Files: {len(bundle.files)}")
    print(f"    - Target: {metadata['target']}")
    print(f"    - Checksum: {metadata['checksum'][:16]}...")


def test_artifact_bundle_checksum():
    """Test that checksum is calculated correctly."""
    print("\nTest: Artifact bundle checksum")
    
    if not HAS_COMPILER:
        print("  [SKIP] Compiler modules not available")
        return
    
    bundle1 = ArtifactBundle(
        files=[
            ArtifactFile(path="file1.txt", content="content1"),
            ArtifactFile(path="file2.txt", content="content2")
        ],
        instructions_md="# Instructions",
        rollback_md="# Rollback",
        metadata={"target": "MOCK", "timestamp": "2024-01-01T00:00:00Z", "version_id": "v1", "checksum": ""}
    )
    
    bundle2 = ArtifactBundle(
        files=[
            ArtifactFile(path="file1.txt", content="content1"),
            ArtifactFile(path="file2.txt", content="content2")
        ],
        instructions_md="# Instructions",
        rollback_md="# Rollback",
        metadata={"target": "MOCK", "timestamp": "2024-01-01T00:00:00Z", "version_id": "v1", "checksum": ""}
    )
    
    checksum1 = bundle1.calculate_checksum()
    checksum2 = bundle2.calculate_checksum()
    
    assert checksum1 == checksum2, "Same content should produce same checksum"
    assert len(checksum1) == 64, "SHA256 checksum should be 64 characters"
    
    print("  [PASS] Checksum calculation works correctly")
    print(f"    - Checksum length: {len(checksum1)}")


def test_artifact_bundle_file_operations():
    """Test artifact bundle file operations."""
    print("\nTest: Artifact bundle file operations")
    
    if not HAS_COMPILER:
        print("  [SKIP] Compiler modules not available")
        return
    
    bundle = ArtifactBundle(
        files=[
            ArtifactFile(path="test.txt", content="test content")
        ],
        instructions_md="# Instructions",
        rollback_md="# Rollback",
        metadata={"target": "MOCK", "timestamp": "2024-01-01T00:00:00Z", "version_id": "v1", "checksum": ""}
    )
    
    # Test get_file
    file = bundle.get_file("test.txt")
    assert file is not None, "Should find file"
    assert file.content == "test content", "Content should match"
    
    # Test get_file for non-existent file
    missing = bundle.get_file("missing.txt")
    assert missing is None, "Should return None for missing file"
    
    print("  [PASS] File operations work correctly")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Compiler Interface Tests")
    print("=" * 60)
    
    tests = [
        test_artifact_bundle_structure,
        test_artifact_bundle_metadata_required_fields,
        test_artifact_bundle_validation_errors,
        test_mock_compiler_interface,
        test_mock_compiler_compile,
        test_artifact_bundle_checksum,
        test_artifact_bundle_file_operations,
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
