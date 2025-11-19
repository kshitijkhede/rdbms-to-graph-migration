"""
Neo4j Loader

Loads nodes and relationships into Neo4j graph database.
"""

import logging
from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError
from tqdm import tqdm
from ..models.graph_model import GraphModel, NodeLabel, RelationshipType


class Neo4jLoader:
    """Loads data into Neo4j graph database."""
    
    def __init__(self, uri: str, username: str, password: str, database: str = "neo4j"):
        """
        Initialize Neo4j loader.
        
        Args:
            uri: Neo4j connection URI
            username: Neo4j username
            password: Neo4j password
            database: Neo4j database name
        """
        self.uri = uri
        self.username = username
        self.password = password
        self.database = database
        self.driver = None
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def connect(self) -> None:
        """Establish connection to Neo4j."""
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password))
            self.driver.verify_connectivity()
            self.logger.info(f"Connected to Neo4j database: {self.database}")
        except Exception as e:
            self.logger.error(f"Failed to connect to Neo4j: {e}")
            raise
    
    def disconnect(self) -> None:
        """Close Neo4j connection."""
        if self.driver:
            self.driver.close()
            self.logger.info("Disconnected from Neo4j")
    
    def test_connection(self) -> bool:
        """
        Test Neo4j connection.
        
        Returns:
            True if connection successful
        """
        try:
            self.connect()
            with self.driver.session(database=self.database) as session:
                result = session.run("RETURN 1 as result")
                value = result.single()["result"]
                self.disconnect()
                return value == 1
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False
    
    def create_constraints_and_indexes(self, graph_model: GraphModel) -> None:
        """
        Create constraints and indexes for the graph model.
        
        Args:
            graph_model: Graph model with node labels and relationships
        """
        self.logger.info("Creating constraints and indexes")
        
        with self.driver.session(database=self.database) as session:
            for node_label in graph_model.node_labels.values():
                # Create uniqueness constraint on primary key
                if node_label.primary_key:
                    try:
                        constraint_name = f"{node_label.name}_{node_label.primary_key}_unique"
                        query = f"""
                            CREATE CONSTRAINT {constraint_name} IF NOT EXISTS
                            FOR (n:{node_label.name})
                            REQUIRE n.{node_label.primary_key} IS UNIQUE
                        """
                        session.run(query)
                        self.logger.debug(f"Created constraint: {constraint_name}")
                    except Neo4jError as e:
                        self.logger.warning(f"Could not create constraint: {e}")
                
                # Create indexes on indexed properties
                for index_prop in node_label.indexes:
                    try:
                        index_name = f"{node_label.name}_{index_prop}_index"
                        query = f"""
                            CREATE INDEX {index_name} IF NOT EXISTS
                            FOR (n:{node_label.name})
                            ON (n.{index_prop})
                        """
                        session.run(query)
                        self.logger.debug(f"Created index: {index_name}")
                    except Neo4jError as e:
                        self.logger.warning(f"Could not create index: {e}")
        
        self.logger.info("Constraints and indexes created")
    
    def clear_database(self) -> None:
        """Clear all nodes and relationships from the database."""
        self.logger.warning("Clearing database...")
        
        with self.driver.session(database=self.database) as session:
            session.run("MATCH (n) DETACH DELETE n")
        
        self.logger.info("Database cleared")
    
    def load_nodes_batch(self, label: str, nodes: List[Dict[str, Any]], 
                        id_property: str = "id") -> int:
        """
        Load a batch of nodes.
        
        Args:
            label: Node label
            nodes: List of node property dictionaries
            id_property: Name of the ID property
            
        Returns:
            Number of nodes created
        """
        if not nodes:
            return 0
        
        query = f"""
            UNWIND $nodes AS node
            CREATE (n:{label})
            SET n = node
        """
        
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(query, nodes=nodes)
                summary = result.consume()
                count = summary.counters.nodes_created
                self.logger.debug(f"Loaded {count} nodes with label {label}")
                return count
        except Neo4jError as e:
            self.logger.error(f"Error loading nodes: {e}")
            raise
    
    def load_relationships_batch(self, rel_type: str, from_label: str, to_label: str,
                                relationships: List[Dict[str, Any]],
                                from_id_prop: str = "id", 
                                to_id_prop: str = "id") -> int:
        """
        Load a batch of relationships.
        
        Args:
            rel_type: Relationship type
            from_label: Source node label
            to_label: Target node label
            relationships: List of relationship dictionaries with from_id, to_id, and properties
            from_id_prop: Property name for source node ID
            to_id_prop: Property name for target node ID
            
        Returns:
            Number of relationships created
        """
        if not relationships:
            return 0
        
        query = f"""
            UNWIND $rels AS rel
            MATCH (from:{from_label} {{{from_id_prop}: rel.from_id}})
            MATCH (to:{to_label} {{{to_id_prop}: rel.to_id}})
            CREATE (from)-[r:{rel_type}]->(to)
            SET r = rel.properties
        """
        
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(query, rels=relationships)
                summary = result.consume()
                count = summary.counters.relationships_created
                self.logger.debug(
                    f"Loaded {count} relationships of type {rel_type}"
                )
                return count
        except Neo4jError as e:
            self.logger.error(f"Error loading relationships: {e}")
            raise
    
    def get_node_count(self, label: Optional[str] = None) -> int:
        """
        Get count of nodes.
        
        Args:
            label: Optional node label filter
            
        Returns:
            Number of nodes
        """
        with self.driver.session(database=self.database) as session:
            if label:
                query = f"MATCH (n:{label}) RETURN count(n) as count"
            else:
                query = "MATCH (n) RETURN count(n) as count"
            
            result = session.run(query)
            return result.single()["count"]
    
    def get_relationship_count(self, rel_type: Optional[str] = None) -> int:
        """
        Get count of relationships.
        
        Args:
            rel_type: Optional relationship type filter
            
        Returns:
            Number of relationships
        """
        with self.driver.session(database=self.database) as session:
            if rel_type:
                query = f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count"
            else:
                query = "MATCH ()-[r]->() RETURN count(r) as count"
            
            result = session.run(query)
            return result.single()["count"]
    
    def execute_cypher(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query.
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            
        Returns:
            List of result records
        """
        with self.driver.session(database=self.database) as session:
            result = session.run(query, parameters or {})
            return [dict(record) for record in result]
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
