"""
Helper Utilities

Utility functions for data processing, formatting, and common operations.
"""

import re
from typing import List, Iterator, Any, Dict, Optional
from datetime import datetime, timedelta
import logging


logger = logging.getLogger(__name__)


def sanitize_label(name: str) -> str:
    """
    Sanitize a string to be used as a Neo4j label.
    
    Args:
        name: Original name
        
    Returns:
        Sanitized label name
    """
    # Remove special characters, keep only alphanumeric and underscores
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '', name)
    
    # Ensure it starts with a letter
    if sanitized and not sanitized[0].isalpha():
        sanitized = 'N' + sanitized
    
    # Convert to PascalCase
    parts = sanitized.split('_')
    sanitized = ''.join(word.capitalize() for word in parts if word)
    
    return sanitized or 'Node'


def sanitize_property_name(name: str) -> str:
    """
    Sanitize a string to be used as a Neo4j property name.
    
    Args:
        name: Original name
        
    Returns:
        Sanitized property name
    """
    # Replace spaces and special characters with underscores
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    
    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')
    
    # Convert to camelCase
    parts = sanitized.split('_')
    if parts:
        sanitized = parts[0].lower() + ''.join(word.capitalize() for word in parts[1:] if word)
    
    return sanitized or 'property'


def batch_iterator(data: List[Any], batch_size: int) -> Iterator[List[Any]]:
    """
    Create an iterator that yields batches of data.
    
    Args:
        data: List of items to batch
        batch_size: Size of each batch
        
    Yields:
        Batches of items
    """
    for i in range(0, len(data), batch_size):
        yield data[i:i + batch_size]


def estimate_migration_time(row_count: int, batch_size: int, 
                           rows_per_second: int = 1000) -> float:
    """
    Estimate migration time based on row count.
    
    Args:
        row_count: Total number of rows
        batch_size: Batch size for processing
        rows_per_second: Estimated processing rate
        
    Returns:
        Estimated time in seconds
    """
    if row_count == 0:
        return 0.0
    
    batches = (row_count + batch_size - 1) // batch_size
    total_seconds = row_count / rows_per_second
    
    # Add overhead for batch processing
    overhead_per_batch = 0.1  # seconds
    total_seconds += batches * overhead_per_batch
    
    return total_seconds


def format_bytes(bytes_count: int) -> str:
    """
    Format bytes into human-readable string.
    
    Args:
        bytes_count: Number of bytes
        
    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_count < 1024.0:
            return f"{bytes_count:.2f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.2f} PB"


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted string (e.g., "2h 15m 30s")
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    
    duration = timedelta(seconds=int(seconds))
    days = duration.days
    hours, remainder = divmod(duration.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}s")
    
    return " ".join(parts)


def convert_sql_type_to_graph_type(sql_type: str) -> str:
    """
    Convert SQL data type to graph property type.
    
    Args:
        sql_type: SQL data type
        
    Returns:
        Graph property type
    """
    sql_type_lower = sql_type.lower()
    
    # Integer types
    if any(t in sql_type_lower for t in ['int', 'serial', 'bigserial']):
        return 'INTEGER'
    
    # Float types
    if any(t in sql_type_lower for t in ['float', 'double', 'real', 'decimal', 'numeric']):
        return 'FLOAT'
    
    # Boolean types
    if any(t in sql_type_lower for t in ['bool', 'bit']):
        return 'BOOLEAN'
    
    # Date/Time types
    if any(t in sql_type_lower for t in ['date', 'time', 'timestamp']):
        if 'date' in sql_type_lower and 'time' not in sql_type_lower:
            return 'DATE'
        return 'DATETIME'
    
    # JSON types
    if 'json' in sql_type_lower:
        return 'MAP'
    
    # Default to string
    return 'STRING'


def create_relationship_type_name(from_table: str, to_table: str, 
                                  fk_name: Optional[str] = None) -> str:
    """
    Create a relationship type name from table names.
    
    Args:
        from_table: Source table name
        to_table: Target table name
        fk_name: Optional foreign key name for additional context
        
    Returns:
        Relationship type name in SCREAMING_SNAKE_CASE
    """
    # Convert table names to singular if possible
    from_singular = from_table.rstrip('s') if from_table.endswith('s') else from_table
    to_singular = to_table.rstrip('s') if to_table.endswith('s') else to_table
    
    # Create relationship name
    rel_name = f"{from_singular}_{to_singular}"
    
    # Convert to SCREAMING_SNAKE_CASE
    rel_name = re.sub(r'([A-Z])', r'_\1', rel_name).upper()
    rel_name = re.sub(r'[^A-Z0-9_]', '_', rel_name)
    rel_name = re.sub(r'_+', '_', rel_name)
    rel_name = rel_name.strip('_')
    
    return rel_name


def validate_neo4j_identifier(identifier: str) -> bool:
    """
    Validate if a string is a valid Neo4j identifier.
    
    Args:
        identifier: String to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not identifier:
        return False
    
    # Neo4j identifiers must start with a letter or underscore
    if not (identifier[0].isalpha() or identifier[0] == '_'):
        return False
    
    # Rest can be letters, digits, or underscores
    return all(c.isalnum() or c == '_' for c in identifier)


def truncate_string(text: str, max_length: int = 100, suffix: str = '...') -> str:
    """
    Truncate a string to a maximum length.
    
    Args:
        text: String to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix
