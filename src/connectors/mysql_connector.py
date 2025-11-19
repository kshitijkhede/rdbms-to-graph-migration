"""
MySQL Connector

MySQL-specific implementation of database connector.
"""

import mysql.connector
from typing import List, Dict, Any, Optional
from .rdbms_connector import RDBMSConnector


class MySQLConnector(RDBMSConnector):
    """MySQL database connector."""
    
    def connect(self) -> None:
        """Establish MySQL connection."""
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.username,
                password=self.password
            )
            self.cursor = self.connection.cursor()
            self.logger.info(f"Connected to MySQL database: {self.database}")
        except Exception as e:
            self.logger.error(f"Failed to connect to MySQL: {e}")
            raise
    
    def disconnect(self) -> None:
        """Close MySQL connection."""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        self.logger.info("Disconnected from MySQL")
    
    def test_connection(self) -> bool:
        """Test MySQL connection."""
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
        """Get list of tables in MySQL database."""
        db = schema or self.database
        query = """
            SELECT TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = %s
            AND TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
        """
        results = self.execute_query(query, (db,))
        return [row['TABLE_NAME'] for row in results]
    
    def get_table_columns(self, table_name: str, 
                         schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get columns for a MySQL table."""
        db = schema or self.database
        query = """
            SELECT 
                COLUMN_NAME,
                DATA_TYPE,
                IS_NULLABLE,
                CHARACTER_MAXIMUM_LENGTH,
                NUMERIC_PRECISION,
                NUMERIC_SCALE,
                COLUMN_DEFAULT,
                EXTRA,
                ORDINAL_POSITION
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s
            AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
        """
        results = self.execute_query(query, (db, table_name))
        
        columns = []
        for row in results:
            columns.append({
                'name': row['COLUMN_NAME'],
                'data_type': row['DATA_TYPE'],
                'is_nullable': row['IS_NULLABLE'] == 'YES',
                'max_length': row['CHARACTER_MAXIMUM_LENGTH'],
                'precision': row['NUMERIC_PRECISION'],
                'scale': row['NUMERIC_SCALE'],
                'default_value': row['COLUMN_DEFAULT'],
                'is_auto_increment': 'auto_increment' in (row['EXTRA'] or '').lower(),
                'ordinal_position': row['ORDINAL_POSITION']
            })
        
        return columns
    
    def get_primary_key(self, table_name: str, 
                       schema: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get primary key for a MySQL table."""
        db = schema or self.database
        query = """
            SELECT 
                CONSTRAINT_NAME,
                COLUMN_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = %s
            AND TABLE_NAME = %s
            AND CONSTRAINT_NAME = 'PRIMARY'
            ORDER BY ORDINAL_POSITION
        """
        results = self.execute_query(query, (db, table_name))
        
        if not results:
            return None
        
        return {
            'name': 'PRIMARY',
            'columns': [row['COLUMN_NAME'] for row in results]
        }
    
    def get_foreign_keys(self, table_name: str, 
                        schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get foreign keys for a MySQL table."""
        db = schema or self.database
        query = """
            SELECT 
                kcu.CONSTRAINT_NAME,
                kcu.COLUMN_NAME,
                kcu.REFERENCED_TABLE_NAME,
                kcu.REFERENCED_COLUMN_NAME,
                rc.UPDATE_RULE,
                rc.DELETE_RULE
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
            JOIN INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS rc
                ON kcu.CONSTRAINT_NAME = rc.CONSTRAINT_NAME
                AND kcu.TABLE_SCHEMA = rc.CONSTRAINT_SCHEMA
            WHERE kcu.TABLE_SCHEMA = %s
            AND kcu.TABLE_NAME = %s
            AND kcu.REFERENCED_TABLE_NAME IS NOT NULL
        """
        results = self.execute_query(query, (db, table_name))
        
        foreign_keys = []
        for row in results:
            foreign_keys.append({
                'name': row['CONSTRAINT_NAME'],
                'column': row['COLUMN_NAME'],
                'referenced_table': row['REFERENCED_TABLE_NAME'],
                'referenced_column': row['REFERENCED_COLUMN_NAME'],
                'on_update': row['UPDATE_RULE'],
                'on_delete': row['DELETE_RULE']
            })
        
        return foreign_keys
    
    def get_indexes(self, table_name: str, 
                   schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get indexes for a MySQL table."""
        db = schema or self.database
        query = """
            SELECT 
                INDEX_NAME,
                COLUMN_NAME,
                NON_UNIQUE
            FROM INFORMATION_SCHEMA.STATISTICS
            WHERE TABLE_SCHEMA = %s
            AND TABLE_NAME = %s
            AND INDEX_NAME != 'PRIMARY'
            ORDER BY INDEX_NAME, SEQ_IN_INDEX
        """
        results = self.execute_query(query, (db, table_name))
        
        # Group by index name
        indexes_dict = {}
        for row in results:
            index_name = row['INDEX_NAME']
            if index_name not in indexes_dict:
                indexes_dict[index_name] = {
                    'name': index_name,
                    'columns': [],
                    'is_unique': row['NON_UNIQUE'] == 0
                }
            indexes_dict[index_name]['columns'].append(row['COLUMN_NAME'])
        
        return list(indexes_dict.values())
    
    def get_row_count(self, table_name: str, 
                     schema: Optional[str] = None) -> int:
        """Get row count for a MySQL table."""
        db = schema or self.database
        query = f"SELECT COUNT(*) as count FROM `{db}`.`{table_name}`"
        result = self.execute_query(query)
        return result[0]['count'] if result else 0
    
    def fetch_data(self, table_name: str, batch_size: int = 1000,
                  offset: int = 0, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch data from a MySQL table in batches."""
        db = schema or self.database
        query = f"SELECT * FROM `{db}`.`{table_name}` LIMIT %s OFFSET %s"
        return self.execute_query(query, (batch_size, offset))
