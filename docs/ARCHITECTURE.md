# Architecture Documentation

## Overview

This document provides an in-depth explanation of the RDBMS-to-Graph Migration Engine architecture, design decisions, and implementation details.

## System Architecture

### High-Level Design

The migration engine follows a **4-phase pipeline architecture**, inspired by the AMANDA system referenced in the research paper. Each phase is independent, allowing for manual intervention and enrichment.

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Phase 1    │────▶│   Phase 2    │────▶│   Phase 3    │────▶│   Phase 4    │
│   Extract    │     │   Enrich     │     │     Load     │     │   Validate   │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
     MySQL              mapping.json           Neo4j             Verification
```

### Component Breakdown

#### Phase 1: Metadata Extractor (`extractor.py`)

**Purpose**: Reverse-engineer the relational schema into a structured representation.

**Process**:
1. Connect to MySQL database
2. Query `information_schema` for metadata
3. Extract tables, columns, data types
4. Identify primary keys and foreign keys
5. Detect patterns (junction tables, inheritance)
6. Generate default mapping configuration
7. Save to `mapping.json`

**Key Algorithms**:

**Junction Table Detection**:
```python
def is_junction_table(table):
    return (
        len(primary_keys) >= 2 and
        all(pk in foreign_keys for pk in primary_keys)
    )
```

**Inheritance Pattern Detection**:
```python
def is_inheritance(table):
    return (
        len(primary_keys) == 1 and
        primary_key in foreign_keys
    )
```

#### Phase 2: Semantic Mapping (Manual)

**Purpose**: Allow domain experts to enrich the auto-generated mapping with business logic.

**Configuration Structure**:
```json
{
  "database": "db_name",
  "tables": {
    "table_name": {
      "columns": [...],
      "primary_keys": [...],
      "foreign_keys": [...],
      "is_junction_table": bool,
      "inheritance": {...},
      "mapping": {
        "type": "entity|junction|inheritance",
        "node_label": "NodeLabel",
        "properties": [
          {
            "source_column": "col_name",
            "target_property": "propName",
            "type": "data_type"
          }
        ],
        "relationships": [
          {
            "type": "foreign_key|many_to_many",
            "source_column": "fk_column",
            "target_node": "TargetLabel",
            "relationship_type": "REL_TYPE"
          }
        ]
      }
    }
  }
}
```

**Enrichment Options**:
- Rename node labels for clarity
- Customize relationship types
- Mark tables for special handling
- Define property transformations
- Specify inheritance hierarchies

#### Phase 3: ETL Pipeline (`loader.py`)

**Purpose**: Execute the physical data migration from MySQL to Neo4j.

**Process Flow**:

1. **Initialization**
   - Load mapping configuration
   - Connect to both databases
   - Create Neo4j constraints

2. **First Pass: Entity Nodes**
   - Iterate through non-junction tables
   - Extract data using Pandas
   - Transform according to mapping
   - Load into Neo4j using MERGE

3. **Second Pass: Relationships**
   - Process foreign keys
   - Create directed edges
   - Preserve referential integrity

4. **Third Pass: Junction Tables**
   - Dissolve junction tables
   - Create many-to-many relationships
   - Transfer additional properties

**Batch Processing**:
```python
for batch_start in range(0, len(df), batch_size):
    batch = df.iloc[batch_start:batch_start + batch_size]
    process_batch(batch)
```

**Transaction Safety**:
```python
with neo4j_driver.session() as session:
    with session.begin_transaction() as tx:
        for record in batch:
            tx.run(query, parameters)
        tx.commit()
```

#### Phase 4: Validation Suite (`validator.py`)

**Purpose**: Prove migration correctness through parallel verification.

**Validation Tests**:

1. **Row Count Validation**
   - Count rows in MySQL table
   - Count nodes in Neo4j with same label
   - Compare for equality

2. **Relationship Count Validation**
   - Count non-NULL foreign keys in MySQL
   - Count relationships in Neo4j
   - Compare for equality

3. **Business Query Validation**
   - Execute equivalent queries on both databases
   - Compare results
   - Verify semantic consistency

**Example Validation**:
```python
# MySQL
SELECT COUNT(DISTINCT customer_id) FROM Orders;

# Neo4j
MATCH (c:Customer)-[:PLACED]->(o:Order)
RETURN COUNT(DISTINCT c);
```

## Design Patterns

### 1. Strategy Pattern

Different migration strategies for different table types:
- Entity table → Nodes
- Junction table → Relationships
- Inheritance table → Multi-label nodes

### 2. Template Method Pattern

Common migration flow with customizable steps:
```python
def migrate():
    connect()
    extract()
    transform()  # Customizable
    load()
    validate()
    disconnect()
```

### 3. Factory Pattern

Creating appropriate handlers based on table type:
```python
def get_handler(table_info):
    if table_info['is_junction']:
        return JunctionTableHandler()
    elif table_info['inheritance']:
        return InheritanceHandler()
    else:
        return EntityTableHandler()
```

## Data Flow

### Extract Phase
```
MySQL ──┬─► information_schema.tables
        ├─► information_schema.columns
        ├─► information_schema.key_column_usage
        └─► information_schema.referential_constraints
           │
           ▼
        mapping.json (draft)
```

### Load Phase
```
MySQL Table ──► Pandas DataFrame ──► Transformation ──► Neo4j Cypher ──► Graph
     │              │                      │                  │
     │              │                      │                  │
  SELECT *      Batch Read         Property Mapping      MERGE/CREATE
                                   Type Conversion       Relationship
```

## Performance Considerations

### Memory Management

- **Streaming**: Process data in batches to avoid loading entire tables into memory
- **Pandas Chunking**: Use `chunksize` parameter in `read_sql()`
- **Connection Pooling**: Reuse database connections

### Query Optimization

- **Indexes**: Create constraints/indexes in Neo4j before bulk loading
- **MERGE vs CREATE**: Use MERGE for idempotency, CREATE for performance
- **Batch Size Tuning**: Balance memory usage vs transaction overhead

### Scalability

Current implementation handles databases with:
- Up to 100 tables
- Up to 1M rows per table
- Up to 10M total relationships

For larger datasets, consider:
- Parallel processing
- Distributed Neo4j clusters
- Incremental migration

## Error Handling

### Connection Failures

```python
try:
    connection = mysql.connector.connect(**config)
except mysql.connector.Error as e:
    log_error(e)
    retry_with_backoff()
```

### Data Validation

```python
def validate_data(value, expected_type):
    if not isinstance(value, expected_type):
        log_warning(f"Type mismatch: {value}")
        return convert_type(value, expected_type)
    return value
```

### Transaction Rollback

```python
try:
    with session.begin_transaction() as tx:
        load_data(tx)
        tx.commit()
except Exception as e:
    tx.rollback()
    log_error(e)
```

## Security Considerations

### Credential Management

- Store credentials in `config.py` (not in version control)
- Use environment variables in production
- Implement credential encryption

### SQL Injection Prevention

- Use parameterized queries
- Validate user input
- Escape special characters

### Access Control

- Follow principle of least privilege
- Read-only access for extraction
- Separate credentials for different phases

## Testing Strategy

### Unit Tests

Test individual components:
- Schema detection algorithms
- Data transformation functions
- Query generation logic

### Integration Tests

Test component interactions:
- MySQL → Mapping generation
- Mapping → Neo4j loading
- End-to-end pipeline

### Validation Tests

Verify migration correctness:
- Data integrity checks
- Relationship preservation
- Query equivalence

## Future Enhancements

### Short-term

1. **Logging Framework**: Replace print statements with proper logging
2. **Configuration Validation**: JSON schema validation for mapping.json
3. **Progress Indicators**: Real-time progress bars for long operations
4. **Dry Run Mode**: Preview changes without executing

### Medium-term

1. **GUI Configuration**: Web interface for mapping enrichment
2. **Multiple Source Support**: PostgreSQL, Oracle, SQL Server
3. **Multiple Target Support**: MongoDB, ArangoDB, Amazon Neptune
4. **Incremental Migration**: Detect and migrate only changes

### Long-term

1. **Bi-directional Sync**: Keep MySQL and Neo4j in sync
2. **Query Translation**: Automatically translate SQL to Cypher
3. **Performance Profiling**: Built-in profiling and optimization
4. **Cloud Deployment**: Docker containers, Kubernetes orchestration

## Appendix: Cypher Pattern Reference

### Creating Nodes
```cypher
MERGE (n:Label {id: $id})
SET n.property = $value
```

### Creating Relationships
```cypher
MATCH (a:LabelA {id: $id_a})
MATCH (b:LabelB {id: $id_b})
MERGE (a)-[r:REL_TYPE]->(b)
SET r.property = $value
```

### Creating Constraints
```cypher
CREATE CONSTRAINT constraint_name IF NOT EXISTS
FOR (n:Label) REQUIRE n.property IS UNIQUE
```

### Clearing Database
```cypher
MATCH (n) DETACH DELETE n
```
