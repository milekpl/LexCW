import pytest
from app.services.query_builder import DynamicQueryBuilder
from app.models.search_query import SearchQuery, SearchFilter, SortOrder

@pytest.mark.integration
def test_simple_lexical_unit_search():
    """
    Tests that a simple search query with a single keyword searches in lexical-unit forms.
    """
    query = SearchQuery(keywords=["test"])
    builder = DynamicQueryBuilder(dialect="xquery")
    
    generated_query, params = builder.build_query(query)
    
    # Should generate XQuery for BaseX searching in lexical-unit forms
    assert 'for $entry in collection("lift")//entry' in generated_query
    assert '$entry/lexical-unit/form/text[contains(., $keyword1)]' in generated_query
    assert isinstance(params, dict)
    assert params["keyword1"] == "test"

@pytest.mark.integration
def test_sense_definition_search():
    """
    Tests searching within sense definitions.
    """
    query = SearchQuery(filters=[
        SearchFilter(field="sense.definition", operator="contains", value="animal")
    ])
    builder = DynamicQueryBuilder(dialect="xquery")
    
    generated_query, params = builder.build_query(query)
    
    # Should search within sense definitions
    assert '$entry/sense/definition/form/text[contains(., $param1)]' in generated_query
    assert params["param1"] == "animal"

@pytest.mark.integration
def test_grammatical_info_search():
    """
    Tests searching by grammatical information (POS).
    """
    query = SearchQuery(filters=[
        SearchFilter(field="grammatical-info.value", operator="equals", value="noun")
    ])
    builder = DynamicQueryBuilder(dialect="xquery")
    
    generated_query, params = builder.build_query(query)
    
    # Should search within grammatical-info
    assert '$entry/sense/grammatical-info/@value = $param1' in generated_query
    assert params["param1"] == "noun"

@pytest.mark.integration
def test_etymology_search():
    """
    Tests searching within etymology information.
    """
    query = SearchQuery(filters=[
        SearchFilter(field="etymology.source", operator="contains", value="Latin")
    ])
    builder = DynamicQueryBuilder(dialect="xquery")
    
    generated_query, params = builder.build_query(query)
    
    # Should search within etymology
    assert '$entry/etymology/@source[contains(., $param1)]' in generated_query
    assert params["param1"] == "Latin"

@pytest.mark.integration
def test_relation_search():
    """
    Tests searching entries that have specific relations.
    """
    query = SearchQuery(filters=[
        SearchFilter(field="relation.type", operator="equals", value="synonym")
    ])
    builder = DynamicQueryBuilder(dialect="xquery")
    
    generated_query, params = builder.build_query(query)
    
    # Should search within relations
    assert '$entry/relation[@type = $param1]' in generated_query
    assert params["param1"] == "synonym"

@pytest.mark.integration
def test_complex_multi_field_query():
    """
    Tests a complex query combining multiple LIFT elements.
    """
    query = SearchQuery(
        keywords=["run"],
        filters=[
            SearchFilter(field="grammatical-info.value", operator="equals", value="verb"),
            SearchFilter(field="sense.definition", operator="contains", value="move")
        ]
    )
    builder = DynamicQueryBuilder(dialect="xquery")
    
    generated_query, params = builder.build_query(query)
    
    # Should combine all conditions
    assert '$entry/lexical-unit/form/text[contains(., $keyword1)]' in generated_query
    assert '$entry/sense/grammatical-info/@value = $param1' in generated_query
    assert '$entry/sense/definition/form/text[contains(., $param2)]' in generated_query
    assert params["keyword1"] == "run"
    assert params["param1"] == "verb"
    assert params["param2"] == "move"
