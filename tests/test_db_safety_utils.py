"""
Safe database naming and validation utilities for testing.

This module provides functions to ensure test databases are properly isolated
and don't interfere with production databases.
"""

import re
import uuid
from datetime import datetime
from typing import List

# Safety: List of protected database names that should never be dropped
PROTECTED_DATABASES = {'dictionary', 'production', 'backup', 'main', 'dev', 'staging'}


def is_safe_database_name(db_name: str) -> bool:
    """
    Validate that a database name is safe for testing.
    
    Args:
        db_name: The database name to validate
        
    Returns:
        True if the database name is safe for testing, False otherwise
    """
    # Must start with 'test_'
    if not db_name.startswith('test_'):
        return False
    
    # Must not contain protected patterns
    db_name_lower = db_name.lower()
    for protected in PROTECTED_DATABASES:
        if protected in db_name_lower:
            return False
            
    # Must match our naming pattern: test_YYYYMMDD_HHMM_<type>_<random>
    # Example: test_20251225_1430_unit_abc123
    pattern = r'test_\d{8}_\d{4}_[a-z]+_[a-f0-9]{6}'
    return bool(re.match(pattern, db_name))


def generate_safe_db_name(test_type: str = 'unit') -> str:
    """
    Generate a safe, unique database name for testing.
    
    Args:
        test_type: Type of test (unit, integration, e2e)
        
    Returns:
        A safe, unique database name
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    random_suffix = uuid.uuid4().hex[:6]
    db_name = f"test_{timestamp}_{test_type}_{random_suffix}"
    
    # Validate the generated name
    if not is_safe_database_name(db_name):
        raise ValueError(f"Generated unsafe database name: {db_name}")
    
    return db_name


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
        return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M')
        
    except (IndexError, ValueError) as e:
        raise ValueError(f"Could not extract timestamp from database name {db_name}: {e}")


def is_protected_database(db_name: str) -> bool:
    """
    Check if a database name is protected and should never be modified.
    
    Args:
        db_name: The database name to check
        
    Returns:
        True if the database is protected, False otherwise
    """
    db_name_lower = db_name.lower()
    return any(protected in db_name_lower for protected in PROTECTED_DATABASES)


def validate_database_safety(db_names: List[str]) -> List[str]:
    """
    Validate a list of database names for safety.
    
    Args:
        db_names: List of database names to validate
        
    Returns:
        List of unsafe database names
    """
    unsafe_dbs = []
    for db_name in db_names:
        if is_protected_database(db_name):
            unsafe_dbs.append(db_name)
        elif db_name.startswith('test_') and not is_safe_database_name(db_name):
            unsafe_dbs.append(db_name)
    return unsafe_dbs


if __name__ == "__main__":
    # Test the utilities
    print("Testing safe database utilities...")
    
    # Test safe name generation
    safe_name = generate_safe_db_name('unit')
    print(f"Generated safe name: {safe_name}")
    print(f"Is safe: {is_safe_database_name(safe_name)}")
    
    # Test timestamp extraction
    timestamp = extract_db_timestamp(safe_name)
    print(f"Extracted timestamp: {timestamp}")
    
    # Test protected databases
    protected_names = ['dictionary', 'production_db', 'test_production_data']
    for name in protected_names:
        print(f"{name} is protected: {is_protected_database(name)}")
    
    print("All tests passed!")