"""
S→C→T Migration Example

Demonstrates the complete Source → Conceptual → Target transformation
with semantic enrichment using DBRE techniques.

This example shows:
1. Schema extraction from relational database (S)
2. Semantic enrichment to conceptual model (S→C)
3. Graph transformation (C→T)
4. Data migration to Neo4j

Requirements:
- MySQL database with sample schema
- Neo4j instance running
- Configuration file (see migration_config.example.yml)
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.connectors import MySQLConnector
from src.analyzers import SchemaAnalyzer, SemanticEnricher
from src.transformers import GraphTransformer
from src.loaders import Neo4jLoader
from src.extractors import DataExtractor
from src.models import RelationshipCardinality, RelationshipSemantics, EntityType


def print_section(title):
    """Print formatted section header"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def demonstrate_sct_architecture():
    """
    Complete demonstration of S→C→T architecture with semantic enrichment.
    """
    
    print_section("S→C→T MIGRATION DEMONSTRATION")
    
    # Configuration
    mysql_config = {
        'host': 'localhost',
        'port': 3306,
        'database': 'university_db',
        'username': 'root',
        'password': 'password'
    }
    
    neo4j_config = {
        'uri': 'bolt://localhost:7687',
        'username': 'neo4j',
        'password': 'password',
        'database': 'neo4j'
    }
    
    # ========================================================================
    # PHASE 1: Extract Schema from Source Database (S)
    # ========================================================================
    
    print_section("PHASE 1: Schema Extraction (S)")
    
    print("Connecting to MySQL database...")
    mysql_connector = MySQLConnector(**mysql_config)
    mysql_connector.connect()
    print("✓ Connected successfully\n")
    
    print("Analyzing relational schema...")
    schema_analyzer = SchemaAnalyzer(mysql_connector)
    db_schema = schema_analyzer.analyze()
    
    print(f"Schema Analysis Results:")
    print(f"  • Total tables: {len(db_schema.tables)}")
    print(f"  • Entity tables: {len(db_schema.get_entity_tables())}")
    print(f"  • Junction tables: {len(db_schema.get_junction_tables())}")
    print(f"  • Total foreign keys: {sum(len(t.foreign_keys) for t in db_schema.tables.values())}")
    
    print("\nSample Tables:")
    for table_name in list(db_schema.tables.keys())[:5]:
        table = db_schema.tables[table_name]
        print(f"  • {table_name} ({table.row_count:,} rows, {len(table.columns)} columns)")
    
    # ========================================================================
    # PHASE 2: Semantic Enrichment (S→C)
    # ========================================================================
    
    print_section("PHASE 2: Semantic Enrichment (S→C)")
    
    print("Applying DBRE techniques for semantic enrichment...")
    enricher = SemanticEnricher(db_schema)
    conceptual_model = enricher.enrich()
    print("✓ Enrichment complete\n")
    
    # Display enrichment results
    print(f"Conceptual Model Statistics:")
    print(f"  • Total entities: {len(conceptual_model.entities)}")
    print(f"  • Strong entities: {len(conceptual_model.get_strong_entities())}")
    print(f"  • Weak entities: {len(conceptual_model.get_weak_entities())}")
    print(f"  • Relationships: {len(conceptual_model.relationships)}")
    print(f"  • Inheritance hierarchies: {len(conceptual_model.inheritance_hierarchies)}")
    
    # Show entity type breakdown
    entity_types = {}
    for entity in conceptual_model.entities.values():
        entity_type = entity.entity_type.value
        entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
    
    print(f"\nEntity Type Breakdown:")
    for entity_type, count in entity_types.items():
        print(f"  • {entity_type}: {count}")
    
    # Show detected inheritance hierarchies
    if conceptual_model.inheritance_hierarchies:
        print(f"\n🔗 Detected Inheritance Hierarchies:")
        for idx, hierarchy in enumerate(conceptual_model.inheritance_hierarchies, 1):
            print(f"  {idx}. {' → '.join(hierarchy)}")
    
    # Show weak entity groups
    if conceptual_model.weak_entity_groups:
        print(f"\n🔗 Detected Weak Entity Groups:")
        for owner, weak_entities in conceptual_model.weak_entity_groups.items():
            print(f"  • {owner} owns: {', '.join(weak_entities)}")
    
    # Show relationship cardinality distribution
    cardinality_dist = {}
    for rel in conceptual_model.relationships:
        card = rel.cardinality.value
        cardinality_dist[card] = cardinality_dist.get(card, 0) + 1
    
    print(f"\nRelationship Cardinality Distribution:")
    for cardinality, count in cardinality_dist.items():
        print(f"  • {cardinality}: {count}")
    
    # Show relationship semantics distribution
    semantics_dist = {}
    for rel in conceptual_model.relationships:
        sem = rel.semantics.value
        semantics_dist[sem] = semantics_dist.get(sem, 0) + 1
    
    print(f"\nRelationship Semantics Distribution:")
    for semantics, count in semantics_dist.items():
        print(f"  • {semantics}: {count}")
    
    # Display sample enriched relationships
    print(f"\n🏷️  Sample Enriched Relationships:")
    for rel in list(conceptual_model.relationships)[:8]:
        card_symbol = rel.cardinality.value
        semantic_type = rel.semantics.value
        flags = []
        if rel.is_inheritance:
            flags.append("inheritance")
        if rel.is_aggregation:
            flags.append("aggregation")
        if rel.is_composition:
            flags.append("composition")
        flag_str = f" [{', '.join(flags)}]" if flags else ""
        print(f"  • {rel.source_entity} -{rel.name}[{card_symbol}, {semantic_type}]{flag_str}-> {rel.target_entity}")
    
    # ========================================================================
    # PHASE 3: Transform to Graph Model (C→T)
    # ========================================================================
    
    print_section("PHASE 3: Graph Transformation (C→T)")
    
    print("Transforming conceptual model to property graph...")
    transformer = GraphTransformer(db_schema=db_schema, conceptual_model=conceptual_model)
    graph_model = transformer.transform()
    print("✓ Transformation complete\n")
    
    print(f"Graph Model Statistics:")
    print(f"  • Node labels: {len(graph_model.node_labels)}")
    print(f"  • Relationship types: {len(graph_model.relationship_types)}")
    print(f"  • Total properties: {sum(len(nl.properties) for nl in graph_model.node_labels.values())}")
    
    print(f"\nSample Node Labels:")
    for label_name in list(graph_model.node_labels.keys())[:5]:
        node_label = graph_model.node_labels[label_name]
        print(f"  • {node_label.label} ({len(node_label.properties)} properties)")
    
    print(f"\nSample Relationship Types:")
    for rel_type_name in list(graph_model.relationship_types.keys())[:8]:
        rel_type = graph_model.relationship_types[rel_type_name]
        print(f"  • {rel_type.type}: {rel_type.from_label} → {rel_type.to_label}")
    
    # ========================================================================
    # PHASE 4: Load to Neo4j (Optional)
    # ========================================================================
    
    print_section("PHASE 4: Data Migration to Neo4j")
    
    print("Would you like to proceed with data migration to Neo4j? (y/n): ", end='')
    response = input().strip().lower()
    
    if response == 'y':
        print("\nConnecting to Neo4j...")
        neo4j_loader = Neo4jLoader(**neo4j_config)
        neo4j_loader.connect()
        print("✓ Connected successfully\n")
        
        print("Creating constraints and indexes...")
        neo4j_loader.create_constraints_and_indexes(graph_model)
        print("✓ Schema created\n")
        
        print("Migrating data...")
        batch_size = 1000
        extractor = DataExtractor(mysql_connector, batch_size)
        
        # Migrate nodes
        for table in db_schema.get_entity_tables():
            if table.row_count == 0:
                continue
            
            # Get corresponding node label
            node_label = None
            for label in graph_model.node_labels.values():
                if label.source_table == table.name:
                    node_label = label
                    break
            
            if not node_label:
                continue
            
            print(f"  • Migrating {table.name} → {node_label.label} ({table.row_count:,} rows)...")
            
            total_loaded = 0
            for batch in extractor.extract_table_data(table):
                nodes = []
                for row in batch:
                    properties = {k: v for k, v in row.items() if v is not None}
                    nodes.append(properties)
                
                count = neo4j_loader.load_nodes_batch(node_label.label, nodes)
                total_loaded += count
            
            print(f"    ✓ Loaded {total_loaded:,} nodes")
        
        # Migrate relationships
        print("\n  Migrating relationships...")
        for table in db_schema.tables.values():
            for fk in table.foreign_keys:
                # Find corresponding relationship type in graph model
                rel_type_name = fk.relationship_name if fk.relationship_name else f"FK_{table.name}_{fk.referenced_table}".upper()
                
                if rel_type_name not in graph_model.relationship_types:
                    continue
                
                rel_type = graph_model.relationship_types[rel_type_name]
                
                total_rels = 0
                for batch in extractor.extract_table_data(table):
                    relationships = []
                    for row in batch:
                        if row.get(fk.column) is not None:
                            from_id = row.get(table.primary_key.columns[0] if table.primary_key else 'id')
                            to_id = row.get(fk.column)
                            if from_id and to_id:
                                relationships.append({
                                    'from_id': from_id,
                                    'to_id': to_id,
                                    'properties': {}
                                })
                    
                    if relationships:
                        count = neo4j_loader.load_relationships_batch(
                            rel_type.type, rel_type.from_label, rel_type.to_label, relationships
                        )
                        total_rels += count
                
                if total_rels > 0:
                    print(f"    • {rel_type.type}: {total_rels:,} relationships")
        
        neo4j_loader.close()
        print("\n✓ Data migration complete!")
    else:
        print("\nSkipping data migration.")
    
    # ========================================================================
    # Export Conceptual Model
    # ========================================================================
    
    print_section("Export Results")
    
    output_file = Path(__file__).parent / 'conceptual_model_output.json'
    with open(output_file, 'w') as f:
        json.dump(conceptual_model.to_dict(), f, indent=2)
    
    print(f"✓ Conceptual model exported to: {output_file}")
    
    # Cleanup
    mysql_connector.disconnect()
    
    print_section("S→C→T MIGRATION COMPLETE")
    
    print("Summary:")
    print(f"  • Source: {len(db_schema.tables)} relational tables")
    print(f"  • Conceptual: {len(conceptual_model.entities)} entities, {len(conceptual_model.relationships)} relationships")
    print(f"  • Target: {len(graph_model.node_labels)} node types, {len(graph_model.relationship_types)} relationship types")
    print(f"  • Semantic features: {len(conceptual_model.inheritance_hierarchies)} hierarchies, {len(conceptual_model.get_weak_entities())} weak entities")
    print("\n✅ All phases completed successfully!")


def demonstrate_comparison():
    """
    Compare S→T (direct) vs S→C→T (enriched) transformations.
    """
    
    print_section("COMPARISON: S→T vs S→C→T")
    
    # Configuration (reuse from above)
    mysql_config = {
        'host': 'localhost',
        'port': 3306,
        'database': 'university_db',
        'username': 'root',
        'password': 'password'
    }
    
    print("Connecting to database...")
    mysql_connector = MySQLConnector(**mysql_config)
    mysql_connector.connect()
    
    print("Analyzing schema...")
    schema_analyzer = SchemaAnalyzer(mysql_connector)
    db_schema = schema_analyzer.analyze()
    
    # Method 1: Direct S→T transformation
    print("\n" + "="*70)
    print("METHOD 1: Direct S→T Transformation (No Enrichment)")
    print("="*70 + "\n")
    
    transformer_st = GraphTransformer(db_schema=db_schema)
    graph_model_st = transformer_st.transform()
    
    print(f"Results:")
    print(f"  • Node labels: {len(graph_model_st.node_labels)}")
    print(f"  • Relationship types: {len(graph_model_st.relationship_types)}")
    
    print(f"\nSample relationships (generic names):")
    for rel_name in list(graph_model_st.relationship_types.keys())[:5]:
        rel = graph_model_st.relationship_types[rel_name]
        print(f"  • {rel.type}: {rel.from_label} → {rel.to_label}")
    
    # Method 2: S→C→T with enrichment
    print("\n" + "="*70)
    print("METHOD 2: S→C→T Transformation (With Enrichment)")
    print("="*70 + "\n")
    
    enricher = SemanticEnricher(db_schema)
    conceptual_model = enricher.enrich()
    
    transformer_sct = GraphTransformer(db_schema=db_schema, conceptual_model=conceptual_model)
    graph_model_sct = transformer_sct.transform()
    
    print(f"Results:")
    print(f"  • Node labels: {len(graph_model_sct.node_labels)}")
    print(f"  • Relationship types: {len(graph_model_sct.relationship_types)}")
    print(f"  • Semantic relationships: {len(conceptual_model.relationships)}")
    print(f"  • Inheritance hierarchies: {len(conceptual_model.inheritance_hierarchies)}")
    
    print(f"\nSample relationships (semantic names):")
    for rel in list(conceptual_model.relationships)[:5]:
        print(f"  • {rel.name} [{rel.cardinality.value}, {rel.semantics.value}]: {rel.source_entity} → {rel.target_entity}")
    
    # Comparison
    print("\n" + "="*70)
    print("COMPARISON SUMMARY")
    print("="*70 + "\n")
    
    print(f"Feature                        | S→T (Direct) | S→C→T (Enriched)")
    print(f"{'-'*70}")
    print(f"Semantic relationship names    | ❌ No        | ✅ Yes")
    print(f"Cardinality inference          | ❌ No        | ✅ Yes")
    print(f"Inheritance detection          | ❌ No        | ✅ Yes")
    print(f"Weak entity identification     | ❌ No        | ✅ Yes")
    print(f"Aggregation/Composition        | ❌ No        | ✅ Yes")
    print(f"Business-meaningful names      | ❌ No        | ✅ Yes")
    
    mysql_connector.disconnect()
    print("\n✅ Comparison complete!")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='S→C→T Migration Demonstration')
    parser.add_argument('--mode', choices=['full', 'compare'], default='full',
                       help='Demonstration mode: full S→C→T or comparison')
    
    args = parser.parse_args()
    
    try:
        if args.mode == 'full':
            demonstrate_sct_architecture()
        elif args.mode == 'compare':
            demonstrate_comparison()
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
