"""Unit tests for ODL core module."""

import pytest
import json
from pathlib import Path

from src.odl.core import ODLProcessor
from src.odl.validator import ODLValidationError
from src.odl.loader import ODLLoader
from src.odl.validator import ODLValidator
from src.odl.normalizer import ODLNormalizer


class TestODLLoader:
    """Tests for ODL loader."""
    
    def test_load_valid_file(self, tmp_path):
        """Test loading a valid ODL file."""
        odl_file = tmp_path / "test.odl.json"
        odl_file.write_text(json.dumps({
            "version": "1.0.0",
            "objects": [{"name": "Customer", "identifiers": ["id"]}]
        }))
        
        loader = ODLLoader()
        data = loader.load(odl_file)
        
        assert data["version"] == "1.0.0"
        assert len(data["objects"]) == 1
    
    def test_load_nonexistent_file(self):
        """Test loading a nonexistent file raises error."""
        loader = ODLLoader()
        
        with pytest.raises(FileNotFoundError):
            loader.load("nonexistent.odl.json")
    
    def test_load_from_string(self):
        """Test loading from JSON string."""
        loader = ODLLoader()
        data = loader.load_from_string('{"version": "1.0.0", "objects": []}')
        
        assert data["version"] == "1.0.0"


class TestODLValidator:
    """Tests for ODL validator."""
    
    def test_missing_object_reference(self):
        """Test validation error for missing object reference in relationship."""
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
        
        assert not is_valid
        assert len(errors) > 0
        assert any("Order" in error and "unknown object" in error.lower() for error in errors)
        assert any("Available objects" in error for error in errors)
    
    def test_duplicate_metric_name(self):
        """Test validation error for duplicate metric names."""
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
        
        assert not is_valid
        assert len(errors) > 0
        assert any("Duplicate metric name" in error and "TotalRevenue" in error for error in errors)
        assert any("First occurrence" in error for error in errors)
    
    def test_invalid_relationship_cardinality(self):
        """Test validation error for invalid relationship cardinality."""
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
        
        assert not is_valid
        assert len(errors) > 0
        assert any("invalid cardinality" in error.lower() for error in errors)
        assert any("Valid values" in error for error in errors)
    
    def test_relationship_join_key_missing_from_mapped_tables(self):
        """Test validation error when relationship join key references missing property."""
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
        
        assert not is_valid
        assert len(errors) > 0
        # Should find error about missing property
        assert any("customer_id" in error.lower() and "unknown property" in error.lower() for error in errors)
        assert any("Available properties" in error for error in errors)
    
    def test_valid_odl_passes(self):
        """Test that valid ODL passes validation."""
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
        
        assert is_valid
        assert len(errors) == 0


class TestODLNormalizer:
    """Tests for ODL normalizer."""
    
    def test_normalize_sorts_lists(self):
        """Test that normalization sorts lists for stability."""
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
        assert [o.name for o in ir.objects] == ["Alpha", "Beta", "Zebra"]
        
        # Metrics should be sorted
        assert [m.name for m in ir.metrics] == ["MetricA", "MetricB"]
    
    def test_normalize_canonical_names(self):
        """Test that normalization preserves canonical names."""
        normalizer = ODLNormalizer()
        
        odl_data = {
            "version": "1.0.0",
            "objects": [
                {
                    "name": "Customer",
                    "identifiers": ["customer_id"],
                    "properties": [
                        {"name": "customer_id", "type": "string"},
                        {"name": "name", "type": "string"}
                    ]
                }
            ]
        }
        
        ir = normalizer.normalize(odl_data)
        
        assert len(ir.objects) == 1
        assert ir.objects[0].name == "Customer"
        assert ir.objects[0].identifiers == ["customer_id"]  # Sorted


class TestODLProcessor:
    """Integration tests for ODL processor."""
    
    def test_process_valid_file(self, tmp_path):
        """Test processing a valid ODL file."""
        odl_file = tmp_path / "test.odl.json"
        odl_file.write_text(json.dumps({
            "version": "1.0.0",
            "objects": [
                {
                    "name": "Customer",
                    "identifiers": ["id"],
                    "properties": [{"name": "id", "type": "string"}]
                }
            ],
            "snowflake": {
                "database": "TEST_DB",
                "schema": "PUBLIC"
            }
        }))
        
        processor = ODLProcessor()
        ir, is_valid, errors = processor.process(odl_file)
        
        assert is_valid
        assert len(errors) == 0
        assert ir.version == "1.0.0"
        assert len(ir.objects) == 1
        assert ir.objects[0].name == "Customer"
    
    def test_process_invalid_file(self, tmp_path):
        """Test processing an invalid ODL file."""
        odl_file = tmp_path / "test.odl.json"
        odl_file.write_text(json.dumps({
            "version": "1.0.0",
            "objects": [],
            "relationships": [
                {
                    "name": "test",
                    "from": "MissingObject",
                    "to": "AlsoMissing",
                    "joinKeys": [["x", "y"]]
                }
            ]
        }))
        
        processor = ODLProcessor()
        ir, is_valid, errors = processor.process(odl_file)
        
        assert not is_valid
        assert len(errors) > 0
        # Should still normalize (for debugging)
        assert ir is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
