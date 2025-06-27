"""
PostgreSQL Setup and Migration CLI Tool

Command-line interface for setting up PostgreSQL schema and 
migrating data from SQLite to PostgreSQL.
"""
import argparse
import logging
import os
import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.postgresql_connector import PostgreSQLConnector
from app.utils.exceptions import DatabaseError


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def create_schema(connector: PostgreSQLConnector) -> None:
    """Create the complete PostgreSQL schema for dictionary and corpus data."""
    print("Creating PostgreSQL schema...")
    
    # Dictionary tables
    schema_queries = [
        """
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
        """,
        """
        CREATE TABLE IF NOT EXISTS entries (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            entry_id TEXT UNIQUE NOT NULL,
            headword TEXT NOT NULL,
            pronunciation TEXT,
            grammatical_info JSONB,
            date_created TIMESTAMP,
            date_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            custom_fields JSONB,
            frequency_rank INTEGER,
            subtlex_frequency FLOAT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS senses (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            sense_id TEXT UNIQUE NOT NULL,
            entry_id UUID NOT NULL,
            definition TEXT,
            grammatical_info JSONB,
            custom_fields JSONB,
            sort_order INTEGER,
            semantic_field TEXT,
            usage_notes TEXT,
            FOREIGN KEY (entry_id) REFERENCES entries (id) ON DELETE CASCADE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS examples (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            example_id TEXT UNIQUE NOT NULL,
            sense_id UUID NOT NULL,
            text TEXT NOT NULL,
            translation TEXT,
            custom_fields JSONB,
            sort_order INTEGER,
            source TEXT,
            confidence_score FLOAT,
            FOREIGN KEY (sense_id) REFERENCES senses (id) ON DELETE CASCADE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS entry_relations (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            source_id UUID NOT NULL,
            target_id UUID NOT NULL,
            relation_type TEXT NOT NULL,
            is_sense_relation BOOLEAN DEFAULT false,
            confidence FLOAT DEFAULT 1.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (source_id) REFERENCES entries (id) ON DELETE CASCADE,
            FOREIGN KEY (target_id) REFERENCES entries (id) ON DELETE CASCADE
        );
        """,
        # Corpus tables
        """
        CREATE TABLE IF NOT EXISTS corpus_documents (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            document_name TEXT NOT NULL,
            source_language TEXT NOT NULL DEFAULT 'en',
            target_language TEXT NOT NULL DEFAULT 'pl',
            document_type TEXT DEFAULT 'parallel_corpus',
            metadata JSONB,
            sentence_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS corpus_sentence_pairs (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            document_id UUID NOT NULL,
            source_text TEXT NOT NULL,
            target_text TEXT NOT NULL,
            source_id TEXT,
            alignment_score FLOAT DEFAULT 1.0,
            sentence_length_source INTEGER,
            sentence_length_target INTEGER,
            pos_tags_source JSONB,
            pos_tags_target JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (document_id) REFERENCES corpus_documents (id) ON DELETE CASCADE
        );
        """,
        # Indexes for performance
        """
        CREATE INDEX IF NOT EXISTS idx_entries_headword ON entries(headword);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_entries_entry_id ON entries(entry_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_senses_entry_id ON senses(entry_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_examples_sense_id ON examples(sense_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_corpus_pairs_document_id ON corpus_sentence_pairs(document_id);
        """,
        # Full-text search indexes
        """
        CREATE INDEX IF NOT EXISTS idx_corpus_source_text_fts 
        ON corpus_sentence_pairs USING gin(to_tsvector('english', source_text));
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_corpus_target_text_fts 
        ON corpus_sentence_pairs USING gin(to_tsvector('simple', target_text));
        """
    ]
    
    for i, query in enumerate(schema_queries, 1):
        try:
            connector.execute_query(query)
            print(f"✓ Schema step {i}/{len(schema_queries)} completed")
        except Exception as e:
            print(f"✗ Schema step {i} failed: {e}")
            if "already exists" not in str(e):
                raise
    
    print("✓ PostgreSQL schema created successfully!")


def test_connection(connector: PostgreSQLConnector) -> bool:
    """Test PostgreSQL connection and basic functionality."""
    try:
        # Test basic query
        results = connector.fetch_all("SELECT version()")
        if results:
            print(f"✓ PostgreSQL connection successful: {results[0]['version'][:50]}...")
            return True
        else:
            print("✗ PostgreSQL connection failed: No version returned")
            return False
    except Exception as e:
        print(f"✗ PostgreSQL connection failed: {e}")
        return False


def show_status(connector: PostgreSQLConnector) -> None:
    """Show current database status and table counts."""
    print("\nDatabase Status:")
    print("=" * 50)
    
    tables = [
        "entries",
        "senses", 
        "examples",
        "entry_relations",
        "corpus_documents",
        "corpus_sentence_pairs"
    ]
    
    for table in tables:
        try:
            results = connector.fetch_all(f"SELECT COUNT(*) as count FROM {table}")
            count = results[0]['count']
            print(f"{table:25}: {count:>10,} records")
        except Exception as e:
            print(f"{table:25}: ERROR - {e}")


def load_config_from_env() -> dict:
    """Load PostgreSQL configuration from environment variables."""
    return {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': int(os.getenv('POSTGRES_PORT', 5432)),
        'database': os.getenv('POSTGRES_DB', 'dictionary_analytics'),
        'username': os.getenv('POSTGRES_USER', 'dict_user'),
        'password': os.getenv('POSTGRES_PASSWORD', '')
    }


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="PostgreSQL Setup and Migration Tool"
    )
    parser.add_argument(
        'action',
        choices=['setup', 'test', 'status', 'migrate'],
        help='Action to perform'
    )
    parser.add_argument(
        '--sqlite-path',
        help='Path to SQLite database file (for migration)'
    )
    parser.add_argument(
        '--host',
        default=os.getenv('POSTGRES_HOST', 'localhost'),
        help='PostgreSQL host'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=int(os.getenv('POSTGRES_PORT', 5432)),
        help='PostgreSQL port'
    )
    parser.add_argument(
        '--database',
        default=os.getenv('POSTGRES_DB', 'dictionary_analytics'),
        help='PostgreSQL database name'
    )
    parser.add_argument(
        '--username',
        default=os.getenv('POSTGRES_USER', 'dict_user'),
        help='PostgreSQL username'
    )
    parser.add_argument(
        '--password',
        default=os.getenv('POSTGRES_PASSWORD', ''),
        help='PostgreSQL password'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    setup_logging(args.verbose)
    
    # Import here to avoid circular imports
    from app.database.postgresql_connector import PostgreSQLConfig
    
    # Create configuration
    config = PostgreSQLConfig(
        host=args.host,
        port=args.port,
        database=args.database,
        username=args.username,
        password=args.password
    )
    
    try:
        # Create connector
        connector = PostgreSQLConnector(config)
        
        if args.action == 'test':
            success = test_connection(connector)
            sys.exit(0 if success else 1)
        
        elif args.action == 'setup':
            if test_connection(connector):
                create_schema(connector)
                show_status(connector)
            else:
                sys.exit(1)
        
        elif args.action == 'status':
            if test_connection(connector):
                show_status(connector)
            else:
                sys.exit(1)
        
        elif args.action == 'migrate':
            if not args.sqlite_path:
                print("Error: --sqlite-path required for migration")
                sys.exit(1)
            
            if not os.path.exists(args.sqlite_path):
                print(f"Error: SQLite file not found: {args.sqlite_path}")
                sys.exit(1)
            
            print("Migration functionality will be implemented shortly.")
            print(f"SQLite source: {args.sqlite_path}")
            
    except DatabaseError as e:
        print(f"Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
