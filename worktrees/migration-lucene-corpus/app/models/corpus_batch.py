"""
Fast corpus processing models for high-performance linguistic analysis.
Optimized for large-scale corpus processing with minimal memory overhead.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import json


@dataclass
class ProcessingStats:
    """Statistics for corpus processing performance."""
    
    avg_processing_time: float = 0.0
    cache_hit_rate: float = 0.0
    memory_usage_mb: float = 0.0
    total_processing_time: float = 0.0
    throughput_sentences_per_sec: float = 0.0
    failed_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ProcessingStats:
        """Create from dictionary."""
        return cls(**data)


@dataclass
class CorpusBatch:
    """Batch of processed corpus sentences with performance metrics."""
    
    total_sentences: int
    processed_sentences: int = 0
    failed_sentences: int = 0
    processing_stats: Optional[ProcessingStats] = None
    errors: List[str] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize default values."""
        if self.errors is None:
            self.errors = []
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.processing_stats is None:
            self.processing_stats = ProcessingStats()
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_sentences == 0:
            return 0.0
        return self.processed_sentences / self.total_sentences
    
    def add_error(self, error: str) -> None:
        """Add processing error."""
        self.errors.append(error)
        self.failed_sentences += 1
    
    def update_stats(self, 
                    processing_time: float,
                    cache_hits: int,
                    total_cache_requests: int,
                    memory_usage: float) -> None:
        """Update processing statistics."""
        if self.processing_stats is None:
            self.processing_stats = ProcessingStats()
        
        self.processing_stats.total_processing_time = processing_time
        self.processing_stats.avg_processing_time = (
            processing_time / self.processed_sentences if self.processed_sentences > 0 else 0.0
        )
        self.processing_stats.cache_hit_rate = (
            cache_hits / total_cache_requests if total_cache_requests > 0 else 0.0
        )
        self.processing_stats.memory_usage_mb = memory_usage
        self.processing_stats.throughput_sentences_per_sec = (
            self.processed_sentences / processing_time if processing_time > 0 else 0.0
        )
        self.processing_stats.failed_count = self.failed_sentences
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'total_sentences': self.total_sentences,
            'processed_sentences': self.processed_sentences,
            'failed_sentences': self.failed_sentences,
            'success_rate': self.success_rate,
            'processing_stats': self.processing_stats.to_dict() if self.processing_stats else None,
            'errors': self.errors,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CorpusBatch:
        """Create from dictionary."""
        stats_data = data.get('processing_stats')
        processing_stats = ProcessingStats.from_dict(stats_data) if stats_data else None
        
        timestamp_str = data.get('timestamp')
        timestamp = datetime.fromisoformat(timestamp_str) if timestamp_str else None
        
        return cls(
            total_sentences=data['total_sentences'],
            processed_sentences=data.get('processed_sentences', 0),
            failed_sentences=data.get('failed_sentences', 0),
            processing_stats=processing_stats,
            errors=data.get('errors', []),
            timestamp=timestamp
        )


@dataclass
class LinguisticFeatures:
    """Fast linguistic features extracted from text."""
    
    tokens: List[str]
    pos_tags: List[str]
    lemmas: List[str]
    sentence_length: int
    
    # Optional advanced features (computed on demand)
    dependencies: Optional[List[Dict[str, Any]]] = None
    entities: Optional[List[Dict[str, str]]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> LinguisticFeatures:
        """Create from dictionary."""
        return cls(**data)


class CorpusCache:
    """High-performance in-memory cache for linguistic analysis."""
    
    def __init__(self, max_size: int = 100000):
        """Initialize cache with size limit."""
        self.max_size = max_size
        self._cache: Dict[str, LinguisticFeatures] = {}
        self._access_count: Dict[str, int] = {}
        self.hits = 0
        self.misses = 0
    
    def get(self, text_hash: str) -> Optional[LinguisticFeatures]:
        """Get cached features."""
        if text_hash in self._cache:
            self._access_count[text_hash] += 1
            self.hits += 1
            return self._cache[text_hash]
        
        self.misses += 1
        return None
    
    def put(self, text_hash: str, features: LinguisticFeatures) -> None:
        """Cache features with LRU eviction."""
        if len(self._cache) >= self.max_size:
            # Remove least recently used item
            lru_key = min(self._access_count.keys(), key=lambda k: self._access_count[k])
            del self._cache[lru_key]
            del self._access_count[lru_key]
        
        self._cache[text_hash] = features
        self._access_count[text_hash] = 1
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    def clear(self) -> None:
        """Clear cache."""
        self._cache.clear()
        self._access_count.clear()
        self.hits = 0
        self.misses = 0


@dataclass
class ProcessingConfig:
    """Configuration for fast corpus processing."""
    
    batch_size: int = 5000  # Large batches for efficiency
    max_workers: int = 4    # Parallel processing
    cache_enabled: bool = True
    spacy_model: str = "en_core_web_sm"
    
    # spaCy optimizations
    disable_components: List[str] = None
    max_text_length: int = 1000000  # 1MB per text
    
    # Memory management
    max_memory_mb: int = 500
    gc_frequency: int = 1000  # Run GC every N sentences
    
    def __post_init__(self):
        """Initialize default disabled components."""
        if self.disable_components is None:
            # Disable expensive components for speed
            self.disable_components = ['ner', 'parser', 'textcat']
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ProcessingConfig:
        """Create from dictionary."""
        return cls(**data)
