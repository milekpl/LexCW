# Detailed Implementation Plan for Undefined Ranges Support

Based on the specification in `docs/UNDEFINED_RANGES_SPECIFICATION.md`, here's the detailed implementation plan:

## Phase 1: Database Schema and Models

Remember that postgres should be accessed as defined in .env file. Use .venv to run python.

### 1.1 Create Database Migration
**File**: `migrations/add_custom_ranges_tables.py`

```python
"""Add custom ranges tables for undefined SIL Fieldworks ranges."""

from app.models.base import db
import sqlalchemy as sa

def upgrade():
    # Create custom_ranges table
    db.create_table(
        'custom_ranges',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('project_id', sa.Integer, sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('range_type', sa.String(50), nullable=False),  # 'relation' or 'trait'
        sa.Column('range_name', sa.String(255), nullable=False),
        sa.Column('element_id', sa.String(255), nullable=False),
        sa.Column('element_label', sa.Text),
        sa.Column('element_description', sa.Text),
        sa.Column('parent_range', sa.String(255)),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now())
    )
    
    # Create custom_range_values table
    db.create_table(
        'custom_range_values',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('custom_range_id', sa.Integer, sa.ForeignKey('custom_ranges.id'), nullable=False),
        sa.Column('value', sa.String(255), nullable=False),
        sa.Column('label', sa.Text),
        sa.Column('description', sa.Text),
        sa.Column('created_at', sa.DateTime, default=sa.func.now())
    )

def downgrade():
    db.drop_table('custom_range_values')
    db.drop_table('custom_ranges')
```

### 1.2 Create Model Classes
**File**: `app/models/custom_ranges.py`

```python
from app.models.base import db, BaseModel

class CustomRange(BaseModel):
    __tablename__ = 'custom_ranges'
    
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    range_type = db.Column(db.String(50), nullable=False)  # 'relation' or 'trait'
    range_name = db.Column(db.String(255), nullable=False)
    element_id = db.Column(db.String(255), nullable=False)
    element_label = db.Column(db.Text)
    element_description = db.Column(db.Text)
    parent_range = db.Column(db.String(255))
    
    # Relationship
    values = db.relationship('CustomRangeValue', backref='custom_range', lazy=True)

class CustomRangeValue(BaseModel):
    __tablename__ = 'custom_range_values'
    
    custom_range_id = db.Column(db.Integer, db.ForeignKey('custom_ranges.id'), nullable=False)
    value = db.Column(db.String(255), nullable=False)
    label = db.Column(db.Text)
    description = db.Column(db.Text)
```

## Phase 2: LIFT Import Updates

### 2.1 Update LIFT Parser
**File**: `app/services/lift_parser.py`

Add method to detect undefined ranges:

```python
def identify_undefined_ranges(self, lift_xml, ranges_xml, list_xml):
    """Identify relation types and traits not defined in ranges."""
    undefined_relations = set()
    undefined_traits = defaultdict(set)
    
    # Parse LIFT for used relations and traits
    lift_tree = ET.parse(lift_xml)
    relations = set()
    traits = defaultdict(set)
    
    for rel in lift_tree.iter('relation'):
        rel_type = rel.get('type')
        if rel_type:
            relations.add(rel_type)
        for trait in rel:
            if trait.tag == 'trait':
                name = trait.get('name')
                value = trait.get('value')
                if name and value:
                    traits[name].add(value)
    
    # Parse ranges for defined elements
    defined_elements = self._parse_defined_elements(ranges_xml)
    
    # Find undefined
    for rel in relations:
        if rel not in defined_elements:
            undefined_relations.add(rel)
    
    for trait_name, values in traits.items():
        if trait_name not in defined_elements:
            undefined_traits[trait_name] = values
    
    return undefined_relations, undefined_traits
```

### 2.2 Update Import Service
**File**: `app/services/lift_import_service.py`

Add custom range creation:

```python
def create_custom_ranges(self, project_id, undefined_relations, undefined_traits, list_xml):
    """Create custom range entries for undefined elements."""
    from app.models.custom_ranges import CustomRange, CustomRangeValue
    
    # Process relations
    for rel_type in undefined_relations:
        custom_range = CustomRange(
            project_id=project_id,
            range_type='relation',
            range_name='lexical-relation',  # Assume lexical-relation parent
            element_id=rel_type,
            element_label=rel_type,
            element_description=f'Custom relation type: {rel_type}'
        )
        db.session.add(custom_range)
        db.session.flush()  # Get ID
        
        # Add default value
        value = CustomRangeValue(
            custom_range_id=custom_range.id,
            value=rel_type,
            label=rel_type
        )
        db.session.add(value)
    
    # Process traits
    for trait_name, values in undefined_traits.items():
        custom_range = CustomRange(
            project_id=project_id,
            range_type='trait',
            range_name=trait_name,
            element_id=trait_name,
            element_label=trait_name,
            element_description=f'Custom trait: {trait_name}'
        )
        db.session.add(custom_range)
        db.session.flush()
        
        # Add values, try to match from list.xml
        list_values = self._get_list_values(list_xml, trait_name)
        for value in values:
            label = value
            if list_values and value in list_values:
                label = list_values[value].get('label', value)
            
            range_value = CustomRangeValue(
                custom_range_id=custom_range.id,
                value=value,
                label=label
            )
            db.session.add(range_value)
    
    db.session.commit()
```

## Phase 3: Ranges Loading Updates

### 3.1 Update Ranges Service
**File**: `app/services/ranges_service.py`

Modify to merge file and DB ranges:

```python
def get_all_ranges(self, project_id):
    """Get ranges from file and database."""
    file_ranges = self._load_file_ranges()
    custom_ranges = self._load_custom_ranges(project_id)
    
    # Merge ranges
    merged = file_ranges.copy()
    for range_name, elements in custom_ranges.items():
        if range_name not in merged:
            merged[range_name] = []
        merged[range_name].extend(elements)
    
    return merged

def _load_custom_ranges(self, project_id):
    """Load custom ranges from database."""
    from app.models.custom_ranges import CustomRange, CustomRangeValue
    
    custom_ranges = defaultdict(list)
    
    ranges = CustomRange.query.filter_by(project_id=project_id).all()
    for cr in ranges:
        elements = []
        for val in cr.values:
            elements.append({
                'id': val.value,
                'label': val.label or val.value,
                'description': val.description,
                'custom': True,
                'range_id': cr.id
            })
        custom_ranges[cr.range_name].extend(elements)
    
    return custom_ranges
```

## Phase 4: Ranges Editor Updates

### 4.1 Update API
**File**: `app/api/ranges_editor.py`

Add endpoints for custom ranges:

```python
@ranges_editor_bp.route('/custom', methods=['GET'])
def get_custom_ranges():
    project_id = get_current_project_id()
    custom_ranges = CustomRange.query.filter_by(project_id=project_id).all()
    return jsonify([cr.to_dict() for cr in custom_ranges])

@ranges_editor_bp.route('/custom', methods=['POST'])
def create_custom_range():
    data = request.get_json()
    project_id = get_current_project_id()
    
    custom_range = CustomRange(
        project_id=project_id,
        range_type=data['range_type'],
        range_name=data['range_name'],
        element_id=data['element_id'],
        element_label=data.get('element_label'),
        element_description=data.get('element_description')
    )
    
    db.session.add(custom_range)
    db.session.flush()
    
    # Add values
    for val_data in data.get('values', []):
        value = CustomRangeValue(
            custom_range_id=custom_range.id,
            value=val_data['value'],
            label=val_data.get('label'),
            description=val_data.get('description')
        )
        db.session.add(value)
    
    db.session.commit()
    return jsonify(custom_range.to_dict()), 201
```

### 4.2 Update Frontend
**File**: `app/static/js/ranges-editor.js`

Add UI indicators for custom ranges:

```javascript
function loadRanges() {
    $.get('/api/ranges-editor/custom')
        .done(function(customRanges) {
            // Mark custom ranges in UI
            customRanges.forEach(function(cr) {
                $(`.range-element[data-id="${cr.element_id}"]`)
                    .addClass('custom-range')
                    .attr('data-custom-id', cr.id);
            });
        });
}

function saveCustomRange(rangeData) {
    $.post('/api/ranges-editor/custom', JSON.stringify(rangeData))
        .done(function(response) {
            // Update UI with new custom range
            addRangeToUI(response);
        });
}
```

## Phase 5: Export Updates

### 5.1 Update Export Service
**File**: `app/services/lift_export_service.py`

Include custom ranges in export:

```python
def export_ranges_file(self, project_id, output_path):
    """Export ranges file including custom ranges."""
    # Load standard ranges
    standard_ranges = self._load_standard_ranges()
    
    # Load custom ranges
    custom_ranges = self._load_custom_ranges_for_export(project_id)
    
    # Merge
    for range_name, elements in custom_ranges.items():
        if range_name not in standard_ranges:
            standard_ranges[range_name] = []
        standard_ranges[range_name].extend(elements)
    
    # Write XML
    self._write_ranges_xml(standard_ranges, output_path)
```

## Phase 6: Testing

### 6.1 Unit Tests
**File**: `tests/unit/test_custom_ranges.py`

```python
def test_custom_range_creation():
    # Test creating and retrieving custom ranges
    pass

def test_undefined_range_detection():
    # Test identifying undefined ranges in LIFT files
    pass
```

### 6.2 Integration Tests
**File**: `tests/integration/test_custom_ranges_import.py`

```python
def test_import_with_custom_ranges():
    # Test importing LIFT with undefined ranges creates custom entries
    pass
```

## Phase 7: Documentation

### 7.1 Update API Documentation
**File**: `API_DOCUMENTATION.md`

Add sections for custom ranges endpoints.

### 7.2 Update User Guide
**File**: `docs/lift-user-guide.html`

Add section on handling custom ranges from SIL Fieldworks.

## Implementation Order

1. Database migration and models
2. LIFT import updates
3. Ranges loading updates  
4. Ranges editor API updates
5. Frontend updates
6. Export updates
7. Testing
8. Documentation

## Risk Assessment

- **Data Migration**: Ensure existing projects don't lose ranges
- **Performance**: Custom range loading should be cached
- **Compatibility**: Exported files must remain valid LIFT
- **UI Complexity**: Clearly distinguish custom vs standard ranges

## Success Criteria

- SIL Fieldworks LIFT files import without losing trait/relation data
- Ranges editor shows and allows editing of custom ranges
- Exported LIFT files include custom ranges
- No regression in existing functionality