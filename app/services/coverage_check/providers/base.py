"""
Base class for resource providers.

A ResourceProvider converts an external lexical resource (dictionary,
frequency list, raw text) into CLSF for gap analysis.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional

from app.services.coverage_check.models import LexicalSenseFormat


class ResourceType(Enum):
    DICTIONARY = "dictionary"
    FREQUENCY_LIST = "frequency_list"
    TEXT = "text"


class ResourceProvider(ABC):
    """Abstract base for all resource providers."""

    @abstractmethod
    def to_clsf(self, source_path: str = None, **kwargs) -> LexicalSenseFormat:
        """Convert the resource to CLSF.

        Args:
            source_path: Path to the resource file (may be None for
                         built-in resources like WordNet).
        """

    @abstractmethod
    def supported_formats(self) -> List[str]:
        """List of supported file extensions (e.g. ['.txt', '.csv'])."""

    @property
    @abstractmethod
    def resource_type(self) -> ResourceType:
        """The type of resource this provider handles."""
