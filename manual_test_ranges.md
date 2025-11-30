# Manual Verification for Range Dropdowns

## API Endpoints (✅ VERIFIED BY TESTS)

All API endpoints return 200 OK with valid data:

```bash
# Start the Flask server
./start-services.sh

# Test API endpoints
curl http://localhost:5000/api/ranges/grammatical-info
curl http://localhost:5000/api/ranges/academic-domain
curl http://localhost:5000/api/ranges/semantic-domain  
curl http://localhost:5000/api/ranges/usage-type
```

All should return JSON with `"success": true` and populated `"data"` object.

## Browser Verification (MANUAL)

To verify dropdowns work in the actual UI:

1. Start services: `./start-services.sh`
2. Navigate to: `http://localhost:5000/entries`
3. Click on an existing entry to edit
4. In the entry form, verify these dropdowns are populated:
   - **Grammatical Info** (Part of Speech) - should have Noun, Verb, etc.
   - **Academic Domain** - should have domain-type values  
   - **Semantic Domain** - should have semantic-domain-ddp4 values
   - **Usage Type** - should have usage-type values

## What Was Fixed

1. **BaseX Query**: Changed from hardcoded filename to collection-based query
2. **API Mappings**: Added `academic-domain → domain-type` in `app/api/ranges.py`
3. **JavaScript**: Extended to initialize ALL `.dynamic-lift-range` elements, not just grammatical-info
4. **Syntax Error**: Fixed "const grammatic selects" → "const dynamicSelects"
5. **Test Data**: Updated to use `domain-type` instead of `academic-domain`

## Files Changed

- `app/services/dictionary_service.py` - BaseX query
- `app/api/ranges.py` - Academic domain mapping
- `app/static/js/entry-form.js` - Initialize all dropdowns  
- `tests/conftest.py` - Test data fixtures
