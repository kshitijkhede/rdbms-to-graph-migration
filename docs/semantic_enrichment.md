# Semantic Enrichment in RDBMS-to-Graph Migration

## Overview

This document describes the **semantic enrichment layer** implemented in the RDBMS-to-Graph migration system. The system follows the **S→C→T (Source→Conceptual→Target)** architecture mandated by academic research standards, where semantic information lost during the original database design is recovered through Database Reverse Engineering (DBRE) techniques.

## Architecture: S→C→T Transformation

### Traditional Approach (S→T)
```
Relational Schema (S) → Graph Model (T)
```
**Limitation**: Direct mapping loses semantic information (inheritance, cardinality, aggregation, business-meaningful names)

### Enhanced Approach (S→C→T)
```
Relational Schema (S) → Conceptual Model (C) → Graph Model (T)
```
**Advantage**: Intermediate conceptual layer preserves and enriches semantic information

## Conceptual Model Layer

### Core Components

#### 1. ConceptualEntity
Represents an entity in the conceptual schema with enriched semantic properties.

```python
@dataclass
class ConceptualEntity:
    name: str
    attributes: List[ConceptualAttribute]
    entity_type: EntityType
    primary_key: List[str]
    
    # Semantic enrichment properties
    is_weak_entity: bool = False
    owner_entity: Optional[str] = None
    is_superclass: bool = False
    is_subclass: bool = False
    superclass_entity: Optional[str] = None
```

**Entity Types:**
- `STRONG`: Independent entity with its own primary key
- `WEAK`: Entity dependent on another (owner) entity
- `SUPERCLASS`: Parent in an inheritance hierarchy
- `SUBCLASS`: Child in an inheritance hierarchy
- `ASSOCIATIVE`: Junction entity representing M:N relationship

#### 2. ConceptualRelationship
Represents a relationship between entities with cardinality and semantic information.

```python
@dataclass
class ConceptualRelationship:
    name: str
    source_entity: str
    target_entity: str
    cardinality: RelationshipCardinality
    semantics: RelationshipSemantics
    attributes: List[ConceptualAttribute]
    
    # Semantic flags
    is_inheritance: bool = False
    is_aggregation: bool = False
    is_composition: bool = False
```

**Relationship Cardinality:**
- `ONE_TO_ONE`: 1:1 relationship
- `ONE_TO_MANY`: 1:N relationship
- `MANY_TO_ONE`: N:1 relationship
- `MANY_TO_MANY`: M:N relationship

**Relationship Semantics:**
- `ASSOCIATION`: General relationship between entities
- `AGGREGATION`: "Has-a" relationship with independent lifecycles
- `COMPOSITION`: Strong "Has-a" with dependent lifecycle
- `INHERITANCE`: "Is-a" relationship (generalization/specialization)
- `DEPENDENCY`: Weak dependency relationship

## Semantic Enrichment Techniques

### 1. Inheritance Hierarchy Detection

**Algorithm**: Analyzes naming patterns and foreign key structures to identify superclass-subclass relationships.

**Detection Patterns:**
1. **Shared Primary Key Pattern**: 
   - Subclass table has FK to superclass that is also its PK
   - Example: `Employee(emp_id) ← Manager(emp_id FK PK)`

2. **Naming Convention Pattern**:
   - Table names suggest specialization (e.g., `Person` → `Student`, `Employee`)
   - Prefix/suffix matching (e.g., `*_Type` tables)

3. **Column Pattern Matching**:
   - Subclasses share common column prefixes with superclass
   - Type discriminator columns (e.g., `person_type`, `employee_category`)

**Example Detection:**
```python
# Database Schema
Person(person_id, name, email)
Employee(person_id FK PK, department, hire_date)
Customer(person_id FK PK, customer_since, loyalty_points)

# Detected Hierarchy
Person (Superclass)
  ├── Employee (Subclass)
  └── Customer (Subclass)
```

**Inference Rules:**
```python
IF table T has FK to table S
AND FK columns = T.primary_key
AND similar_naming(T.name, S.name)
THEN T is_subclass_of S
```

### 2. Weak Entity Detection

**Algorithm**: Identifies entities that cannot exist independently and require an owner entity.

**Detection Criteria:**
1. **Composite Primary Key Including FK**: PK contains foreign key column(s)
2. **Naming Dependency**: Table name suggests dependence (e.g., `Order_Items`, `Employee_Dependents`)
3. **Existence Dependency**: All FK columns are NOT NULL and part of PK

**Example Detection:**
```python
# Database Schema
Order(order_id, customer_id, order_date)
Order_Item(order_id FK PK, item_number PK, product_id, quantity)

# Detection Result
Order_Item is WEAK_ENTITY
  - Owner: Order
  - Identifying relationship: Contains
  - Partial key: item_number
```

**Inference Rules:**
```python
IF table T has composite PK
AND PK contains FK to table O
AND FK is NOT NULL
AND T.name contains O.name OR shared_prefix(T.name, O.name)
THEN T is weak_entity owned_by O
```

### 3. Aggregation Detection

**Algorithm**: Distinguishes between composition and aggregation relationships.

**Detection Criteria:**

**Composition** (Strong ownership):
1. Child table has FK with CASCADE DELETE
2. FK is NOT NULL
3. Naming suggests containment (`*_Detail`, `*_Line`, `*_Item`)

**Aggregation** (Weak ownership):
1. Child table has FK without CASCADE DELETE
2. FK may be NULL
3. Naming suggests membership (`*_Member`, `*_Assignment`)

**Example:**
```python
# Composition
Order → Order_Item (CASCADE DELETE, NOT NULL)
  Relationship type: COMPOSITION
  
# Aggregation  
Department ← Employee (NO CASCADE, NULLABLE)
  Relationship type: AGGREGATION
```

### 4. Cardinality Inference

**Algorithm**: Determines relationship cardinality from foreign key constraints and data statistics.

**Detection Rules:**

#### One-to-One (1:1)
```python
IF FK has UNIQUE constraint
AND FK is NOT NULL
THEN cardinality = ONE_TO_ONE
```

**Example:**
```sql
User(user_id)
UserProfile(user_id FK UNIQUE NOT NULL)
→ User -[HAS_PROFILE:1:1]-> UserProfile
```

#### One-to-Many (1:N)
```python
IF FK has no UNIQUE constraint
AND referenced table has no FK back to source
THEN cardinality = ONE_TO_MANY
```

**Example:**
```sql
Department(dept_id)
Employee(emp_id, dept_id FK)
→ Department -[HAS_EMPLOYEES:1:N]-> Employee
```

#### Many-to-One (N:1)
```python
# Reverse of 1:N from target perspective
IF target has 1:N to source
THEN source has N:1 to target
```

#### Many-to-Many (M:N)
```python
IF junction_table exists
AND has exactly 2 FKs
AND both FKs are part of composite PK
THEN relationship is MANY_TO_MANY
```

**Example:**
```sql
Student(student_id)
Student_Course(student_id FK PK, course_id FK PK)
Course(course_id)
→ Student -[ENROLLED_IN:M:N]-> Course
```

### 5. Business-Meaningful Relationship Naming

**Algorithm**: Generates semantic relationship names instead of generic FK names.

**Naming Strategies:**

#### Strategy 1: Verb Extraction from Column Names
```python
# FK column: manager_id → "MANAGES"
# FK column: author_id → "AUTHORED_BY"
# FK column: parent_category_id → "HAS_PARENT"

Pattern: {verb}_id → {VERB}
```

#### Strategy 2: Table Name Analysis
```python
# Order → Customer: "PLACED_BY"
# Employee → Department: "WORKS_IN"
# Product → Category: "BELONGS_TO"

Semantic mapping based on domain knowledge
```

#### Strategy 3: Junction Table Semantics
```python
# Student_Course → "ENROLLED_IN"
# Author_Book → "WROTE"
# Doctor_Patient → "TREATS"

Extract verb from junction table name or context
```

#### Strategy 4: Cardinality-Based Naming
```python
# 1:N: Parent → Child = "HAS" or "OWNS"
# N:1: Child → Parent = "BELONGS_TO" or "PART_OF"
# M:N: Entity1 ↔ Entity2 = "ASSOCIATED_WITH"
```

**Example Transformations:**
```python
# Before (Generic)
Employee.department_id FK → Department
Relationship: FK_EMPLOYEE_DEPARTMENT

# After (Semantic)
Employee -[WORKS_IN:N:1]-> Department
```

## Usage Examples

### Command-Line Interface

#### 1. Semantic Enrichment Only (S→C)
```bash
python -m src.cli enrich \
    --config config/migration_config.yml \
    --output conceptual_model.json
```

**Output:**
```
🧠 Performing semantic enrichment (S→C)...
📊 Phase 1: Extracting relational schema...
   ✓ Found 15 tables
   
🔍 Phase 2: Semantic enrichment...
📈 Semantic Enrichment Results:
   ✓ Entities: 15
   ✓ Strong Entities: 12
   ✓ Weak Entities: 3
   ✓ Relationships: 28
   ✓ Inheritance Hierarchies: 2
   ✓ Inheritance Relationships: 4
   ✓ Aggregation Relationships: 8
   
🔗 Detected Inheritance Hierarchies:
   1. Person → Employee → Manager
   2. Product → DigitalProduct
   
🔗 Detected Weak Entity Groups:
   Order owns: Order_Item
   Employee owns: Employee_Dependent
   
🏷️ Sample Enriched Relationships:
   • Order -CONTAINS[1:N, COMPOSITION]-> Order_Item
   • Employee -WORKS_IN[N:1, AGGREGATION]-> Department
   • Student -ENROLLED_IN[M:N, ASSOCIATION]-> Course
```

#### 2. Full S→C→T Migration
```bash
python -m src.cli migrate-sct \
    --config config/migration_config.yml
```

**Output:**
```
🚀 Starting S→C→T migration with semantic enrichment...
📊 Phase 1: Extracting relational schema (S)...
   ✓ Extracted 15 tables
   
🧠 Phase 2: Semantic enrichment (S→C)...
   ✓ Created 15 enriched entities
   ✓ Created 28 semantic relationships
   ✓ Detected 2 inheritance hierarchies
   
🔄 Phase 3: Transforming to graph model (C→T)...
   ✓ Created 15 node labels
   ✓ Created 28 relationship types
   
📤 Phase 4: Migrating data...
  • Order → Order (5,234 rows)
    ✓ Loaded 5,234 nodes
  • Order_Item → OrderItem (18,921 rows)
    ✓ Loaded 18,921 nodes
    
🔗 Migrating relationships...
    • Order -CONTAINS-> OrderItem: 18,921 relationships
    • Employee -WORKS_IN-> Department: 450 relationships
    
✅ S→C→T migration complete in 2m 34s!
```

### Programmatic Usage

```python
from src.analyzers import SchemaAnalyzer, SemanticEnricher
from src.transformers import GraphTransformer
from src.connectors import MySQLConnector

# Connect to source database
connector = MySQLConnector(host='localhost', database='mydb', 
                          username='user', password='pass')
connector.connect()

# Phase 1: Extract schema (S)
analyzer = SchemaAnalyzer(connector)
db_schema = analyzer.analyze()

# Phase 2: Semantic enrichment (S→C)
enricher = SemanticEnricher(db_schema)
conceptual_model = enricher.enrich()

# Inspect results
print(f"Entities: {len(conceptual_model.entities)}")
print(f"Strong entities: {len(conceptual_model.get_strong_entities())}")
print(f"Weak entities: {len(conceptual_model.get_weak_entities())}")

# Show inheritance hierarchies
for hierarchy in conceptual_model.inheritance_hierarchies:
    print(f"Hierarchy: {' → '.join(hierarchy)}")

# Phase 3: Transform to graph (C→T)
transformer = GraphTransformer(db_schema=db_schema, 
                              conceptual_model=conceptual_model)
graph_model = transformer.transform()

# Export conceptual model
import json
with open('conceptual_model.json', 'w') as f:
    json.dump(conceptual_model.to_dict(), f, indent=2)
```

## Implementation Details

### SemanticEnricher Class

**Location:** `src/analyzers/semantic_enricher.py`

**Key Methods:**

```python
class SemanticEnricher:
    def enrich(self) -> ConceptualModel:
        """Main enrichment pipeline"""
        self._detect_inheritance_hierarchies()
        self._detect_weak_entities_and_aggregation()
        self._build_conceptual_entities()
        self._build_conceptual_relationships()
        return self.conceptual_model
    
    def _detect_inheritance_hierarchies(self):
        """Detect superclass-subclass relationships"""
        # Pattern matching on FKs and naming
        
    def _detect_weak_entities_and_aggregation(self):
        """Identify weak entities and aggregation types"""
        # Composite PK analysis
        
    def _infer_relationship_cardinality(self, fk: ForeignKey) -> str:
        """Determine 1:1, 1:N, N:1, or M:N cardinality"""
        # Constraint analysis
        
    def _generate_relationship_name(self, source_table, target_table, fk) -> str:
        """Create business-meaningful relationship name"""
        # Semantic naming strategies
```

### GraphTransformer Enhancement

**Location:** `src/transformers/graph_transformer.py`

**Dual-Mode Support:**

```python
class GraphTransformer:
    def __init__(self, db_schema: DatabaseSchema, 
                 conceptual_model: Optional[ConceptualModel] = None):
        self.db_schema = db_schema
        self.conceptual_model = conceptual_model
    
    def transform(self) -> GraphModel:
        """Transform to graph model"""
        if self.conceptual_model:
            return self._transform_from_conceptual()  # C→T
        else:
            return self._transform_from_schema()      # S→T
```

## Benefits of Semantic Enrichment

### 1. Improved Graph Semantics
- **Before:** Generic `FK_ORDER_CUSTOMER` relationships
- **After:** Meaningful `PLACED_BY[N:1]` relationships

### 2. Preserved Domain Knowledge
- Inheritance hierarchies explicitly modeled
- Weak entity dependencies captured
- Aggregation vs composition distinguished

### 3. Better Query Semantics
```cypher
// Before (Generic)
MATCH (o:Order)-[r:FK_ORDER_CUSTOMER]->(c:Customer)
RETURN o, c

// After (Semantic)
MATCH (o:Order)-[r:PLACED_BY]->(c:Customer)
RETURN o, c
```

### 4. Enhanced Data Modeling
- Superclass/subclass hierarchies → Node labels with inheritance
- Weak entities → Proper identifying relationships
- M:N with attributes → Explicit relationship properties

## Configuration

### Enabling Semantic Enrichment

**In migration_config.yml:**
```yaml
source:
  type: mysql
  host: localhost
  database: mydb
  username: user
  password: pass

target:
  uri: bolt://localhost:7687
  username: neo4j
  password: password

migration:
  batch_size: 1000
  semantic_enrichment: true  # Enable S→C→T architecture
  preserve_inheritance: true
  infer_cardinality: true
  generate_semantic_names: true
```

## Testing Semantic Enrichment

### Unit Tests

**Location:** `tests/unit/test_semantic_enricher.py`

```python
def test_inheritance_detection():
    # Test superclass-subclass detection
    
def test_weak_entity_detection():
    # Test weak entity identification
    
def test_cardinality_inference():
    # Test 1:1, 1:N, M:N detection
    
def test_relationship_naming():
    # Test semantic name generation
```

### Integration Tests

**Location:** `tests/integration/test_sct_migration.py`

```python
def test_full_sct_pipeline():
    # Test complete S→C→T transformation
```

## References

### Academic Foundations
1. **Database Reverse Engineering (DBRE)**: Techniques for recovering semantic information from physical schemas
2. **ER Model Recovery**: Algorithms for inferring conceptual models from relational databases
3. **Semantic Data Migration**: Research on preserving meaning during schema transformations

### Implementation Standards
- S→C→T architecture (mandatory for research-grade implementations)
- DBRE pattern recognition algorithms
- Semantic enrichment techniques from data engineering literature

## Troubleshooting

### Issue: Inheritance Not Detected
**Solution:** Check naming conventions. Ensure subclass tables have FK to superclass that is part of PK.

### Issue: Wrong Cardinality Inferred
**Solution:** Verify UNIQUE constraints on FK columns. Consider adding explicit hints in configuration.

### Issue: Generic Relationship Names
**Solution:** Review FK column naming. Use descriptive names like `manager_id` instead of `fk_1`.

## Future Enhancements

1. **Machine Learning-based Enrichment**: Use ML to learn naming patterns from training data
2. **Natural Language Processing**: Extract semantics from column/table comments
3. **Interactive Refinement**: Allow user to review and adjust inferred semantics
4. **Domain-Specific Rules**: Configurable enrichment rules per industry (e-commerce, healthcare, etc.)

---

**Last Updated:** 2024
**Version:** 1.0.0
**Authors:** DBMS Final Project Team
