"""
Setup PostgreSQL integration testing environment.

This script helps set up PostgreSQL for local testing without Docker.
"""
import os
import sys
import subprocess
import logging

def check_postgresql_connection():
    """Check if PostgreSQL is accessible."""
    try:
        import psycopg2
        
        # Try to connect with default test credentials
        conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=int(os.getenv('POSTGRES_PORT', 5432)),
            database=os.getenv('POSTGRES_DB', 'postgres'),  # Connect to default DB first
            user=os.getenv('POSTGRES_USER', 'postgres'),
            password=os.getenv('POSTGRES_PASSWORD', '')
        )
        conn.close()
        return True
    except psycopg2.Error as e:
        print(f"PostgreSQL connection failed: {e}")
        return False
    except ImportError:
        print("psycopg2 not installed. Run: pip install psycopg2-binary")
        return False

def create_test_database():
    """Create test database if it doesn't exist."""
    try:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
        
        # Connect to PostgreSQL server
        conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=int(os.getenv('POSTGRES_PORT', 5432)),
            database='postgres',  # Connect to default DB
            user=os.getenv('POSTGRES_USER', 'postgres'),
            password=os.getenv('POSTGRES_PASSWORD', '')
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Create test database
        test_db = os.getenv('POSTGRES_TEST_DB', 'dictionary_test')
        test_user = os.getenv('POSTGRES_TEST_USER', 'dict_user')
        test_password = os.getenv('POSTGRES_TEST_PASSWORD', 'dict_pass')
        
        # Create user if doesn't exist
        cursor.execute(f"""
            DO $$ 
            BEGIN
                IF NOT EXISTS (SELECT FROM pg_user WHERE usename = '{test_user}') THEN
                    CREATE USER {test_user} WITH PASSWORD '{test_password}';
                END IF;
            END $$;
        """)
        
        # Create database if doesn't exist
        cursor.execute(f"""
            SELECT 1 FROM pg_database WHERE datname = '{test_db}'
        """)
        
        if not cursor.fetchone():
            cursor.execute(f"CREATE DATABASE {test_db} OWNER {test_user}")
            print(f"Created test database: {test_db}")
        else:
            print(f"Test database already exists: {test_db}")
        
        # Grant permissions
        cursor.execute(f"GRANT ALL PRIVILEGES ON DATABASE {test_db} TO {test_user}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"Failed to create test database: {e}")
        return False

def setup_environment_variables():
    """Set up environment variables for testing."""
    test_env = {
        'POSTGRES_HOST': 'localhost',
        'POSTGRES_PORT': '5432',
        'POSTGRES_DB': 'dictionary_test',
        'POSTGRES_USER': 'dict_user',
        'POSTGRES_PASSWORD': 'dict_pass',
        'TESTING': 'true'
    }
    
    print("Setting up environment variables for testing:")
    for key, value in test_env.items():
        os.environ[key] = value
        print(f"  {key}={value}")

def main():
    """Main setup function."""
    print("PostgreSQL Integration Testing Setup")
    print("=" * 40)
    
    # Check if PostgreSQL is available
    print("1. Checking PostgreSQL connection...")
    if not check_postgresql_connection():
        print("\nPostgreSQL is not available. Please:")
        print("- Install PostgreSQL locally, or")
        print("- Run with Docker: docker-compose up postgres_test")
        print("- Set environment variables for remote PostgreSQL")
        return False
    
    print("✓ PostgreSQL connection successful")
    
    # Setup environment variables
    print("\n2. Setting up environment variables...")
    setup_environment_variables()
    print("✓ Environment variables configured")
    
    # Create test database
    print("\n3. Creating test database...")
    if not create_test_database():
        print("✗ Failed to create test database")
        return False
    
    print("✓ Test database configured")
    
    print("\n" + "=" * 40)
    print("Setup completed successfully!")
    print("\nYou can now run integration tests:")
    print("pytest tests/test_postgresql_real_integration.py -v")
    print("pytest tests/test_migration_real_integration.py -v")
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
