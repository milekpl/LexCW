import pytest


from app.utils.xquery_builder import XQueryBuilder


@pytest.mark.unit
def test_build_entries_by_grammatical_info_query_escapes_grammatical_info() -> None:
    malicious = 'Noun"] | //entry | ["'
    query = XQueryBuilder.build_entries_by_grammatical_info_query(
        grammatical_info=malicious,
        db_name="test_db",
        has_namespace=True,
    )

    # Raw payload should not appear in query unescaped.
    assert malicious not in query

    escaped = XQueryBuilder.escape_xquery_string(malicious)
    assert f'[@value="{escaped}"]' in query


@pytest.mark.unit
def test_build_related_entries_query_escapes_entry_id_and_relation_type() -> None:
    malicious_entry_id = 'word"] | //entry | ["'
    malicious_relation_type = 'synonym"] | //relation | ["'

    query = XQueryBuilder.build_related_entries_query(
        entry_id=malicious_entry_id,
        relation_type=malicious_relation_type,
        db_name="test_db",
        has_namespace=True,
    )

    assert malicious_entry_id not in query
    assert malicious_relation_type not in query

    escaped_entry_id = XQueryBuilder.escape_xquery_string(malicious_entry_id)
    escaped_relation_type = XQueryBuilder.escape_xquery_string(malicious_relation_type)

    assert f'[@id="{escaped_entry_id}"]' in query
    assert f'[@type="{escaped_relation_type}"]' in query


@pytest.mark.unit
def test_build_reverse_related_entries_query_escapes_inputs() -> None:
    malicious_entry_id = 'entry"] | //entry | ["'
    malicious_relation_type = 'synonym"] | //relation | ["'

    query = XQueryBuilder.build_reverse_related_entries_query(
        entry_id=malicious_entry_id,
        relation_type=malicious_relation_type,
        db_name="test_db",
        has_namespace=False,
    )

    assert malicious_entry_id not in query
    assert malicious_relation_type not in query

    escaped_entry_id = XQueryBuilder.escape_xquery_string(malicious_entry_id)
    escaped_relation_type = XQueryBuilder.escape_xquery_string(malicious_relation_type)

    assert f'@ref="{escaped_entry_id}"' in query
    assert f'[@type="{escaped_relation_type}"]' in query
