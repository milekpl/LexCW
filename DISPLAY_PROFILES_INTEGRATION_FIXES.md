# Display Profiles Integration Fixes

## Issues Identified

1. **Database Tables Missing**
   - Display profile tables not created in development database
   - Causing "Internal server error" when accessing `/display-profiles`

2. **Entry View Not Using CSS Display**
   - Entry view page at `/entries/<id>` uses hardcoded template
   - Should use CSS-based rendering via `/api/display` endpoint

3. **Language Codes in Headword Display**
   - Headword showing as "acceptance test [en] [en]"
   - Language codes should not appear in entry view page

4. **No Entry Preview in Profile Editor**
   - Profile editor needs live preview of how entry will render
   - Should show preview in modal or side panel

## Implementation Plan

### 1. Create Database Tables
Run migration or create tables for DisplayProfile and ProfileElement

### 2. Update Entry View to Use CSS Display
Modify `app/templates/entry_view.html` to:
- Call `/api/display/<entry_id>` to get CSS-rendered HTML
- Fall back to current rendering if no profile configured
- Remove language codes from headword display

### 3. Add Entry Preview to Profile Editor
Update `app/templates/display_profiles.html` and JS to:
- Load a sample entry for preview
- Update preview when profile changes
- Show preview in dedicated panel

### 4. Fix Language Code Display
Update templates to not show language attributes for lexical-unit

## Files to Modify

- `app/templates/entry_view.html` - Use CSS display API
- `app/static/js/display-profiles.js` - Add live preview functionality  
- Database migration or initialization script
