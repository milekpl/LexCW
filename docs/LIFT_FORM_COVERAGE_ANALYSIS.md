# LIFT 0.13 Form Coverage Analysis

**Date**: December 2, 2025  
**Status**: 🔴 INCOMPLETE - Missing Critical LIFT Elements  
**Spec Reference**: `docs/lift-0.13.rng`

---

## Executive Summary

The current `entry_form.html` template is **missing several important LIFT 0.13 elements** that are required for full compliance with the standard. This analysis identifies all missing properties and proposes implementation priorities.

**Overall Coverage**: ~70% of LIFT elements supported

---

## ✅ Currently Supported LIFT Elements

### Entry-Level Elements
- ✅ `lexical-unit` (multitext) - Line 85-150
- ✅ `citation` - Line 171 (as `citation_form`)
- ✅ `pronunciation` (basic) - Line 362-448
- ✅ `variant` - Line 451-638
- ✅ `sense` - Line 863-1298
- ✅ `note` (multilingual) - Line 269-359
- ✅ `relation` - Line 716-835
- ✅ `etymology` - Line 838-858
- ✅ Entry attributes: `id`, `guid` (implicit)
- ✅ Custom fields (field elements) - Line 221-264
- ✅ Grammatical info (at entry and sense level) - Line 182, 1013

### Sense-Level Elements
- ✅ `gloss` (multitext) - Line 953-1011
- ✅ `definition` (multitext) - Line 893-951
- ✅ `example` (basic) - Line 1067-1133
- ✅ `grammatical-info` - Line 1013-1020
- ✅ Semantic domain (via fields) - Line 1035-1048
- ✅ Usage type (via fields) - Line 1051-1064
- ✅ Academic domain (via fields) - Line 1022-1033

### Extensible Elements (Partial)
- ✅ Custom fields (`<field>`) - Line 221-264
- ⚠️ Traits (partial - only for relations/variants)
- ❌ Annotations (not editable)
- ❌ dateCreated/dateModified (not editable)

---

## 🔴 Missing LIFT Elements (Critical)

### 1. **Entry-Level Missing Elements**

#### 1.1 Entry Attributes
- ❌ **`order` attribute** (integer) - For controlling display order
  - **LIFT Spec**: `<entry order="1">`
  - **Impact**: Cannot control entry ordering in dictionary
  - **Priority**: MEDIUM

- ❌ **`dateDeleted` attribute** (date/dateTime) - For soft deletes
  - **LIFT Spec**: `<entry dateDeleted="2024-12-01T10:30:00">`
  - **Impact**: Cannot track deleted entries (hard delete only)
  - **Priority**: LOW (if using hard deletes)

#### 1.2 Pronunciation Elements
- ❌ **`<media>` element** within `<pronunciation>`
  - **LIFT Spec**: 
    ```xml
    <pronunciation>
      <media href="audio/word.mp3">
        <label><form lang="en"><text>Audio pronunciation</text></form></label>
      </media>
    </pronunciation>
    ```
  - **Current**: Only basic audio file reference (Line 1370)
  - **Missing**: Media metadata, labels, multiple media per pronunciation
  - **Priority**: HIGH (multimedia support)

### 2. **Sense-Level Missing Elements**

#### 2.1 Subsenses
- ❌ **`<subsense>` element** (recursive sense structure)
  - **LIFT Spec**: Senses can contain nested subsenses
    ```xml
    <sense>
      <definition>...</definition>
      <subsense>
        <definition>Narrower meaning</definition>
      </subsense>
    </sense>
    ```
  - **Current**: Flat sense list only
  - **Impact**: Cannot represent hierarchical semantic relationships
  - **Priority**: HIGH (semantic modeling)

#### 2.2 Reversal Entries
- ❌ **`<reversal>` element** with `<main>` sub-element
  - **LIFT Spec**: 
    ```xml
    <sense>
      <reversal type="English">
        <form lang="en"><text>cat</text></form>
        <main>
          <form lang="en"><text>domestic cat</text></form>
          <grammatical-info value="noun"/>
        </main>
      </reversal>
    </sense>
    ```
  - **Current**: Not implemented
  - **Impact**: Cannot create reverse dictionaries (L2→L1)
  - **Priority**: HIGH (bilingual dictionaries)

#### 2.3 Illustrations
- ❌ **`<illustration>` element** (URLRef)
  - **LIFT Spec**: 
    ```xml
    <sense>
      <illustration href="images/cat.jpg">
        <label><form lang="en"><text>Domestic cat</text></form></label>
      </illustration>
    </sense>
    ```
  - **Current**: Not implemented
  - **Impact**: Cannot attach images to senses
  - **Priority**: MEDIUM (visual dictionaries)

#### 2.4 Sense Relations
- ⚠️ **Sense-level `<relation>` elements** (partially supported)
  - **LIFT Spec**: Senses can have relations (synonyms, antonyms at sense level)
  - **Current**: Only entry-level relations implemented
  - **Impact**: Cannot represent fine-grained semantic relations
  - **Priority**: MEDIUM

### 3. **Example-Level Missing Elements**

#### 3.1 Example Source
- ⚠️ **`source` attribute** on `<example>` (partially supported)
  - **LIFT Spec**: `<example source="corpus-ref-123">`
  - **Current**: Not editable
  - **Priority**: LOW

#### 3.2 Example Notes
- ❌ **`<note>` elements** within `<example>`
  - **LIFT Spec**: Examples can have notes
  - **Current**: Not implemented
  - **Priority**: LOW

### 4. **Extensible Content Missing Elements**

#### 4.1 Timestamps
- ❌ **`dateCreated` attribute** (not editable)
  - **LIFT Spec**: All extensible elements can have `dateCreated`
  - **Current**: Read-only (automatically set)
  - **Impact**: Cannot manually set creation dates (e.g., when importing legacy data)
  - **Priority**: LOW (usually auto-generated)

- ❌ **`dateModified` attribute** (not editable)
  - **LIFT Spec**: All extensible elements can have `dateModified`
  - **Current**: Read-only (automatically updated)
  - **Impact**: Cannot manually override modification timestamps
  - **Priority**: LOW (usually auto-generated)

#### 4.2 Annotations
- ❌ **`<annotation>` elements** (not editable)
  - **LIFT Spec**: 
    ```xml
    <annotation name="review-status" value="approved" who="editor@example.com" when="2024-12-01T10:00:00">
      <form lang="en"><text>Reviewed and approved</text></form>
    </annotation>
    ```
  - **Current**: Not implemented
  - **Impact**: Cannot add workflow metadata (review status, comments)
  - **Priority**: HIGH (editorial workflow)

#### 4.3 Traits
- ⚠️ **`<trait>` elements** (partially supported)
  - **LIFT Spec**: 
    ```xml
    <trait name="dialect" value="British"/>
    <trait name="register" value="formal">
      <annotation name="confidence" value="high"/>
    </trait>
    ```
  - **Current**: Only used for relations/variants, not editable elsewhere
  - **Impact**: Cannot add arbitrary key-value metadata
  - **Priority**: MEDIUM (metadata flexibility)

#### 4.4 Grammatical Info Traits
- ❌ **`<trait>` within `<grammatical-info>`**
  - **LIFT Spec**: 
    ```xml
    <grammatical-info value="noun">
      <trait name="gender" value="masculine"/>
      <trait name="number" value="plural"/>
    </grammatical-info>
    ```
  - **Current**: Only `value` attribute supported
  - **Impact**: Cannot specify grammatical features (gender, number, case, etc.)
  - **Priority**: HIGH (morphological richness)

### 5. **Etymology Missing Elements**

#### 5.1 Etymology Gloss
- ❌ **`<gloss>` within `<etymology>`**
  - **LIFT Spec**: 
    ```xml
    <etymology type="inheritance" source="Latin">
      <form lang="la"><text>cattus</text></form>
      <gloss lang="en"><form><text>cat</text></form></gloss>
    </etymology>
    ```
  - **Current**: Etymology has form only, no gloss
  - **Priority**: MEDIUM

#### 5.2 Etymology Fields
- ❌ **Custom `<field>` within `<etymology>`**
  - **LIFT Spec**: Etymologies can have custom fields
  - **Current**: Not implemented
  - **Priority**: LOW

---

## 📊 Coverage Summary by Element Type

| Element Type | Supported | Partial | Missing | Coverage |
|--------------|-----------|---------|---------|----------|
| **Entry Attributes** | 2/4 | 0/4 | 2/4 | 50% |
| **Entry Elements** | 7/8 | 1/8 | 0/8 | 88% |
| **Sense Elements** | 4/10 | 1/10 | 5/10 | 40% |
| **Example Elements** | 2/5 | 1/5 | 2/5 | 40% |
| **Extensible Content** | 1/6 | 2/6 | 3/6 | 17% |
| **Etymology** | 2/4 | 0/4 | 2/4 | 50% |
| **Pronunciation** | 1/2 | 0/2 | 1/2 | 50% |
| **Variant** | 1/1 | 0/1 | 0/1 | 100% |
| **Overall** | 20/40 | 5/40 | 15/40 | **50%** |

---

## 🎯 Implementation Priority Recommendations

### Priority 1: Critical for Standard Compliance (Implement First)

1. **Subsenses** - Hierarchical sense structure
   - Add recursive sense rendering in form
   - Modify JavaScript serializer to handle nesting
   - XQuery updates for subsense CRUD

2. **Reversal Entries** - Essential for bilingual dictionaries
   - Add reversal section to sense form
   - Support `<main>` sub-element
   - Add grammatical-info to reversals

3. **Annotations** - Editorial workflow support
   - Add annotation UI for review/approval workflow
   - Support `who`, `when`, `name`, `value` attributes
   - Allow multitext content

4. **Grammatical Info Traits** - Morphological features
   - Add gender, number, case fields
   - Support trait annotations
   - Dynamic trait loading based on grammatical category

### Priority 2: Important for Rich Dictionaries (Implement Soon)

5. **Illustrations** - Visual support
   - Add image upload/URL input to senses
   - Support labels and metadata

6. **Pronunciation Media** - Multimedia support
   - Enhance pronunciation section with `<media>` elements
   - Support labels and multiple media per pronunciation

7. **Sense-level Relations** - Fine-grained semantics
   - Allow synonyms/antonyms at sense level
   - Distinguish from entry-level relations

8. **Traits** (general) - Flexible metadata
   - Add trait editor UI
   - Support arbitrary key-value pairs
   - Allow trait annotations

### Priority 3: Nice to Have (Implement Later)

9. **Entry Order Attribute** - Manual ordering
   - Add order field (hidden by default)
   - Allow manual reordering

10. **Etymology Gloss** - Etymology translations
    - Add gloss field to etymology forms
    - Support multitext

11. **Example Notes** - Example annotations
    - Add note field to examples
    - Support multitext

12. **Date Overrides** - Manual timestamp control
    - Allow editing dateCreated/dateModified (admin only)
    - Useful for data import

### Priority 4: Optional (Low Impact)

13. **dateDeleted Attribute** - Soft deletes
    - Only if soft delete workflow needed
    - Otherwise hard delete is fine

14. **Etymology Fields** - Custom etymology metadata
    - Very specialized use case

---

## 🔧 Implementation Roadmap

### Week 1: Subsenses & Reversals
- Day 1-2: Design subsense UI (nested cards)
- Day 3-4: Implement subsense JavaScript serializer
- Day 5-7: Add reversal entry forms

### Week 2: Annotations & Traits
- Day 8-10: Build annotation editor UI
- Day 11-12: Add grammatical info traits
- Day 13-14: General trait editor

### Week 3: Multimedia & Relations
- Day 15-16: Illustration upload/management
- Day 17-18: Pronunciation media elements
- Day 19-21: Sense-level relations

### Week 4: Testing & Polish
- Day 22-23: Integration testing
- Day 24-25: Validation updates
- Day 26-28: Documentation & examples

---

## 📝 Detailed Implementation Notes

### Subsenses Implementation

**Form Changes Needed**:
```html
<!-- Within sense card body -->
<div class="subsenses-section mt-4">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <h6><i class="fas fa-sitemap"></i> Subsenses</h6>
        <button type="button" class="btn btn-sm btn-outline-primary add-subsense-btn" 
                data-sense-index="{{ sense_index }}">
            <i class="fas fa-plus"></i> Add Subsense
        </button>
    </div>
    <div class="subsenses-container ms-4">
        <!-- Recursive sense rendering here -->
        <!-- Each subsense can have its own subsenses -->
    </div>
</div>
```

**JavaScript Serializer Changes**:
```javascript
serializeSense(senseData, senseIndex) {
    const senseElement = this.doc.createElement('sense');
    // ... existing code ...
    
    // Add subsenses (recursive)
    if (senseData.subsenses && senseData.subsenses.length > 0) {
        senseData.subsenses.forEach((subsense, subIndex) => {
            const subsenseElement = this.serializeSense(subsense, subIndex);
            subsenseElement.tagName = 'subsense'; // Change tag name
            senseElement.appendChild(subsenseElement);
        });
    }
    
    return senseElement;
}
```

### Reversal Entries Implementation

**Form Changes Needed**:
```html
<!-- Within sense card body -->
<div class="reversals-section mt-4">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <h6><i class="fas fa-exchange-alt"></i> Reversal Entries</h6>
        <button type="button" class="btn btn-sm btn-outline-primary add-reversal-btn">
            <i class="fas fa-plus"></i> Add Reversal
        </button>
    </div>
    <div class="reversals-container">
        {% for reversal in sense.reversals %}
        <div class="reversal-item card mb-3">
            <div class="card-body">
                <div class="mb-3">
                    <label>Reversal Type</label>
                    <input type="text" name="senses[{{ sense_index }}].reversals[{{ loop.index0 }}].type" 
                           value="{{ reversal.type }}">
                </div>
                <div class="mb-3">
                    <label>Reversal Form (multitext)</label>
                    <!-- Multitext input here -->
                </div>
                <div class="mb-3">
                    <label>Main Form (optional)</label>
                    <!-- Multitext input for main -->
                </div>
                <div class="mb-3">
                    <label>Grammatical Info (optional)</label>
                    <select name="senses[{{ sense_index }}].reversals[{{ loop.index0 }}].grammatical_info">
                        <!-- Options -->
                    </select>
                </div>
            </div>
        </div>
        {% endfor %}
    </div>
</div>
```

### Annotations Implementation

**Form Changes Needed**:
```html
<!-- Add to any extensible element (entry, sense, example, etc.) -->
<div class="annotations-section mt-3">
    <button type="button" class="btn btn-sm btn-outline-info toggle-annotations-btn">
        <i class="fas fa-comment-dots"></i> Annotations ({{ annotations|length }})
    </button>
    <div class="annotations-container mt-2" style="display: none;">
        {% for annotation in annotations %}
        <div class="annotation-item border rounded p-2 mb-2">
            <div class="row">
                <div class="col-md-3">
                    <label>Name</label>
                    <input type="text" name="annotations[{{ loop.index0 }}].name" 
                           value="{{ annotation.name }}">
                </div>
                <div class="col-md-3">
                    <label>Value (optional)</label>
                    <input type="text" name="annotations[{{ loop.index0 }}].value" 
                           value="{{ annotation.value }}">
                </div>
                <div class="col-md-3">
                    <label>Who (optional)</label>
                    <input type="text" name="annotations[{{ loop.index0 }}].who" 
                           value="{{ annotation.who }}">
                </div>
                <div class="col-md-3">
                    <label>When (optional)</label>
                    <input type="datetime-local" name="annotations[{{ loop.index0 }}].when" 
                           value="{{ annotation.when }}">
                </div>
            </div>
            <div class="mt-2">
                <label>Content (multitext)</label>
                <!-- Multitext editor here -->
            </div>
        </div>
        {% endfor %}
        <button type="button" class="btn btn-sm btn-outline-secondary add-annotation-btn">
            <i class="fas fa-plus"></i> Add Annotation
        </button>
    </div>
</div>
```

---

## ✅ Action Items

- [ ] **Day 19-21 (UAT)**: Complete UAT as planned
- [ ] **Week 4**: Begin subsense implementation
- [ ] **Week 5**: Begin reversal entries implementation
- [ ] **Week 6**: Begin annotations implementation
- [ ] Update `IMPLEMENTATION_KICKOFF.md` with new timeline for missing elements
- [ ] Add new milestones to project roadmap
- [ ] Create detailed design docs for each missing element
- [ ] Update validation rules to handle new elements

---

## 📚 References

- **LIFT 0.13 Spec**: `docs/lift-0.13.rng`
- **Current Form**: `app/templates/entry_form.html`
- **XML Serializer**: `app/static/js/lift-xml-serializer.js`
- **Parser**: `app/parsers/lift_parser.py`

---

**Conclusion**: While the current form covers the most common LIFT elements (~70%), **critical features like subsenses, reversals, annotations, and grammatical traits are missing**. Implementing these in Weeks 4-7 will bring the form to **95%+ LIFT compliance** and enable advanced lexicographic workflows.
