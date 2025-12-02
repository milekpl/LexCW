# LIFT 0.13 Complete Implementation Plan

**Based on**: SIL FieldWorks LIFT Implementation  
**Date**: December 2, 2025  
**Status**: ✅ WEEK 4 IN PROGRESS - Day 22-23 COMPLETE (21/21 tests passing)  
**Branch**: `feature/xml-direct-manipulation`  
**Reference**: [FieldWorks LiftMergerTests.cs](https://github.com/sillsdev/FieldWorks/blob/5eb08254/Src/LexText/LexTextControls/LexTextControlsTests/LiftMergerTests.cs)

---

## Executive Summary

This plan extends the XML Direct Manipulation implementation (Weeks 1-3 ✅ COMPLETE) to achieve **100% LIFT 0.13 compliance** with full FieldWorks feature parity. The current implementation supports ~50% of LIFT elements. This plan adds the remaining 50% over 4 additional weeks (Weeks 4-7).

**Current Status**: ✅ Week 4 Day 22-23 COMPLETE (Subsenses fully implemented + 21 tests passing)  
**Completed**: Weeks 1-3 (XML Direct Manipulation foundation - all 116 tests passing)  
**Target**: Full SIL FieldWorks LIFT compatibility (100% element coverage)

---

## Key Findings from FieldWorks Analysis

### Custom Fields FieldWorks Supports

From `LiftMergerTests.cs` analysis, FieldWorks uses the following custom fields extensively:

#### 1. **Predefined Custom Fields** (via `<field>` elements)
- ✅ `cv-pattern` - Syllable pattern for pronunciations
- ✅ `tone` - Tone information for pronunciations
- ✅ `comment` - Comments/notes in etymology
- ✅ `import-residue` - Legacy data preservation
- ✅ `literal-meaning` - Literal meaning for compounds/idioms
- ✅ `summary-definition` - Entry-level summary definition
- ✅ **`exemplar`** - Exemplar form for sense (⚠️ **MISSING IN OUR FORM**)
- ✅ **`scientific-name`** - Scientific name for sense (⚠️ **MISSING IN OUR FORM**)

#### 2. **Custom Field Types** (via `qaa-x-spec` specification)
- ✅ `String` - Single-string custom fields
- ✅ `MultiUnicode` - Multi-writing system text
- ✅ `Integer` - Numeric values
- ✅ `GenDate` - Generic date (approximate, before, after)
- ✅ `ReferenceAtomic` - Single reference to CmPossibility
- ✅ `ReferenceCollection` - Multiple references to CmPossibility
- ✅ `OwningAtomic` - Owns StText (formatted text)

#### 3. **Custom Possibility Lists** (via `<range>` in lift-ranges)
Examples from FieldWorks:
- `CustomCmPossibiltyList` - User-defined classification lists
- `CustomList Number2` - Additional custom lists
- `status` range with `Pending`, `Confirmed` values
- `do-not-publish-in` - Publication control lists
- `location` - Geographic locations hierarchy
- `anthro-code` - Anthropology codes

#### 4. **Trait Usage Patterns**
From test data analysis:
```xml
<!-- Morph type trait (standard) -->
<trait name="morph-type" value="stem"/>

<!-- Custom list reference trait -->
<trait name="semantic-domain-ddp4" value="2.6.5.1 Man"/>

<!-- Custom field integer trait -->
<trait name="CustomFldEntry Number" value="13"/>

<!-- Custom field date trait -->
<trait name="CustomFldEntry GenDate" value="201105232"/>

<!-- Custom list single item trait -->
<trait name="CustomFldEntry ListSingleItem" value="graphology"/>

<!-- Grammatical info trait (morphology) -->
<grammatical-info value="Noun">
  <trait name="gender" value="masculine"/>
  <trait name="number" value="plural"/>
</grammatical-info>

<!-- Variant/allomorph trait -->
<variant>
  <trait name="paradigm" value="sing"/>
</variant>

<!-- Publication control trait -->
<trait name="do-not-publish-in" value="Main Dictionary"/>

<!-- Example status trait -->
<example>
  <trait name="CustomExampleStatus" value="Pending"/>
</example>
```

#### 5. **StText Custom Fields** (Formatted Text)
FieldWorks supports rich formatted text in custom fields:
```xml
<field type="Long Text">
  <form lang="en"><text>
    <span class="Bulleted List">
      <span lang="en">This is </span>
      <span lang="en" class="Emphasized Text">multiple</span>
      <span lang="en"> paragraphs.</span>
    </span>
    ¶  <!-- Paragraph separator -->
    <span class="Normal">
      <span lang="en">Second paragraph with </span>
      <span lang="en" class="Strong">formatting</span>
    </span>
  </text></form>
</field>
```

---

## Updated Coverage Analysis

### Current Coverage: 50% → Target: 100%

| Category | Currently Supported | Missing (Priority 1) | Missing (Priority 2) | Total Coverage |
|----------|---------------------|----------------------|----------------------|----------------|
| **Entry Elements** | 8/12 | 2 (subsenses, order) | 2 (dateDeleted, media) | 67% → 100% |
| **Sense Elements** | 5/14 | 4 (subsenses, reversals, illustrations, annotations) | 5 (sense relations, trait editor) | 36% → 100% |
| **Example Elements** | 3/7 | 2 (example notes, source) | 2 (example fields, traits) | 43% → 100% |
| **Extensible Content** | 2/8 | 3 (annotations, general traits, grammatical traits) | 3 (dateCreated/Modified editor) | 25% → 100% |
| **Custom Fields** | 1/7 | **3 (exemplar, scientific-name, StText)** | 3 (integer, gendate, possibility refs) | **14% → 100%** |
| **Pronunciation** | 1/3 | 1 (media elements) | 1 (cv-pattern, tone) | 33% → 100% |
| **Etymology** | 2/5 | 1 (gloss, fields) | 2 (comment field) | 40% → 100% |
| **Overall** | 22/56 | **16** | **18** | **39% → 100%** |

---

## 🚨 Critical FieldWorks Features Missing from Coverage Analysis

### 1. **Exemplar Field** (Sense-Level Custom Field)
- **FieldWorks Usage**: Stores exemplar form for sense
- **LIFT Implementation**:
  ```xml
  <field tag="exemplar">
    <form lang="en"><text>This field stores the exemplar form for the current sense.</text></form>
  </field>
  ```
- **Example**:
  ```xml
  <sense>
    <field type="exemplar">
      <form lang="fr"><text>homme exemplaire</text></form>
    </field>
  </sense>
  ```
- **Priority**: **HIGH** (FieldWorks standard field)

### 2. **Scientific Name Field** (Sense-Level Custom Field)
- **FieldWorks Usage**: Stores scientific name for biological terms
- **LIFT Implementation**:
  ```xml
  <field tag="scientific-name">
    <form lang="en"><text>This field stores the scientific name pertinent to the current sense.</text></form>
  </field>
  ```
- **Example**:
  ```xml
  <sense>
    <gloss lang="en"><text>cat</text></gloss>
    <field type="scientific-name">
      <form lang="la"><text>Felis catus</text></form>
    </field>
  </sense>
  ```
- **Priority**: **HIGH** (FieldWorks standard field, essential for botanical/zoological dictionaries)

### 3. **Literal Meaning Field** (Entry-Level Custom Field)
- **FieldWorks Usage**: Literal meaning of compounds/idioms
- **LIFT Implementation**:
  ```xml
  <field tag="literal-meaning">
    <form lang="en"><text>This field is used to store a literal meaning of the entry.</text></form>
  </field>
  ```
- **Example**:
  ```xml
  <entry>
    <lexical-unit><form lang="fr"><text>pied-à-terre</text></form></lexical-unit>
    <field type="literal-meaning">
      <form lang="en"><text>foot to ground</text></form>
    </field>
    <sense>
      <definition><form lang="en"><text>temporary residence</text></form></definition>
    </sense>
  </entry>
  ```
- **Priority**: **MEDIUM** (useful for compound/idiom dictionaries)

### 4. **Summary Definition Field** (Entry-Level Custom Field)
- **FieldWorks Usage**: Entry-level summary definition
- **LIFT Implementation**:
  ```xml
  <field tag="summary-definition">
    <form lang="en"><text>A summary definition summarizing all senses.</text></form>
  </field>
  ```
- **Priority**: **LOW** (pragmatic, not theoretical)

### 5. **CV Pattern & Tone Fields** (Pronunciation-Level Custom Fields)
- **FieldWorks Usage**: Syllable pattern and tone information
- **LIFT Implementation**:
  ```xml
  <pronunciation>
    <form lang="qaa-fonipa-x-kal"><text>ʔapa</text></form>
    <field type="cv-pattern">
      <form lang="en"><text>CVCV</text></form>
    </field>
    <field type="tone">
      <form lang="en"><text>HLH</text></form>
    </field>
  </pronunciation>
  ```
- **Priority**: **MEDIUM** (important for phonological analysis)

### 6. **Comment Field** (Etymology-Level Custom Field)
- **FieldWorks Usage**: Notes in etymology
- **LIFT Implementation**:
  ```xml
  <etymology type="inheritance" source="Latin">
    <form lang="la"><text>cattus</text></form>
    <field type="comment">
      <form lang="en"><text>Borrowed via Old French</text></form>
    </field>
  </etymology>
  ```
- **Priority**: **LOW**

### 7. **StText Custom Fields** (Rich Formatted Text)
- **FieldWorks Usage**: Long text with paragraph styles and character formatting
- **LIFT Implementation**:
  ```xml
  <field type="Long Text">
    <form lang="en"><text>
      <span class="Bulleted List"><span lang="en">Paragraph one</span></span>¶
      <span class="Normal"><span lang="en" class="Strong">Bold text</span></span>
    </text></form>
  </field>
  ```
- **Priority**: **LOW** (complex, rarely used)

---

## Revised Implementation Roadmap (Weeks 4-7)

### Week 4: Priority 1 Critical Features (Days 22-28)

#### **Day 22-23: Subsenses (Recursive Sense Structure)**
- **Goal**: Support hierarchical sense structure
- **Tasks**:
  - [ ] Add subsense section to sense card (recursive rendering)
  - [ ] Modify JavaScript serializer to handle nested senses
  - [ ] Update XQuery operations for subsense CRUD
  - [ ] Write unit tests (15 tests)
- **Acceptance Criteria**:
  - ✅ Can add/edit/delete subsenses recursively
  - ✅ Subsenses render correctly in UI
  - ✅ XML serialization includes subsense nesting

#### **Day 24-25: Reversals (Bilingual Dictionary Support)**
- **Goal**: Support L2→L1 reversals with main element
- **Tasks**:
  - [ ] Add reversal section to sense form
  - [ ] Support `<reversal>` with `<main>` sub-element
  - [ ] Add grammatical-info to reversals
  - [ ] Write unit tests (12 tests)
- **Acceptance Criteria**:
  - ✅ Can add reversals with main form
  - ✅ Reversals support grammatical info
  - ✅ Multiple reversals per sense

#### **Day 26-27: Annotations (Editorial Workflow)**
- **Goal**: Support workflow metadata (review status, comments)
- **Tasks**:
  - [ ] Add annotation UI (collapsible section)
  - [ ] Support `who`, `when`, `name`, `value` attributes
  - [ ] Allow multitext content
  - [ ] Write unit tests (10 tests)
- **Acceptance Criteria**:
  - ✅ Can add annotations to any extensible element
  - ✅ Annotations support all attributes
  - ✅ Multitext content renders correctly

#### **Day 28: FieldWorks Standard Custom Fields**
- **Goal**: Add `exemplar` and `scientific-name` fields
- **Tasks**:
  - [ ] Add exemplar field to sense form
  - [ ] Add scientific-name field to sense form
  - [ ] Add literal-meaning field to entry form
  - [ ] Update JavaScript serializer
  - [ ] Write unit tests (8 tests)
- **Acceptance Criteria**:
  - ✅ Exemplar field works for senses
  - ✅ Scientific-name field works for senses
  - ✅ Literal-meaning field works for entries
  - ✅ Fields serialize correctly to LIFT XML

---

### Week 5: Grammatical Features & Traits (Days 29-35)

#### **Day 29-30: Grammatical Info Traits**
- **Goal**: Support morphological features (gender, number, case)
- **Tasks**:
  - [ ] Add trait editor to grammatical-info
  - [ ] Support gender, number, case, tense fields
  - [ ] Dynamic trait loading based on POS
  - [ ] Write unit tests (15 tests)
- **Acceptance Criteria**:
  - ✅ Can add traits to grammatical-info
  - ✅ Traits support all morphological features
  - ✅ Traits serialize correctly

#### **Day 31-32: General Traits (Flexible Metadata)**
- **Goal**: Support arbitrary key-value traits on all elements
- **Tasks**:
  - [ ] Add trait editor UI (modal dialog)
  - [ ] Support trait annotations
  - [ ] Allow traits on entry, sense, example, etc.
  - [ ] Write unit tests (12 tests)
- **Acceptance Criteria**:
  - ✅ Can add traits to any element
  - ✅ Traits support arbitrary key-value pairs
  - ✅ Trait annotations work correctly

#### **Day 33-34: Illustrations (Visual Support)**
- **Goal**: Support images for senses
- **Tasks**:
  - [ ] Add image upload/URL input to senses
  - [ ] Support labels and metadata
  - [ ] Display thumbnails in sense cards
  - [ ] Write unit tests (8 tests)
- **Acceptance Criteria**:
  - ✅ Can upload images or provide URLs
  - ✅ Images display correctly
  - ✅ Labels and captions work

#### **Day 35: Pronunciation Media Elements**
- **Goal**: Enhance pronunciation with media metadata
- **Tasks**:
  - [ ] Add `<media>` element support
  - [ ] Support labels and multiple media per pronunciation
  - [ ] Write unit tests (6 tests)
- **Acceptance Criteria**:
  - ✅ Can add multiple media per pronunciation
  - ✅ Media labels work correctly

---

### Week 6: Advanced Custom Fields (Days 36-42)

#### **Day 36-37: Custom Field Type Support**
- **Goal**: Support all FieldWorks custom field types
- **Tasks**:
  - [ ] Integer custom fields (trait-based)
  - [ ] GenDate custom fields (trait-based)
  - [ ] MultiUnicode custom fields (field-based)
  - [ ] Write unit tests (15 tests)
- **Acceptance Criteria**:
  - ✅ Integer fields work for entry/sense/example
  - ✅ GenDate fields support approximate dates
  - ✅ MultiUnicode fields support multiple writing systems

#### **Day 38-39: Custom Possibility Lists**
- **Goal**: Support user-defined classification lists
- **Tasks**:
  - [ ] ReferenceAtomic custom fields (single selection)
  - [ ] ReferenceCollection custom fields (multi-selection)
  - [ ] Load custom ranges from lift-ranges file
  - [ ] Write unit tests (12 tests)
- **Acceptance Criteria**:
  - ✅ Can reference custom possibility lists
  - ✅ Single and multi-selection work
  - ✅ Custom lists load from ranges

#### **Day 40-41: Pronunciation Custom Fields**
- **Goal**: Add cv-pattern and tone fields
- **Tasks**:
  - [ ] Add cv-pattern field to pronunciations
  - [ ] Add tone field to pronunciations
  - [ ] Update JavaScript serializer
  - [ ] Write unit tests (6 tests)
- **Acceptance Criteria**:
  - ✅ CV pattern field works
  - ✅ Tone field works
  - ✅ Fields serialize correctly

#### **Day 42: Sense Relations (Fine-Grained Semantics)**
- **Goal**: Support sense-level relations
- **Tasks**:
  - [ ] Add relation section to sense form
  - [ ] Distinguish sense relations from entry relations
  - [ ] Write unit tests (8 tests)
- **Acceptance Criteria**:
  - ✅ Can add sense-level synonyms/antonyms
  - ✅ Sense relations distinct from entry relations

---

### Week 7: Polish & Optional Features (Days 43-49)

#### **Day 43-44: Entry Order & Optional Attributes**
- **Goal**: Support manual ordering and optional attributes
- **Tasks**:
  - [ ] Add order field (hidden by default)
  - [ ] Support dateCreated/dateModified editor (admin only)
  - [ ] Support dateDeleted attribute (soft deletes)
  - [ ] Write unit tests (10 tests)
- **Acceptance Criteria**:
  - ✅ Order attribute works
  - ✅ Date overrides work (admin only)
  - ✅ Soft delete works

#### **Day 45-46: Etymology Enhancements**
- **Goal**: Complete etymology support
- **Tasks**:
  - [ ] Add gloss field to etymology
  - [ ] Add comment field to etymology
  - [ ] Add custom fields to etymology
  - [ ] Write unit tests (8 tests)
- **Acceptance Criteria**:
  - ✅ Etymology gloss works
  - ✅ Etymology comment works
  - ✅ Etymology custom fields work

#### **Day 47-48: Example Enhancements**
- **Goal**: Complete example support
- **Tasks**:
  - [ ] Add note field to examples
  - [ ] Add source attribute editor
  - [ ] Add custom fields to examples
  - [ ] Write unit tests (8 tests)
- **Acceptance Criteria**:
  - ✅ Example notes work
  - ✅ Example source works
  - ✅ Example custom fields work

#### **Day 49: Final Integration Testing**
- **Goal**: Comprehensive end-to-end testing
- **Tasks**:
  - [ ] Run all unit tests (200+ tests)
  - [ ] Run integration tests (50+ tests)
  - [ ] Test with real FieldWorks LIFT files
  - [ ] Performance testing with complex entries
  - [ ] Update documentation
- **Acceptance Criteria**:
  - ✅ All tests passing
  - ✅ FieldWorks LIFT files import correctly
  - ✅ Performance acceptable
  - ✅ Documentation complete

---

## Success Metrics (Updated)

| Metric | Week 3 Target | Week 7 Target | Current |
|--------|---------------|---------------|---------|
| **LIFT Element Coverage** | 50% | **100%** | 50% |
| **FieldWorks Compatibility** | 60% | **100%** | 60% |
| **Custom Field Support** | 14% | **100%** | 14% |
| **Test Coverage** | 100% | **100%** | 100% |
| **Entry Load Time** | ≤200ms | ≤250ms | <10ms ✅ |
| **Entry Save Time** | ≤250ms | ≤300ms | 6.99ms ✅ |
| **Critical Bugs** | <3 | <3 | 0 ✅ |

---

## Implementation Notes

### Custom Field Registration

All custom fields must be registered in the header:
```xml
<header>
  <fields>
    <field tag="exemplar">
      <form lang="en"><text>This field stores the exemplar form for the current sense.</text></form>
    </field>
    <field tag="scientific-name">
      <form lang="en"><text>This field stores the scientific name pertinent to the current sense.</text></form>
    </field>
    <!-- Custom fields with type specification -->
    <field tag="CustomFldEntry Number">
      <form lang="en"><text>Number Custom Field Description</text></form>
      <form lang="qaa-x-spec"><text>Class=LexEntry; Type=Integer</text></form>
    </field>
  </fields>
</header>
```

### Trait vs Field Decision Tree

**Use `<trait>` when**:
- Single value (name-value pair)
- Simple data types (string, integer, date)
- No multitext needed
- Example: `<trait name="morph-type" value="stem"/>`

**Use `<field>` when**:
- Multitext content (multiple writing systems)
- Complex data (formatted text, StText)
- Descriptive content
- Example: `<field type="exemplar"><form lang="fr"><text>...</text></form></field>`

### Testing Strategy

Each feature must have:
1. **Unit tests** (JavaScript + Python)
   - XML serialization tests
   - Parsing tests
   - Validation tests

2. **Integration tests**
   - Form submission tests
   - Database round-trip tests
   - FieldWorks LIFT file import tests

3. **Compatibility tests**
   - Import real FieldWorks LIFT files
   - Verify all elements preserved
   - Export and re-import test

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Performance degradation** | LOW | HIGH | Benchmark after each feature |
| **UI complexity** | MEDIUM | MEDIUM | Progressive disclosure (collapsible sections) |
| **Testing complexity** | HIGH | HIGH | Automated test suite for each feature |
| **FieldWorks compatibility issues** | MEDIUM | HIGH | Test with real FieldWorks files weekly |
| **User adoption resistance** | LOW | MEDIUM | Make advanced features optional/hidden by default |

---

## Next Steps

### Immediate Actions (Week 4 Starting)

1. ✅ **Complete Day 19-21**: User Acceptance Testing for Week 3 ✅ DONE
   - ✅ Deployed current implementation to staging
   - ✅ Ran manual testing scenarios
   - ✅ Collected user feedback (positive, no critical bugs)

2. ✅ **Prepare for Week 4**: ✅ DONE
   - ✅ Reviewed implementation plan
   - ✅ Updated `IMPLEMENTATION_KICKOFF.md` with Weeks 4-7
   - ✅ Ready to start subsenses implementation

3. ▶️ **Day 22 - Start Subsenses Implementation**:
   - Read FieldWorks subsense test examples
   - Design recursive sense UI component
   - Update JavaScript serializer for nested senses
   - Create unit tests for subsense structure

### Stakeholder Review Questions

- **Should we proceed with UAT using 50% coverage**, or delay until critical features are added?
- **Which custom fields are essential** for your dictionary projects? (exemplar, scientific-name, others?)
- **Are subsenses and reversals critical** for your current work?
- **What timeline works best** for the 4-week extension?

---

## Conclusion

This plan extends the XML Direct Manipulation project to **100% LIFT 0.13 compliance** with full FieldWorks feature parity. The 4-week implementation (Weeks 4-7) systematically adds:

- **16 Priority 1 features** (subsenses, reversals, annotations, FieldWorks custom fields)
- **18 Priority 2 features** (grammatical traits, illustrations, pronunciation media, advanced custom fields)
- **Full FieldWorks compatibility** (import/export with zero data loss)

**Total Implementation**: 7 weeks (3 complete ✅, 4 planned 📋)  
**Expected Completion**: End of Week 7  
**Success Criteria**: 100% LIFT element coverage, FieldWorks compatibility, >90% test coverage

---

**Ready to proceed?** Please review and approve to start Week 4 implementation.
