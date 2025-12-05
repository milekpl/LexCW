# CSS-Based Editor Implementation Subtasks

## 1. Core Services Implementation

### 1.1 Complete CSS Mapping Service
**Files**: `app/services/css_mapping_service.py`
**Subtasks**:
- [ ] Implement `render_entry()` method with full LIFT-to-HTML transformation
- [ ] Add XML parsing and element extraction
- [ ] Implement CSS class application logic
- [ ] Add element ordering based on display profile
- [ ] Implement conditional display logic (hide empty elements)
- [ ] Add error handling and validation

### 1.2 Create LIFT-to-HTML Transformer
**Files**: `app/utils/lift_to_html_transformer.py`
**Subtasks**:
- [ ] Implement XML element traversal
- [ ] Create HTML builder class
- [ ] Add support for all LIFT elements (lexical-unit, pronunciation, sense, etc.)
- [ ] Implement nested element handling
- [ ] Add attribute preservation
- [ ] Create unit tests for transformer

### 1.3 Enhance Display Profile Model
**Files**: `app/models/display_profile.py`
**Subtasks**:
- [ ] Add validation for profile structure
- [ ] Implement element configuration validation
- [ ] Add serialization/deserialization methods
- [ ] Create default profile factory
- [ ] Add profile cloning functionality

## 2. API Implementation

### 2.1 Complete Display API Endpoints
**Files**: `app/api/display.py`
**Subtasks**:
- [ ] Implement `PUT /api/display-profiles/{id}` endpoint
- [ ] Implement `DELETE /api/display-profiles/{id}` endpoint
- [ ] Add preview endpoint `GET /api/entries/{id}/preview`
- [ ] Implement error handling and validation
- [ ] Add authentication/authorization
- [ ] Create API documentation

### 2.2 Add LIFT Schema API
**Files**: `app/api/lift_schema.py`
**Subtasks**:
- [ ] Create endpoint to list all mappable LIFT elements
- [ ] Add element metadata (description, allowed children, etc.)
- [ ] Implement element hierarchy information
- [ ] Add example configurations
- [ ] Create caching mechanism

## 3. Admin Interface

### 3.1 Profile Management UI
**Files**: `app/templates/admin/display_profiles.html`
**Subtasks**:
- [ ] Create profile list view
- [ ] Implement profile creation form
- [ ] Add profile editing interface
- [ ] Create profile deletion functionality
- [ ] Add profile import/export
- [ ] Implement responsive design

### 3.2 Interactive Editor
**Files**: `app/static/js/display_profile_editor.js`
**Subtasks**:
- [ ] Implement drag-and-drop element reordering
- [ ] Create CSS class assignment interface
- [ ] Add element configuration panels
- [ ] Implement live preview functionality
- [ ] Add undo/redo functionality
- [ ] Create save/load profile handlers

### 3.3 Preview System
**Files**: `app/static/js/entry_visualizer.js`
**Subtasks**:
- [ ] Implement entry selection for preview
- [ ] Create preview rendering engine
- [ ] Add style switching functionality
- [ ] Implement performance optimization
- [ ] Add error handling and fallback

## 4. CSS Implementation

### 4.1 Default Stylesheets
**Files**: `app/static/css/dictionary.css`
**Subtasks**:
- [ ] Create base dictionary styling
- [ ] Implement headword styling
- [ ] Add pronunciation formatting
- [ ] Create sense block layout
- [ ] Add grammatical info styling
- [ ] Implement responsive design

### 4.2 Export-Specific Styles
**Files**: `app/static/css/print-export.css`, `app/static/css/kindle-export.css`
**Subtasks**:
- [ ] Create print-optimized styles
- [ ] Implement Kindle-compatible CSS
- [ ] Add page break handling
- [ ] Create font optimization
- [ ] Add cross-reference styling

## 5. Integration

### 5.1 Entry Form Integration
**Files**: `app/templates/entry_form.html`, `app/views.py`
**Subtasks**:
- [ ] Add profile selector to entry forms
- [ ] Implement profile context passing
- [ ] Add preview button/functionality
- [ ] Create style switching UI
- [ ] Add profile management link

### 5.2 Structural Grouping
**Files**: `app/utils/entry_grouping.py`
**Subtasks**:
- [ ] Implement root-based entry identification
- [ ] Create subentry detection logic
- [ ] Add relation-based grouping
- [ ] Implement rendering algorithm
- [ ] Add performance optimization

## 6. Testing

### 6.1 Unit Tests
**Files**: `tests/unit/test_css_mapping_service.py`
**Subtasks**:
- [ ] Test profile CRUD operations
- [ ] Test XML-to-HTML transformation
- [ ] Test element ordering logic
- [ ] Test CSS class application
- [ ] Test error handling

### 6.2 Integration Tests
**Files**: `tests/integration/test_display_api.py`
**Subtasks**:
- [ ] Test API endpoints
- [ ] Test profile management
- [ ] Test entry preview functionality
- [ ] Test error scenarios
- [ ] Test authentication

### 6.3 UI Tests
**Files**: `tests/integration/test_display_editor_ui.py`
**Subtasks**:
- [ ] Test editor interface
- [ ] Test drag-and-drop functionality
- [ ] Test preview system
- [ ] Test responsive design
- [ ] Test accessibility

## 7. Documentation

### 7.1 User Documentation
**Files**: `docs/CSS_EDITOR_USAGE.md`
**Subtasks**:
- [ ] Create user guide for profile management
- [ ] Add tutorial for creating custom styles
- [ ] Document export integration
- [ ] Add troubleshooting section
- [ ] Create examples and templates

### 7.2 Developer Documentation
**Files**: `docs/CSS_EDITOR_DEVELOPMENT.md`
**Subtasks**:
- [ ] Document architecture and components
- [ ] Add API reference
- [ ] Create extension points documentation
- [ ] Add performance considerations
- [ ] Document testing strategy

## Implementation Priority Matrix

| Priority | Component | Estimated Time | Dependencies |
|----------|-----------|----------------|--------------|
| P0 | CSS Mapping Service | 3-5 days | None |
| P0 | Display API Endpoints | 2-3 days | CSS Mapping Service |
| P1 | Admin Interface | 5-7 days | Display API |
| P1 | Default CSS Styles | 2-3 days | None |
| P2 | Entry Integration | 3-4 days | CSS Mapping Service, Admin Interface |
| P2 | Structural Grouping | 4-5 days | CSS Mapping Service |
| P3 | Export Integration | 3-4 days | CSS Mapping Service |
| P3 | Advanced Features | 5-7 days | All core components |

## Risk Mitigation Strategy

### High Risk Areas
1. **XML Transformation Complexity**
   - Start with simple elements, gradually add complexity
   - Create comprehensive unit tests for each element type
   - Implement fallback rendering for unsupported elements

2. **Performance with Large Entries**
   - Implement caching at multiple levels
   - Add incremental rendering capability
   - Create performance monitoring

3. **Cross-Format Compatibility**
   - Create format-specific CSS processors
   - Implement validation for each export format
   - Add format-specific testing

## Quality Assurance Plan

### Testing Strategy
- **Unit Tests**: 90%+ coverage for core services
- **Integration Tests**: End-to-end API and UI testing
- **Performance Tests**: Large entry rendering benchmarks
- **Accessibility Tests**: WCAG compliance verification
- **Cross-Browser Tests**: Chrome, Firefox, Safari compatibility

### Code Quality
- **Type Annotations**: Full type hints throughout
- **Documentation**: Comprehensive docstrings
- **Error Handling**: Graceful degradation
- **Logging**: Comprehensive logging system
- **Code Reviews**: Mandatory peer reviews

## Deployment Plan

### Phase 1: Core Implementation
- Implement CSS Mapping Service
- Complete Display API
- Create basic admin interface
- Add default CSS styles

### Phase 2: Integration
- Connect to entry display system
- Implement structural grouping
- Add export integration

### Phase 3: Polish & Optimization
- Performance tuning
- Advanced features
- Comprehensive testing
- Documentation

### Phase 4: Release
- Beta testing with power users
- Bug fixing
- Final documentation
- Production deployment