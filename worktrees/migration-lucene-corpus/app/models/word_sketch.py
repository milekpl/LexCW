"""
Data models for word sketch functionality and corpus analysis.

Provides model classes for word sketches, SUBTLEX norms, frequency analysis,
and corpus sentence processing with strict typing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
import uuid


@dataclass
class WordSketch:
    """
    Represents a grammatical collocation (word sketch) with strength metrics.
    
    Based on Sketch Engine methodology with logDice scoring for collocation strength.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    headword: str = ""
    headword_lemma: str = ""
    headword_pos: str = ""
    collocate: str = ""
    collocate_lemma: str = ""
    collocate_pos: str = ""
    grammatical_relation: str = ""  # e.g., 'subj_of', 'obj_of', 'mod_by'
    relation_pattern: str = ""
    frequency: int = 1
    logdice_score: float = 0.0
    mutual_information: float = 0.0
    t_score: float = 0.0
    sentence_ids: List[str] = field(default_factory=list)
    corpus_source: str = "parallel_corpus"
    confidence_level: float = 1.0
    sketch_grammar_version: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self) -> None:
        """Validate word sketch data after initialization."""
        if not self.headword or not self.collocate:
            raise ValueError("Headword and collocate are required")
        if not self.grammatical_relation:
            raise ValueError("Grammatical relation is required")
        if self.logdice_score < 0:
            raise ValueError("LogDice score cannot be negative")
    
    def __str__(self) -> str:
        """String representation of word sketch."""
        return (f"{self.headword} {self.grammatical_relation} {self.collocate} "
                f"(logDice: {self.logdice_score:.2f})")


@dataclass
class SketchGrammar:
    """
    Represents a sketch grammar pattern for finding grammatical relations.
    
    Stores CQP (Corpus Query Processor) patterns used to identify collocations.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    pattern_name: str = ""  # e.g., 'subj_of', 'obj_of', 'mod_by'
    pattern_cqp: str = ""   # CQP/regex pattern
    pattern_description: str = ""
    language: str = "en"
    pos_constraints: Dict[str, Any] = field(default_factory=dict)
    bidirectional: bool = False
    priority: int = 1
    grammar_source: str = ""
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self) -> None:
        """Validate sketch grammar data."""
        if not self.pattern_name or not self.pattern_cqp:
            raise ValueError("Pattern name and CQP pattern are required")
    
    def __str__(self) -> str:
        """String representation of sketch grammar."""
        return f"{self.pattern_name}: {self.pattern_description}"


@dataclass
class SUBTLEXNorm:
    """
    Represents SUBTLEX frequency norms for psychologically validated word frequencies.
    
    SUBTLEX provides frequency data based on subtitle corpora, validated for
    psychological experiments and linguistic research.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    word: str = ""
    pos_tag: str = ""
    frequency_per_million: float = 0.0
    context_diversity: float = 0.0  # CD measure
    word_length: int = 0
    log_frequency: float = 0.0
    zipf_score: float = 0.0  # Zipf frequency score
    phonological_neighbors: int = 0
    orthographic_neighbors: int = 0
    age_of_acquisition: float = 0.0
    concreteness_rating: float = 0.0
    valence_rating: float = 0.0
    arousal_rating: float = 0.0
    dominance_rating: float = 0.0
    subtlex_dataset: str = "subtlex_us"  # 'subtlex_us', 'subtlex_uk', etc.
    created_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self) -> None:
        """Validate SUBTLEX norm data."""
        if not self.word:
            raise ValueError("Word is required")
        if self.frequency_per_million < 0:
            raise ValueError("Frequency cannot be negative")
        if not 0 <= self.context_diversity <= 1:
            raise ValueError("Context diversity must be between 0 and 1")
    
    def __str__(self) -> str:
        """String representation of SUBTLEX norm."""
        return f"{self.word} ({self.pos_tag}): {self.frequency_per_million:.2f}/M"


@dataclass
class FrequencyAnalysis:
    """
    Combines corpus frequency with SUBTLEX norms for comprehensive frequency analysis.
    
    Provides both domain-specific corpus frequency and psychologically validated
    frequency data for lexicographic decision making.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    word: str = ""
    lemma: str = ""
    pos_tag: str = ""
    corpus_frequency: int = 0
    corpus_relative_freq: float = 0.0
    subtlex_frequency: float = 0.0
    subtlex_context_diversity: float = 0.0
    frequency_ratio: float = 0.0  # corpus_freq / subtlex_freq
    psychological_accessibility: float = 0.0  # Computed accessibility score
    corpus_source: str = ""
    last_updated: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self) -> None:
        """Validate frequency analysis data."""
        if not self.word or not self.lemma:
            raise ValueError("Word and lemma are required")
        if self.corpus_frequency < 0:
            raise ValueError("Corpus frequency cannot be negative")
    
    def calculate_psychological_accessibility(self) -> float:
        """
        Calculate psychological accessibility score based on frequency and diversity.
        
        Combines SUBTLEX frequency and context diversity with corpus-specific
        frequency to generate an accessibility score (0-1 scale).
        
        Returns:
            Psychological accessibility score (0-1)
        """
        if self.subtlex_frequency <= 0:
            return 0.0
        
        # Normalize SUBTLEX frequency (log scale)
        log_subtlex = min(self.subtlex_frequency / 100.0, 1.0)
        
        # Context diversity component
        diversity_component = self.subtlex_context_diversity
        
        # Corpus frequency component (normalized)
        corpus_component = min(self.corpus_frequency / 1000.0, 1.0)
        
        # Weighted combination
        accessibility = (0.5 * log_subtlex + 
                        0.3 * diversity_component + 
                        0.2 * corpus_component)
        
        self.psychological_accessibility = min(accessibility, 1.0)
        return self.psychological_accessibility
    
    def __str__(self) -> str:
        """String representation of frequency analysis."""
        return (f"{self.word}: corpus={self.corpus_frequency}, "
                f"subtlex={self.subtlex_frequency:.2f}, "
                f"accessibility={self.psychological_accessibility:.3f}")


@dataclass
class CorpusSentence:
    """
    Represents a sentence in the parallel corpus with linguistic annotation.
    
    Optimized for sentence-aligned corpora with cached linguistic processing
    to avoid redundant POS tagging and lemmatization.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str = ""
    sentence_number: int = 0
    source_text: str = ""
    target_text: str = ""
    source_tokens: List[str] = field(default_factory=list)
    target_tokens: List[str] = field(default_factory=list)
    source_lemmas: List[str] = field(default_factory=list)
    target_lemmas: List[str] = field(default_factory=list)
    source_pos_tags: List[str] = field(default_factory=list)
    target_pos_tags: List[str] = field(default_factory=list)
    alignment_score: float = 1.0
    linguistic_processed: bool = False
    processing_timestamp: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self) -> None:
        """Validate corpus sentence data."""
        if not self.source_text:
            raise ValueError("Source text is required")
        if not 0 <= self.alignment_score <= 1:
            raise ValueError("Alignment score must be between 0 and 1")
    
    def is_ready_for_processing(self) -> bool:
        """Check if sentence is ready for linguistic processing."""
        return bool(self.source_text and not self.linguistic_processed)
    
    def mark_as_processed(self) -> None:
        """Mark sentence as linguistically processed."""
        self.linguistic_processed = True
        self.processing_timestamp = datetime.now()
    
    def __str__(self) -> str:
        """String representation of corpus sentence."""
        return (f"Sentence {self.sentence_number}: {self.source_text[:50]}... "
                f"-> {self.target_text[:50]}...")


@dataclass
class ProcessingBatch:
    """
    Represents a batch of sentences for efficient processing.
    
    Used to track batch processing operations for POS tagging, lemmatization,
    and word sketch extraction across large corpora.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    batch_type: str = ""  # 'pos_tagging', 'lemmatization', 'word_sketch'
    document_ids: List[str] = field(default_factory=list)
    sentence_range_start: int = 0
    sentence_range_end: int = 0
    status: str = "pending"  # 'pending', 'processing', 'completed', 'failed'
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: str = ""
    processing_stats: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self) -> None:
        """Validate processing batch data."""
        if not self.batch_type:
            raise ValueError("Batch type is required")
        if self.sentence_range_start < 0 or self.sentence_range_end < self.sentence_range_start:
            raise ValueError("Invalid sentence range")
    
    def start_processing(self) -> None:
        """Mark batch as started."""
        self.status = "processing"
        self.started_at = datetime.now()
    
    def complete_processing(self, stats: Optional[Dict[str, Any]] = None) -> None:
        """Mark batch as completed."""
        self.status = "completed"
        self.completed_at = datetime.now()
        if stats:
            self.processing_stats.update(stats)
    
    def fail_processing(self, error: str) -> None:
        """Mark batch as failed."""
        self.status = "failed"
        self.error_message = error
        self.completed_at = datetime.now()
    
    def __str__(self) -> str:
        """String representation of processing batch."""
        return (f"{self.batch_type} batch: {self.sentence_range_start}-"
                f"{self.sentence_range_end} [{self.status}]")
