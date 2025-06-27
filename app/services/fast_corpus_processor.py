"""
Fast corpus processor for high-performance linguistic analysis.
Optimized for large-scale processing with minimal spaCy overhead.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional, Iterator, Generator
import hashlib
import time
import gc
import psutil
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager

try:
    import spacy
    from spacy.lang.en import English
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    spacy = None
    English = None

from app.models.corpus_batch import (
    CorpusBatch, ProcessingStats, LinguisticFeatures, 
    CorpusCache, ProcessingConfig
)
from app.utils.exceptions import DatabaseError


class FastCorpusProcessor:
    """High-performance corpus processor with minimal spaCy overhead."""
    
    def __init__(self, postgres_conn, config: Optional[ProcessingConfig] = None):
        """
        Initialize fast corpus processor.
        
        Args:
            postgres_conn: PostgreSQL connection
            config: Processing configuration
        """
        self.postgres_conn = postgres_conn
        self.config = config or ProcessingConfig()
        
        # Performance tracking
        self.cache_hits = 0
        self.cache_misses = 0
        self.total_processed = 0
        
        # Initialize cache
        self._linguistic_cache = CorpusCache() if self.config.cache_enabled else None
        
        # Initialize spaCy with optimizations
        self.nlp = None
        if SPACY_AVAILABLE:
            self._initialize_spacy()
        
        # Performance properties
        self.batch_size = self.config.batch_size
        self.max_workers = self.config.max_workers
        self.cache_enabled = self.config.cache_enabled
    
    def _initialize_spacy(self) -> None:
        """Initialize spaCy with performance optimizations."""
        if not SPACY_AVAILABLE:
            raise ImportError("spaCy not available. Install with: pip install spacy")
        
        try:
            # Load model with minimal components
            self.nlp = spacy.load(
                self.config.spacy_model,
                disable=self.config.disable_components
            )
            
            # Configure for speed
            self.nlp.max_length = self.config.max_text_length
            
            # Optimize pipeline for batch processing
            self._optimize_spacy_pipeline()
            
        except OSError:
            # Fallback to blank model if specific model not available
            self.nlp = English()
            for component in self.config.disable_components:
                if component in self.nlp.pipe_names:
                    self.nlp.remove_pipe(component)
    
    def _optimize_spacy_pipeline(self) -> None:
        """Optimize spaCy pipeline for maximum speed."""
        if not self.nlp:
            return
        
        # Disable expensive components for speed
        for component in self.config.disable_components:
            if component in self.nlp.pipe_names and component not in self.nlp.disabled:
                self.nlp.disable_pipe(component)
    
    @contextmanager
    def _memory_monitor(self):
        """Context manager to monitor memory usage."""
        process = psutil.Process(os.getpid())
        start_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        yield start_memory
        
        end_memory = process.memory_info().rss / 1024 / 1024  # MB
        if end_memory > self.config.max_memory_mb:
            gc.collect()  # Force garbage collection if memory usage too high
    
    def _get_text_hash(self, text: str) -> str:
        """Generate hash for text caching."""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]
    
    def analyze_sentence(self, text: str) -> LinguisticFeatures:
        """
        Analyze single sentence with caching.
        
        Args:
            text: Input text
            
        Returns:
            Linguistic features
        """
        if not text.strip():
            return LinguisticFeatures(
                tokens=[], pos_tags=[], lemmas=[], sentence_length=0
            )
        
        # Check cache first
        text_hash = self._get_text_hash(text)
        if self._linguistic_cache:
            cached_features = self._linguistic_cache.get(text_hash)
            if cached_features:
                self.cache_hits += 1
                return cached_features
            
            self.cache_misses += 1
        
        # Process with spaCy
        features = self._extract_features(text)
        
        # Cache result
        if self._linguistic_cache:
            self._linguistic_cache.put(text_hash, features)
        
        return features
    
    def _extract_features(self, text: str) -> LinguisticFeatures:
        """Extract linguistic features using spaCy."""
        if not self.nlp:
            # Fallback to basic tokenization
            tokens = text.split()
            return LinguisticFeatures(
                tokens=tokens,
                pos_tags=['UNKNOWN'] * len(tokens),
                lemmas=tokens,
                sentence_length=len(tokens)
            )
        
        # Process with spaCy
        doc = self.nlp(text)
        
        tokens = [token.text for token in doc]
        pos_tags = [token.pos_ for token in doc]
        lemmas = [token.lemma_ for token in doc]
        
        return LinguisticFeatures(
            tokens=tokens,
            pos_tags=pos_tags,
            lemmas=lemmas,
            sentence_length=len(tokens)
        )
    
    def extract_linguistic_features(self, text: str) -> Dict[str, Any]:
        """Extract linguistic features as dictionary."""
        features = self.analyze_sentence(text)
        return features.to_dict()
    
    def process_batch(self, sentences: List[str]) -> CorpusBatch:
        """
        Process batch of sentences efficiently.
        
        Args:
            sentences: List of sentences to process
            
        Returns:
            Processed corpus batch
        """
        start_time = time.time()
        processed_count = 0
        failed_count = 0
        errors = []
        
        with self._memory_monitor() as start_memory:
            # Process in smaller chunks for memory efficiency
            chunk_size = min(self.batch_size, len(sentences))
            
            for i in range(0, len(sentences), chunk_size):
                chunk = sentences[i:i + chunk_size]
                
                try:
                    if self.nlp and len(chunk) > 1:
                        # Use spaCy's efficient batch processing
                        docs = list(self.nlp.pipe(chunk, batch_size=chunk_size))
                        processed_count += len(docs)
                    else:
                        # Process individually
                        for sentence in chunk:
                            try:
                                self.analyze_sentence(sentence)
                                processed_count += 1
                            except Exception as e:
                                failed_count += 1
                                errors.append(f"Error processing sentence: {str(e)}")
                
                except Exception as e:
                    failed_count += len(chunk)
                    errors.append(f"Batch processing error: {str(e)}")
                
                # Periodic garbage collection
                gc_interval = max(1, self.config.gc_frequency // chunk_size)
                if (i // chunk_size) % gc_interval == 0:
                    gc.collect()
        
        # Calculate final statistics
        total_time = time.time() - start_time
        current_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        
        batch = CorpusBatch(
            total_sentences=len(sentences),
            processed_sentences=processed_count,
            failed_sentences=failed_count,
            errors=errors
        )
        
        # Update statistics
        total_cache_requests = self.cache_hits + self.cache_misses
        batch.update_stats(
            processing_time=total_time,
            cache_hits=self.cache_hits,
            total_cache_requests=total_cache_requests,
            memory_usage=current_memory
        )
        
        self.total_processed += processed_count
        return batch
    
    def process_parallel(self, sentences: List[str]) -> CorpusBatch:
        """
        Process sentences in parallel for maximum speed.
        
        Args:
            sentences: List of sentences to process
            
        Returns:
            Processed corpus batch
        """
        if self.max_workers <= 1:
            return self.process_batch(sentences)
        
        start_time = time.time()
        chunk_size = max(1, len(sentences) // self.max_workers)
        chunks = [sentences[i:i + chunk_size] for i in range(0, len(sentences), chunk_size)]
        
        total_processed = 0
        total_failed = 0
        all_errors = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_chunk = {
                executor.submit(self.process_batch, chunk): chunk 
                for chunk in chunks
            }
            
            for future in as_completed(future_to_chunk):
                try:
                    result = future.result()
                    total_processed += result.processed_sentences
                    total_failed += result.failed_sentences
                    all_errors.extend(result.errors)
                except Exception as e:
                    chunk = future_to_chunk[future]
                    total_failed += len(chunk)
                    all_errors.append(f"Parallel processing error: {str(e)}")
        
        total_time = time.time() - start_time
        current_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        
        batch = CorpusBatch(
            total_sentences=len(sentences),
            processed_sentences=total_processed,
            failed_sentences=total_failed,
            errors=all_errors
        )
        
        total_cache_requests = self.cache_hits + self.cache_misses
        batch.update_stats(
            processing_time=total_time,
            cache_hits=self.cache_hits,
            total_cache_requests=total_cache_requests,
            memory_usage=current_memory
        )
        
        return batch
    
    def process_file_stream(self, file_lines: Iterator[str]) -> CorpusBatch:
        """
        Process large files with streaming for memory efficiency.
        
        Args:
            file_lines: Iterator of file lines
            
        Returns:
            Processed corpus batch
        """
        return self._process_stream(file_lines)
    
    def _process_stream(self, lines: Iterator[str]) -> CorpusBatch:
        """Internal streaming processor."""
        start_time = time.time()
        total_sentences = 0
        processed_sentences = 0
        failed_sentences = 0
        errors = []
        
        batch_buffer = []
        
        with self._memory_monitor():
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                batch_buffer.append(line)
                total_sentences += 1
                
                # Process in batches to manage memory
                if len(batch_buffer) >= self.batch_size:
                    batch_result = self.process_batch(batch_buffer)
                    processed_sentences += batch_result.processed_sentences
                    failed_sentences += batch_result.failed_sentences
                    errors.extend(batch_result.errors)
                    batch_buffer = []
            
            # Process remaining sentences
            if batch_buffer:
                batch_result = self.process_batch(batch_buffer)
                processed_sentences += batch_result.processed_sentences
                failed_sentences += batch_result.failed_sentences
                errors.extend(batch_result.errors)
        
        total_time = time.time() - start_time
        current_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        
        batch = CorpusBatch(
            total_sentences=total_sentences,
            processed_sentences=processed_sentences,
            failed_sentences=failed_sentences,
            errors=errors
        )
        
        total_cache_requests = self.cache_hits + self.cache_misses
        batch.update_stats(
            processing_time=total_time,
            cache_hits=self.cache_hits,
            total_cache_requests=total_cache_requests,
            memory_usage=current_memory
        )
        
        return batch
    
    def auto_optimize_batch_size(self, sample_sentences: List[str]) -> None:
        """
        Automatically optimize batch size based on performance.
        
        Args:
            sample_sentences: Sample sentences for testing
        """
        if len(sample_sentences) < 100:
            return  # Need enough samples
        
        best_throughput = 0
        best_batch_size = self.batch_size
        
        # Test different batch sizes
        test_sizes = [100, 500, 1000, 2000, 5000]
        
        for test_size in test_sizes:
            if test_size > len(sample_sentences):
                continue
            
            # Test with smaller sample
            test_sample = sample_sentences[:min(test_size, len(sample_sentences))]
            
            start_time = time.time()
            old_batch_size = self.batch_size
            self.batch_size = test_size
            
            try:
                result = self.process_batch(test_sample)
                throughput = result.processing_stats.throughput_sentences_per_sec
                
                if throughput > best_throughput:
                    best_throughput = throughput
                    best_batch_size = test_size
            except Exception:
                pass  # Skip failed test
            finally:
                self.batch_size = old_batch_size
        
        # Apply best batch size
        self.batch_size = best_batch_size
    
    def _measure_performance(self, sentences: List[str]) -> float:
        """Measure processing performance."""
        start_time = time.time()
        self.process_batch(sentences)
        return time.time() - start_time
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get caching statistics."""
        total_requests = self.cache_hits + self.cache_misses
        return {
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'hit_rate': self.cache_hits / total_requests if total_requests > 0 else 0.0,
            'total_processed': self.total_processed
        }
