"""
Schema Analyzer

Analyzes RDBMS schema and extracts metadata about tables, columns,
relationships, and constraints.
"""

import logging
from typing import Dict, Any, Optional
from ..connectors.rdbms_connector import RDBMSConnector
from ..models.schema_model import (
    DatabaseSchema, Table, Column, PrimaryKey, 
    ForeignKey, Index, ColumnType
)
from ..utils.helpers import convert_sql_type_to_graph_type


class SchemaAnalyzer:
    """Analyzes database schema structure."""
    
    def __init__(self, connector: RDBMSConnector):
        """
        Initialize schema analyzer.
        
        Args:
            connector: Database connector instance
        """
        self.connector = connector
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def analyze(self, schema: Optional[str] = None) -> DatabaseSchema:
        """
        Analyze complete database schema.
        
        Args:
            schema: Optional schema name
            
        Returns:
            DatabaseSchema object
        """
        self.logger.info(f"Analyzing database schema: {self.connector.database}")
        
        db_schema = DatabaseSchema(
            database_name=self.connector.database,
            database_type=self.connector.__class__.__name__.replace('Connector', '').lower()
        )
        
        # Get all tables
        table_names = self.connector.get_tables(schema)
        self.logger.info(f"Found {len(table_names)} tables")
        
        # Analyze each table
        for table_name in table_names:
            try:
                table = self._analyze_table(table_name, schema)
                db_schema.add_table(table)
                self.logger.debug(f"Analyzed table: {table_name}")
            except Exception as e:
                self.logger.error(f"Error analyzing table {table_name}: {e}")
        
        self.logger.info(f"Schema analysis complete: {len(db_schema.tables)} tables")
        return db_schema
    
    def _analyze_table(self, table_name: str, schema: Optional[str] = None) -> Table:
        """
        Analyze a single table.
        
        Args:
            table_name: Name of the table
            schema: Optional schema name
            
        Returns:
            Table object
        """
        table = Table(name=table_name, schema=schema or 'public')
        
        # Get columns
        columns_data = self.connector.get_table_columns(table_name, schema)
        for col_data in columns_data:
            column = Column(
                name=col_data['name'],
                data_type=col_data['data_type'],
                column_type=self._map_column_type(col_data['data_type']),
                is_nullable=col_data['is_nullable'],
                max_length=col_data.get('max_length'),
                precision=col_data.get('precision'),
                scale=col_data.get('scale'),
                default_value=col_data.get('default_value'),
                is_auto_increment=col_data.get('is_auto_increment', False),
                ordinal_position=col_data.get('ordinal_position', 0)
            )
            table.columns.append(column)
        
        # Get primary key
        pk_data = self.connector.get_primary_key(table_name, schema)
        if pk_data:
            table.primary_key = PrimaryKey(
                name=pk_data['name'],
                columns=pk_data['columns']
            )
        
        # Get foreign keys
        fks_data = self.connector.get_foreign_keys(table_name, schema)
        for fk_data in fks_data:
            foreign_key = ForeignKey(
                name=fk_data['name'],
                column=fk_data['column'],
                referenced_table=fk_data['referenced_table'],
                referenced_column=fk_data['referenced_column'],
                on_delete=fk_data.get('on_delete'),
                on_update=fk_data.get('on_update')
            )
            table.foreign_keys.append(foreign_key)
        
        # Get indexes
        indexes_data = self.connector.get_indexes(table_name, schema)
        for idx_data in indexes_data:
            index = Index(
                name=idx_data['name'],
                columns=idx_data['columns'],
                is_unique=idx_data.get('is_unique', False)
            )
            table.indexes.append(index)
        
        # Get row count
        try:
            table.row_count = self.connector.get_row_count(table_name, schema)
        except Exception as e:
            self.logger.warning(f"Could not get row count for {table_name}: {e}")
            table.row_count = 0
        
        return table
    
    def _map_column_type(self, data_type: str) -> ColumnType:
        """
        Map SQL data type to ColumnType enum.
        
        Args:
            data_type: SQL data type
            
        Returns:
            ColumnType enum value
        """
        data_type_lower = data_type.lower()
        
        type_mapping = {
            'int': ColumnType.INTEGER,
            'integer': ColumnType.INTEGER,
            'smallint': ColumnType.SMALLINT,
            'bigint': ColumnType.BIGINT,
            'decimal': ColumnType.DECIMAL,
            'numeric': ColumnType.NUMERIC,
            'float': ColumnType.FLOAT,
            'double': ColumnType.DOUBLE,
            'real': ColumnType.DOUBLE,
            'varchar': ColumnType.VARCHAR,
            'char': ColumnType.CHAR,
            'text': ColumnType.TEXT,
            'date': ColumnType.DATE,
            'datetime': ColumnType.DATETIME,
            'timestamp': ColumnType.TIMESTAMP,
            'time': ColumnType.TIME,
            'boolean': ColumnType.BOOLEAN,
            'bool': ColumnType.BOOLEAN,
            'bit': ColumnType.BOOLEAN,
            'binary': ColumnType.BINARY,
            'blob': ColumnType.BINARY,
            'json': ColumnType.JSON,
            'jsonb': ColumnType.JSON
        }
        
        # Check for exact match or substring match
        for key, value in type_mapping.items():
            if key in data_type_lower:
                return value
        
        return ColumnType.UNKNOWN
    
    def get_schema_summary(self, db_schema: DatabaseSchema) -> Dict[str, Any]:
        """
        Get summary statistics of the schema.
        
        Args:
            db_schema: DatabaseSchema object
            
        Returns:
            Summary dictionary
        """
        total_columns = sum(len(table.columns) for table in db_schema.tables.values())
        total_fks = sum(len(table.foreign_keys) for table in db_schema.tables.values())
        total_indexes = sum(len(table.indexes) for table in db_schema.tables.values())
        total_rows = sum(table.row_count for table in db_schema.tables.values())
        
        junction_tables = db_schema.get_junction_tables()
        entity_tables = db_schema.get_entity_tables()
        
        return {
            'database_name': db_schema.database_name,
            'database_type': db_schema.database_type,
            'total_tables': len(db_schema.tables),
            'entity_tables': len(entity_tables),
            'junction_tables': len(junction_tables),
            'total_columns': total_columns,
            'total_foreign_keys': total_fks,
            'total_indexes': total_indexes,
            'total_rows': total_rows,
            'tables_with_data': sum(1 for t in db_schema.tables.values() if t.row_count > 0)
        }
