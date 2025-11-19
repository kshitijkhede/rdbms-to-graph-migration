"""Unit tests for schema analyzer."""

import pytest
from unittest.mock import Mock, MagicMock
from src.analyzers.schema_analyzer import SchemaAnalyzer
from src.models.schema_model import DatabaseSchema, Table, Column


class TestSchemaAnalyzer:
    """Test suite for SchemaAnalyzer."""
    
    @pytest.fixture
    def mock_connector(self):
        """Create a mock database connector."""
        connector = Mock()
        connector.database = "test_db"
        connector.__class__.__name__ = "MySQLConnector"
        return connector
    
    @pytest.fixture
    def analyzer(self, mock_connector):
        """Create SchemaAnalyzer instance with mock connector."""
        return SchemaAnalyzer(mock_connector)
    
    def test_analyze_returns_database_schema(self, analyzer, mock_connector):
        """Test that analyze returns a DatabaseSchema object."""
        # Setup mock
        mock_connector.get_tables.return_value = ['users', 'posts']
        mock_connector.get_table_columns.return_value = [
            {
                'name': 'id',
                'data_type': 'int',
                'is_nullable': False,
                'max_length': None,
                'precision': None,
                'scale': None,
                'default_value': None,
                'is_auto_increment': True,
                'ordinal_position': 1
            }
        ]
        mock_connector.get_primary_key.return_value = {
            'name': 'PRIMARY',
            'columns': ['id']
        }
        mock_connector.get_foreign_keys.return_value = []
        mock_connector.get_indexes.return_value = []
        mock_connector.get_row_count.return_value = 100
        
        # Execute
        result = analyzer.analyze()
        
        # Assert
        assert isinstance(result, DatabaseSchema)
        assert result.database_name == "test_db"
        assert len(result.tables) == 2
    
    def test_analyze_table_extracts_columns(self, analyzer, mock_connector):
        """Test that _analyze_table correctly extracts columns."""
        # Setup
        mock_connector.get_table_columns.return_value = [
            {
                'name': 'id',
                'data_type': 'int',
                'is_nullable': False,
                'max_length': None,
                'precision': None,
                'scale': None,
                'default_value': None,
                'is_auto_increment': True,
                'ordinal_position': 1
            },
            {
                'name': 'name',
                'data_type': 'varchar',
                'is_nullable': True,
                'max_length': 100,
                'precision': None,
                'scale': None,
                'default_value': None,
                'is_auto_increment': False,
                'ordinal_position': 2
            }
        ]
        mock_connector.get_primary_key.return_value = None
        mock_connector.get_foreign_keys.return_value = []
        mock_connector.get_indexes.return_value = []
        mock_connector.get_row_count.return_value = 0
        
        # Execute
        table = analyzer._analyze_table('test_table')
        
        # Assert
        assert len(table.columns) == 2
        assert table.columns[0].name == 'id'
        assert table.columns[1].name == 'name'
    
    def test_get_schema_summary(self, analyzer):
        """Test schema summary generation."""
        # Create test schema
        db_schema = DatabaseSchema(
            database_name="test_db",
            database_type="mysql"
        )
        
        table = Table(name="users")
        table.row_count = 100
        table.columns = [Column(name="id", data_type="int")]
        db_schema.add_table(table)
        
        # Execute
        summary = analyzer.get_schema_summary(db_schema)
        
        # Assert
        assert summary['database_name'] == "test_db"
        assert summary['total_tables'] == 1
        assert summary['total_rows'] == 100
