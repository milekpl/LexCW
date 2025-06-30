"""
Quick test to verify dashboard mocking works fast
"""
import pytest
from unittest.mock import Mock, patch

def test_mock_only():
    """Test that just mocking is fast."""
    mock_service = Mock()
    mock_service.count_entries.return_value = 150
    mock_service.count_senses_and_examples.return_value = (300, 450)
    
    # Simulate what the dashboard does
    entries = mock_service.count_entries()
    senses, examples = mock_service.count_senses_and_examples()
    
    assert entries == 150
    assert senses == 300
    assert examples == 450

if __name__ == "__main__":
    test_mock_only()
    print("Mock test passed quickly!")
