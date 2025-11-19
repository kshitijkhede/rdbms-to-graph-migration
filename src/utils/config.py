"""
Configuration Loader

Loads and validates migration configuration from YAML files.
"""

import yaml
from typing import Dict, Any, Optional
from pathlib import Path
import logging


class ConfigLoader:
    """Configuration loader and validator."""
    
    def __init__(self, config_path: str):
        """
        Initialize configuration loader.
        
        Args:
            config_path: Path to YAML configuration file
        """
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def load(self) -> Dict[str, Any]:
        """
        Load configuration from YAML file.
        
        Returns:
            Configuration dictionary
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            
            self.logger.info(f"Loaded configuration from {self.config_path}")
            self._validate()
            return self.config
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing YAML: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
            raise
    
    def _validate(self) -> None:
        """Validate configuration structure and required fields."""
        required_sections = ['source', 'target']
        for section in required_sections:
            if section not in self.config:
                raise ValueError(f"Missing required configuration section: {section}")
        
        # Validate source configuration
        source = self.config['source']
        required_source_fields = ['type', 'host', 'database', 'username', 'password']
        for field in required_source_fields:
            if field not in source:
                raise ValueError(f"Missing required source field: {field}")
        
        # Validate source type
        valid_types = ['mysql', 'postgresql', 'sqlserver']
        if source['type'] not in valid_types:
            raise ValueError(f"Invalid source type: {source['type']}. Must be one of {valid_types}")
        
        # Validate target configuration
        target = self.config['target']
        if 'neo4j' not in target:
            raise ValueError("Missing neo4j configuration in target section")
        
        neo4j_config = target['neo4j']
        required_neo4j_fields = ['uri', 'username', 'password']
        for field in required_neo4j_fields:
            if field not in neo4j_config:
                raise ValueError(f"Missing required neo4j field: {field}")
        
        self.logger.info("Configuration validation passed")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key.
        
        Args:
            key: Configuration key (supports dot notation, e.g., 'source.host')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_source_config(self) -> Dict[str, Any]:
        """Get source database configuration."""
        return self.config.get('source', {})
    
    def get_target_config(self) -> Dict[str, Any]:
        """Get target database configuration."""
        return self.config.get('target', {}).get('neo4j', {})
    
    def get_migration_config(self) -> Dict[str, Any]:
        """Get migration settings."""
        defaults = {
            'batch_size': 1000,
            'max_workers': 4,
            'validate_before': True,
            'validate_after': True,
            'create_indexes': True
        }
        migration_config = self.config.get('migration', {})
        return {**defaults, **migration_config}
    
    def get_mapping_config(self) -> Dict[str, Any]:
        """Get schema mapping configuration."""
        defaults = {
            'foreign_keys_as_relationships': True,
            'junction_tables_as_relationships': True,
            'tables_as_nodes': []
        }
        mapping_config = self.config.get('mapping', {})
        return {**defaults, **mapping_config}
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration."""
        defaults = {
            'level': 'INFO',
            'file': 'logs/migration.log'
        }
        logging_config = self.config.get('logging', {})
        return {**defaults, **logging_config}
