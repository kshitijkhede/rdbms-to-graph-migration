"""Pytest configuration and fixtures."""

import pytest
from unittest.mock import Mock


@pytest.fixture
def mock_mysql_connector():
    """Create a mock MySQL connector."""
    connector = Mock()
    connector.database = "test_db"
    connector.host = "localhost"
    connector.port = 3306
    return connector


@pytest.fixture
def mock_neo4j_loader():
    """Create a mock Neo4j loader."""
    loader = Mock()
    loader.uri = "bolt://localhost:7687"
    loader.database = "neo4j"
    return loader


@pytest.fixture
def sample_table_data():
    """Sample table data for testing."""
    return [
        {'id': 1, 'name': 'Alice', 'email': 'alice@example.com'},
        {'id': 2, 'name': 'Bob', 'email': 'bob@example.com'},
        {'id': 3, 'name': 'Charlie', 'email': 'charlie@example.com'}
    ]
