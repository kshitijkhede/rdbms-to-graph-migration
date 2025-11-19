# Architecture

## System Overview

The RDBMS to Property Graph Migration System is designed with a modular architecture that separates concerns and allows for easy extension and maintenance.

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────┐
│                     CLI Interface                        │
│                      (src/cli.py)                        │
└────────────────────┬─────────────────────────────────────┘
                     │
         ┌───────────┼───────────┐
         │           │           │
         ▼           ▼           ▼
┌────────────┐ ┌──────────┐ ┌──────────┐
│   Analyze  │ │  Migrate │ │ Validate │
│   Command  │ │  Command │ │  Command │
└─────┬──────┘ └────┬─────┘ └────┬─────┘
      │             │             │
      └─────────────┼─────────────┘
                    │
    ┌───────────────┼───────────────┐
    │               │               │
    ▼               ▼               ▼
┌─────────┐   ┌──────────┐   ┌──────────┐
│ Schema  │   │  Data    │   │   Data   │
│Analyzer │   │Extractor │   │Validator │
└────┬────┘   └────┬─────┘   └────┬─────┘
     │             │              │
     │             │              │
     ▼             ▼              ▼
┌─────────────────────────────────────┐
│        Data Models Layer            │
│  - DatabaseSchema                   │
│  - GraphModel                       │
│  - Table, Column, ForeignKey        │
│  - NodeLabel, RelationshipType      │
└─────────────────────────────────────┘
     │                           │
     ▼                           ▼
┌──────────┐              ┌──────────┐
│ Graph    │              │  Neo4j   │
│Transform │              │  Loader  │
└─────┬────┘              └────┬─────┘
      │                        │
      └────────────┬───────────┘
                   │
    ┌──────────────┼──────────────┐
    │              │              │
    ▼              ▼              ▼
┌─────────┐  ┌──────────┐  ┌──────────┐
│  MySQL  │  │PostgreSQL│  │   Neo4j  │
│Connector│  │Connector │  │ Database │
└─────────┘  └──────────┘  └──────────┘
```

## Core Components

### 1. Connectors (`src/connectors/`)

**Purpose**: Interface with different database systems

**Components**:
- `RDBMSConnector`: Abstract base class for RDBMS connectors
- `MySQLConnector`: MySQL-specific implementation
- `PostgreSQLConnector`: PostgreSQL-specific implementation
- `SQLServerConnector`: SQL Server-specific implementation

**Responsibilities**:
- Establish database connections
- Execute queries
- Fetch schema metadata
- Extract data in batches

### 2. Analyzers (`src/analyzers/`)

**Purpose**: Analyze and understand source database structure

**Components**:
- `SchemaAnalyzer`: Analyzes database schema structure

**Responsibilities**:
- Introspect tables, columns, constraints
- Identify relationships and foreign keys
- Detect junction tables
- Calculate statistics

### 3. Transformers (`src/transformers/`)

**Purpose**: Transform relational model to graph model

**Components**:
- `GraphTransformer`: Converts relational schemas to graph models

**Responsibilities**:
- Map tables to node labels
- Convert foreign keys to relationships
- Transform junction tables to relationships
- Handle data type conversions

### 4. Extractors (`src/extractors/`)

**Purpose**: Extract data from source database

**Components**:
- `DataExtractor`: Extracts data in batches

**Responsibilities**:
- Batch data extraction
- Progress tracking
- Memory-efficient data streaming

### 5. Loaders (`src/loaders/`)

**Purpose**: Load data into Neo4j

**Components**:
- `Neo4jLoader`: Loads nodes and relationships into Neo4j

**Responsibilities**:
- Create constraints and indexes
- Load nodes in batches
- Create relationships
- Manage transactions

### 6. Validators (`src/validators/`)

**Purpose**: Validate migration integrity

**Components**:
- `DataValidator`: Validates pre and post-migration

**Responsibilities**:
- Pre-migration validation
- Post-migration validation
- Row count comparison
- Referential integrity checks

### 7. Models (`src/models/`)

**Purpose**: Data structure definitions

**Components**:
- `schema_model.py`: Relational schema models
- `graph_model.py`: Graph schema models

**Classes**:
- `Table`, `Column`, `ForeignKey`, `PrimaryKey`
- `NodeLabel`, `RelationshipType`, `Property`
- `DatabaseSchema`, `GraphModel`

### 8. Utilities (`src/utils/`)

**Purpose**: Common utilities and helpers

**Components**:
- `config.py`: Configuration management
- `logger.py`: Logging setup
- `helpers.py`: Utility functions

## Data Flow

### Migration Process Flow

```
1. Load Configuration
   └─> Parse YAML config file
   
2. Connect to Databases
   ├─> Source RDBMS
   └─> Target Neo4j
   
3. Analyze Schema
   ├─> Extract table definitions
   ├─> Identify relationships
   └─> Detect junction tables
   
4. Transform Schema
   ├─> Map tables to nodes
   ├─> Map foreign keys to relationships
   └─> Map junction tables to relationships
   
5. Create Graph Schema
   ├─> Create constraints
   └─> Create indexes
   
6. Migrate Data
   ├─> Extract data in batches
   ├─> Transform to graph format
   └─> Load into Neo4j
   
7. Validate
   ├─> Compare row counts
   ├─> Check relationships
   └─> Verify integrity
```

## Design Patterns

### 1. Factory Pattern
- Database connector creation based on configuration
- Different connectors for MySQL, PostgreSQL, SQL Server

### 2. Strategy Pattern
- Pluggable transformation strategies
- Customizable mapping rules

### 3. Iterator Pattern
- Batch processing of large datasets
- Memory-efficient data extraction

### 4. Template Method Pattern
- Base connector with abstract methods
- Subclasses implement database-specific logic

## Extension Points

### Adding New Database Support

1. Create new connector class inheriting from `RDBMSConnector`
2. Implement abstract methods for metadata extraction
3. Register in connector factory

### Custom Transformations

1. Extend `GraphTransformer` class
2. Override transformation methods
3. Configure via mapping configuration

### Custom Validation

1. Extend `DataValidator` class
2. Add custom validation methods
3. Integrate with CLI commands

## Performance Considerations

### Batch Processing
- Configurable batch sizes
- Memory-efficient streaming
- Parallel processing support

### Indexing Strategy
- Create indexes before data load
- Unique constraints on primary keys
- Deferred constraint checking

### Connection Pooling
- Reuse database connections
- Connection timeout handling
- Automatic reconnection

## Security Considerations

### Credentials Management
- Support for environment variables
- Configuration file encryption
- No hardcoded credentials

### Data Validation
- Input sanitization
- SQL injection prevention
- Type checking

### Access Control
- Database user permissions
- Read-only source access
- Write access to target only
