"""
Data Extractor

Extracts data from RDBMS tables in batches for migration.
"""

import logging
from typing import List, Dict, Any, Iterator, Optional
from ..connectors.rdbms_connector import RDBMSConnector
from ..models.schema_model import Table
from tqdm import tqdm


class DataExtractor:
    """Extracts data from relational database tables."""
    
    def __init__(self, connector: RDBMSConnector, batch_size: int = 1000):
        """
        Initialize data extractor.
        
        Args:
            connector: Database connector instance
            batch_size: Number of rows to fetch per batch
        """
        self.connector = connector
        self.batch_size = batch_size
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def extract_table_data(self, table: Table, 
                          schema: Optional[str] = None,
                          show_progress: bool = True) -> Iterator[List[Dict[str, Any]]]:
        """
        Extract all data from a table in batches.
        
        Args:
            table: Table object
            schema: Optional schema name
            show_progress: Whether to show progress bar
            
        Yields:
            Batches of row data as dictionaries
        """
        self.logger.info(f"Extracting data from table: {table.name}")
        
        total_rows = table.row_count
        if total_rows == 0:
            self.logger.info(f"Table {table.name} is empty, skipping")
            return
        
        num_batches = (total_rows + self.batch_size - 1) // self.batch_size
        
        # Create progress bar if requested
        progress_bar = None
        if show_progress:
            progress_bar = tqdm(
                total=total_rows,
                desc=f"Extracting {table.name}",
                unit="rows"
            )
        
        try:
            offset = 0
            batch_num = 1
            
            while offset < total_rows:
                try:
                    # Fetch batch
                    batch_data = self.connector.fetch_data(
                        table.name,
                        batch_size=self.batch_size,
                        offset=offset,
                        schema=schema
                    )
                    
                    if not batch_data:
                        break
                    
                    # Update progress
                    if progress_bar:
                        progress_bar.update(len(batch_data))
                    
                    self.logger.debug(
                        f"Extracted batch {batch_num}/{num_batches} "
                        f"({len(batch_data)} rows) from {table.name}"
                    )
                    
                    yield batch_data
                    
                    offset += self.batch_size
                    batch_num += 1
                    
                except Exception as e:
                    self.logger.error(
                        f"Error extracting batch at offset {offset} "
                        f"from {table.name}: {e}"
                    )
                    raise
        
        finally:
            if progress_bar:
                progress_bar.close()
        
        self.logger.info(f"Completed extraction of {table.name}")
    
    def extract_single_batch(self, table_name: str, offset: int = 0,
                           schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Extract a single batch of data from a table.
        
        Args:
            table_name: Name of the table
            offset: Starting row offset
            schema: Optional schema name
            
        Returns:
            List of row dictionaries
        """
        return self.connector.fetch_data(
            table_name,
            batch_size=self.batch_size,
            offset=offset,
            schema=schema
        )
    
    def extract_by_primary_key(self, table: Table, start_id: Any, end_id: Any,
                              schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Extract data using primary key range (more efficient for large tables).
        
        Args:
            table: Table object
            start_id: Starting primary key value
            end_id: Ending primary key value
            schema: Optional schema name
            
        Returns:
            List of row dictionaries
        """
        if not table.primary_key or len(table.primary_key.columns) != 1:
            raise ValueError(f"Table {table.name} must have a single-column primary key")
        
        pk_column = table.primary_key.columns[0]
        schema_name = schema or table.schema
        
        query = f"""
            SELECT * FROM {schema_name}.{table.name}
            WHERE {pk_column} >= {start_id} AND {pk_column} < {end_id}
            ORDER BY {pk_column}
        """
        
        return self.connector.execute_query(query)
    
    def count_rows(self, table_name: str, schema: Optional[str] = None) -> int:
        """
        Get row count for a table.
        
        Args:
            table_name: Name of the table
            schema: Optional schema name
            
        Returns:
            Number of rows
        """
        return self.connector.get_row_count(table_name, schema)
