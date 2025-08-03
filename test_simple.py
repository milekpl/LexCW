import pytest

@pytest.mark.unit
def test_simple():
    """A simple test."""
    assert 1 + 1 == 2

def test_unmarked():
    """A test without markers."""
    assert 2 + 2 == 4
