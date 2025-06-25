"""
Base exporter for the Dictionary Writing System.
"""

import logging
from typing import List, Optional, Any
from abc import ABC, abstractmethod

from app.models.entry import Entry
from app.services.dictionary_service import DictionaryService


class BaseExporter(ABC):
    """
    Base class for all exporters.
    
    Attributes:
        dictionary_service: The dictionary service to use for retrieving entries.
        logger: Logger for the exporter.
    """
    
    def __init__(self, dictionary_service: DictionaryService):
        """
        Initialize a base exporter.
        
        Args:
            dictionary_service: The dictionary service to use.
        """
        self.dictionary_service = dictionary_service
        self.logger = logging.getLogger(__name__)
    
    @abstractmethod
    def export(self, output_path: str, entries: Optional[List[Entry]] = None, *args: Any, **kwargs: Any) -> str:
        """
        Export entries to the specified format.
        
        Args:
            output_path: Path to save the exported file.
            entries: List of entries to export. If None, all entries will be exported.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
            
        Returns:
            Path to the exported file.
            
        Raises:
            Exception: If the export fails.
        """
        pass
