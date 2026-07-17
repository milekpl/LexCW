"""
SUBTLEX frequency list provider.

Converts SUBTLEX-format frequency lists (word, LgCount, Cd) to CLSF.
Supports tab-separated and comma-separated formats.
"""
from __future__ import annotations

import csv
import os
from typing import List

from app.services.coverage_check.models import (
    LexicalSenseFormat, Metadata, Entry, Sense,
)
from app.services.coverage_check.providers.base import ResourceProvider, ResourceType


class SubtlexProvider(ResourceProvider):
    """Convert a SUBTLEX frequency list to CLSF.

    Expected columns: word, LgCount (log frequency), Cd (CD ratio).
    The first row may be a header (auto-detected).
    """

    def __init__(self, language: str = "en"):
        self.language = language

    def to_clsf(self, source_path: str = None, **kwargs) -> LexicalSenseFormat:
        if not source_path or not os.path.isfile(source_path):
            raise FileNotFoundError(f"SUBTLEX file not found: {source_path}")

        # Auto-detect delimiter
        delimiter = self._detect_delimiter(source_path)

        entries = []
        with open(source_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter=delimiter)
            for i, row in enumerate(reader):
                if len(row) < 2:
                    continue

                word = row[0].strip()
                if not word:
                    continue

                # Skip header row
                if i == 0 and not word[0].isalpha():
                    continue
                if i == 0 and row[1].strip().lower() in ("lgcount", "lg_count", "frequency", "freq"):
                    continue

                # Parse frequency values
                try:
                    lg_count = float(row[1].strip()) if row[1].strip() else 0.0
                except ValueError:
                    continue

                cd = 0.0
                if len(row) >= 3:
                    try:
                        cd = float(row[2].strip()) if row[2].strip() else 0.0
                    except ValueError:
                        pass

                entry = Entry(
                    headword=word,
                    language=self.language,
                    source="subtlex",
                    senses=[
                        Sense(
                            definition="",
                            semantic_domain="frequency",
                            confidence=lg_count,
                        )
                    ],
                )
                entries.append(entry)

        # Sort by log frequency descending
        entries.sort(key=lambda e: e.senses[0].confidence if e.senses else 0, reverse=True)

        return LexicalSenseFormat(
            metadata=Metadata(
                name=os.path.basename(source_path),
                language=self.language,
                source_url=source_path,
                description=f"SUBTLEX frequency list ({len(entries)} words)",
            ),
            entries=entries,
        )

    def supported_formats(self) -> List[str]:
        return [".txt", ".csv", ".tsv"]

    @property
    def resource_type(self) -> ResourceType:
        return ResourceType.FREQUENCY_LIST

    @staticmethod
    def _detect_delimiter(filepath: str) -> str:
        with open(filepath, "r", encoding="utf-8") as f:
            first_line = f.readline()
        if "\t" in first_line:
            return "\t"
        if ";" in first_line:
            return ";"
        return ","
