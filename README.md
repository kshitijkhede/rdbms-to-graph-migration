# RDBMS to Property Graph Migration System

A comprehensive, production-ready system for migrating relational database schemas and data to property graph databases (Neo4j). This project implements complete data migration from RDBMS (MySQL, PostgreSQL, SQL Server) to Neo4j property graph model.

## 🎯 Project Overview

This system provides an automated, scalable solution for transforming relational database structures into graph database models while preserving data integrity, relationships, and business logic.

### Key Features

- **Multi-Database Support**: MySQL, PostgreSQL, SQL Server
- **Automatic Schema Analysis**: Introspects RDBMS schemas to identify tables, relationships, constraints
- **Intelligent Graph Mapping**: Transforms relational models to property graph models
- **Batch Processing**: Efficient data migration with configurable batch sizes
- **Data Validation**: Pre and post-migration validation checks
- **Error Handling**: Comprehensive error handling and rollback capabilities
- **Progress Tracking**: Real-time migration progress monitoring
- **Configuration-Driven**: YAML-based configuration for flexibility
- **CLI Interface**: Easy-to-use command-line interface

## 🏗️ Architecture

```
┌─────────────────┐
│  Source RDBMS   │
│ (MySQL/PG/MSSQL)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Schema Analyzer │ ◄─── Introspects database structure
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Data Extractor  │ ◄─── Extracts data with batching
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Graph Transformer│ ◄─── Maps relational → graph model
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Neo4j Loader   │ ◄─── Loads into graph database
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Validator     │ ◄─── Verifies migration integrity
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Target Neo4j   │
│  Graph Database │
└─────────────────┘
```

## 📋 Prerequisites

- Python 3.8+
- Source database (MySQL 5.7+, PostgreSQL 10+, or SQL Server 2017+)
- Neo4j 4.0+ (Community or Enterprise)
- At least 4GB RAM (8GB+ recommended for large datasets)

## 🚀 Installation

### 1. Clone the Repository

```bash
cd /home/student/DBMS/final
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Linux/Mac
# or
venv\Scripts\activate  # On Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## ⚙️ Configuration

### 1. Create Configuration File

Copy the example configuration:

```bash
cp config/migration_config.example.yml config/migration_config.yml
```

### 2. Edit Configuration

```yaml
# config/migration_config.yml
source:
  type: mysql  # mysql, postgresql, or sqlserver
  host: localhost
  port: 3306
  database: my_database
  username: db_user
  password: db_password

target:
  neo4j:
    uri: bolt://localhost:7687
    username: neo4j
    password: password
    database: neo4j  # For Neo4j 4.0+

migration:
  batch_size: 1000
  max_workers: 4
  validate_before: true
  validate_after: true
  create_indexes: true
  
mapping:
  # Define custom node labels and relationship types
  tables_as_nodes:
    - users
    - products
  
  foreign_keys_as_relationships: true
  junction_tables_as_relationships: true
  
logging:
  level: INFO
  file: logs/migration.log
```

## 📖 Usage

### Basic Migration

```bash
# Run complete migration
python -m src.cli migrate --config config/migration_config.yml

# Dry run (analyze only, no data migration)
python -m src.cli migrate --config config/migration_config.yml --dry-run

# Migrate specific tables only
python -m src.cli migrate --config config/migration_config.yml --tables users,orders,products
```

### Schema Analysis Only

```bash
# Analyze source database schema
python -m src.cli analyze --config config/migration_config.yml

# Export schema analysis to JSON
python -m src.cli analyze --config config/migration_config.yml --output schema_analysis.json
```

### Validation

```bash
# Validate migrated data
python -m src.cli validate --config config/migration_config.yml

# Compare row counts
python -m src.cli validate --config config/migration_config.yml --check-counts
```

## 📊 Migration Process

### 1. Pre-Migration Analysis

```bash
python -m src.cli analyze --config config/migration_config.yml
```

This will:
- Analyze source database schema
- Identify tables, columns, relationships
- Detect primary keys, foreign keys, constraints
- Generate recommended graph model mapping
- Estimate migration time and resources

### 2. Execute Migration

```bash
python -m src.cli migrate --config config/migration_config.yml
```

The system will:
1. Connect to source and target databases
2. Analyze schema structure
3. Create graph model mapping
4. Extract data in batches
5. Transform to graph model
6. Load into Neo4j
7. Create indexes and constraints
8. Validate data integrity

### 3. Post-Migration Validation

```bash
python -m src.cli validate --config config/migration_config.yml
```

Validation includes:
- Row count comparison
- Relationship integrity
- Data type validation
- Constraint verification

## 🔄 Transformation Rules

### Tables → Nodes

**Primary tables** (with business entities) become **Node Labels**:

```sql
-- RDBMS: users table
CREATE TABLE users (
  id INT PRIMARY KEY,
  name VARCHAR(100),
  email VARCHAR(100)
);
```

```cypher
// Neo4j: User nodes
CREATE (:User {id: 1, name: 'John Doe', email: 'john@example.com'})
```

### Foreign Keys → Relationships

**Foreign key relationships** become **Relationships**:

```sql
-- RDBMS: orders table with foreign key
CREATE TABLE orders (
  id INT PRIMARY KEY,
  user_id INT,
  total DECIMAL(10,2),
  FOREIGN KEY (user_id) REFERENCES users(id)
);
```

```cypher
// Neo4j: User-PLACED->Order relationship
CREATE (u:User {id: 1})-[:PLACED]->(o:Order {id: 101, total: 99.99})
```

### Junction Tables → Relationships with Properties

**Many-to-many junction tables** become **Relationships with properties**:

```sql
-- RDBMS: user_products junction table
CREATE TABLE user_products (
  user_id INT,
  product_id INT,
  quantity INT,
  purchased_at TIMESTAMP,
  PRIMARY KEY (user_id, product_id)
);
```

```cypher
// Neo4j: PURCHASED relationship with properties
CREATE (u:User)-[:PURCHASED {quantity: 2, purchased_at: datetime()}]->(p:Product)
```

## 🎨 Example Migration

### Source Database (MySQL)

```sql
-- E-commerce database schema
CREATE TABLE customers (
  id INT PRIMARY KEY,
  name VARCHAR(100),
  email VARCHAR(100)
);

CREATE TABLE products (
  id INT PRIMARY KEY,
  name VARCHAR(100),
  price DECIMAL(10,2),
  category VARCHAR(50)
);

CREATE TABLE orders (
  id INT PRIMARY KEY,
  customer_id INT,
  order_date DATE,
  status VARCHAR(20),
  FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE TABLE order_items (
  order_id INT,
  product_id INT,
  quantity INT,
  unit_price DECIMAL(10,2),
  PRIMARY KEY (order_id, product_id),
  FOREIGN KEY (order_id) REFERENCES orders(id),
  FOREIGN KEY (product_id) REFERENCES products(id)
);
```

### Target Graph Model (Neo4j)

```cypher
// Nodes
(:Customer {id, name, email})
(:Product {id, name, price, category})
(:Order {id, order_date, status})

// Relationships
(:Customer)-[:PLACED]->(:Order)
(:Order)-[:CONTAINS {quantity, unit_price}]->(:Product)
```

### Migration Command

```bash
python -m src.cli migrate --config config/ecommerce_migration.yml
```

## 📈 Performance Optimization

### For Large Databases (1M+ rows)

```yaml
migration:
  batch_size: 5000  # Increase batch size
  max_workers: 8    # Increase parallelism
  use_apoc: true    # Use APOC procedures for bulk loading
  memory_limit: 8GB # Set memory limit
```

### Create Indexes Before Migration

```yaml
migration:
  create_indexes: true
  indexes:
    - label: User
      property: id
    - label: Product
      property: id
    - label: Order
      property: order_date
```

## 🧪 Testing

```bash
# Run unit tests
pytest tests/unit/

# Run integration tests
pytest tests/integration/

# Run all tests with coverage
pytest --cov=src tests/
```

## 📁 Project Structure

```
rdbms-to-graph-migration/
├── src/
│   ├── __init__.py
│   ├── cli.py                      # Command-line interface
│   ├── connectors/
│   │   ├── __init__.py
│   │   ├── rdbms_connector.py     # Base RDBMS connector
│   │   ├── mysql_connector.py     # MySQL specific
│   │   ├── postgres_connector.py  # PostgreSQL specific
│   │   └── sqlserver_connector.py # SQL Server specific
│   ├── analyzers/
│   │   ├── __init__.py
│   │   └── schema_analyzer.py     # Schema introspection
│   ├── extractors/
│   │   ├── __init__.py
│   │   └── data_extractor.py      # Data extraction
│   ├── transformers/
│   │   ├── __init__.py
│   │   └── graph_transformer.py   # Relational to graph mapping
│   ├── loaders/
│   │   ├── __init__.py
│   │   └── neo4j_loader.py        # Neo4j data loader
│   ├── validators/
│   │   ├── __init__.py
│   │   └── data_validator.py      # Migration validation
│   ├── models/
│   │   ├── __init__.py
│   │   ├── schema_model.py        # Schema representation
│   │   └── graph_model.py         # Graph model representation
│   └── utils/
│       ├── __init__.py
│       ├── config.py              # Configuration loader
│       ├── logger.py              # Logging setup
│       └── helpers.py             # Utility functions
├── config/
│   ├── migration_config.example.yml
│   └── logging.yml
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── examples/
│   ├── simple_migration.py
│   └── custom_transformation.py
├── docs/
│   ├── architecture.md
│   ├── api_reference.md
│   └── troubleshooting.md
├── logs/
├── requirements.txt
├── setup.py
├── .gitignore
└── README.md
```

## 🐛 Troubleshooting

### Connection Issues

```bash
# Test source database connection
python -m src.cli test-connection --config config/migration_config.yml --type source

# Test Neo4j connection
python -m src.cli test-connection --config config/migration_config.yml --type target
```

### Memory Issues

If encountering out-of-memory errors:

```yaml
migration:
  batch_size: 500  # Reduce batch size
  streaming: true  # Enable streaming mode
```

### Performance Issues

```yaml
migration:
  max_workers: 2  # Reduce parallelism
  use_transactions: true
  transaction_size: 1000
```

## 📚 Additional Resources

- [Neo4j Graph Data Modeling Guide](https://neo4j.com/developer/data-modeling/)
- [APOC Procedures Documentation](https://neo4j.com/labs/apoc/)
- [Graph Database Best Practices](https://neo4j.com/developer/guide-performance-tuning/)

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

## ✨ Features Roadmap

- [ ] Support for additional graph databases (Amazon Neptune, ArangoDB)
- [ ] Web-based UI for configuration and monitoring
- [ ] Real-time incremental migration
- [ ] Automatic schema optimization suggestions
- [ ] Support for complex data types (JSON, arrays)
- [ ] Migration rollback capabilities
- [ ] Data anonymization during migration
- [ ] Performance benchmarking tools

## 📞 Support

For issues and questions:
- Create an issue on GitHub
- Check the [documentation](docs/)
- Review [troubleshooting guide](docs/troubleshooting.md)

## 🏆 Acknowledgments

Developed as part of Database Management Systems course project - demonstrating practical application of database migration techniques and graph database technologies.

---

**Author**: Your Name  
**Institution**: Your University  
**Course**: Database Management Systems  
**Year**: 2025
