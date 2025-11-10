"""
Enrichment Rule Constants
Defines the semantic transformation rules for SCT migration

This module provides the vocabulary for enrichment rules that transform
"flat" Source-to-Target migrations into enriched Source-to-Conceptual-to-Target
migrations, as described in the research paper.
"""

# Enrichment rule types
ENRICHMENT_NONE = 'NONE'
"""No enrichment - standard node creation"""

ENRICHMENT_MERGE_ON_LABEL = 'MERGE_ON_LABEL'
"""
For Class Table Inheritance (CTI):
Instead of creating separate nodes, add a label to an existing node.
Example: (Person) becomes (Person:Student) with combined properties.
"""

ENRICHMENT_REL_FROM_JUNCTION = 'REL_FROM_JUNCTION_TABLE'
"""
For Aggregation patterns:
Dissolve junction tables into relationships with properties.
Example: Order_Items becomes (Order)-[:CONTAINS {quantity, price}]->(Product)
"""

ENRICHMENT_LABEL_FROM_COLUMN = 'LABEL_FROM_COLUMN'
"""
For Single Table Inheritance (STI):
Create node labels based on a type/discriminator column value.
Example: Employee table with 'type' column creates :Manager or :Engineer labels
"""

# Relationship types
REL_TYPE_FOREIGN_KEY = 'foreign_key'
"""Standard 1:N relationship from foreign key"""

REL_TYPE_MANY_TO_MANY = 'many_to_many'
"""M:N relationship from junction table"""

REL_TYPE_INHERITANCE = 'inheritance'
"""Inheritance relationship (typically enriched to multi-label)"""
