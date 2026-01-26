"""
Workset coverage analysis for word sketch enrichment.

This service analyzes workset entries against word sketch data to:
1. Identify entries with good corpus coverage
2. Find entries missing coverage (priority for new entries)
3. Generate actionable items for workset curation
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class CoverageResult:
    """Coverage analysis result for a single entry."""
    entry_id: str
    lemma: str
    pos: str
    has_coverage: bool
    corpus_count: int
    coverage_score: float
    collocations_count: int
    needs_enrichment: bool
    is_estimated: bool = False


@dataclass
class CoverageReport:
    """Workset coverage analysis report."""
    workset_id: int
    workset_name: str
    total_entries: int
    covered_entries: int
    missing_entries: List[Dict[str, Any]]  # [{lemma, pos, suggestions}]
    coverage_percentage: float
    priority_items: List[Dict[str, Any]]  # High-value missing entries
    results: List[CoverageResult] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)


class CoverageService:
    """
    Analyzes workset entries against word sketch data.

    Priority workflow:
    1. Coverage checking - identify entries missing word sketch data
    2. Enrich existing entries - find collocations/examples to add
    3. Draft new subentries - identify gaps for new entries
    """

    # Thresholds for collocation significance
    #
    # MIN_COLLOCATION_LOGDICE = 6.0
    #   Standard cutoff used in corpus linguistics. LogDice scores range from 0-14,
    #   where higher values indicate stronger collocational association. Collocations
    #   above 6.0 show statistically significant co-occurrence patterns that are
    #   unlikely to be due to chance alone. This is the industry-standard threshold
    #   used in Sketch Engine and similar corpus tools.
    #
    # MIN_COLLOCATION_FREQUENCY = 3
    #   Minimum number of occurrences required to consider a collocation reliable.
    #   A collocation appearing only 1-2 times in a corpus is likely to be a random
    #   artifact rather than a genuine linguistic pattern. This threshold ensures
    #   we only surface collocations with reproducible evidence.
    #
    # COVERAGE_THRESHOLD = 0.7
    #   Coverage score is calculated as (collocation_count/10 * 0.4) + (avg_logdice/14 * 0.6).
    #   A score of 0.7 represents good coverage, roughly equivalent to having at least
    #   7+ collocations with an average logDice of 8+. Below this threshold, an entry
    #   should be prioritized for enrichment with additional collocational data.
    MIN_COLLOCATION_LOGDICE = 6.0
    MIN_COLLOCATION_FREQUENCY = 3
    COVERAGE_THRESHOLD = 0.7

    def __init__(
        self,
        word_sketch_client=None,
        workset_service=None
    ):
        """
        Initialize the coverage service.

        Args:
            word_sketch_client: WordSketchClient instance (optional, created if None)
            workset_service: WorksetService instance (optional, created if None)
        """
        # Import here to avoid circular imports
        from app.services.word_sketch import WordSketchClient

        self.ws_client = word_sketch_client or WordSketchClient()
        self.workset_service = workset_service
        self.logger = logging.getLogger(__name__)

    def _get_cache_key(self, lemma: str, pos: str = None, min_logdice: float = 0) -> str:
        """
        Generate cache key for coverage analysis requests.

        Format matches WordSketchClient in __init__.py for consistency:
        ws:lemma:pos:min_logdice (optional parts are omitted if empty/zero)

        Args:
            lemma: Word lemma
            pos: Optional part of speech
            min_logdice: Optional minimum logDice threshold

        Returns:
            Cache key string in format "ws:lemma:pos:min_logdice"
        """
        parts = ["ws", lemma.lower()]
        if pos:
            parts.append(pos)
        if min_logdice > 0:
            parts.append(str(min_logdice))
        return ":".join(parts)

    def analyze_workset(
        self,
        workset_id: int,
        min_logdice: float = None
    ) -> CoverageReport:
        """
        Analyze workset for word sketch coverage.

        Args:
            workset_id: ID of the workset to analyze
            min_logdice: Minimum logDice threshold (default: MIN_COLLOCATION_LOGDICE)

        Returns:
            CoverageReport with analysis results
        """
        min_logdice = min_logdice or self.MIN_COLLOCATION_LOGDICE

        # Get workset entries
        workset = self._get_workset(workset_id)
        if not workset:
            raise ValueError(f"Workset {workset_id} not found")

        total_entries = workset.get('total_entries', len(workset.get('entries', [])))
        entries = workset.get('entries', [])

        covered_entries = 0
        missing_entries = []
        priority_items = []
        results = []

        for entry_data in entries:
            entry_id = entry_data.get('id')
            lemma, pos = self._extract_lemma_pos(entry_data)

            if not lemma:
                continue

            # Check word sketch coverage
            sketch = self.ws_client.word_sketch(lemma, pos, min_logdice)

            if sketch and sketch.collocations:
                covered_entries += 1

                # Check if entry needs enrichment
                collocations_count = len(sketch.collocations)
                coverage_score = self._calculate_coverage_score(sketch)
                needs_enrichment = coverage_score < self.COVERAGE_THRESHOLD

                result = CoverageResult(
                    entry_id=entry_id,
                    lemma=lemma,
                    pos=pos,
                    has_coverage=True,
                    corpus_count=sketch.total_examples,
                    coverage_score=coverage_score,
                    collocations_count=collocations_count,
                    needs_enrichment=needs_enrichment
                )
                results.append(result)

                if needs_enrichment:
                    missing_entries.append({
                        'entry_id': entry_id,
                        'lemma': lemma,
                        'pos': pos,
                        'collocations_found': collocations_count,
                        'coverage_score': coverage_score,
                        'suggestions': self._generate_enrichment_suggestions(sketch)
                    })
            else:
                # Missing coverage - high priority for curation
                result = CoverageResult(
                    entry_id=entry_id,
                    lemma=lemma,
                    pos=pos,
                    has_coverage=False,
                    corpus_count=0,
                    coverage_score=0.0,
                    collocations_count=0,
                    needs_enrichment=True
                )
                results.append(result)

                priority_items.append({
                    'entry_id': entry_id,
                    'lemma': lemma,
                    'pos': pos,
                    'priority_score': self._calculate_priority(entry_data),
                    'reason': 'No corpus coverage found'
                })

        coverage_pct = (covered_entries / total_entries * 100) if total_entries > 0 else 0

        # Sort priority items by score (highest first)
        priority_items.sort(key=lambda x: x['priority_score'], reverse=True)

        return CoverageReport(
            workset_id=workset_id,
            workset_name=workset.get('name', 'Unknown'),
            total_entries=total_entries,
            covered_entries=covered_entries,
            missing_entries=missing_entries,
            coverage_percentage=round(coverage_pct, 2),
            priority_items=priority_items[:50],  # Top 50 priorities
            results=results
        )

    def check_entry_coverage(
        self,
        lemma: str,
        pos: str = None,
        min_logdice: float = None
    ) -> CoverageResult:
        """
        Check coverage for a single lemma.

        Args:
            lemma: Word lemma to check
            pos: Optional part of speech
            min_logdice: Minimum logDice threshold

        Returns:
            CoverageResult for the lemma
        """
        min_logdice = min_logdice or self.MIN_COLLOCATION_LOGDICE

        sketch = self.ws_client.word_sketch(lemma, pos, min_logdice)

        if sketch and sketch.collocations:
            coverage_score = self._calculate_coverage_score(sketch)
            return CoverageResult(
                entry_id="",
                lemma=lemma,
                pos=pos or sketch.pos,
                has_coverage=True,
                corpus_count=sketch.total_examples,
                coverage_score=coverage_score,
                collocations_count=len(sketch.collocations),
                needs_enrichment=coverage_score < self.COVERAGE_THRESHOLD
            )
        else:
            return CoverageResult(
                entry_id="",
                lemma=lemma,
                pos=pos or "",
                has_coverage=False,
                corpus_count=0,
                coverage_score=0.0,
                collocations_count=0,
                needs_enrichment=True
            )

    def _get_workset(self, workset_id: int) -> Optional[Dict[str, Any]]:
        """Get workset data from workset service."""
        if self.workset_service is None:
            # Import here to avoid circular import
            try:
                from app.services.workset_service import WorksetService
                self.workset_service = WorksetService()
            except ImportError:
                self.logger.warning("WorksetService not available")
                return None

        try:
            return self.workset_service.get_workset(workset_id)
        except Exception as e:
            self.logger.warning(f"Could not fetch workset {workset_id}: {e}")
            return None

    def _extract_lemma_pos(self, entry_data: Dict) -> tuple:
        """Extract lemma and POS from entry data."""
        lemma = ""

        # Try lexical_unit (dict format)
        lexical_unit = entry_data.get('lexical_unit', {})
        if isinstance(lexical_unit, dict):
            lemma = lexical_unit.get('en') or lexical_unit.get('en_US') or next(iter(lexical_unit.values()), "")
        elif isinstance(lexical_unit, str):
            lemma = lexical_unit

        # Fallback to headword field
        if not lemma:
            lemma = entry_data.get('headword', '')

        # Extract POS
        pos = ""
        grammatical_info = entry_data.get('grammatical_info', {})
        if isinstance(grammatical_info, dict):
            pos = grammatical_info.get('part_of_speech', '')
        elif isinstance(grammatical_info, str):
            pos = grammatical_info

        return lemma.strip() if lemma else "", pos.strip() if pos else ""

    def _calculate_coverage_score(self, sketch) -> float:
        """
        Calculate coverage score based on word sketch data.

        Score considers:
        - Number of collocations
        - Average logDice of collocations
        - Total corpus frequency
        """
        if not sketch or not sketch.collocations:
            return 0.0

        # Factor 1: Number of collocation types (normalized to 10)
        collocation_score = min(len(sketch.collocations) / 10, 1.0)

        # Factor 2: Average logDice (normalized to 14)
        if sketch.collocations:
            avg_logdice = sum(c.logdice for c in sketch.collocations) / len(sketch.collocations)
            logdice_score = avg_logdice / 14.0
        else:
            logdice_score = 0.0

        # Combined score (weighted)
        score = (collocation_score * 0.4) + (logdice_score * 0.6)

        return min(score, 1.0)

    def _calculate_priority(self, entry_data: Dict) -> float:
        """
        Calculate priority score for an entry needing coverage.

        Higher score = should be addressed first.
        """
        score = 0.5  # Base score

        # Recently created entries might need more attention
        created_at = entry_data.get('date_created')
        if created_at:
            try:
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                days_old = (datetime.now() - created_at).days
                score += min(days_old / 30, 0.3)  # Max 0.3 bonus
            except Exception:
                pass

        # Entries with citations might be more important
        if entry_data.get('citations'):
            score += 0.1

        return min(score, 1.0)

    def _generate_enrichment_suggestions(self, sketch) -> Dict[str, Any]:
        """Generate suggestions for enriching an entry."""
        if not sketch or not sketch.collocations:
            return {}

        suggestions = {
            'collocations': [],
            'high_value_collocations': []
        }

        for coll in sketch.collocations:
            coll_info = {
                'lemma': coll.collocate,
                'relation': coll.relation_name or coll.relation,
                'logdice': round(coll.logdice, 2),
                'frequency': coll.frequency,
                'examples': coll.examples[:2]
            }

            # High-value = strong association
            if coll.logdice >= 8.0 and coll.frequency >= self.MIN_COLLOCATION_FREQUENCY:
                suggestions['high_value_collocations'].append(coll_info)

            suggestions['collocations'].append(coll_info)

        return suggestions

    def get_missing_lemmas(self, workset_id: int) -> List[str]:
        """
        Get list of lemmas missing word sketch coverage.

        Useful for batch operations or reports.
        """
        report = self.analyze_workset(workset_id)
        return [
            item['lemma']
            for item in report.priority_items
            if item.get('reason') == 'No corpus coverage found'
        ]
