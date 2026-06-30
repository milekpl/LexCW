"""
CSV parser for dictionary import.

One row per sense; main entry fields can be spread across rows.
Dot notation in headers maps to LIFT levels (e.g. "definition.value").
"""

from __future__ import annotations

import csv
import io
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class CSVRow:
    columns: dict[str, str] = field(default_factory=dict)


@dataclass
class CSVData:
    headers: list[str] = field(default_factory=list)
    rows: list[CSVRow] = field(default_factory=list)


class CSVParser:
    """Parse CSV data into a simple column/row structure.

    The actual conversion to LIFT is handled by ImportConverter.
    """

    def __init__(
        self,
        delimiter: str = ",",
        quotechar: str = '"',
    ):
        self.delimiter = delimiter
        self.quotechar = quotechar

    def parse(self, text: str) -> CSVData:
        reader = csv.DictReader(
            io.StringIO(text),
            delimiter=self.delimiter,
            quotechar=self.quotechar,
        )
        headers = reader.fieldnames or []
        data = CSVData(headers=headers)
        for row_dict in reader:
            clean = {}
            for k, v in row_dict.items():
                if v is not None:
                    clean[k] = v.strip()
            data.rows.append(CSVRow(columns=clean))
        return data
