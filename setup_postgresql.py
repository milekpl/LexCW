#!/usr/bin/env python3
"""
PostgreSQL setup script.

Provides utilities for setting up and configuring PostgreSQL for the dictionary project.
"""

import os
from typing import Dict, Any


def load_config_from_env() -> Dict[str, Any]:
    """
    Load PostgreSQL configuration from environment variables.
    
    Returns:
        Dict containing PostgreSQL connection configuration.
    """
    config = {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': int(os.getenv('POSTGRES_PORT', '5432')),
        'database': os.getenv('POSTGRES_DB', 'dictionary'),
        'username': os.getenv('POSTGRES_USER', 'postgres'),
        'password': os.getenv('POSTGRES_PASSWORD', ''),
    }
    return config


if __name__ == '__main__':
    print("PostgreSQL Configuration:")
    config = load_config_from_env()
    for key, value in config.items():
        if key == 'password':
            print(f"  {key}: {'*' * len(str(value)) if value else '(empty)'}")
        else:
            print(f"  {key}: {value}")
