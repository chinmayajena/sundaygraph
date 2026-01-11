#!/usr/bin/env python3
"""Run database migrations."""

import sys
import os
from pathlib import Path

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("ERROR: psycopg2 not installed. Install with: pip install psycopg2-binary")
    sys.exit(1)


def run_migration(connection_string: str, migration_file: Path) -> bool:
    """
    Run a migration file.
    
    Args:
        connection_string: PostgreSQL connection string
        migration_file: Path to migration SQL file
        
    Returns:
        True if successful, False otherwise
    """
    if not migration_file.exists():
        print(f"ERROR: Migration file not found: {migration_file}")
        return False
    
    try:
        conn = psycopg2.connect(connection_string)
        cursor = conn.cursor()
        
        print(f"Running migration: {migration_file.name}")
        
        with open(migration_file, 'r', encoding='utf-8') as f:
            migration_sql = f.read()
        
        cursor.execute(migration_sql)
        conn.commit()
        
        print(f"Migration {migration_file.name} completed successfully")
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"ERROR: Migration failed: {e}")
        if 'conn' in locals():
            conn.rollback()
        return False


def main():
    """Main migration runner."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run database migrations")
    parser.add_argument(
        "--connection-string",
        help="PostgreSQL connection string (e.g., postgresql://user:pass@host:port/db)",
        default=None
    )
    parser.add_argument(
        "--host", default="localhost",
        help="PostgreSQL host (default: localhost)"
    )
    parser.add_argument(
        "--port", type=int, default=5432,
        help="PostgreSQL port (default: 5432)"
    )
    parser.add_argument(
        "--database", default="sundaygraph",
        help="Database name (default: sundaygraph)"
    )
    parser.add_argument(
        "--user", default="postgres",
        help="Database user (default: postgres)"
    )
    parser.add_argument(
        "--password", default="password",
        help="Database password (default: password)"
    )
    parser.add_argument(
        "--migration-dir", default="migrations",
        help="Migration directory (default: migrations)"
    )
    
    args = parser.parse_args()
    
    # Build connection string
    if args.connection_string:
        connection_string = args.connection_string
    else:
        connection_string = f"postgresql://{args.user}:{args.password}@{args.host}:{args.port}/{args.database}"
    
    # Find migration files
    migration_dir = Path(args.migration_dir)
    if not migration_dir.exists():
        print(f"ERROR: Migration directory not found: {migration_dir}")
        sys.exit(1)
    
    migration_files = sorted(migration_dir.glob("*.sql"))
    
    if not migration_files:
        print(f"No migration files found in {migration_dir}")
        sys.exit(1)
    
    print(f"Found {len(migration_files)} migration file(s)")
    print(f"Connection: {args.host}:{args.port}/{args.database}")
    print()
    
    # Run migrations
    success_count = 0
    for migration_file in migration_files:
        if run_migration(connection_string, migration_file):
            success_count += 1
        else:
            print(f"Migration failed: {migration_file.name}")
            sys.exit(1)
    
    print()
    print(f"All migrations completed successfully ({success_count}/{len(migration_files)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
