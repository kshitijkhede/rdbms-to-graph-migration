# 🚀 How to Run and View Results

## Quick Start Guide

### 1. Prerequisites Check

Make sure these services are running:

```bash
# Check MySQL is running
mysql -u migration -p'Migration@123' -e "SHOW DATABASES;" | grep migration_source

# Check Neo4j is running
ps aux | grep neo4j | grep -v grep
```

### 2. Activate Virtual Environment

```bash
cd /home/student/DBMS/Project/rdbms-to-graph-migration
source venv/bin/activate
```

---

## 🎯 Running the Complete Migration

### Option 1: University Schema (CTI Inheritance Pattern)

```bash
# Step 1: Extract schema and detect patterns
python main.py --phase 1 --database migration_source_university

# Step 2: Review the generated mapping (optional)
cat data/mapping.json | python3 -m json.tool | less

# Step 3: Migrate data to Neo4j
python main.py --phase 3 --database migration_source_university

# Step 4: Validate the migration
python main.py --phase 4 --database migration_source_university
```

**Expected Output**: 8/8 tests passed ✓

### Option 2: E-Commerce Schema (Junction Table Pattern)

```bash
# Step 1: Extract schema
python main.py --phase 1 --database migration_source_ecommerce

# Step 2: Migrate data
python main.py --phase 3 --database migration_source_ecommerce

# Step 3: Validate
python main.py --phase 4 --database migration_source_ecommerce
```

**Expected Output**: 7/7 tests passed ✓

---

## 👁️ Viewing Results in Neo4j Browser

### Method 1: Neo4j Browser (Recommended)

1. **Open Neo4j Browser**:
   ```
   http://localhost:7474
   ```

2. **Login**:
   - Username: `neo4j`
   - Password: `Migration@123`

3. **View All Data**:
   ```cypher
   MATCH (n)
   RETURN n
   LIMIT 100
   ```

4. **View Specific Patterns**:

   **University - CTI Multi-Label Nodes**:
   ```cypher
   // See Students with multi-labels (:Person:Student)
   MATCH (s:Person:Student)
   RETURN s
   
   // See Professors with multi-labels (:Person:Professor)
   MATCH (p:Person:Professor)
   RETURN p
   
   // See enrollment relationships
   MATCH (e:Enrolled_In)-[:HAS_STUDENT]->(s:Student)
   RETURN e, s
   ```

   **E-Commerce - Junction Table Dissolution**:
   ```cypher
   // See dissolved junction table (Order_Items → CONTAINS)
   MATCH (o:Orders)-[r:CONTAINS]->(p:Products)
   RETURN o, r, p
   
   // Calculate Customer A's revenue
   MATCH (c:Customers {customer_name: 'Customer A'})
         <-[:HAS_CUSTOMERS]-(o:Orders)
         -[r:CONTAINS]->(p:Products)
   RETURN c.customer_name, 
          p.product_name, 
          r.quantity, 
          r.price_at_purchase,
          (r.quantity * r.price_at_purchase) AS line_total
   ```

### Method 2: Command Line Query

Create a quick query script:

```bash
python3 << 'EOF'
from neo4j import GraphDatabase

driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "Migration@123"))

print("\n=== CURRENT GRAPH STATISTICS ===\n")

with driver.session() as session:
    # Show all node types
    result = session.run("MATCH (n) RETURN labels(n)[0] as label, count(*) as count ORDER BY label")
    print("📊 Nodes:")
    for record in result:
        print(f"   • {record['label']}: {record['count']}")
    
    # Show all relationship types
    result = session.run("MATCH ()-[r]->() RETURN type(r) as type, count(*) as count ORDER BY type")
    print("\n🔗 Relationships:")
    for record in result:
        print(f"   • :{record['type']}: {record['count']}")
    
    # Show sample data
    print("\n📝 Sample Data:")
    result = session.run("MATCH (n) RETURN n LIMIT 3")
    for record in result:
        print(f"   {dict(record['n'])}")

driver.close()
EOF
```

---

## 📊 Viewing MySQL Source Data (Before Migration)

```bash
# University schema
mysql -u migration -p'Migration@123' migration_source_university -e "
SELECT p.person_id, p.name, s.major, s.gpa 
FROM Person p 
LEFT JOIN Student s ON p.person_id = s.person_id;
"

# E-Commerce schema
mysql -u migration -p'Migration@123' migration_source_ecommerce -e "
SELECT oi.order_id, oi.product_id, oi.quantity, oi.price_at_purchase
FROM Order_Items oi
LIMIT 5;
"
```

---

## 🔍 Comparing MySQL vs Neo4j Results

Run this validation script:

```bash
python3 << 'EOF'
from neo4j import GraphDatabase
import mysql.connector

print("\n=== UNIVERSITY SCHEMA COMPARISON ===\n")

# MySQL
mysql_conn = mysql.connector.connect(
    host='localhost',
    user='migration',
    password='Migration@123',
    database='migration_source_university'
)
cursor = mysql_conn.cursor(dictionary=True)
cursor.execute("SELECT COUNT(*) as count FROM Student")
mysql_students = cursor.fetchone()['count']
print(f"MySQL Students: {mysql_students}")
mysql_conn.close()

# Neo4j
neo4j_driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "Migration@123"))
with neo4j_driver.session() as session:
    result = session.run("MATCH (s:Student) RETURN count(s) as count")
    neo4j_students = result.single()['count']
    print(f"Neo4j Students: {neo4j_students}")
    
    # Check multi-label implementation
    result = session.run("MATCH (n:Person:Student) RETURN count(n) as count")
    multi_label = result.single()['count']
    print(f"Multi-label (:Person:Student): {multi_label}")
    
    if mysql_students == neo4j_students == multi_label:
        print("✅ CTI Multi-Label Implementation: SUCCESS!")
    else:
        print("❌ Mismatch detected")

neo4j_driver.close()
EOF
```

---

## 📁 Viewing Generated Files

```bash
# View the enriched mapping file
cat data/mapping.json | python3 -m json.tool | less

# Search for enrichment rules
grep -A5 "enrichment_rule" data/mapping.json | grep -v "^--$"

# Check for multi-label nodes
grep "merge_on_label" data/mapping.json

# Check for junction table dissolution
grep "dissolve_to_relationship" data/mapping.json
```

---

## 🎨 Visual Graph Exploration

### Using Neo4j Browser Graph View

1. Open http://localhost:7474
2. Run this query for a visual graph:

```cypher
// University Schema - See the CTI pattern
MATCH path = (p:Person)-[]-(related)
RETURN path
LIMIT 50
```

```cypher
// E-Commerce - See the dissolved junction pattern
MATCH path = (c:Customers)<-[]-(o:Orders)-[]->(p:Products)
RETURN path
LIMIT 50
```

The browser will show:
- **Nodes** as circles (colored by label)
- **Relationships** as arrows
- **Multi-labels** as nodes with multiple colors

---

## 🧪 Testing Individual Components

### Test Pattern Detection

```bash
python3 << 'EOF'
import sys
sys.path.insert(0, '/home/student/DBMS/Project/rdbms-to-graph-migration')
from src.extractor import MetadataExtractor
from config.config import MYSQL_CONFIG

MYSQL_CONFIG['database'] = 'migration_source_university'
extractor = MetadataExtractor(MYSQL_CONFIG)
extractor.connect()

# Test inheritance detection
table_info = extractor.extract_tables()
student_info = table_info['Student']
print(f"Student table inheritance detected: {student_info.get('is_inheritance', False)}")
print(f"Enrichment rule: {student_info['mapping'].get('enrichment_rule', 'NONE')}")

extractor.disconnect()
EOF
```

### Test Cypher Generation

```bash
python3 << 'EOF'
import sys
sys.path.insert(0, '/home/student/DBMS/Project/rdbms-to-graph-migration')
from src.loader import DataLoader

loader = DataLoader()
loader.load_mapping()

# Test Cypher for Student table
student_mapping = loader.mapping['tables']['Student']
cypher, is_enriched = loader.get_node_cypher_query(
    student_mapping['mapping'],
    student_mapping['primary_keys']
)
print(f"\nGenerated Cypher for Student:")
print(cypher)
print(f"\nIs Enriched: {is_enriched}")
EOF
```

---

## 🐛 Troubleshooting

### Neo4j Connection Issues

```bash
# Check if Neo4j is running
sudo systemctl status neo4j

# Or check process
ps aux | grep neo4j

# Test connection
python3 -c "
from neo4j import GraphDatabase
driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'Migration@123'))
driver.verify_connectivity()
print('✓ Connected')
driver.close()
"
```

### MySQL Connection Issues

```bash
# Test connection
mysql -u migration -p'Migration@123' -e "SELECT 1;"

# Check databases exist
mysql -u migration -p'Migration@123' -e "SHOW DATABASES LIKE 'migration_source%';"
```

### Clear Neo4j and Start Fresh

```bash
python3 << 'EOF'
from neo4j import GraphDatabase
driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "Migration@123"))
with driver.session() as session:
    session.run("MATCH (n) DETACH DELETE n")
    print("✓ Neo4j database cleared")
driver.close()
EOF
```

---

## 📈 Performance Monitoring

```bash
# Monitor during migration
watch -n 2 'echo "MySQL Rows:" && mysql -u migration -pMigration@123 migration_source_university -e "SELECT TABLE_NAME, TABLE_ROWS FROM information_schema.TABLES WHERE TABLE_SCHEMA=\"migration_source_university\"" && echo "\nNeo4j Nodes:" && python3 -c "from neo4j import GraphDatabase; d=GraphDatabase.driver(\"bolt://localhost:7687\", auth=(\"neo4j\", \"Migration@123\")); s=d.session(); r=s.run(\"MATCH (n) RETURN count(n) as c\"); print(r.single()[\"c\"]); d.close()"'
```

---

## 📚 Additional Resources

- **Full Documentation**: See `COMPLETION_REPORT.md`
- **Architecture**: See `docs/ARCHITECTURE.md`
- **Quick Start**: See `docs/QUICKSTART.md`
- **Mapping File**: `data/mapping.json` (generated after Phase 1)

---

## ✨ Pro Tips

1. **Always run Phase 1 first** - It generates the mapping file needed for Phase 3
2. **Check the mapping file** - Review enrichment rules before migrating
3. **Use Neo4j Browser** - Best way to visualize the graph
4. **Run Phase 4** - Validates that migration was successful
5. **Clear Neo4j between runs** - Prevents duplicate data

---

**Need help?** Check the logs or run with verbose mode:
```bash
python main.py --phase 3 --database migration_source_university --verbose
```
