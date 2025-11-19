"""
SQL Server Connector

SQL Server-specific implementation of database connector.
"""

import pyodbc
from typing import List, Dict, Any, Optional
from .rdbms_connector import RDBMSConnector


class SQLServerConnector(RDBMSConnector):
    """SQL Server database connector."""
    
    def __init__(self, host: str, port: int, database: str, 
                 username: str, password: str, driver: str = "ODBC Driver 17 for SQL Server"):
        """
        Initialize SQL Server connector.
        
        Args:
            host: Database host
            port: Database port
            database: Database name
            username: Database username
            password: Database password
            driver: ODBC driver name
        """
        super().__init__(host, port, database, username, password)
        self.driver = driver
    
    def connect(self) -> None:
        """Establish SQL Server connection."""
        try:
            connection_string = (
                f"DRIVER={{{self.driver}}};"
                f"SERVER={self.host},{self.port};"
                f"DATABASE={self.database};"
                f"UID={self.username};"
                f"PWD={self.password}"
            )
            self.connection = pyodbc.connect(connection_string)
            self.cursor = self.connection.cursor()
            self.logger.info(f"Connected to SQL Server database: {self.database}")
        except Exception as e:
            self.logger.error(f"Failed to connect to SQL Server: {e}")
            raise
    
    def disconnect(self) -> None:
        """Close SQL Server connection."""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        self.logger.info("Disconnected from SQL Server")
    
    def test_connection(self) -> bool:
        """Test SQL Server connection."""
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
        """Get list of tables in SQL Server database."""
        schema_name = schema or 'dbo'
        query = """
            SELECT TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = ?
            AND TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
        """
        results = self.execute_query(query, (schema_name,))
        return [row['TABLE_NAME'] for row in results]
    
    def get_table_columns(self, table_name: str, 
                         schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get columns for a SQL Server table."""
        schema_name = schema or 'dbo'
        query = """
            SELECT 
                c.COLUMN_NAME,
                c.DATA_TYPE,
                c.IS_NULLABLE,
                c.CHARACTER_MAXIMUM_LENGTH,
                c.NUMERIC_PRECISION,
                c.NUMERIC_SCALE,
                c.COLUMN_DEFAULT,
                c.ORDINAL_POSITION,
                COLUMNPROPERTY(OBJECT_ID(c.TABLE_SCHEMA + '.' + c.TABLE_NAME), 
                    c.COLUMN_NAME, 'IsIdentity') AS IS_IDENTITY
            FROM INFORMATION_SCHEMA.COLUMNS c
            WHERE c.TABLE_SCHEMA = ?
            AND c.TABLE_NAME = ?
            ORDER BY c.ORDINAL_POSITION
        """
        results = self.execute_query(query, (schema_name, table_name))
        
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
                'is_auto_increment': bool(row['IS_IDENTITY']),
                'ordinal_position': row['ORDINAL_POSITION']
            })
        
        return columns
    
    def get_primary_key(self, table_name: str, 
                       schema: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get primary key for a SQL Server table."""
        schema_name = schema or 'dbo'
        query = """
            SELECT 
                kcu.CONSTRAINT_NAME,
                kcu.COLUMN_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
            JOIN INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
                ON kcu.CONSTRAINT_NAME = tc.CONSTRAINT_NAME
                AND kcu.TABLE_SCHEMA = tc.TABLE_SCHEMA
            WHERE tc.TABLE_SCHEMA = ?
            AND tc.TABLE_NAME = ?
            AND tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
            ORDER BY kcu.ORDINAL_POSITION
        """
        results = self.execute_query(query, (schema_name, table_name))
        
        if not results:
            return None
        
        return {
            'name': results[0]['CONSTRAINT_NAME'],
            'columns': [row['COLUMN_NAME'] for row in results]
        }
    
    def get_foreign_keys(self, table_name: str, 
                        schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get foreign keys for a SQL Server table."""
        schema_name = schema or 'dbo'
        query = """
            SELECT 
                fk.name AS CONSTRAINT_NAME,
                c1.name AS COLUMN_NAME,
                t2.name AS REFERENCED_TABLE,
                c2.name AS REFERENCED_COLUMN,
                fk.update_referential_action_desc AS UPDATE_RULE,
                fk.delete_referential_action_desc AS DELETE_RULE
            FROM sys.foreign_keys fk
            JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
            JOIN sys.tables t1 ON fk.parent_object_id = t1.object_id
            JOIN sys.schemas s1 ON t1.schema_id = s1.schema_id
            JOIN sys.columns c1 ON fkc.parent_object_id = c1.object_id 
                AND fkc.parent_column_id = c1.column_id
            JOIN sys.tables t2 ON fk.referenced_object_id = t2.object_id
            JOIN sys.columns c2 ON fkc.referenced_object_id = c2.object_id 
                AND fkc.referenced_column_id = c2.column_id
            WHERE s1.name = ?
            AND t1.name = ?
        """
        results = self.execute_query(query, (schema_name, table_name))
        
        foreign_keys = []
        for row in results:
            foreign_keys.append({
                'name': row['CONSTRAINT_NAME'],
                'column': row['COLUMN_NAME'],
                'referenced_table': row['REFERENCED_TABLE'],
                'referenced_column': row['REFERENCED_COLUMN'],
                'on_update': row['UPDATE_RULE'],
                'on_delete': row['DELETE_RULE']
            })
        
        return foreign_keys
    
    def get_indexes(self, table_name: str, 
                   schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get indexes for a SQL Server table."""
        schema_name = schema or 'dbo'
        query = """
            SELECT 
                i.name AS INDEX_NAME,
                c.name AS COLUMN_NAME,
                i.is_unique AS IS_UNIQUE
            FROM sys.indexes i
            JOIN sys.index_columns ic ON i.object_id = ic.object_id 
                AND i.index_id = ic.index_id
            JOIN sys.columns c ON ic.object_id = c.object_id 
                AND ic.column_id = c.column_id
            JOIN sys.tables t ON i.object_id = t.object_id
            JOIN sys.schemas s ON t.schema_id = s.schema_id
            WHERE s.name = ?
            AND t.name = ?
            AND i.is_primary_key = 0
            ORDER BY i.name, ic.key_ordinal
        """
        results = self.execute_query(query, (schema_name, table_name))
        
        # Group by index name
        indexes_dict = {}
        for row in results:
            index_name = row['INDEX_NAME']
            if index_name and index_name not in indexes_dict:
                indexes_dict[index_name] = {
                    'name': index_name,
                    'columns': [],
                    'is_unique': bool(row['IS_UNIQUE'])
                }
            if index_name:
                indexes_dict[index_name]['columns'].append(row['COLUMN_NAME'])
        
        return list(indexes_dict.values())
    
    def get_row_count(self, table_name: str, 
                     schema: Optional[str] = None) -> int:
        """Get row count for a SQL Server table."""
        schema_name = schema or 'dbo'
        query = f"SELECT COUNT(*) as count FROM [{schema_name}].[{table_name}]"
        result = self.execute_query(query)
        return result[0]['count'] if result else 0
    
    def fetch_data(self, table_name: str, batch_size: int = 1000,
                  offset: int = 0, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch data from a SQL Server table in batches."""
        schema_name = schema or 'dbo'
        # SQL Server uses OFFSET/FETCH for pagination
        query = f"""
            SELECT * FROM [{schema_name}].[{table_name}]
            ORDER BY (SELECT NULL)
            OFFSET ? ROWS
            FETCH NEXT ? ROWS ONLY
        """
        return self.execute_query(query, (offset, batch_size))
