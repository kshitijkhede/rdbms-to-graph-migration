"""
Main Orchestrator Script
Coordinates all phases of the RDBMS-to-Graph migration pipeline
"""
import sys
import argparse
from src.extractor import MetadataExtractor
from src.loader import DataLoader
from src.validator import MigrationValidator


def print_banner(text):
    """Print a formatted banner"""
    print("\n" + "=" * 70)
    print(text.center(70))
    print("=" * 70)


def run_phase1(database_name, output_file=None):
    """
    Run Phase 1: Metadata Extraction
    
    Args:
        database_name: MySQL database name
        output_file: Path to save mapping file
    """
    print_banner("PHASE 1: METADATA EXTRACTION")
    
    extractor = MetadataExtractor(database_name)
    metadata = extractor.extract_schema_metadata()
    extractor.save_mapping_file(metadata, output_file)
    
    print("\n✓ Phase 1 completed successfully!")
    print(f"  Generated mapping file: {output_file or 'data/mapping.json'}")
    print("\n  Next Steps:")
    print("  1. Review and enrich the mapping file")
    print("  2. Run Phase 3 to migrate data")


def run_phase3(mapping_file=None, database_name=None, clear_db=False):
    """
    Run Phase 3: Data Migration (ETL)
    
    Args:
        mapping_file: Path to mapping configuration
        database_name: MySQL database name
        clear_db: Whether to clear Neo4j before migration
    """
    print_banner("PHASE 3: ETL PIPELINE - DATA MIGRATION")
    
    loader = DataLoader(mapping_file, database_name)
    loader.migrate_all(clear_db=clear_db)
    
    print("\n✓ Phase 3 completed successfully!")
    print("\n  Next Steps:")
    print("  1. Run Phase 4 to validate the migration")
    print("  2. Query your Neo4j database to explore the graph")


def run_phase4(mapping_file=None, database_name=None):
    """
    Run Phase 4: Migration Validation
    
    Args:
        mapping_file: Path to mapping configuration
        database_name: MySQL database name
    """
    print_banner("PHASE 4: MIGRATION VALIDATION")
    
    validator = MigrationValidator(mapping_file, database_name)
    success = validator.validate_all()
    
    if success:
        print("\n✓ Phase 4 completed successfully!")
        print("  All validation tests passed!")
    else:
        print("\n✗ Phase 4 completed with errors")
        print("  Some validation tests failed. Please review the results.")
    
    return success


def run_full_pipeline(database_name, clear_db=False):
    """
    Run the complete migration pipeline (all phases)
    
    Args:
        database_name: MySQL database name
        clear_db: Whether to clear Neo4j before migration
    """
    print_banner("RDBMS-TO-GRAPH MIGRATION ENGINE")
    print(f"\nDatabase: {database_name}")
    print(f"Clear Neo4j: {clear_db}")
    
    try:
        # Phase 1: Extract
        run_phase1(database_name)
        
        # Phase 3: Load (skipping Phase 2 as it's manual enrichment)
        print("\n" + "⏳ Proceeding to Phase 3...")
        input("Press Enter to continue or Ctrl+C to stop and enrich mapping file...")
        run_phase3(database_name=database_name, clear_db=clear_db)
        
        # Phase 4: Validate
        print("\n" + "⏳ Proceeding to Phase 4...")
        input("Press Enter to continue...")
        success = run_phase4(database_name=database_name)
        
        if success:
            print_banner("MIGRATION COMPLETED SUCCESSFULLY! 🎉")
        else:
            print_banner("MIGRATION COMPLETED WITH WARNINGS ⚠️")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Pipeline interrupted by user")
    except Exception as e:
        print(f"\n\n✗ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()


def main():
    """
    Main entry point with CLI argument parsing
    """
    parser = argparse.ArgumentParser(
        description='RDBMS-to-Graph Migration Engine',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run complete pipeline
  python main.py --full --database migration_source_ecommerce --clear
  
  # Run individual phases
  python main.py --phase 1 --database migration_source_ecommerce
  python main.py --phase 3 --database migration_source_ecommerce --clear
  python main.py --phase 4 --database migration_source_ecommerce
  
  # Use custom mapping file
  python main.py --phase 3 --mapping custom_mapping.json --clear
        """
    )
    
    parser.add_argument(
        '--phase',
        type=int,
        choices=[1, 3, 4],
        help='Run specific phase (1=Extract, 3=Load, 4=Validate)'
    )
    
    parser.add_argument(
        '--full',
        action='store_true',
        help='Run complete pipeline (all phases)'
    )
    
    parser.add_argument(
        '--database', '-db',
        type=str,
        help='MySQL database name'
    )
    
    parser.add_argument(
        '--mapping', '-m',
        type=str,
        help='Path to mapping JSON file'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Output path for mapping file (Phase 1 only)'
    )
    
    parser.add_argument(
        '--clear',
        action='store_true',
        help='Clear Neo4j database before migration'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.phase and not args.full:
        parser.print_help()
        return
    
    # Run requested operation
    if args.full:
        if not args.database:
            print("Error: --database is required for full pipeline")
            return
        run_full_pipeline(args.database, args.clear)
    
    elif args.phase == 1:
        if not args.database:
            print("Error: --database is required for Phase 1")
            return
        run_phase1(args.database, args.output)
    
    elif args.phase == 3:
        run_phase3(args.mapping, args.database, args.clear)
    
    elif args.phase == 4:
        run_phase4(args.mapping, args.database)


if __name__ == "__main__":
    main()
