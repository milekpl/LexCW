"""
POS Tagger Service — Automatic Part-of-Speech tagging for text and dictionary entries.

Supports spaCy NLP model tagging with Penn Treebank, Universal Dependencies,
and custom per-language tagset mappings for lexicographer distinction mapping.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.services.import_converter import normalize_pos
from app.services.pos_coherence_service import POS_ROOT_MAP, get_root_pos

logger = logging.getLogger(__name__)

# Lazy spaCy loading
_SPACY_NLP: Any = None
_SPACY_LOADED: bool = False
_SPACY_NLP_PARSER: Any = None
_SPACY_PARSER_LOADED: bool = False


def _get_spacy_nlp() -> Any:
    global _SPACY_NLP, _SPACY_LOADED
    if not _SPACY_LOADED:
        _SPACY_LOADED = True
        try:
            import spacy
            try:
                _SPACY_NLP = spacy.load(
                    "en_core_web_sm",
                    disable=["parser", "ner", "lemmatizer", "attribute_ruler"]
                )
            except Exception:
                _SPACY_NLP = spacy.blank("en")
        except ImportError:
            _SPACY_NLP = None
    return _SPACY_NLP


def _get_spacy_nlp_parser() -> Any:
    global _SPACY_NLP_PARSER, _SPACY_PARSER_LOADED
    if not _SPACY_PARSER_LOADED:
        _SPACY_PARSER_LOADED = True
        try:
            import spacy
            try:
                _SPACY_NLP_PARSER = spacy.load("en_core_web_sm", disable=["ner", "lemmatizer"])
            except Exception:
                _SPACY_NLP_PARSER = spacy.blank("en")
        except ImportError:
            _SPACY_NLP_PARSER = None
    return _SPACY_NLP_PARSER



# Path to persistent tagset mappings JSON file
TAGSET_MAPPINGS_FILE = Path(__file__).resolve().parent.parent.parent / "config" / "pos_tagset_mappings.json"

# Built-in Penn Treebank & Universal Dependencies POS tag map
PENN_AND_UD_POS_MAP: Dict[str, str] = {
    # Penn Treebank Nouns
    "NN": "Noun",
    "NNS": "Noun",
    "NNP": "Proper Noun",
    "NNPS": "Proper Noun",
    # Penn Treebank Verbs
    "VB": "Verb",
    "VBD": "Verb",
    "VBG": "Verb",
    "VBN": "Verb",
    "VBP": "Verb",
    "VBZ": "Verb",
    "MD": "Auxiliary Verb",
    # Penn Treebank Adjectives
    "JJ": "Adjective",
    "JJR": "Adjective",
    "JJS": "Adjective",
    # Penn Treebank Adverbs
    "RB": "Adverb",
    "RBR": "Adverb",
    "RBS": "Adverb",
    "WRB": "Adverb",
    # Penn Treebank Pronouns
    "PRP": "Pronoun",
    "PRP$": "Possessive Pronoun",
    "WP": "Pronoun",
    "WP$": "Possessive Pronoun",
    # Penn Treebank Prepositions / Conjunctions
    "IN": "Preposition",
    "CC": "Connective",
    # Penn Treebank Determiners / Articles
    "DT": "Determiner",
    "PDT": "Determiner",
    # Penn Treebank Numerals
    "CD": "Cardinal",
    # Penn Treebank Interjections
    "UH": "Interjection",
    # Universal Dependencies (UD) POS Tags
    "NOUN": "Noun",
    "PROPN": "Proper Noun",
    "VERB": "Verb",
    "AUX": "Auxiliary Verb",
    "ADJ": "Adjective",
    "ADV": "Adverb",
    "PRON": "Pronoun",
    "DET": "Determiner",
    "ADP": "Preposition",
    "CONJ": "Connective",
    "CCONJ": "Connective",
    "SCONJ": "Connective",
    "INTJ": "Interjection",
    "NUM": "Cardinal",
    "PART": "Particle",
    "SYM": "Symbol",
    "X": "Other",
}


def _get_spacy_nlp() -> Any:
    global _SPACY_NLP, _SPACY_LOADED
    if not _SPACY_LOADED:
        _SPACY_LOADED = True
        try:
            import spacy
            try:
                _SPACY_NLP = spacy.load(
                    "en_core_web_sm",
                    disable=["parser", "ner", "lemmatizer", "attribute_ruler"]
                )
            except Exception:
                _SPACY_NLP = spacy.blank("en")
        except ImportError:
            _SPACY_NLP = None
    return _SPACY_NLP


# Maps a top-level root POS category to its phrasal category label.
PHRASE_CATEGORY_BY_ROOT_POS: Dict[str, str] = {
    "Noun": "Noun Phrase",
    "Proper Noun": "Noun Phrase",
    "Pronoun": "Noun Phrase",
    "Determiner": "Noun Phrase",
    "Article": "Noun Phrase",
    "Verb": "Verb Phrase",
    "Auxiliary Verb": "Verb Phrase",
    "Adjective": "Adjective Phrase",
    "Adverb": "Adverb Phrase",
    "Preposition": "Prepositional Phrase",
    "Cardinal": "Numeral Phrase",
    "Ordinal": "Numeral Phrase",
}

# Returned when a segment's phrase category cannot be determined.
UNCLASSIFIED_PHRASE: str = "Other Phrase"


# Rule-based suffix and keyword heuristics for POS tagging fallback
POS_SUFFIX_RULES: List[Tuple[re.Pattern[str], str]] = [
    (re.compile(r".*tion$|.*ment$|.*ness$|.*ity$|.*ance$|.*ence$|.*ship$", re.IGNORECASE), "Noun"),
    (re.compile(r".*able$|.*ible$|.*ous$|.*ful$|.*less$|.*ive$|.*ic$", re.IGNORECASE), "Adjective"),
    (re.compile(r".*ly$", re.IGNORECASE), "Adverb"),
    (re.compile(r".*ize$|.*ise$|.*ify$|.*ate$", re.IGNORECASE), "Verb"),
]

DEFINITION_KEYWORD_RULES: List[Tuple[re.Pattern[str], str]] = [
    (re.compile(r"^a\s+kind\s+of|^a\s+type\s+of|^the\s+act\s+of|^a\s+person\s+who|^the\s+quality\s+of|^a\s+state\s+of", re.IGNORECASE), "Noun"),
    (re.compile(r"^to\s+[a-z]+|^cause\s+to|^make\s+or\s+become", re.IGNORECASE), "Verb"),
    (re.compile(r"^relating\s+to|^characteristic\s+of|^having\s+the\s+quality\s+of|^resembling", re.IGNORECASE), "Adjective"),
    (re.compile(r"^in\s+a\s+.*\s+manner|^in\s+a\s+way", re.IGNORECASE), "Adverb"),
]


class POSTaggerService:
    """POS Tagger service with customizable Penn / Universal / per-language tagset mappings."""

    def __init__(self) -> None:
        self._tagset_mappings: Dict[str, Dict[str, str]] = self._load_tagset_mappings()

    def _load_tagset_mappings(self) -> Dict[str, Dict[str, str]]:
        """Load tagset mappings from config file or return built-in defaults."""
        if TAGSET_MAPPINGS_FILE.exists():
            try:
                with open(TAGSET_MAPPINGS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error loading {TAGSET_MAPPINGS_FILE}: {e}")
        return {
            "en": dict(PENN_AND_UD_POS_MAP),
            "universal": dict(PENN_AND_UD_POS_MAP),
        }

    def get_tagset_mappings(self, lang: Optional[str] = None) -> Dict[str, Any]:
        """Retrieve configured tagset mappings for a language or all languages."""
        if lang:
            cleaned_lang = lang.lower().split("-")[0]
            lang_map = self._tagset_mappings.get(cleaned_lang)
            if lang_map:
                return lang_map
            return self._tagset_mappings.get("universal", PENN_AND_UD_POS_MAP)
        return self._tagset_mappings

    def save_tagset_mappings(self, lang: str, mappings: Dict[str, str]) -> Dict[str, Any]:
        """Update and persist tagset mappings for a specific language."""
        cleaned_lang = lang.lower().split("-")[0]
        self._tagset_mappings[cleaned_lang] = mappings
        try:
            TAGSET_MAPPINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(TAGSET_MAPPINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._tagset_mappings, f, indent=2)
            logger.info(f"Saved custom POS tagset mapping for '{cleaned_lang}' ({len(mappings)} rules)")
        except Exception as e:
            logger.error(f"Failed to save tagset mappings file: {e}")
        return self._tagset_mappings[cleaned_lang]

    def normalize_tag(self, raw_tag: str, lang: str = "en", user_map: Optional[Dict[str, str]] = None) -> str:
        """
        Normalize a raw POS tag (Penn Treebank, UD, or custom model tag) to canonical LIFT POS.
        
        Resolution order:
        1. user_map passed explicitly
        2. Configured tagset mapping for the language
        3. Built-in Penn & Universal POS map
        4. Taxonomy root pos map (POS_ROOT_MAP)
        """
        if not raw_tag:
            return ""

        raw_clean = raw_tag.strip()

        # 1. Direct user_map lookup
        if user_map:
            if raw_clean in user_map:
                return user_map[raw_clean]
            if raw_clean.upper() in user_map:
                return user_map[raw_clean.upper()]

        # 2. Configured language tagset lookup
        lang_map = self.get_tagset_mappings(lang)
        if raw_clean in lang_map:
            return lang_map[raw_clean]
        if raw_clean.upper() in lang_map:
            return lang_map[raw_clean.upper()]

        # 3. Penn Treebank & Universal POS lookup
        if raw_clean in PENN_AND_UD_POS_MAP:
            return PENN_AND_UD_POS_MAP[raw_clean]
        if raw_clean.upper() in PENN_AND_UD_POS_MAP:
            return PENN_AND_UD_POS_MAP[raw_clean.upper()]

        # 4. Standard import_converter / pos_coherence normalization
        norm = normalize_pos(raw_clean)
        return get_root_pos(norm) or norm

    def tag_text(self, text: str, lang: str = "en", user_map: Optional[Dict[str, str]] = None) -> List[Dict[str, str]]:
        """Tokenize and tag text with POS labels and canonical LIFT distinctions."""
        if not text or not text.strip():
            return []

        nlp = _get_spacy_nlp()
        if nlp is not None and hasattr(nlp, "pipe_names") and "tagger" in nlp.pipe_names:
            doc = nlp(text)
            tokens = []
            for token in doc:
                fine_tag = token.tag_ or token.pos_
                norm = self.normalize_tag(fine_tag, lang=lang, user_map=user_map) or token.pos_
                tokens.append({
                    "text": token.text,
                    "pos": token.pos_,
                    "tag": fine_tag,
                    "normalized_pos": norm,
                })
            return tokens

        # Fallback regex tokenizer & rule tagger
        words = re.findall(r"\b\w+\b", text)
        result = []
        for word in words:
            pos = "Noun"
            for pattern, target_pos in POS_SUFFIX_RULES:
                if pattern.match(word):
                    pos = target_pos
                    break
            norm = self.normalize_tag(pos, lang=lang, user_map=user_map)
            result.append({
                "text": word,
                "pos": pos,
                "tag": pos[:3].upper(),
                "normalized_pos": norm,
            })
        return result

    def predict_entry_pos(self, entry: Dict[str, Any], lang: str = "en", user_map: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Predict top POS category for a dictionary entry.
        
        Analyzes headword, grammatical info, definitions, and glosses.
        """
        headword = ""
        if isinstance(entry, dict):
            headword = entry.get("headword") or entry.get("lexical_unit") or ""
            existing_pos = entry.get("grammatical_info") or entry.get("pos") or ""
            senses = entry.get("senses") or []
        else:
            existing_pos = getattr(entry, "grammatical_info", "")
            senses = getattr(entry, "senses", [])

        # Check existing explicit POS
        if existing_pos:
            norm_existing = self.normalize_tag(str(existing_pos), lang=lang, user_map=user_map)
            if norm_existing:
                return {
                    "predicted_pos": norm_existing,
                    "original_pos": str(existing_pos),
                    "confidence": 0.95,
                    "method": "existing_grammatical_info",
                }

        # Collect definitions and glosses
        def_texts: List[str] = []
        for sense in senses:
            if isinstance(sense, dict):
                def_val = sense.get("definition") or sense.get("gloss") or ""
                if isinstance(def_val, dict):
                    def_texts.extend([str(v) for v in def_val.values() if v])
                elif isinstance(def_val, str):
                    def_texts.append(def_val)
            else:
                def_val = getattr(sense, "definition", None) or getattr(sense, "gloss", None)
                if isinstance(def_val, str):
                    def_texts.append(def_val)

        full_def = " ".join(def_texts).strip()

        # Rule 1: Definition pattern matching
        for pattern, pos_category in DEFINITION_KEYWORD_RULES:
            if pattern.search(full_def):
                norm_pos = self.normalize_tag(pos_category, lang=lang, user_map=user_map)
                return {
                    "predicted_pos": norm_pos,
                    "confidence": 0.85,
                    "method": "definition_keyword_rule",
                    "matched_definition": full_def[:100],
                }

        # Rule 2: Morphological suffix matching on headword
        if headword:
            for pattern, pos_category in POS_SUFFIX_RULES:
                if pattern.match(headword):
                    norm_pos = self.normalize_tag(pos_category, lang=lang, user_map=user_map)
                    return {
                        "predicted_pos": norm_pos,
                        "confidence": 0.70,
                        "method": "headword_suffix_rule",
                    }

        # Fallback default
        return {
            "predicted_pos": "Noun",
            "confidence": 0.50,
            "method": "fallback_default",
        }

    def tag_entries_batch(self, entries: List[Dict[str, Any]], lang: str = "en", user_map: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """Predict POS for a list of entry dicts."""
        results = []
        for entry in entries:
            eid = entry.get("id") or entry.get("entry_id") or ""
            pred = self.predict_entry_pos(entry, lang=lang, user_map=user_map)
            results.append({
                "entry_id": eid,
                "headword": entry.get("headword", ""),
                **pred,
            })
        return results

    def _phrase_category_for_root_pos(self, root_pos: str) -> str:
        """Map a root POS category to a phrasal category label (Noun -> Noun Phrase)."""
        if not root_pos:
            return UNCLASSIFIED_PHRASE
        return PHRASE_CATEGORY_BY_ROOT_POS.get(get_root_pos(root_pos), UNCLASSIFIED_PHRASE)

    def _detect_phrase_category(self, seg: str, lang: str) -> str:
        """Detect the phrasal category (Noun Phrase, Verb Phrase, ...) of a segment.

        Uses the spaCy dependency parser (root token POS) when available, falling
        back to lightweight suffix/keyword heuristics otherwise.
        """
        nlp_parser = _get_spacy_nlp_parser()
        if nlp_parser is not None and hasattr(nlp_parser, "pipe_names") and "parser" in nlp_parser.pipe_names:
            doc = nlp_parser(seg)
            roots = [tok for tok in doc if tok.dep_ == "ROOT" or tok.head == tok]
            root_tok = roots[0] if roots else doc[0]
            root_raw = root_tok.tag_ or root_tok.pos_
            norm_pos = self.normalize_tag(root_raw, lang=lang) or root_tok.pos_
            return self._phrase_category_for_root_pos(norm_pos)

        # Fallback: no parser available.
        text = seg.strip().lower()
        if text.startswith("to "):
            return "Verb Phrase"
        for word in re.findall(r"\b\w+\b", seg):
            for pattern, pos_cat in POS_SUFFIX_RULES:
                if pattern.match(word):
                    return self._phrase_category_for_root_pos(pos_cat)
        return "Noun Phrase"

    def analyze_definition_phrases(
        self,
        definition_text: str,
        lang: str = "en",
        expected_pos: Optional[str] = None,
        delimiter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Split a definition by delimiter (e.g. ',', ';', or custom) and analyze the
        phrase category (Noun Phrase, Verb Phrase, Adjective Phrase, ...) of each
        segment.

        Two modes:
        - If ``expected_pos`` is supplied the comparison is anchored to that POS
          (used by the manual definition-coherence API tool).
        - Otherwise the dominant phrase category among the segments is used as the
          reference, so the rule checks *internal* phrase-category coherence across
          the comma-separated segments (it does NOT compare the definition against
          the headword / entry POS).
        """
        if not definition_text or not definition_text.strip():
            return {
                "is_consistent": True,
                "segments": [],
                "contradictions": [],
            }

        # Check CacheService cache first
        from app.services.cache_service import CacheService
        import json
        import hashlib

        cache = CacheService()
        cache_key = None
        if cache.is_available():
            h = hashlib.md5(f"{definition_text}:{lang}:{expected_pos}:{delimiter}".encode('utf-8')).hexdigest()
            cache_key = f"pos_tagger:analysis:{h}"
            try:
                cached_val = cache.get(cache_key)
                if cached_val:
                    return json.loads(cached_val)
            except Exception:
                pass

        delim = delimiter if delimiter else ",;"
        if len(delim) == 1:
            delim_pattern = rf"{re.escape(delim)}\s*"
        else:
            delim_pattern = rf"[{re.escape(delim)}]\s*"

        segments = [s.strip() for s in re.split(delim_pattern, definition_text) if s.strip()]

        analyzed_segments = []
        for seg in segments:
            phrase_category = self._detect_phrase_category(seg, lang)
            analyzed_segments.append({
                "segment_text": seg,
                "phrase_category": phrase_category,
            })

        # Determine the reference phrase category.
        classified = [
            s["phrase_category"]
            for s in analyzed_segments
            if s["phrase_category"] != UNCLASSIFIED_PHRASE
        ]
        if expected_pos:
            reference = self._phrase_category_for_root_pos(get_root_pos(expected_pos))
        elif classified:
            # Most common phrase category; ties resolve to the first occurrence.
            reference = max(classified, key=classified.count)
        else:
            reference = ""

        contradictions = []
        for seg in analyzed_segments:
            seg_cat = seg["phrase_category"]
            if not reference or seg_cat == UNCLASSIFIED_PHRASE:
                continue
            if seg_cat != reference:
                contradictions.append({
                    "segment_text": seg["segment_text"],
                    "found_pos": seg_cat,
                    "expected_pos": reference,
                })

        res = {
            "is_consistent": len(contradictions) == 0,
            "reference_phrase_category": reference,
            "expected_pos": reference,
            "segments": analyzed_segments,
            "contradictions": contradictions,
        }

        if cache.is_available() and cache_key:
            try:
                cache.set(cache_key, json.dumps(res), ttl=86400 * 7)  # Cache for 7 days
            except Exception:
                pass

        return res



_CACHED_POS_TAGGER: Optional[POSTaggerService] = None



def get_pos_tagger_service() -> POSTaggerService:
    """Return singleton POSTaggerService instance."""
    global _CACHED_POS_TAGGER
    if _CACHED_POS_TAGGER is None:
        _CACHED_POS_TAGGER = POSTaggerService()
    return _CACHED_POS_TAGGER
