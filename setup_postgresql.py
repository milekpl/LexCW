#!/usr/bin/env python3
"""
PostgreSQL setup utilities for the dictionary application.
"""

import os
from typing import Dict, Any


def load_config_from_env() -> Dict[str, Any]:
    """
    Load PostgreSQL configuration from environment variables.
    
    Returns:
        Dict containing database configuration.
    """
    return {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': int(os.getenv('POSTGRES_PORT', '5432')),
        'database': os.getenv('POSTGRES_DB', 'dictionary'),
        'username': os.getenv('POSTGRES_USER', 'postgres'),
        'password': os.getenv('POSTGRES_PASSWORD', '')
    }


if __name__ == '__main__':
    print("PostgreSQL configuration:")
    config = load_config_from_env()
    for key, value in config.items():
        print(f"  {key}: {value}")
