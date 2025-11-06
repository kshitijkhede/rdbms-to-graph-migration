"""
Phase 3: ETL Pipeline / Loader
Reads mapping.json, extracts data from MySQL, transforms it, and loads into Neo4j
"""
import json
import mysql.connector
import pandas as pd
from neo4j import GraphDatabase
from config.config import MYSQL_CONFIG, NEO4J_CONFIG, MIGRATION_SETTINGS, MAPPING_FILE_PATH
from src.neo4j_connection import Neo4jConnection


class DataLoader:
    """
    ETL Pipeline for migrating data from MySQL to Neo4j
    """
    
    def __init__(self, mapping_file=None, database_name=None):
        """
        Initialize the loader
        
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
        
        # Neo4j connection
        self.neo4j_conn = Neo4jConnection()
        self.neo4j_driver = None
        
        self.batch_size = MIGRATION_SETTINGS['batch_size']
        self.transaction_size = MIGRATION_SETTINGS['transaction_size']
    
    def load_mapping(self):
        """
        Load mapping configuration from JSON file
        """
        print(f"Loading mapping file: {self.mapping_file}")
        with open(self.mapping_file, 'r') as f:
            self.mapping = json.load(f)
        
        # Update database name if different
        if 'database' in self.mapping:
            self.mysql_config['database'] = self.mapping['database']
        
        print(f"Mapping loaded for database: {self.mysql_config['database']}")
        print(f"Tables to migrate: {len(self.mapping.get('tables', {}))}")
    
    def connect_databases(self):
        """
        Establish connections to both MySQL and Neo4j
        """
        # Connect to MySQL
        try:
            self.mysql_conn = mysql.connector.connect(**self.mysql_config)
            print(f"Connected to MySQL: {self.mysql_config['database']}")
        except mysql.connector.Error as e:
            print(f"Error connecting to MySQL: {e}")
            raise
        
        # Connect to Neo4j
        try:
            self.neo4j_driver = self.neo4j_conn.get_driver()
            self.neo4j_conn.verify_connectivity()
        except Exception as e:
            print(f"Error connecting to Neo4j: {e}")
            raise
    
    def disconnect_databases(self):
        """
        Close database connections
        """
        if self.mysql_conn:
            self.mysql_conn.close()
            print("Disconnected from MySQL")
        
        if self.neo4j_conn:
            self.neo4j_conn.close()
    
    def create_constraints(self):
        """
        Create uniqueness constraints in Neo4j for efficient merging
        """
        print("\nCreating Neo4j constraints...")
        
        with self.neo4j_driver.session() as session:
            for table_name, table_info in self.mapping['tables'].items():
                mapping = table_info['mapping']
                
                # Skip junction tables
                if mapping.get('dissolve_to_relationship'):
                    continue
                
                node_label = mapping['node_label']
                primary_keys = table_info['primary_keys']
                
                # Create constraint for each primary key
                for pk in primary_keys:
                    constraint_name = f"{node_label}_{pk}_unique"
                    try:
                        query = f"""
                        CREATE CONSTRAINT {constraint_name} IF NOT EXISTS
                        FOR (n:{node_label})
                        REQUIRE n.{pk} IS UNIQUE
                        """
                        session.run(query)
                        print(f"  Created constraint: {constraint_name}")
                    except Exception as e:
                        print(f"  Constraint may already exist: {constraint_name}")
    
    def extract_table_data(self, table_name):
        """
        Extract data from MySQL table using Pandas
        
        Args:
            table_name: Name of the table to extract
            
        Returns:
            DataFrame: Table data
        """
        print(f"  Extracting data from {table_name}...")
        query = f"SELECT * FROM {table_name}"
        df = pd.read_sql(query, self.mysql_conn)
        print(f"    Extracted {len(df)} rows")
        return df
    
    def migrate_entity_table(self, table_name, table_info):
        """
        Migrate an entity table to Neo4j nodes
        
        Args:
            table_name: Name of the table
            table_info: Table metadata and mapping
        """
        print(f"\nMigrating entity table: {table_name}")
        
        mapping = table_info['mapping']
        node_label = mapping['node_label']
        
        # Extract data
        df = self.extract_table_data(table_name)
        
        if df.empty:
            print(f"  No data to migrate for {table_name}")
            return
        
        # Get property mappings
        property_mappings = {
            prop['source_column']: prop['target_property']
            for prop in mapping['properties']
        }
        
        # Get primary key for MERGE
        primary_keys = table_info['primary_keys']
        if not primary_keys:
            print(f"  Warning: No primary key found for {table_name}")
            return
        
        merge_key = primary_keys[0]  # Use first PK for merging
        
        # Create nodes in batches
        with self.neo4j_driver.session() as session:
            records_migrated = 0
            
            for batch_start in range(0, len(df), self.batch_size):
                batch_df = df.iloc[batch_start:batch_start + self.batch_size]
                
                for _, row in batch_df.iterrows():
                    # Build properties dict
                    properties = {}
                    for source_col, target_prop in property_mappings.items():
                        if source_col in row and pd.notna(row[source_col]):
                            value = row[source_col]
                            # Convert numpy types to Python types
                            if hasattr(value, 'item'):
                                value = value.item()
                            properties[target_prop] = value
                    
                    # Add primary key for merge
                    if merge_key in row:
                        merge_value = row[merge_key]
                        if hasattr(merge_value, 'item'):
                            merge_value = merge_value.item()
                        
                        # Create/merge node
                        query = f"""
                        MERGE (n:{node_label} {{{merge_key}: $merge_value}})
                        SET n += $properties
                        """
                        
                        session.run(query, {
                            'merge_value': merge_value,
                            'properties': properties
                        })
                        
                        records_migrated += 1
                
                print(f"    Migrated {records_migrated}/{len(df)} records")
        
        print(f"  ✓ Successfully migrated {records_migrated} nodes for {table_name}")
    
    def migrate_relationships(self, table_name, table_info):
        """
        Create relationships based on foreign keys
        
        Args:
            table_name: Name of the table
            table_info: Table metadata and mapping
        """
        mapping = table_info['mapping']
        relationships = mapping.get('relationships', [])
        
        if not relationships:
            return
        
        print(f"\nCreating relationships for: {table_name}")
        
        # Extract data
        df = self.extract_table_data(table_name)
        
        if df.empty:
            return
        
        node_label = mapping['node_label']
        primary_key = table_info['primary_keys'][0] if table_info['primary_keys'] else None
        
        with self.neo4j_driver.session() as session:
            for rel in relationships:
                if rel['type'] != 'foreign_key':
                    continue
                
                rel_type = rel['relationship_type']
                source_col = rel['source_column']
                target_node = rel['target_node']
                target_col = rel['target_column']
                
                print(f"  Creating {rel_type} relationships...")
                
                relationships_created = 0
                
                for _, row in df.iterrows():
                    if pd.notna(row[source_col]) and pd.notna(row[primary_key]):
                        source_val = row[primary_key]
                        target_val = row[source_col]
                        
                        # Convert numpy types
                        if hasattr(source_val, 'item'):
                            source_val = source_val.item()
                        if hasattr(target_val, 'item'):
                            target_val = target_val.item()
                        
                        query = f"""
                        MATCH (source:{node_label} {{{primary_key}: $source_val}})
                        MATCH (target:{target_node} {{{target_col}: $target_val}})
                        MERGE (source)-[r:{rel_type}]->(target)
                        """
                        
                        session.run(query, {
                            'source_val': source_val,
                            'target_val': target_val
                        })
                        
                        relationships_created += 1
                
                print(f"    ✓ Created {relationships_created} {rel_type} relationships")
    
    def migrate_junction_table(self, table_name, table_info):
        """
        Migrate junction table as relationships between entities
        
        Args:
            table_name: Name of the junction table
            table_info: Table metadata and mapping
        """
        print(f"\nMigrating junction table: {table_name}")
        
        mapping = table_info['mapping']
        relationships = mapping.get('relationships', [])
        
        if not relationships or relationships[0]['type'] != 'many_to_many':
            print(f"  Skipping: Not configured as many-to-many")
            return
        
        rel_config = relationships[0]
        from_table = rel_config['from_table']
        from_col = rel_config['from_column']
        to_table = rel_config['to_table']
        to_col = rel_config['to_column']
        rel_type = rel_config['relationship_type']
        
        # Extract data
        df = self.extract_table_data(table_name)
        
        if df.empty:
            print(f"  No relationships to create")
            return
        
        # Get any additional properties (non-FK columns)
        fk_columns = {from_col, to_col}
        property_columns = [col for col in df.columns if col not in fk_columns]
        
        with self.neo4j_driver.session() as session:
            relationships_created = 0
            
            for _, row in df.iterrows():
                if pd.notna(row[from_col]) and pd.notna(row[to_col]):
                    from_val = row[from_col]
                    to_val = row[to_col]
                    
                    if hasattr(from_val, 'item'):
                        from_val = from_val.item()
                    if hasattr(to_val, 'item'):
                        to_val = to_val.item()
                    
                    # Build relationship properties
                    rel_props = {}
                    for prop_col in property_columns:
                        if pd.notna(row[prop_col]):
                            val = row[prop_col]
                            if hasattr(val, 'item'):
                                val = val.item()
                            rel_props[prop_col] = val
                    
                    # Create relationship
                    query = f"""
                    MATCH (from:{from_table} {{{from_table.lower()}_id: $from_val}})
                    MATCH (to:{to_table} {{{to_table.lower()}_id: $to_val}})
                    MERGE (from)-[r:{rel_type}]->(to)
                    SET r += $properties
                    """
                    
                    # Try with actual PK column names from the referenced tables
                    # This is a simplified version - in production, we'd get actual PK names
                    alt_query = f"""
                    MATCH (from:{from_table})
                    WHERE from.{from_col.replace('_id', '')} = $from_val 
                       OR from.{from_col} = $from_val
                    MATCH (to:{to_table})
                    WHERE to.{to_col.replace('_id', '')} = $to_val
                       OR to.{to_col} = $to_val
                    MERGE (from)-[r:{rel_type}]->(to)
                    SET r += $properties
                    """
                    
                    try:
                        session.run(alt_query, {
                            'from_val': from_val,
                            'to_val': to_val,
                            'properties': rel_props
                        })
                        relationships_created += 1
                    except Exception as e:
                        print(f"    Warning: Could not create relationship: {e}")
            
            print(f"  ✓ Created {relationships_created} {rel_type} relationships")
    
    def migrate_all(self, clear_db=False):
        """
        Execute complete migration pipeline
        
        Args:
            clear_db: Whether to clear Neo4j database before migration
        """
        print("\n" + "=" * 60)
        print("Phase 3: ETL Pipeline - Data Migration")
        print("=" * 60)
        
        try:
            # Load mapping and connect
            self.load_mapping()
            self.connect_databases()
            
            # Optionally clear database
            if clear_db:
                self.neo4j_conn.clear_database()
            
            # Create constraints
            self.create_constraints()
            
            # First pass: Migrate entity tables (nodes)
            print("\n--- Migrating Entity Tables (Nodes) ---")
            for table_name, table_info in self.mapping['tables'].items():
                mapping = table_info['mapping']
                
                # Skip junction tables in first pass
                if mapping.get('dissolve_to_relationship'):
                    continue
                
                self.migrate_entity_table(table_name, table_info)
            
            # Second pass: Create relationships from foreign keys
            print("\n--- Creating Relationships from Foreign Keys ---")
            for table_name, table_info in self.mapping['tables'].items():
                mapping = table_info['mapping']
                
                if mapping.get('dissolve_to_relationship'):
                    continue
                
                self.migrate_relationships(table_name, table_info)
            
            # Third pass: Migrate junction tables
            print("\n--- Migrating Junction Tables (Many-to-Many) ---")
            for table_name, table_info in self.mapping['tables'].items():
                mapping = table_info['mapping']
                
                if mapping.get('dissolve_to_relationship'):
                    self.migrate_junction_table(table_name, table_info)
            
            print("\n" + "=" * 60)
            print("Migration completed successfully!")
            print("=" * 60)
            
        except Exception as e:
            print(f"\nError during migration: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            self.disconnect_databases()


def main():
    """
    Main function to run data loading
    """
    import sys
    
    mapping_file = None
    database_name = None
    clear_db = False
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        mapping_file = sys.argv[1]
    if len(sys.argv) > 2:
        database_name = sys.argv[2]
    if '--clear' in sys.argv:
        clear_db = True
    
    loader = DataLoader(mapping_file, database_name)
    loader.migrate_all(clear_db=clear_db)


if __name__ == "__main__":
    main()
