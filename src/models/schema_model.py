"""
Schema Model Classes

Represents relational database schema components including tables,
columns, constraints, and relationships.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum


class ColumnType(Enum):
    """Database column types."""
    INTEGER = "INTEGER"
    BIGINT = "BIGINT"
    SMALLINT = "SMALLINT"
    DECIMAL = "DECIMAL"
    NUMERIC = "NUMERIC"
    FLOAT = "FLOAT"
    DOUBLE = "DOUBLE"
    VARCHAR = "VARCHAR"
    CHAR = "CHAR"
    TEXT = "TEXT"
    DATE = "DATE"
    DATETIME = "DATETIME"
    TIMESTAMP = "TIMESTAMP"
    TIME = "TIME"
    BOOLEAN = "BOOLEAN"
    BINARY = "BINARY"
    JSON = "JSON"
    UNKNOWN = "UNKNOWN"


@dataclass
class Column:
    """Represents a database column."""
    name: str
    data_type: str
    column_type: ColumnType = ColumnType.UNKNOWN
    is_nullable: bool = True
    max_length: Optional[int] = None
    precision: Optional[int] = None
    scale: Optional[int] = None
    default_value: Optional[Any] = None
    is_auto_increment: bool = False
    ordinal_position: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert column to dictionary."""
        return {
            'name': self.name,
            'data_type': self.data_type,
            'column_type': self.column_type.value,
            'is_nullable': self.is_nullable,
            'max_length': self.max_length,
            'precision': self.precision,
            'scale': self.scale,
            'default_value': self.default_value,
            'is_auto_increment': self.is_auto_increment,
            'ordinal_position': self.ordinal_position
        }


@dataclass
class PrimaryKey:
    """Represents a primary key constraint."""
    name: str
    columns: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert primary key to dictionary."""
        return {
            'name': self.name,
            'columns': self.columns
        }


@dataclass
class ForeignKey:
    """Represents a foreign key constraint with semantic enrichment."""
    name: str
    column: str
    referenced_table: str
    referenced_column: str
    on_delete: Optional[str] = None
    on_update: Optional[str] = None
    # Semantic enrichment properties
    cardinality: Optional[str] = None  # '1:1', '1:N', 'N:M'
    relationship_name: Optional[str] = None  # Business-meaningful name
    is_inheritance: bool = False  # True if represents subclass relationship
    is_aggregation: bool = False  # True if represents part-of relationship
    is_weak_entity: bool = False  # True if target is weak entity
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert foreign key to dictionary."""
        return {
            'name': self.name,
            'column': self.column,
            'referenced_table': self.referenced_table,
            'referenced_column': self.referenced_column,
            'on_delete': self.on_delete,
            'on_update': self.on_update,
            'cardinality': self.cardinality,
            'relationship_name': self.relationship_name,
            'is_inheritance': self.is_inheritance,
            'is_aggregation': self.is_aggregation,
            'is_weak_entity': self.is_weak_entity
        }


@dataclass
class Index:
    """Represents a database index."""
    name: str
    columns: List[str]
    is_unique: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert index to dictionary."""
        return {
            'name': self.name,
            'columns': self.columns,
            'is_unique': self.is_unique
        }


@dataclass
class Constraint:
    """Represents a generic database constraint."""
    name: str
    type: str
    definition: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert constraint to dictionary."""
        return {
            'name': self.name,
            'type': self.type,
            'definition': self.definition
        }


@dataclass
class Table:
    """Represents a database table with semantic classification."""
    name: str
    schema: str = "public"
    columns: List[Column] = field(default_factory=list)
    primary_key: Optional[PrimaryKey] = None
    foreign_keys: List[ForeignKey] = field(default_factory=list)
    indexes: List[Index] = field(default_factory=list)
    constraints: List[Constraint] = field(default_factory=list)
    row_count: int = 0
    # Semantic classification
    is_superclass: bool = False  # Part of inheritance hierarchy (parent)
    is_subclass: bool = False  # Part of inheritance hierarchy (child)
    superclass_table: Optional[str] = None  # Name of superclass if subclass
    is_weak_entity: bool = False  # Depends on another entity for existence
    owner_table: Optional[str] = None  # Owning entity if weak
    
    def get_column(self, column_name: str) -> Optional[Column]:
        """Get column by name."""
        for column in self.columns:
            if column.name == column_name:
                return column
        return None
    
    def is_junction_table(self) -> bool:
        """
        Determine if this is a junction table (many-to-many).
        Junction table criteria:
        - Has exactly 2 foreign keys
        - Primary key consists of the foreign key columns
        - Has minimal or no other columns
        """
        if len(self.foreign_keys) != 2:
            return False
        
        if not self.primary_key:
            return False
        
        fk_columns = {fk.column for fk in self.foreign_keys}
        pk_columns = set(self.primary_key.columns)
        
        # Primary key should be (subset of or equal to) foreign key columns
        return pk_columns.issubset(fk_columns)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert table to dictionary."""
        return {
            'name': self.name,
            'schema': self.schema,
            'columns': [col.to_dict() for col in self.columns],
            'primary_key': self.primary_key.to_dict() if self.primary_key else None,
            'foreign_keys': [fk.to_dict() for fk in self.foreign_keys],
            'indexes': [idx.to_dict() for idx in self.indexes],
            'constraints': [const.to_dict() for const in self.constraints],
            'row_count': self.row_count,
            'is_junction': self.is_junction_table()
        }


@dataclass
class DatabaseSchema:
    """Represents a complete database schema."""
    database_name: str
    database_type: str  # mysql, postgresql, sqlserver
    tables: Dict[str, Table] = field(default_factory=dict)
    version: Optional[str] = None
    
    def add_table(self, table: Table) -> None:
        """Add a table to the schema."""
        self.tables[table.name] = table
    
    def get_table(self, table_name: str) -> Optional[Table]:
        """Get table by name."""
        return self.tables.get(table_name)
    
    def get_junction_tables(self) -> List[Table]:
        """Get all junction tables."""
        return [table for table in self.tables.values() if table.is_junction_table()]
    
    def get_entity_tables(self) -> List[Table]:
        """Get all non-junction tables."""
        return [table for table in self.tables.values() if not table.is_junction_table()]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert schema to dictionary."""
        return {
            'database_name': self.database_name,
            'database_type': self.database_type,
            'version': self.version,
            'tables': {name: table.to_dict() for name, table in self.tables.items()},
            'table_count': len(self.tables),
            'junction_table_count': len(self.get_junction_tables()),
            'entity_table_count': len(self.get_entity_tables())
        }
