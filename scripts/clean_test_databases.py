#!/usr/bin/env python3
"""
Utility script to safely clean up orphaned test databases.

This script helps identify and clean up test databases that may have been
left behind due to test failures or incomplete cleanup.
"""

import argparse
import logging
import re
import sys
import os
from datetime import datetime
try:
    from dateutil.parser import parse
except ImportError:
    # Fallback to basic datetime parsing if dateutil is not available
    def parse(timestamp_str):
        """Basic timestamp parser fallback."""
        try:
            return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M')
        except ValueError:
            return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database.basex_connector import BaseXConnector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def find_test_databases() -> list[str]:
    """
    Find all test databases matching our naming pattern.
    
    Returns:
        List of test database names
    """
    connector = BaseXConnector(
        host='localhost',
        port=1984,
        username='admin',
        password='admin',
        database=None
    )

    try:
        connector.connect()
        result = connector.execute_query("db:list()")
        all_dbs = result.split()

        # Filter for test databases
        test_dbs = []
        pattern = r'test_\d{8}_\d{4}_[a-z]+_[a-f0-9]{6}'
        for db in all_dbs:
            if re.match(pattern, db):
                test_dbs.append(db)

        return test_dbs

    except Exception as e:
        logger.error(f"Failed to list databases: {e}")
        return []
    finally:
        try:
            connector.disconnect()
        except Exception:
            pass


def extract_db_timestamp(db_name: str) -> datetime:
    """
    Extract the creation timestamp from a test database name.
    
    Args:
        db_name: The database name
        
    Returns:
        The creation timestamp
        
    Raises:
        ValueError: If the database name doesn't contain a valid timestamp
    """
    try:
        # Extract timestamp parts: test_YYYYMMDD_HHMM_...
        parts = db_name.split('_')
        if len(parts) < 3:
            raise ValueError(f"Invalid database name format: {db_name}")
        
        date_part = parts[1]  # YYYYMMDD
        time_part = parts[2]  # HHMM
        
        # Parse as YYYYMMDD_HHMM
        timestamp_str = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]} {time_part[:2]}:{time_part[2:4]}"
        return parse(timestamp_str)
        
    except (IndexError, ValueError) as e:
        raise ValueError(f"Could not extract timestamp from database name {db_name}: {e}")


def clean_test_databases(dry_run: bool = True, max_age_days: int = 7) -> list[str]:
    """
    Clean up test databases older than specified age.
    
    Args:
        dry_run: If True, only show what would be cleaned without actually dropping
        max_age_days: Maximum age in days for test databases
        
    Returns:
        List of databases that were (or would be) cleaned
    """
    test_dbs = find_test_databases()
    cleaned = []

    if not test_dbs:
        logger.info("No test databases found")
        return cleaned

    logger.info(f"Found {len(test_dbs)} test databases")

    for db_name in test_dbs:
        try:
            # Extract timestamp from database name
            db_time = extract_db_timestamp(db_name)
            age = datetime.now() - db_time
            age_days = age.days
            
            if age_days > max_age_days:
                if dry_run:
                    logger.info(f"[DRY RUN] Would drop: {db_name} (age: {age_days} days, created: {db_time})")
                else:
                    connector = BaseXConnector(
                        host='localhost',
                        port=1984,
                        username='admin',
                        password='admin',
                        database=None
                    )
                    try:
                        connector.connect()
                        # Verify database exists
                        result = connector.execute_query("db:list()")
                        if db_name in result:
                            connector.execute_command(f"DROP DB {db_name}")
                            logger.info(f"Dropped: {db_name} (age: {age_days} days, created: {db_time})")
                            cleaned.append(db_name)
                        else:
                            logger.warning(f"Database {db_name} not found during cleanup")
                    finally:
                        try:
                            connector.disconnect()
                        except Exception:
                            pass
            else:
                logger.debug(f"Keeping recent database: {db_name} (age: {age_days} days)")
                
        except Exception as e:
            logger.error(f"Error processing {db_name}: {e}")

    return cleaned


def list_all_databases() -> None:
    """List all databases on the server."""
    connector = BaseXConnector(
        host='localhost',
        port=1984,
        username='admin',
        password='admin',
        database=None
    )

    try:
        connector.connect()
        result = connector.execute_query("db:list()")
        all_dbs = result.split()
        
        if not all_dbs:
            logger.info("No databases found")
            return
        
        logger.info(f"All databases on server:")
        for db in sorted(all_dbs):
            if db.startswith('test_'):
                logger.info(f"  {db} (test)")
            else:
                logger.info(f"  {db}")
                
    except Exception as e:
        logger.error(f"Failed to list databases: {e}")
    finally:
        try:
            connector.disconnect()
        except Exception:
            pass


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Clean up orphaned test databases",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run - show what would be cleaned
  python clean_test_databases.py --dry-run

  # Actually clean databases older than 7 days
  python clean_test_databases.py --force

  # Clean databases older than 14 days
  python clean_test_databases.py --force --max-age 14

  # List all databases
  python clean_test_databases.py --list-all
        """
    )
    
    parser.add_argument("--dry-run", action="store_true", 
                       help="Show what would be cleaned without actually dropping")
    parser.add_argument("--force", action="store_true",
                       help="Actually drop databases (use with caution)")
    parser.add_argument("--max-age", type=int, default=7,
                       help="Maximum age in days for test databases (default: 7)")
    parser.add_argument("--list-all", action="store_true",
                       help="List all databases on the server")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")

    if args.list_all:
        list_all_databases()
        return

    if args.force:
        logger.info(f"Cleaning test databases older than {args.max_age} days...")
        cleaned = clean_test_databases(dry_run=False, max_age_days=args.max_age)
        logger.info(f"Cleaned {len(cleaned)} test databases")
    else:
        logger.info("Dry run - showing what would be cleaned:")
        clean_test_databases(dry_run=True, max_age_days=args.max_age)


if __name__ == "__main__":
    main()