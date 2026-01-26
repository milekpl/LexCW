"""
Entry enrichment service using word sketch data.

This service provides enrichment proposals for dictionary entries:
- Collocations with grammatical relations
- Example sentences from parallel corpus (with translations)
- Suggested subentry structures
- Confidence scores for each proposal
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class EnrichmentProposal:
    """Proposed enrichment for an entry."""
    proposal_type: str  # 'collocate', 'example', 'translation', 'subentry', 'gloss'
    value: str
    confidence: float  # 0.0 - 1.0
    grammatical_relation: Optional[str] = None
    relation_name: Optional[str] = None
    examples: List[str] = field(default_factory=list)
    translations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.proposal_type,
            'value': self.value,
            'confidence': round(self.confidence, 2),
            'relation': self.grammatical_relation,
            'relation_name': self.relation_name,
            'examples': self.examples,
            'translations': self.translations,
            'metadata': self.metadata
        }


@dataclass
class SubentryDraft:
    """Draft structure for a new subentry based on collocation data."""
    suggested_headword: str
    parent_lemma: str
    relation_type: str
    relation_name: str
    definition_template: str
    examples: List[str] = field(default_factory=list)
    translations: List[str] = field(default_factory=list)
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'suggested_headword': self.suggested_headword,
            'parent_lemma': self.parent_lemma,
            'relation_type': self.relation_type,
            'relation_name': self.relation_name,
            'definition_template': self.definition_template,
            'examples': self.examples,
            'translations': self.translations,
            'confidence': round(self.confidence, 2),
            'metadata': self.metadata
        }


class EnrichmentService:
    """
    Provides enrichment data for dictionary entries.

    Integrates with:
    - Word sketch service for collocations
    - Lucene corpus for examples (parallel corpus with translations)
    """

    # =============================================================================
    # THRESHOLDS FOR ENRICHMENT PROPOSALS
    # =============================================================================
    # These thresholds are based on corpus linguistics research and determine
    # which collocations and examples are statistically significant enough
    # to propose as dictionary enrichments.
    #
    # Scientific basis:
    # - logDice measures association strength on 0-14 scale; values > 6 indicate
    #   strong association (Lampatou & Koplenig, 2013)
    # - Minimum frequency ensures reliability; sparse data (< 3 occurrences)
    #   has high variance and unreliable statistics
    # - Example limits prevent overwhelming users with too many suggestions

    # Minimum logDice score for a collocation to be proposed.
    # logDice = 14 - (logdice formula), on 0-14 scale where 14 = perfect association.
    # Threshold of 6.0 captures moderately strong associations while filtering noise.
    # Research (Rychly, 2008) suggests scores above 6 indicate meaningful collocations.
    MIN_LOGDICE_FOR_PROPOSAL = 6.0

    # Minimum frequency count for a collocation to be considered.
    # Values below 3 have high statistical variance and unreliable logDice scores.
    # This ensures each proposed collocation has been observed multiple times.
    MIN_FREQUENCY_FOR_PROPOSAL = 3

    # Maximum number of example sentences to include per proposal.
    # Balances providing enough context (for understanding) against information overload.
    # 5 examples typically shows sufficient usage patterns without overwhelming.
    MAX_EXAMPLES_PER_PROPOSAL = 5

    # Maximum total number of enrichment proposals to return.
    # Limits response size and processing time while covering diverse enrichments.
    # 20 proposals provides good coverage for most lemma entries.
    MAX_PROPOSALS = 20

    def __init__(
        self,
        word_sketch_client=None,
        corpus_client=None
    ):
        """
        Initialize the enrichment service.

        Args:
            word_sketch_client: WordSketchClient instance
            corpus_client: LuceneCorpusClient instance for parallel examples
        """
        from app.services.word_sketch import WordSketchClient

        self.ws_client = word_sketch_client or WordSketchClient()
        self.logger = logging.getLogger(__name__)

        # LuceneCorpusClient is optional - it may not be available in all environments
        try:
            from app.services.lucene_corpus_client import LuceneCorpusClient
            self.corpus_client = corpus_client or LuceneCorpusClient()
        except ImportError:
            self.corpus_client = corpus_client
            self.logger.warning(
                "LuceneCorpusClient not available - example translations disabled. "
                "Ensure app.services.lucene_corpus_client is installed."
            )

    def get_enrichment_proposals(
        self,
        lemma: str,
        pos: str = None,
        include_examples: bool = True,
        max_proposals: int = None
    ) -> List[EnrichmentProposal]:
        """
        Get all enrichment proposals for a lemma.

        Args:
            lemma: Entry lemma
            pos: Optional part of speech
            include_examples: Whether to fetch corpus examples
            max_proposals: Maximum number of proposals (default: MAX_PROPOSALS)

        Returns:
            List of enrichment proposals sorted by confidence
        """
        max_proposals = max_proposals or self.MAX_PROPOSALS
        proposals = []

        # Get word sketch data
        sketch = self.ws_client.word_sketch(lemma, pos, self.MIN_LOGDICE_FOR_PROPOSAL)

        if sketch:
            # Generate collocation proposals
            for coll in sketch.collocations:
                if coll.frequency < self.MIN_FREQUENCY_FOR_PROPOSAL:
                    continue

                proposal = EnrichmentProposal(
                    proposal_type='collocate',
                    value=coll.collocate,
                    confidence=self._calculate_confidence(coll),
                    grammatical_relation=coll.relation,
                    relation_name=coll.relation_name,
                    examples=coll.examples[:self.MAX_EXAMPLES_PER_PROPOSAL],
                    metadata={
                        'logdice': coll.logdice,
                        'frequency': coll.frequency
                    }
                )
                proposals.append(proposal)

        # Add example sentences if requested
        if include_examples:
            example_proposals = self._get_example_proposals(lemma)
            proposals.extend(example_proposals)

        # Sort by confidence and limit
        proposals.sort(key=lambda p: p.confidence, reverse=True)

        return proposals[:max_proposals]

    def get_collocations_for_entry(
        self,
        lemma: str,
        pos: str = None,
        min_logdice: float = None
    ) -> List[EnrichmentProposal]:
        """
        Get collocation proposals for an entry.

        Specifically useful for adding collocations to existing senses.
        """
        min_logdice = min_logdice or self.MIN_LOGDICE_FOR_PROPOSAL
        proposals = []

        sketch = self.ws_client.word_sketch(lemma, pos, min_logdice)

        if sketch:
            for coll in sketch.collocations:
                if coll.frequency < self.MIN_FREQUENCY_FOR_PROPOSAL:
                    continue

                proposals.append(EnrichmentProposal(
                    proposal_type='collocate',
                    value=coll.collocate,
                    confidence=self._calculate_confidence(coll),
                    grammatical_relation=coll.relation,
                    relation_name=coll.relation_name,
                    examples=coll.examples[:3],
                    metadata={
                        'logdice': coll.logdice,
                        'frequency': coll.frequency
                    }
                ))

        return sorted(proposals, key=lambda p: p.confidence, reverse=True)

    def get_examples_with_translations(
        self,
        lemma: str,
        collocate: str = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get example sentences with translations from parallel corpus.

        Args:
            lemma: Headword lemma
            collocate: Optional collocate to narrow examples
            limit: Maximum number of examples

        Returns:
            List of example objects with 'source', 'target', 'translation'
        """
        examples = []

        try:
            # Use the Lucene corpus client for parallel examples
            query = lemma
            if collocate:
                query = f'"{lemma}" AND "{collocate}"'

            count, hits = self.corpus_client.concordance(query, limit=limit)

            for hit in hits:
                examples.append({
                    'source': f"{hit.left} {hit.match} {hit.right}",
                    'match': hit.match,
                    'left': hit.left,
                    'right': hit.right,
                    'translation': None  # Translation would come from parallel field
                })

        except Exception as e:
            self.logger.warning(f"Failed to fetch examples for {lemma}: {e}")

        return examples

    def draft_subentry(
        self,
        parent_lemma: str,
        collocate: str,
        relation: str,
        relation_name: str = "",
        examples: List[str] = None
    ) -> SubentryDraft:
        """
        Draft a new subentry based on collocation data.

        Creates a structure ready for manual review and editing.

        Args:
            parent_lemma: The headword this subentry relates to
            collocate: The collocate word
            relation: Grammatical relation ID
            relation_name: Human-readable relation name
            examples: Example sentences

        Returns:
            SubentryDraft ready for review
        """
        # Calculate confidence based on collocate strength
        sketch = self.ws_client.word_sketch(parent_lemma)
        confidence = 0.5  # Default

        if sketch:
            for coll in sketch.collocations:
                if coll.collocate.lower() == collocate.lower():
                    confidence = self._calculate_confidence(coll)
                    break

        # Generate definition template
        definition = self._generate_definition_template(
            parent_lemma, collocate, relation, relation_name
        )

        return SubentryDraft(
            suggested_headword=collocate,
            parent_lemma=parent_lemma,
            relation_type=relation,
            relation_name=relation_name,
            definition_template=definition,
            examples=examples[:5] if examples else [],
            translations=[],  # Would come from parallel corpus
            confidence=confidence,
            metadata={
                'generated_at': datetime.now().isoformat(),
                'source': 'word_sketch'
            }
        )

    def get_suggested_subentries(
        self,
        lemma: str,
        pos: str = None,
        min_logdice: float = 7.0,
        max: int = 10
    ) -> List[SubentryDraft]:
        """
        Get suggested subentries for a lemma.

        Identifies high-value collocates that could become subentries.

        Args:
            lemma: Headword lemma
            pos: Optional part of speech
            min_logdice: Minimum logDice threshold
            max: Maximum subentries to suggest

        Returns:
            List of SubentryDraft objects
        """
        drafts = []

        sketch = self.ws_client.word_sketch(lemma, pos, min_logdice)

        if sketch:
            for coll in sketch.collocations:
                if coll.frequency < self.MIN_FREQUENCY_FOR_PROPOSAL:
                    continue

                # Only draft for certain relation types that indicate subentries
                if self._is_subentry_relation(coll.relation):
                    draft = self.draft_subentry(
                        parent_lemma=lemma,
                        collocate=coll.collocate,
                        relation=coll.relation,
                        relation_name=coll.relation_name,
                        examples=coll.examples
                    )
                    drafts.append(draft)

        return drafts[:max]

    def _get_example_proposals(self, lemma: str) -> List[EnrichmentProposal]:
        """Get example sentence proposals from corpus."""
        proposals = []

        try:
            count, hits = self.corpus_client.concordance(lemma, limit=20)

            for hit in hits:
                example = f"{hit.left} {hit.match} {hit.right}"
                proposal = EnrichmentProposal(
                    proposal_type='example',
                    value=example,
                    confidence=0.7,  # Good confidence for corpus examples
                    examples=[example],
                    metadata={
                        'source': 'parallel_corpus',
                        'match': hit.match
                    }
                )
                proposals.append(proposal)

        except Exception as e:
            self.logger.warning(f"Failed to fetch examples for {lemma}: {e}")

        return proposals

    def _calculate_confidence(self, coll) -> float:
        """Calculate confidence score for a collocation proposal."""
        # logDice is on 0-14 scale, normalize to 0-1
        logdice_score = min(coll.logdice / 14.0, 1.0)

        # Frequency factor (logarithmic scaling)
        import math
        freq_score = min(math.log10(coll.frequency + 1) / 4.0, 1.0)

        # Combined score (weighted average)
        confidence = (logdice_score * 0.7) + (freq_score * 0.3)

        return round(confidence, 2)

    def _is_subentry_relation(self, relation: str) -> bool:
        """
        Determine if a relation type indicates a subentry.

        Relations that typically become subentries:
        - Compound relations (noun_compound)
        - Phrase relations
        - Strong collocations that form idiomatic expressions
        """
        subentry_relations = {
            'noun_compound',
            'adj_nouns',  # Nouns modified by adjective (e.g., "red house")
            'verb_objects',  # Verb + object compounds
        }

        # Check for compound patterns
        if 'compound' in relation.lower():
            return True
        if relation in subentry_relations:
            return True

        return False

    def _generate_definition_template(
        self,
        parent: str,
        collocate: str,
        relation: str,
        relation_name: str
    ) -> str:
        """Generate a definition template for a subentry."""
        # Map relation to template
        templates = {
            'noun_compound': f"A {collocate} that is associated with or forms a compound with {parent}",
            'adj_nouns': f"A {collocate} {parent} or a {parent} that is {collocate}",
            'verb_objects': f"To use {parent} with or for {collocate}",
            'mod_by': f"Something that {collocate}s {parent}",
            'modifies': f"{collocate} that modifies {parent}",
        }

        # Use specific template or generate generic one
        if relation in templates:
            return templates[relation]

        # Generic template
        return f"[Auto-generated from corpus: {collocate} (relation: {relation_name or relation})]"

    def proposals_to_dict(self, proposals: List[EnrichmentProposal]) -> List[Dict]:
        """Convert proposals to dictionary format for JSON response."""
        return [p.to_dict() for p in proposals]

    def drafts_to_dict(self, drafts: List[SubentryDraft]) -> List[Dict]:
        """Convert subentry drafts to dictionary format for JSON response."""
        return [d.to_dict() for d in drafts]
