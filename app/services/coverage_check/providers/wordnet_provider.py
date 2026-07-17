"""
WordNet provider — converts NLTK WordNet to CLSF.

Extracts synsets, definitions, examples, and cross-lingual
translations via Open Multilingual WordNet (OMW).
"""
from __future__ import annotations

from typing import List, Optional, Dict, Set

from app.services.coverage_check.models import (
    LexicalSenseFormat, Metadata, Entry, Sense, Example,
)
from app.services.coverage_check.providers.base import ResourceProvider, ResourceType


# POS mapping from WordNet tag to human-readable
_WN_POS_MAP = {
    "n": "noun",
    "v": "verb",
    "a": "adjective",
    "s": "adjective",
    "r": "adverb",
}

# ISO 639-1 (2-letter) → ISO 639-3 (3-letter) mapping for OMW
_ISO639_1_TO_3 = {
    "en": "eng", "pl": "pol", "de": "deu", "fr": "fra",
    "es": "spa", "it": "ita", "pt": "por", "nl": "nld",
    "ru": "rus", "ja": "jpn", "zh": "zho", "ar": "arb",
    "cs": "ces", "da": "dan", "fi": "fin", "el": "ell",
    "he": "heb", "hu": "hun", "id": "ind", "ko": "kor",
    "no": "nor", "sv": "swe", "tr": "tur", "vi": "vie",
}


def _to_omw_code(lang: str) -> str:
    """Convert ISO 639-1 code to ISO 639-3 for OMW."""
    if len(lang) == 3:
        return lang
    return _ISO639_1_TO_3.get(lang, lang)


class WordNetProvider(ResourceProvider):
    """Convert NLTK WordNet to CLSF.

    Optionally includes cross-lingual translations via OMW-1.4.
    No input file needed — uses NLTK's bundled WordNet data.
    """

    def __init__(self, language: str = "en", target_language: str = None):
        self.language = language
        self.target_language = target_language
        self._wn = None

    def _get_wn(self):
        if self._wn is None:
            import nltk
            from nltk.corpus import wordnet as wn
            self._wn = wn
        return self._wn

    def to_clsf(self, source_path: str = None, **kwargs) -> LexicalSenseFormat:
        wn = self._get_wn()

        # Group synsets by (lemma, POS) to build multi-sense entries
        entries_by_key: Dict[str, Entry] = {}

        for synset in wn.all_synsets():
            pos = _WN_POS_MAP.get(synset.pos(), synset.pos())
            for lemma in synset.lemmas():
                name = lemma.name().replace("_", " ")
                key = f"{name}|{pos}"

                if key not in entries_by_key:
                    entries_by_key[key] = Entry(
                        headword=name,
                        part_of_speech=pos,
                        language=self.language,
                        source="wordnet",
                        senses=[],
                    )

                # Get translations for target language
                translations = []
                if self.target_language and self.target_language != self.language:
                    try:
                        omw_code = _to_omw_code(self.target_language)
                        trans_lemmas = synset.lemmas(omw_code)
                        translations = [t.name().replace("_", " ") for t in trans_lemmas]
                    except Exception:
                        pass

                sense = Sense(
                    id=f"wn:{synset.offset()}{synset.pos()}",
                    definition=synset.definition(),
                    translations=translations,
                    examples=[Example(languages={"en": ex}) for ex in synset.examples()],
                    synset_id=f"wn:{synset.offset()}{synset.pos()}",
                    semantic_domain=synset.lexname(),
                )
                entries_by_key[key].senses.append(sense)

        entries = list(entries_by_key.values())

        return LexicalSenseFormat(
            metadata=Metadata(
                name="WordNet",
                version="3.1",
                language=self.language,
                description=f"Princeton WordNet via NLTK ({len(entries)} entries)",
            ),
            entries=entries,
        )

    def get_word_entry(self, word: str) -> Optional[Entry]:
        """Get a single word's entry with all synsets."""
        wn = self._get_wn()
        synsets = wn.synsets(word)
        if not synsets:
            return None

        # Use first synset's POS as the primary POS
        primary_pos = _WN_POS_MAP.get(synsets[0].pos(), synsets[0].pos())

        senses = []
        for synset in synsets:
            translations = []
            if self.target_language and self.target_language != self.language:
                try:
                    omw_code = _to_omw_code(self.target_language)
                    trans_lemmas = synset.lemmas(omw_code)
                    translations = [t.name().replace("_", " ") for t in trans_lemmas]
                except Exception:
                    pass

            senses.append(Sense(
                id=f"wn:{synset.offset()}{synset.pos()}",
                definition=synset.definition(),
                translations=translations,
                examples=list(synset.examples()),
                synset_id=f"wn:{synset.offset()}{synset.pos()}",
                semantic_domain=synset.lexname(),
            ))

        return Entry(
            headword=word,
            part_of_speech=primary_pos,
            language=self.language,
            source="wordnet",
            senses=senses,
        )

    def get_synset_count(self, word: str) -> int:
        """Get the number of synsets for a word."""
        wn = self._get_wn()
        return len(wn.synsets(word))

    def get_synsets_for_language(self, word: str, target_language: str = None) -> List[Dict]:
        """Get synsets with optional cross-lingual translations."""
        wn = self._get_wn()
        synsets = wn.synsets(word)
        result = []
        for syn in synsets:
            entry = {
                "synset_id": f"wn:{syn.offset()}{syn.pos()}",
                "definition": syn.definition(),
            }
            if target_language:
                try:
                    omw_code = _to_omw_code(target_language)
                    trans = syn.lemmas(omw_code)
                    entry["translations"] = [t.name().replace("_", " ") for t in trans]
                except Exception:
                    entry["translations"] = []
            result.append(entry)
        return result

    def supported_formats(self) -> List[str]:
        return []  # WordNet doesn't need input files

    @property
    def resource_type(self) -> ResourceType:
        return ResourceType.DICTIONARY
