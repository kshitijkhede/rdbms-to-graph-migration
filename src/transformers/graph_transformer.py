"""
Graph Transformer

Transforms relational database schema and data into graph model.
"""

import logging
from typing import Dict, List, Any, Optional
from ..models.schema_model import DatabaseSchema, Table, ForeignKey
from ..models.graph_model import (
    GraphModel, NodeLabel, RelationshipType, Property, PropertyType
)
from ..utils.helpers import (
    sanitize_label, sanitize_property_name,
    convert_sql_type_to_graph_type, create_relationship_type_name
)


class GraphTransformer:
    """Transforms relational schema to graph model."""
    
    def __init__(self, db_schema: DatabaseSchema, config: Optional[Dict[str, Any]] = None):
        """
        Initialize graph transformer.
        
        Args:
            db_schema: Database schema to transform
            config: Optional mapping configuration
        """
        self.db_schema = db_schema
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        self.graph_model = GraphModel(
            name=db_schema.database_name + "_graph",
            source_schema_name=db_schema.database_name
        )
    
    def transform(self) -> GraphModel:
        """
        Transform complete database schema to graph model.
        
        Returns:
            GraphModel object
        """
        self.logger.info("Starting schema transformation to graph model")
        
        # Transform entity tables to nodes
        entity_tables = self.db_schema.get_entity_tables()
        for table in entity_tables:
            node_label = self._table_to_node_label(table)
            self.graph_model.add_node_label(node_label)
        
        self.logger.info(f"Created {len(self.graph_model.node_labels)} node labels")
        
        # Transform foreign keys to relationships
        for table in entity_tables:
            for fk in table.foreign_keys:
                rel_type = self._foreign_key_to_relationship(table, fk)
                if rel_type:
                    self.graph_model.add_relationship_type(rel_type)
        
        # Transform junction tables to relationships
        junction_tables = self.db_schema.get_junction_tables()
        for table in junction_tables:
            rel_type = self._junction_table_to_relationship(table)
            if rel_type:
                self.graph_model.add_relationship_type(rel_type)
        
        self.logger.info(
            f"Created {len(self.graph_model.relationship_types)} relationship types"
        )
        
        return self.graph_model
    
    def _table_to_node_label(self, table: Table) -> NodeLabel:
        """
        Convert a table to a node label.
        
        Args:
            table: Table to convert
            
        Returns:
            NodeLabel object
        """
        label_name = sanitize_label(table.name)
        node_label = NodeLabel(
            name=label_name,
            source_table=table.name
        )
        
        # Convert columns to properties
        for column in table.columns:
            # Skip foreign key columns (they become relationships)
            is_fk = any(fk.column == column.name for fk in table.foreign_keys)
            if is_fk:
                continue
            
            prop_name = sanitize_property_name(column.name)
            prop_type = self._get_property_type(column.data_type)
            
            is_required = not column.is_nullable
            is_indexed = False
            
            # Mark primary key as indexed
            if table.primary_key and column.name in table.primary_key.columns:
                is_indexed = True
                node_label.primary_key = prop_name
            
            property_obj = Property(
                name=prop_name,
                type=prop_type,
                is_required=is_required,
                is_indexed=is_indexed,
                original_column=column.name
            )
            node_label.add_property(property_obj)
        
        # Add indexes
        for index in table.indexes:
            for col_name in index.columns:
                prop_name = sanitize_property_name(col_name)
                if prop_name not in node_label.indexes:
                    node_label.indexes.append(prop_name)
        
        return node_label
    
    def _foreign_key_to_relationship(self, table: Table, 
                                    fk: ForeignKey) -> Optional[RelationshipType]:
        """
        Convert a foreign key to a relationship type.
        
        Args:
            table: Source table
            fk: Foreign key constraint
            
        Returns:
            RelationshipType object or None
        """
        from_label = sanitize_label(table.name)
        to_label = sanitize_label(fk.referenced_table)
        
        # Create relationship name
        rel_name = create_relationship_type_name(table.name, fk.referenced_table, fk.name)
        
        rel_type = RelationshipType(
            name=rel_name,
            from_label=from_label,
            to_label=to_label,
            source_foreign_key=fk.name
        )
        
        return rel_type
    
    def _junction_table_to_relationship(self, table: Table) -> Optional[RelationshipType]:
        """
        Convert a junction table to a relationship type with properties.
        
        Args:
            table: Junction table
            
        Returns:
            RelationshipType object or None
        """
        if len(table.foreign_keys) != 2:
            return None
        
        fk1, fk2 = table.foreign_keys
        from_label = sanitize_label(fk1.referenced_table)
        to_label = sanitize_label(fk2.referenced_table)
        
        # Create relationship name from the junction table name
        rel_name = sanitize_label(table.name).upper()
        
        rel_type = RelationshipType(
            name=rel_name,
            from_label=from_label,
            to_label=to_label,
            source_junction_table=table.name
        )
        
        # Add non-FK columns as relationship properties
        fk_columns = {fk1.column, fk2.column}
        for column in table.columns:
            if column.name not in fk_columns:
                prop_name = sanitize_property_name(column.name)
                prop_type = self._get_property_type(column.data_type)
                
                property_obj = Property(
                    name=prop_name,
                    type=prop_type,
                    is_required=not column.is_nullable,
                    original_column=column.name
                )
                rel_type.add_property(property_obj)
        
        return rel_type
    
    def _get_property_type(self, sql_type: str) -> PropertyType:
        """
        Convert SQL type to PropertyType.
        
        Args:
            sql_type: SQL data type
            
        Returns:
            PropertyType enum value
        """
        graph_type = convert_sql_type_to_graph_type(sql_type)
        
        type_mapping = {
            'STRING': PropertyType.STRING,
            'INTEGER': PropertyType.INTEGER,
            'FLOAT': PropertyType.FLOAT,
            'BOOLEAN': PropertyType.BOOLEAN,
            'DATE': PropertyType.DATE,
            'DATETIME': PropertyType.DATETIME,
            'MAP': PropertyType.MAP
        }
        
        return type_mapping.get(graph_type, PropertyType.STRING)
    
    def transform_row_to_node(self, table_name: str, 
                             row_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform a table row to node properties.
        
        Args:
            table_name: Source table name
            row_data: Row data dictionary
            
        Returns:
            Node properties dictionary
        """
        label_name = sanitize_label(table_name)
        node_label = self.graph_model.get_node_label(label_name)
        
        if not node_label:
            raise ValueError(f"No node label found for table: {table_name}")
        
        properties = {}
        table = self.db_schema.get_table(table_name)
        
        for column in table.columns:
            # Skip foreign key columns
            is_fk = any(fk.column == column.name for fk in table.foreign_keys)
            if is_fk:
                continue
            
            prop_name = sanitize_property_name(column.name)
            value = row_data.get(column.name)
            
            # Convert value if needed
            properties[prop_name] = self._convert_value(value, column.data_type)
        
        return properties
    
    def _convert_value(self, value: Any, sql_type: str) -> Any:
        """
        Convert SQL value to appropriate Python type for Neo4j.
        
        Args:
            value: Original value
            sql_type: SQL data type
            
        Returns:
            Converted value
        """
        if value is None:
            return None
        
        # Handle dates and timestamps
        if 'date' in sql_type.lower() or 'time' in sql_type.lower():
            return str(value)
        
        # Handle JSON
        if 'json' in sql_type.lower() and isinstance(value, str):
            import json
            try:
                return json.loads(value)
            except:
                return value
        
        return value
