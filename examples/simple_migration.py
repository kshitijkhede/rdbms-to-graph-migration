"""
Simple Migration Example

This example demonstrates a basic migration from MySQL to Neo4j.
"""

from src.connectors.mysql_connector import MySQLConnector
from src.analyzers.schema_analyzer import SchemaAnalyzer
from src.transformers.graph_transformer import GraphTransformer
from src.loaders.neo4j_loader import Neo4jLoader
from src.extractors.data_extractor import DataExtractor
from src.utils.logger import setup_logger


def main():
    """Execute a simple migration."""
    # Setup logging
    logger = setup_logger(level="INFO", log_file="logs/simple_migration.log")
    logger.info("Starting simple migration example")
    
    # Connect to MySQL
    mysql_conn = MySQLConnector(
        host="localhost",
        port=3306,
        database="test_db",
        username="root",
        password="password"
    )
    
    # Connect to Neo4j
    neo4j_loader = Neo4jLoader(
        uri="bolt://localhost:7687",
        username="neo4j",
        password="password"
    )
    
    try:
        # Connect to databases
        mysql_conn.connect()
        neo4j_loader.connect()
        
        # Analyze schema
        logger.info("Analyzing schema...")
        analyzer = SchemaAnalyzer(mysql_conn)
        db_schema = analyzer.analyze()
        
        # Transform to graph model
        logger.info("Transforming to graph model...")
        transformer = GraphTransformer(db_schema)
        graph_model = transformer.transform()
        
        # Create constraints and indexes
        logger.info("Creating constraints and indexes...")
        neo4j_loader.create_constraints_and_indexes(graph_model)
        
        # Extract and load data
        logger.info("Migrating data...")
        extractor = DataExtractor(mysql_conn, batch_size=1000)
        
        # Migrate nodes (entity tables)
        for table in db_schema.get_entity_tables():
            if table.row_count == 0:
                continue
            
            logger.info(f"Migrating table: {table.name}")
            
            for batch in extractor.extract_table_data(table):
                # Transform rows to nodes
                nodes = []
                for row in batch:
                    properties = transformer.transform_row_to_node(table.name, row)
                    nodes.append(properties)
                
                # Load batch
                from src.utils.helpers import sanitize_label
                label = sanitize_label(table.name)
                neo4j_loader.load_nodes_batch(label, nodes)
        
        logger.info("Migration complete!")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        raise
    
    finally:
        # Cleanup
        mysql_conn.disconnect()
        neo4j_loader.disconnect()


if __name__ == "__main__":
    main()
