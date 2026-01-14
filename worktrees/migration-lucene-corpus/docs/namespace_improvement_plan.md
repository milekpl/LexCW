# XML Namespace Handling Improvement Plan

## Problem Analysis

The current implementation has several namespace handling issues:

1. **Inconsistent XQuery patterns**: Uses `//*:entry` wildcards and `local-name()` workarounds
2. **Missing namespace declarations**: XQuery queries don't properly declare LIFT namespace
3. **Fallback mechanisms**: Parser has to try with/without namespaces due to inconsistency
4. **Performance impact**: `local-name()` and wildcard patterns are slower than proper namespace queries

## LIFT 0.13 Namespace Structure

From the RelaxNG schema, LIFT format doesn't actually define a default namespace. The schema uses:
- No default namespace declared
- Elements are in the null namespace
- The schema itself is for validation, not for namespace declaration

However, when LIFT files are created by tools like FieldWorks, they often include:
```xml
<lift version="0.13" producer="FieldWorks">
```

Some tools may add namespaces like:
```xml
<lift xmlns="http://fieldworks.sil.org/schemas/lift/0.13" version="0.13">
```

## Solution Strategy

### Phase 1: Namespace Detection and Normalization (Week 1)

1. **Create Namespace Detector**
   - Analyze XML to determine if LIFT namespace is declared
   - Handle both namespaced and non-namespaced LIFT files
   - Create utility to normalize namespace declarations

2. **Update Database Storage Strategy**
   - Store all LIFT data with consistent namespace declarations
   - Strip or add namespaces as needed during import
   - Ensure internal consistency

### Phase 2: XQuery Standardization (Week 1-2)

1. **Create XQuery Namespace Manager**
   - Centralized namespace declaration management
   - Standard XQuery prologues for all queries
   - Query builder utilities for common patterns

2. **Update All XQuery Patterns**
   - Replace `local-name()` with proper namespace queries
   - Replace `//*:entry` with declared namespace paths
   - Optimize for performance

### Phase 3: Parser Enhancement (Week 2)

1. **Enhance LIFT Parser**
   - Remove fallback mechanisms where possible
   - Use consistent namespace handling
   - Improve error reporting for namespace issues

2. **Update Element Tree Handling**
   - Proper namespace handling in ElementTree operations
   - Consistent namespace registration
   - Better namespace stripping/addition utilities

## Implementation Details

### 1. Namespace Detection Utility

```python
class LIFTNamespaceManager:
    """Manages LIFT namespace detection and normalization."""
    
    LIFT_NAMESPACE = "http://fieldworks.sil.org/schemas/lift/0.13"
    FLEX_NAMESPACE = "http://fieldworks.sil.org/schemas/flex/0.1"
    
    @classmethod
    def detect_namespaces(cls, xml_content: str) -> Dict[str, str]:
        """Detect namespaces used in LIFT XML."""
        
    @classmethod
    def normalize_lift_xml(cls, xml_content: str, target_namespace: Optional[str] = None) -> str:
        """Normalize LIFT XML to use consistent namespace."""
        
    @classmethod
    def get_xpath_with_namespace(cls, xpath: str, has_namespace: bool = True) -> str:
        """Convert XPath to use proper namespace declarations."""
```

### 2. XQuery Builder

```python
class XQueryBuilder:
    """Builder for LIFT-specific XQuery queries."""
    
    @staticmethod
    def get_prologue(has_lift_namespace: bool = False) -> str:
        """Get XQuery prologue with namespace declarations."""
        if has_lift_namespace:
            return """
            declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
            declare namespace flex = "http://fieldworks.sil.org/schemas/flex/0.1";
            """
        return ""
    
    @staticmethod
    def build_entry_query(entry_id: str, db_name: str, has_namespace: bool = False) -> str:
        """Build query to retrieve entry by ID."""
        prologue = XQueryBuilder.get_prologue(has_namespace)
        path = "lift:entry" if has_namespace else "entry"
        return f"""
        {prologue}
        for $entry in collection('{db_name}')///{path}[@id="{entry_id}"]
        return $entry
        """
```

### 3. Database Schema Strategy

**Option A: Store with LIFT namespace (Recommended)**
- All stored XML uses proper LIFT namespace
- Consistent internal representation
- Better XQuery performance
- Standard compliant

**Option B: Store without namespace**
- Simpler queries
- Smaller storage size
- May conflict with standard LIFT tools

**Decision: Use Option A** for better standards compliance and tool interoperability.

## Migration Plan

### Week 1: Infrastructure
1. Create `LIFTNamespaceManager` utility class
2. Create `XQueryBuilder` utility class  
3. Add namespace detection to LIFT parser
4. Create migration script for existing data

### Week 2: Query Updates
1. Update all XQuery patterns in `DictionaryService`
2. Update test queries to use proper namespaces
3. Remove `local-name()` workarounds
4. Update LIFT parser namespace handling

### Week 3: Testing and Validation
1. Comprehensive testing with both namespaced and non-namespaced LIFT files
2. Performance testing to ensure optimization
3. Integration testing with existing data
4. Update all test fixtures

### Week 4: Documentation and Cleanup
1. Update documentation with namespace handling details
2. Clean up deprecated fallback code
3. Add namespace validation to import process
4. Create troubleshooting guide for namespace issues

## Expected Benefits

1. **Performance**: 20-30% improvement in XQuery execution time
2. **Maintainability**: Cleaner, more understandable code
3. **Standards Compliance**: Better interoperability with LIFT tools
4. **Robustness**: Fewer edge cases and fallback mechanisms
5. **Debugging**: Clearer error messages for namespace issues

## Risk Mitigation

1. **Backward Compatibility**: Support both namespaced and non-namespaced files during transition
2. **Data Migration**: Comprehensive backup and rollback procedures
3. **Testing**: Extensive testing with real-world LIFT files
4. **Gradual Rollout**: Phase-by-phase implementation with validation at each step

## Success Metrics

1. All `local-name()` usage eliminated from XQuery
2. All tests passing with consistent namespace handling
3. Performance improvements measured and documented
4. Successful import/export of both namespaced and non-namespaced LIFT files
5. Zero regression in existing functionality
