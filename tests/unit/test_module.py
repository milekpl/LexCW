"""
Test module for configuring application dependencies.
"""
from __future__ import annotations

from injector import Module, provider, singleton

from app.database.mock_connector import MockDatabaseConnector
from app.services.dictionary_service import DictionaryService


class AppTestModule(Module):
    """
    Test module for configuring application dependencies.
    """
    @provider
    @singleton
    def provide_db_connector(self) -> MockDatabaseConnector:
        """
        Provides a mock database connector for testing.
        """
        return MockDatabaseConnector()

    @provider
    @singleton
    def provide_dictionary_service(self, db_connector: MockDatabaseConnector) -> DictionaryService:
        """
        Provides a dictionary service with a mock connector.
        """
        return DictionaryService(db_connector=db_connector)
