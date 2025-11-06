"""
Neo4j Connection Module
Handles connection setup and verification for Neo4j database
"""
from neo4j import GraphDatabase
from config.config import NEO4J_CONFIG


class Neo4jConnection:
    """
    Manages Neo4j database connections
    """
    
    def __init__(self, uri=None, user=None, password=None):
        """
        Initialize Neo4j connection parameters
        
        Args:
            uri: Neo4j connection URI (default from config)
            user: Neo4j username (default from config)
            password: Neo4j password (default from config)
        """
        self.uri = uri or NEO4J_CONFIG['uri']
        self.user = user or NEO4J_CONFIG['user']
        self.password = password or NEO4J_CONFIG['password']
        self.driver = None
    
    def get_driver(self):
        """
        Creates and returns a Neo4j Driver instance.
        
        Returns:
            Neo4j Driver instance
        """
        try:
            self.driver = GraphDatabase.driver(
                self.uri, 
                auth=(self.user, self.password)
            )
            return self.driver
        except Exception as e:
            print(f"Error: Failed to create Neo4j driver: {e}")
            raise
    
    def verify_connectivity(self):
        """
        Verifies the connection to the Neo4j database.
        
        Returns:
            bool: True if connection is successful
        """
        print("Attempting to verify Neo4j connection...")
        try:
            if not self.driver:
                self.get_driver()
            
            self.driver.verify_connectivity()
            print("Success: Neo4j connection verified.")
            return True
        except Exception as e:
            print(f"Error: Failed to connect to Neo4j database: {e}")
            print("Please check credentials and if the database is running.")
            raise
    
    def close(self):
        """
        Closes the Neo4j driver connection
        """
        if self.driver:
            self.driver.close()
            print("Neo4j driver closed.")
    
    def execute_query(self, query, parameters=None):
        """
        Execute a Cypher query
        
        Args:
            query: Cypher query string
            parameters: Dictionary of parameters for the query
            
        Returns:
            Query results
        """
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [record for record in result]
    
    def clear_database(self):
        """
        Clears all nodes and relationships from the database
        Warning: This will delete all data!
        """
        print("Clearing Neo4j database...")
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        print("Database cleared successfully.")


def main():
    """
    Test Neo4j connection
    """
    connection = None
    try:
        connection = Neo4jConnection()
        driver = connection.get_driver()
        connection.verify_connectivity()
        print("Neo4j setup is correct.")
    except Exception as e:
        print(f"Project setup failed: {e}")
    finally:
        if connection:
            connection.close()


if __name__ == "__main__":
    main()
