import pytest
from app.utils.xquery_builder import XQueryBuilder

@pytest.mark.integration
def test_minimal_insert(dict_service_with_db):
    db_name = dict_service_with_db.db_connector.database
    prologue = f'''
    declare namespace lift = "{XQueryBuilder.LIFT_NAMESPACE}";
    declare namespace flex = "{XQueryBuilder.FLEX_NAMESPACE}";
    '''
    entry_selector = "lift:entry[@id=\"complex_entry\"]"
    sense_min = (
        '<sense id="sense_minimal">'
        '<definition><form lang="en"><text>Minimal sense</text></form></definition>'
        '</sense>'
    )
    update_query = f"""{prologue}
    insert node {sense_min} as last into (collection('{db_name}')//{entry_selector})[1]
    """
    result = dict_service_with_db.db_connector.execute_update(update_query)
    print(f"Minimal insert result: {result}")
    # Fetch and print entry XML after update
    entry_xml = dict_service_with_db.db_connector.execute_query(
        f"for $e in collection('{db_name}')//*[local-name()='entry' and @id='complex_entry'] return $e"
    )
    print(f"Entry XML after minimal insert: {entry_xml}")
    assert '<sense id="sense_minimal">' in entry_xml, f"Inserted sense not found in entry XML: {entry_xml}"
