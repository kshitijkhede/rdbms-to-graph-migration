# Quick Start Guide

This guide will help you get started with the RDBMS-to-Graph Migration Engine in 10 minutes.

## Prerequisites Check

Before starting, verify you have:

- [ ] Python 3.10 or higher installed
- [ ] MySQL 8.0 or higher running
- [ ] Neo4j 5.x installed (Desktop or AuraDB)
- [ ] Git installed (for cloning)

## Step 1: Setup Project (2 minutes)

```bash
# Clone or navigate to project directory
cd /path/to/rdbms-to-graph-migration

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Configure Databases (2 minutes)

### Configure MySQL

Edit `config/config.py`:

```python
MYSQL_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'YOUR_MYSQL_PASSWORD',  # ← Change this
    'database': 'migration_source_ecommerce',
}
```

### Configure Neo4j

1. Start Neo4j Desktop
2. Create a new database (password: e.g., "password")
3. Start the database
4. Update `config/config.py`:

```python
NEO4J_CONFIG = {
    'uri': 'neo4j://localhost:7687',
    'user': 'neo4j',
    'password': 'YOUR_NEO4J_PASSWORD',  # ← Change this
}
```

## Step 3: Load Sample Data (1 minute)

```bash
# Load E-Commerce schema into MySQL
mysql -u root -p < sql_schemas/ecommerce_schema.sql
# Enter your MySQL password when prompted

# Verify data loaded
mysql -u root -p -e "USE migration_source_ecommerce; SHOW TABLES;"
```

You should see:
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

## Step 4: Test Connections (1 minute)

```bash
# Test Neo4j connection
python -m src.neo4j_connection
```

Expected output:
```
Attempting to verify Neo4j connection...
Success: Neo4j connection verified.
Neo4j setup is correct.
```

## Step 5: Run Migration (4 minutes)

### Option A: Full Automated Pipeline

```bash
python main.py --full --database migration_source_ecommerce --clear
```

This will:
1. Extract schema metadata
2. Generate mapping.json
3. Pause for you to review (Press Enter to continue)
4. Migrate data to Neo4j
5. Validate the migration

### Option B: Step-by-Step

```bash
# Phase 1: Extract schema
python main.py --phase 1 --database migration_source_ecommerce

# Review generated file
cat data/mapping.json

# Phase 3: Migrate data
python main.py --phase 3 --database migration_source_ecommerce --clear

# Phase 4: Validate
python main.py --phase 4 --database migration_source_ecommerce
```

## Step 6: Explore Results

### In Neo4j Browser

Open Neo4j Browser (http://localhost:7474) and run:

```cypher
// View all nodes
MATCH (n) RETURN n LIMIT 50

// View schema
CALL db.schema.visualization()

// Count nodes by type
MATCH (n) 
RETURN labels(n) as Type, COUNT(n) as Count

// Find customers and their orders
MATCH (c:Customers)-[r]->(o:Orders)
RETURN c, r, o LIMIT 10

// Complex query: Customers who ordered Electronics
MATCH (c:Customers)-[:HAS_ORDERS]->(o:Orders)
      -[:HAS_ORDER_ITEMS]->(p:Products)
WHERE p.category = 'Electronics'
RETURN c.customer_name, COUNT(DISTINCT o) as order_count
```

### Validation Report

Check the validation output:

```
=== VALIDATION REPORT ===
Total Tests: 8
Passed: 8 ✓
Failed: 0 ✗
Success Rate: 100.0%

🎉 All validations passed! Migration is successful.
```

## Common Issues & Solutions

### Issue: "Can't connect to MySQL server"

**Solution:**
```bash
# Check if MySQL is running
sudo systemctl status mysql

# Start MySQL if not running
sudo systemctl start mysql

# Verify you can login
mysql -u root -p
```

### Issue: "Failed to connect to Neo4j database"

**Solution:**
- Open Neo4j Desktop
- Make sure your database is Started (green play button)
- Check the URI matches (usually `neo4j://localhost:7687`)
- Verify the password in config.py matches your Neo4j password

### Issue: "Import 'neo4j' could not be resolved"

**Solution:**
```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: "No module named 'config'"

**Solution:**
```bash
# Make sure you're running from the project root directory
cd /path/to/rdbms-to-graph-migration

# Run with python -m syntax
python -m src.extractor
```

## Next Steps

### Try the University Schema

```bash
# Load university data
mysql -u root -p < sql_schemas/university_schema.sql

# Migrate
python main.py --full --database migration_source_university --clear
```

### Customize Mappings

1. Run Phase 1 to generate mapping
2. Edit `data/mapping.json`:
   - Change node labels
   - Customize relationship types
   - Add/remove properties
3. Run Phase 3 with custom mapping:
   ```bash
   python main.py --phase 3 --mapping data/mapping.json --clear
   ```

### Explore Advanced Queries

Try these Cypher queries:

```cypher
// Find inheritance relationships (University schema)
MATCH (s:Student:Person)
RETURN s.name, s.major, s.gpa

// Find aggregation (E-commerce schema)
MATCH path = (c:Customers)-[:HAS_ORDERS]->(o:Orders)
              -[:HAS_ORDER_ITEMS]->(p:Products)
RETURN path LIMIT 5

// Complex analytics
MATCH (c:Customers)-[:HAS_ORDERS]->(o:Orders)
WITH c, COUNT(o) as total_orders
WHERE total_orders > 1
RETURN c.customer_name, total_orders
ORDER BY total_orders DESC
```

## Help & Support

- **Documentation**: See `README.md` for full documentation
- **Architecture**: See `docs/ARCHITECTURE.md` for technical details
- **Issues**: Check the troubleshooting section in README.md

## Success Checklist

- [ ] All dependencies installed
- [ ] MySQL connection successful
- [ ] Neo4j connection successful
- [ ] Sample data loaded
- [ ] Migration completed
- [ ] Validation passed (100%)
- [ ] Can query data in Neo4j Browser

**Congratulations!** 🎉 You've successfully migrated your first relational database to a graph database!
