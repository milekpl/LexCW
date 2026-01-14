"""
Enhanced searchable language field with variant, historical, and custom language support.

This field addresses the user requirement for more flexibility, supporting:
1. Language variants (English UK/US, Spanish Spain/Mexico, etc.)
2. Historical languages (Latin, Ancient Greek, Sanskrit)
3. Constructed languages (Esperanto, Klingon, etc.)
4. Custom language input for specialized lexicographic work

This solves the problem: "English (UK) dictionary to English (US) dictionary is currently impossible"
"""

from __future__ import annotations
from typing import Any, Optional
from wtforms import Field, StringField
from wtforms.widgets import HiddenInput
from markupsafe import Markup
import json

# Enhanced imports for variant support
from app.utils.comprehensive_languages import get_language_by_code, search_languages
from app.utils.language_variants import (
    get_all_enhanced_languages,
    search_enhanced_languages, 
    validate_language_input,
    CustomLanguage
)


class EnhancedLanguageMultiSelectWidget:
    """
    Enhanced widget supporting language variants and custom languages.
    
    Features:
    - Search across all language types (standard, variants, historical, constructed)
    - Custom language creation for specialized work
    - Rich metadata display (type, region, family, notes)
    - Language variant grouping (show en-US, en-GB under English)
    """
    
    def __call__(self, field: 'EnhancedLanguageMultiSelectField', **kwargs: Any) -> Markup:
        """Render the enhanced language selection widget."""
        
        # Get all available languages including variants (with error handling)
        try:
            all_languages = get_all_enhanced_languages()
        except (ImportError, RuntimeError):
            # Fallback for unit tests or when Flask context is not available
            all_languages = [
                {'code': 'en', 'name': 'English', 'family': 'Indo-European', 'region': 'Global', 'type': 'standard'},
                {'code': 'es', 'name': 'Spanish', 'family': 'Indo-European', 'region': 'Global', 'type': 'standard'},
                {'code': 'fr', 'name': 'French', 'family': 'Indo-European', 'region': 'Global', 'type': 'standard'},
                {'code': 'de', 'name': 'German', 'family': 'Indo-European', 'region': 'Europe', 'type': 'standard'},
                {'code': 'zh', 'name': 'Chinese', 'family': 'Sino-Tibetan', 'region': 'East Asia', 'type': 'standard'},
            ]
        
        # Prepare JavaScript data
        js_languages = []
        for lang in all_languages:
            js_lang = {
                'code': lang.get('code', ''),
                'name': lang.get('name', ''),
                'family': lang.get('family', ''),
                'region': lang.get('region', ''),
                'type': lang.get('type', 'standard'),
                'notes': lang.get('notes', ''),
                'searchable': f"{lang.get('name', '')} {lang.get('code', '')} {lang.get('family', '')} {lang.get('region', '')} {lang.get('notes', '')}".lower()
            }
            js_languages.append(js_lang)
        
        # Get current selections
        current_selections = getattr(field, 'data', []) or []
        
        widget_html = f'''
        <div class="enhanced-language-selector" data-field-name="{field.name}">
            <!-- Search Input -->
            <div class="language-search-container">
                <input type="text" 
                       class="language-search-input form-control" 
                       placeholder="Search by name, code, or type 'Custom: MyLanguage' for custom languages..."
                       autocomplete="off"
                       data-field="{field.name}">
                <button type="button" class="language-search-clear btn btn-sm btn-secondary" title="Clear search">
                    ✕
                </button>
            </div>
            
            <!-- Search Results -->
            <div class="language-search-results" style="display: none;">
                <div class="search-results-header">
                    <span class="results-count">Search results</span>
                    <div class="language-type-filter">
                        <label><input type="checkbox" value="standard" checked> Standard</label>
                        <label><input type="checkbox" value="variant" checked> Variants</label>
                        <label><input type="checkbox" value="historical"> Historical</label>
                        <label><input type="checkbox" value="constructed"> Constructed</label>
                        <label><input type="checkbox" value="custom" checked> Custom</label>
                    </div>
                </div>
                <div class="search-results-list"></div>
                <div class="custom-language-creator" style="display: none;">
                    <div class="custom-language-form">
                        <h6>Create Custom Language</h6>
                        <input type="text" class="custom-name-input form-control form-control-sm" placeholder="Language name">
                        <input type="text" class="custom-code-input form-control form-control-sm" placeholder="Code (optional)">
                        <input type="text" class="custom-notes-input form-control form-control-sm" placeholder="Notes (optional)">
                        <button type="button" class="btn btn-sm btn-primary create-custom-btn">Create</button>
                        <button type="button" class="btn btn-sm btn-secondary cancel-custom-btn">Cancel</button>
                    </div>
                </div>
            </div>
            
            <!-- Selected Languages Display -->
            <div class="selected-languages-container">
                <h6>Selected Languages:</h6>
                <div class="selected-languages-list">
                    <!-- Selected languages will be populated here -->
                </div>
            </div>
            
            <!-- Hidden field to store the actual form data -->
            <input type="hidden" name="{field.name}" value="{json.dumps(current_selections)}" class="language-data-field">
        </div>
        
        <style>
        .enhanced-language-selector {{
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 15px;
            background: #fafafa;
        }}
        
        .language-search-container {{
            display: flex;
            gap: 5px;
            margin-bottom: 10px;
        }}
        
        .language-search-input {{
            flex: 1;
        }}
        
        .language-search-results {{
            border: 1px solid #ccc;
            border-radius: 4px;
            background: white;
            max-height: 300px;
            overflow-y: auto;
            margin-bottom: 15px;
        }}
        
        .search-results-header {{
            background: #f8f9fa;
            padding: 8px 12px;
            border-bottom: 1px solid #dee2e6;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .language-type-filter {{
            display: flex;
            gap: 10px;
            font-size: 0.85em;
        }}
        
        .language-type-filter label {{
            display: flex;
            align-items: center;
            gap: 3px;
            margin: 0;
            cursor: pointer;
        }}
        
        .search-result-item {{
            padding: 8px 12px;
            border-bottom: 1px solid #eee;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .search-result-item:hover {{
            background: #e3f2fd;
        }}
        
        .language-main-info {{
            flex: 1;
        }}
        
        .language-name {{
            font-weight: 500;
            color: #2c3e50;
        }}
        
        .language-meta {{
            font-size: 0.85em;
            color: #666;
            margin-top: 2px;
        }}
        
        .language-type-badge {{
            background: #6c757d;
            color: white;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.75em;
            margin-left: 8px;
        }}
        
        .language-type-badge.variant {{ background: #17a2b8; }}
        .language-type-badge.historical {{ background: #6f42c1; }}
        .language-type-badge.constructed {{ background: #fd7e14; }}
        .language-type-badge.custom {{ background: #28a745; }}
        
        .selected-languages-list {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }}
        
        .selected-language-item {{
            background: #e7f3ff;
            border: 1px solid #b3d9ff;
            border-radius: 20px;
            padding: 5px 12px;
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.9em;
        }}
        
        .selected-language-name {{
            font-weight: 500;
        }}
        
        .selected-language-meta {{
            color: #666;
            font-size: 0.8em;
        }}
        
        .remove-language {{
            background: #dc3545;
            color: white;
            border: none;
            border-radius: 50%;
            width: 18px;
            height: 18px;
            font-size: 0.75em;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        
        .custom-language-creator {{
            border-top: 1px solid #dee2e6;
            padding: 12px;
            background: #f8f9fa;
        }}
        
        .custom-language-form {{
            display: flex;
            gap: 8px;
            align-items: end;
            flex-wrap: wrap;
        }}
        
        .custom-language-form input {{
            min-width: 120px;
        }}
        
        .no-results {{
            padding: 20px;
            text-align: center;
            color: #666;
            font-style: italic;
        }}
        </style>
        
        <script>
        // Enhanced language selector JavaScript
        (function() {{
            const allLanguages = {json.dumps(js_languages)};
            const fieldName = '{field.name}';
            let selectedLanguages = {json.dumps(current_selections)};
            
            const container = document.querySelector(`[data-field-name="${{fieldName}}"]`);
            const searchInput = container.querySelector('.language-search-input');
            const searchResults = container.querySelector('.language-search-results');
            const resultsList = container.querySelector('.search-results-list');
            const selectedList = container.querySelector('.selected-languages-list');
            const hiddenField = container.querySelector('.language-data-field');
            const clearBtn = container.querySelector('.language-search-clear');
            const typeFilters = container.querySelectorAll('.language-type-filter input[type="checkbox"]');
            const customCreator = container.querySelector('.custom-language-creator');
            
            // Initialize
            updateSelectedDisplay();
            updateHiddenField();
            
            // Search functionality
            searchInput.addEventListener('input', function() {{
                const query = this.value.trim();
                
                if (!query) {{
                    searchResults.style.display = 'none';
                    return;
                }}
                
                // Check for custom language creation
                if (query.toLowerCase().startsWith('custom:')) {{
                    showCustomCreator(query.replace(/^custom:\\s*/i, ''));
                    return;
                }}
                
                performSearch(query);
            }});
            
            // Clear search
            clearBtn.addEventListener('click', function() {{
                searchInput.value = '';
                searchResults.style.display = 'none';
                customCreator.style.display = 'none';
            }});
            
            // Type filters
            typeFilters.forEach(filter => {{
                filter.addEventListener('change', function() {{
                    if (searchInput.value.trim()) {{
                        performSearch(searchInput.value.trim());
                    }}
                }});
            }});
            
            function performSearch(query) {{
                const activeTypes = Array.from(typeFilters)
                    .filter(f => f.checked)
                    .map(f => f.value);
                
                const results = allLanguages.filter(lang => {{
                    const typeMatch = activeTypes.includes(lang.type || 'standard');
                    const textMatch = lang.searchable.includes(query.toLowerCase());
                    return typeMatch && textMatch;
                }});
                
                displayResults(results, query);
            }}
            
            function displayResults(results, query) {{
                resultsList.innerHTML = '';
                
                if (results.length === 0) {{
                    resultsList.innerHTML = `
                        <div class="no-results">
                            No languages found for "${{query}}"<br>
                            <small>Try typing "Custom: YourLanguageName" to create a custom language</small>
                        </div>`;
                }} else {{
                    results.forEach(lang => {{
                        const item = createResultItem(lang);
                        resultsList.appendChild(item);
                    }});
                }}
                
                container.querySelector('.results-count').textContent = `${{results.length}} result${{results.length === 1 ? '' : 's'}}`;
                searchResults.style.display = 'block';
                customCreator.style.display = 'none';
            }}
            
            function createResultItem(lang) {{
                const item = document.createElement('div');
                item.className = 'search-result-item';
                
                const isSelected = selectedLanguages.some(sel => sel.code === lang.code);
                if (isSelected) {{
                    item.style.opacity = '0.5';
                    item.style.pointerEvents = 'none';
                }}
                
                item.innerHTML = `
                    <div class="language-main-info">
                        <div class="language-name">${{lang.name}} (${{lang.code}})</div>
                        <div class="language-meta">${{lang.family}} • ${{lang.region}}${{lang.notes ? ' • ' + lang.notes : ''}}</div>
                    </div>
                    <span class="language-type-badge ${{lang.type || 'standard'}}">${{(lang.type || 'standard').toUpperCase()}}</span>
                `;
                
                if (!isSelected) {{
                    item.addEventListener('click', function() {{
                        addLanguage(lang);
                    }});
                }}
                
                return item;
            }}
            
            function showCustomCreator(initialName = '') {{
                customCreator.style.display = 'block';
                searchResults.style.display = 'block';
                resultsList.innerHTML = '';
                
                const nameInput = customCreator.querySelector('.custom-name-input');
                const codeInput = customCreator.querySelector('.custom-code-input');
                const notesInput = customCreator.querySelector('.custom-notes-input');
                const createBtn = customCreator.querySelector('.create-custom-btn');
                const cancelBtn = customCreator.querySelector('.cancel-custom-btn');
                
                nameInput.value = initialName;
                codeInput.value = '';
                notesInput.value = '';
                
                createBtn.onclick = function() {{
                    const name = nameInput.value.trim();
                    if (!name) {{
                        alert('Please enter a language name');
                        return;
                    }}
                    
                    const code = codeInput.value.trim() || generateCustomCode(name);
                    const notes = notesInput.value.trim();
                    
                    const customLang = {{
                        code: code,
                        name: name,
                        family: 'Custom',
                        region: 'User-defined',
                        type: 'custom',
                        notes: notes || 'User-defined language'
                    }};
                    
                    addLanguage(customLang);
                    searchInput.value = '';
                    searchResults.style.display = 'none';
                }};
                
                cancelBtn.onclick = function() {{
                    searchInput.value = '';
                    searchResults.style.display = 'none';
                }};
            }}
            
            function generateCustomCode(name) {{
                const words = name.split(' ');
                const firstWord = words[0].replace(/[^a-zA-Z]/g, '');
                return firstWord.substring(0, 3).toLowerCase() || 'cust';
            }}
            
            function addLanguage(lang) {{
                // Check if already selected
                if (selectedLanguages.some(sel => sel.code === lang.code)) {{
                    return;
                }}
                
                selectedLanguages.push(lang);
                updateSelectedDisplay();
                updateHiddenField();
                
                // Hide search results
                searchInput.value = '';
                searchResults.style.display = 'none';
            }}
            
            function removeLanguage(code) {{
                selectedLanguages = selectedLanguages.filter(lang => lang.code !== code);
                updateSelectedDisplay();
                updateHiddenField();
            }}
            
            function updateSelectedDisplay() {{
                selectedList.innerHTML = '';
                
                selectedLanguages.forEach(lang => {{
                    const item = document.createElement('div');
                    item.className = 'selected-language-item';
                    
                    item.innerHTML = `
                        <div>
                            <div class="selected-language-name">${{lang.name}} (${{lang.code}})</div>
                            <div class="selected-language-meta">${{lang.family}} • ${{lang.type || 'standard'}}</div>
                        </div>
                        <button type="button" class="remove-language" title="Remove ${{lang.name}}">×</button>
                    `;
                    
                    item.querySelector('.remove-language').addEventListener('click', function() {{
                        removeLanguage(lang.code);
                    }});
                    
                    selectedList.appendChild(item);
                }});
                
                if (selectedLanguages.length === 0) {{
                    selectedList.innerHTML = '<div style="color: #666; font-style: italic; padding: 10px;">No languages selected</div>';
                }}
            }}
            
            function updateHiddenField() {{
                hiddenField.value = JSON.stringify(selectedLanguages);
            }}
            
            // Hide search results when clicking outside
            document.addEventListener('click', function(e) {{
                if (!container.contains(e.target)) {{
                    searchResults.style.display = 'none';
                }}
            }});
        }})();
        </script>
        '''
        
        return Markup(widget_html)


class EnhancedLanguageMultiSelectField(Field):
    """
    Enhanced multi-select field for comprehensive language selection.
    
    Supports:
    - Standard languages from comprehensive database
    - Language variants (en-US, es-MX, etc.)
    - Historical languages (Latin, Sanskrit, etc.)
    - Constructed languages (Esperanto, Klingon, etc.)
    - Custom user-defined languages
    """
    
    widget = EnhancedLanguageMultiSelectWidget()
    
    def __init__(self, label: Optional[str] = None, validators: Optional[list] = None, **kwargs: Any):
        super().__init__(label, validators, **kwargs)
        self.data: list[dict[str, str]] = []
    
    def process_formdata(self, valuelist: list[str]) -> None:
        """Process form data from the hidden field."""
        if valuelist:
            try:
                import json
                self.data = json.loads(valuelist[0])
            except (ValueError, IndexError, TypeError):
                self.data = []
        else:
            self.data = []
    
    def _value(self) -> str:
        """Return the field value as JSON string."""
        if self.data:
            import json
            return json.dumps(self.data)
        return "[]"
    
    def get_selected_codes(self) -> list[str]:
        """Get list of selected language codes."""
        return [lang.get('code', '') for lang in self.data]
    
    def populate_from_codes(self, codes: list[str]) -> None:
        """Populate field from list of language codes."""
        self.data = []
        for code in codes:
            self.add_language_by_code(code)
    
    def get_selected_languages(self) -> list[dict[str, str]]:
        """Get the currently selected languages."""
        return self.data or []
    
    def set_selected_languages(self, languages: list[dict[str, str]]) -> None:
        """Set the selected languages."""
        self.data = languages or []
    
    def add_language_by_code(self, code: str) -> bool:
        """
        Add a language by code. Supports enhanced languages and variants.
        
        Args:
            code: Language code (e.g., 'en', 'en-US', 'la', 'eo')
            
        Returns:
            True if language was added, False if not found or already present
        """
        # Check if already selected
        if any(lang.get('code') == code for lang in self.data):
            return False
        
        # Try to find in enhanced languages with error handling
        try:
            all_languages = get_all_enhanced_languages()
            for lang in all_languages:
                if lang.get('code') == code:
                    self.data.append(lang)
                    return True
        except (ImportError, RuntimeError):
            # Fall back to basic language set for unit tests
            basic_languages = [
                {'code': 'en', 'name': 'English', 'family': 'Indo-European', 'region': 'Global'},
                {'code': 'es', 'name': 'Spanish', 'family': 'Indo-European', 'region': 'Global'},
                {'code': 'fr', 'name': 'French', 'family': 'Indo-European', 'region': 'Global'},
                {'code': 'de', 'name': 'German', 'family': 'Indo-European', 'region': 'Europe'},
                {'code': 'zh', 'name': 'Chinese', 'family': 'Sino-Tibetan', 'region': 'East Asia'},
                {'code': 'ar', 'name': 'Arabic', 'family': 'Afro-Asiatic', 'region': 'Middle East'},
                {'code': 'pt', 'name': 'Portuguese', 'family': 'Indo-European', 'region': 'Global'},
                {'code': 'ru', 'name': 'Russian', 'family': 'Indo-European', 'region': 'Europe, Asia'},
                {'code': 'ja', 'name': 'Japanese', 'family': 'Japonic', 'region': 'East Asia'},
                {'code': 'ko', 'name': 'Korean', 'family': 'Koreanic', 'region': 'East Asia'},
            ]
            for lang in basic_languages:
                if lang.get('code') == code:
                    self.data.append(lang)
                    return True
        
        # Try fallback to standard search
        try:
            from app.utils.comprehensive_languages import get_language_by_code
            lang = get_language_by_code(code)
            if lang:
                self.data.append(lang)
                return True
        except Exception:
            pass
        
        return False
    
    def validate_custom_language(self, name: str, code: Optional[str] = None) -> Optional[dict[str, str]]:
        """
        Validate and create a custom language entry.
        
        Args:
            name: Language name
            code: Optional language code
            
        Returns:
            Language dictionary if valid, None if invalid
        """
        try:
            custom = CustomLanguage(
                code=code or self._generate_code_from_name(name),
                name=name,
                notes="User-defined language"
            )
            return custom.to_dict()
        except ValueError:
            return None
    
    def _generate_code_from_name(self, name: str) -> str:
        """Generate a code from language name."""
        import re
        words = name.split()
        if words:
            first_word = re.sub(r'[^a-zA-Z]', '', words[0])
            if len(first_word) >= 3:
                return first_word[:3].lower()
            elif len(first_word) >= 2:
                return first_word.lower()
        return "cust"
