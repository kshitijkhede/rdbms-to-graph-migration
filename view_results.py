#!/usr/bin/env python3
"""
Interactive Results Viewer for RDBMS-to-Graph Migration
"""
from neo4j import GraphDatabase
import mysql.connector
from tabulate import tabulate

class ResultsViewer:
    def __init__(self):
        self.neo4j_driver = GraphDatabase.driver(
            "bolt://localhost:7687", 
            auth=("neo4j", "Migration@123")
        )
    
    def show_neo4j_overview(self):
        print("\n" + "="*80)
        print("                    NEO4J GRAPH DATABASE OVERVIEW")
        print("="*80)
        
        with self.neo4j_driver.session() as session:
            # Nodes
            result = session.run("MATCH (n) RETURN labels(n)[0] as label, count(*) as count ORDER BY label")
            node_data = [[r['label'], r['count']] for r in result]
            print("\n📊 NODES:")
            print(tabulate(node_data, headers=['Label', 'Count'], tablefmt='grid'))
            
            # Relationships
            result = session.run("MATCH ()-[r]->() RETURN type(r) as type, count(*) as count ORDER BY type")
            rel_data = [[r['type'], r['count']] for r in result]
            print("\n🔗 RELATIONSHIPS:")
            print(tabulate(rel_data, headers=['Type', 'Count'], tablefmt='grid'))
    
    def show_cti_pattern(self):
        print("\n" + "="*80)
        print("        CTI PATTERN: Multi-Label Nodes (University Schema)")
        print("="*80)
        
        with self.neo4j_driver.session() as session:
            result = session.run("""
                MATCH (n:Person:Student)
                RETURN n.person_id as id, n.name as name, n.major as major, n.gpa as gpa
                LIMIT 5
            """)
            data = [[r['id'], r['name'], r['major'], r['gpa']] for r in result]
            if data:
                print("\n✨ Multi-label Nodes: (:Person:Student)")
                print(tabulate(data, headers=['ID', 'Name', 'Major', 'GPA'], tablefmt='grid'))
            else:
                print("\n⚠️  No multi-label nodes found. Run University schema migration:")
                print("   python main.py --phase 3 --database migration_source_university")
    
    def show_junction_dissolution(self):
        print("\n" + "="*80)
        print("    JUNCTION TABLE DISSOLUTION: Relationships with Properties")
        print("="*80)
        
        with self.neo4j_driver.session() as session:
            result = session.run("""
                MATCH (o:Orders)-[r:CONTAINS]->(p:Products)
                RETURN o.order_id as order, p.product_name as product, 
                       r.quantity as qty, r.price_at_purchase as price,
                       (r.quantity * r.price_at_purchase) as total
                ORDER BY o.order_id
                LIMIT 10
            """)
            data = [[r['order'], r['product'], r['qty'], f"${r['price']:.2f}", f"${r['total']:.2f}"] for r in result]
            if data:
                print("\n🔄 Order_Items table → :CONTAINS relationships")
                print(tabulate(data, headers=['Order ID', 'Product', 'Qty', 'Price', 'Total'], tablefmt='grid'))
            else:
                print("\n⚠️  No :CONTAINS relationships found. Run E-Commerce schema migration:")
                print("   python main.py --phase 3 --database migration_source_ecommerce")
    
    def show_business_query(self):
        print("\n" + "="*80)
        print("              BUSINESS QUERY: Customer Revenue Calculation")
        print("="*80)
        
        with self.neo4j_driver.session() as session:
            result = session.run("""
                MATCH (c:Customers)<-[:HAS_CUSTOMERS]-(o:Orders)-[r:CONTAINS]->(p:Products)
                WITH c.customer_name as customer, 
                     sum(r.quantity * r.price_at_purchase) as total
                RETURN customer, total
                ORDER BY total DESC
            """)
            data = [[r['customer'], f"${r['total']:.2f}"] for r in result]
            if data:
                print("\n💰 Revenue by Customer:")
                print(tabulate(data, headers=['Customer', 'Total Revenue'], tablefmt='grid'))
                
                # Show query comparison
                print("\n✨ Query Simplification:")
                print("   SQL:    4-table JOIN (Customers → Orders → Order_Items → Products)")
                print("   Cypher: 2-hop traversal (Customers ← Orders → Products)")
            else:
                print("\n⚠️  No revenue data found.")
    
    def show_comparison(self):
        print("\n" + "="*80)
        print("                MYSQL vs NEO4J COMPARISON")
        print("="*80)
        
        try:
            # MySQL counts
            mysql_conn = mysql.connector.connect(
                host='localhost',
                user='migration',
                password='Migration@123',
                database='migration_source_ecommerce'
            )
            cursor = mysql_conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM Customers")
            mysql_customers = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM Orders")
            mysql_orders = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM Order_Items")
            mysql_order_items = cursor.fetchone()[0]
            
            mysql_conn.close()
            
            # Neo4j counts
            with self.neo4j_driver.session() as session:
                result = session.run("MATCH (c:Customers) RETURN count(c) as count")
                neo4j_customers = result.single()['count']
                
                result = session.run("MATCH (o:Orders) RETURN count(o) as count")
                neo4j_orders = result.single()['count']
                
                result = session.run("MATCH ()-[r:CONTAINS]->() RETURN count(r) as count")
                neo4j_contains = result.single()['count']
            
            data = [
                ['Customers', mysql_customers, neo4j_customers, '✓' if mysql_customers == neo4j_customers else '✗'],
                ['Orders', mysql_orders, neo4j_orders, '✓' if mysql_orders == neo4j_orders else '✗'],
                ['Order_Items / :CONTAINS', mysql_order_items, neo4j_contains, '✓' if mysql_order_items == neo4j_contains else '✗']
            ]
            print(tabulate(data, headers=['Entity', 'MySQL Rows', 'Neo4j Count', 'Match'], tablefmt='grid'))
            
        except Exception as e:
            print(f"\n⚠️  Could not connect to MySQL: {e}")
    
    def close(self):
        self.neo4j_driver.close()

if __name__ == "__main__":
    viewer = ResultsViewer()
    
    try:
        viewer.show_neo4j_overview()
        viewer.show_junction_dissolution()
        viewer.show_business_query()
        viewer.show_comparison()
        
        print("\n" + "="*80)
        print("                        VIEWING OPTIONS")
        print("="*80)
        print("\n🌐 Open Neo4j Browser for visual graph:")
        print("   URL: http://localhost:7474")
        print("   Username: neo4j")
        print("   Password: Migration@123")
        print("\n📊 Sample Cypher Queries:")
        print("   MATCH (n) RETURN n LIMIT 50")
        print("   MATCH path = (:Orders)-[:CONTAINS]->(:Products) RETURN path")
        print("\n" + "="*80 + "\n")
        
    finally:
        viewer.close()
