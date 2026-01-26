"""
Word Sketch Service Client for external word sketch service (port 8080).

This client provides access to the word sketch Lucene service which provides
corpus-based collocation analysis. It supports caching and graceful degradation
when the service is unavailable.
"""
from __future__ import annotations

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
import requests
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)


@dataclass
class CollocationResult:
    """Single collocation from word sketch."""
    collocate: str
    lemma: str
    relation: str
    relation_name: str = ""
    logdice: float = 0.0
    frequency: int = 0
    examples: List[str] = field(default_factory=list)


@dataclass
class WordSketchResult:
    """Complete word sketch for a lemma."""
    lemma: str
    pos: str = ""
    collocations: List[CollocationResult] = field(default_factory=list)
    translations: List[str] = field(default_factory=list)
    total_examples: int = 0


class WordSketchClient:
    """Client for word sketch service with caching and graceful degradation.

    The word sketch service runs on port 8080 and provides:
    - GET /health - Health check
    - GET /api/relations - List grammatical relations
    - GET /api/sketch/{lemma} - Get word sketch
    - POST /api/sketch/query - Custom CQL pattern query
    """

    DEFAULT_BASE_URL = "http://localhost:8080"
    CACHE_TTL = 3600  # 1 hour

    def __init__(
        self,
        base_url: str = None,
        cache: Any = None,
        session: requests.Session = None
    ):
        """
        Initialize the word sketch client.

        Args:
            base_url: Base URL of the word sketch service (default: localhost:8080)
            cache: Cache service instance (must have get/set/clear_pattern methods)
            session: Requests session for HTTP calls
        """
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip('/')
        self._session = session or requests.Session()
        self._session.timeout = 30
        self._cache = cache
        self._available: Optional[bool] = None  # Lazy health check

    def is_available(self) -> bool:
        """Check if service is available with lazy initialization."""
        if self._available is None:
            try:
                health = self.health()
                self._available = health.get("status") == "ok"
            except Exception as e:
                logger.warning(f"Word sketch service health check failed: {e}")
                self._available = False
        return self._available

    def health(self) -> Dict[str, Any]:
        """Get service health status.

        Returns:
            Health status dictionary with 'status' key ('ok' or 'unhealthy')
        """
        try:
            response = self._session.get(
                f"{self.base_url}/health",
                timeout=5
            )
            response.raise_for_status()
            return response.json()
        except RequestException as e:
            logger.warning(f"Word sketch service health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

    def _get_cache_key(self, lemma: str, pos: str = None, min_logdice: float = 0) -> str:
        """Generate cache key for word sketch request."""
        parts = ["ws", lemma.lower()]
        if pos:
            parts.append(pos)
        if min_logdice > 0:
            parts.append(str(min_logdice))
        return ":".join(parts)

    def _get_from_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """Get data from cache if available."""
        if self._cache:
            try:
                return self._cache.get(key)
            except Exception as e:
                logger.warning(f"Cache get failed: {e}")
        return None

    def _set_cache(self, key: str, data: Dict[str, Any], ttl: int = None) -> None:
        """Store data in cache if available."""
        if self._cache:
            try:
                self._cache.set(key, data, ttl or self.CACHE_TTL)
            except Exception as e:
                logger.warning(f"Cache set failed: {e}")

    def _clear_cache_pattern(self, pattern: str) -> int:
        """Clear cache entries matching pattern."""
        if self._cache:
            try:
                return self._cache.clear_pattern(pattern)
            except Exception as e:
                logger.warning(f"Cache clear failed: {e}")
        return 0

    def _transform_response(self, data: Dict[str, Any]) -> WordSketchResult:
        """Transform API response to WordSketchResult."""
        collocations = []
        pos_group = ""  # Default value

        # Try to get pos_group from patterns or top-level
        if "patterns" in data:
            for relation_id, pattern_data in data.get("patterns", {}).items():
                pattern_name = pattern_data.get("name", relation_id)
                pos_group = pattern_data.get("pos_group", "")

                for coll in pattern_data.get("collocations", []):
                    collocations.append(CollocationResult(
                        collocate=coll.get("lemma", ""),
                        lemma=coll.get("lemma", ""),
                        relation=relation_id,
                        relation_name=pattern_name,
                        logdice=coll.get("logDice", 0.0),
                        frequency=coll.get("frequency", 0),
                        examples=coll.get("examples", [])
                    ))

        # Handle custom query response (flat collocations array)
        elif "collocations" in data:
            pos_group = data.get("pos", "")
            for coll in data.get("collocations", []):
                collocations.append(CollocationResult(
                    collocate=coll.get("lemma", ""),
                    lemma=coll.get("lemma", ""),
                    relation="custom",
                    relation_name="",
                    logdice=coll.get("logDice", 0.0),
                    frequency=coll.get("frequency", 0),
                    examples=coll.get("examples", [])
                ))

        return WordSketchResult(
            lemma=data.get("lemma", ""),
            pos=pos_group,
            collocations=collocations,
            translations=[],  # Translations come from parallel corpus
            total_examples=sum(c.frequency for c in collocations)
        )

    def word_sketch(
        self,
        lemma: str,
        pos: str = None,
        min_logdice: float = 0,
        limit: int = 10
    ) -> Optional[WordSketchResult]:
        """
        Get complete word sketch for a lemma.

        Args:
            lemma: Word lemma to search
            pos: Optional part of speech filter (noun, verb, adj, adv)
            min_logdice: Minimum logDice score threshold (0-14 scale)
            limit: Maximum collocates per relation (default: 10)

        Returns:
            WordSketchResult or None if unavailable
        """
        # Check cache first
        cache_key = self._get_cache_key(lemma, pos, min_logdice)
        cached = self._get_from_cache(cache_key)
        if cached:
            logger.debug(f"Word sketch cache hit for {lemma}")
            return WordSketchResult(**cached)

        # Graceful degradation - return None if unavailable
        if not self.is_available():
            logger.warning(f"Word sketch service unavailable for lemma: {lemma}")
            return None

        try:
            params = {"lemma": lemma, "limit": limit}
            if pos:
                params["pos"] = pos
            if min_logdice > 0:
                params["min_logdice"] = min_logdice

            response = self._session.get(
                f"{self.base_url}/api/sketch/{lemma}",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            # Transform to our model
            result = self._transform_response(data)

            # Cache the result
            self._set_cache(cache_key, {
                "lemma": result.lemma,
                "pos": result.pos,
                "collocations": [
                    {
                        "collocate": c.collocate,
                        "lemma": c.lemma,
                        "relation": c.relation,
                        "relation_name": c.relation_name,
                        "logdice": c.logdice,
                        "frequency": c.frequency,
                        "examples": c.examples
                    }
                    for c in result.collocations
                ],
                "translations": result.translations,
                "total_examples": result.total_examples
            })

            logger.debug(f"Word sketch fetched for {lemma}: {len(result.collocations)} collocations")
            return result

        except RequestException as e:
            logger.error(f"Word sketch request failed for {lemma}: {e}")
            self._available = False
            return None
        except (KeyError, ValueError) as e:
            logger.error(f"Word sketch response parsing failed for {lemma}: {e}")
            return None

    def relations(self) -> Dict[str, List[Dict[str, str]]]:
        """
        Get available grammatical relations from the service.

        Returns:
            Dictionary mapping POS groups to lists of relation definitions.
            Each relation has: id, name, pattern, pos_group
        """
        if not self.is_available():
            logger.warning("Word sketch service unavailable for relations query")
            return {}

        try:
            response = self._session.get(
                f"{self.base_url}/api/relations",
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            return data.get("relations", {})
        except RequestException as e:
            logger.error(f"Relations query failed: {e}")
            self._available = False
            return {}

    def custom_query(
        self,
        lemma: str,
        pattern: str,
        min_logdice: float = 0,
        limit: int = 50
    ) -> Optional[WordSketchResult]:
        """
        Execute custom CQL pattern query.

        Args:
            lemma: Headword lemma
            pattern: CQL pattern (e.g., "[tag=jj.*]~{0,3}")
            min_logdice: Minimum logDice score
            limit: Maximum results

        Returns:
            WordSketchResult with collocations matching the pattern
        """
        # This endpoint returns a flat list of collocations
        cache_key = f"ws:query:{lemma}:{pattern}:{min_logdice}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return WordSketchResult(**cached)

        if not self.is_available():
            return None

        try:
            response = self._session.post(
                f"{self.base_url}/api/sketch/query",
                json={
                    "lemma": lemma,
                    "pattern": pattern,
                    "min_logdice": min_logdice,
                    "limit": limit
                },
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            # Transform flat collocations to WordSketchResult
            collocations = []
            for coll in data.get("collocations", []):
                collocations.append(CollocationResult(
                    collocate=coll.get("lemma", ""),
                    lemma=coll.get("lemma", ""),
                    relation="custom",
                    relation_name=pattern,
                    logdice=coll.get("logDice", 0.0),
                    frequency=coll.get("frequency", 0),
                    examples=coll.get("examples", [])
                ))

            result = WordSketchResult(
                lemma=data.get("lemma", lemma),
                collocations=collocations,
                total_examples=sum(c.frequency for c in collocations)
            )

            self._set_cache(cache_key, {
                "lemma": result.lemma,
                "pos": result.pos,
                "collocations": [
                    {
                        "collocate": c.collocate,
                        "lemma": c.lemma,
                        "relation": c.relation,
                        "relation_name": c.relation_name,
                        "logdice": c.logdice,
                        "frequency": c.frequency,
                        "examples": c.examples
                    }
                    for c in result.collocations
                ],
                "translations": result.translations,
                "total_examples": result.total_examples
            })

            return result

        except RequestException as e:
            logger.error(f"Custom query failed for {lemma}: {e}")
            return None

    def clear_cache(self, lemma: str = None) -> int:
        """
        Clear cached word sketches.

        Args:
            lemma: Optional specific lemma to clear (clears all if None)

        Returns:
            Number of cache entries cleared
        """
        if lemma:
            pattern = f"ws:{lemma.lower()}:*"
        else:
            pattern = "ws:*"
        return self._clear_cache_pattern(pattern)
