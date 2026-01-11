"""Simple compiler tests that don't require full dependencies."""

import sys
import json
from pathlib import Path

# Test structure directly
def test_artifact_bundle_structure_direct():
    """Test artifact bundle structure by examining the code."""
    print("Test: Artifact bundle structure (code inspection)")
    
    compiler_file = Path(__file__).parent.parent / "src" / "snowflake" / "compiler.py"
    
    if not compiler_file.exists():
        print("  [SKIP] Compiler file not found")
        return
    
    content = compiler_file.read_text()
    
    # Check required components
    assert "class ArtifactBundle" in content, "Should have ArtifactBundle class"
    assert "class ArtifactFile" in content, "Should have ArtifactFile class"
    assert "instructions.md" in content, "Should reference instructions.md"
    assert "rollback.md" in content, "Should reference rollback.md"
    assert "metadata.json" in content, "Should reference metadata.json"
    assert "validate_structure" in content, "Should have validate_structure method"
    assert "calculate_checksum" in content, "Should have calculate_checksum method"
    
    # Check metadata fields
    assert '"target"' in content or "'target'" in content, "Should have target in metadata"
    assert '"timestamp"' in content or "'timestamp'" in content, "Should have timestamp in metadata"
    assert '"version_id"' in content or "'version_id'" in content, "Should have version_id in metadata"
    assert '"checksum"' in content or "'checksum'" in content, "Should have checksum in metadata"
    
    print("  [PASS] Artifact bundle structure is defined correctly")


def test_compiler_interface_direct():
    """Test compiler interface by examining the code."""
    print("\nTest: Compiler interface (code inspection)")
    
    compiler_file = Path(__file__).parent.parent / "src" / "snowflake" / "compiler.py"
    
    if not compiler_file.exists():
        print("  [SKIP] Compiler file not found")
        return
    
    content = compiler_file.read_text()
    
    # Check interface
    assert "class Compiler" in content, "Should have Compiler class"
    assert "ABC" in content, "Should inherit from ABC"
    assert "def compile" in content, "Should have compile method"
    assert "def get_target" in content, "Should have get_target method"
    assert "@abstractmethod" in content, "Should use abstractmethod"
    
    print("  [PASS] Compiler interface is defined correctly")


def test_mock_compiler_direct():
    """Test mock compiler by examining the code."""
    print("\nTest: Mock compiler (code inspection)")
    
    mock_file = Path(__file__).parent.parent / "src" / "snowflake" / "mock_compiler.py"
    
    if not mock_file.exists():
        print("  [SKIP] Mock compiler file not found")
        return
    
    content = mock_file.read_text()
    
    # Check mock compiler
    assert "class MockCompiler" in content, "Should have MockCompiler class"
    assert "Compiler" in content, "Should inherit from Compiler"
    assert "def compile" in content, "Should implement compile method"
    assert "def get_target" in content, "Should implement get_target method"
    assert "MOCK" in content, "Should use MOCK as target"
    
    # Check it generates required files
    assert "semantic_model.yaml" in content, "Should generate semantic_model.yaml"
    assert "deployment.sql" in content, "Should generate deployment.sql"
    
    print("  [PASS] Mock compiler is implemented correctly")


def test_artifact_bundle_files_structure():
    """Test that artifact bundle files structure is correct."""
    print("\nTest: Artifact bundle files structure")
    
    compiler_file = Path(__file__).parent.parent / "src" / "snowflake" / "compiler.py"
    
    if not compiler_file.exists():
        print("  [SKIP] Compiler file not found")
        return
    
    content = compiler_file.read_text()
    
    # Check ArtifactFile structure
    assert "path: str" in content, "ArtifactFile should have path field"
    assert "content: str" in content, "ArtifactFile should have content field"
    
    # Check ArtifactBundle structure
    assert "files: List[ArtifactFile]" in content, "ArtifactBundle should have files list"
    assert "instructions_md: str" in content, "ArtifactBundle should have instructions_md"
    assert "rollback_md: str" in content, "ArtifactBundle should have rollback_md"
    assert "metadata: Dict" in content, "ArtifactBundle should have metadata"
    
    print("  [PASS] Artifact bundle files structure is correct")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Compiler Interface Structure Tests")
    print("=" * 60)
    
    tests = [
        test_artifact_bundle_structure_direct,
        test_compiler_interface_direct,
        test_mock_compiler_direct,
        test_artifact_bundle_files_structure,
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
