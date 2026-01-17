# Lucene Corpus Search Implementation Plan

**Date:** 2026-01-17
**Based on:** `docs/plans/2026-01-17-corpus-search-integration-design.md`

## Step 1: Create Corpus Search API Endpoint

**File:** `app/api/corpus_search.py`

### Implementation Details:

```python
from flask import Blueprint, jsonify, request, current_app

corpus_search_bp = Blueprint('corpus_search', __name__)

@corpus_search_bp.route('/search', methods=['GET'])
def search_corpus():
    """
    Search corpus for KWIC concordance results.
    """
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({
            'success': False,
            'error': 'Missing required parameter: q'
        }), 400

    limit = min(int(request.args.get('limit', 500)), 2000)
    context = min(int(request.args.get('context', 8)), 15)

    try:
        total, hits = current_app.lucene_corpus_client.concordance(
            query=query,
            limit=limit,
            context_size=context
        )

        results = [
            {
                'left': hit.left,
                'match': hit.match,
                'right': hit.right,
                'sentence_id': hit.sentence_id
            }
            for hit in hits
        ]

        return jsonify({
            'success': True,
            'query': query,
            'total': total,
            'results': results
        })

    except Exception as e:
        current_app.logger.error(f"Corpus search failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

### Integration in `corpus_routes.py`:

Add at the top of the file:
```python
from app.api.corpus_search import corpus_search_bp
```

Register the blueprint:
```python
def register_corpus_routes(app):
    app.register_blueprint(corpus_search_bp, url_prefix='/api/corpus')
```

## Step 2: Create JavaScript Module

**File:** `app/static/js/corpus-search.js`

### Module Structure:

```javascript
// app/static/js/corpus-search.js

class CorpusSearch {
    constructor(options = {}) {
        this.targetField = null;  // 'example' or 'definition'
        this.targetIndex = null;  // sense index
        this.headword = null;
        this.results = [];
        this.defaultLimit = 500;
        this.defaultContext = 8;
    }

    open(targetField, targetIndex, headword) { }
    close() { }
    search(query) { }
    insertResult(result) { }
    copyResult(result) { }
}

CorpusSearch.getInstance = function() { };
```

### Key Methods:

```javascript
async search(query) {
    const limit = this.defaultLimit;
    const context = this.defaultContext;

    const response = await fetch(
        `/api/corpus/search?q=${encodeURIComponent(query)}&limit=${limit}&context=${context}`
    );

    const data = await response.json();

    if (!data.success) {
        throw new Error(data.error || 'Search failed');
    }

    this.results = data.results;
    return data;
}

insertResult(result) {
    // Construct full sentence from KWIC parts
    const sentence = `${result.left} ${result.match} ${result.right}`;

    if (this.targetField === 'example') {
        // Find the example container and add new example
        const senseIndex = this.targetIndex;
        const exampleContainer = document.querySelector(
            `[data-sense-index="${senseIndex}"] .examples-container`
        );
        // Trigger add example with pre-filled text
    }
}

copyResult(result) {
    const sentence = `${result.left} ${result.match} ${result.right}`;
    navigator.clipboard.writeText(sentence.trim());
    // Show toast notification
}
```

## Step 3: Create CSS Styles

**File:** `app/static/css/corpus-search.css`

### Styles:

```css
.corpus-search-modal .modal-dialog {
    max-width: 800px;
}

.corpus-search-results {
    max-height: 60vh;
    overflow-y: auto;
    scroll-behavior: smooth;
}

.corpus-result {
    padding: 12px 16px;
    border-bottom: 1px solid #e0e0e0;
    cursor: pointer;
    transition: background-color 0.2s;
}

.corpus-result:hover {
    background-color: #f8f9fa;
}

.corpus-kwic {
    font-family: 'Roboto Mono', monospace;
    font-size: 14px;
    line-height: 1.6;
}

.corpus-kwic em {
    font-style: normal;
    background-color: #fff3cd;
    font-weight: 600;
    padding: 0 2px;
}

.corpus-result-actions {
    margin-top: 8px;
    display: flex;
    gap: 8px;
}

.corpus-search-loading {
    text-align: center;
    padding: 40px;
    color: #6c757d;
}

.corpus-error {
    text-align: center;
    padding: 40px;
    color: #dc3545;
}
```

## Step 4: Create Modal Template

**File:** `app/templates/corpus_search_modal.html`

### Template:

```html
<!-- Corpus Search Modal -->
<div class="modal fade corpus-search-modal" id="corpusSearchModal"
     tabindex="-1" aria-labelledby="corpusSearchModalLabel" aria-hidden="true">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title" id="corpusSearchModalLabel">
                    <i class="fas fa-search"></i> Search Corpus Examples
                </h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"
                        aria-label="Close"></button>
            </div>
            <div class="modal-body">
                <!-- Search Input -->
                <div class="input-group mb-3">
                    <span class="input-group-text">
                        <i class="fas fa-search"></i>
                    </span>
                    <input type="text" class="form-control" id="corpusSearchInput"
                           placeholder="Search corpus for examples...">
                    <button class="btn btn-primary" type="button" id="corpusSearchBtn">
                        Search
                    </button>
                </div>

                <!-- Results Info -->
                <div id="corpusResultsInfo" class="text-muted mb-2" style="display: none;">
                    <small>Found <span id="corpusResultCount">0</span> examples</small>
                </div>

                <!-- Results Container -->
                <div id="corpusSearchResults" class="corpus-search-results">
                    <div class="text-center text-muted py-5">
                        <i class="fas fa-search fa-3x mb-3"></i>
                        <p>Enter a search term to find corpus examples</p>
                    </div>
                </div>

                <!-- Loading State -->
                <div id="corpusSearchLoading" class="corpus-search-loading" style="display: none;">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <p class="mt-2">Searching corpus...</p>
                </div>

                <!-- Error State -->
                <div id="corpusSearchError" class="corpus-error" style="display: none;">
                    <i class="fas fa-exclamation-triangle fa-2x"></i>
                    <p class="mt-2" id="corpusErrorMessage"></p>
                    <button class="btn btn-outline-primary mt-2" id="corpusRetryBtn">
                        Try Again
                    </button>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                    Cancel
                </button>
            </div>
        </div>
    </div>
</div>
```

## Step 5: Add Buttons to Entry Form

**Location:** `app/templates/entry_form.html`

### In Examples Section (around line 644):

```html
<div class="examples-section mt-4">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <h6><i class="fas fa-quote-left"></i> Examples</h6>
        <div class="d-flex gap-2">
            <button type="button" class="btn btn-sm btn-outline-primary search-corpus-btn"
                    data-sense-index="INDEX">
                <i class="fas fa-search"></i> Search Corpus
            </button>
            <button type="button" class="btn btn-sm btn-outline-primary add-example-btn"
                    data-sense-index="INDEX">
                <i class="fas fa-plus"></i> Add Example
            </button>
        </div>
    </div>
    <!-- ... existing examples container ... -->
</div>
```

### In Definition Area (around line 470):

```html
<div class="mb-3">
    <label class="form-label">Definition <span class="text-danger">*</span></label>
    <div class="multilingual-forms definition-forms">
        <!-- ... existing definition forms ... -->
    </div>
    <div class="mt-2 d-flex gap-2">
        <button type="button" class="btn btn-sm btn-outline-primary add-definition-language-btn"
                data-sense-index="INDEX"
                title="Add another language">
            <i class="fas fa-plus"></i> Add Language
        </button>
        <button type="button" class="btn btn-sm btn-outline-secondary search-corpus-btn"
                data-sense-index="INDEX" data-field="definition"
                title="Search corpus for usage examples">
            <i class="fas fa-search"></i> Search Corpus
        </button>
    </div>
</div>
```

### Include Modal in Template (around line 957):

```html
{% include 'corpus_search_modal.html' %}
```

### Include JavaScript (around line 1036):

```html
<!-- Corpus Search -->
<script defer src="{{ url_for('static', filename='js/corpus-search.js') }}"></script>
<script>
document.addEventListener('DOMContentLoaded', function() {
    if (typeof CorpusSearch !== 'undefined') {
        window.corpusSearch = CorpusSearch.getInstance();
    }
});
</script>
```

## Step 6: Register Endpoint

**File:** `app/routes/corpus_routes.py`

Add at the end of the file:

```python
def register_corpus_search_routes(app):
    """Register corpus search API routes."""
    from app.api.corpus_search import corpus_search_bp
    app.register_blueprint(corpus_search_bp, url_prefix='/api/corpus')
```

Update `__init__.py` or main route registration to call this function.

## Testing Checklist

- [ ] API returns correct format for valid queries
- [ ] API returns error for missing query parameter
- [ ] Modal opens when "Search Corpus" button is clicked
- [ ] Headword is pre-filled in search input
- [ ] Results display correctly (left | match | right)
- [ ] Results are scrollable
- [ ] "Insert as Example" action creates new example
- [ ] "Copy" action copies text to clipboard
- [ ] Error state displays when Lucene is unavailable
- [ ] Modal closes properly on Cancel/close
- [ ] Keyboard navigation works
- [ ] ARIA attributes are correct

## Files to Create

1. `app/api/corpus_search.py` - API endpoint
2. `app/static/js/corpus-search.js` - JavaScript module
3. `app/static/css/corpus-search.css` - CSS styles
4. `app/templates/corpus_search_modal.html` - Modal template

## Files to Modify

1. `app/routes/corpus_routes.py` - Register endpoint
2. `app/templates/entry_form.html` - Add buttons and include modal
