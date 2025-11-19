"""
Graph Model Classes

Represents property graph components including nodes, relationships,
and the complete graph model.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
from enum import Enum


class PropertyType(Enum):
    """Property data types in graph database."""
    STRING = "STRING"
    INTEGER = "INTEGER"
    FLOAT = "FLOAT"
    BOOLEAN = "BOOLEAN"
    DATE = "DATE"
    DATETIME = "DATETIME"
    LIST = "LIST"
    MAP = "MAP"


@dataclass
class Property:
    """Represents a node or relationship property."""
    name: str
    type: PropertyType
    is_required: bool = False
    is_indexed: bool = False
    original_column: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert property to dictionary."""
        return {
            'name': self.name,
            'type': self.type.value,
            'is_required': self.is_required,
            'is_indexed': self.is_indexed,
            'original_column': self.original_column
        }


@dataclass
class NodeLabel:
    """Represents a node label (type) in the graph."""
    name: str
    properties: List[Property] = field(default_factory=list)
    source_table: Optional[str] = None
    primary_key: Optional[str] = None
    indexes: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    
    def add_property(self, prop: Property) -> None:
        """Add a property to the node label."""
        self.properties.append(prop)
    
    def get_property(self, name: str) -> Optional[Property]:
        """Get property by name."""
        for prop in self.properties:
            if prop.name == name:
                return prop
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert node label to dictionary."""
        return {
            'name': self.name,
            'properties': [prop.to_dict() for prop in self.properties],
            'source_table': self.source_table,
            'primary_key': self.primary_key,
            'indexes': self.indexes,
            'constraints': self.constraints
        }


@dataclass
class RelationshipType:
    """Represents a relationship type in the graph."""
    name: str
    from_label: str
    to_label: str
    properties: List[Property] = field(default_factory=list)
    source_foreign_key: Optional[str] = None
    source_junction_table: Optional[str] = None
    is_required: bool = False
    
    def add_property(self, prop: Property) -> None:
        """Add a property to the relationship."""
        self.properties.append(prop)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert relationship type to dictionary."""
        return {
            'name': self.name,
            'from_label': self.from_label,
            'to_label': self.to_label,
            'properties': [prop.to_dict() for prop in self.properties],
            'source_foreign_key': self.source_foreign_key,
            'source_junction_table': self.source_junction_table,
            'is_required': self.is_required
        }


@dataclass
class Node:
    """Represents a node instance."""
    label: str
    properties: Dict[str, Any] = field(default_factory=dict)
    id_property: str = "id"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary."""
        return {
            'label': self.label,
            'properties': self.properties,
            'id_property': self.id_property
        }


@dataclass
class Relationship:
    """Represents a relationship instance."""
    type: str
    from_node_label: str
    to_node_label: str
    from_id: Any
    to_id: Any
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert relationship to dictionary."""
        return {
            'type': self.type,
            'from_node_label': self.from_node_label,
            'to_node_label': self.to_node_label,
            'from_id': self.from_id,
            'to_id': self.to_id,
            'properties': self.properties
        }


@dataclass
class GraphModel:
    """Represents the complete graph model."""
    name: str
    node_labels: Dict[str, NodeLabel] = field(default_factory=dict)
    relationship_types: Dict[str, RelationshipType] = field(default_factory=dict)
    source_schema_name: Optional[str] = None
    
    def add_node_label(self, label: NodeLabel) -> None:
        """Add a node label to the model."""
        self.node_labels[label.name] = label
    
    def add_relationship_type(self, rel_type: RelationshipType) -> None:
        """Add a relationship type to the model."""
        key = f"{rel_type.from_label}_{rel_type.name}_{rel_type.to_label}"
        self.relationship_types[key] = rel_type
    
    def get_node_label(self, name: str) -> Optional[NodeLabel]:
        """Get node label by name."""
        return self.node_labels.get(name)
    
    def get_relationships_for_label(self, label: str) -> List[RelationshipType]:
        """Get all relationships involving a label."""
        relationships = []
        for rel in self.relationship_types.values():
            if rel.from_label == label or rel.to_label == label:
                relationships.append(rel)
        return relationships
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert graph model to dictionary."""
        return {
            'name': self.name,
            'source_schema_name': self.source_schema_name,
            'node_labels': {name: label.to_dict() for name, label in self.node_labels.items()},
            'relationship_types': {name: rel.to_dict() for name, rel in self.relationship_types.items()},
            'node_label_count': len(self.node_labels),
            'relationship_type_count': len(self.relationship_types)
        }
    
    def get_cypher_schema(self) -> str:
        """Generate Cypher statements to represent the schema."""
        statements = []
        
        # Node constraints
        for label in self.node_labels.values():
            if label.primary_key:
                statements.append(
                    f"CREATE CONSTRAINT {label.name}_unique_{label.primary_key} "
                    f"IF NOT EXISTS FOR (n:{label.name}) "
                    f"REQUIRE n.{label.primary_key} IS UNIQUE"
                )
        
        # Indexes
        for label in self.node_labels.values():
            for index in label.indexes:
                statements.append(
                    f"CREATE INDEX {label.name}_{index}_index "
                    f"IF NOT EXISTS FOR (n:{label.name}) ON (n.{index})"
                )
        
        return ";\n".join(statements)
