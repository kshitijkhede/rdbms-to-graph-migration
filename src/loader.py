"""
Phase 3: ETL Pipeline / Loader
Reads mapping.json, extracts data from MySQL, transforms it, and loads into Neo4j
WITH ENRICHMENT RULE SUPPORT for SCT migration
"""
import json
import mysql.connector
import pandas as pd
from neo4j import GraphDatabase
from config.config import MYSQL_CONFIG, NEO4J_CONFIG, MIGRATION_SETTINGS, MAPPING_FILE_PATH
from src.neo4j_connection import Neo4jConnection
from src.enrichment_rules import (
    ENRICHMENT_NONE,
    ENRICHMENT_MERGE_ON_LABEL,
    ENRICHMENT_REL_FROM_JUNCTION,
    REL_TYPE_FOREIGN_KEY,
    REL_TYPE_MANY_TO_MANY
)


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
                
                # Handle composite keys vs single keys differently
                if len(primary_keys) > 1:
                    # For composite keys, create a NODE KEY constraint (Neo4j Enterprise)
                    # or skip constraint creation (Neo4j Community doesn't support composite NODE KEY)
                    constraint_name = f"{node_label}_composite_key"
                    try:
                        # Try to create NODE KEY constraint (Enterprise feature)
                        pk_list = ', '.join([f"n.{pk}" for pk in primary_keys])
                        query = f"""
                        CREATE CONSTRAINT {constraint_name} IF NOT EXISTS
                        FOR (n:{node_label})
                        REQUIRE ({pk_list}) IS NODE KEY
                        """
                        session.run(query)
                        print(f"  Created composite key constraint: {constraint_name}")
                    except Exception as e:
                        # NODE KEY not supported in Community Edition, skip constraint
                        print(f"  Note: Composite key constraint not supported (Community Edition)")
                        print(f"        Table {node_label} uses composite key: {primary_keys}")
                else:
                    # Single primary key - create unique constraint
                    pk = primary_keys[0]
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
    
    def get_node_cypher_query(self, node_mapping, primary_keys):
        """
        Generate appropriate Cypher query based on enrichment rule.
        This is the "brain" of the SCT engine - dynamically generates
        different Cypher based on semantic patterns.
        
        Args:
            node_mapping: Mapping configuration for the node
            primary_keys: List of primary key columns
            
        Returns:
            tuple: (cypher_query, is_enriched)
        """
        rule = node_mapping.get('enrichment_rule', ENRICHMENT_NONE)
        
        if rule == ENRICHMENT_MERGE_ON_LABEL:
            # ENRICHED CTI RULE: Add label to existing node
            # Instead of creating separate Person and Student nodes,
            # find the existing :Person node and add :Student label
            merge_label = node_mapping['merge_on_label']
            merge_key_prop = node_mapping['merge_key_property']
            target_label = node_mapping['target_label']
            
            print(f"    → Using ENRICHMENT: {ENRICHMENT_MERGE_ON_LABEL}")
            print(f"    → Will add label '{target_label}' to existing '{merge_label}' nodes")
            
            # This query finds the existing :Person node and adds :Student label + properties
            cypher = f"""
            MATCH (n:{merge_label} {{{merge_key_prop}: $pk_val}})
            SET n:{target_label}, n += $props
            RETURN n
            """
            return cypher, True
        
        else:
            # STANDARD RULE: Create or update node normally
            node_label = node_mapping['node_label']
            
            # Handle composite primary keys
            if len(primary_keys) > 1:
                # Build merge pattern for composite keys: {pk1: $pk1, pk2: $pk2}
                merge_keys = ', '.join([f"{pk}: ${pk}" for pk in primary_keys])
                cypher = f"""
                MERGE (n:{node_label} {{{merge_keys}}})
                ON CREATE SET n += $props
                ON MATCH SET n += $props
                RETURN n
                """
            else:
                # Single primary key
                pk_col = primary_keys[0] if primary_keys else 'id'
                cypher = f"""
                MERGE (n:{node_label} {{{pk_col}: $pk_val}})
                ON CREATE SET n += $props
                ON MATCH SET n += $props
                RETURN n
                """
            return cypher, False
    
    def migrate_entity_table(self, table_name, table_info):
        """
        Migrate an entity table to Neo4j nodes WITH ENRICHMENT SUPPORT
        
        Args:
            table_name: Name of the table
            table_info: Table metadata and mapping
        """
        print(f"\nMigrating entity table: {table_name}")
        
        mapping = table_info['mapping']
        primary_keys = table_info['primary_keys']
        
        # Check if this is an enriched inheritance mapping
        is_inheritance = mapping.get('enrichment_rule') == ENRICHMENT_MERGE_ON_LABEL
        if is_inheritance:
            print(f"  → ENRICHMENT: Adding label '{mapping['target_label']}' to existing '{mapping['merge_on_label']}' nodes")
        
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
        
        # Get primary key
        if not primary_keys:
            print(f"  Warning: No primary key found for {table_name}")
            return
        
        # Generate dynamic Cypher based on enrichment rule
        cypher, is_enriched = self.get_node_cypher_query(mapping, primary_keys)
        
        # Determine if we have composite keys
        has_composite_keys = len(primary_keys) > 1
        
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
                    
                    try:
                        # Handle composite vs single primary keys
                        if has_composite_keys:
                            # Build parameter dict for composite keys
                            pk_params = {}
                            for pk in primary_keys:
                                if pk in row:
                                    pk_val = row[pk]
                                    if hasattr(pk_val, 'item'):
                                        pk_val = pk_val.item()
                                    pk_params[pk] = pk_val
                            # Merge pk_params with properties for the query
                            session.run(cypher, **pk_params, props=properties)
                        else:
                            # Single primary key - use old logic
                            pk_col = primary_keys[0]
                            if pk_col in row:
                                pk_val = row[pk_col]
                                if hasattr(pk_val, 'item'):
                                    pk_val = pk_val.item()
                                session.run(cypher, pk_val=pk_val, props=properties)
                        
                        records_migrated += 1
                    except Exception as e:
                        print(f"    Error loading node: {e}")
                
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
        Migrate junction table as relationships between entities WITH PROPERTIES
        This implements the ENRICHMENT_REL_FROM_JUNCTION rule
        
        Args:
            table_name: Name of the junction table
            table_info: Table metadata and mapping
        """
        print(f"\nMigrating junction table: {table_name}")
        
        mapping = table_info['mapping']
        enrichment_rule = mapping.get('enrichment_rule')
        
        if enrichment_rule == ENRICHMENT_REL_FROM_JUNCTION:
            print(f"  → ENRICHMENT: Dissolving junction table into relationships with properties")
        
        relationships = mapping.get('relationships', [])
        
        if not relationships or relationships[0]['type'] != REL_TYPE_MANY_TO_MANY:
            print(f"  Skipping: Not configured as many-to-many")
            return
        
        rel_config = relationships[0]
        from_table = rel_config['from_table']
        from_col = rel_config['from_column']
        from_key = rel_config.get('from_key', from_col)
        to_table = rel_config['to_table']
        to_col = rel_config['to_column']
        to_key = rel_config.get('to_key', to_col)
        rel_type = rel_config['relationship_type']
        
        # Get relationship property mappings
        rel_properties = rel_config.get('properties', [])
        
        # Extract data
        df = self.extract_table_data(table_name)
        
        if df.empty:
            print(f"  No relationships to create")
            return
        
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
                    
                    # Build relationship properties from junction table columns
                    rel_props = {}
                    for prop_mapping in rel_properties:
                        source_col = prop_mapping['source_column']
                        target_prop = prop_mapping['target_property']
                        if source_col in row and pd.notna(row[source_col]):
                            val = row[source_col]
                            if hasattr(val, 'item'):
                                val = val.item()
                            rel_props[target_prop] = val
                    
                    # Create relationship with properties
                    query = f"""
                    MATCH (from:{from_table} {{{from_key}: $from_val}})
                    MATCH (to:{to_table} {{{to_key}: $to_val}})
                    MERGE (from)-[r:{rel_type}]->(to)
                    SET r += $properties
                    """
                    
                    try:
                        session.run(query, {
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
