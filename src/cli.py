"""
Command Line Interface

CLI for the RDBMS to Graph migration system.
Supports both S→C→T (with semantic enrichment) and direct S→T transformation.
"""

import click
import json
import sys
from pathlib import Path
import logging

from .utils.config import ConfigLoader
from .utils.logger import setup_logger
from .connectors import MySQLConnector, PostgreSQLConnector, SQLServerConnector
from .analyzers import SchemaAnalyzer, SemanticEnricher
from .extractors import DataExtractor
from .transformers import GraphTransformer
from .loaders import Neo4jLoader
from .validators import DataValidator
from .utils.helpers import format_duration, estimate_migration_time
import time


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """RDBMS to Property Graph Migration System"""
    pass


@cli.command()
@click.option('--config', '-c', required=True, type=click.Path(exists=True),
              help='Path to configuration file')
@click.option('--output', '-o', type=click.Path(), 
              help='Output file for schema analysis (JSON)')
def analyze(config, output):
    """Analyze source database schema"""
    click.echo("🔍 Analyzing database schema...")
    
    # Load configuration
    config_loader = ConfigLoader(config)
    cfg = config_loader.load()
    
    # Setup logging
    log_config = config_loader.get_logging_config()
    logger = setup_logger(level=log_config['level'], log_file=log_config['file'])
    
    try:
        # Connect to source database
        source_config = config_loader.get_source_config()
        connector = _create_connector(source_config)
        
        with connector:
            # Analyze schema
            analyzer = SchemaAnalyzer(connector)
            db_schema = analyzer.analyze()
            
            # Get summary
            summary = analyzer.get_schema_summary(db_schema)
            
            # Display summary
            click.echo("\n📊 Schema Analysis Summary:")
            click.echo(f"  Database: {summary['database_name']}")
            click.echo(f"  Type: {summary['database_type']}")
            click.echo(f"  Total Tables: {summary['total_tables']}")
            click.echo(f"  Entity Tables: {summary['entity_tables']}")
            click.echo(f"  Junction Tables: {summary['junction_tables']}")
            click.echo(f"  Total Columns: {summary['total_columns']}")
            click.echo(f"  Total Foreign Keys: {summary['total_foreign_keys']}")
            click.echo(f"  Total Indexes: {summary['total_indexes']}")
            click.echo(f"  Total Rows: {summary['total_rows']:,}")
            
            # Save to file if requested
            if output:
                output_path = Path(output)
                with open(output_path, 'w') as f:
                    json.dump(db_schema.to_dict(), f, indent=2, default=str)
                click.echo(f"\n💾 Analysis saved to: {output}")
            
            click.echo("\n✅ Schema analysis complete!")
    
    except Exception as e:
        click.echo(f"\n❌ Error: {e}", err=True)
        logger.error(f"Analysis failed: {e}", exc_info=True)
        sys.exit(1)


@cli.command()
@click.option('--config', '-c', required=True, type=click.Path(exists=True),
              help='Path to configuration file')
@click.option('--dry-run', is_flag=True, help='Analyze only, do not migrate data')
@click.option('--tables', '-t', help='Comma-separated list of tables to migrate')
@click.option('--clear-target', is_flag=True, help='Clear target database before migration')
def migrate(config, dry_run, tables, clear_target):
    """Execute complete database migration"""
    click.echo("🚀 Starting migration process...")
    
    # Load configuration
    config_loader = ConfigLoader(config)
    cfg = config_loader.load()
    
    # Setup logging
    log_config = config_loader.get_logging_config()
    logger = setup_logger(level=log_config['level'], log_file=log_config['file'])
    
    start_time = time.time()
    
    try:
        # Get configuration
        source_config = config_loader.get_source_config()
        target_config = config_loader.get_target_config()
        migration_config = config_loader.get_migration_config()
        
        # Connect to source
        click.echo("\n📡 Connecting to source database...")
        source_connector = _create_connector(source_config)
        source_connector.connect()
        
        # Connect to target
        click.echo("📡 Connecting to Neo4j...")
        neo4j_loader = Neo4jLoader(
            uri=target_config['uri'],
            username=target_config['username'],
            password=target_config['password'],
            database=target_config.get('database', 'neo4j')
        )
        neo4j_loader.connect()
        
        # Analyze schema
        click.echo("\n🔍 Analyzing source schema...")
        analyzer = SchemaAnalyzer(source_connector)
        db_schema = analyzer.analyze()
        summary = analyzer.get_schema_summary(db_schema)
        click.echo(f"  Found {summary['total_tables']} tables with {summary['total_rows']:,} rows")
        
        # Transform to graph model
        click.echo("\n🔄 Transforming to graph model...")
        transformer = GraphTransformer(db_schema, config_loader.get_mapping_config())
        graph_model = transformer.transform()
        click.echo(f"  Created {len(graph_model.node_labels)} node labels")
        click.echo(f"  Created {len(graph_model.relationship_types)} relationship types")
        
        # Validate before migration
        if migration_config.get('validate_before'):
            click.echo("\n✓ Running pre-migration validation...")
            validator = DataValidator(source_connector, neo4j_loader, db_schema, graph_model)
            pre_results = validator.validate_pre_migration()
            if not pre_results['valid']:
                click.echo("❌ Pre-migration validation failed!")
                for error in pre_results['errors']:
                    click.echo(f"  ⚠ {error}")
                if not click.confirm("Continue anyway?"):
                    sys.exit(1)
        
        if dry_run:
            click.echo("\n🔍 Dry run complete (no data migrated)")
            source_connector.disconnect()
            neo4j_loader.disconnect()
            return
        
        # Clear target database if requested
        if clear_target:
            click.echo("\n🗑 Clearing target database...")
            neo4j_loader.clear_database()
        
        # Create constraints and indexes
        if migration_config.get('create_indexes'):
            click.echo("\n📑 Creating constraints and indexes...")
            neo4j_loader.create_constraints_and_indexes(graph_model)
        
        # Migrate data
        click.echo("\n📦 Migrating data...")
        _migrate_data(source_connector, neo4j_loader, db_schema, graph_model, 
                     transformer, migration_config, tables)
        
        # Validate after migration
        if migration_config.get('validate_after'):
            click.echo("\n✓ Running post-migration validation...")
            validator = DataValidator(source_connector, neo4j_loader, db_schema, graph_model)
            post_results = validator.validate_post_migration()
            
            if post_results['valid']:
                click.echo("✅ Post-migration validation passed!")
            else:
                click.echo("❌ Post-migration validation failed!")
                for error in post_results['errors']:
                    click.echo(f"  ⚠ {error}")
        
        # Cleanup
        source_connector.disconnect()
        neo4j_loader.disconnect()
        
        # Summary
        elapsed_time = time.time() - start_time
        click.echo(f"\n✅ Migration complete in {format_duration(elapsed_time)}!")
    
    except Exception as e:
        click.echo(f"\n❌ Error: {e}", err=True)
        logger.error(f"Migration failed: {e}", exc_info=True)
        sys.exit(1)


@cli.command()
@click.option('--config', '-c', required=True, type=click.Path(exists=True),
              help='Path to configuration file')
@click.option('--check-counts', is_flag=True, help='Compare row counts')
def validate(config, check_counts):
    """Validate migrated data"""
    click.echo("✓ Validating migration...")
    
    config_loader = ConfigLoader(config)
    cfg = config_loader.load()
    
    log_config = config_loader.get_logging_config()
    logger = setup_logger(level=log_config['level'], log_file=log_config['file'])
    
    try:
        source_config = config_loader.get_source_config()
        target_config = config_loader.get_target_config()
        
        source_connector = _create_connector(source_config)
        source_connector.connect()
        
        neo4j_loader = Neo4jLoader(
            uri=target_config['uri'],
            username=target_config['username'],
            password=target_config['password'],
            database=target_config.get('database', 'neo4j')
        )
        neo4j_loader.connect()
        
        analyzer = SchemaAnalyzer(source_connector)
        db_schema = analyzer.analyze()
        
        transformer = GraphTransformer(db_schema)
        graph_model = transformer.transform()
        
        validator = DataValidator(source_connector, neo4j_loader, db_schema, graph_model)
        
        click.echo("\n📊 Validation Results:")
        
        if check_counts:
            post_results = validator.validate_post_migration()
            
            click.echo("\nRow Counts Comparison:")
            for table_name, counts in post_results.get('row_counts', {}).items():
                status = "✅" if counts['match'] else "❌"
                click.echo(
                    f"  {status} {table_name}: "
                    f"Source={counts['source']}, Target={counts['target']}"
                )
            
            if post_results['valid']:
                click.echo("\n✅ All validations passed!")
            else:
                click.echo("\n❌ Some validations failed!")
        
        source_connector.disconnect()
        neo4j_loader.disconnect()
    
    except Exception as e:
        click.echo(f"\n❌ Error: {e}", err=True)
        logger.error(f"Validation failed: {e}", exc_info=True)
        sys.exit(1)


@cli.command()
@click.option('--config', '-c', required=True, type=click.Path(exists=True),
              help='Path to configuration file')
@click.option('--type', '-t', type=click.Choice(['source', 'target']), 
              required=True, help='Connection type to test')
def test_connection(config, type):
    """Test database connection"""
    config_loader = ConfigLoader(config)
    cfg = config_loader.load()
    
    try:
        if type == 'source':
            click.echo("Testing source database connection...")
            source_config = config_loader.get_source_config()
            connector = _create_connector(source_config)
            
            if connector.test_connection():
                click.echo("✅ Source connection successful!")
            else:
                click.echo("❌ Source connection failed!")
                sys.exit(1)
        
        else:  # target
            click.echo("Testing Neo4j connection...")
            target_config = config_loader.get_target_config()
            neo4j_loader = Neo4jLoader(
                uri=target_config['uri'],
                username=target_config['username'],
                password=target_config['password'],
                database=target_config.get('database', 'neo4j')
            )
            
            if neo4j_loader.test_connection():
                click.echo("✅ Neo4j connection successful!")
            else:
                click.echo("❌ Neo4j connection failed!")
                sys.exit(1)
    
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


def _create_connector(config: dict):
    """Create appropriate database connector"""
    db_type = config['type'].lower()
    
    if db_type == 'mysql':
        return MySQLConnector(
            host=config['host'],
            port=config.get('port', 3306),
            database=config['database'],
            username=config['username'],
            password=config['password']
        )
    elif db_type == 'postgresql':
        return PostgreSQLConnector(
            host=config['host'],
            port=config.get('port', 5432),
            database=config['database'],
            username=config['username'],
            password=config['password']
        )
    elif db_type == 'sqlserver':
        return SQLServerConnector(
            host=config['host'],
            port=config.get('port', 1433),
            database=config['database'],
            username=config['username'],
            password=config['password']
        )
    else:
        raise ValueError(f"Unsupported database type: {db_type}")


def _migrate_data(source_connector, neo4j_loader, db_schema, graph_model, 
                 transformer, migration_config, tables_filter):
    """Migrate data from source to target"""
    batch_size = migration_config.get('batch_size', 1000)
    
    # Filter tables if specified
    entity_tables = db_schema.get_entity_tables()
    if tables_filter:
        table_names = [t.strip() for t in tables_filter.split(',')]
        entity_tables = [t for t in entity_tables if t.name in table_names]
    
    extractor = DataExtractor(source_connector, batch_size)
    
    # Migrate nodes
    for table in entity_tables:
        if table.row_count == 0:
            continue
        
        from .utils.helpers import sanitize_label
        label = sanitize_label(table.name)
        
        click.echo(f"\n  Migrating {table.name} ({table.row_count:,} rows)...")
        
        total_loaded = 0
        for batch in extractor.extract_table_data(table, show_progress=False):
            # Transform rows to nodes
            nodes = []
            for row in batch:
                properties = transformer.transform_row_to_node(table.name, row)
                nodes.append(properties)
            
            # Load batch
            count = neo4j_loader.load_nodes_batch(label, nodes)
            total_loaded += count
        
        click.echo(f"    ✓ Loaded {total_loaded:,} nodes")
    
    # Migrate relationships
    click.echo("\n  Migrating relationships...")
    for table in db_schema.tables.values():
        for fk in table.foreign_keys:
            _migrate_foreign_key_relationships(
                table, fk, source_connector, neo4j_loader, 
                transformer, batch_size
            )
    
    # Migrate junction table relationships
    junction_tables = db_schema.get_junction_tables()
    if tables_filter:
        junction_tables = [t for t in junction_tables if t.name in table_names]
    
    for table in junction_tables:
        _migrate_junction_relationships(
            table, source_connector, neo4j_loader, 
            transformer, batch_size
        )


def _migrate_foreign_key_relationships(table, fk, source_connector, neo4j_loader, 
                                      transformer, batch_size):
    """Migrate relationships from foreign keys"""
    from .utils.helpers import sanitize_label, create_relationship_type_name
    
    extractor = DataExtractor(source_connector, batch_size)
    from_label = sanitize_label(table.name)
    to_label = sanitize_label(fk.referenced_table)
    rel_type = create_relationship_type_name(table.name, fk.referenced_table)
    
    total_loaded = 0
    for batch in extractor.extract_table_data(table, show_progress=False):
        relationships = []
        for row in batch:
            if row.get(fk.column) is not None:
                relationships.append({
                    'from_id': row.get(table.primary_key.columns[0] if table.primary_key else 'id'),
                    'to_id': row.get(fk.column),
                    'properties': {}
                })
        
        if relationships:
            count = neo4j_loader.load_relationships_batch(
                rel_type, from_label, to_label, relationships
            )
            total_loaded += count
    
    if total_loaded > 0:
        click.echo(f"    ✓ Created {total_loaded:,} {rel_type} relationships")


def _get_node_label_for_table(table, graph_model):
    """Get the node label for a given table"""
    from .utils.helpers import sanitize_label
    label = sanitize_label(table.name)
    for node_label in graph_model.node_labels.values():
        if node_label.label == label:
            return node_label
    return None


def _migrate_table_to_nodes(table, source_connector, neo4j_loader, node_label, batch_size):
    """Migrate a single table to nodes"""
    if table.row_count == 0:
        return
    
    click.echo(f"  • {table.name} → {node_label.label} ({table.row_count:,} rows)")
    
    extractor = DataExtractor(source_connector, batch_size)
    total_loaded = 0
    
    for batch in extractor.extract_table_data(table, show_progress=False):
        nodes = []
        for row in batch:
            # Convert row to properties
            properties = {k: v for k, v in row.items() if v is not None}
            nodes.append(properties)
        
        if nodes:
            count = neo4j_loader.load_nodes_batch(node_label.label, nodes)
            total_loaded += count
    
    click.echo(f"    ✓ Loaded {total_loaded:,} nodes")


def _migrate_all_relationships(db_schema, source_connector, neo4j_loader, 
                               transformer, batch_size):
    """Migrate all relationships from foreign keys and junction tables"""
    # Migrate FK relationships
    for table in db_schema.tables.values():
        for fk in table.foreign_keys:
            _migrate_fk_relationships(
                table, fk, source_connector, neo4j_loader, batch_size
            )
    
    # Migrate junction table relationships
    junction_tables = db_schema.get_junction_tables()
    for table in junction_tables:
        _migrate_junction_relationships(
            table, source_connector, neo4j_loader, batch_size
        )


def _migrate_fk_relationships(table, fk, source_connector, neo4j_loader, batch_size):
    """Migrate relationships from a foreign key"""
    from .utils.helpers import sanitize_label
    
    # Use enriched relationship name if available
    rel_type = fk.relationship_name if fk.relationship_name else f"FK_{table.name}_{fk.referenced_table}".upper()
    from_label = sanitize_label(table.name)
    to_label = sanitize_label(fk.referenced_table)
    
    extractor = DataExtractor(source_connector, batch_size)
    total_loaded = 0
    
    for batch in extractor.extract_table_data(table, show_progress=False):
        relationships = []
        for row in batch:
            if row.get(fk.column) is not None:
                from_id = row.get(table.primary_key.columns[0] if table.primary_key else 'id')
                to_id = row.get(fk.column)
                if from_id is not None and to_id is not None:
                    rel_props = {
                        'from_id': from_id,
                        'to_id': to_id,
                        'properties': {}
                    }
                    # Add cardinality as property if available
                    if fk.cardinality:
                        rel_props['properties']['cardinality'] = fk.cardinality
                    relationships.append(rel_props)
        
        if relationships:
            count = neo4j_loader.load_relationships_batch(
                rel_type, from_label, to_label, relationships
            )
            total_loaded += count
    
    if total_loaded > 0:
        click.echo(f"    • {from_label} -{rel_type}-> {to_label}: {total_loaded:,} relationships")


def _migrate_junction_relationships(table, source_connector, neo4j_loader, batch_size):
    """Migrate relationships from junction tables"""
    from .utils.helpers import sanitize_label
    
    if len(table.foreign_keys) != 2:
        return
    
    fk1, fk2 = table.foreign_keys
    from_label = sanitize_label(fk1.referenced_table)
    to_label = sanitize_label(fk2.referenced_table)
    rel_type = sanitize_label(table.name).upper()
    
    extractor = DataExtractor(source_connector, batch_size)
    
    total_loaded = 0
    for batch in extractor.extract_table_data(table, show_progress=False):
        relationships = []
        for row in batch:
            # Get relationship properties (non-FK columns)
            properties = {}
            for col in table.columns:
                if col.name not in [fk1.column, fk2.column]:
                    from ..utils.helpers import sanitize_property_name
                    prop_name = sanitize_property_name(col.name)
                    properties[prop_name] = row.get(col.name)
            
            relationships.append({
                'from_id': row.get(fk1.column),
                'to_id': row.get(fk2.column),
                'properties': properties
            })
        
        if relationships:
            count = neo4j_loader.load_relationships_batch(
                rel_type, from_label, to_label, relationships
            )
            total_loaded += count
    
    if total_loaded > 0:
        click.echo(f"    ✓ Created {total_loaded:,} {rel_type} relationships")


@cli.command(name='enrich')
@click.option('--config', '-c', required=True, type=click.Path(exists=True),
              help='Path to configuration file')
@click.option('--output', '-o', type=click.Path(), 
              help='Output file for conceptual model (JSON)')
def enrich_schema(config, output):
    """
    Perform semantic enrichment (S→C transformation).
    Analyzes schema and infers semantic information using DBRE techniques.
    """
    click.echo("🧠 Performing semantic enrichment (S→C)...")
    
    config_loader = ConfigLoader(config)
    cfg = config_loader.load()
    
    log_config = config_loader.get_logging_config()
    logger = setup_logger(level=log_config['level'], log_file=log_config['file'])
    
    try:
        source_config = config_loader.get_source_config()
        
        # Connect to source
        click.echo("\n📡 Connecting to source database...")
        source_connector = _create_connector(source_config)
        source_connector.connect()
        
        # Phase 1: Extract schema (S)
        click.echo("\n📊 Phase 1: Extracting relational schema...")
        analyzer = SchemaAnalyzer(source_connector)
        db_schema = analyzer.analyze()
        click.echo(f"   ✓ Found {len(db_schema.tables)} tables")
        
        # Phase 2: Semantic enrichment (S→C)
        click.echo("\n🔍 Phase 2: Semantic enrichment...")
        enricher = SemanticEnricher(db_schema)
        conceptual_model = enricher.enrich()
        
        # Display enrichment results
        click.echo("\n📈 Semantic Enrichment Results:")
        click.echo(f"   ✓ Entities: {len(conceptual_model.entities)}")
        click.echo(f"   ✓ Strong Entities: {len(conceptual_model.get_strong_entities())}")
        click.echo(f"   ✓ Weak Entities: {len(conceptual_model.get_weak_entities())}")
        click.echo(f"   ✓ Relationships: {len(conceptual_model.relationships)}")
        click.echo(f"   ✓ Inheritance Hierarchies: {len(conceptual_model.inheritance_hierarchies)}")
        click.echo(f"   ✓ Inheritance Relationships: {len(conceptual_model.get_inheritance_relationships())}")
        click.echo(f"   ✓ Aggregation Relationships: {len(conceptual_model.get_aggregation_relationships())}")
        
        # Show inheritance hierarchies
        if conceptual_model.inheritance_hierarchies:
            click.echo("\n🔗 Detected Inheritance Hierarchies:")
            for idx, hierarchy in enumerate(conceptual_model.inheritance_hierarchies, 1):
                click.echo(f"   {idx}. {' → '.join(hierarchy)}")
        
        # Show weak entity groups
        if conceptual_model.weak_entity_groups:
            click.echo("\n🔗 Detected Weak Entity Groups:")
            for owner, weak_entities in conceptual_model.weak_entity_groups.items():
                click.echo(f"   {owner} owns: {', '.join(weak_entities)}")
        
        # Show sample relationships with enriched names
        click.echo("\n🏷️  Sample Enriched Relationships:")
        for rel in list(conceptual_model.relationships)[:5]:
            card_symbol = rel.cardinality.value
            semantic_type = rel.semantics.value
            click.echo(f"   • {rel.source_entity} -{rel.name}[{card_symbol}, {semantic_type}]-> {rel.target_entity}")
        
        # Save to file if requested
        if output:
            with open(output, 'w') as f:
                json.dump(conceptual_model.to_dict(), f, indent=2)
            click.echo(f"\n💾 Conceptual model saved to: {output}")
        
        source_connector.disconnect()
        click.echo("\n✅ Semantic enrichment complete!")
        
    except Exception as e:
        click.echo(f"\n❌ Error: {e}", err=True)
        logger.error(f"Enrichment failed: {e}", exc_info=True)
        sys.exit(1)


@cli.command(name='migrate-sct')
@click.option('--config', '-c', required=True, type=click.Path(exists=True),
              help='Path to configuration file')
@click.option('--dry-run', is_flag=True, help='Analyze only, do not migrate data')
@click.option('--tables', '-t', help='Comma-separated list of tables to migrate')
@click.option('--clear-target', is_flag=True, help='Clear target database before migration')
def migrate_sct(config, dry_run, tables, clear_target):
    """
    Execute migration using S→C→T architecture with semantic enrichment.
    This is the preferred method that preserves semantic information.
    """
    click.echo("🚀 Starting S→C→T migration with semantic enrichment...")
    
    config_loader = ConfigLoader(config)
    cfg = config_loader.load()
    
    log_config = config_loader.get_logging_config()
    logger = setup_logger(level=log_config['level'], log_file=log_config['file'])
    
    start_time = time.time()
    
    try:
        source_config = config_loader.get_source_config()
        target_config = config_loader.get_target_config()
        migration_config = config_loader.get_migration_config()
        
        # Connect to source
        click.echo("\n📡 Connecting to source database...")
        source_connector = _create_connector(source_config)
        source_connector.connect()
        
        # Phase 1: Extract schema (S)
        click.echo("\n📊 Phase 1: Extracting relational schema (S)...")
        analyzer = SchemaAnalyzer(source_connector)
        db_schema = analyzer.analyze()
        click.echo(f"   ✓ Extracted {len(db_schema.tables)} tables")
        
        # Phase 2: Semantic enrichment (S→C)
        click.echo("\n🧠 Phase 2: Semantic enrichment (S→C)...")
        enricher = SemanticEnricher(db_schema)
        conceptual_model = enricher.enrich()
        click.echo(f"   ✓ Created {len(conceptual_model.entities)} enriched entities")
        click.echo(f"   ✓ Created {len(conceptual_model.relationships)} semantic relationships")
        click.echo(f"   ✓ Detected {len(conceptual_model.inheritance_hierarchies)} inheritance hierarchies")
        
        # Phase 3: Transform to graph (C→T)
        click.echo("\n🔄 Phase 3: Transforming to graph model (C→T)...")
        transformer = GraphTransformer(db_schema=db_schema, conceptual_model=conceptual_model)
        graph_model = transformer.transform()
        click.echo(f"   ✓ Created {len(graph_model.node_labels)} node labels")
        click.echo(f"   ✓ Created {len(graph_model.relationship_types)} relationship types")
        
        if dry_run:
            click.echo("\n🔍 Dry run complete - no data migrated")
            source_connector.disconnect()
            return
        
        # Connect to Neo4j
        click.echo("\n📡 Connecting to Neo4j...")
        neo4j_loader = Neo4jLoader(
            uri=target_config['uri'],
            username=target_config['username'],
            password=target_config['password'],
            database=target_config.get('database', 'neo4j')
        )
        neo4j_loader.connect()
        
        if clear_target:
            click.echo("\n🗑️  Clearing target database...")
            neo4j_loader.clear_database()
        
        # Create constraints and indexes
        click.echo("\n🔧 Creating constraints and indexes...")
        neo4j_loader.create_constraints_and_indexes(graph_model)
        
        # Migrate data (using existing logic)
        click.echo("\n📤 Phase 4: Migrating data...")
        batch_size = migration_config.get('batch_size', 1000)
        
        # Filter tables if specified
        tables_to_migrate = None
        if tables:
            tables_to_migrate = [t.strip() for t in tables.split(',')]
        
        # Migrate entity tables
        entity_tables = db_schema.get_entity_tables()
        for table in entity_tables:
            if tables_to_migrate and table.name not in tables_to_migrate:
                continue
            
            node_label = _get_node_label_for_table(table, graph_model)
            if node_label:
                _migrate_table_to_nodes(table, source_connector, neo4j_loader, 
                                       node_label, batch_size)
        
        # Migrate relationships
        click.echo("\n🔗 Migrating relationships...")
        _migrate_all_relationships(db_schema, source_connector, neo4j_loader, 
                                  transformer, batch_size)
        
        # Validation
        click.echo("\n✓ Validating migration...")
        validator = DataValidator(source_connector, neo4j_loader, db_schema, graph_model)
        post_results = validator.validate_post_migration()
        
        total_mismatches = len([c for c in post_results.get('row_counts', {}).values() 
                               if not c['match']])
        if total_mismatches == 0:
            click.echo("   ✅ All row counts match!")
        else:
            click.echo(f"   ⚠️  {total_mismatches} table(s) with count mismatches")
        
        # Cleanup
        source_connector.disconnect()
        neo4j_loader.close()
        
        elapsed = time.time() - start_time
        click.echo(f"\n✅ S→C→T migration complete in {format_duration(elapsed)}!")
        
    except Exception as e:
        click.echo(f"\n❌ Error: {e}", err=True)
        logger.error(f"S→C→T migration failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    cli()
