"""
Test JavaScript rendering of pronunciations.

This test ensures that the pronunciation values are correctly rendered in the HTML.
"""

from __future__ import annotations

import pytest
from flask import Flask
from app import create_app
from app.models.entry import Entry
from bs4 import BeautifulSoup
import json
import re


class TestPronunciationJsRendering:
    """Test that pronunciations are correctly rendered in JavaScript."""
    
    @pytest.fixture
    def app(self) -> Flask:
        """Create test app."""
        app = create_app('testing')
        return app
    
    def test_template_json_escaping(self, app: Flask):
        """Test that the template properly JSON-escapes IPA characters."""
        with app.app_context():
            # Sample IPA string with special characters
            ipa_value = "ˈprɒtɪstəntɪzm"
            
            # Create a simple template that uses the tojson filter
            template = """
            <script>
                const value = {{ ipa_value | tojson | safe }};
                document.write('Value: ' + value);
            </script>
            """
            
            # Render the template
            from flask import render_template_string
            rendered = render_template_string(template, ipa_value=ipa_value)
            
            # The rendered template should contain properly escaped Unicode characters
            # Example: \u02c8 for ˈ
            assert '\\u' in rendered
            
            # Check that it doesn't contain the raw IPA characters directly in the script
            # (This would be a problem since we're checking script content)
            script_content = re.search(r'<script>(.*?)</script>', rendered, re.DOTALL).group(1)
            assert ipa_value not in script_content.strip()
    
    def test_js_no_double_escaping(self, app: Flask):
        """Test that our JavaScript doesn't double-escape the already escaped values."""
        with app.app_context():
            # Create a template that simulates how entry_form.html passes data
            # to the PronunciationFormsManager
            template = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>No Double Escaping Test</title>
            </head>
            <body>
                <div id="pronunciation-container"></div>
                
                <script>
                    // Mock PronunciationFormsManager that just outputs the input value
                    class PronunciationFormsManager {
                        constructor(containerId, options) {
                            this.container = document.getElementById(containerId);
                            this.pronunciations = options.pronunciations || [];
                            
                            // Just output the value directly for testing
                            if (this.pronunciations.length > 0) {
                                this.container.innerHTML = '<pre>' + JSON.stringify(this.pronunciations[0].value) + '</pre>';
                            }
                        }
                    }
                    
                    // Initialize with test data
                    const pronunciations = [];
                    pronunciations.push({
                        type: {{ writing_system | tojson | safe }},
                        value: {{ ipa_value | tojson | safe }},
                        audio_file: "",
                        is_default: true
                    });
                    
                    // Create the manager
                    window.pronunciationFormsManager = new PronunciationFormsManager('pronunciation-container', {
                        pronunciations: pronunciations
                    });
                </script>
            </body>
            </html>
            """
            
            # Render the template with our test data
            from flask import render_template_string
            rendered = render_template_string(
                template, 
                writing_system="seh-fonipa",
                ipa_value="ˈprɒtɪstəntɪzm"
            )
            
            # Parse the HTML
            soup = BeautifulSoup(rendered, 'html.parser')
            
            # Find the pre tag that contains our output
            pre_tag = soup.find('pre')
            assert pre_tag is not None
            
            # Parse the JSON string to get the actual value
            value_json = pre_tag.string
            value = json.loads(value_json)
            
            # It should match our original input
            assert value == "ˈprɒtɪstəntɪzm"
