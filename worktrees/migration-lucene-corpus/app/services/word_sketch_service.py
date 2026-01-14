"""
Word Sketch service for PostgreSQL-backed grammatical collocation analysis.

Implements word sketch functionality based on Sketch Engine methodology,
integrated with PostgreSQL for performance and SUBTLEX for psychological validity.
"""
from __future__ import annotations

import re
import math
import uuid
import hashlib
from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime

from app.database.postgresql_connector import PostgreSQLConnector
from app.models.word_sketch import (
    WordSketch, SketchGrammar, SUBTLEXNorm, 
    FrequencyAnalysis, CorpusSentence, ProcessingBatch
)
from app.utils.exceptions import DatabaseError, ValidationError


class WordSketchService:
    """
    Service for managing word sketches, SUBTLEX integration, and corpus processing.
    
    Provides high-level operations for word sketch extraction, frequency analysis,
    and sentence-aligned corpus processing with PostgreSQL backend.
    """
    
    def __init__(self, postgres_connector: PostgreSQLConnector) -> None:
        """
        Initialize word sketch service.
        
        Args:
            postgres_connector: PostgreSQL database connector
        """
        self.db = postgres_connector
        self.logger = logging.getLogger(__name__)
        self._nlp_model: Any = None  # Lazy-loaded spaCy model
    
    def create_word_sketch_tables(self) -> None:
        """Create all word sketch related tables in PostgreSQL."""
        try:
            self.db.create_word_sketch_tables()
            self.logger.info("Word sketch tables created successfully")
        except DatabaseError as e:
            self.logger.error(f"Failed to create word sketch tables: {e}")
            raise
    
    def insert_word_sketch(self, word_sketch: WordSketch) -> bool:
        """
        Insert a word sketch into the database.
        
        Args:
            word_sketch: WordSketch object to insert
            
        Returns:
            True if insertion successful
            
        Raises:
            DatabaseError: If insertion fails
        """
        query = """
        INSERT INTO word_sketches (
            id, headword, headword_lemma, headword_pos,
            collocate, collocate_lemma, collocate_pos,
            grammatical_relation, relation_pattern, frequency,
            logdice_score, mutual_information, t_score,
            sentence_ids, corpus_source, confidence_level,
            sketch_grammar_version
        ) VALUES (
            %(id)s, %(headword)s, %(headword_lemma)s, %(headword_pos)s,
            %(collocate)s, %(collocate_lemma)s, %(collocate_pos)s,
            %(grammatical_relation)s, %(relation_pattern)s, %(frequency)s,
            %(logdice_score)s, %(mutual_information)s, %(t_score)s,
            %(sentence_ids)s, %(corpus_source)s, %(confidence_level)s,
            %(sketch_grammar_version)s
        )
        """
        
        parameters = {
            'id': word_sketch.id,
            'headword': word_sketch.headword,
            'headword_lemma': word_sketch.headword_lemma,
            'headword_pos': word_sketch.headword_pos,
            'collocate': word_sketch.collocate,
            'collocate_lemma': word_sketch.collocate_lemma,
            'collocate_pos': word_sketch.collocate_pos,
            'grammatical_relation': word_sketch.grammatical_relation,
            'relation_pattern': word_sketch.relation_pattern,
            'frequency': word_sketch.frequency,
            'logdice_score': word_sketch.logdice_score,
            'mutual_information': word_sketch.mutual_information,
            't_score': word_sketch.t_score,
            'sentence_ids': word_sketch.sentence_ids,
            'corpus_source': word_sketch.corpus_source,
            'confidence_level': word_sketch.confidence_level,
            'sketch_grammar_version': word_sketch.sketch_grammar_version
        }
        
        try:
            self.db.execute_query(query, parameters)
            return True
        except DatabaseError as e:
            self.logger.error(f"Failed to insert word sketch: {e}")
            raise
    
    def get_word_sketches(
        self, 
        headword: str, 
        relation: Optional[str] = None,
        min_logdice: float = 0.0,
        limit: int = 100
    ) -> List[WordSketch]:
        """
        Retrieve word sketches for a given headword.
        
        Args:
            headword: The headword to search for
            relation: Optional grammatical relation filter
            min_logdice: Minimum logDice score threshold
            limit: Maximum number of results
            
        Returns:
            List of WordSketch objects
        """
        query = """
        SELECT * FROM word_sketches 
        WHERE headword_lemma = %(headword)s
        AND logdice_score >= %(min_logdice)s
        """
        
        parameters = {
            'headword': headword.lower(),
            'min_logdice': min_logdice
        }
        
        if relation:
            query += " AND grammatical_relation = %(relation)s"
            parameters['relation'] = relation
        
        query += " ORDER BY logdice_score DESC LIMIT %(limit)s"
        parameters['limit'] = limit
        
        try:
            results = self.db.fetch_all(query, parameters)
            return [self._result_to_word_sketch(row) for row in results]
        except DatabaseError as e:
            self.logger.error(f"Failed to fetch word sketches: {e}")
            raise
    
    def calculate_logdice(
        self, 
        collocation_freq: int,
        word1_freq: int,
        word2_freq: int,
        corpus_size: int
    ) -> float:
        """
        Calculate logDice score for collocation strength (Sketch Engine formula).
        
        Args:
            collocation_freq: Frequency of the collocation
            word1_freq: Frequency of first word
            word2_freq: Frequency of second word
            corpus_size: Total corpus size
            
        Returns:
            LogDice score
        """
        if collocation_freq <= 0 or word1_freq <= 0 or word2_freq <= 0:
            return 0.0
        
        # LogDice formula: 14 + log2((2 * collocation_freq) / (word1_freq * word2_freq / corpus_size))
        # Simplified: 14 + log2((2 * collocation_freq * corpus_size) / (word1_freq * word2_freq))
        dice_coefficient = (2 * collocation_freq * corpus_size) / (word1_freq * word2_freq)
        
        if dice_coefficient <= 0:
            return 0.0
        
        logdice = 14 + math.log2(dice_coefficient)
        return max(logdice, 0.0)
    
    def import_subtlex_data(self, subtlex_data: List[Dict[str, Any]]) -> bool:
        """
        Import SUBTLEX frequency norms data into PostgreSQL.
        
        Args:
            subtlex_data: List of SUBTLEX norm dictionaries
            
        Returns:
            True if import successful
            
        Raises:
            DatabaseError: If import fails
        """
        if not subtlex_data:
            raise ValidationError("No SUBTLEX data provided")
        
        query = """
        INSERT INTO subtlex_norms (
            word, pos_tag, frequency_per_million, context_diversity,
            word_length, log_frequency, zipf_score, phonological_neighbors,
            orthographic_neighbors, age_of_acquisition, concreteness_rating,
            valence_rating, arousal_rating, dominance_rating, subtlex_dataset
        ) VALUES (
            %(word)s, %(pos_tag)s, %(frequency_per_million)s, %(context_diversity)s,
            %(word_length)s, %(log_frequency)s, %(zipf_score)s, %(phonological_neighbors)s,
            %(orthographic_neighbors)s, %(age_of_acquisition)s, %(concreteness_rating)s,
            %(valence_rating)s, %(arousal_rating)s, %(dominance_rating)s, %(subtlex_dataset)s
        ) ON CONFLICT (word, pos_tag, subtlex_dataset) DO UPDATE SET
            frequency_per_million = EXCLUDED.frequency_per_million,
            context_diversity = EXCLUDED.context_diversity
        """
        
        # Prepare batch transaction
        transactions = []
        for norm_data in subtlex_data:
            parameters = {
                'word': norm_data.get('word', ''),
                'pos_tag': norm_data.get('pos_tag', ''),
                'frequency_per_million': norm_data.get('frequency_per_million', 0.0),
                'context_diversity': norm_data.get('context_diversity', 0.0),
                'word_length': norm_data.get('word_length', 0),
                'log_frequency': norm_data.get('log_frequency', 0.0),
                'zipf_score': norm_data.get('zipf_score', 0.0),
                'phonological_neighbors': norm_data.get('phonological_neighbors', 0),
                'orthographic_neighbors': norm_data.get('orthographic_neighbors', 0),
                'age_of_acquisition': norm_data.get('age_of_acquisition', 0.0),
                'concreteness_rating': norm_data.get('concreteness_rating', 0.0),
                'valence_rating': norm_data.get('valence_rating', 0.0),
                'arousal_rating': norm_data.get('arousal_rating', 0.0),
                'dominance_rating': norm_data.get('dominance_rating', 0.0),
                'subtlex_dataset': norm_data.get('subtlex_dataset', 'subtlex_us')
            }
            transactions.append((query, parameters))
        
        try:
            self.db.execute_transaction(transactions)
            self.logger.info(f"Imported {len(subtlex_data)} SUBTLEX norms")
            return True
        except DatabaseError as e:
            self.logger.error(f"Failed to import SUBTLEX data: {e}")
            raise
    
    def calculate_psychological_accessibility(
        self,
        subtlex_freq: float,
        context_diversity: float,
        corpus_freq: int
    ) -> float:
        """
        Calculate psychological accessibility score.
        
        Combines SUBTLEX frequency, context diversity, and corpus frequency
        to generate an accessibility score for lexicographic prioritization.
        
        Args:
            subtlex_freq: SUBTLEX frequency per million
            context_diversity: SUBTLEX context diversity measure
            corpus_freq: Corpus-specific frequency
            
        Returns:
            Psychological accessibility score (0-1)
        """
        if subtlex_freq <= 0:
            return 0.0
        
        # Normalize SUBTLEX frequency (log scale, max ~100/M)
        log_subtlex = min(math.log10(subtlex_freq + 1) / 2.0, 1.0)
        
        # Context diversity component (already 0-1)
        diversity_component = min(context_diversity, 1.0)
        
        # Corpus frequency component (normalized by typical maximum)
        corpus_component = min(corpus_freq / 1000.0, 1.0)
        
        # Weighted combination: SUBTLEX frequency most important
        accessibility = (0.5 * log_subtlex + 
                        0.3 * diversity_component + 
                        0.2 * corpus_component)
        
        return min(accessibility, 1.0)
    
    def get_frequency_analysis(self, word: str, pos_tag: str) -> Optional[FrequencyAnalysis]:
        """
        Get combined frequency analysis for a word.
        
        Args:
            word: Word to analyze
            pos_tag: Part of speech tag
            
        Returns:
            FrequencyAnalysis object or None if not found
        """
        query = """
        SELECT 
            f.word, f.lemma, f.pos_tag, f.corpus_frequency,
            f.corpus_relative_freq, f.subtlex_frequency,
            f.subtlex_context_diversity, f.frequency_ratio,
            f.psychological_accessibility, f.corpus_source
        FROM frequency_analysis f
        WHERE f.lemma = %(word)s AND f.pos_tag = %(pos_tag)s
        """
        
        try:
            result = self.db.fetch_one(query, {'word': word.lower(), 'pos_tag': pos_tag})
            if result:
                return FrequencyAnalysis(**result)
            return None
        except DatabaseError as e:
            self.logger.error(f"Failed to fetch frequency analysis: {e}")
            raise
    
    def process_sentence_batch(self, batch_size: int = 1000) -> bool:
        """
        Process a batch of unprocessed sentences for linguistic annotation.
        
        Args:
            batch_size: Number of sentences to process in batch
            
        Returns:
            True if processing successful
        """
        # Get unprocessed sentences
        query = """
        SELECT id, source_text, target_text 
        FROM corpus_sentences 
        WHERE linguistic_processed = false 
        LIMIT %(batch_size)s
        """
        
        try:
            sentences = self.db.fetch_all(query, {'batch_size': batch_size})
            if not sentences:
                self.logger.info("No unprocessed sentences found")
                return True
            
            # Process sentences (would integrate with spaCy here)
            for sentence in sentences:
                self._process_single_sentence(sentence)
            
            self.logger.info(f"Processed {len(sentences)} sentences")
            return True
            
        except DatabaseError as e:
            self.logger.error(f"Failed to process sentence batch: {e}")
            raise
    
    def extract_word_sketches(self, sentences: List[CorpusSentence]) -> List[WordSketch]:
        """
        Extract word sketches from processed sentences.
        
        Args:
            sentences: List of linguistically processed sentences
            
        Returns:
            List of extracted word sketches
        """
        sketches = []
        
        for sentence in sentences:
            if not sentence.linguistic_processed:
                continue
                
            # Apply sketch patterns to find collocations
            sentence_sketches = self._extract_sketches_from_sentence(sentence)
            sketches.extend(sentence_sketches)
        
        return sketches
    
    def get_linguistic_analysis(self, text: str, language: str = 'en') -> Optional[Dict[str, Any]]:
        """
        Get linguistic analysis with caching to avoid reprocessing.
        
        Args:
            text: Text to analyze
            language: Language code
            
        Returns:
            Dictionary with tokens, lemmas, POS tags
        """
        # Generate cache key
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        
        # Check cache
        cache_query = """
        SELECT tokens, lemmas, pos_tags 
        FROM linguistic_cache 
        WHERE text_hash = %(text_hash)s AND language = %(language)s
        """
        
        try:
            cached = self.db.fetch_one(cache_query, {
                'text_hash': text_hash, 
                'language': language
            })
            
            if cached:
                return cached
            
            # Process and cache
            analysis = self._analyze_text(text, language)
            self._cache_linguistic_analysis(text_hash, text, language, analysis)
            return analysis
            
        except DatabaseError as e:
            self.logger.error(f"Failed to get linguistic analysis: {e}")
            return None
    
    def load_sketch_patterns(self, patterns: List[Dict[str, Any]]) -> bool:
        """
        Load sketch grammar patterns into the database.
        
        Args:
            patterns: List of sketch grammar pattern dictionaries
            
        Returns:
            True if loading successful
        """
        query = """
        INSERT INTO sketch_grammars (
            pattern_name, pattern_cqp, pattern_description,
            language, pos_constraints, bidirectional,
            priority, grammar_source
        ) VALUES (
            %(pattern_name)s, %(pattern_cqp)s, %(pattern_description)s,
            %(language)s, %(pos_constraints)s, %(bidirectional)s,
            %(priority)s, %(grammar_source)s
        ) ON CONFLICT (pattern_name, language) DO UPDATE SET
            pattern_cqp = EXCLUDED.pattern_cqp,
            pattern_description = EXCLUDED.pattern_description
        """
        
        transactions = []
        for pattern in patterns:
            parameters = {
                'pattern_name': pattern.get('pattern_name', ''),
                'pattern_cqp': pattern.get('pattern_cqp', ''),
                'pattern_description': pattern.get('pattern_description', ''),
                'language': pattern.get('language', 'en'),
                'pos_constraints': pattern.get('pos_constraints', {}),
                'bidirectional': pattern.get('bidirectional', False),
                'priority': pattern.get('priority', 1),
                'grammar_source': pattern.get('grammar_source', '')
            }
            transactions.append((query, parameters))
        
        try:
            self.db.execute_transaction(transactions)
            return True
        except DatabaseError as e:
            self.logger.error(f"Failed to load sketch patterns: {e}")
            raise
    
    def apply_sketch_patterns(self, sentence_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Apply sketch patterns to find grammatical relations in sentence.
        
        Args:
            sentence_data: Dictionary with tokens, lemmas, pos_tags
            
        Returns:
            List of collocation matches
        """
        matches = []
        tokens = sentence_data.get('tokens', [])
        lemmas = sentence_data.get('lemmas', [])
        pos_tags = sentence_data.get('pos_tags', [])
        
        if len(tokens) != len(lemmas) or len(tokens) != len(pos_tags):
            return matches
        
        # Simple pattern matching for verb-adverb modification
        for i in range(len(tokens) - 1):
            if pos_tags[i] == 'VERB' and pos_tags[i + 1] == 'ADV':
                matches.append({
                    'headword': tokens[i],
                    'headword_lemma': lemmas[i],
                    'collocate': tokens[i + 1],
                    'collocate_lemma': lemmas[i + 1],
                    'relation': 'mod_by',
                    'position': i
                })
        
        return matches
    
    def _result_to_word_sketch(self, row: Dict[str, Any]) -> WordSketch:
        """Convert database row to WordSketch object."""
        return WordSketch(
            id=row.get('id', str(uuid.uuid4())),
            headword=row['headword'],
            headword_lemma=row.get('headword_lemma', row['headword']),
            headword_pos=row.get('headword_pos', 'UNKNOWN'),
            collocate=row['collocate'],
            collocate_lemma=row.get('collocate_lemma', row['collocate']),
            collocate_pos=row.get('collocate_pos', 'UNKNOWN'),
            grammatical_relation=row['grammatical_relation'],
            relation_pattern=row.get('relation_pattern', ''),
            frequency=row['frequency'],
            logdice_score=row['logdice_score'],
            mutual_information=row.get('mutual_information', 0.0),
            t_score=row.get('t_score', 0.0),
            sentence_ids=row.get('sentence_ids', []),
            corpus_source=row.get('corpus_source', 'parallel_corpus'),
            confidence_level=row.get('confidence_level', 1.0),
            sketch_grammar_version=row.get('sketch_grammar_version', ''),
            created_at=row.get('created_at', datetime.now())
        )
    
    def _process_single_sentence(self, sentence: Dict[str, Any]) -> None:
        """Process a single sentence for linguistic annotation."""
        # This would integrate with spaCy processing
        # For now, simulate processing
        update_query = """
        UPDATE corpus_sentences 
        SET linguistic_processed = true, processing_timestamp = CURRENT_TIMESTAMP
        WHERE id = %(sentence_id)s
        """
        self.db.execute_query(update_query, {'sentence_id': sentence['id']})
    
    def _extract_sketches_from_sentence(self, sentence: CorpusSentence) -> List[WordSketch]:
        """Extract word sketches from a single processed sentence."""
        sketches = []
        
        # Apply basic verb-adverb pattern
        tokens = sentence.source_tokens
        lemmas = sentence.source_lemmas
        pos_tags = sentence.source_pos_tags
        
        for i in range(len(tokens) - 1):
            if len(pos_tags) > i + 1 and pos_tags[i] == 'VERB' and pos_tags[i + 1] == 'ADV':
                sketch = WordSketch(
                    headword=tokens[i],
                    headword_lemma=lemmas[i] if i < len(lemmas) else tokens[i],
                    headword_pos='VERB',
                    collocate=tokens[i + 1],
                    collocate_lemma=lemmas[i + 1] if i + 1 < len(lemmas) else tokens[i + 1],
                    collocate_pos='ADV',
                    grammatical_relation='mod_by',
                    frequency=1,
                    logdice_score=5.0,  # Would be calculated properly
                    sentence_ids=[sentence.id]
                )
                sketches.append(sketch)
        
        return sketches
    
    def _analyze_text(self, text: str, language: str) -> Dict[str, Any]:
        """Analyze text for linguistic features (would use spaCy)."""
        # Simplified analysis for testing - preserve original case for consistency
        tokens = text.split()
        return {
            'tokens': tokens,
            'lemmas': tokens,  # Keep original case for consistency
            'pos_tags': ['NOUN'] * len(tokens)  # Simplified
        }
    
    def _cache_linguistic_analysis(
        self, 
        text_hash: str, 
        text: str, 
        language: str, 
        analysis: Dict[str, Any]
    ) -> None:
        """Cache linguistic analysis results."""
        query = """
        INSERT INTO linguistic_cache (
            text_hash, original_text, language, tokens, lemmas, pos_tags
        ) VALUES (
            %(text_hash)s, %(original_text)s, %(language)s, 
            %(tokens)s, %(lemmas)s, %(pos_tags)s
        )
        """
        
        parameters = {
            'text_hash': text_hash,
            'original_text': text,
            'language': language,
            'tokens': analysis.get('tokens', []),
            'lemmas': analysis.get('lemmas', []),
            'pos_tags': analysis.get('pos_tags', [])
        }
        
        try:
            self.db.execute_query(query, parameters)
        except DatabaseError:
            # Cache insertion failure is not critical
            pass
