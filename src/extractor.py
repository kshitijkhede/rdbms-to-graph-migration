"""
Phase 1: Metadata Extractor
Extracts schema information from MySQL database by interrogating information_schema
"""
import json
import mysql.connector
from config.config import MYSQL_CONFIG, MAPPING_FILE_PATH
from src.enrichment_rules import (
    ENRICHMENT_NONE,
    ENRICHMENT_MERGE_ON_LABEL,
    ENRICHMENT_REL_FROM_JUNCTION,
    REL_TYPE_FOREIGN_KEY,
    REL_TYPE_MANY_TO_MANY,
    REL_TYPE_INHERITANCE
)


class MetadataExtractor:
    """
    Extracts metadata from MySQL database schemas
    """
    
    def __init__(self, database_name=None):
        """
        Initialize the extractor
        
        Args:
            database_name: Name of the database to extract from
        """
        self.config = MYSQL_CONFIG.copy()
        if database_name:
            self.config['database'] = database_name
        self.connection = None
        self.cursor = None
    
    def connect(self):
        """
        Establish connection to MySQL database
        """
        try:
            self.connection = mysql.connector.connect(**self.config)
            self.cursor = self.connection.cursor(dictionary=True)
            print(f"Connected to MySQL database: {self.config['database']}")
        except mysql.connector.Error as e:
            print(f"Error connecting to MySQL: {e}")
            raise
    
    def disconnect(self):
        """
        Close database connection
        """
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
            print("Disconnected from MySQL database")
    
    def extract_tables(self):
        """
        Extract all table names from the database
        
        Returns:
            list: List of table names
        """
        query = """
            SELECT TABLE_NAME as table_name
            FROM information_schema.tables
            WHERE table_schema = %s AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """
        self.cursor.execute(query, (self.config['database'],))
        tables = [row['table_name'] for row in self.cursor.fetchall()]
        print(f"Found {len(tables)} tables: {tables}")
        return tables
    
    def extract_columns(self, table_name):
        """
        Extract column information for a specific table
        
        Args:
            table_name: Name of the table
            
        Returns:
            list: List of column dictionaries
        """
        query = """
            SELECT 
                COLUMN_NAME as column_name,
                DATA_TYPE as data_type,
                IS_NULLABLE as is_nullable,
                COLUMN_KEY as column_key,
                COLUMN_DEFAULT as column_default,
                EXTRA as extra
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
        """
        self.cursor.execute(query, (self.config['database'], table_name))
        columns = []
        for row in self.cursor.fetchall():
            columns.append({
                'name': row['column_name'],
                'type': row['data_type'],
                'nullable': row['is_nullable'] == 'YES',
                'key': row['column_key'],
                'default': row['column_default'],
                'extra': row['extra']
            })
        return columns
    
    def extract_primary_keys(self, table_name):
        """
        Extract primary key columns for a table
        
        Args:
            table_name: Name of the table
            
        Returns:
            list: List of primary key column names
        """
        query = """
            SELECT COLUMN_NAME as column_name
            FROM information_schema.key_column_usage
            WHERE table_schema = %s 
                AND table_name = %s 
                AND constraint_name = 'PRIMARY'
            ORDER BY ordinal_position
        """
        self.cursor.execute(query, (self.config['database'], table_name))
        return [row['column_name'] for row in self.cursor.fetchall()]
    
    def extract_foreign_keys(self, table_name):
        """
        Extract foreign key relationships for a table
        
        Args:
            table_name: Name of the table
            
        Returns:
            list: List of foreign key dictionaries
        """
        query = """
            SELECT 
                kcu.COLUMN_NAME as column_name,
                kcu.REFERENCED_TABLE_NAME as referenced_table_name,
                kcu.REFERENCED_COLUMN_NAME as referenced_column_name,
                kcu.CONSTRAINT_NAME as constraint_name
            FROM information_schema.key_column_usage kcu
            WHERE kcu.table_schema = %s 
                AND kcu.table_name = %s
                AND kcu.REFERENCED_TABLE_NAME IS NOT NULL
            ORDER BY kcu.ordinal_position
        """
        self.cursor.execute(query, (self.config['database'], table_name))
        foreign_keys = []
        for row in self.cursor.fetchall():
            foreign_keys.append({
                'column': row['column_name'],
                'references_table': row['referenced_table_name'],
                'references_column': row['referenced_column_name'],
                'constraint_name': row['constraint_name']
            })
        return foreign_keys
    
    def detect_junction_table(self, table_name, primary_keys, foreign_keys):
        """
        Detect if a table is a junction table (many-to-many relationship)
        
        A junction table typically has:
        - Composite primary key
        - All PK columns are also FKs
        - Minimal additional columns
        
        Args:
            table_name: Name of the table
            primary_keys: List of PK columns
            foreign_keys: List of FK dictionaries
            
        Returns:
            bool: True if table appears to be a junction table
        """
        if len(primary_keys) < 2:
            return False
        
        fk_columns = {fk['column'] for fk in foreign_keys}
        pk_set = set(primary_keys)
        
        # Check if all PKs are FKs
        return pk_set.issubset(fk_columns)
    
    def detect_inheritance_pattern(self, table_name, primary_keys, foreign_keys):
        """
        Detect if a table follows Class Table Inheritance pattern
        
        A CTI sub-type table has:
        - Single column PK that is also an FK to the parent table
        
        Args:
            table_name: Name of the table
            primary_keys: List of PK columns
            foreign_keys: List of FK dictionaries
            
        Returns:
            dict or None: Parent table info if inheritance detected
        """
        if len(primary_keys) != 1:
            return None
        
        pk_column = primary_keys[0]
        
        # Check if the PK is also an FK
        for fk in foreign_keys:
            if fk['column'] == pk_column:
                return {
                    'parent_table': fk['references_table'],
                    'parent_column': fk['references_column']
                }
        
        return None
    
    def extract_schema_metadata(self):
        """
        Extract complete schema metadata
        
        Returns:
            dict: Complete schema metadata
        """
        self.connect()
        
        try:
            tables = self.extract_tables()
            schema_metadata = {
                'database': self.config['database'],
                'tables': {}
            }
            
            for table_name in tables:
                print(f"\nAnalyzing table: {table_name}")
                
                columns = self.extract_columns(table_name)
                primary_keys = self.extract_primary_keys(table_name)
                foreign_keys = self.extract_foreign_keys(table_name)
                
                # Detect patterns
                is_junction = self.detect_junction_table(
                    table_name, primary_keys, foreign_keys
                )
                inheritance_info = self.detect_inheritance_pattern(
                    table_name, primary_keys, foreign_keys
                )
                
                table_info = {
                    'columns': columns,
                    'primary_keys': primary_keys,
                    'foreign_keys': foreign_keys,
                    'is_junction_table': is_junction,
                    'inheritance': inheritance_info,
                    'mapping': self._generate_default_mapping(
                        table_name, columns, primary_keys, 
                        foreign_keys, is_junction, inheritance_info
                    )
                }
                
                schema_metadata['tables'][table_name] = table_info
                
                print(f"  - Columns: {len(columns)}")
                print(f"  - Primary Keys: {primary_keys}")
                print(f"  - Foreign Keys: {len(foreign_keys)}")
                print(f"  - Junction Table: {is_junction}")
                print(f"  - Inheritance: {inheritance_info is not None}")
            
            return schema_metadata
        
        finally:
            self.disconnect()
    
    def _generate_default_mapping(self, table_name, columns, primary_keys, 
                                   foreign_keys, is_junction, inheritance_info):
        """
        Generate default mapping configuration WITH ENRICHMENT RULES
        
        Args:
            table_name: Name of the table
            columns: List of column dictionaries
            primary_keys: List of PK columns
            foreign_keys: List of FK dictionaries
            is_junction: Boolean indicating if table is a junction table
            inheritance_info: Dictionary with inheritance information
            
        Returns:
            dict: Default mapping configuration with enrichment rules
        """
        mapping = {
            'type': 'entity',  # Can be 'entity', 'junction', or 'inheritance'
            'node_label': table_name,
            'enrichment_rule': ENRICHMENT_NONE,  # Default: no enrichment
            'properties': [],
            'relationships': []
        }
        
        # Determine mapping type and enrichment rule
        if is_junction:
            mapping['type'] = 'junction'
            mapping['dissolve_to_relationship'] = True
            mapping['enrichment_rule'] = ENRICHMENT_REL_FROM_JUNCTION
            
        elif inheritance_info:
            mapping['type'] = 'inheritance'
            mapping['extends'] = inheritance_info['parent_table']
            mapping['enrichment_rule'] = ENRICHMENT_MERGE_ON_LABEL
            # Add enrichment-specific fields for CTI
            mapping['merge_on_label'] = inheritance_info['parent_table']
            mapping['merge_key_property'] = inheritance_info['parent_column']
            mapping['target_label'] = table_name
        
        # Map columns to properties (exclude technical PKs)
        fk_columns = {fk['column'] for fk in foreign_keys}
        for col in columns:
            col_name = col['name']
            # Skip auto-increment IDs and FK columns (they become relationships)
            if col['extra'] == 'auto_increment':
                continue
            if col_name in fk_columns and not is_junction:
                continue
            
            mapping['properties'].append({
                'source_column': col_name,
                'target_property': col_name,
                'type': col['type']
            })
        
        # Map foreign keys to relationships
        if not is_junction:
            for fk in foreign_keys:
                # Skip if this is an inheritance FK
                if (inheritance_info and 
                    fk['references_table'] == inheritance_info['parent_table']):
                    continue
                
                mapping['relationships'].append({
                    'type': REL_TYPE_FOREIGN_KEY,
                    'source_column': fk['column'],
                    'target_node': fk['references_table'],
                    'target_column': fk['references_column'],
                    'relationship_type': f"HAS_{fk['references_table'].upper()}"
                })
        else:
            # For junction tables, create relationship between the two entities
            if len(foreign_keys) >= 2:
                # Extract additional properties from junction table (e.g., quantity, price)
                junction_props = []
                fk_columns = {fk['column'] for fk in foreign_keys}
                for col in columns:
                    if col['name'] not in fk_columns and col['extra'] != 'auto_increment':
                        junction_props.append({
                            'source_column': col['name'],
                            'target_property': col['name'],
                            'type': col['type']
                        })
                
                mapping['relationships'] = [{
                    'type': REL_TYPE_MANY_TO_MANY,
                    'from_table': foreign_keys[0]['references_table'],
                    'from_column': foreign_keys[0]['column'],
                    'from_key': foreign_keys[0]['references_column'],
                    'to_table': foreign_keys[1]['references_table'],
                    'to_column': foreign_keys[1]['column'],
                    'to_key': foreign_keys[1]['references_column'],
                    'relationship_type': f"CONTAINS",
                    'properties': junction_props
                }]
        
        return mapping
    
    def save_mapping_file(self, metadata, output_path=None):
        """
        Save metadata to JSON mapping file
        
        Args:
            metadata: Schema metadata dictionary
            output_path: Path to save the file (default from config)
        """
        output_path = output_path or MAPPING_FILE_PATH
        
        with open(output_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"\nMapping file saved to: {output_path}")
        print("You can now manually enrich this file before running Phase 3 (ETL)")


def main():
    """
    Main function to run metadata extraction
    """
    import sys
    
    database_name = None
    if len(sys.argv) > 1:
        database_name = sys.argv[1]
    
    print("=" * 60)
    print("Phase 1: Metadata Extraction")
    print("=" * 60)
    
    extractor = MetadataExtractor(database_name)
    
    try:
        metadata = extractor.extract_schema_metadata()
        extractor.save_mapping_file(metadata)
        
        print("\n" + "=" * 60)
        print("Metadata extraction completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError during extraction: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
