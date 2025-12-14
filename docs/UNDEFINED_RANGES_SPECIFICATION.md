## Plan for Handling Undefined Traits and Relation Types in LIFT Import/Export

### Problem Summary
The analysis of the sample LIFT file reveals that SIL Fieldworks exports custom relation types and traits not defined in the standard LIFT ranges file:

- **Undefined Relation Type**: `_component-lexeme` (used for complex form relationships)
- **Undefined Traits**: 
  - `is-primary` (boolean, indicates primary component)
  - `complex-form-type` (values from "Complex Form Types" list: Compound, Derivative, etc.)
  - `hide-minor-entry` (boolean, controls entry visibility)
  - `variant-type` (values from "Variant Types" list: Free Variant, Spelling Variant, etc.)

These are hidden in the current app because the ranges system only recognizes defined ranges.

### Proposed Solution

#### 1. Storage Solution
Store undefined/custom ranges in PostgreSQL rather than extending the LIFT ranges file, to maintain separation between standard LIFT ranges and project-specific customizations.

**Database Schema**:
```sql
CREATE TABLE custom_ranges (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id),
    range_type VARCHAR(50), -- 'relation' or 'trait'
    range_name VARCHAR(255), -- e.g., 'complex-form-type'
    element_id VARCHAR(255), -- for relations: relation type, for traits: trait name
    element_label TEXT,
    element_description TEXT,
    parent_range VARCHAR(255), -- for hierarchical ranges
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE custom_range_values (
    id SERIAL PRIMARY KEY,
    custom_range_id INTEGER REFERENCES custom_ranges(id),
    value VARCHAR(255),
    label TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### 2. Import Process Updates
- When parsing LIFT files, identify undefined relation types and traits
- Automatically create entries in `custom_ranges` and `custom_range_values` tables
- Link values from `list.xml` where available (e.g., complex-form-type → Complex Form Types list)

#### 3. Ranges Editor Updates
- Load ranges from both the LIFT ranges file AND the custom_ranges table
- Allow editing of custom ranges with the same UI as standard ranges
- Save custom range changes to PostgreSQL
- Provide option to export custom ranges back to the LIFT ranges file for sharing

#### 4. Initial Project Setup
- For new projects, pre-populate `custom_ranges` with common SIL Fieldworks ranges:
  - `_component-lexeme` relation type
  - `complex-form-type`, `variant-type`, `is-primary`, `hide-minor-entry` traits
  - Values from corresponding lists in `list.xml`

#### 5. Export Compatibility
- When exporting LIFT files, include custom ranges in the output ranges file
- Ensure exported files are compatible with SIL Fieldworks

### Implementation Steps
1. Create database migration for custom ranges tables
2. Update LIFT import logic to detect and store undefined ranges
3. Modify ranges loading to merge file + database ranges
4. Update ranges editor UI to handle custom ranges
5. Add export functionality for custom ranges
6. Test with sample files to ensure compatibility

This approach ensures that SIL Fieldworks exports are fully supported while maintaining clean separation between standard and custom ranges.