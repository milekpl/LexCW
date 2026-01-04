#!/usr/bin/env python3
"""
Tests for DictionaryService initialization and parameters.
"""

from __future__ import annotations

import pytest
import inspect
from app.services.dictionary_service import DictionaryService


class TestDictionaryServiceParameters:
    """Test DictionaryService parameter configuration."""

    def test_dictionary_service_no_unused_params(self):
        """DictionaryService should not accept unused backup_manager/backup_scheduler."""
        sig = inspect.signature(DictionaryService.__init__)
        params = list(sig.parameters.keys())

        assert 'backup_manager' not in params, "backup_manager should be removed"
        assert 'backup_scheduler' not in params, "backup_scheduler should be removed"
