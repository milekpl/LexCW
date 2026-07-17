"""
DANTE XML provider — converts DANTE lexical entries to CLSF.

DANTE (Dictionary of the Association for National Language Enhancement)
is a large English lexical resource with headwords, variants, senses,
examples, collocations, and usage labels.
"""
from __future__ import annotations

import logging
import os
import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional

from app.services.coverage_check.models import (
    LexicalSenseFormat, Metadata, Entry, Sense, Example,
)
from app.services.coverage_check.providers.base import ResourceProvider, ResourceType

logger = logging.getLogger(__name__)

# POS code mapping from DANTE to standard POS
_DANTE_POS_MAP = {
    'n': 'noun',
    'v': 'verb',
    'adj': 'adjective',
    'adv': 'adverb',
    'prep': 'preposition',
    'conj': 'conjunction',
    'pron': 'pronoun',
    'num': 'numeral',
    'interj': 'interjection',
    'det': 'determiner',
    'art': 'article',
}


class DanteProvider(ResourceProvider):
    """Convert DANTE XML to CLSF."""

    def __init__(self, xml_path: str):
        self.xml_path = xml_path
        self._root = None

    def _strip_namespaces(self) -> None:
        """Remove namespace URIs from element tags."""
        for elem in self._root.iter():
            if isinstance(elem.tag, str) and '}' in elem.tag:
                elem.tag = elem.tag.split('}', 1)[1]

    def _text_of(self, elem: Optional[ET.Element]) -> str:
        """Get normalized text content from an element."""
        if elem is None:
            return ''
        text = ''.join(elem.itertext())
        text = text.replace('\u00A0', ' ')
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def to_clsf(self, source_path: str = None, **kwargs) -> LexicalSenseFormat:
        """Convert DANTE XML to CLSF."""
        path = source_path or self.xml_path
        if not path or not os.path.exists(path):
            raise FileNotFoundError(f"DANTE XML not found: {path}")

        tree = ET.parse(path)
        self._root = tree.getroot()
        self._strip_namespaces()

        entries = list(self._root.findall('.//Entry'))
        logger.info(f"Processing {len(entries)} DANTE entries...")

        clsf_entries = []
        sense_count = 0

        for entry in entries:
            try:
                cls_entry = self._convert_entry(entry)
                if cls_entry:
                    clsf_entries.append(cls_entry)
                    sense_count += len(cls_entry.senses)
            except Exception as e:
                logger.warning(f"Error converting entry: {e}")
                continue

        logger.info(f"Converted {len(clsf_entries)} entries with {sense_count} senses")

        return LexicalSenseFormat(
            metadata=Metadata(
                name="DANTE Dictionary",
                version="1.0",
                language="en",
                description=f"Converted from DANTE XML ({len(clsf_entries)} entries)",
            ),
            entries=clsf_entries,
        )

    def _convert_entry(self, entry: ET.Element) -> Optional[Entry]:
        """Convert a single DANTE Entry to CLSF Entry."""
        headword = self._extract_headword(entry)
        if not headword:
            return None

        senses = self._extract_senses(entry)
        if not senses:
            senses = [Sense(id='1', definition='')]

        return Entry(
            headword=headword,
            part_of_speech=self._get_primary_pos(entry) or None,
            language='en',
            senses=senses,
            source='DANTE',
        )

    def _extract_headword(self, entry: ET.Element) -> Optional[str]:
        """Extract the main headword from entry."""
        hwd = entry.find('.//HWD')
        if hwd is not None and hwd.text:
            return hwd.text.strip()

        var = entry.find('.//VAR')
        if var is not None and var.text:
            return var.text.strip()

        return None

    def _extract_senses(self, entry: ET.Element) -> List[Sense]:
        """Extract all senses from a DANTE entry."""
        senses = []
        sense_idx = 0

        # Process compound senses (CpdCnt)
        for cpd in entry.findall('.//CpdCnt'):
            cpd_lemma = self._text_of(cpd.find('.//CPD')) or None
            for sense_container in cpd.findall('.//FwkSenCnt'):
                sense = self._convert_sense(sense_container, sense_idx + 1, lemma=cpd_lemma)
                if sense:
                    senses.append(sense)
                    sense_idx += 1

        # Process MWE/Phrase senses
        for ph in entry.findall('.//FwkMWEBlk'):
            for phr_cnt in ph.findall('.//PhrCnt'):
                phr_lemma = self._text_of(phr_cnt.find('.//PHR')) or None
                for sense_container in phr_cnt.findall('.//FwkSenCnt'):
                    sense = self._convert_sense(sense_container, sense_idx + 1, lemma=phr_lemma)
                    if sense:
                        senses.append(sense)
                        sense_idx += 1

        # Process top-level senses
        for sense_container in entry.findall('.//FwkSenCnt'):
            inside_cpd = any(
                sense_container is sc
                for cpd in entry.findall('.//CpdCnt')
                for sc in cpd.findall('.//FwkSenCnt')
            )
            inside_phr = any(
                sense_container is sc
                for ph in entry.findall('.//FwkMWEBlk')
                for cnt in ph.findall('.//PhrCnt')
                for sc in cnt.findall('.//FwkSenCnt')
            )
            if inside_cpd or inside_phr:
                continue

            sense = self._convert_sense(sense_container, sense_idx + 1)
            if sense:
                senses.append(sense)
                sense_idx += 1

        return senses

    def _convert_sense(self, sense_container: ET.Element, sense_num: int,
                       lemma: Optional[str] = None) -> Optional[Sense]:
        """Convert a DANTE sense container to CLSF Sense."""
        definition = self._text_of(sense_container.find('.//MEANING')) or ''

        if not definition and not lemma:
            return None

        # Extract examples
        examples = []
        for ex_cnt in sense_container.findall('.//ExCnt'):
            ex = ex_cnt.find('.//EX')
            if ex is not None:
                ex_text = self._text_of(ex)
                if ex_text:
                    examples.append(Example(languages={"en": ex_text}))

        # Extract usage notes/labels
        usage_parts = []
        for labelgp in sense_container.findall('.//LabelGp'):
            for child in labelgp:
                txt = child.get('label') or self._text_of(child)
                if txt:
                    tag = child.tag.lower() if isinstance(child.tag, str) else ''
                    usage_parts.append(f"[{tag}] {txt}")
        usage_text = " | ".join(usage_parts) if usage_parts else None

        # Extract grammar codes
        grammar_codes = []
        for gram in sense_container.findall('.//GRAM'):
            code = gram.get('code') or self._text_of(gram)
            if code:
                grammar_codes.append(code.strip())

        # Translations: lemma (for compounds/MWEs) + grammar codes
        translations = []
        if lemma:
            translations.append(lemma)
        translations.extend(grammar_codes)

        return Sense(
            id=str(sense_num),
            definition=definition,
            translations=translations if translations else [],
            examples=examples if examples else [],
        )

    def _get_primary_pos(self, entry: ET.Element) -> str:
        """Get the primary part of speech for an entry."""
        for pos in entry.findall('.//POS'):
            code = pos.get('code')
            if code:
                return _DANTE_POS_MAP.get(code.lower(), code)
        return ''

    def supported_formats(self) -> List[str]:
        return ["xml"]

    @property
    def resource_type(self) -> ResourceType:
        return ResourceType.DICTIONARY
