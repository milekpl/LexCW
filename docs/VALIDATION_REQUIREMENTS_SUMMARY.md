# Validation Requirements Summary

## Executive Summary

I have completed a comprehensive analysis of the current validation system and documented all requirements for the centralized validation refactor. The analysis reveals **69 distinct validation rules** across 7 major categories, with varying implementation states and priorities.

## Key Findings

### Current State
- **Scattered Implementation**: Validation logic currently spread across 4+ model files
- **Inconsistent Coverage**: Some rules fully implemented, others partially or missing
- **Test Coverage**: Excellent - comprehensive test suite exists in `tests/test_validation_rules.py`
- **Mixed Priorities**: 23 critical rules, 49 warning-level rules, 28 informational
- **LIFT Schema Analysis**: Additional 33 advanced validation rules identified from LIFT 0.13 schema

### Validation Rule Categories

| Category | Rules | Implementation Status | Priority Distribution |
|----------|-------|----------------------|---------------------|
| **R1: Entry Level** | 8 rules | 6 implemented, 2 gaps | 5 critical, 3 warning |
| **R2: Sense Level** | 6 rules | All implemented | 3 critical, 3 warning |
| **R3: Notes & Multilingual** | 3 rules | 2 implemented, 1 gap | 0 critical, 3 warning |
| **R4: Pronunciation/IPA** | 5 rules | 3 implemented, 2 gaps | 2 critical, 3 warning |
| **R5: Relations & References** | 6 rules | 1 partial, 5 gaps | 3 critical, 3 warning |
| **R6: Part-of-Speech** | 4 rules | 2 partial, 2 gaps | 0 critical, 4 warning |
| **R7: Client-Side** | 4 rules | Partial implementation | 0 critical, 4 warning |
| **R8: LIFT Schema Advanced** | 33 rules | New (not implemented) | 10 critical, 30 warning/info |

**Total: 69 validation rules** → **Total: 102 validation rules**

### Implementation Gaps Identified

#### Critical Gaps (Must Address)

1. **Reference Integrity** (R5.1.x): No validation for entry/sense references
2. **Double Length Markers** (R4.2.2): Missing IPA sequence validation
3. **Unique Note Types** (R3.1.1): Logic exists but not implemented
4. **Media File Validation** (R8.1.x): No validation for audio/image file existence
5. **LIFT Schema Compliance** (R8.x): 33 new advanced validation rules identified

#### Architecture Issues

1. **Database Dependencies**: 8 rules require full dataset access
2. **LIFT Dependencies**: 7 rules need LIFT ranges/traits parsing  
3. **File System Dependencies**: 3 rules need file/resource access
4. **Client-Server Sync**: Validation logic duplicated, not centralized

## Recommended Implementation Approach

### Phase 1: Foundation (Priority)
1. **Create Central Rule Engine**: `services/validation_engine.py`
2. **Define Rule Configuration**: `validation_rules.json` (declarative format)
3. **Implement Self-Contained Rules**: 45 rules that don't need external data
4. **Preserve Test Compatibility**: All existing tests must pass

### Phase 2: Integration
1. **PySchematron Setup**: XML validation for LIFT compliance
2. **Database-Dependent Rules**: Reference integrity validation
3. **LIFT Range Integration**: Dynamic rule loading from LIFT data
4. **API Endpoints**: `/api/validation/*` for centralized validation

### Phase 3: Client-Side
1. **JavaScript Validation Engine**: Mirror server-side rules
2. **Real-time Feedback**: Inline validation with 500ms response time
3. **Form State Management**: Track changes and validation status
4. **Error Display**: Consistent, actionable error messages

### Phase 4: Migration & Cleanup
1. **Remove Model Validation**: Delete scattered validation logic
2. **Update Service Layer**: Route all validation through central engine
3. **Performance Optimization**: Caching and batch validation
4. **Documentation**: Update system architecture docs

## Success Metrics

- **Centralization**: 0% validation logic in model classes
- **Performance**: <500ms validation time for typical entries
- **Test Coverage**: 100% existing test compatibility + new LIFT schema tests
- **Extensibility**: New rules added via config, not code
- **Consistency**: Same validation logic client and server-side
- **LIFT Compliance**: Full support for LIFT 0.13 schema validation
- **Resource Integrity**: Media files and external references validated

## Files to Review

### Primary Documents

- **`CENTRALIZED_VALIDATION_REQUIREMENTS.md`**: Complete 102-rule specification
- **`tests/test_validation_rules.py`**: Comprehensive test suite (688 lines)
- **`refactor-schematron.md`**: Implementation roadmap and TDD approach

### Current Implementation

- **`app/models/entry.py`**: Lines 270-420 contain main validation logic
- **`app/models/sense.py`**: Basic sense validation
- **`app/static/js/entry-form.js`**: Client-side POS validation logic

### Configuration Targets

- **`validation_rules.json`**: (To be created) Central rule definitions
- **`schemas/lift_validation.sch`**: (To be created) Schematron schema
- **`services/validation_engine.py`**: (To be created) Core validation engine

## Next Steps

1. **Review Requirements**: Please review `CENTRALIZED_VALIDATION_REQUIREMENTS.md`
2. **Approve Approach**: Confirm the 4-phase implementation strategy
3. **Prioritize Rules**: Confirm critical vs. warning vs. informational priorities for new R8 rules
4. **Define Resource Validation**: Specify file system access patterns for media validation
5. **Begin Implementation**: Start with Phase 1 (central rule engine)

The requirements document now provides a complete roadmap for migrating from scattered validation logic to a centralized, declarative system that includes comprehensive LIFT schema compliance, media file validation, and advanced semantic validation rules while maintaining full backward compatibility and test coverage.
