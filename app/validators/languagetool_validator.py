"""
LanguageTool Validator with Grammar and Bitext Support.

Validates text using LanguageTool server API.
Supports:
- Single-language grammar/spell checking
- Bitext (translation) quality checking
- Caching of results for repeated validation
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

from app.validators.base import (
    Validator,
    ValidationResult,
    CacheableValidator,
    BatchValidator
)


class LanguageToolValidator(CacheableValidator, BatchValidator):
    """
    LanguageTool grammar and bitext validator.

    Connects to a LanguageTool server for:
    - Grammar rule checking
    - Spelling verification
    - Style suggestions
    - Bitext (translation) quality assessment

    Results are cached to avoid repeated API calls for unchanged content.
    """

    def __init__(
        self,
        cache_service: Optional[Any] = None,
        db_session: Optional[Any] = None,
        server_url: Optional[str] = None,
        timeout: int = 30,
        ttl: int = 86400
    ):
        """
        Initialize LanguageTool validator.

        Args:
            cache_service: CacheService instance
            db_session: Database session for persistent cache
            server_url: LanguageTool server URL
            timeout: Request timeout in seconds
            ttl: Cache TTL in seconds
        """
        super().__init__(cache_service, db_session, ttl)
        self.logger = logging.getLogger(__name__)

        # Server configuration
        self.server_url = server_url or self._get_server_url()
        self.timeout = timeout

        # Lazy initialization of HTTP session
        self._session = None

    def _get_server_url(self) -> str:
        """Get LanguageTool server URL from environment or defaults."""
        import os
        host = os.getenv('LANGUAGETOOL_HOST', 'localhost')
        port = os.getenv('LANGUAGETOOL_PORT', '8081')
        return f"http://{host}:{port}"

    @property
    def validator_type(self) -> str:
        return 'languagetool'

    @property
    def display_name(self) -> str:
        return 'LanguageTool'

    @property
    def session(self):
        """Lazy-load HTTP session."""
        if self._session is None:
            import requests
            self._session = requests.Session()
        return self._session

    def validate(
        self,
        text: str,
        lang: str = 'en',
        target_lang: Optional[str] = None,
        mother_tongue: Optional[str] = None,
        enabled_rules: Optional[List[str]] = None,
        disabled_rules: Optional[List[str]] = None,
        entry_id: Optional[str] = None,
        date_modified: Optional[str] = None,
        **kwargs
    ) -> ValidationResult:
        """
        Validate text using LanguageTool.

        Args:
            text: Text to validate
            lang: Source language code (e.g., 'en', 'pl')
            target_lang: Target language for bitext checking
            mother_tongue: User's mother tongue for better suggestions
            enabled_rules: List of rule IDs to enable
            disabled_rules: List of rule IDs to disable
            entry_id: Entry ID for caching
            date_modified: Entry's date_modified for cache invalidation
            **kwargs: Additional options

        Returns:
            ValidationResult with matches and suggestions
        """
        if not text or not text.strip():
            return ValidationResult(
                is_valid=True,
                validator_type=self.validator_type,
                cached=False,
                metadata={'empty': True}
            )

        # Build cache key
        cache_key = self.get_cache_key(
            entry_id or 'unknown',
            text,
            lang=lang,
            target_lang=target_lang,
            mother_tongue=mother_tongue
        )

        # Try cache first
        cached = self._get_from_cache(cache_key)
        if cached:
            cached.metadata['cache_key'] = cache_key
            return cached

        # Check DB cache if we have entry info
        if entry_id and date_modified:
            content_hash = self._get_content_hash(text)
            db_cached = self._check_db_cache(entry_id, date_modified, content_hash)
            if db_cached:
                db_cached.metadata['cache_key'] = cache_key
                return db_cached

        # Perform validation
        result = self._call_languagetool(
            text=text,
            lang=lang,
            target_lang=target_lang,
            mother_tongue=mother_tongue,
            enabled_rules=enabled_rules,
            disabled_rules=disabled_rules
        )

        # Cache the result
        self._save_to_cache(cache_key, result)
        if entry_id and date_modified:
            self._save_to_db(entry_id, date_modified, content_hash, result)

        result.metadata['cache_key'] = cache_key
        return result

    def _call_languagetool(
        self,
        text: str,
        lang: str,
        target_lang: Optional[str] = None,
        mother_tongue: Optional[str] = None,
        enabled_rules: Optional[List[str]] = None,
        disabled_rules: Optional[List[str]] = None
    ) -> ValidationResult:
        """
        Call LanguageTool API.

        Args:
            text: Text to validate
            lang: Language code
            target_lang: Target language for bitext
            mother_tongue: User's mother tongue
            enabled_rules: Rules to enable
            disabled_rules: Rules to disable

        Returns:
            ValidationResult
        """
        import requests

        endpoint = f"{self.server_url}/v2/check"

        payload = {
            'text': text,
            'language': lang,
        }

        # Add bitext parameters if target language specified
        if target_lang:
            payload['motherTongue'] = target_lang

        # Rule filtering
        if enabled_rules:
            payload['enabledRules'] = ','.join(enabled_rules)
        if disabled_rules:
            payload['disabledRules'] = ','.join(disabled_rules)

        try:
            response = self.session.post(
                endpoint,
                data=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()

            # Parse matches
            matches = self._parse_matches(data.get('matches', []))

            # Assess bitext quality if target_lang specified
            bitext_quality = None
            if target_lang:
                bitext_quality = self._assess_bitext_quality(
                    text, target_lang, matches
                )

            return ValidationResult(
                is_valid=len(matches) == 0,
                validator_type=self.validator_type,
                cached=False,
                suggestions=self._extract_suggestions(matches),
                matches=matches,
                bitext_quality=bitext_quality,
                metadata={
                    'language': lang,
                    'target_lang': target_lang,
                    'api_success': True
                }
            )

        except requests.RequestException as e:
            self.logger.warning(f"LanguageTool API error: {e}")
            return ValidationResult(
                is_valid=True,  # Don't fail on API error
                validator_type=self.validator_type,
                cached=False,
                metadata={
                    'error': str(e),
                    'api_error': True
                }
            )

    def _parse_matches(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parse LanguageTool matches into standardized format.

        Args:
            matches: Raw matches from API

        Returns:
            Standardized match dicts
        """
        parsed = []

        for match in matches:
            rule = match.get('rule', {})
            category = rule.get('category', {})

            parsed_match = {
                'message': match.get('message'),
                'short_message': match.get('shortMessage'),
                'rule_id': rule.get('id'),
                'rule_subid': rule.get('subId'),
                'rule_category': category.get('name'),
                'category_id': category.get('id'),
                'offset': match.get('offset'),
                'length': match.get('length'),
                'replacements': [
                    r.get('value') for r in match.get('replacements', [])
                ],
                'context': {
                    'text': match.get('context', {}).get('text'),
                    'offset': match.get('context', {}).get('offset'),
                    'length': match.get('context', {}).get('length')
                },
                'sentence': match.get('sentence')
            }
            parsed.append(parsed_match)

        return parsed

    def _extract_suggestions(self, matches: List[Dict[str, Any]]) -> List[str]:
        """
        Extract all suggestions from matches.

        Args:
            matches: List of match dicts

        Returns:
            Flattened list of all suggested replacements
        """
        suggestions = []
        for match in matches:
            for replacement in match.get('replacements', []):
                if replacement not in suggestions:
                    suggestions.append(replacement)
        return suggestions

    def _assess_bitext_quality(
        self,
        text: str,
        target_lang: str,
        matches: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Assess translation quality based on LanguageTool feedback.

        Args:
            text: Source text
            target_lang: Target language
            matches: Rule matches

        Returns:
            Quality assessment dict
        """
        issues = []

        for match in matches:
            category = match.get('rule_category', '').lower()

            # Categorize issues by type
            if 'grammar' in category:
                issues.append({
                    'type': 'grammar',
                    'message': match.get('message'),
                    'rule_id': match.get('rule_id')
                })
            elif 'spelling' in category:
                issues.append({
                    'type': 'spelling',
                    'message': match.get('message'),
                    'rule_id': match.get('rule_id')
                })
            elif 'style' in category:
                issues.append({
                    'type': 'style',
                    'message': match.get('message'),
                    'rule_id': match.get('rule_id')
                })
            else:
                issues.append({
                    'type': 'general',
                    'message': match.get('message'),
                    'rule_id': match.get('rule_id')
                })

        # Calculate quality score (simple heuristic)
        word_count = len(text.split())
        issue_count = len(issues)
        score = max(0, 100 - (issue_count * 10)) if word_count > 0 else 100

        return {
            'score': score,
            'issue_count': issue_count,
            'issues': issues,
            'target_lang': target_lang
        }

    def get_cache_key(
        self,
        entry_id: str,
        text: str,
        **kwargs
    ) -> str:
        """
        Generate cache key for LanguageTool validation.

        Args:
            entry_id: Entry identifier
            text: Text being validated
            **kwargs: Parameters that affect validation

        Returns:
            Cache key string
        """
        # Include relevant parameters in key
        key_parts = [
            'lt',
            entry_id,
            self._get_content_hash(text),
            kwargs.get('lang', 'unknown'),
            kwargs.get('target_lang', '')
        ]
        return ':'.join(str(p) for p in key_parts)

    def _get_content_hash(self, text: str) -> str:
        """Get truncated SHA256 hash of text."""
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    def invalidate_for_entry(self, entry_id: str) -> int:
        """
        Invalidate all cached results for an entry.

        Args:
            entry_id: Entry identifier

        Returns:
            Number of cache entries invalidated
        """
        count = 0

        # Clear Redis cache
        if self.cache_service:
            count += self.cache_service.clear_pattern(f"lt:{entry_id}:*")

        # Clear DB cache
        try:
            from app.models.validation_cache_models import ValidationResultCache
            count += ValidationResultCache.query.filter(
                ValidationResultCache.entry_id == entry_id,
                ValidationResultCache.validator_type == 'languagetool'
            ).delete()
            if self.db_session:
                self.db_session.commit()
        except Exception as e:
            self.logger.warning(f"DB invalidation error: {e}")

        return count

    def validate_batch(
        self,
        entries: List[Dict[str, Any]],
        lang: str = 'en',
        target_lang: Optional[str] = None,
        **kwargs
    ) -> Dict[str, ValidationResult]:
        """
        Validate multiple entries.

        Note: LanguageTool doesn't have a true batch API, so we
        make individual requests. Override in subclass if your
        LT server supports batch endpoints.

        Args:
            entries: List of {'id': str, 'text': str}
            lang: Language code
            target_lang: Target language for bitext
            **kwargs: Additional options

        Returns:
            Dict mapping entry_id -> ValidationResult
        """
        results = {}

        for entry in entries:
            entry_id = entry['id']
            text = entry.get('text', '')

            result = self.validate(
                text=text,
                lang=lang,
                target_lang=target_lang,
                entry_id=entry_id,
                **kwargs
            )
            results[entry_id] = result

        return results

    def check_grammar_only(
        self,
        text: str,
        lang: str = 'en',
        **kwargs
    ) -> ValidationResult:
        """
        Check grammar only (no spelling).

        Args:
            text: Text to validate
            lang: Language code
            **kwargs: Additional options

        Returns:
            ValidationResult with grammar-only matches
        """
        return self.validate(
            text=text,
            lang=lang,
            enabled_rules=[
                'GRAMMAR',
                'MISC',
                'PUNCTUATION'
            ],
            **kwargs
        )

    def check_spelling_only(
        self,
        text: str,
        lang: str = 'en',
        **kwargs
    ) -> ValidationResult:
        """
        Check spelling only (no grammar).

        Args:
            text: Text to validate
            lang: Language code
            **kwargs: Additional options

        Returns:
            ValidationResult with spelling-only matches
        """
        return self.validate(
            text=text,
            lang=lang,
            disabled_rules=['GRAMMAR'],
            **kwargs
        )
