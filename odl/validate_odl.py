#!/usr/bin/env python3
"""
ODL Validation Script

Validates ODL JSON files against the schema.
"""

import json
import sys
from pathlib import Path

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False
    print("Warning: jsonschema not installed. Only basic JSON validation will be performed.")


def validate_json_structure(odl_file: Path, schema_file: Path) -> bool:
    """Validate ODL file structure."""
    try:
        # Load schema
        with open(schema_file, 'r', encoding='utf-8') as f:
            schema = json.load(f)
        
        # Load ODL file
        with open(odl_file, 'r', encoding='utf-8') as f:
            odl = json.load(f)
        
        # Basic validation
        print(f"Validating {odl_file.name}...")
        
        # Check required fields
        if 'version' not in odl:
            print("ERROR: Missing 'version' field")
            return False
        
        if 'objects' not in odl:
            print("ERROR: Missing 'objects' field")
            return False
        
        if not odl['objects']:
            print("ERROR: 'objects' array is empty")
            return False
        
        # Check objects have required fields
        for obj in odl['objects']:
            if 'name' not in obj:
                print(f"ERROR: Object missing 'name' field: {obj}")
                return False
        
        # Check relationships
        if 'relationships' in odl:
            for rel in odl['relationships']:
                required = ['name', 'from', 'to', 'joinKeys']
                for field in required:
                    if field not in rel:
                        print(f"ERROR: Relationship missing '{field}' field: {rel}")
                        return False
        
        # Check metrics
        if 'metrics' in odl:
            for metric in odl['metrics']:
                required = ['name', 'expression', 'grain']
                for field in required:
                    if field not in metric:
                        print(f"ERROR: Metric missing '{field}' field: {metric}")
                        return False
        
        # Check dimensions
        if 'dimensions' in odl:
            for dim in odl['dimensions']:
                required = ['name', 'sourceProperty']
                for field in required:
                    if field not in dim:
                        print(f"ERROR: Dimension missing '{field}' field: {dim}")
                        return False
        
        # Check Snowflake mapping
        if 'snowflake' in odl:
            snowflake = odl['snowflake']
            if 'database' not in snowflake:
                print("ERROR: Snowflake mapping missing 'database' field")
                return False
            if 'schema' not in snowflake:
                print("ERROR: Snowflake mapping missing 'schema' field")
                return False
        
        print("[PASS] Basic structure validation passed")
        
        # JSON Schema validation (if available)
        if HAS_JSONSCHEMA:
            try:
                jsonschema.validate(instance=odl, schema=schema)
                print("[PASS] JSON Schema validation passed")
            except jsonschema.ValidationError as e:
                print(f"ERROR: JSON Schema validation failed: {e.message}")
                print(f"  Path: {'.'.join(str(p) for p in e.path)}")
                return False
        else:
            print("[SKIP] JSON Schema validation skipped (jsonschema not installed)")
        
        # Print summary
        print(f"\nSummary:")
        print(f"  Objects: {len(odl.get('objects', []))}")
        print(f"  Relationships: {len(odl.get('relationships', []))}")
        print(f"  Metrics: {len(odl.get('metrics', []))}")
        print(f"  Dimensions: {len(odl.get('dimensions', []))}")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON: {e}")
        return False
    except FileNotFoundError as e:
        print(f"ERROR: File not found: {e}")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def main():
    """Main validation function."""
    if len(sys.argv) < 2:
        print("Usage: python validate_odl.py <odl_file.json> [schema_file.json]")
        sys.exit(1)
    
    odl_file = Path(sys.argv[1])
    schema_file = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).parent / "schema" / "odl.schema.json"
    
    if not odl_file.exists():
        print(f"ERROR: ODL file not found: {odl_file}")
        sys.exit(1)
    
    if not schema_file.exists():
        print(f"ERROR: Schema file not found: {schema_file}")
        sys.exit(1)
    
    success = validate_json_structure(odl_file, schema_file)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
