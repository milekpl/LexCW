#!/usr/bin/env python3
"""Wrapper script to fix encoding issues before importing psycopg2."""

import os
import sys

# Set environment variables before any imports
os.environ['LC_ALL'] = 'C.UTF-8'
os.environ['LC_CTYPE'] = 'C.UTF-8'
os.environ['LANG'] = 'C.UTF-8'
os.environ['PYTHONIOENCODING'] = 'utf-8'

# Now run the actual migration
if __name__ == "__main__":
    from app.database.sqlite_postgres_migrator import main
    main()
