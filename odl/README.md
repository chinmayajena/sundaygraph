# Ontology Definition Language (ODL)

ODL is a JSON-based language for defining semantic models that can be compiled to Snowflake semantic model YAML format.

## Files

- **`schema/odl.schema.json`** - JSON Schema definition for ODL files
- **`examples/snowflake_retail.odl.json`** - Example ODL file for retail e-commerce domain
- **`validate_odl.py`** - Validation script for ODL files

## ODL Structure

### Required Fields

- `version` - ODL schema version (e.g., "1.0.0")
- `objects` - Array of objects (entities) in the ontology

### Optional Fields

- `name` - Name of the ontology/semantic model
- `description` - Description of the ontology
- `relationships` - Array of relationships between objects
- `metrics` - Array of metrics (measures)
- `dimensions` - Array of dimensions
- `snowflake` - Snowflake-specific mapping configuration

## Object Structure

Each object must have:
- `name` - Object name (PascalCase, e.g., "Customer")
- `identifiers` - Array of primary key property names
- `properties` - Array of property definitions
- `snowflake` (optional) - Object-specific Snowflake mapping

### Property Structure

Each property must have:
- `name` - Property name (camelCase, e.g., "customer_id")
- `type` - Data type (string, number, integer, decimal, boolean, date, timestamp, time, array, object)
- `description` (optional) - Property description
- `nullable` (optional) - Whether property can be null (default: true)
- `required` (optional) - Whether property is required (default: false)

## Relationship Structure

Each relationship must have:
- `name` - Relationship name (camelCase, e.g., "placed_by")
- `from` - Source object name
- `to` - Target object name
- `joinKeys` - Array of join key pairs `[fromProperty, toProperty]`
- `cardinality` (optional) - Relationship cardinality (one_to_one, one_to_many, many_to_one, many_to_many)
- `description` (optional) - Relationship description

## Metric Structure

Each metric must have:
- `name` - Metric name (PascalCase, e.g., "TotalRevenue")
- `expression` - SQL expression for calculating the metric
- `grain` - Array of objects that define the grain
- `type` (optional) - Metric type (sum, count, average, min, max, distinct_count, custom)
- `format` (optional) - Format string for display (e.g., "$#,##0.00")
- `description` (optional) - Metric description

## Dimension Structure

Each dimension must have:
- `name` - Dimension name (PascalCase, e.g., "CustomerName")
- `sourceProperty` - Property path in format "Object.property" (e.g., "Customer.name")
- `type` (optional) - Dimension type (categorical, temporal, geographic, numeric)
- `description` (optional) - Dimension description

## Snowflake Mapping

The `snowflake` block defines Snowflake-specific configuration:

```json
{
  "snowflake": {
    "database": "RETAIL_DB",
    "schema": "PUBLIC",
    "warehouse": "COMPUTE_WH",  // Optional
    "tableMappings": {
      "Customer": "customers",
      "Order": "orders"
    }
  }
}
```

### Per-Object Snowflake Mapping

Objects can override global Snowflake settings:

```json
{
  "name": "Customer",
  "snowflake": {
    "table": "customers",
    "schema": "CUSTOM_SCHEMA",  // Optional override
    "database": "CUSTOM_DB"     // Optional override
  }
}
```

## Example

See `examples/snowflake_retail.odl.json` for a complete example with:
- 4 objects: Customer, Order, Product, OrderItem
- 3 relationships: placed_by (Order->Customer), contains, includes
- 5 metrics: TotalRevenue, OrderCount, AverageOrderValue, TotalItemsSold, UniqueCustomers
- 4 dimensions: CustomerName, OrderDate, ProductCategory, OrderStatus

## Validation

Validate an ODL file:

```bash
python odl/validate_odl.py odl/examples/snowflake_retail.odl.json
```

For full JSON Schema validation, install jsonschema:

```bash
pip install jsonschema
```

## Compilation to Snowflake

ODL files are designed to compile cleanly to Snowflake semantic model YAML format. The compiler will:

1. Map objects to Snowflake entities
2. Convert relationships to Snowflake joins
3. Transform metrics to Snowflake measures
4. Map dimensions to Snowflake dimensions
5. Apply Snowflake table mappings

See the main README.md for compilation instructions.
