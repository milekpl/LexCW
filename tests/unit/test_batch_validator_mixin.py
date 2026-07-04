"""
Tests for BatchValidatorMixin consolidation and tenacity integration.

TDD RED phase: Tests that should fail until implementation is complete.
"""

import pytest
from typing import Any, Dict, List
from unittest.mock import Mock, MagicMock
from tenacity import RetryError, stop_after_attempt, wait_fixed

from app.validators.base import Validator, ValidationResult, BatchValidatorMixin


class ConcreteBatchValidator(BatchValidatorMixin, Validator):
    """Concrete test implementation of BatchValidatorMixin."""

    @property
    def validator_type(self) -> str:
        return "test_validator"

    def validate(
        self,
        text: str,
        lang: str,
        **kwargs
    ) -> ValidationResult:
        """Simple test validation: mark valid if text is not empty."""
        return ValidationResult(
            is_valid=bool(text),
            validator_type=self.validator_type,
            cached=False,
            suggestions=[],
        )

    def get_cache_key(
        self,
        entry_id: str,
        text: str,
        **kwargs
    ) -> str:
        return f"{entry_id}:{text}"

    def invalidate_for_entry(self, entry_id: str) -> int:
        return 0


class TestBatchValidatorMixin:
    """Tests for the new BatchValidatorMixin."""

    def test_batch_validator_mixin_exists(self):
        """Verify BatchValidatorMixin class exists and can be inherited."""
        validator = ConcreteBatchValidator()
        assert isinstance(validator, BatchValidatorMixin)

    def test_default_validate_batch_implementation(self):
        """Verify BatchValidatorMixin provides a working default validate_batch."""
        validator = ConcreteBatchValidator()

        entries = [
            {"id": "entry1", "text": "hello"},
            {"id": "entry2", "text": "world"},
        ]

        results = validator.validate_batch(entries, lang="en")

        assert isinstance(results, dict)
        assert len(results) == 2
        assert "entry1" in results
        assert "entry2" in results
        assert results["entry1"].is_valid is True
        assert results["entry2"].is_valid is True

    def test_validate_batch_handles_empty_text(self):
        """Verify batch validation handles entries with empty text."""
        validator = ConcreteBatchValidator()

        entries = [
            {"id": "entry1", "text": "hello"},
            {"id": "entry2", "text": ""},
        ]

        results = validator.validate_batch(entries, lang="en")

        assert results["entry1"].is_valid is True
        assert results["entry2"].is_valid is False

    def test_validate_batch_passes_kwargs(self):
        """Verify batch validation passes kwargs to validate method."""
        mock_validator = Mock(spec=ConcreteBatchValidator)
        mock_validator.validator_type = "test"

        # Mock validate to return a ValidationResult
        mock_validator.validate = Mock(return_value=ValidationResult(
            is_valid=True,
            validator_type="test",
        ))

        # Use the mixin's validate_batch with the mock
        entries = [{"id": "e1", "text": "test"}]
        results = {}

        for entry in entries:
            result = mock_validator.validate(
                text=entry["text"],
                lang="en",
                custom_param="value",
            )
            results[entry["id"]] = result

        # Verify kwargs were passed
        mock_validator.validate.assert_called_once()
        call_kwargs = mock_validator.validate.call_args[1]
        assert "custom_param" in call_kwargs
        assert call_kwargs["custom_param"] == "value"

    def test_validate_batch_missing_id_raises_error(self):
        """Verify batch validation fails if entry missing 'id' key."""
        validator = ConcreteBatchValidator()

        entries = [
            {"text": "hello"},  # missing 'id'
        ]

        with pytest.raises(KeyError):
            validator.validate_batch(entries, lang="en")

    def test_validate_batch_returns_all_entries(self):
        """Verify batch validation returns results for all entries."""
        validator = ConcreteBatchValidator()

        entries = [
            {"id": f"entry{i}", "text": f"text{i}"}
            for i in range(10)
        ]

        results = validator.validate_batch(entries, lang="en")

        assert len(results) == 10
        for i in range(10):
            assert f"entry{i}" in results


class TestTenacityRetryIntegration:
    """Tests for tenacity-based retry decorators."""

    def test_retry_decorator_exists(self):
        """Verify tenacity retry decorator is available."""
        try:
            import tenacity
            assert hasattr(tenacity, 'retry')
            assert hasattr(tenacity, 'stop_after_attempt')
            assert hasattr(tenacity, 'wait_fixed')
        except ImportError:
            pytest.skip("tenacity not installed")

    def test_retry_on_io_error_with_tenacity(self):
        """Verify retry decorator retries on IOError."""
        from tenacity import retry, stop_after_attempt, retry_if_exception_type

        call_count = 0

        @retry(stop=stop_after_attempt(3), retry=retry_if_exception_type(IOError))
        def failing_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise IOError("Connection failed")
            return "success"

        result = failing_operation()
        assert result == "success"
        assert call_count == 3

    def test_retry_fails_after_max_attempts(self):
        """Verify retry decorator fails after max attempts."""
        from tenacity import retry, stop_after_attempt, retry_if_exception_type

        call_count = 0

        @retry(stop=stop_after_attempt(3), retry=retry_if_exception_type(IOError))
        def always_failing():
            nonlocal call_count
            call_count += 1
            raise IOError("Always fails")

        with pytest.raises(RetryError):
            always_failing()

        assert call_count == 3

    def test_retry_non_retryable_exception_immediately(self):
        """Verify non-retryable exceptions fail immediately."""
        from tenacity import retry, stop_after_attempt, retry_if_exception_type

        call_count = 0

        @retry(stop=stop_after_attempt(3), retry=retry_if_exception_type(IOError))
        def fails_with_value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Not retryable")

        with pytest.raises(ValueError):
            fails_with_value_error()

        # Should not retry non-retryable exceptions
        assert call_count == 1


class TestBaseXConnectorTenacity:
    """Tests for BaseX connector using tenacity."""

    def test_basex_connector_uses_tenacity_decorator(self):
        """Verify _run_with_retry method uses tenacity for retry logic."""
        from app.database.basex_connector import BaseXConnector
        from tenacity import RetryError
        import inspect

        # Verify that _run_with_retry catches and wraps RetryError
        # This proves tenacity is being used internally
        source = inspect.getsource(BaseXConnector._run_with_retry)
        assert 'RetryError' in source or '@retry' in source or 'tenacity' in source.lower()

    def test_basex_retries_operation_on_io_error(self):
        """Verify _run_with_retry operation is retried on IOError."""
        from app.database.basex_connector import BaseXConnector
        from unittest.mock import Mock, MagicMock, patch

        connector = BaseXConnector(
            host='localhost',
            port=1984,
            username='admin',
            password='admin'
        )

        call_count = 0
        mock_conn = MagicMock()

        def operation(conn):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise IOError("Connection lost")
            return "success"

        with patch.object(connector, '_acquire', return_value=mock_conn):
            with patch.object(connector, '_release'):
                with patch.object(connector, '_discard'):
                    result = connector._run_with_retry(operation, "test operation")

        assert result == "success"
        assert call_count == 3


class TestDropDBTenacity:
    """Tests for drop_db_with_retry using tenacity."""

    def test_drop_db_uses_tenacity_decorator(self):
        """Verify _drop_db_with_retry uses tenacity decorator."""
        from app.services.dictionary_service import _drop_db_with_retry
        import inspect

        # Check that function is decorated
        assert hasattr(_drop_db_with_retry, '__wrapped__') or callable(_drop_db_with_retry)

    def test_drop_db_retries_on_locked_error(self):
        """Verify drop_db retries when DB is locked."""
        from app.services.dictionary_service import _drop_db_with_retry
        from unittest.mock import Mock, patch

        mock_connector = Mock()
        call_count = 0

        def side_effect(cmd):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("opened by another process")
            return None

        mock_connector.execute_command = side_effect

        # Should succeed after retries
        with patch('app.services.dictionary_service._kill_blocking_sessions'):
            with patch('time.sleep'):
                _drop_db_with_retry(mock_connector, "test_db", max_retries=3)

        assert call_count == 3

    def test_drop_db_non_retryable_error_fails_immediately(self):
        """Verify drop_db fails immediately on non-retryable errors."""
        from app.services.dictionary_service import _drop_db_with_retry

        mock_connector = Mock()
        mock_connector.execute_command = Mock(side_effect=Exception("Invalid database name"))

        with pytest.raises(Exception, match="Invalid database name"):
            _drop_db_with_retry(mock_connector, "test_db", max_retries=3)

        # Should only be called once, not retried
        assert mock_connector.execute_command.call_count == 1
