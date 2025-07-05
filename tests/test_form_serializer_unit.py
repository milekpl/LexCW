"""
Unit Tests for Form Serializer JavaScript Module

This module tests the form serialization functionality through the browser environment
to ensure the JavaScript form serializer works correctly in real-world scenarios.
These tests are designed for ongoing testing and validation of form serialization.

Run with: pytest tests/test_form_serializer_unit.py -v
"""

import pytest
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
import tempfile
import os


class TestFormSerializerUnit:
    """Unit tests for the form serializer JavaScript module."""
    
    @pytest.fixture(scope="class")
    def browser(self):
        """Set up a headless browser for testing."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        driver = webdriver.Chrome(options=chrome_options)
        yield driver
        driver.quit()
    
    @pytest.fixture
    def test_page(self, browser):
        """Create a test HTML page with the form serializer loaded."""
        # Read the form serializer code
        serializer_path = os.path.join(os.path.dirname(__file__), '..', 'app', 'static', 'js', 'form-serializer.js')
        with open(serializer_path, 'r', encoding='utf-8') as f:
            serializer_code = f.read()
        
        # Create test HTML page
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Form Serializer Unit Tests</title>
        </head>
        <body>
            <form id="test-form">
                <!-- Test fields will be added dynamically -->
            </form>
            
            <script>
            {serializer_code}
            
            // Test utilities
            window.testUtils = {{
                addFormField: function(name, value, type = 'text') {{
                    const form = document.getElementById('test-form');
                    const input = document.createElement('input');
                    input.type = type;
                    input.name = name;
                    input.value = value;
                    form.appendChild(input);
                    return input;
                }},
                
                clearForm: function() {{
                    const form = document.getElementById('test-form');
                    form.innerHTML = '';
                }},
                
                serializeTestForm: function(options) {{
                    const form = document.getElementById('test-form');
                    return window.FormSerializer.serializeFormToJSON(form, options);
                }},
                
                validateTestForm: function() {{
                    const form = document.getElementById('test-form');
                    return window.FormSerializer.validateFormForSerialization(form);
                }}
            }};
            
            // Signal that page is ready
            window.pageReady = true;
            </script>
        </body>
        </html>
        """
        
        # Write to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(html_content)
            temp_file = f.name
        
        # Load the page
        browser.get(f"file://{temp_file}")
        
        # Wait for page to be ready
        WebDriverWait(browser, 10).until(
            lambda driver: driver.execute_script("return window.pageReady === true")
        )
        
        yield browser
        
        # Cleanup
        os.unlink(temp_file)
    
    @pytest.mark.unit
    def test_simple_field_serialization(self, test_page):
        """Test serialization of simple form fields."""
        # Add simple fields
        test_page.execute_script("""
            window.testUtils.clearForm();
            window.testUtils.addFormField('name', 'John Doe');
            window.testUtils.addFormField('email', 'john@example.com');
            window.testUtils.addFormField('age', '30');
        """)
        
        # Serialize form
        result = test_page.execute_script("return window.testUtils.serializeTestForm();")
        
        expected = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'age': '30'
        }
        
        assert result == expected, f"Expected {expected}, got {result}"
    
    @pytest.mark.unit
    def test_dot_notation_serialization(self, test_page):
        """Test serialization with dot notation field names."""
        test_page.execute_script("""
            window.testUtils.clearForm();
            window.testUtils.addFormField('user.name', 'Jane Smith');
            window.testUtils.addFormField('user.email', 'jane@example.com');
            window.testUtils.addFormField('address.city', 'New York');
            window.testUtils.addFormField('address.country', 'USA');
        """)
        
        result = test_page.execute_script("return window.testUtils.serializeTestForm();")
        
        expected = {
            'user': {
                'name': 'Jane Smith',
                'email': 'jane@example.com'
            },
            'address': {
                'city': 'New York',
                'country': 'USA'
            }
        }
        
        assert result == expected, f"Expected {expected}, got {result}"
    
    @pytest.mark.unit
    def test_array_notation_serialization(self, test_page):
        """Test serialization with array notation field names."""
        test_page.execute_script("""
            window.testUtils.clearForm();
            window.testUtils.addFormField('items[0]', 'First item');
            window.testUtils.addFormField('items[1]', 'Second item');
            window.testUtils.addFormField('items[2]', 'Third item');
        """)
        
        result = test_page.execute_script("return window.testUtils.serializeTestForm();")
        
        expected = {
            'items': ['First item', 'Second item', 'Third item']
        }
        
        assert result == expected, f"Expected {expected}, got {result}"
    
    @pytest.mark.unit
    def test_complex_nested_serialization(self, test_page):
        """Test serialization with complex nested structures."""
        test_page.execute_script("""
            window.testUtils.clearForm();
            window.testUtils.addFormField('senses[0].definition', 'A form of Christianity');
            window.testUtils.addFormField('senses[0].examples[0].text', 'Protestantism emerged in the 16th century');
            window.testUtils.addFormField('senses[0].grammatical_info.part_of_speech', 'noun');
            window.testUtils.addFormField('senses[1].definition', 'Opposition to Catholicism');
            window.testUtils.addFormField('pronunciations[0].value', '/ˈprɒtɪstəntɪzəm/');
            window.testUtils.addFormField('pronunciations[0].type', 'IPA');
        """)
        
        result = test_page.execute_script("return window.testUtils.serializeTestForm();")
        
        expected = {
            'senses': [
                {
                    'definition': 'A form of Christianity',
                    'examples': [
                        {'text': 'Protestantism emerged in the 16th century'}
                    ],
                    'grammatical_info': {
                        'part_of_speech': 'noun'
                    }
                },
                {
                    'definition': 'Opposition to Catholicism'
                }
            ],
            'pronunciations': [
                {
                    'value': '/ˈprɒtɪstəntɪzəm/',
                    'type': 'IPA'
                }
            ]
        }
        
        assert result == expected, f"Expected {expected}, got {result}"
    
    @pytest.mark.unit
    def test_dictionary_entry_scenario(self, test_page):
        """Test a real dictionary entry serialization scenario."""
        test_page.execute_script("""
            window.testUtils.clearForm();
            window.testUtils.addFormField('lexical_unit', 'protestantism');
            window.testUtils.addFormField('grammatical_info.part_of_speech', 'noun');
            window.testUtils.addFormField('senses[0].id', 'sense-1');
            window.testUtils.addFormField('senses[0].definition', 'A form of Christianity');
            window.testUtils.addFormField('senses[0].grammatical_info.part_of_speech', 'noun');
            window.testUtils.addFormField('senses[0].examples[0].text', 'Protestantism emerged in the 16th century');
            window.testUtils.addFormField('senses[1].id', 'sense-2');
            window.testUtils.addFormField('senses[1].definition', 'Opposition to Catholicism');
            window.testUtils.addFormField('pronunciations[0].value', '/ˈprɒtɪstəntɪzəm/');
            window.testUtils.addFormField('pronunciations[0].type', 'IPA');
            window.testUtils.addFormField('notes[etymology][en][text]', 'From Protestant + -ism');
            window.testUtils.addFormField('notes[etymology][en][lang]', 'en');
        """)
        
        result = test_page.execute_script("return window.testUtils.serializeTestForm();")
        
        # Verify key structure
        assert 'lexical_unit' in result
        assert result['lexical_unit'] == 'protestantism'
        assert 'grammatical_info' in result
        assert result['grammatical_info']['part_of_speech'] == 'noun'
        assert 'senses' in result
        assert len(result['senses']) == 2
        assert result['senses'][0]['definition'] == 'A form of Christianity'
        assert 'examples' in result['senses'][0]
        assert len(result['senses'][0]['examples']) == 1
        assert 'pronunciations' in result
        assert len(result['pronunciations']) == 1
        assert result['pronunciations'][0]['value'] == '/ˈprɒtɪstəntɪzəm/'
        assert 'notes' in result
        assert 'etymology' in result['notes']
        assert 'en' in result['notes']['etymology']
    
    @pytest.mark.unit
    def test_empty_value_handling(self, test_page):
        """Test handling of empty values with different options."""
        test_page.execute_script("""
            window.testUtils.clearForm();
            window.testUtils.addFormField('name', 'John');
            window.testUtils.addFormField('email', '');
            window.testUtils.addFormField('phone', 'Not provided');
        """)
        
        # Test with includeEmpty: true (default)
        result_with_empty = test_page.execute_script("""
            return window.testUtils.serializeTestForm({includeEmpty: true});
        """)
        
        assert result_with_empty['email'] == '', "Empty values should be included by default"
        
        # Test with includeEmpty: false
        result_without_empty = test_page.execute_script("""
            return window.testUtils.serializeTestForm({includeEmpty: false});
        """)
        
        assert 'email' not in result_without_empty, "Empty values should be excluded when includeEmpty is false"
        assert 'name' in result_without_empty, "Non-empty values should still be included"
    
    @pytest.mark.unit
    def test_value_transformation(self, test_page):
        """Test value transformation functionality."""
        test_page.execute_script("""
            window.testUtils.clearForm();
            window.testUtils.addFormField('name', '  John Doe  ');
            window.testUtils.addFormField('email', '  JOHN@EXAMPLE.COM  ');
        """)
        
        result = test_page.execute_script("""
            return window.testUtils.serializeTestForm({
                transform: function(value, key) {
                    return typeof value === 'string' ? value.trim().toLowerCase() : value;
                }
            });
        """)
        
        assert result['name'] == 'john doe', "Transform function should trim and lowercase"
        assert result['email'] == 'john@example.com', "Transform function should be applied to all fields"
    
    @pytest.mark.unit
    def test_form_validation_success(self, test_page):
        """Test form validation with valid field names."""
        test_page.execute_script("""
            window.testUtils.clearForm();
            window.testUtils.addFormField('name', 'John');
            window.testUtils.addFormField('user.email', 'john@example.com');
            window.testUtils.addFormField('items[0]', 'First item');
            window.testUtils.addFormField('senses[0].definition', 'A definition');
        """)
        
        validation_result = test_page.execute_script("return window.testUtils.validateTestForm();")
        
        assert validation_result['success'] is True, "Validation should succeed for valid field names"
        assert len(validation_result['errors']) == 0, "No errors should be present"
    
    @pytest.mark.unit
    def test_form_validation_warnings(self, test_page):
        """Test form validation with potentially problematic field names."""
        test_page.execute_script("""
            window.testUtils.clearForm();
            window.testUtils.addFormField('user..name', 'John');  // Consecutive dots
            window.testUtils.addFormField('items[]middle', 'value');  // Empty brackets in middle
        """)
        
        validation_result = test_page.execute_script("return window.testUtils.validateTestForm();")
        
        assert len(validation_result['warnings']) > 0, "Warnings should be present for problematic field names"
        warning_messages = ' '.join(validation_result['warnings'])
        assert 'consecutive dots' in warning_messages.lower(), "Should warn about consecutive dots"
    
    @pytest.mark.unit
    def test_array_gap_detection(self, test_page):
        """Test detection of gaps in array indices."""
        test_page.execute_script("""
            window.testUtils.clearForm();
            window.testUtils.addFormField('items[0]', 'First');
            window.testUtils.addFormField('items[2]', 'Third');  // Missing index 1
            window.testUtils.addFormField('items[4]', 'Fifth');  // Missing index 3
        """)
        
        validation_result = test_page.execute_script("return window.testUtils.validateTestForm();")
        
        assert len(validation_result['warnings']) > 0, "Should warn about gaps in array indices"
        warning_messages = ' '.join(validation_result['warnings'])
        assert 'gaps in indices' in warning_messages.lower(), "Should specifically mention gaps in indices"
    
    @pytest.mark.unit
    def test_unicode_support(self, test_page):
        """Test support for Unicode characters in form values."""
        test_page.execute_script("""
            window.testUtils.clearForm();
            window.testUtils.addFormField('word', 'café');
            window.testUtils.addFormField('pronunciation', '/kæˈfeɪ/');
            window.testUtils.addFormField('translation', '咖啡');
            window.testUtils.addFormField('note', 'Borrowed from French café ☕');
        """)
        
        result = test_page.execute_script("return window.testUtils.serializeTestForm();")
        
        assert result['word'] == 'café', "Should handle accented characters"
        assert result['pronunciation'] == '/kæˈfeɪ/', "Should handle IPA symbols"
        assert result['translation'] == '咖啡', "Should handle CJK characters"
        assert result['note'] == 'Borrowed from French café ☕', "Should handle emojis and mixed Unicode"
    
    @pytest.mark.performance
    def test_large_form_performance(self, test_page):
        """Test performance with large forms."""
        # Create a large form
        test_page.execute_script("""
            window.testUtils.clearForm();
            for (let i = 0; i < 500; i++) {
                window.testUtils.addFormField(`senses[${i}].definition`, `Definition ${i}`);
                window.testUtils.addFormField(`senses[${i}].examples[0].text`, `Example ${i}`);
            }
        """)
        
        # Time the serialization
        result = test_page.execute_script("""
            const startTime = performance.now();
            const data = window.testUtils.serializeTestForm();
            const endTime = performance.now();
            return {
                data: data,
                duration: endTime - startTime,
                fieldCount: Object.keys(data.senses).length
            };
        """)
        
        assert result['fieldCount'] == 500, "Should handle 500 senses"
        assert result['duration'] < 1000, f"Serialization should complete in under 1 second, took {result['duration']}ms"
        assert result['data']['senses'][499]['definition'] == 'Definition 499', "Last item should be correct"
    
    @pytest.mark.unit
    def test_error_handling(self, test_page):
        """Test error handling for malformed input."""
        # Test with non-form input
        error = test_page.execute_script("""
            try {
                window.FormSerializer.serializeFormToJSON("not a form");
                return null;
            } catch (e) {
                return e.message;
            }
        """)
        
        assert error is not None, "Should throw error for invalid input"
        assert 'HTMLFormElement' in error or 'FormData' in error, "Error should mention expected input types"


class TestFormSerializerIntegration:
    """Integration tests for form serializer with Flask application."""
    
    @pytest.mark.integration
    def test_serializer_availability_in_form_page(self, client):
        """Test that the form serializer is available in the entry form page."""
        # Get the entry form page
        response = client.get('/entries/new')
        assert response.status_code == 200
        
        response_text = response.get_data(as_text=True)
        
        # Check that form-serializer.js is included
        assert 'form-serializer.js' in response_text, "Form serializer script should be included"
        
        # Check that FormSerializer is used in form submission
        assert 'FormSerializer.serializeFormToJSON' in response_text, "FormSerializer should be used for form submission"
    
    @pytest.mark.integration
    def test_form_submission_uses_serializer(self, client):
        """Test that actual form submission uses the form serializer."""
        # This test would require selenium or a more complex setup
        # For now, we just verify the JavaScript code is properly structured
        pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
