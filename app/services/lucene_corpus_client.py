"""
Lucene Corpus Client for communicating with the corpus search service.

This client provides a clean interface to the Lucene corpus service
running at port 8082, replacing PostgreSQL-based corpus queries.
"""
from __future__ import annotations

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import requests
from requests.exceptions import RequestException


logger = logging.getLogger(__name__)


@dataclass
class ConcordanceHit:
    """Represents a single corpus search result from parallel corpus (TMX format)."""
    source: str  # Source language text
    target: str  # Target language translation
    sentence_id: Optional[str] = None


class LuceneCorpusClient:
    """Client for the Lucene corpus search service."""

    def __init__(self, base_url: str = "http://localhost:8082"):
        """
        Initialize the Lucene corpus client.

        Args:
            base_url: Base URL of the Lucene corpus service
        """
        self.base_url = base_url.rstrip('/')
        self._session = requests.Session()
        self._session.timeout = 30

    def health(self) -> Dict[str, Any]:
        """
        Get service health status.

        Returns:
            Health status dictionary from /health endpoint
        """
        try:
            response = self._session.get(f"{self.base_url}/health", timeout=5)
            response.raise_for_status()
            return response.json()
        except RequestException as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

    def is_available(self) -> bool:
        """Check if the corpus service is available."""
        try:
            return self.health().get("status") == "ok"
        except Exception:
            return False

    def concordance(
        self,
        query: str,
        limit: int = 50,
        context_size: int = 5
    ) -> tuple[int, List[ConcordanceHit]]:
        """
        Search for parallel corpus matches (source/target format).

        Args:
            query: Search query
            limit: Maximum number of results
            context_size: Reserved for KWIC context (not used in parallel format)

        Returns:
            Tuple of (total_count, list of ConcordanceHit)
        """
        try:
            response = self._session.get(
                f"{self.base_url}/concordance",
                params={"q": query, "limit": limit},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            hits = [
                ConcordanceHit(
                    source=h.get("source", ""),
                    target=h.get("target", ""),
                    sentence_id=h.get("sentence_id")
                )
                for h in data.get("hits", [])
            ]
            return data.get("total", len(hits)), hits

        except RequestException as e:
            logger.error(f"Concordance search failed for query '{query}': {e}")
            return 0, []

    def count(self, query: str) -> int:
        """
        Get the count of matching documents.

        Args:
            query: Search query

        Returns:
            Number of matching documents
        """
        try:
            response = self._session.get(
                f"{self.base_url}/count",
                params={"q": query},
                timeout=30
            )
            response.raise_for_status()
            return response.json().get("count", 0)

        except RequestException as e:
            logger.error(f"Count query failed for '{query}': {e}")
            return 0

    def stats(self) -> Dict[str, Any]:
        """
        Get corpus statistics from the Lucene index using /health endpoint.

        Returns:
            Dictionary with total_documents and health info

        Raises:
            RequestException: If the Lucene service is unavailable
        """
        response = self._session.get(f"{self.base_url}/health", timeout=30)
        response.raise_for_status()
        data = response.json()

        # Map health response to stats format
        return {
            "total_documents": data.get("docs", 0),
            "status": "ok",
            "heap_used_mb": data.get("heapUsedMb"),
            "heap_max_mb": data.get("heapMaxMb"),
            "uptime_seconds": data.get("uptimeSeconds")
        }

    def compare(
        self,
        query_a: str,
        query_b: str,
        metric: str = "frequency"
    ) -> Dict[str, Any]:
        """
        Compare two queries.

        Args:
            query_a: First query
            query_b: Second query
            metric: Comparison metric (frequency, logdice, etc.)

        Returns:
            Comparison results
        """
        try:
            response = self._session.post(
                f"{self.base_url}/compare",
                json={"a": query_a, "b": query_b, "metric": metric},
                timeout=30
            )
            response.raise_for_status()
            return response.json()

        except RequestException as e:
            logger.error(f"Compare query failed: {e}")
            return {"error": str(e)}

    def optimize(self) -> Dict[str, Any]:
        """
        Optimize the Lucene index by merging segments.

        Returns:
            Dictionary with optimization results

        Raises:
            RequestException: If the optimization fails
        """
        try:
            response = self._session.post(f"{self.base_url}/optimize", timeout=300)
            response.raise_for_status()
            return response.json()
        except RequestException as e:
            logger.error(f"Optimize failed: {e}")
            raise

    def clear(self) -> Dict[str, Any]:
        """
        Clear all documents from the Lucene index.

        WARNING: This permanently deletes all indexed data.

        Returns:
            Dictionary with deletion count

        Raises:
            RequestException: If the clear operation fails
        """
        try:
            response = self._session.post(f"{self.base_url}/clear", timeout=300)
            response.raise_for_status()
            return response.json()
        except RequestException as e:
            logger.error(f"Clear failed: {e}")
            raise
