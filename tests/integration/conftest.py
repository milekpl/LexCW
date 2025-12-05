"""
Conftest for integration tests.
Imports fixtures from parent conftest.
"""

from __future__ import annotations

import sys
import os

# Add parent directory to Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Import fixtures from parent conftest
from tests.conftest import (
    basex_available,
    test_db_name,
    basex_test_connector,
    dict_service_with_db,
)

__all__ = [
    'basex_available',
    'test_db_name',
    'basex_test_connector',
    'dict_service_with_db',
]
