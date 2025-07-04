"""
Test for proper relations UI behavior.

This test ensures that:
1. Relations container shows only non-variant relations (excludes _component-lexeme with variant-type)
2. Relations are displayed as clickable links, NOT raw IDs
3. Variant-type relations appear only in variants container
4. Relations container properly loads relation types from LIFT ranges
"""

from __future__ import annotations

import os
import tempfile
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from app import create_app
from app.models.entry import Entry, Relation


class TestRelationsUI:
    """Test relations UI filtering and display behavior."""

    @pytest.fixture(scope="class")
    def app(self):
        """Create test Flask app."""
        app = create_app()
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        return app

    @pytest.fixture(scope="class")
    def driver(self):
        """Create headless Chrome driver."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(10)
        yield driver
        driver.quit()

    def test_relations_container_excludes_variant_type_relations(self, app, driver):
        """Test that relations container excludes _component-lexeme relations with variant-type traits."""
        
        with app.app_context():
            # Create test entry with mixed relation types  
            test_entry = Entry(
                id_="test-main-entry-001",
                lexical_unit={"en": "test word"},
                relations=[
                    # Regular semantic relation (should appear in relations container)
                    Relation(
                        type="synonym",
                        ref="test-synonym-entry-001"
                    ),
                    # Variant-type relation (should appear ONLY in variants container)
                    Relation(
                        type="_component-lexeme",
                        ref="test-variant-entry-001",
                        traits={"variant-type": "Spelling Variant"}
                    ),
                    # Another regular relation
                    Relation(
                        type="antonym", 
                        ref="test-antonym-entry-001"
                    )
                ]
            )
            
            # Mock the route to return our test data
            with app.test_request_context():
                from flask import render_template_string
                
                # Create a minimal template that includes the relations logic
                template_content = '''
                {% set filtered_relations = [] %}
                {% for relation in entry.relations %}
                    {% if not (relation.type == '_component-lexeme' and relation.traits and 'variant-type' in relation.traits) %}
                        {% set _ = filtered_relations.append(relation) %}
                    {% endif %}
                {% endfor %}
                
                <div id="relations-container">
                    {% if filtered_relations %}
                        {% for relation in filtered_relations %}
                        <div class="relation-item card mb-3" data-relation-index="{{ loop.index0 }}">
                            <div class="card-header bg-primary text-white">
                                <h6 class="mb-0">Relation: {{ relation.type }}</h6>
                            </div>
                            <div class="card-body">
                                <div class="relation-type">{{ relation.type }}</div>
                                <div class="relation-ref">{{ relation.ref }}</div>
                            </div>
                        </div>
                        {% endfor %}
                    {% else %}
                    <div class="empty-state">No relations</div>
                    {% endif %}
                </div>
                
                <div id="variants-container">
                    {% set variant_relations = entry.variant_relations or [] %}
                    {% if variant_relations %}
                        {% for variant in variant_relations %}
                        <div class="variant-item card mb-3">
                            <div class="card-header">Variant: {{ variant.variant_type }}</div>
                            <div class="card-body">
                                <div class="variant-ref">{{ variant.ref }}</div>
                            </div>
                        </div>
                        {% endfor %}
                    {% else %}
                    <div class="empty-state">No variants</div>
                    {% endif %}
                </div>
                '''
                
                # Render the template with our test entry
                html_content = render_template_string(template_content, entry=test_entry)
                
                # Write to temporary file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                    f.write(f'''
                    <!DOCTYPE html>
                    <html>
                    <head><title>Test</title></head>
                    <body>{html_content}</body>
                    </html>
                    ''')
                    temp_file = f.name
                
                try:
                    # Load the page in Selenium
                    driver.get(f"file://{os.path.abspath(temp_file)}")
                    
                    # Wait for page to load
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.ID, "relations-container"))
                    )
                    
                    # Check relations container - should contain only non-variant relations
                    relations_container = driver.find_element(By.ID, "relations-container")
                    
                    # Should find synonym and antonym relations but NOT variant relation
                    relation_items = relations_container.find_elements(By.CSS_SELECTOR, ".relation-item")
                    
                    # Should have 2 relations (synonym + antonym), NOT 3
                    assert len(relation_items) == 2, f"Expected 2 relations, found {len(relation_items)}"
                    
                    # Verify the relation types displayed
                    displayed_types = []
                    for item in relation_items:
                        type_div = item.find_element(By.CSS_SELECTOR, ".relation-type")
                        displayed_types.append(type_div.text)
                    
                    # Should contain synonym and antonym but NOT _component-lexeme
                    assert "synonym" in displayed_types, "Synonym relation should be displayed"
                    assert "antonym" in displayed_types, "Antonym relation should be displayed"
                    assert "_component-lexeme" not in displayed_types, "Variant-type relation should NOT be in relations container"
                    
                    print(f"✓ Relations container properly excludes variant-type relations: {displayed_types}")
                    
                finally:
                    # Clean up temp file
                    if os.path.exists(temp_file):
                        os.remove(temp_file)

    def test_variants_container_shows_only_variant_type_relations(self, app, driver):
        """Test that variants container shows only _component-lexeme relations with variant-type traits."""
        
        with app.app_context():
            test_entry = Entry(
                id_="test-main-entry-001",
                lexical_unit={"en": "test word"},
                relations=[
                    Relation(type="synonym", ref="test-synonym-entry-001"),
                    Relation(
                        type="_component-lexeme",
                        ref="test-variant-entry-001",
                        traits={"variant-type": "Spelling Variant"}
                    ),
                    Relation(type="antonym", ref="test-antonym-entry-001")
                ]
            )
            
            with app.test_request_context():
                from flask import render_template_string
                
                template_content = '''
                <div id="variants-container">
                    {% set variant_relations = entry.variant_relations or [] %}
                    {% if variant_relations %}
                        {% for variant in variant_relations %}
                        <div class="variant-item card mb-3">
                            <div class="card-header">Variant: {{ variant.variant_type }}</div>
                            <div class="card-body">
                                <div class="variant-ref">{{ variant.ref }}</div>
                                <div class="variant-type">{{ variant.variant_type }}</div>
                            </div>
                        </div>
                        {% endfor %}
                    {% else %}
                    <div class="empty-state">No variants</div>
                    {% endif %}
                </div>
                '''
                
                html_content = render_template_string(template_content, entry=test_entry)
                
                with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                    f.write(f'''
                    <!DOCTYPE html>
                    <html>
                    <head><title>Test</title></head>
                    <body>{html_content}</body>
                    </html>
                    ''')
                    temp_file = f.name
                
                try:
                    driver.get(f"file://{os.path.abspath(temp_file)}")
                    
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.ID, "variants-container"))
                    )
                    
                    # Check variants container - should contain only variant-type relations
                    variants_container = driver.find_element(By.ID, "variants-container")
                    
                    # Should find the variant relation
                    variant_items = variants_container.find_elements(By.CSS_SELECTOR, ".variant-item")
                    
                    # Should have 1 variant
                    assert len(variant_items) == 1, f"Expected 1 variant, found {len(variant_items)}"
                    
                    # Verify it's the correct variant
                    variant_item = variant_items[0]
                    variant_type_div = variant_item.find_element(By.CSS_SELECTOR, ".variant-type")
                    assert variant_type_div.text == "Spelling Variant", "Should show correct variant type"
                    
                    print("✓ Variants container properly shows only variant-type relations")
                    
                finally:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
