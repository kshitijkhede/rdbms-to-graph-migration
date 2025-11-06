# RDBMS-to-Graph Migration Engine

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Neo4j](https://img.shields.io/badge/neo4j-5.x-green.svg)](https://neo4j.com/)
[![MySQL](https://img.shields.io/badge/mysql-8.0+-orange.svg)](https://www.mysql.com/)

## 📋 Overview

An advanced **Source-to-Conceptual-to-Target (SCT) migration engine** that migrates data from relational databases (MySQL) to graph databases (Neo4j) while preserving and enriching semantic relationships. This project implements the research findings from the IEEE paper *"Data Migration from Conventional Databases into NoSQL: Methods and Techniques"* (2023).

### Key Features

- ✨ **Intelligent Schema Analysis**: Automatically detects tables, columns, PKs, FKs, and complex patterns
- 🔄 **Pattern Recognition**: Identifies inheritance (Class Table Inheritance) and aggregation patterns
- 📊 **ETL Pipeline**: Efficient batch processing with Pandas for data transformation
- ✅ **Validation Suite**: Comprehensive validation to ensure migration integrity
- 🎯 **Configurable Mapping**: Human-enrichable JSON configuration for semantic control
- 🚀 **Production-Ready**: Transaction-safe, batch processing, error handling

## 🏗️ Architecture

The engine follows a modular, 4-phase architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                    RDBMS-to-Graph Migration Engine          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Phase 1: Metadata Extractor                                │
│  ├─ Interrogates information_schema                         │
│  ├─ Detects tables, columns, PKs, FKs                       │
│  └─ Generates mapping.json (draft)                          │
│                                                              │
│  Phase 2: Semantic Mapping Configurator (Manual)            │
│  ├─ Review and enrich mapping.json                          │
│  ├─ Define inheritance patterns                             │
│  └─ Configure aggregation rules                             │
│                                                              │
│  Phase 3: Data ETL Pipeline                                 │
│  ├─ Reads enriched mapping.json                             │
│  ├─ Extracts from MySQL (Pandas)                            │
│  ├─ Transforms data in-flight                               │
│  └─ Loads into Neo4j (Cypher)                               │
│                                                              │
│  Phase 4: Validation Suite                                  │
│  ├─ Validates row counts                                    │
│  ├─ Verifies relationships                                  │
│  └─ Runs business queries                                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘

Source (MySQL)  →  Conceptual (JSON)  →  Target (Neo4j)
```

## 🔧 Technical Stack

- **Language**: Python 3.10+
- **Source Database**: MySQL 8.0+
- **Target Database**: Neo4j 5.x
- **Key Libraries**:
  - `neo4j` - Official Neo4j Python driver
  - `mysql-connector-python` - MySQL database connector
  - `pandas` - Data manipulation and analysis
  - `SQLAlchemy` - SQL toolkit and ORM

## 📦 Installation

### Prerequisites

1. **Python 3.10+**
   ```bash
   python --version
   ```

2. **MySQL 8.0+**
   ```bash
   mysql --version
   ```

3. **Neo4j 5.x**
   - Download [Neo4j Desktop](https://neo4j.com/download/)
   - Or use [Neo4j AuraDB](https://neo4j.com/cloud/aura/) (cloud)

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd rdbms-to-graph-migration
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure databases**
   
   Edit `config/config.py`:
   ```python
   MYSQL_CONFIG = {
       'host': 'localhost',
       'port': 3306,
       'user': 'root',
       'password': 'your_mysql_password',
       'database': 'migration_source_ecommerce',
   }
   
   NEO4J_CONFIG = {
       'uri': 'neo4j://localhost:7687',
       'user': 'neo4j',
       'password': 'your_neo4j_password',
   }
   ```

5. **Setup sample databases**
   
   Load the sample schemas into MySQL:
   ```bash
   # E-Commerce schema (demonstrates aggregation)
   mysql -u root -p < sql_schemas/ecommerce_schema.sql
   
   # University schema (demonstrates inheritance)
   mysql -u root -p < sql_schemas/university_schema.sql
   ```

6. **Verify Neo4j connection**
   ```bash
   python -m src.neo4j_connection
   ```

## 🚀 Usage

### Quick Start - Full Pipeline

Run the complete migration pipeline:

```bash
python main.py --full --database migration_source_ecommerce --clear
```

### Individual Phases

#### Phase 1: Extract Metadata

Extract schema information from MySQL:

```bash
python main.py --phase 1 --database migration_source_ecommerce
```

Or run directly:
```bash
python -m src.extractor migration_source_ecommerce
```

This generates `data/mapping.json` containing:
- Table structures
- Column definitions
- Primary/Foreign keys
- Detected patterns (junction tables, inheritance)
- Default mapping rules

#### Phase 2: Enrich Mapping (Manual)

Review and edit `data/mapping.json` to:
- Customize node labels
- Define relationship types
- Configure property mappings
- Mark inheritance hierarchies
- Specify aggregation rules

Example mapping structure:
```json
{
  "database": "migration_source_ecommerce",
  "tables": {
    "Customers": {
      "mapping": {
        "type": "entity",
        "node_label": "Customer",
        "properties": [...],
        "relationships": [...]
      }
    }
  }
}
```

#### Phase 3: Migrate Data

Execute the ETL pipeline:

```bash
python main.py --phase 3 --database migration_source_ecommerce --clear
```

Or run directly:
```bash
python -m src.loader data/mapping.json migration_source_ecommerce --clear
```

Options:
- `--clear`: Clears Neo4j database before migration
- `--mapping`: Specify custom mapping file

#### Phase 4: Validate Migration

Verify migration integrity:

```bash
python main.py --phase 4 --database migration_source_ecommerce
```

Or run directly:
```bash
python -m src.validator data/mapping.json migration_source_ecommerce
```

The validator checks:
- Row counts (MySQL vs Neo4j)
- Relationship counts
- Business query consistency

## 📊 Sample Schemas

### E-Commerce Schema (Aggregation Pattern)

Demonstrates how composite keys and aggregation relationships are handled:

**Tables:**
- `Customers` → Customer nodes
- `Products` → Product nodes
- `Orders` → Order nodes (aggregate root)
- `Order_Items` → Relationships with properties (dissolved junction table)

**Graph Model:**
```
(Customer)-[:PLACED]->(Order)-[:CONTAINS {quantity, price}]->(Product)
```

### University Schema (Inheritance Pattern)

Demonstrates Class Table Inheritance (CTI):

**Tables:**
- `Person` → Base entity
- `Student` → Inherits from Person
- `Professor` → Inherits from Person
- `Enrolled_In` → Enrollment relationships

**Graph Model:**
```
(Student:Person)-[:ENROLLED_IN {grade}]->(Course)
(Professor:Person)-[:TEACHES]->(Course)
```

## 🎯 Transformation Rules

### Default Mappings

1. **Tables → Node Labels**
   - Each entity table becomes a node label
   - Example: `Customers` → `:Customer`

2. **Rows → Nodes**
   - Each row becomes a graph node
   - Example: Customer record → `(:Customer {customer_id: 'C100', ...})`

3. **Columns → Properties**
   - Non-FK columns become node properties
   - Auto-increment IDs typically excluded

4. **Foreign Keys → Relationships**
   - FK constraints become directed edges
   - Example: `Orders.customer_id` → `(Customer)-[:HAS_ORDERS]->(Order)`

5. **Junction Tables → Relationships**
   - Many-to-many tables dissolved
   - Composite keys detected automatically
   - Additional columns become relationship properties

6. **Inheritance → Node Labels**
   - CTI pattern creates multiple labels
   - Example: Student → `(:Person:Student)`

## 📈 Performance

- **Batch Processing**: Configurable batch sizes (default: 1000 records)
- **Transactions**: Safe transaction boundaries (default: 500 records)
- **Memory Efficient**: Pandas streaming for large datasets
- **Parallel Capable**: Multi-threaded loading support (future enhancement)

## 🧪 Testing

Run validation after migration:

```bash
python main.py --phase 4 --database migration_source_ecommerce
```

Expected output:
```
=== VALIDATION REPORT ===
Total Tests: 8
Passed: 8 ✓
Failed: 0 ✗
Success Rate: 100.0%

🎉 All validations passed! Migration is successful.
```

## 📁 Project Structure

```
rdbms-to-graph-migration/
├── config/
│   ├── __init__.py
│   └── config.py              # Database configuration
├── src/
│   ├── __init__.py
│   ├── extractor.py           # Phase 1: Metadata extraction
│   ├── loader.py              # Phase 3: ETL pipeline
│   ├── validator.py           # Phase 4: Validation
│   └── neo4j_connection.py    # Neo4j connection manager
├── sql_schemas/
│   ├── ecommerce_schema.sql   # E-commerce sample schema
│   └── university_schema.sql  # University sample schema
├── data/
│   └── mapping.json           # Generated mapping file (gitignored)
├── tests/                     # Unit tests (future)
├── docs/                      # Additional documentation
├── main.py                    # Main orchestrator
├── requirements.txt           # Python dependencies
├── .gitignore
└── README.md
```

## 🔍 Troubleshooting

### Connection Issues

**MySQL Connection Failed:**
```bash
# Check MySQL is running
sudo systemctl status mysql

# Test connection
mysql -u root -p
```

**Neo4j Connection Failed:**
```bash
# Verify Neo4j is running in Neo4j Desktop
# Or test connection
python -m src.neo4j_connection
```

### Migration Errors

**"No primary key found":**
- Ensure source tables have primary keys defined
- Check `information_schema` access permissions

**"Constraint already exists":**
- Use `--clear` flag to clear database before migration
- Or manually drop constraints in Neo4j Browser

### Validation Failures

**Row count mismatch:**
- Check if junction tables are included in count
- Verify data wasn't modified during migration

**Relationship count mismatch:**
- Review FK mapping in `mapping.json`
- Check for NULL foreign key values

## 🤝 Contributing

Contributions are welcome! Areas for enhancement:

- [ ] Support for PostgreSQL source databases
- [ ] Support for MongoDB target databases
- [ ] GUI for mapping enrichment
- [ ] Advanced pattern detection (polymorphic associations)
- [ ] Incremental migration support
- [ ] Performance profiling tools
- [ ] Docker containerization

## 📚 References

This project implements concepts from:

1. IEEE Paper: *"Data Migration from Conventional Databases into NoSQL: Methods and Techniques"* (2023)
2. Neo4j Documentation: [Graph Data Modeling](https://neo4j.com/developer/guide-data-modeling/)
3. Martin Fowler: [ORM Patterns](https://martinfowler.com/eaaCatalog/)

## 📄 License

MIT License - see LICENSE file for details

## 👥 Authors

Developed as part of DBMS research project

## 🙏 Acknowledgments

- Research paper authors for theoretical foundation
- Neo4j community for graph modeling best practices
- MySQL and Python communities for excellent documentation

---

**Note**: This is a research/educational project. For production use, consider:
- Adding comprehensive error handling
- Implementing logging framework
- Adding retry mechanisms
- Performance optimization for large datasets
- Security hardening (credential management)
