"""
Configuration file for RDBMS-to-Graph Migration Engine
Update these settings according to your environment
"""

# MySQL Source Database Configuration
MYSQL_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'migration',
    'password': 'Migration@123',
    'database': 'migration_source_ecommerce',  # Default database
}

# Neo4j Target Database Configuration
NEO4J_CONFIG = {
    'uri': 'bolt://localhost:7687',
    'user': 'neo4j',
    'password': 'Migration@123',  # Update with your Neo4j password
}

# Migration Settings
MIGRATION_SETTINGS = {
    'batch_size': 1000,  # Number of records to process in each batch
    'transaction_size': 500,  # Number of records per transaction
    'log_level': 'INFO',  # Logging level: DEBUG, INFO, WARNING, ERROR
    'output_dir': 'data',  # Directory for generated mapping files
}

# Paths
MAPPING_FILE_PATH = 'data/mapping.json'
SCHEMA_OUTPUT_PATH = 'data/schema_analysis.json'
