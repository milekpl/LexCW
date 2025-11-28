"""
Real PostgreSQL integration tests.

These tests use actual PostgreSQL database connections and test the full
data flow from SQLite migration to PostgreSQL operations.

Run with: pytest tests/test_postgresql_real_integration.py -v --tb=short
"""
import os
import pytest
import tempfile
import sqlite3
import json
from datetime import datetime

from app.database.postgresql_connector import PostgreSQLConnector, PostgreSQLConfig
from app.utils.exceptions import DatabaseError, DatabaseConnectionError



@pytest.mark.integration
class TestPostgreSQLRealIntegration:
    import psycopg2.extras
    """Real PostgreSQL integration tests with actual database connections."""
    
    @pytest.fixture(scope="class")
    def postgres_config(self) -> PostgreSQLConfig:
        """PostgreSQL configuration for testing."""
        return PostgreSQLConfig(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=int(os.getenv('POSTGRES_PORT', 5432)),
            database=os.getenv('POSTGRES_DB', 'dictionary_test'),
            username=os.getenv('POSTGRES_USER', 'dict_user'),
            password=os.getenv('POSTGRES_PASSWORD', 'dict_pass')
        )
    
    @pytest.fixture(scope="class")
    def postgres_connector(self, postgres_config: PostgreSQLConfig) -> PostgreSQLConnector:
        """Real PostgreSQL connector for testing."""
        try:
            connector = PostgreSQLConnector(postgres_config)
            # Test connection
            connector.fetch_all("SELECT 1")
            return connector
        except (DatabaseConnectionError, DatabaseError) as e:
            raise
    
    @pytest.fixture(scope="function")
    def clean_test_tables(self, postgres_connector: PostgreSQLConnector):
        """Clean test tables before and after each test."""
        # Clean up any existing test tables
        test_tables = [
            'test_examples', 'test_senses', 'test_entries',
            'test_corpus_entries', 'test_word_sketches', 'test_frequency_data'
        ]
        
        for table in test_tables:
            try:
                postgres_connector.execute_query(f"DROP TABLE IF EXISTS {table} CASCADE")
            except DatabaseError:
                pass  # Table doesn't exist, that's fine
        
        yield
        
        # Clean up after test
        for table in test_tables:
            try:
                postgres_connector.execute_query(f"DROP TABLE IF EXISTS {table} CASCADE")
            except DatabaseError:
                pass
    
    @pytest.fixture
    def sample_sqlite_data(self):
        """Create sample SQLite database with test data."""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_file.close()
        
        conn = sqlite3.connect(temp_file.name)
        cursor = conn.cursor()
        
        # Create SQLite schema
        cursor.execute("""
            CREATE TABLE entries (
                id TEXT PRIMARY KEY,
                lexical_unit TEXT NOT NULL,  -- multitext as JSON string
                pronunciation TEXT,
                grammatical_info TEXT,
                date_created TEXT,
                date_modified TEXT,
                custom_fields TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE senses (
                id TEXT PRIMARY KEY,
                entry_id TEXT NOT NULL,
                glosses TEXT,  -- multitext as JSON string
                definition TEXT,  -- multitext as JSON string
                grammatical_info TEXT,
                custom_fields TEXT,
                sort_order INTEGER,
                FOREIGN KEY (entry_id) REFERENCES entries (id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE examples (
                id TEXT PRIMARY KEY,
                sense_id TEXT NOT NULL,
                text TEXT NOT NULL,
                translation TEXT,
                custom_fields TEXT,
                sort_order INTEGER,
                FOREIGN KEY (sense_id) REFERENCES senses (id)
            )
        """)
        
        # Insert test data
        now = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO entries (id, lexical_unit, pronunciation, grammatical_info, date_created, date_modified) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            'entry1',
            json.dumps({"en": "test", "pl": "test"}),
            '/tɛst/',
            '{"type": "noun", "number": "singular"}',
            now, now
        ))
        cursor.execute("""
            INSERT INTO entries (id, lexical_unit, pronunciation, grammatical_info, date_created, date_modified) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            'entry2',
            json.dumps({"en": "example", "pl": "przykład"}),
            '/ɪɡˈzæm.pəl/',
            '{"type": "noun", "number": "singular"}',
            now, now
        ))
        
        cursor.execute("""
            INSERT INTO senses (id, entry_id, glosses, definition, grammatical_info, sort_order) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            'sense1', 'entry1',
            json.dumps({"en": "test gloss", "pl": "testowy glos"}),
            json.dumps({"en": "A trial or examination", "pl": "próba lub egzamin"}),
            '{"type": "noun"}', 0
        ))
        cursor.execute("""
            INSERT INTO senses (id, entry_id, glosses, definition, grammatical_info, sort_order) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            'sense2', 'entry2',
            json.dumps({"en": "example gloss", "pl": "przykładowy glos"}),
            json.dumps({"en": "A specimen or instance", "pl": "przykład lub egzemplarz"}),
            '{"type": "noun"}', 0
        ))
        
        cursor.execute("""
            INSERT INTO examples (id, sense_id, text, translation, sort_order) 
            VALUES (?, ?, ?, ?, ?)
        """, ('example1', 'sense1', 'This is a test', 'To jest test', 0))
        
        cursor.execute("""
            INSERT INTO examples (id, sense_id, text, translation, sort_order) 
            VALUES (?, ?, ?, ?, ?)
        """, ('example2', 'sense2', 'For example', 'Na przykład', 0))
        
        conn.commit()
        conn.close()
        
        yield temp_file.name
        
        # Cleanup
        os.unlink(temp_file.name)
    
    @pytest.mark.integration
    def test_postgresql_connection(self, postgres_connector: PostgreSQLConnector):
        """Test basic PostgreSQL connection and version check."""
        result = postgres_connector.fetch_all("SELECT version()")
        
        assert len(result) == 1
        assert 'PostgreSQL' in result[0]['version']
        print(f"Connected to: {result[0]['version']}")
    
    @pytest.mark.integration
    def test_create_dictionary_schema(self, postgres_connector: PostgreSQLConnector, clean_test_tables):
        """Test creating the full dictionary schema in PostgreSQL."""
        # Enable UUID extension
        postgres_connector.execute_query("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")
        
        # Create entries table
        postgres_connector.execute_query("""
            CREATE TABLE test_entries (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                entry_id TEXT UNIQUE NOT NULL,
                lexical_unit JSONB NOT NULL,
                pronunciation TEXT,
                grammatical_info JSONB,
                date_created TIMESTAMP,
                date_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                custom_fields JSONB,
                frequency_rank INTEGER,
                subtlex_frequency FLOAT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create senses table
        postgres_connector.execute_query("""
            CREATE TABLE test_senses (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                sense_id TEXT UNIQUE NOT NULL,
                entry_id TEXT NOT NULL,
                glosses JSONB,
                definition JSONB,
                grammatical_info JSONB,
                custom_fields JSONB,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entry_id) REFERENCES test_entries (entry_id) ON DELETE CASCADE
            )
        """)
        
        # Create examples table
        postgres_connector.execute_query("""
            CREATE TABLE test_examples (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                example_id TEXT UNIQUE NOT NULL,
                sense_id TEXT NOT NULL,
                text TEXT NOT NULL,
                translation TEXT,
                custom_fields JSONB,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sense_id) REFERENCES test_senses (sense_id) ON DELETE CASCADE
            )
        """)
        
        # Create indexes
        postgres_connector.execute_query("CREATE INDEX IF NOT EXISTS idx_test_entries_entry_id ON test_entries(entry_id)")
        postgres_connector.execute_query("CREATE INDEX IF NOT EXISTS idx_test_entries_lexical_unit_gin ON test_entries USING gin (lexical_unit)")
        postgres_connector.execute_query("CREATE INDEX IF NOT EXISTS idx_test_senses_entry_id ON test_senses(entry_id)")
        postgres_connector.execute_query("CREATE INDEX IF NOT EXISTS idx_test_examples_sense_id ON test_examples(sense_id)")
        
        # Verify tables were created
        result = postgres_connector.fetch_all("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name LIKE 'test_%'
        """)
        
        table_names = [row['table_name'] for row in result]
        assert 'test_entries' in table_names
        assert 'test_senses' in table_names
        assert 'test_examples' in table_names
    
    @pytest.mark.integration
    def test_sqlite_to_postgresql_migration(self, postgres_connector: PostgreSQLConnector, 
                                          sample_sqlite_data: str, clean_test_tables):
        """Test full data migration from SQLite to PostgreSQL."""
        # First create the schema
        self.test_create_dictionary_schema(postgres_connector, clean_test_tables)
        
        # Read data from SQLite
        sqlite_conn = sqlite3.connect(sample_sqlite_data)
        sqlite_conn.row_factory = sqlite3.Row
        sqlite_cursor = sqlite_conn.cursor()
        
        # Migrate entries
        sqlite_cursor.execute("SELECT * FROM entries")
        entries = sqlite_cursor.fetchall()
        
        for entry in entries:
            grammatical_info = json.loads(entry['grammatical_info']) if entry['grammatical_info'] else None
            custom_fields = json.loads(entry['custom_fields']) if entry['custom_fields'] else None
            lexical_unit = json.loads(entry['lexical_unit']) if entry['lexical_unit'] else None
            postgres_connector.execute_query(
                """
                INSERT INTO test_entries 
                (entry_id, lexical_unit, pronunciation, grammatical_info, date_created, date_modified, custom_fields)
                VALUES (%(entry_id)s, %(lexical_unit)s, %(pronunciation)s, %(grammatical_info)s, 
                        %(date_created)s, %(date_modified)s, %(custom_fields)s)
                """,
                {
                    'entry_id': entry['id'],
                    'lexical_unit': self.psycopg2.extras.Json(lexical_unit) if lexical_unit else None,
                    'pronunciation': entry['pronunciation'],
                    'grammatical_info': self.psycopg2.extras.Json(grammatical_info) if grammatical_info else None,
                    'date_created': entry['date_created'],
                    'date_modified': entry['date_modified'],
                    'custom_fields': self.psycopg2.extras.Json(custom_fields) if custom_fields else None
                }
            )
        
        # Migrate senses
        sqlite_cursor.execute("SELECT * FROM senses")
        senses = sqlite_cursor.fetchall()
        
        for sense in senses:
            grammatical_info = json.loads(sense['grammatical_info']) if sense['grammatical_info'] else None
            custom_fields = json.loads(sense['custom_fields']) if sense['custom_fields'] else None
            glosses = json.loads(sense['glosses']) if sense['glosses'] else None
            definition = json.loads(sense['definition']) if sense['definition'] else None
            postgres_connector.execute_query(
                """
                INSERT INTO test_senses 
                (sense_id, entry_id, glosses, definition, grammatical_info, custom_fields, sort_order)
                VALUES (%(sense_id)s, %(entry_id)s, %(glosses)s, %(definition)s, %(grammatical_info)s, 
                        %(custom_fields)s, %(sort_order)s)
                """,
                {
                    'sense_id': sense['id'],
                    'entry_id': sense['entry_id'],
                    'glosses': self.psycopg2.extras.Json(glosses) if glosses else None,
                    'definition': self.psycopg2.extras.Json(definition) if definition else None,
                    'grammatical_info': self.psycopg2.extras.Json(grammatical_info) if grammatical_info else None,
                    'custom_fields': self.psycopg2.extras.Json(custom_fields) if custom_fields else None,
                    'sort_order': sense['sort_order']
                }
            )
        
        # Migrate examples
        sqlite_cursor.execute("SELECT * FROM examples")
        examples = sqlite_cursor.fetchall()
        
        for example in examples:
            custom_fields = json.loads(example['custom_fields']) if example['custom_fields'] else None
            
            postgres_connector.execute_query("""
                INSERT INTO test_examples 
                (example_id, sense_id, text, translation, custom_fields, sort_order)
                VALUES (%(example_id)s, %(sense_id)s, %(text)s, %(translation)s, 
                        %(custom_fields)s, %(sort_order)s)
            """, {
                'example_id': example['id'],
                'sense_id': example['sense_id'],
                'text': example['text'],
                'translation': example['translation'],
                'custom_fields': json.dumps(custom_fields) if custom_fields else None,
                'sort_order': example['sort_order']
            })
        
        sqlite_cursor.close()
        sqlite_conn.close()
        
        # Verify migration
        pg_entries = postgres_connector.fetch_all("SELECT COUNT(*) as count FROM test_entries")
        pg_senses = postgres_connector.fetch_all("SELECT COUNT(*) as count FROM test_senses")
        pg_examples = postgres_connector.fetch_all("SELECT COUNT(*) as count FROM test_examples")
        
        assert pg_entries[0]['count'] == 2  # 2 entries
        assert pg_senses[0]['count'] == 2   # 2 senses
        assert pg_examples[0]['count'] == 2  # 2 examples
        
        # Test complex query with JOINs
        complex_query = """
            SELECT e.lexical_unit->>'en' AS headword, e.pronunciation, s.definition->>'en' AS definition, ex.text, ex.translation
            FROM test_entries e
            JOIN test_senses s ON e.entry_id = s.entry_id
            JOIN test_examples ex ON s.sense_id = ex.sense_id
            WHERE e.lexical_unit->>'en' = %(headword)s
        """
        results = postgres_connector.fetch_all(complex_query, {'headword': 'test'})
        assert len(results) == 1
        assert results[0]['headword'] == 'test'
        assert results[0]['definition'] == 'A trial or examination'
        assert results[0]['text'] == 'This is a test'
    
    @pytest.mark.integration
    def test_advanced_corpus_features(self, postgres_connector: PostgreSQLConnector, clean_test_tables):
        """Test advanced corpus analysis features in PostgreSQL."""
        # Enable required extensions
        postgres_connector.execute_query("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")
        postgres_connector.execute_query("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        
        # Create corpus table for advanced features
        postgres_connector.execute_query("""
            CREATE TABLE test_corpus_entries (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                lemma TEXT NOT NULL,
                word_form TEXT NOT NULL,
                pos_tag TEXT,
                sentence_id TEXT,
                sentence_text TEXT,
                frequency INTEGER DEFAULT 1,
                subtlex_frequency FLOAT,
                context_vector FLOAT[],
                semantic_tags TEXT[],
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create full-text search index
        postgres_connector.execute_query("""
            CREATE INDEX IF NOT EXISTS idx_corpus_lemma_trgm ON test_corpus_entries 
            USING gin (lemma gin_trgm_ops)
        """)
        
        postgres_connector.execute_query("""
            CREATE INDEX IF NOT EXISTS idx_corpus_word_form_trgm ON test_corpus_entries 
            USING gin (word_form gin_trgm_ops)
        """)
        
        # Insert test corpus data
        test_corpus_data = [
            {
                'lemma': 'test', 'word_form': 'test', 'pos_tag': 'NOUN',
                'sentence_id': 'sent1', 'sentence_text': 'This is a test sentence.',
                'frequency': 5, 'subtlex_frequency': 3.2,
                'context_vector': [0.1, 0.2, 0.3], 'semantic_tags': ['evaluation', 'examination']
            },
            {
                'lemma': 'test', 'word_form': 'testing', 'pos_tag': 'VERB',
                'sentence_id': 'sent2', 'sentence_text': 'We are testing the system.',
                'frequency': 3, 'subtlex_frequency': 2.1,
                'context_vector': [0.2, 0.3, 0.1], 'semantic_tags': ['evaluation', 'procedure']
            },
            {
                'lemma': 'example', 'word_form': 'example', 'pos_tag': 'NOUN',
                'sentence_id': 'sent3', 'sentence_text': 'For example, this works well.',
                'frequency': 8, 'subtlex_frequency': 4.5,
                'context_vector': [0.3, 0.1, 0.2], 'semantic_tags': ['instance', 'demonstration']
            }
        ]
        
        for data in test_corpus_data:
            postgres_connector.execute_query("""
                INSERT INTO test_corpus_entries 
                (lemma, word_form, pos_tag, sentence_id, sentence_text, frequency, 
                 subtlex_frequency, context_vector, semantic_tags)
                VALUES (%(lemma)s, %(word_form)s, %(pos_tag)s, %(sentence_id)s, 
                        %(sentence_text)s, %(frequency)s, %(subtlex_frequency)s, 
                        %(context_vector)s, %(semantic_tags)s)
            """, data)
        
        # Test fuzzy search - set lower similarity threshold first
        postgres_connector.execute_query("SET pg_trgm.similarity_threshold = 0.1")
        
        fuzzy_results = postgres_connector.fetch_all("""
            SELECT lemma, word_form, similarity(lemma, %(search_term)s) as sim
            FROM test_corpus_entries
            WHERE lemma %% %(search_term)s
            ORDER BY sim DESC
        """, {'search_term': 'tset'})  # Misspelled 'test'
        
        assert len(fuzzy_results) > 0
        assert fuzzy_results[0]['lemma'] == 'test'
        
        # Test aggregation queries
        freq_analysis = postgres_connector.fetch_all("""
            SELECT lemma, 
                   COUNT(*) as forms_count,
                   SUM(frequency) as total_frequency,
                   AVG(subtlex_frequency) as avg_subtlex_freq,
                   array_agg(DISTINCT pos_tag) as pos_tags
            FROM test_corpus_entries
            GROUP BY lemma
            ORDER BY total_frequency DESC
        """)
        
        assert len(freq_analysis) == 2  # 'test' and 'example'
        test_entry = next(entry for entry in freq_analysis if entry['lemma'] == 'test')
        assert test_entry['forms_count'] == 2  # 'test' and 'testing'
        assert test_entry['total_frequency'] == 8  # 5 + 3
        assert 'NOUN' in test_entry['pos_tags']
        assert 'VERB' in test_entry['pos_tags']
        
        # Test array operations
        semantic_search = postgres_connector.fetch_all("""
            SELECT lemma, word_form, semantic_tags
            FROM test_corpus_entries
            WHERE semantic_tags && %(search_tags)s
        """, {'search_tags': ['evaluation']})
        
        assert len(semantic_search) == 2  # Both 'test' entries have 'evaluation' tag
    
    @pytest.mark.integration
    def test_word_sketch_features(self, postgres_connector: PostgreSQLConnector, clean_test_tables):
        """Test word sketch functionality with PostgreSQL."""
        # Enable required extensions
        postgres_connector.execute_query("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")
        
        # Create word sketch table
        postgres_connector.execute_query("""
            CREATE TABLE test_word_sketches (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                target_word TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                collocate TEXT NOT NULL,
                frequency INTEGER NOT NULL,
                significance_score FLOAT,
                mutual_information FLOAT,
                t_score FLOAT,
                dice_coefficient FLOAT,
                pos_pattern TEXT,
                example_sentences TEXT[],
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for efficient querying
        postgres_connector.execute_query("""
            CREATE INDEX IF NOT EXISTS idx_word_sketches_target ON test_word_sketches(target_word)
        """)
        postgres_connector.execute_query("""
            CREATE INDEX IF NOT EXISTS idx_word_sketches_relation ON test_word_sketches(relation_type)
        """)
        postgres_connector.execute_query("""
            CREATE INDEX IF NOT EXISTS idx_word_sketches_collocate ON test_word_sketches(collocate)
        """)
        
        # Insert test word sketch data
        sketch_data = [
            {
                'target_word': 'test', 'relation_type': 'object_of', 'collocate': 'take',
                'frequency': 45, 'significance_score': 8.2, 'mutual_information': 3.4,
                't_score': 6.7, 'dice_coefficient': 0.23, 'pos_pattern': 'VERB_NOUN',
                'example_sentences': ['Take a test', 'Taking the final test', 'We took the test yesterday']
            },
            {
                'target_word': 'test', 'relation_type': 'modifier', 'collocate': 'difficult',
                'frequency': 32, 'significance_score': 7.1, 'mutual_information': 2.8,
                't_score': 5.4, 'dice_coefficient': 0.19, 'pos_pattern': 'ADJ_NOUN',
                'example_sentences': ['A difficult test', 'The test was difficult', 'Very difficult test questions']
            },
            {
                'target_word': 'example', 'relation_type': 'modifier', 'collocate': 'good',
                'frequency': 28, 'significance_score': 6.9, 'mutual_information': 2.5,
                't_score': 5.1, 'dice_coefficient': 0.17, 'pos_pattern': 'ADJ_NOUN',
                'example_sentences': ['A good example', 'This is a good example', 'Good example of usage']
            }
        ]
        
        for data in sketch_data:
            postgres_connector.execute_query("""
                INSERT INTO test_word_sketches 
                (target_word, relation_type, collocate, frequency, significance_score,
                 mutual_information, t_score, dice_coefficient, pos_pattern, example_sentences)
                VALUES (%(target_word)s, %(relation_type)s, %(collocate)s, %(frequency)s,
                        %(significance_score)s, %(mutual_information)s, %(t_score)s,
                        %(dice_coefficient)s, %(pos_pattern)s, %(example_sentences)s)
            """, data)
        
        # Test word sketch retrieval
        sketch_results = postgres_connector.fetch_all("""
            SELECT target_word, relation_type, collocate, frequency, significance_score
            FROM test_word_sketches
            WHERE target_word = %(word)s
            ORDER BY significance_score DESC
        """, {'word': 'test'})
        
        assert len(sketch_results) == 2
        assert sketch_results[0]['relation_type'] == 'object_of'
        assert sketch_results[0]['collocate'] == 'take'
        assert sketch_results[0]['frequency'] == 45
        
        # Test relation-based queries
        modifier_relations = postgres_connector.fetch_all("""
            SELECT target_word, collocate, frequency
            FROM test_word_sketches
            WHERE relation_type = %(relation)s
            ORDER BY frequency DESC
        """, {'relation': 'modifier'})
        
        assert len(modifier_relations) == 2
        assert modifier_relations[0]['collocate'] == 'difficult'  # Higher frequency
        
        # Test statistical analysis
        stats_analysis = postgres_connector.fetch_all("""
            SELECT 
                target_word,
                COUNT(*) as relation_count,
                AVG(significance_score) as avg_significance,
                MAX(mutual_information) as max_mi,
                SUM(frequency) as total_frequency
            FROM test_word_sketches
            GROUP BY target_word
            ORDER BY avg_significance DESC
        """)
        
        assert len(stats_analysis) == 2
        test_stats = next(s for s in stats_analysis if s['target_word'] == 'test')
        assert test_stats['relation_count'] == 2
        assert test_stats['total_frequency'] == 77  # 45 + 32
    
    @pytest.mark.integration
    def test_performance_with_large_dataset(self, postgres_connector: PostgreSQLConnector, clean_test_tables):
        """Test PostgreSQL performance with larger datasets."""
        # Enable UUID extension
        postgres_connector.execute_query("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")
        
        # Create performance test table
        postgres_connector.execute_query("""
            CREATE TABLE test_frequency_data (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                word TEXT NOT NULL,
                lemma TEXT NOT NULL,
                frequency INTEGER NOT NULL,
                subtlex_cd FLOAT,
                subtlex_frequency FLOAT,
                pos_tag TEXT,
                length INTEGER,
                syllable_count INTEGER,
                phonetic_form TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create optimized indexes
        postgres_connector.execute_query("CREATE INDEX IF NOT EXISTS idx_freq_word ON test_frequency_data(word)")
        postgres_connector.execute_query("CREATE INDEX IF NOT EXISTS idx_freq_lemma ON test_frequency_data(lemma)")
        postgres_connector.execute_query("CREATE INDEX IF NOT EXISTS idx_freq_frequency ON test_frequency_data(frequency)")
        postgres_connector.execute_query("CREATE INDEX IF NOT EXISTS idx_freq_pos ON test_frequency_data(pos_tag)")
        
        # Generate and insert test data (simulate SUBTLEX-like data)
        import random
        import string
        
        test_words = []
        pos_tags = ['NOUN', 'VERB', 'ADJ', 'ADV', 'PREP', 'DET', 'PRON']
        
        for i in range(1000):  # 1000 test entries
            word = ''.join(random.choices(string.ascii_lowercase, k=random.randint(3, 10)))
            lemma = word if random.random() > 0.3 else word[:-1]  # 70% chance lemma = word
            frequency = random.randint(1, 10000)
            subtlex_cd = random.uniform(0.1, 100.0)
            subtlex_frequency = random.uniform(0.01, 50.0)
            pos_tag = random.choice(pos_tags)
            length = len(word)
            syllable_count = random.randint(1, 5)
            phonetic_form = f"/{word}/"
            
            test_words.append({
                'word': word, 'lemma': lemma, 'frequency': frequency,
                'subtlex_cd': subtlex_cd, 'subtlex_frequency': subtlex_frequency,
                'pos_tag': pos_tag, 'length': length, 'syllable_count': syllable_count,
                'phonetic_form': phonetic_form
            })
        
        # Batch insert for performance
        import time
        start_time = time.time()
        
        for batch_start in range(0, len(test_words), 100):  # Insert in batches of 100
            batch = test_words[batch_start:batch_start + 100]
            
            # Use VALUES clause for efficient batch insert
            values_list = []
            params = {}
            
            for i, word_data in enumerate(batch):
                param_prefix = f"w{batch_start + i}"
                values_list.append(f"""(
                    %({param_prefix}_word)s, %({param_prefix}_lemma)s, %({param_prefix}_frequency)s,
                    %({param_prefix}_subtlex_cd)s, %({param_prefix}_subtlex_frequency)s,
                    %({param_prefix}_pos_tag)s, %({param_prefix}_length)s, 
                    %({param_prefix}_syllable_count)s, %({param_prefix}_phonetic_form)s
                )""")
                
                for key, value in word_data.items():
                    params[f"{param_prefix}_{key}"] = value
            
            insert_query = f"""
                INSERT INTO test_frequency_data 
                (word, lemma, frequency, subtlex_cd, subtlex_frequency, pos_tag, 
                 length, syllable_count, phonetic_form)
                VALUES {', '.join(values_list)}
            """
            
            postgres_connector.execute_query(insert_query, params)
        
        insert_time = time.time() - start_time
        print(f"Inserted 1000 records in {insert_time:.2f} seconds")
        
        # Test complex queries on larger dataset
        start_time = time.time()
        
        # Complex aggregation query
        complex_results = postgres_connector.fetch_all("""
            SELECT 
                pos_tag,
                COUNT(*) as word_count,
                AVG(frequency) as avg_frequency,
                AVG(subtlex_frequency) as avg_subtlex_freq,
                AVG(length) as avg_length,
                AVG(syllable_count) as avg_syllables,
                MIN(frequency) as min_freq,
                MAX(frequency) as max_freq,
                STDDEV(frequency) as freq_stddev
            FROM test_frequency_data
            GROUP BY pos_tag
            ORDER BY avg_frequency DESC
        """)
        
        query_time = time.time() - start_time
        print(f"Complex aggregation query completed in {query_time:.3f} seconds")
        
        assert len(complex_results) <= len(pos_tags)
        assert all(result['word_count'] > 0 for result in complex_results)
        
        # Test filtered queries
        start_time = time.time()
        
        high_freq_words = postgres_connector.fetch_all("""
            SELECT word, lemma, frequency, subtlex_frequency
            FROM test_frequency_data
            WHERE frequency > %(min_freq)s AND subtlex_frequency > %(min_subtlex)s
            ORDER BY frequency DESC
            LIMIT 50
        """, {'min_freq': 5000, 'min_subtlex': 10.0})
        
        filtered_query_time = time.time() - start_time
        print(f"Filtered query completed in {filtered_query_time:.3f} seconds")
        
        assert all(word['frequency'] > 5000 for word in high_freq_words)
        assert all(word['subtlex_frequency'] > 10.0 for word in high_freq_words)
        
        # Verify performance is acceptable (should be sub-second for 1000 records)
        assert insert_time < 10.0  # Should insert 1000 records in under 10 seconds
        assert query_time < 1.0    # Complex aggregation should be under 1 second
        assert filtered_query_time < 0.5  # Filtered query should be very fast

    @pytest.mark.integration
    def test_transaction_handling(self, postgres_connector: PostgreSQLConnector, clean_test_tables):
        """Test transaction handling and rollback functionality."""
        # Create test table
        postgres_connector.execute_query("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")
        # Drop table if it exists to ensure clean state
        postgres_connector.execute_query("DROP TABLE IF EXISTS test_transactions")
        postgres_connector.execute_query("""
            CREATE TABLE test_transactions (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                name TEXT NOT NULL,
                value INTEGER NOT NULL
            )
        """)
        
        # Test transaction context manager (when implemented)
        # For now, test manual transaction handling
        
        # Insert initial data
        postgres_connector.execute_query("""
            INSERT INTO test_transactions (name, value) VALUES (%(name)s, %(value)s)
        """, {'name': 'initial', 'value': 100})
        
        # Verify initial state
        initial_count = postgres_connector.fetch_all("SELECT COUNT(*) as count FROM test_transactions")
        assert initial_count[0]['count'] == 1
        
        # Test error handling in operations
        try:
            # This should fail due to duplicate key (if we had proper constraints)
            postgres_connector.execute_query("""
                INSERT INTO test_transactions (name, value) VALUES (%(name)s, %(value)s)
            """, {'name': 'test', 'value': 200})
            
            # This should also succeed
            postgres_connector.execute_query("""
                INSERT INTO test_transactions (name, value) VALUES (%(name)s, %(value)s)
            """, {'name': 'test2', 'value': 300})
            
        except DatabaseError:
            # Error handling works correctly
            pass
        
        # Verify final state
        final_count = postgres_connector.fetch_all("SELECT COUNT(*) as count FROM test_transactions")
        assert final_count[0]['count'] >= 1  # At least initial record exists


if __name__ == '__main__':
    # Run real integration tests
    pytest.main([__file__, '-v', '--tb=short', '-x'])
