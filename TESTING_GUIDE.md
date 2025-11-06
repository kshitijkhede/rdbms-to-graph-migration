# 🧪 Complete Testing Guide

## Prerequisites Check

Before testing, ensure you have:

### 1. MySQL Installed and Running

```bash
# Check if MySQL is installed
mysql --version

# If not installed, install it:
sudo apt update
sudo apt install mysql-server

# Start MySQL service
sudo systemctl start mysql
sudo systemctl enable mysql

# Secure installation (set root password)
sudo mysql_secure_installation
```

### 2. Neo4j Installed and Running

**Option A: Neo4j Desktop (Recommended for local testing)**
1. Download from: https://neo4j.com/download/
2. Install and launch Neo4j Desktop
3. Create a new project
4. Add a local DBMS (database)
5. Set password (e.g., "password")
6. Start the database

**Option B: Neo4j Community Edition**
```bash
# Follow instructions at: https://neo4j.com/docs/operations-manual/current/installation/
```

---

## 🚀 Step-by-Step Testing Process

### Step 1: Configure Database Credentials

Edit `config/config.py` with your actual credentials:

```bash
cd /home/student/DBMS/Project/rdbms-to-graph-migration
nano config/config.py  # or use any text editor
```

Update:
```python
MYSQL_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'YOUR_MYSQL_PASSWORD',  # ← Change this!
    'database': 'migration_source_ecommerce',
}

NEO4J_CONFIG = {
    'uri': 'neo4j://localhost:7687',
    'user': 'neo4j',
    'password': 'YOUR_NEO4J_PASSWORD',  # ← Change this!
}
```

### Step 2: Load Sample E-Commerce Schema

```bash
# Load the schema into MySQL
mysql -u root -p < sql_schemas/ecommerce_schema.sql

# Verify it loaded
mysql -u root -p -e "USE migration_source_ecommerce; SHOW TABLES;"
```

Expected output:
```
+----------------------------------------+
| Tables_in_migration_source_ecommerce   |
+----------------------------------------+
| Customers                              |
| Order_Items                            |
| Orders                                 |
| Products                               |
+----------------------------------------+
```

### Step 3: Verify Sample Data

```bash
mysql -u root -p -e "USE migration_source_ecommerce; SELECT * FROM Customers;"
```

Expected output:
```
+-------------+---------------+------------------+
| customer_id | customer_name | email            |
+-------------+---------------+------------------+
| C100        | Customer A    | a@example.com    |
| C200        | Customer B    | b@example.com    |
+-------------+---------------+------------------+
```

### Step 4: Test Neo4j Connection

```bash
# Activate virtual environment if not already active
source venv/bin/activate

# Test connection
python -m src.neo4j_connection
```

Expected output:
```
Attempting to verify Neo4j connection...
Success: Neo4j connection verified.
Neo4j setup is correct.
Driver closed.
```

### Step 5: Run Phase 1 - Extract Metadata

```bash
python main.py --phase 1 --database migration_source_ecommerce
```

Expected output:
```
======================================================================
                        PHASE 1: METADATA EXTRACTION
======================================================================

Connected to MySQL database: migration_source_ecommerce
Found 4 tables: ['Customers', 'Order_Items', 'Orders', 'Products']

Analyzing table: Customers
  - Columns: 3
  - Primary Keys: ['customer_id']
  - Foreign Keys: 0
  - Junction Table: False
  - Inheritance: False

Analyzing table: Order_Items
  - Columns: 4
  - Primary Keys: ['order_id', 'product_id']
  - Foreign Keys: 2
  - Junction Table: True
  - Inheritance: False

Analyzing table: Orders
  - Columns: 3
  - Primary Keys: ['order_id']
  - Foreign Keys: 1
  - Junction Table: False
  - Inheritance: False

Analyzing table: Products
  - Columns: 4
  - Primary Keys: ['product_id']
  - Foreign Keys: 0
  - Junction Table: False
  - Inheritance: False

Mapping file saved to: data/mapping.json

✓ Phase 1 completed successfully!
```

### Step 6: Review Generated Mapping (Optional)

```bash
# View the generated mapping
cat data/mapping.json | head -50

# Or open in an editor to customize
nano data/mapping.json
```

The mapping file shows:
- Table structures
- Detected patterns (junction tables, inheritance)
- Default transformation rules

You can customize:
- Node labels
- Relationship types
- Property mappings

### Step 7: Run Phase 3 - Migrate Data

```bash
python main.py --phase 3 --database migration_source_ecommerce --clear
```

Expected output:
```
======================================================================
                PHASE 3: ETL PIPELINE - DATA MIGRATION
======================================================================

Loading mapping file: data/mapping.json
Mapping loaded for database: migration_source_ecommerce
Tables to migrate: 4
Connected to MySQL: migration_source_ecommerce
Attempting to verify Neo4j connection...
Success: Neo4j connection verified.
Clearing Neo4j database...
Database cleared successfully.

Creating Neo4j constraints...
  Created constraint: Customers_customer_id_unique
  Created constraint: Products_product_id_unique
  Created constraint: Orders_order_id_unique

--- Migrating Entity Tables (Nodes) ---

Migrating entity table: Customers
  Extracting data from Customers...
    Extracted 2 rows
    Migrated 2/2 records
  ✓ Successfully migrated 2 nodes for Customers

Migrating entity table: Products
  Extracting data from Products...
    Extracted 3 rows
    Migrated 3/3 records
  ✓ Successfully migrated 3 nodes for Products

Migrating entity table: Orders
  Extracting data from Orders...
    Extracted 3 rows
    Migrated 3/3 records
  ✓ Successfully migrated 3 nodes for Orders

--- Creating Relationships from Foreign Keys ---

Creating relationships for: Orders
  Creating HAS_CUSTOMERS relationships...
    ✓ Created 3 HAS_CUSTOMERS relationships

--- Migrating Junction Tables (Many-to-Many) ---

Migrating junction table: Order_Items
  Extracting data from Order_Items...
    Extracted 5 rows
  ✓ Created 5 ORDERS_TO_PRODUCTS relationships

======================================================================
Migration completed successfully!
======================================================================
```

### Step 8: Verify Data in Neo4j Browser

Open Neo4j Browser (usually http://localhost:7474) and run:

```cypher
// View all nodes
MATCH (n) RETURN n LIMIT 25

// View schema
CALL db.schema.visualization()

// Count nodes by type
MATCH (n)
RETURN labels(n) as Type, COUNT(n) as Count

// See customer orders
MATCH (c:Customers)-[r]->(o:Orders)
RETURN c, r, o

// Complex query: Products ordered by each customer
MATCH path = (c:Customers)-[:HAS_ORDERS]->(o:Orders)-[:CONTAINS]->(p:Products)
RETURN c.customer_name, COLLECT(p.product_name) as products_ordered
```

Expected results:
- 2 Customer nodes
- 3 Product nodes
- 3 Order nodes
- 3 HAS_CUSTOMERS relationships
- 5 CONTAINS relationships (from Order_Items)

### Step 9: Run Phase 4 - Validate Migration

```bash
python main.py --phase 4 --database migration_source_ecommerce
```

Expected output:
```
======================================================================
                    PHASE 4: MIGRATION VALIDATION
======================================================================

Loading mapping file: data/mapping.json
Connected to MySQL: migration_source_ecommerce
Attempting to verify Neo4j connection...
Success: Neo4j connection verified.

--- Validating Row Counts ---

Customers:
  MySQL rows: 2
  Neo4j nodes: 2
  Status: ✓ PASS

Products:
  MySQL rows: 3
  Neo4j nodes: 3
  Status: ✓ PASS

Orders:
  MySQL rows: 3
  Neo4j nodes: 3
  Status: ✓ PASS

--- Validating Relationships ---

Orders -> HAS_CUSTOMERS:
  MySQL FKs: 3
  Neo4j relationships: 3
  Status: ✓ PASS

--- Running Sample Business Queries ---

Query: Customers with orders
  MySQL: 2
  Neo4j: 2
  Status: ✓ PASS

Query: Total unique products ordered
  MySQL: 3
  Neo4j: 3
  Status: ✓ PASS

======================================================================
                        VALIDATION REPORT
======================================================================

Total Tests: 8
Passed: 8 ✓
Failed: 0 ✗

Success Rate: 100.0%

🎉 All validations passed! Migration is successful.
======================================================================
```

---

## 🎯 Testing the University Schema (Inheritance Pattern)

After successfully testing E-Commerce, try the University schema:

```bash
# Load university schema
mysql -u root -p < sql_schemas/university_schema.sql

# Run full pipeline
python main.py --full --database migration_source_university --clear
```

This demonstrates:
- Class Table Inheritance (CTI)
- Person as base entity
- Student and Professor as sub-types
- Multi-label nodes in Neo4j

---

## 🐛 Troubleshooting

### Issue: "Can't connect to MySQL server"

**Solution:**
```bash
sudo systemctl start mysql
sudo systemctl status mysql
```

### Issue: "Access denied for user 'root'"

**Solution:**
```bash
# Reset root password
sudo mysql
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'newpassword';
FLUSH PRIVILEGES;
EXIT;
```

### Issue: "Failed to connect to Neo4j database"

**Solution:**
- Ensure Neo4j Desktop database is Started (green play button)
- Check URI: `neo4j://localhost:7687`
- Verify password in config.py matches Neo4j

### Issue: "Import errors" (neo4j, pandas, etc.)

**Solution:**
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Issue: "No module named 'config'"

**Solution:**
```bash
# Make sure you're in the project root
cd /home/student/DBMS/Project/rdbms-to-graph-migration
python main.py --help
```

---

## 📊 Expected Results Summary

### E-Commerce Migration:
- **Nodes**: 8 total (2 Customers + 3 Products + 3 Orders)
- **Relationships**: 8 total (3 HAS_CUSTOMERS + 5 CONTAINS)
- **Pattern**: Aggregation via junction table

### University Migration:
- **Nodes**: 3 total (1 base Person, 1 Student:Person, 1 Professor:Person)
- **Relationships**: Based on enrollment data
- **Pattern**: Class Table Inheritance (multi-label nodes)

---

## ✅ Success Checklist

- [ ] MySQL installed and running
- [ ] Neo4j installed and running
- [ ] Sample schema loaded into MySQL
- [ ] Configuration file updated with correct passwords
- [ ] Neo4j connection test passed
- [ ] Phase 1 extracted metadata successfully
- [ ] Phase 3 migrated data without errors
- [ ] Phase 4 validation shows 100% pass rate
- [ ] Can query data in Neo4j Browser
- [ ] All expected nodes and relationships exist

---

## 🎓 Learning Outcomes

After completing this testing:

✅ Understand SCT migration methodology  
✅ See pattern detection in action (junction tables, inheritance)  
✅ Experience ETL pipeline execution  
✅ Learn graph data modeling  
✅ Validate data integrity across systems  
✅ Write Cypher queries  

**Congratulations!** You've successfully tested a production-grade database migration engine! 🎉
