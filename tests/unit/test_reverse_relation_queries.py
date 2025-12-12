"""Test reverse relation query functionality."""
import pytest
from app.utils.xquery_builder import XQueryBuilder


def test_build_reverse_related_entries_query_basic():
    """Test building basic reverse relation query."""
    query = XQueryBuilder.build_reverse_related_entries_query(
        entry_id="entry1",
        db_name="test_db",
        has_namespace=True
    )
    
    # Verify query structure
    assert "declare namespace lift" in query
    assert 'collection(\'test_db\')' in query
    assert 'lift:entry' in query
    assert 'lift:relation' in query
    assert '@ref="entry1"' in query
    assert 'return $entry' in query


def test_build_reverse_related_entries_query_with_type():
    """Test building reverse relation query with relation type filter."""
    query = XQueryBuilder.build_reverse_related_entries_query(
        entry_id="entry1",
        db_name="test_db",
        has_namespace=True,
        relation_type="synonym"
    )
    
    # Verify type filter is included
    assert '@type="synonym"' in query
    assert '@ref="entry1"' in query


def test_build_reverse_related_entries_query_without_namespace():
    """Test building reverse relation query without namespaces."""
    query = XQueryBuilder.build_reverse_related_entries_query(
        entry_id="entry1",
        db_name="test_db",
        has_namespace=False
    )
    
    # Verify no namespace declarations
    assert "declare namespace" not in query
    # Verify elements don't have namespace prefix
    assert "lift:entry" not in query
    assert "entry" in query
    assert "relation" in query


def test_build_reverse_related_entries_query_with_pagination():
    """Test building reverse relation query with limit and offset."""
    query = XQueryBuilder.build_reverse_related_entries_query(
        entry_id="entry1",
        db_name="test_db",
        has_namespace=True,
        limit=10,
        offset=5
    )
    
    # Verify pagination
    assert "position() > 5" in query
    assert "[position() <= 10]" in query


if __name__ == "__main__":
    print("Testing reverse relation query builder...")
    test_build_reverse_related_entries_query_basic()
    print("✓ Basic query works")
    
    test_build_reverse_related_entries_query_with_type()
    print("✓ Query with type filter works")
    
    test_build_reverse_related_entries_query_without_namespace()
    print("✓ Query without namespace works")
    
    test_build_reverse_related_entries_query_with_pagination()
    print("✓ Query with pagination works")
    
    print("\nAll tests passed!")
