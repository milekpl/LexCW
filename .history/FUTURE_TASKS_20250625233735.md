# TODO - Future Tasks

## Fix grammatical info parsing in the LIFT parser

Currently, the grammatical info from sense elements in LIFT XML is not being properly parsed into the Sense objects. This issue is visible in the test_create_entry_with_complex_structure test, where:

```xml
<grammatical-info value="noun"/>
```

Is not correctly being parsed into:

```python
sense.grammatical_info = "noun"
```

The grammatical_info field in the Sense object is coming back as None.

### Steps to fix:

1. Debug the LIFT parser's sense parsing logic in app/parsers/lift_parser.py
2. Update the `_parse_sense` method to correctly extract and set the grammatical_info value
3. Add a dedicated test for grammatical_info parsing
4. Verify compatibility with all existing code that uses this property

## Fix pagination in the search_entries method

Currently, the pagination in search_entries is not working as expected. When limit and offset are provided, all entries are still being returned instead of just the specified page.

### Steps to fix:

1. Debug the BaseX XQuery to ensure that the pagination logic is working correctly
2. Test with different BaseX versions to see if this is a version-specific issue
3. Consider using a different XQuery approach for pagination if the current one isn't working
4. Update the tests to be more strict once pagination is fixed

## Improve XML namespace handling

Several parts of the code are using local-name() to work around namespace issues. This approach works but is not ideal for long-term maintenance.

### Steps to fix:

1. Implement a consistent approach to XML namespace handling
2. Refactor the code to use proper namespace declarations in all XQuery expressions
3. Ensure that namespaces are preserved when entries are added to the database
