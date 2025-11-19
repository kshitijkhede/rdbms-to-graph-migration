# API Reference

## Command Line Interface

### migrate

Execute complete database migration.

```bash
python -m src.cli migrate --config <config_file> [OPTIONS]
```

**Options**:
- `--config, -c`: Path to configuration file (required)
- `--dry-run`: Analyze only, do not migrate data
- `--tables, -t`: Comma-separated list of tables to migrate
- `--clear-target`: Clear target database before migration

**Examples**:
```bash
# Full migration
python -m src.cli migrate --config config/migration_config.yml

# Dry run
python -m src.cli migrate --config config/migration_config.yml --dry-run

# Migrate specific tables
python -m src.cli migrate --config config/migration_config.yml --tables users,posts

# Clear and migrate
python -m src.cli migrate --config config/migration_config.yml --clear-target
```

### analyze

Analyze source database schema.

```bash
python -m src.cli analyze --config <config_file> [OPTIONS]
```

**Options**:
- `--config, -c`: Path to configuration file (required)
- `--output, -o`: Output file for analysis (JSON format)

**Examples**:
```bash
# Analyze and display
python -m src.cli analyze --config config/migration_config.yml

# Save analysis to file
python -m src.cli analyze --config config/migration_config.yml --output schema.json
```

### validate

Validate migrated data.

```bash
python -m src.cli validate --config <config_file> [OPTIONS]
```

**Options**:
- `--config, -c`: Path to configuration file (required)
- `--check-counts`: Compare row counts between source and target

**Examples**:
```bash
# Basic validation
python -m src.cli validate --config config/migration_config.yml

# Validate with count comparison
python -m src.cli validate --config config/migration_config.yml --check-counts
```

### test-connection

Test database connections.

```bash
python -m src.cli test-connection --config <config_file> --type <source|target>
```

**Options**:
- `--config, -c`: Path to configuration file (required)
- `--type, -t`: Connection type to test (source or target)

**Examples**:
```bash
# Test source connection
python -m src.cli test-connection --config config/migration_config.yml --type source

# Test target connection
python -m src.cli test-connection --config config/migration_config.yml --type target
```

## Python API

### Connectors

#### MySQLConnector

```python
from src.connectors import MySQLConnector

connector = MySQLConnector(
    host="localhost",
    port=3306,
    database="mydb",
    username="user",
    password="pass"
)

with connector:
    tables = connector.get_tables()
    for table in tables:
        columns = connector.get_table_columns(table)
```

**Methods**:
- `connect()`: Establish connection
- `disconnect()`: Close connection
- `get_tables(schema=None)`: Get list of tables
- `get_table_columns(table_name, schema=None)`: Get column information
- `get_primary_key(table_name, schema=None)`: Get primary key
- `get_foreign_keys(table_name, schema=None)`: Get foreign keys
- `get_indexes(table_name, schema=None)`: Get indexes
- `get_row_count(table_name, schema=None)`: Get row count
- `fetch_data(table_name, batch_size, offset, schema=None)`: Fetch data

#### PostgreSQLConnector

Same interface as MySQLConnector with PostgreSQL-specific implementation.

#### SQLServerConnector

Same interface as MySQLConnector with SQL Server-specific implementation.

### Analyzers

#### SchemaAnalyzer

```python
from src.analyzers import SchemaAnalyzer

analyzer = SchemaAnalyzer(connector)
db_schema = analyzer.analyze()

# Get summary
summary = analyzer.get_schema_summary(db_schema)
print(f"Tables: {summary['total_tables']}")
print(f"Rows: {summary['total_rows']}")
```

**Methods**:
- `analyze(schema=None)`: Analyze complete schema
- `get_schema_summary(db_schema)`: Get schema statistics

### Transformers

#### GraphTransformer

```python
from src.transformers import GraphTransformer

config = {
    'foreign_keys_as_relationships': True,
    'junction_tables_as_relationships': True
}

transformer = GraphTransformer(db_schema, config)
graph_model = transformer.transform()

# Transform row data
properties = transformer.transform_row_to_node('users', row_data)
```

**Methods**:
- `transform()`: Transform schema to graph model
- `transform_row_to_node(table_name, row_data)`: Transform row to node properties

### Loaders

#### Neo4jLoader

```python
from src.loaders import Neo4jLoader

loader = Neo4jLoader(
    uri="bolt://localhost:7687",
    username="neo4j",
    password="password",
    database="neo4j"
)

with loader:
    # Create schema
    loader.create_constraints_and_indexes(graph_model)
    
    # Load nodes
    nodes = [
        {'id': 1, 'name': 'Alice'},
        {'id': 2, 'name': 'Bob'}
    ]
    loader.load_nodes_batch('User', nodes)
    
    # Load relationships
    relationships = [
        {'from_id': 1, 'to_id': 2, 'properties': {}}
    ]
    loader.load_relationships_batch(
        'FOLLOWS', 'User', 'User', relationships
    )
```

**Methods**:
- `connect()`: Connect to Neo4j
- `disconnect()`: Close connection
- `create_constraints_and_indexes(graph_model)`: Create schema
- `load_nodes_batch(label, nodes, id_property)`: Load nodes
- `load_relationships_batch(rel_type, from_label, to_label, relationships)`: Load relationships
- `get_node_count(label=None)`: Count nodes
- `get_relationship_count(rel_type=None)`: Count relationships
- `execute_cypher(query, parameters)`: Execute Cypher query

### Validators

#### DataValidator

```python
from src.validators import DataValidator

validator = DataValidator(
    source_connector,
    neo4j_loader,
    db_schema,
    graph_model
)

# Pre-migration validation
pre_results = validator.validate_pre_migration()
if not pre_results['valid']:
    print("Validation failed!")

# Post-migration validation
post_results = validator.validate_post_migration()
```

**Methods**:
- `validate_pre_migration()`: Validate source database
- `validate_post_migration()`: Validate migrated data
- `validate_relationships()`: Validate relationship integrity
- `check_referential_integrity()`: Check referential integrity

### Data Models

#### DatabaseSchema

```python
from src.models import DatabaseSchema, Table

schema = DatabaseSchema(
    database_name="mydb",
    database_type="mysql"
)

table = Table(name="users")
schema.add_table(table)

# Get tables
all_tables = schema.tables
entity_tables = schema.get_entity_tables()
junction_tables = schema.get_junction_tables()
```

#### GraphModel

```python
from src.models import GraphModel, NodeLabel

graph_model = GraphModel(name="my_graph")

# Add node label
node_label = NodeLabel(name="User", source_table="users")
graph_model.add_node_label(node_label)

# Get Cypher schema
cypher = graph_model.get_cypher_schema()
```

### Utilities

#### ConfigLoader

```python
from src.utils import ConfigLoader

config_loader = ConfigLoader("config/migration_config.yml")
config = config_loader.load()

source_config = config_loader.get_source_config()
target_config = config_loader.get_target_config()
migration_config = config_loader.get_migration_config()
```

#### Logging

```python
from src.utils import setup_logger, get_logger

# Setup logger
logger = setup_logger(
    name="my_migration",
    level="INFO",
    log_file="logs/my_migration.log"
)

logger.info("Starting migration")
logger.error("An error occurred")

# Get existing logger
logger = get_logger("my_migration")
```

#### Helper Functions

```python
from src.utils import helpers

# Sanitize names
label = helpers.sanitize_label("user_accounts")  # Returns "UserAccounts"
prop = helpers.sanitize_property_name("user_id")  # Returns "userId"

# Format utilities
size = helpers.format_bytes(1024000)  # Returns "1000.00 KB"
duration = helpers.format_duration(3665)  # Returns "1h 1m 5s"

# Batch processing
for batch in helpers.batch_iterator(data, batch_size=100):
    process_batch(batch)
```

## Configuration Schema

### Migration Configuration

```yaml
source:
  type: string  # mysql | postgresql | sqlserver
  host: string
  port: integer
  database: string
  username: string
  password: string
  schema: string  # optional

target:
  neo4j:
    uri: string  # bolt://host:port
    username: string
    password: string
    database: string

migration:
  batch_size: integer  # default: 1000
  max_workers: integer  # default: 4
  validate_before: boolean  # default: true
  validate_after: boolean  # default: true
  create_indexes: boolean  # default: true

mapping:
  tables_as_nodes: array<string>
  foreign_keys_as_relationships: boolean
  junction_tables_as_relationships: boolean

logging:
  level: string  # DEBUG | INFO | WARNING | ERROR
  file: string
```

## Error Handling

All API methods raise exceptions on errors:

- `ValueError`: Invalid input or configuration
- `ConnectionError`: Database connection issues
- `RuntimeError`: Migration execution errors
- `Neo4jError`: Neo4j-specific errors

Example:
```python
try:
    connector.connect()
except ConnectionError as e:
    logger.error(f"Connection failed: {e}")
```
