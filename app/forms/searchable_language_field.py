"""
Dynamic target language selection component for settings form.

This creates a searchable, expandable interface for selecting multiple
target languages from the comprehensive language database.
"""

from __future__ import annotations

from wtforms import Field, StringField
from wtforms.widgets import HiddenInput
from markupsafe import Markup
import json
from typing import List, Dict, Any, Optional

from app.utils.comprehensive_languages import (
    get_comprehensive_languages, 
    search_languages,
    get_language_by_code
)


class SearchableLanguageMultiSelectWidget:
    """
    Custom widget for searchable multi-select language field.
    
    Renders as a searchable dropdown with dynamic language addition/removal.
    """
    
    def __call__(self, field: 'SearchableLanguageMultiSelectField', **kwargs: Any) -> Markup:
        """Render the searchable multi-select widget."""
        field_id = kwargs.get('id') or field.id
        field_name = field.name
        
        # Get current selected languages
        selected_languages: List[Dict[str, str]] = []
        if field.data:
            if isinstance(field.data, str):
                try:
                    selected_codes = json.loads(field.data)
                    if isinstance(selected_codes, list):
                        for code in selected_codes:
                            if isinstance(code, str):
                                lang = get_language_by_code(code)
                                if lang:
                                    selected_languages.append(lang)
                except (json.JSONDecodeError, ValueError):
                    pass
            elif isinstance(field.data, list):
                for item in field.data:
                    if isinstance(item, str):
                        lang = get_language_by_code(item)
                        if lang:
                            selected_languages.append(lang)
                    elif isinstance(item, dict):
                        selected_languages.append(item)
        
        # Get all available languages for search
        all_languages = get_comprehensive_languages()
        languages_json = json.dumps(all_languages)
        selected_json = json.dumps(selected_languages)
        
        html = f"""
        <div class="searchable-language-selector" data-field-name="{field_name}">
            <!-- Hidden field to store JSON data -->
            <input type="hidden" name="{field_name}" id="{field_id}" value="{field.data or '[]'}" />
            
            <!-- Search input -->
            <div class="language-search-container mb-3">
                <div class="input-group">
                    <input type="text" 
                           class="form-control language-search-input" 
                           placeholder="Search languages (e.g., 'Swahili', 'zh', 'Indo-European', 'Africa')..."
                           data-field-name="{field_name}">
                    <button type="button" class="btn btn-outline-secondary language-search-clear">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="language-search-results" style="display: none;"></div>
            </div>
            
            <!-- Selected languages display -->
            <div class="selected-languages-container">
                <h6>Selected Target Languages ({len(selected_languages)}):</h6>
                <div class="selected-languages-list">
                    <!-- Will be populated by JavaScript -->
                </div>
                <p class="text-muted small mt-2">
                    <i class="fas fa-info-circle"></i>
                    Search by language name, ISO code, family, or region. 
                    Click languages to add them. Use the × button to remove languages.
                </p>
            </div>
        </div>
        
        <script>
        (function() {{
            const allLanguages = {languages_json};
            const fieldName = "{field_name}";
            const container = document.querySelector(`[data-field-name="${{fieldName}}"]`);
            const hiddenInput = container.querySelector('input[type="hidden"]');
            const searchInput = container.querySelector('.language-search-input');
            const clearButton = container.querySelector('.language-search-clear');
            const resultsContainer = container.querySelector('.language-search-results');
            const selectedContainer = container.querySelector('.selected-languages-list');
            
            let selectedLanguages = {selected_json};
            let searchTimeout;
            
            // Initialize display
            updateSelectedLanguagesDisplay();
            updateHiddenInput();
            
            // Search functionality
            searchInput.addEventListener('input', function() {{
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {{
                    performSearch(this.value);
                }}, 300);
            }});
            
            clearButton.addEventListener('click', function() {{
                searchInput.value = '';
                resultsContainer.style.display = 'none';
            }});
            
            function performSearch(query) {{
                if (!query.trim()) {{
                    resultsContainer.style.display = 'none';
                    return;
                }}
                
                const results = searchLanguages(query.trim(), allLanguages);
                displaySearchResults(results.slice(0, 50)); // Limit to 50 results
            }}
            
            function searchLanguages(query, languages) {{
                query = query.toLowerCase();
                return languages.filter(lang => {{
                    const searchText = [
                        lang.name.toLowerCase(),
                        lang.code.toLowerCase(),
                        lang.family.toLowerCase(),
                        lang.region.toLowerCase()
                    ].join(' ');
                    return searchText.includes(query);
                }});
            }}
            
            function displaySearchResults(results) {{
                if (results.length === 0) {{
                    resultsContainer.innerHTML = '<div class="p-2 text-muted">No languages found</div>';
                    resultsContainer.style.display = 'block';
                    return;
                }}
                
                const html = results.map(lang => {{
                    const isSelected = selectedLanguages.some(selected => selected.code === lang.code);
                    const statusClass = isSelected ? 'bg-light text-muted' : 'language-search-result-item';
                    const statusText = isSelected ? ' (already selected)' : '';
                    
                    return `
                        <div class="language-search-result ${{statusClass}}" 
                             data-code="${{lang.code}}" 
                             data-selectable="${{!isSelected}}">
                            <strong>${{lang.name}}</strong> (${{lang.code}})${{statusText}}
                            <br><small class="text-muted">${{lang.family}} • ${{lang.region}}</small>
                        </div>
                    `;
                }}).join('');
                
                resultsContainer.innerHTML = html;
                resultsContainer.style.display = 'block';
                
                // Add click handlers
                resultsContainer.querySelectorAll('.language-search-result-item').forEach(item => {{
                    item.addEventListener('click', function() {{
                        const code = this.dataset.code;
                        const language = allLanguages.find(l => l.code === code);
                        if (language && !selectedLanguages.some(s => s.code === code)) {{
                            addLanguage(language);
                        }}
                    }});
                }});
            }}
            
            function addLanguage(language) {{
                selectedLanguages.push(language);
                updateSelectedLanguagesDisplay();
                updateHiddenInput();
                searchInput.value = '';
                resultsContainer.style.display = 'none';
            }}
            
            function removeLanguage(code) {{
                selectedLanguages = selectedLanguages.filter(lang => lang.code !== code);
                updateSelectedLanguagesDisplay();
                updateHiddenInput();
            }}
            
            function updateSelectedLanguagesDisplay() {{
                const countHeader = container.querySelector('h6');
                countHeader.textContent = `Selected Target Languages (${{selectedLanguages.length}}):`;
                
                if (selectedLanguages.length === 0) {{
                    selectedContainer.innerHTML = '<p class="text-muted">No languages selected yet. Use the search above to add languages.</p>';
                    return;
                }}
                
                const html = selectedLanguages.map(lang => `
                    <div class="selected-language-item">
                        <span class="language-name">${{lang.name}}</span>
                        <span class="language-code">(${{lang.code}})</span>
                        <button type="button" 
                                class="btn btn-sm btn-outline-danger remove-language" 
                                data-code="${{lang.code}}"
                                title="Remove ${{lang.name}}">
                            <i class="fas fa-times"></i>
                        </button>
                        <div class="language-details">
                            <small class="text-muted">${{lang.family}} • ${{lang.region}}</small>
                        </div>
                    </div>
                `).join('');
                
                selectedContainer.innerHTML = html;
                
                // Add remove handlers
                selectedContainer.querySelectorAll('.remove-language').forEach(button => {{
                    button.addEventListener('click', function() {{
                        removeLanguage(this.dataset.code);
                    }});
                }});
            }}
            
            function updateHiddenInput() {{
                const codes = selectedLanguages.map(lang => lang.code);
                hiddenInput.value = JSON.stringify(codes);
            }}
            
            // Hide results when clicking outside
            document.addEventListener('click', function(e) {{
                if (!container.contains(e.target)) {{
                    resultsContainer.style.display = 'none';
                }}
            }});
        }})();
        </script>
        
        <style>
        .searchable-language-selector {{
            position: relative;
        }}
        
        .language-search-results {{
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: white;
            border: 1px solid #ddd;
            border-radius: 0.375rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            max-height: 300px;
            overflow-y: auto;
            z-index: 1050;
        }}
        
        .language-search-result {{
            padding: 8px 12px;
            border-bottom: 1px solid #f0f0f0;
        }}
        
        .language-search-result-item {{
            cursor: pointer;
        }}
        
        .language-search-result-item:hover {{
            background-color: #f8f9fa;
        }}
        
        .selected-language-item {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 8px 12px;
            margin-bottom: 8px;
            background-color: #e7f3ff;
            border: 1px solid #bee5eb;
            border-radius: 0.375rem;
        }}
        
        .selected-language-item .language-name {{
            font-weight: 500;
        }}
        
        .selected-language-item .language-code {{
            color: #6c757d;
            margin-left: 8px;
        }}
        
        .selected-language-item .language-details {{
            flex: 1;
            margin-left: 12px;
        }}
        
        .selected-language-item .remove-language {{
            margin-left: 8px;
        }}
        </style>
        """
        
        return Markup(html)


class SearchableLanguageMultiSelectField(StringField):
    """
    A field for selecting multiple languages with search functionality.
    
    Stores data as JSON array of language codes in a hidden field,
    with a user-friendly search interface for selection.
    """
    
    widget = SearchableLanguageMultiSelectWidget()
    
    def __init__(self, label: Optional[str] = None, validators: Optional[List[Any]] = None, **kwargs: Any):
        super().__init__(label, validators, **kwargs)
        
    def process_formdata(self, valuelist: List[str]) -> None:
        """Process form data from the hidden JSON field."""
        if valuelist:
            try:
                # Data comes as JSON string of language codes
                data = json.loads(valuelist[0]) if valuelist[0] else []
                self.data = json.dumps(data) if isinstance(data, list) else '[]'
            except (json.JSONDecodeError, ValueError, IndexError):
                self.data = '[]'
        else:
            self.data = '[]'
            
    def _value(self) -> str:
        """Return the field value as JSON string."""
        return self.data or '[]'
        
    def populate_from_codes(self, language_codes: List[str]) -> None:
        """Populate field with list of language codes."""
        self.data = json.dumps(language_codes if language_codes else [])
        
    def get_selected_languages(self) -> List[Dict[str, str]]:
        """Get full language objects for selected codes."""
        if not self.data:
            return []
            
        try:
            codes = json.loads(self.data)
            if not isinstance(codes, list):
                return []
        except (json.JSONDecodeError, ValueError):
            return []
            
        languages: List[Dict[str, str]] = []
        for code in codes:
            if isinstance(code, str):
                lang = get_language_by_code(code)
                if lang:
                    languages.append(lang)
        return languages
    
    def get_selected_codes(self) -> List[str]:
        """Get list of selected language codes."""
        if not self.data:
            return []
            
        try:
            codes = json.loads(self.data)
            return codes if isinstance(codes, list) else []
        except (json.JSONDecodeError, ValueError):
            return []
