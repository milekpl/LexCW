# Pronunciation Display Fix

## Issue

The IPA pronunciation fields were not displaying correctly in the entry edit form, even though the data was present in the backend and being passed to the JavaScript correctly.

## Root Cause

The JavaScript in `pronunciation-forms.js` was HTML-escaping the IPA Unicode characters, preventing them from being properly displayed in the input fields.

## Solution

Modified the `renderPronunciation` method in `pronunciation-forms.js` to pass the IPA values directly to the HTML without additional HTML escaping.

The IPA values are already properly JSON-encoded by the template using the `tojson` filter, so no additional escaping is needed.

## Files Changed

- `app/static/js/pronunciation-forms.js`: Removed the HTML escaping of pronunciation values.
- `app/templates/entry_form.html`: Ensured proper JSON encoding using the `tojson` filter.

## Testing

- Verified the fix works using a test HTML page.
- Added a unit test to ensure the template is correctly JSON-encoding the Unicode characters.
- Manually verified that pronunciations now display correctly in the entry edit form.

## Additional Notes

When working with Unicode characters (like IPA) in JavaScript, be careful about escaping. In this case:

1. The template correctly converts Unicode to `\uXXXX` escapes using `tojson | safe`.
2. The JavaScript correctly parses these escapes back to Unicode.
3. However, adding HTML escaping in the JavaScript prevented the characters from being displayed correctly.
