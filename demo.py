"""
RDBMS to Graph Migration - Quick Demo
Demonstrates the system capabilities without requiring live database connections.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.models.schema_model import DatabaseSchema, Table, Column, ForeignKey, ColumnType
from src.models.conceptual_model import ConceptualModel, ConceptualEntity, ConceptualRelationship, EntityType, RelationshipCardinality, RelationshipSemantics
from src.analyzers.semantic_enricher import SemanticEnricher
from src.transformers.graph_transformer import GraphTransformer


def print_header(title):
    """Print formatted header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def create_sample_schema():
    """Create a sample database schema for demonstration"""
    
    print("📊 Creating sample university database schema...")
    
    db_schema = DatabaseSchema(database_name="university_db", database_type="mysql")
    
    # Students table
    students = Table(name="students", row_count=500, columns=[
        Column("student_id", "INTEGER"),
        Column("first_name", "VARCHAR", max_length=50),
        Column("last_name", "VARCHAR", max_length=50),
        Column("email", "VARCHAR", max_length=100),
        Column("enrollment_date", "DATE")
    ])
    db_schema.add_table(students)
    
    # Courses table
    courses = Table(name="courses", row_count=100, columns=[
        Column("course_id", "INTEGER"),
        Column("course_name", "VARCHAR", max_length=100),
        Column("credits", "INTEGER"),
        Column("department_id", "INTEGER")
    ])
    db_schema.add_table(courses)
    
    # Departments table
    departments = Table(name="departments", row_count=20, columns=[
        Column("department_id", "INTEGER"),
        Column("department_name", "VARCHAR", max_length=100),
        Column("building", "VARCHAR", max_length=50)
    ])
    db_schema.add_table(departments)
    
    # Enrollments junction table
    enrollments = Table(name="enrollments", row_count=2000, columns=[
        Column("student_id", "INTEGER"),
        Column("course_id", "INTEGER"),
        Column("enrollment_date", "DATE"),
        Column("grade", "VARCHAR", max_length=2)
    ])
    db_schema.add_table(enrollments)
    
    # Professors table
    professors = Table(name="professors", row_count=50, columns=[
        Column("professor_id", "INTEGER"),
        Column("first_name", "VARCHAR", max_length=50),
        Column("last_name", "VARCHAR", max_length=50),
        Column("department_id", "INTEGER"),
        Column("hire_date", "DATE")
    ])
    db_schema.add_table(professors)
    
    # Add foreign keys
    courses.foreign_keys.append(ForeignKey(
        name="fk_courses_department",
        column="department_id",
        referenced_table="departments",
        referenced_column="department_id"
    ))
    
    enrollments.foreign_keys.append(ForeignKey(
        name="fk_enrollments_student",
        column="student_id",
        referenced_table="students",
        referenced_column="student_id"
    ))
    
    enrollments.foreign_keys.append(ForeignKey(
        name="fk_enrollments_course",
        column="course_id",
        referenced_table="courses",
        referenced_column="course_id"
    ))
    
    professors.foreign_keys.append(ForeignKey(
        name="fk_professors_department",
        column="department_id",
        referenced_table="departments",
        referenced_column="department_id"
    ))
    
    print(f"✓ Created schema with {len(db_schema.tables)} tables")
    for table_name, table in db_schema.tables.items():
        print(f"  • {table_name}: {len(table.columns)} columns, {table.row_count} rows")
    
    return db_schema


def demonstrate_semantic_enrichment(db_schema):
    """Demonstrate semantic enrichment capabilities"""
    
    print_header("PHASE 1: Semantic Enrichment (S→C Transformation)")
    
    print("🧠 Applying DBRE techniques...")
    print("  • Detecting inheritance hierarchies")
    print("  • Inferring relationship cardinality")
    print("  • Identifying weak entities")
    print("  • Detecting aggregations")
    print("  • Generating semantic relationship names")
    
    enricher = SemanticEnricher(db_schema)
    conceptual_model = enricher.enrich()
    
    print(f"\n✓ Enrichment complete!")
    print(f"\nConceptual Model Statistics:")
    print(f"  • Entities: {len(conceptual_model.entities)}")
    print(f"  • Relationships: {len(conceptual_model.relationships)}")
    print(f"  • Inheritance Hierarchies: {len(conceptual_model.inheritance_hierarchies)}")
    
    print(f"\n📋 Entities:")
    for entity_name, entity in conceptual_model.entities.items():
        entity_type_str = entity.entity_type.value if entity.entity_type else "Strong"
        print(f"  • {entity_name} ({entity_type_str})")
        if entity.attributes:
            attrs = entity.attributes if isinstance(entity.attributes, list) else list(entity.attributes.keys())
            print(f"    Attributes: {', '.join(attrs[:5])}")
    
    print(f"\n🔗 Relationships:")
    for rel in conceptual_model.relationships:
        card_str = rel.cardinality.value if rel.cardinality else "unknown"
        sem_str = f" ({rel.semantics.value})" if rel.semantics != RelationshipSemantics.ASSOCIATION else ""
        print(f"  • {rel.source_entity} → {rel.target_entity}")
        print(f"    Name: {rel.name}, Cardinality: {card_str}{sem_str}")
    
    return conceptual_model


def demonstrate_graph_transformation(conceptual_model):
    """Demonstrate graph transformation"""
    
    print_header("PHASE 2: Graph Transformation (C→T)")
    
    print("🔄 Transforming conceptual model to property graph...")
    
    transformer = GraphTransformer(conceptual_model=conceptual_model)
    graph_model = transformer.transform()
    
    print(f"\n✓ Transformation complete!")
    print(f"\nGraph Model Statistics:")
    print(f"  • Node Types: {len(graph_model.node_labels)}")
    print(f"  • Edge Types: {len(graph_model.relationship_types)}")
    
    print(f"\n🔵 Node Types:")
    for node_name, node_type in graph_model.node_labels.items():
        props_preview = ', '.join([p.name for p in node_type.properties[:4]])
        if len(node_type.properties) > 4:
            props_preview += ", ..."
        print(f"  • {node_type.label}")
        print(f"    Properties: {props_preview}")
    
    print(f"\n➡️  Edge Types:")
    for rel_key, edge_type in graph_model.relationship_types.items():
        props_str = f" ({len(edge_type.properties)} properties)" if edge_type.properties else ""
        print(f"  • {edge_type.from_label} -[{edge_type.name}]-> {edge_type.to_label}{props_str}")
    
    return graph_model


def display_cypher_queries(graph_model):
    """Display sample Cypher queries"""
    
    print_header("Sample Cypher Queries for Neo4j")
    
    print("📝 Node creation query:")
    if graph_model.node_labels:
        node_type = list(graph_model.node_labels.values())[0]
        props = ', '.join([f"{p.name}: ${p.name}" for p in node_type.properties[:3]])
        print(f"  CREATE (n:{node_type.label} {{{props}}})")
    
    print("\n📝 Relationship creation query:")
    if graph_model.relationship_types:
        edge_type = list(graph_model.relationship_types.values())[0]
        print(f"  MATCH (a:{edge_type.from_label}), (b:{edge_type.to_label})")
        print(f"  WHERE a.id = $from_id AND b.id = $to_id")
        print(f"  CREATE (a)-[:{edge_type.name}]->(b)")
    
    print("\n📝 Sample queries:")
    print("  // Find all students in a department")
    print("  MATCH (d:departments)<-[:BELONGS_TO]-(c:courses)<-[:ENROLLED_IN]-(s:students)")
    print("  WHERE d.department_name = 'Computer Science'")
    print("  RETURN s.first_name, s.last_name, c.course_name")
    
    print("\n  // Find professors and their courses")
    print("  MATCH (p:professors)-[:WORKS_IN]->(d:departments)<-[:BELONGS_TO]-(c:courses)")
    print("  RETURN p.first_name, p.last_name, collect(c.course_name) as courses")


def main():
    """Run the complete demonstration"""
    
    print_header("🚀 RDBMS to Graph Migration System - Demo")
    
    print("""
This demonstration shows the complete S→C→T (Source → Conceptual → Target) 
migration pipeline with semantic enrichment using DBRE techniques.

The system automatically:
  ✓ Analyzes relational schemas
  ✓ Detects inheritance hierarchies
  ✓ Infers relationship cardinality
  ✓ Identifies weak entities and aggregations
  ✓ Generates semantic relationship names
  ✓ Transforms to property graph model
  ✓ Generates optimized Cypher queries
""")
    
    try:
        # Create sample schema
        db_schema = create_sample_schema()
        
        # Demonstrate semantic enrichment
        conceptual_model = demonstrate_semantic_enrichment(db_schema)
        
        # Demonstrate graph transformation
        graph_model = demonstrate_graph_transformation(conceptual_model)
        
        # Display Cypher queries
        display_cypher_queries(graph_model)
        
        print_header("✅ Demo Complete!")
        
        print("""
Next Steps:
  1. Configure your actual database connections in config/migration_config.example.yml
  2. Run: python -m src.cli test-connection -c config.yml -t source
  3. Run: python -m src.cli analyze -c config.yml -o schema.json
  4. Run: python -m src.cli migrate-sct -c config.yml
  
For more examples, check the examples/ directory:
  • examples/simple_migration.py - Basic S→T migration
  • examples/sct_migration.py - Full S→C→T migration
  • examples/custom_transformation.py - Custom transformations
  
Documentation:
  • README.md - Complete project overview
  • docs/semantic_enrichment.md - S→C→T architecture details
  • docs/api_reference.md - API documentation
""")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
