"""
Phase 4: Validation Suite
Verifies migration integrity by running parallel queries on MySQL and Neo4j
"""
import json
import mysql.connector
from src.neo4j_connection import Neo4jConnection
from config.config import MYSQL_CONFIG, MAPPING_FILE_PATH


class MigrationValidator:
    """
    Validates data migration by comparing MySQL and Neo4j results
    """
    
    def __init__(self, mapping_file=None, database_name=None):
        """
        Initialize the validator
        
        Args:
            mapping_file: Path to mapping JSON file
            database_name: MySQL database name
        """
        self.mapping_file = mapping_file or MAPPING_FILE_PATH
        self.mapping = None
        
        # MySQL configuration
        self.mysql_config = MYSQL_CONFIG.copy()
        if database_name:
            self.mysql_config['database'] = database_name
        
        self.mysql_conn = None
        self.mysql_cursor = None
        
        # Neo4j connection
        self.neo4j_conn = Neo4jConnection()
        self.neo4j_driver = None
        
        self.validation_results = []
    
    def load_mapping(self):
        """Load mapping configuration"""
        print(f"Loading mapping file: {self.mapping_file}")
        with open(self.mapping_file, 'r') as f:
            self.mapping = json.load(f)
        
        if 'database' in self.mapping:
            self.mysql_config['database'] = self.mapping['database']
    
    def connect_databases(self):
        """Establish connections to both databases"""
        # MySQL
        try:
            self.mysql_conn = mysql.connector.connect(**self.mysql_config)
            self.mysql_cursor = self.mysql_conn.cursor(dictionary=True)
            print(f"Connected to MySQL: {self.mysql_config['database']}")
        except mysql.connector.Error as e:
            print(f"Error connecting to MySQL: {e}")
            raise
        
        # Neo4j
        try:
            self.neo4j_driver = self.neo4j_conn.get_driver()
            self.neo4j_conn.verify_connectivity()
        except Exception as e:
            print(f"Error connecting to Neo4j: {e}")
            raise
    
    def disconnect_databases(self):
        """Close database connections"""
        if self.mysql_cursor:
            self.mysql_cursor.close()
        if self.mysql_conn:
            self.mysql_conn.close()
            print("Disconnected from MySQL")
        
        if self.neo4j_conn:
            self.neo4j_conn.close()
    
    def validate_row_counts(self):
        """
        Validate that the number of rows in MySQL matches nodes in Neo4j
        """
        print("\n--- Validating Row Counts ---")
        
        for table_name, table_info in self.mapping['tables'].items():
            mapping = table_info['mapping']
            
            # Skip junction tables (they become relationships)
            if mapping.get('dissolve_to_relationship'):
                print(f"\n{table_name} (Junction Table - Skipped)")
                continue
            
            node_label = mapping['node_label']
            
            # Count rows in MySQL
            self.mysql_cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
            mysql_count = self.mysql_cursor.fetchone()['count']
            
            # Count nodes in Neo4j
            with self.neo4j_driver.session() as session:
                result = session.run(f"MATCH (n:{node_label}) RETURN COUNT(n) as count")
                neo4j_count = result.single()['count']
            
            status = "✓" if mysql_count == neo4j_count else "✗"
            result = {
                'test': 'row_count',
                'table': table_name,
                'mysql_count': mysql_count,
                'neo4j_count': neo4j_count,
                'passed': mysql_count == neo4j_count
            }
            
            self.validation_results.append(result)
            
            print(f"\n{table_name}:")
            print(f"  MySQL rows: {mysql_count}")
            print(f"  Neo4j nodes: {neo4j_count}")
            print(f"  Status: {status} {'PASS' if result['passed'] else 'FAIL'}")
    
    def validate_relationships(self):
        """
        Validate that foreign key relationships are preserved
        """
        print("\n--- Validating Relationships ---")
        
        for table_name, table_info in self.mapping['tables'].items():
            mapping = table_info['mapping']
            relationships = mapping.get('relationships', [])
            
            if not relationships:
                continue
            
            node_label = mapping['node_label']
            
            for rel in relationships:
                if rel['type'] == 'foreign_key':
                    rel_type = rel['relationship_type']
                    
                    # Count relationships in MySQL (via FK)
                    source_col = rel['source_column']
                    self.mysql_cursor.execute(
                        f"SELECT COUNT(*) as count FROM {table_name} WHERE {source_col} IS NOT NULL"
                    )
                    mysql_rel_count = self.mysql_cursor.fetchone()['count']
                    
                    # Count relationships in Neo4j
                    with self.neo4j_driver.session() as session:
                        result = session.run(
                            f"MATCH (:{node_label})-[r:{rel_type}]->() RETURN COUNT(r) as count"
                        )
                        neo4j_rel_count = result.single()['count']
                    
                    status = "✓" if mysql_rel_count == neo4j_rel_count else "✗"
                    result = {
                        'test': 'relationship_count',
                        'table': table_name,
                        'relationship': rel_type,
                        'mysql_count': mysql_rel_count,
                        'neo4j_count': neo4j_rel_count,
                        'passed': mysql_rel_count == neo4j_rel_count
                    }
                    
                    self.validation_results.append(result)
                    
                    print(f"\n{table_name} -> {rel_type}:")
                    print(f"  MySQL FKs: {mysql_rel_count}")
                    print(f"  Neo4j relationships: {neo4j_rel_count}")
                    print(f"  Status: {status} {'PASS' if result['passed'] else 'FAIL'}")
    
    def validate_sample_queries(self):
        """
        Run sample business queries on both databases to verify semantic consistency
        """
        print("\n--- Running Sample Business Queries ---")
        
        database = self.mapping.get('database', '')
        
        # Define sample queries based on database type
        if 'ecommerce' in database.lower():
            self._validate_ecommerce_queries()
        elif 'university' in database.lower():
            self._validate_university_queries()
    
    def _validate_ecommerce_queries(self):
        """Sample queries for e-commerce schema"""
        
        # Query 1: Count customers with orders
        print("\nQuery: Customers with orders")
        
        self.mysql_cursor.execute("""
            SELECT COUNT(DISTINCT customer_id) as count 
            FROM Orders
        """)
        mysql_result = self.mysql_cursor.fetchone()['count']
        
        with self.neo4j_driver.session() as session:
            result = session.run("""
                MATCH (c:Customers)-[:HAS_ORDERS]->(o:Orders)
                RETURN COUNT(DISTINCT c) as count
            """)
            neo4j_result = result.single()
            neo4j_result = neo4j_result['count'] if neo4j_result else 0
        
        passed = mysql_result == neo4j_result
        status = "✓" if passed else "✗"
        
        print(f"  MySQL: {mysql_result}")
        print(f"  Neo4j: {neo4j_result}")
        print(f"  Status: {status} {'PASS' if passed else 'FAIL'}")
        
        self.validation_results.append({
            'test': 'business_query',
            'query': 'customers_with_orders',
            'mysql_result': mysql_result,
            'neo4j_result': neo4j_result,
            'passed': passed
        })
        
        # Query 2: Total products ordered
        print("\nQuery: Total unique products ordered")
        
        self.mysql_cursor.execute("""
            SELECT COUNT(DISTINCT product_id) as count 
            FROM Order_Items
        """)
        mysql_result = self.mysql_cursor.fetchone()['count']
        
        with self.neo4j_driver.session() as session:
            # This depends on how Order_Items was migrated
            result = session.run("""
                MATCH (o:Orders)-[:HAS_ORDER_ITEMS]->(p:Products)
                RETURN COUNT(DISTINCT p) as count
            """)
            record = result.single()
            neo4j_result = record['count'] if record else 0
        
        passed = mysql_result == neo4j_result
        status = "✓" if passed else "✗"
        
        print(f"  MySQL: {mysql_result}")
        print(f"  Neo4j: {neo4j_result}")
        print(f"  Status: {status} {'PASS' if passed else 'FAIL'}")
        
        self.validation_results.append({
            'test': 'business_query',
            'query': 'unique_products_ordered',
            'mysql_result': mysql_result,
            'neo4j_result': neo4j_result,
            'passed': passed
        })
    
    def _validate_university_queries(self):
        """Sample queries for university schema"""
        
        # Query 1: Count students
        print("\nQuery: Total students")
        
        self.mysql_cursor.execute("SELECT COUNT(*) as count FROM Student")
        mysql_result = self.mysql_cursor.fetchone()['count']
        
        with self.neo4j_driver.session() as session:
            result = session.run("MATCH (s:Student) RETURN COUNT(s) as count")
            neo4j_result = result.single()['count']
        
        passed = mysql_result == neo4j_result
        status = "✓" if passed else "✗"
        
        print(f"  MySQL: {mysql_result}")
        print(f"  Neo4j: {neo4j_result}")
        print(f"  Status: {status} {'PASS' if passed else 'FAIL'}")
        
        self.validation_results.append({
            'test': 'business_query',
            'query': 'total_students',
            'mysql_result': mysql_result,
            'neo4j_result': neo4j_result,
            'passed': passed
        })
        
        # Query 2: Students with enrollments
        print("\nQuery: Students with course enrollments")
        
        self.mysql_cursor.execute("""
            SELECT COUNT(DISTINCT student_id) as count 
            FROM Enrolled_In
        """)
        mysql_result = self.mysql_cursor.fetchone()['count']
        
        with self.neo4j_driver.session() as session:
            result = session.run("""
                MATCH (s:Student)-[:HAS_ENROLLED_IN]->()
                RETURN COUNT(DISTINCT s) as count
            """)
            record = result.single()
            neo4j_result = record['count'] if record else 0
        
        passed = mysql_result == neo4j_result
        status = "✓" if passed else "✗"
        
        print(f"  MySQL: {mysql_result}")
        print(f"  Neo4j: {neo4j_result}")
        print(f"  Status: {status} {'PASS' if passed else 'FAIL'}")
        
        self.validation_results.append({
            'test': 'business_query',
            'query': 'students_with_enrollments',
            'mysql_result': mysql_result,
            'neo4j_result': neo4j_result,
            'passed': passed
        })
    
    def generate_report(self):
        """Generate validation report"""
        print("\n" + "=" * 60)
        print("VALIDATION REPORT")
        print("=" * 60)
        
        total_tests = len(self.validation_results)
        passed_tests = sum(1 for r in self.validation_results if r['passed'])
        failed_tests = total_tests - passed_tests
        
        print(f"\nTotal Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✓")
        print(f"Failed: {failed_tests} ✗")
        
        if failed_tests > 0:
            print("\nFailed Tests:")
            for result in self.validation_results:
                if not result['passed']:
                    print(f"  - {result['test']}: {result.get('table', result.get('query', 'N/A'))}")
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        print(f"\nSuccess Rate: {success_rate:.1f}%")
        
        if success_rate == 100:
            print("\n🎉 All validations passed! Migration is successful.")
        else:
            print("\n⚠️  Some validations failed. Please review the migration.")
        
        print("=" * 60)
        
        return success_rate == 100
    
    def validate_all(self):
        """
        Run all validation tests
        """
        print("\n" + "=" * 60)
        print("Phase 4: Migration Validation")
        print("=" * 60)
        
        try:
            self.load_mapping()
            self.connect_databases()
            
            # Run validation tests
            self.validate_row_counts()
            self.validate_relationships()
            self.validate_sample_queries()
            
            # Generate report
            success = self.generate_report()
            
            return success
            
        except Exception as e:
            print(f"\nError during validation: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        finally:
            self.disconnect_databases()


def main():
    """
    Main function to run validation
    """
    import sys
    
    mapping_file = None
    database_name = None
    
    if len(sys.argv) > 1:
        mapping_file = sys.argv[1]
    if len(sys.argv) > 2:
        database_name = sys.argv[2]
    
    validator = MigrationValidator(mapping_file, database_name)
    success = validator.validate_all()
    
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
