"""
Semantic Enrichment Module

Implements Database Reverse Engineering (DBRE) techniques to infer
semantic information from relational schemas, as required by the
research paper's S→C→T architecture.

This module analyzes relational patterns to detect:
- Cardinality (1:1, 1:N, N:M)
- Inheritance hierarchies (IS-A relationships)
- Aggregation/Composition (PART-OF relationships)
- Weak entities
- Business-meaningful relationship names
"""

import logging
import re
from typing import List, Dict, Optional, Set, Tuple
from ..models.schema_model import DatabaseSchema, Table, ForeignKey
from ..models.conceptual_model import (
    ConceptualModel, ConceptualEntity, ConceptualRelationship,
    EntityType, RelationshipCardinality, RelationshipSemantics
)


class SemanticEnricher:
    """
    Enriches relational schema with semantic information using DBRE techniques.
    Implements the S→C transformation in the SCT architecture.
    """
    
    def __init__(self, db_schema: DatabaseSchema):
        """
        Initialize semantic enricher.
        
        Args:
            db_schema: Source relational database schema
        """
        self.db_schema = db_schema
        self.logger = logging.getLogger(self.__class__.__name__)
        self.conceptual_model = ConceptualModel(
            name=db_schema.database_name + "_conceptual",
            source_schema_name=db_schema.database_name
        )
    
    def enrich(self) -> ConceptualModel:
        """
        Perform complete semantic enrichment.
        
        Returns:
            Enriched conceptual model
        """
        self.logger.info("Starting semantic enrichment (S→C transformation)")
        
        # Phase 1: Detect inheritance hierarchies
        self._detect_inheritance_hierarchies()
        
        # Phase 2: Detect weak entities and aggregation
        self._detect_weak_entities_and_aggregation()
        
        # Phase 3: Infer cardinality for all relationships
        self._infer_relationship_cardinality()
        
        # Phase 4: Generate business-meaningful relationship names
        self._generate_relationship_names()
        
        # Phase 5: Create conceptual entities
        self._create_conceptual_entities()
        
        # Phase 6: Create conceptual relationships
        self._create_conceptual_relationships()
        
        self.logger.info(f"Semantic enrichment complete: {len(self.conceptual_model.entities)} entities, "
                        f"{len(self.conceptual_model.relationships)} relationships")
        
        return self.conceptual_model
    
    def _detect_inheritance_hierarchies(self) -> None:
        """
        Detect Class Table Inheritance pattern.
        Pattern: Subclass PK is also FK to superclass PK
        """
        self.logger.info("Detecting inheritance hierarchies...")
        
        for table in self.db_schema.tables.values():
            if not table.primary_key or not table.foreign_keys:
                continue
            
            pk_columns = set(table.primary_key.columns)
            
            # Check each FK
            for fk in table.foreign_keys:
                # Inheritance pattern: FK column is part of PK
                if fk.column in pk_columns:
                    referenced_table = self.db_schema.get_table(fk.referenced_table)
                    if referenced_table and referenced_table.primary_key:
                        ref_pk_columns = set(referenced_table.primary_key.columns)
                        
                        # If FK points to entire PK of referenced table
                        if {fk.referenced_column} == ref_pk_columns or fk.referenced_column in ref_pk_columns:
                            # This is inheritance!
                            self.logger.info(f"Detected inheritance: {table.name} IS-A {fk.referenced_table}")
                            
                            # Mark tables
                            table.is_subclass = True
                            table.superclass_table = fk.referenced_table
                            referenced_table.is_superclass = True
                            
                            # Mark FK
                            fk.is_inheritance = True
                            fk.relationship_name = f"IS_A_{fk.referenced_table.upper()}"
                            fk.cardinality = "1:1"
                            
                            # Track hierarchy
                            self._add_to_hierarchy(fk.referenced_table, table.name)
    
    def _add_to_hierarchy(self, superclass: str, subclass: str) -> None:
        """Add to inheritance hierarchy tracking."""
        # Find existing hierarchy or create new one
        for hierarchy in self.conceptual_model.inheritance_hierarchies:
            if superclass in hierarchy:
                hierarchy.append(subclass)
                return
        # New hierarchy
        self.conceptual_model.inheritance_hierarchies.append([superclass, subclass])
    
    def _detect_weak_entities_and_aggregation(self) -> None:
        """
        Detect weak entities through:
        - Mandatory FK (part of PK)
        - CASCADE delete rules
        - Mandatory participation (NOT NULL FK)
        """
        self.logger.info("Detecting weak entities and aggregation relationships...")
        
        for table in self.db_schema.tables.values():
            # Skip if already classified as inheritance
            if table.is_subclass:
                continue
            
            if not table.foreign_keys:
                continue
            
            for fk in table.foreign_keys:
                # Already classified as inheritance
                if fk.is_inheritance:
                    continue
                
                is_weak = False
                is_aggregation = False
                
                # Check 1: FK is part of PK (identifying relationship)
                if table.primary_key and fk.column in table.primary_key.columns:
                    is_weak = True
                    is_aggregation = True
                
                # Check 2: CASCADE delete (strong dependency)
                if fk.on_delete and 'CASCADE' in fk.on_delete.upper():
                    is_aggregation = True
                
                # Check 3: FK is NOT NULL (mandatory participation)
                fk_column = table.get_column(fk.column)
                if fk_column and not fk_column.is_nullable:
                    is_aggregation = True
                
                if is_weak:
                    self.logger.info(f"Detected weak entity: {table.name} depends on {fk.referenced_table}")
                    table.is_weak_entity = True
                    table.owner_table = fk.referenced_table
                    fk.is_weak_entity = True
                    fk.is_aggregation = True
                    
                    # Track weak entity group
                    if fk.referenced_table not in self.conceptual_model.weak_entity_groups:
                        self.conceptual_model.weak_entity_groups[fk.referenced_table] = []
                    self.conceptual_model.weak_entity_groups[fk.referenced_table].append(table.name)
                
                elif is_aggregation:
                    self.logger.info(f"Detected aggregation: {table.name} part-of {fk.referenced_table}")
                    fk.is_aggregation = True
    
    def _infer_relationship_cardinality(self) -> None:
        """
        Infer cardinality for each FK relationship.
        Rules:
        - 1:1 if FK is unique or part of unique index
        - 1:N if FK is not unique
        - N:M handled by junction tables separately
        """
        self.logger.info("Inferring relationship cardinality...")
        
        for table in self.db_schema.tables.values():
            for fk in table.foreign_keys:
                if fk.cardinality:  # Already set (e.g., inheritance)
                    continue
                
                # Check if FK column has unique constraint
                is_unique = False
                
                # Check indexes
                for index in table.indexes:
                    if index.is_unique and fk.column in index.columns:
                        if len(index.columns) == 1:  # Single column unique
                            is_unique = True
                            break
                
                # Check if FK is the entire PK (also makes it unique)
                if table.primary_key and len(table.primary_key.columns) == 1:
                    if fk.column == table.primary_key.columns[0]:
                        is_unique = True
                
                if is_unique:
                    fk.cardinality = "1:1"
                    self.logger.debug(f"{table.name}.{fk.column} → {fk.referenced_table}: 1:1")
                else:
                    fk.cardinality = "N:1"  # Many-to-one from source perspective
                    self.logger.debug(f"{table.name}.{fk.column} → {fk.referenced_table}: N:1")
    
    def _generate_relationship_names(self) -> None:
        """
        Generate business-meaningful relationship names from FK names or table names.
        Uses heuristics to create readable names like WORKS_IN, MANAGES, OWNS, etc.
        """
        self.logger.info("Generating business-meaningful relationship names...")
        
        # Common relationship verbs
        verbs = {
            'manager': 'MANAGES',
            'employee': 'EMPLOYS',
            'supervisor': 'SUPERVISES',
            'owner': 'OWNS',
            'creator': 'CREATES',
            'author': 'AUTHORED_BY',
            'user': 'USED_BY',
            'customer': 'PURCHASED_BY',
            'department': 'WORKS_IN',
            'company': 'WORKS_FOR',
            'category': 'BELONGS_TO',
            'parent': 'CHILD_OF',
            'project': 'ASSIGNED_TO'
        }
        
        for table in self.db_schema.tables.values():
            for fk in table.foreign_keys:
                if fk.relationship_name:  # Already set (e.g., inheritance)
                    continue
                
                # Try to infer from FK column name
                fk_lower = fk.column.lower().replace('_id', '').replace('id', '')
                ref_table_lower = fk.referenced_table.lower()
                
                # Check for verb patterns
                relationship_name = None
                for key, verb in verbs.items():
                    if key in fk_lower or key in ref_table_lower:
                        relationship_name = verb
                        break
                
                # Fallback: construct from table names
                if not relationship_name:
                    # Remove common prefixes/suffixes
                    clean_ref = fk.referenced_table.replace('tbl', '').replace('_', '').upper()
                    
                    if fk.is_aggregation:
                        relationship_name = f"PART_OF_{clean_ref}"
                    else:
                        relationship_name = f"HAS_{clean_ref}"
                
                fk.relationship_name = relationship_name
                self.logger.debug(f"Generated relationship name: {table.name} -{relationship_name}-> {fk.referenced_table}")
    
    def _create_conceptual_entities(self) -> None:
        """Create conceptual entities from enriched tables."""
        self.logger.info("Creating conceptual entities...")
        
        for table in self.db_schema.tables.values():
            # Skip junction tables
            if table.is_junction_table():
                continue
            
            # Determine entity type
            if table.is_weak_entity:
                entity_type = EntityType.WEAK
            else:
                entity_type = EntityType.STRONG
            
            # Extract attributes (non-FK columns)
            fk_columns = {fk.column for fk in table.foreign_keys if not fk.is_inheritance}
            attributes = [col.name for col in table.columns if col.name not in fk_columns]
            
            # Key attributes
            key_attributes = table.primary_key.columns if table.primary_key else []
            
            entity = ConceptualEntity(
                name=table.name,
                entity_type=entity_type,
                source_table=table.name,
                attributes=attributes,
                key_attributes=key_attributes,
                superclass=table.superclass_table if table.is_subclass else None,
                owner_entity=table.owner_table if table.is_weak_entity else None
            )
            
            # Add subclasses if superclass
            if table.is_superclass:
                for other_table in self.db_schema.tables.values():
                    if other_table.is_subclass and other_table.superclass_table == table.name:
                        entity.subclasses.append(other_table.name)
            
            self.conceptual_model.add_entity(entity)
    
    def _create_conceptual_relationships(self) -> None:
        """Create conceptual relationships from enriched FKs and junction tables."""
        self.logger.info("Creating conceptual relationships...")
        
        # Regular FK relationships
        for table in self.db_schema.tables.values():
            if table.is_junction_table():
                continue
            
            for fk in table.foreign_keys:
                # Determine semantics
                if fk.is_inheritance:
                    semantics = RelationshipSemantics.INHERITANCE
                elif fk.is_aggregation or fk.is_weak_entity:
                    # Strong ownership = composition
                    if fk.on_delete and 'CASCADE' in fk.on_delete.upper():
                        semantics = RelationshipSemantics.COMPOSITION
                    else:
                        semantics = RelationshipSemantics.AGGREGATION
                else:
                    semantics = RelationshipSemantics.ASSOCIATION
                
                # Convert cardinality string to enum
                cardinality = self._parse_cardinality(fk.cardinality or "N:1")
                
                # Check mandatory participation
                fk_column = table.get_column(fk.column)
                is_mandatory = fk_column and not fk_column.is_nullable
                
                relationship = ConceptualRelationship(
                    name=fk.relationship_name or f"REL_{table.name}_{fk.referenced_table}",
                    source_entity=table.name,
                    target_entity=fk.referenced_table,
                    cardinality=cardinality,
                    semantics=semantics,
                    source_foreign_key=fk.name,
                    is_mandatory_source=is_mandatory,
                    is_mandatory_target=False  # Would need reverse analysis
                )
                
                self.conceptual_model.add_relationship(relationship)
        
        # Junction table relationships (N:M)
        for junction_table in self.db_schema.get_junction_tables():
            if len(junction_table.foreign_keys) < 2:
                continue
            
            fk1, fk2 = junction_table.foreign_keys[0], junction_table.foreign_keys[1]
            
            # Create bidirectional N:M relationship
            # Extract relationship properties (non-FK columns)
            fk_columns = {fk.column for fk in junction_table.foreign_keys}
            rel_attributes = [col.name for col in junction_table.columns 
                            if col.name not in fk_columns]
            
            # Generate meaningful name from junction table
            junction_clean = junction_table.name.replace('_', ' ').title().replace(' ', '_')
            relationship_name = junction_clean.upper()
            
            relationship = ConceptualRelationship(
                name=relationship_name,
                source_entity=fk1.referenced_table,
                target_entity=fk2.referenced_table,
                cardinality=RelationshipCardinality.MANY_TO_MANY,
                semantics=RelationshipSemantics.ASSOCIATION,
                source_junction_table=junction_table.name,
                attributes=rel_attributes
            )
            
            self.conceptual_model.add_relationship(relationship)
    
    def _parse_cardinality(self, cardinality_str: str) -> RelationshipCardinality:
        """Parse cardinality string to enum."""
        if cardinality_str == "1:1":
            return RelationshipCardinality.ONE_TO_ONE
        elif cardinality_str == "1:N":
            return RelationshipCardinality.ONE_TO_MANY
        elif cardinality_str == "N:1":
            return RelationshipCardinality.MANY_TO_ONE
        elif cardinality_str == "N:M":
            return RelationshipCardinality.MANY_TO_MANY
        else:
            return RelationshipCardinality.MANY_TO_ONE  # Default
