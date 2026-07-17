"""
Coverage checking service — orchestrates providers, analyzers, and reports.

This is the main entry point for all coverage checking functionality.
It coordinates resource providers, gap analysis, systematicity checking,
and sense alignment.
"""
from __future__ import annotations

import os
import logging
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional, List

from app.services.coverage_check.models import (
    LexicalSenseFormat, Metadata, Entry, Sense,
)
from app.services.coverage_check.gap_analyzer import GapAnalyzer
from app.services.coverage_check.systematicity_checker import SystematicityChecker
from app.services.coverage_check.sense_alignment import SenseAlignmentAnalyzer
from app.services.coverage_check.providers.text_provider import TextProvider
from app.services.coverage_check.providers.subtlex_provider import SubtlexProvider
from app.services.coverage_check.providers.wordnet_provider import WordNetProvider

logger = logging.getLogger(__name__)

# XQuery to extract all headwords and their sense counts from the BaseX dictionary.
_DICT_HEADWORDS_QUERY = """{prologue}
<results>{{
  for $e in collection('{db_name}')//{entry_path}
  let $hw := ($e/{lexical_unit_path}/{form_path}/{text_path}/string())[1]
  let $pos := ($e/{grammatical_info_path}/@value/string())[1]
  let $pos2 := ($e//{sense_path}/{grammatical_info_path}/@value/string())[1]
  let $sc := count($e//{sense_path})
  let $def := ($e//{sense_path}/{definition_path}/{form_path}/{text_path}/string())[1]
  where $hw != ''
  return <item hw="{{lower-case($hw)}}" pos="{{if ($pos) then $pos else $pos2}}" senses="{{$sc}}" def="{{if ($def) then $def else ''}}"/>
}}</results>"""

# XQuery to extract per-sense data (headword, POS, definition, glosses) for gap analysis.
_DICT_SENSE_DATA_QUERY = """{prologue}
<results>{{
  for $e in collection('{db_name}')//{entry_path}
  let $hw := ($e/{lexical_unit_path}/{form_path}/{text_path}/string())[1]
  let $pos := ($e/{grammatical_info_path}/@value/string())[1]
  let $pos2 := ($e//{sense_path}/{grammatical_info_path}/@value/string())[1]
  where $hw != ''
  for $s in $e//{sense_path}
  let $def := ($s/{definition_path}/{form_path}/{text_path}/string())[1]
  let $glosses := string-join(
    (
      ($s/{definition_path}/{form_path}/{text_path}/string())[. != ''],
      ($s/{gloss_path}/{form_path}/{text_path}/string())[. != '']
    ),
    '|||'
  )
  return <item hw="{{lower-case($hw)}}" pos="{{if ($pos) then $pos else $pos2}}" def="{{normalize-space($def)}}" glosses="{{$glosses}}"/>
}}</results>"""

# XQuery to extract entries without senses (typically variant/minor entries).
_DICT_VARIANT_ENTRIES_QUERY = """{prologue}
<results>{{
  for $e in collection('{db_name}')//{entry_path}
  let $hw := lower-case(($e/{lexical_unit_path}/{form_path}/{text_path}/string())[1])
  let $has_senses := exists($e//{sense_path})
  where $hw != '' and not($has_senses)
  let $pos := ($e/{grammatical_info_path}/@value/string())[1]
  return <item hw="{{$hw}}" pos="{{if ($pos) then $pos else ''}}"/>
}}</results>"""



class CoverageService:
    """Orchestration service for coverage checking."""

    def __init__(self):
        self._wn_provider_cache: Dict[str, WordNetProvider] = {}
        self._basex_dictionary_cache: Optional[LexicalSenseFormat] = None
        self._basex_variant_headwords_cache: Optional[Set[str]] = None
        self._gap_analysis_cache: Optional[Dict[str, Any]] = None
        self._gap_analysis_lang_key: str = ""

    def _get_wn_provider(self, language: str = "en", target_language: str = None) -> WordNetProvider:
        key = f"{language}:{target_language or ''}"
        if key not in self._wn_provider_cache:
            self._wn_provider_cache[key] = WordNetProvider(
                language=language, target_language=target_language,
            )
        return self._wn_provider_cache[key]

    def _load_dictionary_from_basex(self) -> Optional[LexicalSenseFormat]:
        """Load all headwords from the BaseX dictionary as a CLSF.

        Uses the Flask app injector to access the DictionaryService's
        BaseX connector and XQuery builder. Returns None if BaseX is
        unavailable or the query fails.
        """
        if self._basex_dictionary_cache is not None:
            return self._basex_dictionary_cache

        try:
            from flask import current_app
            from app.services.dictionary_service import DictionaryService
            from app.utils.xquery_builder import XQueryBuilder

            dict_service = current_app.injector.get(DictionaryService)
            connector = dict_service.db_connector
            db_name = connector.database
            if not db_name or not connector.is_connected():
                return None

            has_ns = dict_service._detect_namespace_usage()
            prologue = XQueryBuilder.get_namespace_prologue(has_ns)
            entry_path = XQueryBuilder.get_element_path("entry", has_ns)
            lexical_unit_path = XQueryBuilder.get_element_path("lexical-unit", has_ns)
            form_path = XQueryBuilder.get_element_path("form", has_ns)
            text_path = XQueryBuilder.get_element_path("text", has_ns)
            sense_path = XQueryBuilder.get_element_path("sense", has_ns)
            grammatical_info_path = XQueryBuilder.get_element_path("grammatical-info", has_ns)
            definition_path = XQueryBuilder.get_element_path("definition", has_ns)

            query = _DICT_HEADWORDS_QUERY.format(
                prologue=prologue,
                db_name=db_name,
                entry_path=entry_path,
                lexical_unit_path=lexical_unit_path,
                form_path=form_path,
                text_path=text_path,
                sense_path=sense_path,
                grammatical_info_path=grammatical_info_path,
                definition_path=definition_path,
            )

            xml_result = connector.execute_query(query)
            if not xml_result:
                logger.warning("BaseX headword query returned empty result")
                return None

            root = ET.fromstring(xml_result)
            entries = []
            for item in root.findall("item"):
                hw = (item.get("hw") or "").strip().lower()
                pos = (item.get("pos") or "").strip()
                senses_count = int(item.get("senses") or "1")
                defn = (item.get("def") or "").strip()

                if not hw:
                    continue

                senses = [
                    Sense(
                        id=f"{hw}_sense_{i}",
                        definition=defn if i == 0 else "",
                    )
                    for i in range(max(senses_count, 1))
                ]
                entries.append(Entry(
                    headword=hw,
                    part_of_speech=pos if pos else None,
                    senses=senses,
                ))

            if not entries:
                logger.warning("No entries extracted from BaseX")
                return None

            self._basex_dictionary_cache = LexicalSenseFormat(
                metadata=Metadata(
                    name=db_name,
                    description="Auto-loaded from BaseX dictionary",
                ),
                entries=entries,
            )
            logger.info("Loaded %d headwords from BaseX dictionary '%s'", len(entries), db_name)
            return self._basex_dictionary_cache

        except Exception as e:
            logger.warning("Failed to load dictionary from BaseX: %s", e, exc_info=True)
            return None

    def _load_dictionary_with_senses_from_basex(self) -> Optional[LexicalSenseFormat]:
        """Load all entries with per-sense glosses (translations) from BaseX.

        Returns one row per sense with headword, POS, definition, and glosses.
        Groups senses by headword into Entry objects.
        """
        try:
            from flask import current_app
            from app.services.dictionary_service import DictionaryService
            from app.utils.xquery_builder import XQueryBuilder

            dict_service = current_app.injector.get(DictionaryService)
            connector = dict_service.db_connector
            db_name = connector.database
            if not db_name or not connector.is_connected():
                return None

            has_ns = dict_service._detect_namespace_usage()
            prologue = XQueryBuilder.get_namespace_prologue(has_ns)
            entry_path = XQueryBuilder.get_element_path("entry", has_ns)
            lexical_unit_path = XQueryBuilder.get_element_path("lexical-unit", has_ns)
            form_path = XQueryBuilder.get_element_path("form", has_ns)
            text_path = XQueryBuilder.get_element_path("text", has_ns)
            sense_path = XQueryBuilder.get_element_path("sense", has_ns)
            grammatical_info_path = XQueryBuilder.get_element_path("grammatical-info", has_ns)
            definition_path = XQueryBuilder.get_element_path("definition", has_ns)
            gloss_path = XQueryBuilder.get_element_path("gloss", has_ns)

            query = _DICT_SENSE_DATA_QUERY.format(
                prologue=prologue,
                db_name=db_name,
                entry_path=entry_path,
                lexical_unit_path=lexical_unit_path,
                form_path=form_path,
                text_path=text_path,
                sense_path=sense_path,
                grammatical_info_path=grammatical_info_path,
                definition_path=definition_path,
                gloss_path=gloss_path,
            )

            xml_result = connector.execute_query(query)
            if not xml_result:
                logger.warning("BaseX sense data query returned empty result")
                return None

            root = ET.fromstring(xml_result)

            # Group sense rows by headword
            headword_data: Dict[str, Dict[str, Any]] = {}
            for item in root.findall("item"):
                hw = (item.get("hw") or "").strip().lower()
                pos = (item.get("pos") or "").strip()
                defn = (item.get("def") or "").strip()
                glosses_str = (item.get("glosses") or "").strip()
                glosses = [g.strip() for g in glosses_str.split("|||") if g.strip()] if glosses_str else []

                if not hw:
                    continue

                if hw not in headword_data:
                    headword_data[hw] = {"pos": pos, "senses": []}

                headword_data[hw]["senses"].append({
                    "definition": defn,
                    "glosses": glosses,
                })

            entries = []
            for hw, data in headword_data.items():
                senses = []
                for i, s in enumerate(data["senses"]):
                    senses.append(Sense(
                        id=f"{hw}_sense_{i}",
                        definition=s["definition"],
                        translations=s["glosses"] if s["glosses"] else [],
                    ))

                entries.append(Entry(
                    headword=hw,
                    part_of_speech=data["pos"] if data["pos"] else None,
                    senses=senses,
                ))

            # Also fetch entries without senses (variant/minor entries)
            variant_entries = self._load_variant_entries_from_basex(
                connector, has_ns, prologue, entry_path, lexical_unit_path,
                form_path, text_path, sense_path, grammatical_info_path
            )
            if variant_entries:
                variant_hw_set = set()
                for entry in variant_entries:
                    if entry.headword not in headword_data:
                        entries.append(entry)
                        variant_hw_set.add(entry.headword)
                if variant_hw_set:
                    logger.info("Added %d variant entries without senses", len(variant_hw_set))
                    self._basex_variant_headwords_cache = variant_hw_set

            if not entries:
                logger.warning("No sense data extracted from BaseX")
                return None

            logger.info("Loaded %d headwords with %d senses from BaseX", len(entries),
                       sum(len(e.senses) for e in entries))
            return LexicalSenseFormat(
                metadata=Metadata(
                    name=db_name,
                    description="Dictionary with per-sense glosses from BaseX",
                ),
                entries=entries,
            )

        except Exception as e:
            logger.warning("Failed to load sense data from BaseX: %s", e, exc_info=True)
            return None

    def _load_variant_entries_from_basex(
        self,
        connector,
        has_ns: bool,
        prologue: str,
        entry_path: str,
        lexical_unit_path: str,
        form_path: str,
        text_path: str,
        sense_path: str,
        grammatical_info_path: str,
    ) -> Optional[List[Entry]]:
        """Load entries without senses (variant/minor entries) from BaseX."""
        try:
            db_name = connector.database
            query = _DICT_VARIANT_ENTRIES_QUERY.format(
                prologue=prologue,
                db_name=db_name,
                entry_path=entry_path,
                lexical_unit_path=lexical_unit_path,
                form_path=form_path,
                text_path=text_path,
                sense_path=sense_path,
                grammatical_info_path=grammatical_info_path,
            )

            xml_result = connector.execute_query(query)
            if not xml_result:
                return None

            root = ET.fromstring(xml_result)
            entries = []
            for item in root.findall("item"):
                hw = (item.get("hw") or "").strip().lower()
                pos = (item.get("pos") or "").strip()
                if hw:
                    entries.append(Entry(
                        headword=hw,
                        part_of_speech=pos if pos else None,
                        senses=[],
                    ))
            return entries if entries else None

        except Exception as e:
            logger.warning("Failed to load variant entries from BaseX: %s", e, exc_info=True)
            return None

    def _load_variant_entries_from_basex(
        self,
        connector,
        has_ns,
        prologue,
        entry_path,
        lexical_unit_path,
        form_path,
        text_path,
        sense_path,
        grammatical_info_path,
    ) -> List[Entry]:
        """Load variant/minor entries (entries without senses) from BaseX.

        These are typically entries that exist only as variant forms
        of main entries (e.g., 'advertize' as variant of 'advertise').
        """
        try:
            db_name = connector.database
            query = _DICT_VARIANT_ENTRIES_QUERY.format(
                prologue=prologue,
                db_name=db_name,
                entry_path=entry_path,
                lexical_unit_path=lexical_unit_path,
                form_path=form_path,
                text_path=text_path,
                sense_path=sense_path,
                grammatical_info_path=grammatical_info_path,
            )

            xml_result = connector.execute_query(query)
            if not xml_result:
                return []

            root = ET.fromstring(xml_result)
            entries = []
            for item in root.findall("item"):
                hw = (item.get("hw") or "").strip().lower()
                pos = (item.get("pos") or "").strip()

                if not hw:
                    continue

                entries.append(Entry(
                    headword=hw,
                    part_of_speech=pos if pos else None,
                    senses=[],  # No senses for variant entries
                ))

            return entries

        except Exception as e:
            logger.warning("Failed to load variant entries from BaseX: %s", e)
            return []

    def check_resource_coverage(
        self,
        source_path: str,
        resource_type: str,
        language: str = "en",
        target_language: str = None,
    ) -> Dict[str, Any]:
        """Check coverage of a resource file.

        Args:
            source_path: Path to the resource file
            resource_type: 'text', 'subtlex', or 'wordnet'
            language: Language code
            target_language: Target language for translations

        Returns:
            Dictionary with entries and metadata
        """
        if resource_type == "text":
            provider = TextProvider(language=language, target_language=target_language)
        elif resource_type == "subtlex":
            provider = SubtlexProvider(language=language)
        elif resource_type == "wordnet":
            provider = WordNetProvider(language=language, target_language=target_language)
            source_path = None
        else:
            raise ValueError(f"Unknown resource type: {resource_type}")

        clsf = provider.to_clsf(source_path)
        return {
            "metadata": clsf.metadata.to_dict(),
            "entry_count": len(clsf.entries),
            "entries": [e.to_dict() for e in clsf.entries[:100]],  # Limit for API
        }

    def check_text_coverage(
        self,
        text: str,
        language: str = "en",
        target_language: str = None,
    ) -> Dict[str, Any]:
        """Check coverage of raw text.

        Tokenizes, lemmatizes, and deduplicates words from the text.
        """
        provider = TextProvider(language=language, target_language=target_language)
        clsf = provider._text_to_clsf(text, source_name="text-input")
        return {
            "metadata": clsf.metadata.to_dict(),
            "entry_count": len(clsf.entries),
            "entries": [e.to_dict() for e in clsf.entries],
            "input_length": len(text),
        }

    def invalidate_basex_cache(self) -> None:
        """Clear the cached BaseX dictionary and gap analysis. Call after dictionary edits."""
        self._basex_dictionary_cache = None
        self._gap_analysis_cache = None

    def check_systematicity(
        self,
        language: str = "en",
        dictionary: LexicalSenseFormat = None,
    ) -> Dict[str, Any]:
        """Run systematicity checks.

        If no dictionary is provided, attempts to load headwords from the
        BaseX dictionary automatically.
        """
        checker = SystematicityChecker(language=language)

        if dictionary is None:
            dictionary = self._load_dictionary_from_basex()

        if dictionary is None:
            return {
                "total_checks": len(checker._datasets),
                "overall_coverage": 0.0,
                "checks": [],
                "message": "No dictionary available — showing reference categories only",
                "categories": list(checker._datasets.keys()),
            }

        report = checker.check(dictionary)
        return {
            "total_checks": report.total_checks,
            "overall_coverage": report.overall_coverage,
            "checks": [
                {
                    "category": getattr(c, 'category_name', c.category.value),
                    "reference_count": c.reference_count,
                    "found_count": c.found_count,
                    "missing_count": c.missing_count,
                    "coverage_percent": c.coverage_percent,
                    "missing_items": c.missing_items[:50],
                }
                for c in report.checks
            ],
        }

    def check_sense_alignment(
        self,
        language: str = "en",
        target_language: str = None,
        dictionary: LexicalSenseFormat = None,
        threshold_low: float = 0.5,
        threshold_high: float = 2.0,
    ) -> Dict[str, Any]:
        """Compare dictionary sense counts against WordNet."""
        wn_provider = self._get_wn_provider(language, target_language)
        wn_clsf = wn_provider.to_clsf()

        if dictionary is None:
            dictionary = self._load_dictionary_with_senses_from_basex()

        if dictionary is None:
            return {
                "total_checked": 0,
                "flagged_count": 0,
                "words": [],
                "message": "No dictionary available",
            }

        analyzer = SenseAlignmentAnalyzer(
            threshold_low=threshold_low,
            threshold_high=threshold_high,
        )
        report = analyzer.analyze(dictionary, wn_clsf)
        return {
            "total_checked": report.total_checked,
            "flagged_count": report.flagged_count,
            "words": [
                {
                    "headword": w.headword,
                    "dict_count": w.dict_count,
                    "wn_count": w.wn_count,
                    "ratio": round(w.ratio, 2),
                    "status": w.status.value,
                    "per_sense": w.per_sense,
                }
                for w in report.words
            ],
        }

    def get_wordnet_entry(self, word: str, language: str = "en", target_language: str = None) -> Optional[Entry]:
        """Get a single word's WordNet entry."""
        provider = self._get_wn_provider(language, target_language)
        return provider.get_word_entry(word)

    def get_wordnet_synset_count(self, word: str, language: str = "en") -> int:
        """Get the number of synsets for a word."""
        provider = self._get_wn_provider(language)
        return provider.get_synset_count(word)

    def run_gap_analysis(
        self,
        baseline: LexicalSenseFormat,
        dictionary: LexicalSenseFormat,
    ) -> Dict[str, Any]:
        """Run gap analysis between two CLSF datasets."""
        analyzer = GapAnalyzer(baseline=baseline, dictionary=dictionary)
        result = analyzer.analyze()
        return {
            "summary": {
                "date": result.summary.date,
                "baseline": result.summary.baseline,
                "baseline_version": result.summary.baseline_version,
                "dictionary": result.summary.flex_project,
                "total_headwords_baseline": result.summary.total_headwords_baseline,
                "total_headwords_flex": result.summary.total_headwords_flex,
                "headword_coverage": result.summary.headword_coverage,
                "total_senses_baseline": result.summary.total_senses_baseline,
                "total_senses_flex": result.summary.total_senses_flex,
                "sense_coverage": result.summary.sense_coverage,
            },
            "missing_headwords": [
                {
                    "headword": mh.headword,
                    "pos": mh.pos,
                    "priority": mh.priority,
                    "translations": mh.translations,
                }
                for mh in result.missing_headwords
            ],
            "missing_senses": [
                {
                    "headword": ms.headword,
                    "baseline_senses": ms.baseline_senses,
                    "flex_senses": ms.flex_senses,
                    "missing_translations": ms.missing_translations,
                    "missing_senses": ms.missing_senses[:10] if ms.missing_senses else [],
                }
                for ms in result.missing_senses
            ],
            "translation_gaps": [
                {
                    "headword": tg["headword"],
                    "existing_translations": tg["existing_translations"][:5],
                    "missing_translations": tg["missing_translations"][:10],
                }
                for tg in result.translation_gaps
            ],
        }

    def run_wordnet_gap_analysis(
        self,
        language: str = "en",
        target_language: str = None,
    ) -> Dict[str, Any]:
        """Run gap analysis comparing WordNet against the BaseX dictionary."""
        wn_provider = self._get_wn_provider(language, target_language)
        wn_clsf = wn_provider.to_clsf()
        dictionary = self._load_dictionary_with_senses_from_basex()

        if dictionary is None:
            return {
                "summary": {},
                "missing_headwords": [],
                "missing_senses": [],
                "translation_gaps": [],
                "message": "No dictionary available",
            }

        return self.run_gap_analysis(wn_clsf, dictionary)

    def get_cached_gap_analysis(
        self,
        language: str = "en",
        target_language: str = None,
    ) -> Optional[Dict[str, Any]]:
        """Get cached gap analysis. Returns None if not cached or language changed."""
        lang_key = f"{language}:{target_language or ''}"
        if self._gap_analysis_cache and self._gap_analysis_lang_key == lang_key:
            return self._gap_analysis_cache
        return None

    def compute_and_cache_gap_analysis(
        self,
        language: str = "en",
        target_language: str = None,
    ) -> Dict[str, Any]:
        """Compute gap analysis and cache the full result."""
        result = self.run_wordnet_gap_analysis(language, target_language)
        self._gap_analysis_cache = result
        self._gap_analysis_lang_key = f"{language}:{target_language or ''}"
        return result

    def invalidate_gap_analysis_cache(self) -> None:
        """Clear the cached gap analysis. Call after dictionary edits."""
        self._gap_analysis_cache = None

    def filter_gap_analysis(
        self,
        result: Dict[str, Any],
        search: str = "",
        priority: str = "",
        pos: str = "",
        page: int = 1,
        per_page: int = 50,
    ) -> Dict[str, Any]:
        """Filter and paginate a gap analysis result without re-running."""
        missing_hw = list(result.get("missing_headwords", []))

        if search:
            missing_hw = [mh for mh in missing_hw if search in mh.get("headword", "").lower()]
        if priority:
            missing_hw = [mh for mh in missing_hw if mh.get("priority") == priority]
        if pos:
            missing_hw = [mh for mh in missing_hw if pos in (mh.get("pos") or "").lower()]

        total = len(missing_hw)
        start = (page - 1) * per_page
        end = start + per_page
        paginated = missing_hw[start:end]

        return {
            "summary": result.get("summary", {}),
            "missing_headwords": paginated,
            "missing_headwords_total": total,
            "missing_senses": result.get("missing_senses", [])[:per_page],
            "translation_gaps": result.get("translation_gaps", [])[:per_page],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page,
            },
        }

    def generate_report(
        self,
        baseline: LexicalSenseFormat,
        dictionary: LexicalSenseFormat,
        format: str = "markdown",
    ) -> str:
        """Generate a gap analysis report."""
        analyzer = GapAnalyzer(baseline=baseline, dictionary=dictionary)
        result = analyzer.analyze()
        return result.generate_report(format=format)

    def import_clsf_file(self, file_path: str) -> Optional[LexicalSenseFormat]:
        """Import a CLSF file (JSON or YAML)."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.endswith('.yaml') or file_path.endswith('.yml'):
                    import yaml
                    data = yaml.safe_load(f)
                else:
                    import json
                    data = json.load(f)

            # Convert dict to CLSF
            metadata = data.get('metadata', {})
            entries_data = data.get('entries', [])

            entries = []
            for entry_data in entries_data:
                senses = []
                for sense_data in entry_data.get('senses', []):
                    senses.append(Sense(
                        id=sense_data.get('id', ''),
                        definition=sense_data.get('definition', ''),
                        translations=sense_data.get('translations', []),
                        examples=[
                            Example(languages=e.get('languages', {}))
                            if isinstance(e, dict) else Example(text=e)
                            if isinstance(e, str) else e
                            for e in sense_data.get('examples', [])
                        ] if sense_data.get('examples') else [],
                        semantic_domain=sense_data.get('semantic_domain'),
                        synset_id=sense_data.get('synset_id'),
                    ))

                entries.append(Entry(
                    headword=entry_data.get('headword', ''),
                    part_of_speech=entry_data.get('part_of_speech'),
                    senses=senses,
                    variants=entry_data.get('variants', []),
                ))

            return LexicalSenseFormat(
                metadata=Metadata(
                    name=metadata.get('name', 'Imported CLSF'),
                    version=metadata.get('version', ''),
                    language=metadata.get('language', ''),
                    description=metadata.get('description', ''),
                ),
                entries=entries,
            )

        except Exception as e:
            logger.warning("Failed to import CLSF file: %s", e, exc_info=True)
            return None
