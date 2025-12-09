# LIFT Ranges Editor - Implementation Quick Start

**Goal**: Build a complete ranges editor in 20 days using TDD methodology.

---

## Day 1: Service Layer Foundation

### Tasks
1. Create `app/services/ranges_service.py`
2. Implement basic CRUD methods (stubs)
3. Write first unit tests

### Code Template

```python
# app/services/ranges_service.py
"""Service for managing LIFT ranges."""

from __future__ import annotations
import logging
import uuid
from typing import Dict, List, Any, Optional
import xml.etree.ElementTree as ET

from app.database.basex_connector import BaseXConnector
from app.parsers.lift_parser import LIFTRangesParser
from app.utils.exceptions import NotFoundError, ValidationError, DatabaseError


class RangesService:
    """Service for CRUD operations on LIFT ranges."""
    
    def __init__(self, db_connector: BaseXConnector):
        self.db_connector = db_connector
        self.ranges_parser = LIFTRangesParser()
        self.logger = logging.getLogger(__name__)
    
    # --- Range CRUD ---
    
    def get_all_ranges(self) -> Dict[str, Any]:
        """
        Retrieve all ranges from database.
        
        Returns:
            Dict mapping range IDs to range data with structure:
            {
                'range_id': {
                    'id': str,
                    'guid': str,
                    'description': Dict[str, str],  # lang -> text
                    'values': List[Dict]  # hierarchical elements
                }
            }
        """
        db_name = self.db_connector.database
        
        # Query ranges document
        ranges_xml = self.db_connector.execute_query(
            f"collection('{db_name}')//lift-ranges"
        )
        
        if not ranges_xml:
            return {}
        
        # Parse XML to dict
        ranges = self.ranges_parser.parse_string(ranges_xml)
        return ranges
    
    def get_range(self, range_id: str) -> Dict[str, Any]:
        """Get single range by ID."""
        ranges = self.get_all_ranges()
        if range_id not in ranges:
            raise NotFoundError(f"Range '{range_id}' not found")
        return ranges[range_id]
    
    def create_range(self, range_data: Dict[str, Any]) -> str:
        """
        Create new range.
        
        Args:
            range_data: {
                'id': str (required),
                'labels': Dict[str, str],  # lang -> text
                'descriptions': Dict[str, str]  # optional
            }
        
        Returns:
            GUID of created range
        """
        range_id = range_data['id']
        
        # Validate ID uniqueness
        if not self.validate_range_id(range_id):
            raise ValidationError(f"Range ID '{range_id}' already exists")
        
        # Generate GUID
        guid = str(uuid.uuid4())
        
        # Build XML
        labels_xml = self._build_multilingual_xml('label', range_data.get('labels', {}))
        descriptions_xml = self._build_multilingual_xml('description', range_data.get('descriptions', {}))
        
        # Execute XQuery insert
        db_name = self.db_connector.database
        query = f"""
        let $lift-ranges := collection('{db_name}')//lift-ranges
        let $new-range := 
          <range id="{range_id}" guid="{guid}">
            {labels_xml}
            {descriptions_xml}
          </range>
        return insert node $new-range into $lift-ranges
        """
        
        self.db_connector.execute_update(query)
        self.logger.info(f"Created range '{range_id}' with GUID {guid}")
        
        return guid
    
    # --- Validation ---
    
    def validate_range_id(self, range_id: str) -> bool:
        """
        Check if range ID is unique (not already in use).
        
        Returns:
            True if ID is available, False if already exists
        """
        db_name = self.db_connector.database
        query = f"""
        exists(collection('{db_name}')//range[@id='{range_id}'])
        """
        result = self.db_connector.execute_query(query)
        return result.strip().lower() == 'false'
    
    # --- Helper methods ---
    
    def _build_multilingual_xml(self, element_name: str, content: Dict[str, str]) -> str:
        """
        Build multilingual XML structure.
        
        Args:
            element_name: 'label', 'description', or 'abbrev'
            content: Dict mapping language codes to text
        
        Returns:
            XML string like:
            <label>
              <form lang="en"><text>English label</text></form>
              <form lang="pl"><text>Polish label</text></form>
            </label>
        """
        if not content:
            return ''
        
        root = ET.Element(element_name)
        for lang, text in content.items():
            form = ET.SubElement(root, 'form')
            form.set('lang', lang)
            text_elem = ET.SubElement(form, 'text')
            text_elem.text = text
        
        return ET.tostring(root, encoding='unicode')
```

### Unit Test Template

```python
# tests/unit/test_ranges_service.py
"""Unit tests for RangesService."""

import pytest
from unittest.mock import Mock, MagicMock
from app.services.ranges_service import RangesService
from app.utils.exceptions import NotFoundError, ValidationError


class TestRangesService:
    """Test RangesService class."""
    
    @pytest.fixture
    def mock_connector(self):
        """Create mock BaseX connector."""
        connector = Mock()
        connector.database = 'test_db'
        connector.execute_query = Mock()
        connector.execute_update = Mock()
        return connector
    
    @pytest.fixture
    def service(self, mock_connector):
        """Create RangesService with mock connector."""
        return RangesService(mock_connector)
    
    def test_get_all_ranges(self, service, mock_connector):
        """Test retrieving all ranges."""
        # Mock BaseX response
        mock_connector.execute_query.return_value = """
        <lift-ranges>
          <range id="test-range" guid="12345">
            <label><form lang="en"><text>Test Range</text></form></label>
          </range>
        </lift-ranges>
        """
        
        ranges = service.get_all_ranges()
        
        assert 'test-range' in ranges
        assert ranges['test-range']['id'] == 'test-range'
        assert ranges['test-range']['guid'] == '12345'
    
    def test_validate_range_id_unique(self, service, mock_connector):
        """Test range ID uniqueness check."""
        # Mock: ID does not exist
        mock_connector.execute_query.return_value = 'false'
        
        result = service.validate_range_id('new-range')
        
        assert result is True
    
    def test_validate_range_id_duplicate(self, service, mock_connector):
        """Test range ID already exists."""
        # Mock: ID exists
        mock_connector.execute_query.return_value = 'true'
        
        result = service.validate_range_id('existing-range')
        
        assert result is False
    
    def test_create_range_valid(self, service, mock_connector):
        """Test creating a new range."""
        # Mock: ID is unique
        mock_connector.execute_query.return_value = 'false'
        
        range_data = {
            'id': 'custom-range',
            'labels': {'en': 'Custom Range'},
            'descriptions': {'en': 'A custom range for testing'}
        }
        
        guid = service.create_range(range_data)
        
        # Verify GUID generated
        assert guid is not None
        assert len(guid) == 36  # UUID format
        
        # Verify XQuery executed
        mock_connector.execute_update.assert_called_once()
        query = mock_connector.execute_update.call_args[0][0]
        assert 'custom-range' in query
        assert guid in query
    
    def test_create_range_duplicate_id(self, service, mock_connector):
        """Test creating range with duplicate ID raises error."""
        # Mock: ID already exists
        mock_connector.execute_query.return_value = 'true'
        
        range_data = {
            'id': 'existing-range',
            'labels': {'en': 'Existing Range'}
        }
        
        with pytest.raises(ValidationError, match="already exists"):
            service.create_range(range_data)
```

**Run Tests**:
```bash
python -m pytest tests/unit/test_ranges_service.py -v
```

---

## Day 2-3: Complete Service Layer

### Tasks
1. Implement `update_range()`, `delete_range()`
2. Implement element CRUD: `create_range_element()`, `update_range_element()`, `delete_range_element()`
3. Add validation methods
4. Write 20 more unit tests

### Key Methods to Implement

```python
def delete_range(self, range_id: str, migration: Optional[Dict] = None) -> None:
    """
    Delete range with optional data migration.
    
    Args:
        range_id: ID of range to delete
        migration: Optional migration config:
            {
                'operation': 'remove' | 'replace',
                'new_value': str  # Only for 'replace'
            }
    """
    # 1. Check if range exists
    # 2. Find usage in entries
    # 3. If used and no migration, raise ValidationError
    # 4. If migration provided, execute migrate_range_values()
    # 5. Delete range
    pass

def create_range_element(
    self, range_id: str, element_data: Dict[str, Any]
) -> str:
    """
    Create new element in range.
    
    Args:
        element_data: {
            'id': str,
            'parent': Optional[str],
            'labels': Dict[str, str],
            'abbrevs': Optional[Dict[str, str]],
            'descriptions': Optional[Dict[str, str]],
            'traits': Optional[Dict[str, str]]
        }
    
    Returns:
        GUID of created element
    """
    # 1. Validate element ID unique within range
    # 2. Validate parent exists (if specified)
    # 3. Validate no circular reference
    # 4. Generate GUID
    # 5. Build XML and insert
    pass

def validate_parent_reference(
    self, range_id: str, element_id: str, parent_id: str
) -> bool:
    """
    Check if setting parent would create circular reference.
    
    Algorithm:
        1. Start from parent_id
        2. Follow parent chain to root
        3. If element_id appears in chain, it's circular
    
    Returns:
        True if valid, False if circular
    """
    # Get range elements
    # Build parent chain
    # Detect cycle
    pass
```

---

## Day 4-5: API Endpoints

### Create Blueprint

```python
# app/api/ranges_editor.py
"""API endpoints for ranges editor."""

from flask import Blueprint, jsonify, request, current_app
from typing import Union, Tuple, Any

from app.services.ranges_service import RangesService
from app.utils.exceptions import NotFoundError, ValidationError, DatabaseError
from flasgger import swag_from


ranges_editor_bp = Blueprint('ranges_editor', __name__, url_prefix='/api/ranges-editor')


@ranges_editor_bp.route('/', methods=['GET'])
@swag_from({
    'tags': ['Ranges Editor'],
    'summary': 'List all LIFT ranges',
    'responses': {
        200: {
            'description': 'List of ranges',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'data': {'type': 'object'}
                }
            }
        }
    }
})
def list_ranges() -> Union[Tuple[Any, int], Any]:
    """Get all ranges."""
    try:
        service = current_app.injector.get(RangesService)
        ranges = service.get_all_ranges()
        return jsonify({'success': True, 'data': ranges})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@ranges_editor_bp.route('/', methods=['POST'])
@swag_from({
    'tags': ['Ranges Editor'],
    'summary': 'Create new range',
    'parameters': [{
        'in': 'body',
        'name': 'body',
        'required': True,
        'schema': {
            'type': 'object',
            'required': ['id', 'labels'],
            'properties': {
                'id': {'type': 'string'},
                'labels': {'type': 'object'},
                'descriptions': {'type': 'object'}
            }
        }
    }],
    'responses': {
        201: {'description': 'Range created'},
        400: {'description': 'Validation error'},
        500: {'description': 'Server error'}
    }
})
def create_range() -> Union[Tuple[Any, int], Any]:
    """Create new range."""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data or 'id' not in data or 'labels' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: id, labels'
            }), 400
        
        service = current_app.injector.get(RangesService)
        guid = service.create_range(data)
        
        return jsonify({
            'success': True,
            'data': {'guid': guid}
        }), 201
    
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# Add more endpoints...
```

### Register Blueprint

```python
# app/__init__.py (add to create_app function)
from app.api.ranges_editor import ranges_editor_bp

def create_app(config_name='development'):
    # ... existing code ...
    
    # Register ranges editor blueprint
    app.register_blueprint(ranges_editor_bp)
    
    return app
```

### Integration Tests

```python
# tests/integration/test_ranges_api.py
"""Integration tests for ranges editor API."""

import pytest
import json
from app import create_app


@pytest.mark.integration
class TestRangesEditorAPI:
    """Test ranges editor API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app('testing')
        with app.test_client() as client:
            yield client
    
    def test_list_ranges(self, client):
        """Test GET /api/ranges-editor/."""
        response = client.get('/api/ranges-editor/')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'data' in data
    
    def test_create_range_valid(self, client):
        """Test POST /api/ranges-editor/ with valid data."""
        payload = {
            'id': 'test-range',
            'labels': {'en': 'Test Range'},
            'descriptions': {'en': 'A test range'}
        }
        
        response = client.post(
            '/api/ranges-editor/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'guid' in data['data']
    
    def test_create_range_duplicate_id(self, client):
        """Test creating range with duplicate ID."""
        payload = {
            'id': 'grammatical-info',  # Already exists
            'labels': {'en': 'Duplicate'}
        }
        
        response = client.post(
            '/api/ranges-editor/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'already exists' in data['error'].lower()
```

---

## Day 6-8: Usage Analysis & Migration

### Implement Usage Detection

```python
# app/services/ranges_service.py

def find_range_usage(
    self, range_id: str, element_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Find entries using specific range or element.
    
    Returns:
        List of dicts with structure:
        {
            'entry_id': str,
            'headword': str,
            'usage_contexts': [
                {
                    'field': 'grammatical_info',
                    'sense_id': 's1',
                    'value': 'Noun'
                }
            ]
        }
    """
    db_name = self.db_connector.database
    
    # Build XQuery based on range type
    if range_id == 'grammatical-info':
        # Search in grammatical-info elements
        if element_id:
            query = f"""
            for $entry in collection('{db_name}')//entry[
              .//grammatical-info[@value = '{element_id}']
            ]
            return concat(
              $entry/@id, '|',
              $entry/lexical-unit/form[1]/text, '|',
              count($entry//grammatical-info[@value = '{element_id}'])
            )
            """
        else:
            # Find any usage (for range deletion check)
            query = f"""
            for $entry in collection('{db_name}')//entry[
              .//grammatical-info
            ]
            return concat($entry/@id, '|', $entry/lexical-unit/form[1]/text)
            """
    else:
        # Search in traits
        if element_id:
            query = f"""
            for $entry in collection('{db_name}')//entry[
              .//trait[@name = '{range_id}' and @value = '{element_id}']
            ]
            return concat(
              $entry/@id, '|',
              $entry/lexical-unit/form[1]/text, '|',
              count($entry//trait[@name = '{range_id}' and @value = '{element_id}'])
            )
            """
        else:
            query = f"""
            for $entry in collection('{db_name}')//entry[
              .//trait[@name = '{range_id}']
            ]
            return concat($entry/@id, '|', $entry/lexical-unit/form[1]/text)
            """
    
    result = self.db_connector.execute_query(query)
    
    # Parse pipe-delimited results
    usage = []
    for line in result.strip().split('\n'):
        if not line:
            continue
        parts = line.split('|')
        usage.append({
            'entry_id': parts[0],
            'headword': parts[1],
            'count': int(parts[2]) if len(parts) > 2 else 1
        })
    
    return usage


def migrate_range_values(
    self,
    range_id: str,
    old_value: str,
    operation: str,
    new_value: Optional[str] = None,
    dry_run: bool = False
) -> Dict[str, int]:
    """
    Bulk migrate range values in entries.
    
    Args:
        range_id: Range ID
        old_value: Value to replace/remove
        operation: 'replace' or 'remove'
        new_value: New value (required for 'replace')
        dry_run: If True, only count affected entries
    
    Returns:
        {'entries_affected': int, 'fields_updated': int}
    """
    if operation == 'replace' and not new_value:
        raise ValidationError("new_value required for 'replace' operation")
    
    # Find affected entries
    usage = self.find_range_usage(range_id, old_value)
    entries_affected = len(usage)
    
    if dry_run:
        return {
            'entries_affected': entries_affected,
            'fields_updated': 0
        }
    
    # Execute migration
    db_name = self.db_connector.database
    
    if operation == 'replace':
        # Replace operation
        if range_id == 'grammatical-info':
            update_query = f"""
            for $gi in collection('{db_name}')//grammatical-info[@value = '{old_value}']
            return replace value of node $gi/@value with '{new_value}'
            """
        else:
            update_query = f"""
            for $trait in collection('{db_name}')//trait[@name = '{range_id}' and @value = '{old_value}']
            return replace value of node $trait/@value with '{new_value}'
            """
    else:  # operation == 'remove'
        # Delete operation
        if range_id == 'grammatical-info':
            update_query = f"""
            delete node collection('{db_name}')//grammatical-info[@value = '{old_value}']
            """
        else:
            update_query = f"""
            delete node collection('{db_name}')//trait[@name = '{range_id}' and @value = '{old_value}']
            """
    
    self.db_connector.execute_update(update_query)
    self.logger.info(
        f"Migrated {entries_affected} entries: {operation} '{old_value}' "
        + (f"with '{new_value}'" if new_value else "")
    )
    
    return {
        'entries_affected': entries_affected,
        'fields_updated': entries_affected  # Simplified
    }
```

---

## Day 9-16: Frontend Implementation

### HTML Templates

```html
<!-- app/templates/ranges_editor.html -->
{% extends "base.html" %}

{% block title %}LIFT Ranges Editor{% endblock %}

{% block content %}
<div class="container-fluid mt-4">
  <div class="row">
    <div class="col-md-12">
      <h2>LIFT Ranges Editor</h2>
      <p class="text-muted">Manage controlled vocabularies for your dictionary</p>
      
      <div class="card">
        <div class="card-header d-flex justify-content-between align-items-center">
          <span>Ranges</span>
          <button class="btn btn-primary btn-sm" id="btnNewRange">
            <i class="bi bi-plus"></i> New Range
          </button>
        </div>
        <div class="card-body">
          <input type="text" id="searchRanges" class="form-control mb-3" placeholder="Search ranges...">
          
          <table class="table table-hover" id="rangesTable">
            <thead>
              <tr>
                <th>ID</th>
                <th>Label</th>
                <th>Elements</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <!-- Populated by JavaScript -->
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- Create Range Modal -->
<div class="modal fade" id="createRangeModal" tabindex="-1">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title">Create New Range</h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
      </div>
      <div class="modal-body">
        <form id="createRangeForm">
          <div class="mb-3">
            <label for="rangeId" class="form-label">Range ID</label>
            <input type="text" class="form-control" id="rangeId" required>
            <div class="invalid-feedback">ID already exists</div>
          </div>
          
          <div class="mb-3">
            <label class="form-label">Labels</label>
            <div id="labelsContainer">
              <div class="input-group mb-2">
                <select class="form-select" style="max-width: 100px">
                  <option value="en">en</option>
                  <option value="pl">pl</option>
                </select>
                <input type="text" class="form-control" placeholder="Label text" required>
                <button type="button" class="btn btn-outline-danger" onclick="removeLanguage(this)">
                  <i class="bi bi-trash"></i>
                </button>
              </div>
            </div>
            <button type="button" class="btn btn-sm btn-outline-primary" onclick="addLanguage('labels')">
              + Add Language
            </button>
          </div>
          
          <div class="mb-3">
            <label class="form-label">Descriptions (optional)</label>
            <div id="descriptionsContainer">
              <!-- Similar to labels -->
            </div>
          </div>
        </form>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
        <button type="button" class="btn btn-primary" onclick="createRange()">Create</button>
      </div>
    </div>
  </div>
</div>
{% endblock %}

{% block scripts %}
<script src="{{ url_for('static', filename='js/ranges-editor.js') }}"></script>
{% endblock %}
```

### JavaScript

```javascript
// app/static/js/ranges-editor.js
/**
 * Ranges Editor JavaScript
 */

class RangesEditor {
    constructor() {
        this.ranges = {};
        this.init();
    }
    
    async init() {
        await this.loadRanges();
        this.setupEventListeners();
        this.renderTable();
    }
    
    async loadRanges() {
        try {
            const response = await fetch('/api/ranges-editor/');
            const result = await response.json();
            
            if (result.success) {
                this.ranges = result.data;
            } else {
                alert('Error loading ranges: ' + result.error);
            }
        } catch (error) {
            console.error('Failed to load ranges:', error);
            alert('Failed to load ranges');
        }
    }
    
    setupEventListeners() {
        document.getElementById('btnNewRange').addEventListener('click', () => {
            this.showCreateModal();
        });
        
        document.getElementById('searchRanges').addEventListener('input', (e) => {
            this.filterRanges(e.target.value);
        });
    }
    
    renderTable() {
        const tbody = document.querySelector('#rangesTable tbody');
        tbody.innerHTML = '';
        
        for (const [rangeId, range] of Object.entries(this.ranges)) {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${rangeId}</td>
                <td>${this.getLabel(range)}</td>
                <td>${range.values ? range.values.length : 0}</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" onclick="editor.editRange('${rangeId}')">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="editor.deleteRange('${rangeId}')">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        }
    }
    
    getLabel(range) {
        // Get English label or first available
        if (range.description && range.description.en) {
            return range.description.en;
        }
        if (range.description) {
            const firstLang = Object.keys(range.description)[0];
            return range.description[firstLang];
        }
        return '(No label)';
    }
    
    showCreateModal() {
        const modal = new bootstrap.Modal(document.getElementById('createRangeModal'));
        modal.show();
    }
    
    async createRange() {
        // Get form data
        const rangeId = document.getElementById('rangeId').value;
        const labels = this.collectMultilingualData('labels');
        const descriptions = this.collectMultilingualData('descriptions');
        
        // Validate
        if (!rangeId || Object.keys(labels).length === 0) {
            alert('Range ID and at least one label are required');
            return;
        }
        
        // Call API
        try {
            const response = await fetch('/api/ranges-editor/', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    id: rangeId,
                    labels: labels,
                    descriptions: descriptions
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                alert('Range created successfully');
                bootstrap.Modal.getInstance(document.getElementById('createRangeModal')).hide();
                await this.loadRanges();
                this.renderTable();
            } else {
                alert('Error: ' + result.error);
            }
        } catch (error) {
            console.error('Failed to create range:', error);
            alert('Failed to create range');
        }
    }
    
    collectMultilingualData(containerId) {
        const container = document.getElementById(containerId + 'Container');
        const inputs = container.querySelectorAll('.input-group');
        const data = {};
        
        inputs.forEach(group => {
            const lang = group.querySelector('select').value;
            const text = group.querySelector('input[type="text"]').value;
            if (text) {
                data[lang] = text;
            }
        });
        
        return data;
    }
}

// Initialize on page load
let editor;
document.addEventListener('DOMContentLoaded', () => {
    editor = new RangesEditor();
});
```

---

## Day 17-18: Testing & Polish

### E2E Tests with Playwright

```python
# tests/e2e/test_ranges_editor_ui.py
"""End-to-end tests for ranges editor UI."""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
class TestRangesEditorUI:
    """Test ranges editor user interface."""
    
    def test_create_range_via_ui(self, page: Page, live_server):
        """Test creating a range via UI."""
        # Navigate to ranges editor
        page.goto(f"{live_server.url}/ranges-editor")
        
        # Click "New Range" button
        page.click("button#btnNewRange")
        
        # Wait for modal
        expect(page.locator("#createRangeModal")).to_be_visible()
        
        # Fill form
        page.fill("input#rangeId", "test-range-e2e")
        page.fill("input[placeholder='Label text']", "Test Range E2E")
        
        # Submit
        page.click("button:has-text('Create')")
        
        # Verify success
        expect(page.locator("text=Range created successfully")).to_be_visible()
        
        # Verify appears in table
        expect(page.locator("td:has-text('test-range-e2e')")).to_be_visible()
    
    def test_delete_range_with_usage_warning(self, page: Page, live_server):
        """Test deletion warning for range in use."""
        page.goto(f"{live_server.url}/ranges-editor")
        
        # Try to delete grammatical-info (in use)
        page.click("tr:has-text('grammatical-info') button[class*='danger']")
        
        # Expect usage warning modal
        expect(page.locator("text=Used in")).to_be_visible()
        expect(page.locator("text=entries")).to_be_visible()
```

---

## Day 19-20: Integration & Deployment

### Deployment Checklist

```bash
# 1. Run all tests
python -m pytest tests/unit/ -v
python -m pytest tests/integration/ -v
python -m pytest tests/e2e/ -v

# 2. Backup database
./scripts/backup_database.sh

# 3. Deploy to staging
git checkout staging
git merge feature/ranges-editor
git push staging

# 4. UAT on staging
# - Test creating ranges
# - Test deleting ranges with migration
# - Test hierarchical elements
# - Performance test with 1000+ elements

# 5. Deploy to production
git checkout main
git merge feature/ranges-editor
git push production

# 6. Monitor
tail -f logs/application.log
```

---

## Quick Reference: API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/ranges-editor/` | List all ranges |
| POST | `/api/ranges-editor/` | Create range |
| GET | `/api/ranges-editor/{id}` | Get range |
| PUT | `/api/ranges-editor/{id}` | Update range |
| DELETE | `/api/ranges-editor/{id}` | Delete range |
| GET | `/api/ranges-editor/{id}/elements` | List elements |
| POST | `/api/ranges-editor/{id}/elements` | Create element |
| PUT | `/api/ranges-editor/{id}/elements/{eid}` | Update element |
| DELETE | `/api/ranges-editor/{id}/elements/{eid}` | Delete element |
| GET | `/api/ranges-editor/{id}/usage` | Get usage |
| POST | `/api/ranges-editor/{id}/migrate` | Migrate values |

---

## Testing Commands

```bash
# Unit tests only
python -m pytest tests/unit/test_ranges_service.py -v

# Integration tests only
python -m pytest tests/integration/test_ranges_api.py -v

# E2E tests
python -m pytest tests/e2e/test_ranges_editor_ui.py -v

# All ranges tests
python -m pytest tests/ -k "ranges" -v

# With coverage
python -m pytest tests/ -k "ranges" --cov=app.services.ranges_service --cov-report=html
```

---

**Next Steps**: Start with Day 1 tasks and follow TDD methodology (write test first, then implement).
