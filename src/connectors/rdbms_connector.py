"""
Base RDBMS Connector

Abstract base class for database connectors.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
import logging


class RDBMSConnector(ABC):
    """Abstract base class for RDBMS connectors."""
    
    def __init__(self, host: str, port: int, database: str, 
                 username: str, password: str):
        """
        Initialize RDBMS connector.
        
        Args:
            host: Database host
            port: Database port
            database: Database name
            username: Database username
            password: Database password
        """
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.connection = None
        self.cursor = None
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def connect(self) -> None:
        """Establish database connection."""
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Close database connection."""
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """
        Test database connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_tables(self, schema: Optional[str] = None) -> List[str]:
        """
        Get list of tables in the database.
        
        Args:
            schema: Optional schema name
            
        Returns:
            List of table names
        """
        pass
    
    @abstractmethod
    def get_table_columns(self, table_name: str, 
                         schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get columns for a table.
        
        Args:
            table_name: Name of the table
            schema: Optional schema name
            
        Returns:
            List of column information dictionaries
        """
        pass
    
    @abstractmethod
    def get_primary_key(self, table_name: str, 
                       schema: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get primary key for a table.
        
        Args:
            table_name: Name of the table
            schema: Optional schema name
            
        Returns:
            Primary key information or None
        """
        pass
    
    @abstractmethod
    def get_foreign_keys(self, table_name: str, 
                        schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get foreign keys for a table.
        
        Args:
            table_name: Name of the table
            schema: Optional schema name
            
        Returns:
            List of foreign key information
        """
        pass
    
    @abstractmethod
    def get_indexes(self, table_name: str, 
                   schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get indexes for a table.
        
        Args:
            table_name: Name of the table
            schema: Optional schema name
            
        Returns:
            List of index information
        """
        pass
    
    @abstractmethod
    def get_row_count(self, table_name: str, 
                     schema: Optional[str] = None) -> int:
        """
        Get row count for a table.
        
        Args:
            table_name: Name of the table
            schema: Optional schema name
            
        Returns:
            Number of rows
        """
        pass
    
    @abstractmethod
    def fetch_data(self, table_name: str, batch_size: int = 1000,
                  offset: int = 0, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch data from a table in batches.
        
        Args:
            table_name: Name of the table
            batch_size: Number of rows to fetch
            offset: Starting row offset
            schema: Optional schema name
            
        Returns:
            List of row dictionaries
        """
        pass
    
    def execute_query(self, query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """
        Execute a SQL query and return results.
        
        Args:
            query: SQL query string
            params: Optional query parameters
            
        Returns:
            List of result dictionaries
        """
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            
            # Get column names
            columns = [desc[0] for desc in self.cursor.description] if self.cursor.description else []
            
            # Fetch all results
            results = []
            for row in self.cursor.fetchall():
                results.append(dict(zip(columns, row)))
            
            return results
        except Exception as e:
            self.logger.error(f"Error executing query: {e}")
            self.logger.error(f"Query: {query}")
            raise
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
