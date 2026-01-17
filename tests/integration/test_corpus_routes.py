"""
Test suite for corpus management routes.
"""
from __future__ import annotations

import io
from unittest.mock import Mock, patch

import pytest
from flask import Flask

from app.routes.corpus_routes import corpus_bp
from app.database.corpus_migrator import MigrationStats


@pytest.fixture
def app():
    """Create test Flask app with corpus routes."""
    test_app = Flask(__name__)
    test_app.config['TESTING'] = True
    test_app.register_blueprint(corpus_bp)

    # Ensure injector is available on the app
    from app import injector
    test_app.injector = injector  # type: ignore

    # Create mock Lucene corpus client for routes that need it
    from unittest.mock import Mock
    mock_client = Mock()
    mock_client.stats.return_value = {
        'total_documents': 1000,
        'avg_source_length': 50.5,
        'avg_target_length': 48.2
    }
    mock_client.clear.return_value = {'documentsDeleted': 0}
    mock_client.optimize.return_value = {'segmentsMerged': 0, 'docs': 0}
    test_app.lucene_corpus_client = mock_client

    return test_app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()



@pytest.mark.integration
class TestCorpusUpload:
    """Test corpus upload functionality."""
    
    @pytest.mark.integration
    def test_upload_tmx_file_success(self, client):
        """Test successful TMX file upload and migration."""
        # Create mock TMX content
        tmx_content = """<?xml version="1.0" encoding="UTF-8"?>
        <tmx version="1.4">
            <body>
                <tu tuid="1">
                    <tuv xml:lang="en"><seg>Hello</seg></tuv>
                    <tuv xml:lang="pl"><seg>Cześć</seg></tuv>
                </tu>
            </body>
        </tmx>"""
        
        with patch('app.routes.corpus_routes.CorpusMigrator') as mock_migrator:
            mock_instance = Mock()
            mock_migrator.return_value = mock_instance
            mock_instance.migrate_tmx_corpus.return_value = MigrationStats(
                records_processed=1,
                records_imported=1
            )
            
            response = client.post('/api/corpus/upload', data={
                'file': (io.BytesIO(tmx_content.encode()), 'test.tmx'),
                'source_lang': 'en',
                'target_lang': 'pl'
            })
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert 'stats' in data
    
    @pytest.mark.integration
    def test_upload_csv_file_success(self, client):
        """Test successful CSV file upload and migration."""
        csv_content = "source_text,target_text\nHello,Cześć\nWorld,Świat"
        
        with patch('app.routes.corpus_routes.CorpusMigrator') as mock_migrator:
            mock_instance = Mock()
            mock_migrator.return_value = mock_instance
            mock_instance.create_database_if_not_exists.return_value = None
            mock_instance.create_schema.return_value = None
            mock_instance.import_csv_to_postgres.return_value = 2
            mock_instance.create_indexes.return_value = None
            mock_instance.stats = MigrationStats(records_imported=2)
            
            response = client.post('/api/corpus/upload', data={
                'file': (io.BytesIO(csv_content.encode()), 'test.csv')
            })
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
    
    @pytest.mark.integration
    def test_upload_no_file_error(self, client):
        """Test error when no file is provided."""
        response = client.post('/api/corpus/upload', data={})
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'No file provided' in data['error']
    
    @pytest.mark.integration
    def test_upload_invalid_file_type(self, client):
        """Test error with invalid file type."""
        response = client.post('/api/corpus/upload', data={
            'file': (io.BytesIO(b'invalid content'), 'test.txt')
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'not supported' in data['error']



@pytest.mark.integration
class TestCorpusStats:
    """Test corpus statistics functionality."""
    
    @pytest.mark.integration
    def test_get_corpus_stats_success(self, client):
        """Test successful retrieval of corpus statistics from Lucene."""
        with patch('app.routes.corpus_routes.CorpusMigrator') as mock_migrator:
            mock_instance = Mock()
            mock_migrator.return_value = mock_instance

            response = client.get('/api/corpus/stats')

            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            # Lucene route returns flat structure with total_records
            assert data['total_records'] == 1000
            assert data['source'] == 'lucene'



@pytest.mark.integration
class TestCorpusCleanup:
    """Test corpus cleanup functionality."""
    
    @pytest.mark.integration
    def test_cleanup_corpus_success(self, client):
        """Test successful corpus cleanup via Lucene clear."""
        response = client.post('/api/corpus/cleanup')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        # Lucene route returns message about cleared documents
        assert 'Cleared' in data['message'] or 'documents' in data['message'].lower()

    @pytest.mark.integration
    def test_deduplicate_corpus_success(self, client):
        """Test successful corpus deduplication via Lucene optimize."""
        response = client.post('/api/corpus/deduplicate')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        # Lucene route returns segments_merged and documents_remaining
        assert 'segments_merged' in data or 'documents_remaining' in data



@pytest.mark.integration
class TestTmxToCsvConversion:
    """Test TMX to CSV conversion functionality."""
    
    @pytest.mark.integration
    def test_convert_tmx_to_csv_success(self, client):
        """Test successful TMX to CSV conversion."""
        tmx_content = """<?xml version="1.0" encoding="UTF-8"?>
        <tmx version="1.4">
            <body>
                <tu tuid="1">
                    <tuv xml:lang="en"><seg>Hello</seg></tuv>
                    <tuv xml:lang="pl"><seg>Cześć</seg></tuv>
                </tu>
            </body>
        </tmx>"""
        
        with patch('app.routes.corpus_routes.CorpusMigrator') as mock_migrator:
            mock_instance = Mock()
            mock_migrator.return_value = mock_instance
            mock_instance.convert_tmx_to_csv.return_value = 1
            
            response = client.post('/api/corpus/convert/tmx-to-csv', data={
                'file': (io.BytesIO(tmx_content.encode()), 'test.tmx'),
                'source_lang': 'en',
                'target_lang': 'pl'
            })
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert data['records_converted'] == 1
            assert 'csv_content' in data
    
    @pytest.mark.integration
    def test_convert_tmx_no_file_error(self, client):
        """Test error when no TMX file is provided."""
        response = client.post('/api/corpus/convert/tmx-to-csv', data={})
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'No TMX file provided' in data['error']
