"""
Conceptual Model Classes

Represents the intermediate conceptual schema (C) in the S→C→T architecture.
This layer enriches the relational schema with semantic information before 
graph transformation, as mandated by the research paper.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set
from enum import Enum


class EntityType(Enum):
    """Types of entities in conceptual model."""
    STRONG = "STRONG"  # Independent entity
    WEAK = "WEAK"  # Dependent on another entity
    ASSOCIATIVE = "ASSOCIATIVE"  # Junction/bridge entity


class RelationshipCardinality(Enum):
    """Relationship cardinality types."""
    ONE_TO_ONE = "1:1"
    ONE_TO_MANY = "1:N"
    MANY_TO_ONE = "N:1"
    MANY_TO_MANY = "N:M"


class RelationshipSemantics(Enum):
    """Semantic types of relationships."""
    ASSOCIATION = "ASSOCIATION"  # Regular relationship
    INHERITANCE = "INHERITANCE"  # IS-A relationship
    AGGREGATION = "AGGREGATION"  # HAS-A (weak ownership)
    COMPOSITION = "COMPOSITION"  # PART-OF (strong ownership)


@dataclass
class ConceptualEntity:
    """
    Represents an entity in the conceptual model.
    Enriched from relational table with semantic information.
    """
    name: str
    entity_type: EntityType
    source_table: str
    attributes: List[str] = field(default_factory=list)
    key_attributes: List[str] = field(default_factory=list)
    # Inheritance hierarchy
    superclass: Optional[str] = None
    subclasses: List[str] = field(default_factory=list)
    # Weak entity properties
    owner_entity: Optional[str] = None
    discriminator: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'entity_type': self.entity_type.value,
            'source_table': self.source_table,
            'attributes': self.attributes,
            'key_attributes': self.key_attributes,
            'superclass': self.superclass,
            'subclasses': self.subclasses,
            'owner_entity': self.owner_entity,
            'discriminator': self.discriminator
        }


@dataclass
class ConceptualRelationship:
    """
    Represents a relationship in the conceptual model.
    Enriched with cardinality and semantic meaning.
    """
    name: str  # Business-meaningful name
    source_entity: str
    target_entity: str
    cardinality: RelationshipCardinality
    semantics: RelationshipSemantics
    # Source information
    source_foreign_key: Optional[str] = None
    source_junction_table: Optional[str] = None
    # Relationship properties
    attributes: List[str] = field(default_factory=list)
    is_mandatory_source: bool = False
    is_mandatory_target: bool = False
    participation_note: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'source_entity': self.source_entity,
            'target_entity': self.target_entity,
            'cardinality': self.cardinality.value,
            'semantics': self.semantics.value,
            'source_foreign_key': self.source_foreign_key,
            'source_junction_table': self.source_junction_table,
            'attributes': self.attributes,
            'is_mandatory_source': self.is_mandatory_source,
            'is_mandatory_target': self.is_mandatory_target,
            'participation_note': self.participation_note
        }


@dataclass
class ConceptualModel:
    """
    Represents the complete conceptual schema (C).
    Intermediate layer between relational schema (S) and graph model (T).
    """
    name: str
    source_schema_name: str
    entities: Dict[str, ConceptualEntity] = field(default_factory=dict)
    relationships: List[ConceptualRelationship] = field(default_factory=list)
    # Metadata about enrichment
    inheritance_hierarchies: List[List[str]] = field(default_factory=list)
    weak_entity_groups: Dict[str, List[str]] = field(default_factory=dict)
    
    def add_entity(self, entity: ConceptualEntity) -> None:
        """Add an entity to the conceptual model."""
        self.entities[entity.name] = entity
    
    def add_relationship(self, relationship: ConceptualRelationship) -> None:
        """Add a relationship to the conceptual model."""
        self.relationships.append(relationship)
    
    def get_entity(self, name: str) -> Optional[ConceptualEntity]:
        """Get entity by name."""
        return self.entities.get(name)
    
    def get_strong_entities(self) -> List[ConceptualEntity]:
        """Get all strong (independent) entities."""
        return [e for e in self.entities.values() if e.entity_type == EntityType.STRONG]
    
    def get_weak_entities(self) -> List[ConceptualEntity]:
        """Get all weak (dependent) entities."""
        return [e for e in self.entities.values() if e.entity_type == EntityType.WEAK]
    
    def get_inheritance_relationships(self) -> List[ConceptualRelationship]:
        """Get all IS-A relationships."""
        return [r for r in self.relationships 
                if r.semantics == RelationshipSemantics.INHERITANCE]
    
    def get_aggregation_relationships(self) -> List[ConceptualRelationship]:
        """Get all aggregation/composition relationships."""
        return [r for r in self.relationships 
                if r.semantics in (RelationshipSemantics.AGGREGATION, 
                                   RelationshipSemantics.COMPOSITION)]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'source_schema_name': self.source_schema_name,
            'entities': {name: entity.to_dict() 
                        for name, entity in self.entities.items()},
            'relationships': [rel.to_dict() for rel in self.relationships],
            'inheritance_hierarchies': self.inheritance_hierarchies,
            'weak_entity_groups': self.weak_entity_groups,
            'statistics': {
                'total_entities': len(self.entities),
                'strong_entities': len(self.get_strong_entities()),
                'weak_entities': len(self.get_weak_entities()),
                'total_relationships': len(self.relationships),
                'inheritance_relationships': len(self.get_inheritance_relationships()),
                'aggregation_relationships': len(self.get_aggregation_relationships())
            }
        }
