# TODO - Future Tasks

# TODO - Future Tasks

## ✅ Fix grammatical info parsing in the LIFT parser - COMPLETED

~~Currently, the grammatical info from sense elements in LIFT XML is not being properly parsed into the Sense objects. This issue is visible in the test_create_entry_with_complex_structure test.~~

**FIXED**: The issue was that the LIFT parser was looking for `lift:grammatical-info` with namespace, but the actual XML elements in the database don't have namespace prefixes. Added fallback logic to check for elements both with and without namespace.

The grammatical_info field is now correctly parsed from `<grammatical-info value="noun"/>` into `sense.grammatical_info = "noun"`.

**Technical details:**
- Added helper methods `_find_element_with_fallback()` and `_find_elements_with_fallback()` to handle namespace fallback
- Updated `_parse_sense()` method to use the fallback mechanism
- Added comprehensive tests in `tests/test_grammatical_info_parsing.py` to verify the fix works with and without namespaces

## ✅ Fix web search UI display - COMPLETED  

~~Web search UI was not displaying results, even though the API worked.~~

**FIXED**: The issue was that the JavaScript expected `result.lexical_unit` to be a string, but the API returned it as an object like `{"en": "word"}`. Updated the JavaScript to handle both string and object formats for lexical_unit display.

## Improve XML namespace handling

Several parts of the code are using local-name() to work around namespace issues. This approach works but is not ideal for long-term maintenance.

### Steps to fix:

1. Implement a consistent approach to XML namespace handling
2. Refactor the code to use proper namespace declarations in all XQuery expressions
3. Ensure that namespaces are preserved when entries are added to the database
