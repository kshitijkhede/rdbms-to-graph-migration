"""
Custom Transformation Example

This example demonstrates custom schema mapping and transformations.
"""

from src.connectors.postgresql_connector import PostgreSQLConnector
from src.analyzers.schema_analyzer import SchemaAnalyzer
from src.transformers.graph_transformer import GraphTransformer
from src.loaders.neo4j_loader import Neo4jLoader
from src.models.graph_model import NodeLabel, RelationshipType, Property, PropertyType
from src.utils.logger import setup_logger
from src.utils.helpers import sanitize_label


def custom_transform_user_table(table, graph_model):
    """
    Custom transformation for user table.
    Add derived properties and custom logic.
    """
    # Get the default node label
    label_name = sanitize_label(table.name)
    node_label = graph_model.get_node_label(label_name)
    
    if node_label:
        # Add a custom derived property
        full_name_prop = Property(
            name="fullName",
            type=PropertyType.STRING,
            is_required=False
        )
        node_label.add_property(full_name_prop)
    
    return node_label


def add_custom_relationships(graph_model):
    """Add custom relationships not derived from foreign keys."""
    
    # Example: Add a FRIENDS_WITH relationship between users
    friends_rel = RelationshipType(
        name="FRIENDS_WITH",
        from_label="User",
        to_label="User",
        properties=[]
    )
    
    # Add created_at property
    created_at_prop = Property(
        name="createdAt",
        type=PropertyType.DATETIME,
        is_required=False
    )
    friends_rel.add_property(created_at_prop)
    
    graph_model.add_relationship_type(friends_rel)


def main():
    """Execute custom migration with transformations."""
    logger = setup_logger(level="INFO")
    logger.info("Starting custom transformation example")
    
    # Connect to PostgreSQL
    pg_conn = PostgreSQLConnector(
        host="localhost",
        port=5432,
        database="test_db",
        username="postgres",
        password="password"
    )
    
    # Connect to Neo4j
    neo4j_loader = Neo4jLoader(
        uri="bolt://localhost:7687",
        username="neo4j",
        password="password"
    )
    
    try:
        pg_conn.connect()
        neo4j_loader.connect()
        
        # Analyze schema
        analyzer = SchemaAnalyzer(pg_conn)
        db_schema = analyzer.analyze()
        
        # Transform with custom configuration
        custom_config = {
            'tables_as_nodes': ['users', 'posts', 'comments'],
            'foreign_keys_as_relationships': True,
            'junction_tables_as_relationships': True
        }
        
        transformer = GraphTransformer(db_schema, custom_config)
        graph_model = transformer.transform()
        
        # Apply custom transformations
        logger.info("Applying custom transformations...")
        
        # Custom transform specific tables
        user_table = db_schema.get_table('users')
        if user_table:
            custom_transform_user_table(user_table, graph_model)
        
        # Add custom relationships
        add_custom_relationships(graph_model)
        
        # Create schema in Neo4j
        neo4j_loader.create_constraints_and_indexes(graph_model)
        
        logger.info("Custom transformation complete!")
        
        # Print graph model summary
        print("\nGraph Model Summary:")
        print(f"Node Labels: {len(graph_model.node_labels)}")
        for label_name, label in graph_model.node_labels.items():
            print(f"  - {label_name}: {len(label.properties)} properties")
        
        print(f"\nRelationship Types: {len(graph_model.relationship_types)}")
        for rel_name, rel in graph_model.relationship_types.items():
            print(f"  - {rel.name}: {rel.from_label} -> {rel.to_label}")
        
    except Exception as e:
        logger.error(f"Custom migration failed: {e}", exc_info=True)
        raise
    
    finally:
        pg_conn.disconnect()
        neo4j_loader.disconnect()


if __name__ == "__main__":
    main()
