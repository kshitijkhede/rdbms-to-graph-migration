#!/bin/bash
# Quick Run Script for RDBMS-to-Graph Migration Engine

echo "========================================"
echo " RDBMS-to-Graph Migration Quick Start"
echo "========================================"
echo ""

# Activate virtual environment
source venv/bin/activate

echo "Select a schema to migrate:"
echo "1) University Schema (CTI Pattern)"
echo "2) E-Commerce Schema (Junction Dissolution)"
echo "3) Both (recommended)"
echo "4) View current results"
echo ""
read -p "Enter choice (1-4): " choice

case $choice in
    1)
        echo ""
        echo "📚 Migrating University Schema..."
        echo "=================================="
        python main.py --phase 1 --database migration_source_university
        python main.py --phase 3 --database migration_source_university
        python main.py --phase 4 --database migration_source_university
        ;;
    2)
        echo ""
        echo "🛒 Migrating E-Commerce Schema..."
        echo "=================================="
        python main.py --phase 1 --database migration_source_ecommerce
        python main.py --phase 3 --database migration_source_ecommerce
        python main.py --phase 4 --database migration_source_ecommerce
        ;;
    3)
        echo ""
        echo "📊 Migrating BOTH Schemas..."
        echo "============================"
        
        echo ""
        echo "1/2: University Schema..."
        python main.py --phase 1 --database migration_source_university
        python main.py --phase 3 --database migration_source_university
        python main.py --phase 4 --database migration_source_university
        
        echo ""
        echo "2/2: E-Commerce Schema..."
        # Clear Neo4j first
        python3 << 'EOF'
from neo4j import GraphDatabase
driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "Migration@123"))
with driver.session() as session:
    session.run("MATCH (n) DETACH DELETE n")
    result = session.run("SHOW CONSTRAINTS")
    for record in result:
        try:
            session.run(f"DROP CONSTRAINT {record['name']}")
        except:
            pass
driver.close()
print("✓ Cleared Neo4j for E-Commerce migration")
EOF
        
        python main.py --phase 1 --database migration_source_ecommerce
        python main.py --phase 3 --database migration_source_ecommerce
        python main.py --phase 4 --database migration_source_ecommerce
        ;;
    4)
        echo ""
        echo "📊 Current Results..."
        echo "===================="
        python view_results.py
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "========================================"
echo " ✅ Complete!"
echo "========================================"
echo ""
echo "View results:"
echo "  • Run: python view_results.py"
echo "  • Open: http://localhost:7474 (Neo4j Browser)"
echo "  • Docs: HOW_TO_RUN.md"
echo ""
