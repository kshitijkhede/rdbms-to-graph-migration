"""Unit tests for graph transformer."""

import pytest
from src.transformers.graph_transformer import GraphTransformer
from src.models.schema_model import DatabaseSchema, Table, Column, ForeignKey, PrimaryKey
from src.models.graph_model import GraphModel


class TestGraphTransformer:
    """Test suite for GraphTransformer."""
    
    @pytest.fixture
    def simple_schema(self):
        """Create a simple test schema."""
        schema = DatabaseSchema(
            database_name="test_db",
            database_type="mysql"
        )
        
        # Create users table
        users_table = Table(name="users")
        users_table.columns = [
            Column(name="id", data_type="int", is_nullable=False),
            Column(name="name", data_type="varchar", is_nullable=False),
            Column(name="email", data_type="varchar", is_nullable=True)
        ]
        users_table.primary_key = PrimaryKey(name="PRIMARY", columns=["id"])
        
        # Create posts table with foreign key
        posts_table = Table(name="posts")
        posts_table.columns = [
            Column(name="id", data_type="int", is_nullable=False),
            Column(name="user_id", data_type="int", is_nullable=False),
            Column(name="title", data_type="varchar", is_nullable=False)
        ]
        posts_table.primary_key = PrimaryKey(name="PRIMARY", columns=["id"])
        posts_table.foreign_keys = [
            ForeignKey(
                name="fk_posts_user",
                column="user_id",
                referenced_table="users",
                referenced_column="id"
            )
        ]
        
        schema.add_table(users_table)
        schema.add_table(posts_table)
        
        return schema
    
    @pytest.fixture
    def transformer(self, simple_schema):
        """Create GraphTransformer instance."""
        return GraphTransformer(simple_schema)
    
    def test_transform_creates_graph_model(self, transformer):
        """Test that transform creates a GraphModel."""
        result = transformer.transform()
        
        assert isinstance(result, GraphModel)
        assert len(result.node_labels) > 0
    
    def test_table_to_node_label(self, transformer, simple_schema):
        """Test conversion of table to node label."""
        users_table = simple_schema.get_table("users")
        node_label = transformer._table_to_node_label(users_table)
        
        assert node_label.name == "Users"
        assert node_label.source_table == "users"
        assert len(node_label.properties) > 0
        assert node_label.primary_key == "id"
    
    def test_foreign_key_to_relationship(self, transformer, simple_schema):
        """Test conversion of foreign key to relationship."""
        posts_table = simple_schema.get_table("posts")
        fk = posts_table.foreign_keys[0]
        
        rel_type = transformer._foreign_key_to_relationship(posts_table, fk)
        
        assert rel_type is not None
        assert rel_type.from_label == "Posts"
        assert rel_type.to_label == "Users"
    
    def test_transform_row_to_node(self, transformer, simple_schema):
        """Test transformation of row data to node properties."""
        row_data = {
            'id': 1,
            'name': 'John Doe',
            'email': 'john@example.com'
        }
        
        properties = transformer.transform_row_to_node('users', row_data)
        
        assert 'id' in properties
        assert 'name' in properties
        assert 'email' in properties
