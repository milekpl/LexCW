"""
Fast corpus processing tests - optimized for large-scale processing.
Test-driven development for high-performance corpus analysis.
"""

import pytest
from unittest.mock import Mock, patch
import time

from app.services.fast_corpus_processor import FastCorpusProcessor
from app.models.corpus_batch import CorpusBatch, ProcessingStats


class TestFastCorpusProcessor:
    """Test fast corpus processing with performance optimizations."""
    
    @pytest.fixture
    def mock_postgres_conn(self):
        """Mock PostgreSQL connection for testing."""
        mock_conn = Mock()
        mock_cursor = Mock()
        # Properly mock the context manager
        cursor_context = Mock()
        cursor_context.__enter__ = Mock(return_value=mock_cursor)
        cursor_context.__exit__ = Mock(return_value=None)
        mock_conn.cursor.return_value = cursor_context
        mock_cursor.fetchone.return_value = None
        mock_cursor.fetchall.return_value = []
        return mock_conn
    
    @pytest.fixture
    def processor(self, mock_postgres_conn):
        """Create FastCorpusProcessor instance."""
        with patch('app.services.fast_corpus_processor.spacy') as mock_spacy:
            # Mock spaCy to avoid loading actual model
            mock_nlp = Mock()
            mock_doc = Mock()
            mock_doc.text = "test sentence"
            mock_doc.__iter__ = lambda x: iter([Mock(text="test", pos_="NOUN", lemma_="test")])
            mock_nlp.pipe.return_value = [mock_doc]
            mock_nlp.pipe_names = ["tagger", "parser", "ner"]  # Mock pipe names as list
            mock_nlp.disabled = []  # Mock disabled as empty list
            mock_spacy.load.return_value = mock_nlp
            
            processor = FastCorpusProcessor(mock_postgres_conn)
            return processor
    
    def test_processor_initialization(self, processor):
        """Test processor initializes with optimal settings."""
        assert processor.batch_size >= 1000  # Large batches for efficiency
        assert processor.max_workers >= 2     # Parallel processing
        assert processor.cache_enabled is True
        assert hasattr(processor, '_linguistic_cache')
    
    def test_batch_processing_performance(self, processor):
        """Test batch processing meets performance requirements."""
        # Simulate large corpus
        sentences = [f"Test sentence {i}" for i in range(5000)]
        
        start_time = time.time()
        result = processor.process_batch(sentences)
        processing_time = time.time() - start_time
        
        # Should process at least 1000 sentences per second
        throughput = len(sentences) / processing_time
        assert throughput >= 1000, f"Throughput {throughput:.1f} sentences/sec too slow"
        
        assert isinstance(result, CorpusBatch)
        assert result.total_sentences == len(sentences)
        assert result.processing_stats.avg_processing_time < 0.01  # < 10ms per sentence
    
    def test_linguistic_caching(self, processor):
        """Test linguistic analysis caching for repeated content."""
        test_sentence = "The quick brown fox jumps"
        
        # First processing - cache miss
        start_time = time.time()
        result1 = processor.analyze_sentence(test_sentence)
        first_time = time.time() - start_time
        
        # Second processing - cache hit
        start_time = time.time()
        result2 = processor.analyze_sentence(test_sentence)
        second_time = time.time() - start_time
        
        # Cache hit should be at least 10x faster
        assert second_time < first_time / 10
        assert result1 == result2
        assert processor.cache_hits > 0
    
    def test_memory_efficient_streaming(self, processor):
        """Test memory-efficient streaming for large files."""
        # Mock large file processing
        mock_file_lines = (f"Sentence {i}" for i in range(100000))
        
        with patch.object(processor, '_process_stream') as mock_stream:
            mock_stream.return_value = CorpusBatch(
                total_sentences=100000,
                processed_sentences=100000,
                processing_stats=ProcessingStats(
                    avg_processing_time=0.001,
                    cache_hit_rate=0.8,
                    memory_usage_mb=50.0
                )
            )
            
            result = processor.process_file_stream(mock_file_lines)
            
            # Should use streaming, not load everything into memory
            mock_stream.assert_called_once()
            assert result.processing_stats.memory_usage_mb < 100  # Keep memory usage low
    
    def test_parallel_processing(self, processor):
        """Test parallel processing with multiple workers."""
        sentences = [f"Parallel test {i}" for i in range(1000)]
        
        with patch.object(processor, 'max_workers', 4):
            start_time = time.time()
            result = processor.process_parallel(sentences)
            parallel_time = time.time() - start_time
            
            # Reset for sequential processing
            with patch.object(processor, 'max_workers', 1):
                start_time = time.time()
                processor.process_parallel(sentences)
                sequential_time = time.time() - start_time
                
            # Parallel should be faster (allowing for overhead)
            speedup = sequential_time / parallel_time
            assert speedup >= 1.5, f"Parallel speedup {speedup:.1f}x insufficient"
    
    def test_spacy_optimization(self, processor):
        """Test spaCy pipeline optimizations."""
        # Verify spaCy is configured for speed
        with patch.object(processor, 'nlp') as mock_nlp:
            # Should disable unnecessary pipeline components
            expected_disabled = ['ner', 'parser', 'textcat']
            processor._optimize_spacy_pipeline()
            
            # Check that expensive components are disabled
            for component in expected_disabled:
                assert component in processor.nlp.disabled
    
    def test_error_handling_resilience(self, processor):
        """Test graceful error handling without stopping processing."""
        sentences = ["Good sentence", "Bad sentence", "Another good one"]
        
        # Mock spaCy to fail on middle sentence
        def mock_pipe(texts):
            for i, text in enumerate(texts):
                if "Bad" in text:
                    raise Exception("Processing error")
                yield Mock(text=text, __iter__=lambda: iter([]))
        
        with patch.object(processor.nlp, 'pipe', side_effect=mock_pipe):
            result = processor.process_batch(sentences)
            
            # Should process 2 out of 3 sentences
            assert result.processed_sentences == 2
            assert result.failed_sentences == 1
            assert len(result.errors) == 1
    
    def test_batch_size_optimization(self, processor):
        """Test automatic batch size optimization."""
        # Start with small batch
        processor.batch_size = 100
        
        # Simulate processing performance
        sentences = [f"Test {i}" for i in range(1000)]
        
        with patch.object(processor, '_measure_performance') as mock_measure:
            mock_measure.side_effect = [0.5, 0.3, 0.1]  # Improving performance
            
            processor.auto_optimize_batch_size(sentences[:300])
            
            # Should increase batch size for better performance
            assert processor.batch_size > 100
    
    def test_corpus_statistics_collection(self, processor):
        """Test collection of corpus processing statistics."""
        sentences = [f"Statistical test {i}" for i in range(100)]
        
        result = processor.process_batch(sentences)
        
        assert hasattr(result, 'processing_stats')
        stats = result.processing_stats
        assert stats.total_processing_time > 0
        assert 0 <= stats.cache_hit_rate <= 1.0
        assert stats.avg_processing_time > 0
        assert stats.memory_usage_mb > 0
        assert stats.throughput_sentences_per_sec > 0
    
    def test_linguistic_feature_extraction(self, processor):
        """Test fast linguistic feature extraction."""
        sentence = "The researchers analyzed complex linguistic patterns efficiently"
        
        features = processor.extract_linguistic_features(sentence)
        
        # Should extract essential features quickly
        assert 'tokens' in features
        assert 'pos_tags' in features
        assert 'lemmas' in features
        assert len(features['tokens']) > 0
        
        # Should not include expensive features by default
        assert 'dependencies' not in features
        assert 'entities' not in features


class TestCorpusBatch:
    """Test corpus batch processing model."""
    
    def test_batch_creation(self):
        """Test corpus batch initialization."""
        stats = ProcessingStats(
            avg_processing_time=0.005,
            cache_hit_rate=0.75,
            memory_usage_mb=25.0,
            total_processing_time=5.0,
            throughput_sentences_per_sec=1000.0
        )
        
        batch = CorpusBatch(
            total_sentences=1000,
            processed_sentences=950,
            failed_sentences=50,
            processing_stats=stats
        )
        
        assert batch.total_sentences == 1000
        assert batch.processed_sentences == 950
        assert batch.success_rate == 0.95
        assert batch.processing_stats.cache_hit_rate == 0.75
    
    def test_batch_serialization(self):
        """Test batch serialization for database storage."""
        stats = ProcessingStats(
            avg_processing_time=0.001,
            cache_hit_rate=0.9,
            memory_usage_mb=10.0
        )
        
        batch = CorpusBatch(
            total_sentences=500,
            processed_sentences=500,
            processing_stats=stats
        )
        
        serialized = batch.to_dict()
        assert isinstance(serialized, dict)
        assert serialized['total_sentences'] == 500
        assert serialized['success_rate'] == 1.0
        
        # Should be able to recreate from dict
        batch2 = CorpusBatch.from_dict(serialized)
        assert batch2.total_sentences == batch.total_sentences


class TestPerformanceBenchmarks:
    """Performance benchmark tests for corpus processing."""
    
    @pytest.mark.performance
    def test_large_corpus_benchmark(self, processor):
        """Benchmark processing of large corpus."""
        # Test with 10,000 sentences
        large_corpus = [f"Benchmark sentence {i} with various linguistic complexity" for i in range(10000)]
        
        start_time = time.time()
        result = processor.process_batch(large_corpus)
        total_time = time.time() - start_time
        
        # Performance requirements
        assert total_time < 30.0  # Should complete in under 30 seconds
        assert result.processing_stats.throughput_sentences_per_sec >= 500
        assert result.processing_stats.memory_usage_mb < 200  # Memory efficient
        
        print(f"Processed {len(large_corpus)} sentences in {total_time:.1f}s")
        print(f"Throughput: {result.processing_stats.throughput_sentences_per_sec:.1f} sentences/sec")
        print(f"Memory usage: {result.processing_stats.memory_usage_mb:.1f} MB")
