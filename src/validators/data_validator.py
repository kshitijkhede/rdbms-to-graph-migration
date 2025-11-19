"""
Data Validator

Validates data integrity before and after migration.
"""

import logging
from typing import Dict, Any, List, Optional
from ..connectors.rdbms_connector import RDBMSConnector
from ..loaders.neo4j_loader import Neo4jLoader
from ..models.schema_model import DatabaseSchema
from ..models.graph_model import GraphModel


class DataValidator:
    """Validates migration data integrity."""
    
    def __init__(self, source_connector: RDBMSConnector, 
                 neo4j_loader: Neo4jLoader,
                 db_schema: DatabaseSchema,
                 graph_model: GraphModel):
        """
        Initialize data validator.
        
        Args:
            source_connector: Source database connector
            neo4j_loader: Neo4j loader instance
            db_schema: Source database schema
            graph_model: Target graph model
        """
        self.source_connector = source_connector
        self.neo4j_loader = neo4j_loader
        self.db_schema = db_schema
        self.graph_model = graph_model
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def validate_pre_migration(self) -> Dict[str, Any]:
        """
        Validate source database before migration.
        
        Returns:
            Validation results dictionary
        """
        self.logger.info("Running pre-migration validation")
        
        results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'statistics': {}
        }
        
        # Check source connection
        if not self.source_connector.connection:
            results['valid'] = False
            results['errors'].append("Source database not connected")
            return results
        
        # Collect statistics
        total_tables = len(self.db_schema.tables)
        total_rows = sum(table.row_count for table in self.db_schema.tables.values())
        
        results['statistics'] = {
            'total_tables': total_tables,
            'total_rows': total_rows,
            'entity_tables': len(self.db_schema.get_entity_tables()),
            'junction_tables': len(self.db_schema.get_junction_tables())
        }
        
        # Check for tables with no primary key
        tables_without_pk = []
        for table in self.db_schema.get_entity_tables():
            if not table.primary_key:
                tables_without_pk.append(table.name)
        
        if tables_without_pk:
            results['warnings'].append(
                f"Tables without primary key: {', '.join(tables_without_pk)}"
            )
        
        # Check for orphaned foreign keys
        for table in self.db_schema.tables.values():
            for fk in table.foreign_keys:
                if fk.referenced_table not in self.db_schema.tables:
                    results['errors'].append(
                        f"Foreign key {fk.name} in table {table.name} "
                        f"references non-existent table {fk.referenced_table}"
                    )
                    results['valid'] = False
        
        self.logger.info("Pre-migration validation complete")
        return results
    
    def validate_post_migration(self) -> Dict[str, Any]:
        """
        Validate target database after migration.
        
        Returns:
            Validation results dictionary
        """
        self.logger.info("Running post-migration validation")
        
        results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'statistics': {},
            'row_counts': {}
        }
        
        # Compare row counts
        row_count_mismatches = []
        
        for table in self.db_schema.get_entity_tables():
            source_count = table.row_count
            
            # Get corresponding node label
            from ..utils.helpers import sanitize_label
            label = sanitize_label(table.name)
            
            try:
                target_count = self.neo4j_loader.get_node_count(label)
            except Exception as e:
                results['errors'].append(f"Error getting count for {label}: {e}")
                results['valid'] = False
                continue
            
            results['row_counts'][table.name] = {
                'source': source_count,
                'target': target_count,
                'match': source_count == target_count
            }
            
            if source_count != target_count:
                row_count_mismatches.append({
                    'table': table.name,
                    'source': source_count,
                    'target': target_count,
                    'difference': target_count - source_count
                })
        
        if row_count_mismatches:
            results['valid'] = False
            results['errors'].append(
                f"Row count mismatches found in {len(row_count_mismatches)} tables"
            )
            results['row_count_mismatches'] = row_count_mismatches
        
        # Get target statistics
        total_nodes = self.neo4j_loader.get_node_count()
        total_relationships = self.neo4j_loader.get_relationship_count()
        
        results['statistics'] = {
            'total_nodes': total_nodes,
            'total_relationships': total_relationships,
            'node_labels': len(self.graph_model.node_labels),
            'relationship_types': len(self.graph_model.relationship_types)
        }
        
        self.logger.info("Post-migration validation complete")
        return results
    
    def validate_relationships(self) -> Dict[str, Any]:
        """
        Validate relationship integrity.
        
        Returns:
            Validation results dictionary
        """
        self.logger.info("Validating relationships")
        
        results = {
            'valid': True,
            'errors': [],
            'relationship_counts': {}
        }
        
        for rel_type in self.graph_model.relationship_types.values():
            try:
                count = self.neo4j_loader.get_relationship_count(rel_type.name)
                results['relationship_counts'][rel_type.name] = count
                
                if count == 0:
                    results['warnings'] = results.get('warnings', [])
                    results['warnings'].append(
                        f"Relationship type {rel_type.name} has no instances"
                    )
            except Exception as e:
                results['errors'].append(
                    f"Error validating relationship {rel_type.name}: {e}"
                )
                results['valid'] = False
        
        return results
    
    def check_referential_integrity(self) -> Dict[str, Any]:
        """
        Check referential integrity of relationships.
        
        Returns:
            Validation results dictionary
        """
        self.logger.info("Checking referential integrity")
        
        results = {
            'valid': True,
            'errors': []
        }
        
        # Check for orphaned relationships (relationships without valid nodes)
        for rel_type in self.graph_model.relationship_types.values():
            # Check for relationships with missing source nodes
            query = f"""
                MATCH ()-[r:{rel_type.name}]->(to:{rel_type.to_label})
                WHERE NOT EXISTS {{
                    MATCH (from:{rel_type.from_label})-[r]->(to)
                }}
                RETURN count(r) as orphaned_count
            """
            
            try:
                result = self.neo4j_loader.execute_cypher(query)
                orphaned_count = result[0]['orphaned_count'] if result else 0
                
                if orphaned_count > 0:
                    results['valid'] = False
                    results['errors'].append(
                        f"Found {orphaned_count} orphaned relationships "
                        f"of type {rel_type.name}"
                    )
            except Exception as e:
                self.logger.warning(f"Could not check integrity for {rel_type.name}: {e}")
        
        return results
    
    def get_validation_summary(self, pre_results: Dict[str, Any], 
                             post_results: Dict[str, Any]) -> str:
        """
        Generate a summary of validation results.
        
        Args:
            pre_results: Pre-migration validation results
            post_results: Post-migration validation results
            
        Returns:
            Summary string
        """
        lines = []
        lines.append("=" * 60)
        lines.append("MIGRATION VALIDATION SUMMARY")
        lines.append("=" * 60)
        
        # Pre-migration
        lines.append("\nPRE-MIGRATION:")
        lines.append(f"  Status: {'PASSED' if pre_results['valid'] else 'FAILED'}")
        if pre_results.get('statistics'):
            stats = pre_results['statistics']
            lines.append(f"  Total Tables: {stats.get('total_tables', 0)}")
            lines.append(f"  Total Rows: {stats.get('total_rows', 0)}")
        if pre_results.get('errors'):
            lines.append(f"  Errors: {len(pre_results['errors'])}")
        if pre_results.get('warnings'):
            lines.append(f"  Warnings: {len(pre_results['warnings'])}")
        
        # Post-migration
        lines.append("\nPOST-MIGRATION:")
        lines.append(f"  Status: {'PASSED' if post_results['valid'] else 'FAILED'}")
        if post_results.get('statistics'):
            stats = post_results['statistics']
            lines.append(f"  Total Nodes: {stats.get('total_nodes', 0)}")
            lines.append(f"  Total Relationships: {stats.get('total_relationships', 0)}")
        if post_results.get('errors'):
            lines.append(f"  Errors: {len(post_results['errors'])}")
        
        lines.append("\n" + "=" * 60)
        
        return "\n".join(lines)
