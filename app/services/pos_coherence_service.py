"""
POS Coherence Service — ML-based anomaly detector for dictionary entries.

Uses TF-IDF + SGDClassifier (log_loss) trained on top-level POS taxonomy categories
(Noun, Verb, Adjective, Adverb, Pronoun, Preposition, etc.) to detect real
cross-category contradictions while respecting lexicographer tag enrichments
(e.g., 'Countable Noun' is a subtype of 'Noun', 'Phrasal Verb' is a subtype of 'Verb').
"""

from __future__ import annotations

import logging
import time
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.pipeline import Pipeline, make_pipeline

from app.services.import_converter import normalize_pos

logger = logging.getLogger(__name__)

# Module-level cache for model & cached anomalies (TTL 1 hour)
_CACHED_SERVICE_INSTANCE: Optional['POSCoherenceService'] = None

# Taxonomy mapping: maps fine-grained or variant POS labels to their top-level root POS category.
POS_ROOT_MAP: Dict[str, str] = {
    # Nouns
    "noun": "Noun",
    "countable noun": "Noun",
    "uncountable noun": "Noun",
    "countable or uncountable noun": "Noun",
    "countable": "Noun",
    "uncountable": "Noun",
    "common noun": "Noun",
    "proper noun": "Noun",
    "cn": "Noun",
    "pn": "Noun",
    "n": "Noun",
    # Verbs
    "verb": "Verb",
    "phrasal verb": "Verb",
    "transitive verb": "Verb",
    "intransitive verb": "Verb",
    "auxiliary verb": "Verb",
    "phrasal": "Verb",
    "v": "Verb",
    "vt": "Verb",
    "vi": "Verb",
    "vtr": "Verb",
    "vintr": "Verb",
    # Adjectives
    "adjective": "Adjective",
    "possessive adjective": "Adjective",
    "adj": "Adjective",
    "a": "Adjective",
    # Adverbs
    "adverb": "Adverb",
    "adv": "Adverb",
    # Pronouns
    "pronoun": "Pronoun",
    "personal pronoun": "Pronoun",
    "reflexive pronoun": "Pronoun",
    "possessive pronoun": "Pronoun",
    "relative pronoun": "Pronoun",
    "demonstrative pronoun": "Pronoun",
    "interrogative pronoun": "Pronoun",
    "pro-form": "Pronoun",
    "pro": "Pronoun",
    # Determiners / Articles
    "determiner": "Determiner",
    "possessive determiner": "Determiner",
    "article": "Article",
    "art": "Article",
    "det": "Determiner",
    # Numerals / Quantifiers
    "cardinal": "Cardinal",
    "ordinal": "Ordinal",
    "cardinal numeral": "Cardinal",
    "ordinal numeral": "Ordinal",
    "numeral": "Cardinal",
    "quantifier": "Quantifier",
    # Prepositions / Connectives
    "preposition": "Preposition",
    "prep": "Preposition",
    "connective": "Connective",
    "conjunction": "Connective",
    "conj": "Connective",
    # Interjections
    "interjection": "Interjection",
    "interj": "Interjection",
}


def get_root_pos(pos: str) -> str:
    """Return top-level root category for a POS string (e.g. 'Countable Noun' -> 'Noun')."""
    if not pos:
        return ""
    cleaned = pos.strip().lower()
    return POS_ROOT_MAP.get(cleaned, pos.strip())


class POSCoherenceService:
    """Taxonomy-aware statistical model service for POS-definition coherence detection."""

    def __init__(self) -> None:
        self.pipeline: Optional[Pipeline] = None
        self.classes: List[str] = []
        self.last_trained: float = 0.0
        self.cached_anomalies: List[Dict[str, Any]] = []

    def _fetch_dataset(self, dict_service: Any) -> List[Tuple[str, str, str, str]]:
        has_ns = dict_service._detect_namespace_usage()
        prologue = dict_service._query_builder.get_namespace_prologue(has_ns)
        entry_path = dict_service._query_builder.get_element_path('entry', has_ns)
        sense_path = dict_service._query_builder.get_element_path('sense', has_ns)
        gi_path = dict_service._query_builder.get_element_path('grammatical-info', has_ns)
        def_path = dict_service._query_builder.get_element_path('definition', has_ns)
        gloss_path = dict_service._query_builder.get_element_path('gloss', has_ns)
        text_path = dict_service._query_builder.get_element_path('text', has_ns)
        lu_path = dict_service._query_builder.get_element_path('lexical-unit', has_ns)
        form_path = dict_service._query_builder.get_element_path('form', has_ns)

        db_name = dict_service.db_connector.database
        C = f"collection('{db_name}')"

        query = (
            f"{prologue} "
            f"for $e in {C}//{entry_path} "
            f"let $hw := normalize-space(($e/{lu_path}/{form_path}/{text_path}/string(), '')[1]) "
            f"for $s in $e//{sense_path} "
            f"let $gi := string(($s/{gi_path}/@value/string(), $e/{gi_path}/@value/string())[1]) "
            f"let $def := string-join(($s/{def_path}//{text_path}/string(), $s/{gloss_path}/{text_path}/string()), ' ') "
            f"where $gi != '' and normalize-space($def) != '' "
            f"return concat(string($e/@id), '|||', $hw, '|||', $gi, '|||', normalize-space($def))"
        )

        raw = dict_service.db_connector.execute_query(query)
        lines = (raw or "").strip().split("\n")
        data = []
        for line in lines:
            parts = line.strip().split("|||")
            if len(parts) == 4:
                eid, hw, pos, text = parts
                norm_p = normalize_pos(pos)
                data.append((eid, hw, norm_p, text))
        return data

    def detect_anomalies(
        self,
        dict_service: Any,
        min_confidence: float = 0.80,
        limit: int = 100,
        cache_ttl_sec: float = 3600.0,
    ) -> List[Dict[str, Any]]:
        data = self._fetch_dataset(dict_service)
        return self.detect_anomalies_from_data(data, min_confidence=min_confidence, limit=limit, cache_ttl_sec=cache_ttl_sec)

    def detect_anomalies_from_data(
        self,
        data: List[Tuple[str, str, str, str]],
        min_confidence: float = 0.80,
        limit: int = 100,
        cache_ttl_sec: float = 3600.0,
    ) -> List[Dict[str, Any]]:
        """Run ML prediction on (eid, hw, orig_pos, text) and flag cross-category contradictions."""
        now = time.time()
        if self.pipeline and (now - self.last_trained < cache_ttl_sec) and self.cached_anomalies:
            return self.cached_anomalies[:limit]

        if not data:
            return []

        # Train ML classifier on top-level root POS categories
        X_all = [d[3] for d in data if d[3]]
        y_all = [get_root_pos(d[2]) for d in data if d[3]]

        counts = Counter(y_all)
        valid_indices = [i for i, label in enumerate(y_all) if counts[label] >= 10]
        X = [X_all[i] for i in valid_indices]
        y = [y_all[i] for i in valid_indices]

        if not X:
            return []

        pipeline = make_pipeline(
            TfidfVectorizer(ngram_range=(1, 2), max_features=25000, sublinear_tf=True),
            SGDClassifier(loss="log_loss", max_iter=30, random_state=42, n_jobs=-1, class_weight="balanced"),
        )
        pipeline.fit(X, y)
        probs = pipeline.predict_proba(X)
        classes = list(pipeline.classes_)

        mismatches = []
        for i, idx in enumerate(valid_indices):
            eid, hw, orig_pos, text = data[idx]
            actual_root = get_root_pos(orig_pos)

            pred_idx = probs[i].argmax()
            pred_root = classes[pred_idx]
            conf = float(probs[i][pred_idx])

            # Only flag when actual root category contradicts predicted root category
            if pred_root != actual_root and conf >= min_confidence:
                mismatches.append({
                    "entry_id": eid,
                    "headword": hw,
                    "actual_pos": str(orig_pos),
                    "predicted_pos": str(pred_root),
                    "confidence": round(conf, 3),
                    "definition": text[:150],
                })

        self.pipeline = pipeline
        self.classes = classes
        self.last_trained = now
        self.cached_anomalies = mismatches

        return mismatches[:limit]


def get_pos_coherence_service() -> POSCoherenceService:
    global _CACHED_SERVICE_INSTANCE
    if _CACHED_SERVICE_INSTANCE is None:
        _CACHED_SERVICE_INSTANCE = POSCoherenceService()
    return _CACHED_SERVICE_INSTANCE
