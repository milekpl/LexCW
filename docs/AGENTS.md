# AGENTS.md - Development Guidelines for Agentic Coders

## Build/Lint/Test Commands

### Python Testing
- **Single test**: `python -m pytest tests/unit/test_file.py::test_function -v`
- **Unit tests**: `python -m pytest tests/unit/ -v -m unit`
- **Integration tests**: `python -m pytest tests/integration/ -v -m integration`
- **Coverage**: `python -m pytest --cov=app tests/`

### JavaScript Testing
- **All JS tests**: `npm run test:js`
- **Specific module**: `npm run test:lift-serializer`
- **Coverage**: `npm run test:js:coverage`

### Linting/Formatting
- **JS lint**: `npm run lint:js`
- **Python lint**: `flake8 app/`
- **Python format**: `black app/`

## Code Style Guidelines

### Python
- **Style**: PEP 8 compliance, 4-space indentation
- **Type hints**: Required for all function signatures (use Optional for nullable)
- **Docstrings**: Google-style with Args/Returns/Raises sections
- **Imports**: Standard library → Third-party → Local (blank lines between groups)

### JavaScript
- **Style**: ES6+ patterns, JSDoc comments for functions
- **Modules**: Use ES6 import/export, avoid global variables
- **Naming**: camelCase for variables/functions, PascalCase for classes

## Key Conventions

- **Error handling**: Custom ValidationError class, consistent JSON API responses
- **Testing**: Arrange-Act-Assert pattern, descriptive test names with pytest markers
- **Dependencies**: Use injector library for DI, singleton scope for services
- **Logging**: Contextual logging with appropriate levels (DEBUG/INFO/WARNING/ERROR)

## Display Aspect Configuration

The display aspect feature allows controlling how range-based values are rendered in display profiles. 

### Available Display Aspects

- **`abbr`**: Use abbreviations (default behavior)
- **`label`**: Use full labels from ranges
- **`full`**: Use full labels (same as `label` currently)

### Usage Examples

```python
# Set display aspect for a profile element
element.set_display_aspect('label')  # Use full labels
aspect = element.get_display_aspect()  # Returns 'label'

# Set via service
display_profile_service.set_element_display_aspect(
    profile_id=1,
    element_name='relation',
    aspect='label'
)

# Get current aspect
display_aspect_config = display_profile_service.get_element_display_aspect(
    profile_id=1,
    element_name='relation'
)
# Returns: {'aspect': 'label', 'language': None}
```

### Supported Elements

- **relations**: Control how relation types are displayed (e.g., "antonym" vs "ant")
- **grammatical-info**: Control how part-of-speech values are displayed (e.g., "noun" vs "n")
- **variants**: Control how variant types are displayed (e.g., "spelling" vs "spell")
- **traits**: Control how trait values are displayed (e.g., "science" vs "sci")

### Fallback Behavior

When a label mapping is requested but unavailable, the system falls back to:
1. Humanized label (title-case, spaces for hyphens) for relations
2. Original value for other elements
3. Never fails - always provides some display text

### Testing

Run display aspect tests:
```bash
# Unit tests
python -m pytest tests/unit/test_css_display_aspects.py -v

# Integration tests
python -m pytest tests/integration/test_display_aspect_integration.py -v
```