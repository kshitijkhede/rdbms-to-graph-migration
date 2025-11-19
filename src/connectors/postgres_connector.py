"""
PostgreSQL Connector

PostgreSQL-specific implementation of database connector.
"""

import psycopg2
import psycopg2.extras
from typing import List, Dict, Any, Optional
from .rdbms_connector import RDBMSConnector


class PostgreSQLConnector(RDBMSConnector):
    """PostgreSQL database connector."""
    
    def connect(self) -> None:
        """Establish PostgreSQL connection."""
        try:
            self.connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.username,
                password=self.password
            )
            self.cursor = self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            self.logger.info(f"Connected to PostgreSQL database: {self.database}")
        except Exception as e:
            self.logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise
    
    def disconnect(self) -> None:
        """Close PostgreSQL connection."""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        self.logger.info("Disconnected from PostgreSQL")
    
    def test_connection(self) -> bool:
        """Test PostgreSQL connection."""
        try:
            self.connect()
            self.cursor.execute("SELECT 1")
            result = self.cursor.fetchone()
            self.disconnect()
            return result[0] == 1
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False
    
    def get_tables(self, schema: Optional[str] = None) -> List[str]:
        """Get list of tables in PostgreSQL database."""
        schema_name = schema or 'public'
        query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = %s
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """
        results = self.execute_query(query, (schema_name,))
        return [row['table_name'] for row in results]
    
    def get_table_columns(self, table_name: str, 
                         schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get columns for a PostgreSQL table."""
        schema_name = schema or 'public'
        query = """
            SELECT 
                column_name,
                data_type,
                is_nullable,
                character_maximum_length,
                numeric_precision,
                numeric_scale,
                column_default,
                ordinal_position
            FROM information_schema.columns
            WHERE table_schema = %s
            AND table_name = %s
            ORDER BY ordinal_position
        """
        results = self.execute_query(query, (schema_name, table_name))
        
        columns = []
        for row in results:
            is_auto_increment = False
            if row['column_default']:
                is_auto_increment = 'nextval' in str(row['column_default']).lower()
            
            columns.append({
                'name': row['column_name'],
                'data_type': row['data_type'],
                'is_nullable': row['is_nullable'] == 'YES',
                'max_length': row['character_maximum_length'],
                'precision': row['numeric_precision'],
                'scale': row['numeric_scale'],
                'default_value': row['column_default'],
                'is_auto_increment': is_auto_increment,
                'ordinal_position': row['ordinal_position']
            })
        
        return columns
    
    def get_primary_key(self, table_name: str, 
                       schema: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get primary key for a PostgreSQL table."""
        schema_name = schema or 'public'
        query = """
            SELECT 
                tc.constraint_name,
                kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            WHERE tc.table_schema = %s
            AND tc.table_name = %s
            AND tc.constraint_type = 'PRIMARY KEY'
            ORDER BY kcu.ordinal_position
        """
        results = self.execute_query(query, (schema_name, table_name))
        
        if not results:
            return None
        
        return {
            'name': results[0]['constraint_name'],
            'columns': [row['column_name'] for row in results]
        }
    
    def get_foreign_keys(self, table_name: str, 
                        schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get foreign keys for a PostgreSQL table."""
        schema_name = schema or 'public'
        query = """
            SELECT 
                tc.constraint_name,
                kcu.column_name,
                ccu.table_name AS referenced_table,
                ccu.column_name AS referenced_column,
                rc.update_rule,
                rc.delete_rule
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            JOIN information_schema.referential_constraints rc
                ON rc.constraint_name = tc.constraint_name
                AND rc.constraint_schema = tc.table_schema
            WHERE tc.table_schema = %s
            AND tc.table_name = %s
            AND tc.constraint_type = 'FOREIGN KEY'
        """
        results = self.execute_query(query, (schema_name, table_name))
        
        foreign_keys = []
        for row in results:
            foreign_keys.append({
                'name': row['constraint_name'],
                'column': row['column_name'],
                'referenced_table': row['referenced_table'],
                'referenced_column': row['referenced_column'],
                'on_update': row['update_rule'],
                'on_delete': row['delete_rule']
            })
        
        return foreign_keys
    
    def get_indexes(self, table_name: str, 
                   schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get indexes for a PostgreSQL table."""
        schema_name = schema or 'public'
        query = """
            SELECT
                i.relname AS index_name,
                a.attname AS column_name,
                ix.indisunique AS is_unique
            FROM pg_class t
            JOIN pg_index ix ON t.oid = ix.indrelid
            JOIN pg_class i ON i.oid = ix.indexrelid
            JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
            JOIN pg_namespace n ON n.oid = t.relnamespace
            WHERE t.relname = %s
            AND n.nspname = %s
            AND ix.indisprimary = false
            ORDER BY i.relname, a.attnum
        """
        results = self.execute_query(query, (table_name, schema_name))
        
        # Group by index name
        indexes_dict = {}
        for row in results:
            index_name = row['index_name']
            if index_name not in indexes_dict:
                indexes_dict[index_name] = {
                    'name': index_name,
                    'columns': [],
                    'is_unique': row['is_unique']
                }
            indexes_dict[index_name]['columns'].append(row['column_name'])
        
        return list(indexes_dict.values())
    
    def get_row_count(self, table_name: str, 
                     schema: Optional[str] = None) -> int:
        """Get row count for a PostgreSQL table."""
        schema_name = schema or 'public'
        query = f'SELECT COUNT(*) as count FROM "{schema_name}"."{table_name}"'
        result = self.execute_query(query)
        return result[0]['count'] if result else 0
    
    def fetch_data(self, table_name: str, batch_size: int = 1000,
                  offset: int = 0, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch data from a PostgreSQL table in batches."""
        schema_name = schema or 'public'
        query = f'SELECT * FROM "{schema_name}"."{table_name}" LIMIT %s OFFSET %s'
        results = self.execute_query(query, (batch_size, offset))
        # Convert RealDictRow to dict
        return [dict(row) for row in results]
