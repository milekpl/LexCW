# Lexicographic Curation Workbench (LCW) Specification v2.0 - Final Streamlined

> **⚠️ ARCHITECTURAL EVOLUTION NOTICE**
> The architectural migration to **direct XML manipulation** has been successfully completed. BaseX is now the single source of truth for all LIFT entries, eliminating the dual-database architecture for entry data.

## 1. Introduction

### 1.1 Purpose and Philosophy

This document outlines the specifications for the **Lexicographic Curation Workbench (LCW)**, a Flask-based system designed as an AI-augmented, bulk-processing workbench for professional lexicographers. The LCW prioritizes efficient curation of machine-generated and query-based worksets over single-entry editing, with every feature designed for scalability and validated through a rigorous Test-Driven Development (TDD) cycle.

### 1.2 Background

The current workflow relies on SIL Fieldworks Explorer (Flex), which has become inadequate for managing a large lexicon containing over 153,000 entries. Performance issues and the need for advanced AI-augmented curation workflows necessitate moving to a dedicated, scalable solution with optimized operations for large datasets and bulk processing capabilities.

### 1.3 Project Scope

The LCW provides:

- A TDD-validated, responsive web interface for lexicographic curation
- A hybrid database architecture (BaseX + PostgreSQL) for optimal performance
- AI-augmented bulk processing and workbench-based curation workflows
- Comprehensive linguistic analysis and data enrichment tools
- Advanced import/export functionality with format-specific optimizations
- Complex semantic relation management and validation
- Extensive customization through profile-based field mapping
- Full LIFT format compatibility with round-trip validation
- **Dynamically loaded type/category options from LIFT RANGES file for complete linguistic coverage**

## 2. System Architecture

### 2.1 Overview - Hybrid Database Architecture

The LCW v2.0 employs a sophisticated hybrid database architecture optimized for both performance and semantic querying:

1. **Presentation Layer**: Flask-based responsive web application with TDD-validated components
2. **Business Logic Layer**: Python API with AI/ML integration and bulk processing capabilities
3. **Data Layer**: Hybrid database system combining BaseX (XML) and PostgreSQL (relational)

### 2.2 Technology Stack

#### 2.2.1 Core Technologies

- **Frontend**: Flask, JavaScript ES6+, Bootstrap 5 (responsive design), WebComponents
- **Backend**: Python 3.9+, FastAPI (async API), Celery (task queue)
- **Databases**:
  - BaseX 10+ (hierarchical XML storage for LIFT data)
  - PostgreSQL 14+ (relational analytics and indexing)
- **Testing**: pytest, Playwright, coverage.py (TDD enforcement)
- **AI/ML**: spaCy, transformers, scikit-learn

## 3. Core Features (Workbench-Driven)

### 3.1 Dynamic Range Management

#### 3.1.1 LIFT RANGES Integration

**Critical Requirement**: All type/category options throughout the application are dynamically loaded from the LIFT RANGES file, not hardcoded. This ensures:

- **Complete Linguistic Coverage**: All grammatical categories, relationship types, variant types, and other linguistic classifications from the LIFT RANGES file are available in the UI
- **Hierarchical Support**: Parent-child relationships between categories are preserved and displayed
- **Multilingual Labels**: Support for multiple language labels and abbreviations as defined in the LIFT RANGES
- **Extensibility**: New categories can be added to the LIFT RANGES file without code changes

#### 3.1.2 Dynamic Variant Types from LIFT Traits

**Critical Requirement**: Variant types are extracted from `<trait>` elements in the LIFT XML, not from the RANGES file. This ensures:

- **Real-World Usage**: Only variant types actually used in the data are displayed
- **Precise Categorization**: Variant types match actual data content, not predefined theoretical categories
- **Data-Driven UI**: The UI adapts to the actual data without requiring manual configuration

#### 3.1.3 Language Codes from Project Settings

All language dropdowns (vernacular, translation, etc.) now exclusively use language codes configured in the project settings database. This ensures:

- **Consistency**: Only languages explicitly configured for the project are available for selection
- **Reduced Errors**: Users cannot select languages that aren't configured for their project
- **Project Relevance**: UI is tailored to the specific language codes of the current project
- **Multi-Project Support**: Each project can define its own source and target languages in the database

#### 3.1.4 Pronunciation Language Restrictions

Pronunciation language is restricted to only "seh-fonipa" with no language selector exposed in the UI. This ensures:

- **IPA Standardization**: All phonetic transcriptions use the IPA standard for Sena
- **UI Simplification**: No language dropdown is shown for pronunciation fields
- **Consistency**: All pronunciation data uses the same language code
- **Validation**: Server-side validation enforces this restriction (validation rule R4.1.1)

### 3.2 Workbench Interfaces

#### 3.2.1 Query-Based Worksets

**Test-Driven Specification**: Each workset view is validated through comprehensive UI and API tests.

- **Dynamic Query Builder**: TDD-validated interface for creating complex entry filters using dynamic ranges
- **Workset Management**: Save, load, and share filtered entry collections. This includes saving the UI configuration of the workset, such as column visibility, sorting order, and other UI settings.
- **Bulk Operations**: Apply changes to hundreds or thousands of entries simultaneously
- **Progress Tracking**: Real-time feedback for long-running operations

#### 3.2.2 AI-Augmented Curation Workflows

- **Content Generation Workbench**:
  - Machine-generated example sentences with human approval workflow
  - Automated sense suggestions based on corpus analysis
  - Quality scoring and confidence metrics for all AI-generated content

- **Validation Workbench**:
  - Consistency checking across related entries
  - Pronunciation validation with IPA compliance testing
  - Cross-reference validation and orphan detection

### 3.2 Entry Management (Bulk-Optimized)

#### 3.2.1 Scalable Entry Operations

**TDD Requirements**: All operations handle 1000+ entries with <5 second response times.

- **Bulk CRUD Operations**: Create, read, update, and delete operations for entry collections
- **Atomic Transactions**: Ensure data consistency across large-scale changes
- **Change Tracking**: Comprehensive audit trails for all modifications
- **Rollback Capabilities**: Undo complex bulk operations safely

#### 3.2.2 Enhanced Semantic Relations

- **Graph-Based Visualization**: Interactive semantic network exploration
- **Bulk Relation Creation**: Establish relationships across entry worksets
- **Relation Validation**: Detect and resolve circular dependencies
- **Semantic Clustering**: AI-powered grouping of related concepts

#### 3.2.3 Advanced Grammatical Information

**Machine Learning Integration**: Trained models for automatic grammatical classification.

- **Automated POS Tagging**: ML-powered part-of-speech assignment
- **Morphological Analysis**: Automated inflection and derivation tracking
- **Cross-Linguistic Mapping**: Support for multiple grammatical frameworks
- **Countability Classification**:
  - Trained neural models for noun countability prediction
  - Batch processing for existing entries
  - Confidence scoring and human validation workflows

### 3.3 Data Import/Export

#### 3.3.1 Import Capabilities

- Import from LIFT format
- Import from custom YAML format
- Import from JSON format
- Import from SFM format
- Validation of imported data
- Circular reference detection and resolution

#### 3.3.2 Export Capabilities

- **Kindle Dictionary Export**:
  - Generation of Kindle-compatible dictionary format (.opf, .mobi)
  - Utilization of the customizable CSS mapping (simplified for Kindle) to ensure consistent styling between the UI and the export.
  - Support for Kindle indexing features (inflection forms)
  - Custom formatting and styling options
  - Automatic generation of front and back matter
  - Pronunciation guides using IPA notation
  - Cover image and metadata customization

- **Flutter Mobile App Export**:
  - SQLite database generation optimized for mobile performance
  - Compression of data for smaller app footprint
  - Indexing structure for fast mobile search
  - Support for offline usage and incremental updates
  - Schema designed for Flutter application compatibility

- **Standard Export Formats**:
  - Export to LIFT format for interoperability
  - Export to custom formats (YAML, JSON, TSV)
  - Selective export based on criteria
  - Export templates for different purposes

#### 3.3.3 Batch Processing

- Scheduled batch operations
- Progress tracking for long-running operations
- Error handling and reporting
- Automated validation before and after processing

### 3.4 Analysis Tools

#### 3.4.1 Duplicate Detection

- Multi-criteria duplicate finding
- Configurable similarity thresholds
- Batch merge operations

#### 3.4.2 Statistical Analysis

- Frequency analysis
- Anomaly detection
- Distribution reports
- Completeness assessment

### 3.5 Entry Form Management

#### 3.5.1 Enhanced Pronunciation Integration

The LCW provides comprehensive support for pronunciation management with full audio integration:

- **Audio Upload and Management**:
  - Direct audio file upload for IPA transcriptions
  - Support for common audio formats (MP3, WAV, OGG)
  - Audio validation and conversion services
  - Inline audio preview during form editing
  - One-click audio removal and replacement

- **IPA Transcription Support**:
  - Unicode IPA character display and input
  - Integration with pronunciation audio files
  - Multiple pronunciation forms per entry
  - Default pronunciation marking
  - Language-specific pronunciation handling (seh-fonipa)

#### 3.5.2 Part-of-Speech (POS) Intelligence

The LCW implements intelligent part-of-speech management with automatic inheritance and validation:

- **Automatic POS Inheritance**:
  - Entry-level grammatical information is automatically inherited from senses
  - Inheritance occurs only when all senses share the same part-of-speech
  - Preserves explicit user assignments over automatic inheritance
  - Supports both string and structured grammatical information formats

- **Intelligent Defaults**:
  - First pronunciation is automatically marked as default
  - Empty entries inherit POS from first sense if all senses agree
  - Graceful handling of mixed POS scenarios with clear user guidance

#### 3.5.3 Form Validation and Error Handling

- **Client-Side Validation**:
  - Real-time field validation with immediate feedback
  - Format checking for IPA transcriptions and audio files
  - Consistency checks between related fields

- **Server-Side Validation**:
  - Comprehensive data validation before database persistence
  - Cross-field dependency validation (entry-sense POS consistency)
  - Meaningful error messages with specific guidance for resolution

- **Critical Validation Policy: Invalid Entries Must Always Be Editable**:
  - **Entry Loading**: All entries, regardless of validation state, can be loaded for viewing and editing
  - **Non-Blocking Validation**: Validation errors are displayed as guidance, never as editing blockers
  - **Lexicographer Access**: Ensures lexicographers can always fix broken/invalid entries
  - **Validation Display**: Critical errors, warnings, and info messages shown as guidance in UI
  - **Search Inclusion**: Invalid entries appear in search results and entry lists

### 3.6 Display Profiles and CSS Mapping

Complete display profile system for customizable entry rendering.

The LCW implements a sophisticated CSS-based display profile system that allows lexicographers to customize how dictionary entries are rendered without modifying code. This feature enables project-specific formatting conventions while maintaining data integrity.

**Key Features**:

- **Profile Management**: Create, edit, and manage multiple display profiles
- **CSS Mapping**: Map LIFT XML elements to CSS classes and styles
- **Field Visibility Control**: Show/hide specific fields per profile
- **Language Filtering**: Control which language variants are displayed
- **Preview Mode**: Real-time preview of formatting changes
- **Export Integration**: Profiles can be applied to export formats

For detailed CSS mapping configuration, see Section 7.5.

## 4. Test-Driven Development Framework

### 4.1 TDD Methodology

#### 4.1.1 Red-Green-Refactor Cycle

**Mandatory Process**: Every feature follows the complete TDD cycle:

1. **Red Phase**: Write failing test cases that specify the desired behavior
2. **Green Phase**: Implement minimal code to make tests pass
3. **Refactor Phase**: Improve code quality while maintaining test coverage

#### 4.1.2 Test Coverage Requirements

- **Minimum Coverage**: 90% line coverage for all production code
- **Critical Path Coverage**: 100% coverage for data integrity operations
- **UI Testing**: Selenium-based testing for all user workflows
- **API Testing**: Comprehensive endpoint testing with edge cases

### 4.2 Quality Assurance Framework

#### 4.2.1 Automated Quality Gates

- **Pre-commit Hooks**: Code formatting and basic linting
- **CI Pipeline**: Automated testing on all pull requests
- **Code Review**: Mandatory peer review for all changes
- **Security Scanning**: Automated vulnerability detection

#### 4.2.2 Data Integrity Validation

**LIFT Format Compliance**:

- XML schema validation
- Round-trip testing (import → modify → export)
- Data loss prevention testing

## 5. Non-Functional Requirements

### 5.1 Performance Requirements

#### 5.1.1 Response Time Targets

- **Single Entry Operations**: <500ms response time
- **Bulk Operations (1000+ entries)**: <5 seconds response time
- **Search Operations**: <1 second for complex queries
- **Export Operations**: <30 seconds for full dictionary export

#### 5.1.2 Scalability Requirements

- **Data Volume**: Support for 300,000+ entries without performance degradation
- **Concurrent Users**: Handle 50+ simultaneous users
- **Memory Usage**: <4GB RAM for typical operations
- **Storage**: Efficient use of disk space with compression

### 5.4 Reliability

#### 5.4.1 Backup and Rollback

- **Comprehensive Backup System**:
  - Automated incremental backups of the entire database
  - Configurable backup schedule (hourly, daily, weekly)
  - Backup versioning with retention policies
  - Compression and encryption options for backups
  - External storage support (cloud, network drives)

- **Fine-grained Rollback Capabilities**:
  - Transaction-level rollback for individual operations
  - Session-level rollback for user editing sessions
  - Point-in-time recovery options
  - Selective rollback for specific entries or changes
  - Visual diff and merge tools for resolving conflicts

- **Audit and Recovery**:
  - Complete audit trail of all changes
  - User activity logging
  - Change history visualization
  - Disaster recovery procedures
  - Testing and verification of backup integrity

## 6. Database Design

### 6.1 BaseX Configuration

BaseX is an XML database management system optimized for storing, querying, and managing hierarchical XML data, making it ideal for LIFT format dictionaries. The configuration includes:

- **Optimized XML Indexing**:
  - Value indexes for fast text-based searches
  - Full-text indexes with custom tokenization for linguistic searches
  - Path indexes for efficient XPath/XQuery performance
  - Custom indexes for frequently accessed elements (e.g., headwords, parts of speech)

- **Performance Tuning**:
  - Database splitting by initial letters to improve query performance on large datasets
  - Memory allocation optimization for handling 200,000+ entries
  - Query compression settings to reduce storage requirements while maintaining performance

### 6.2 LIFT Schema Integration

- Support for standard LIFT schema
- Custom extensions for project-specific needs
- Schema validation for data integrity
- Automated validation against the LIFT schema during import and update operations

### 6.3 Caching Strategy

- In-memory caching for frequently accessed data
- Query result caching
- Cache invalidation strategies
- Tiered caching architecture (memory, disk, distributed)

## 7. User Interface Design

### 7.2 Entry Editor

- **Formatted Dictionary Layout**: The primary view for an entry will be a formatted, dictionary-style layout, not a raw data-entry form. This allows lexicographers to review entries in a natural, intuitive format, making it easier to spot errors and inconsistencies.
- **In-Place Editing**: Editing will be performed in-place or through minimal, context-sensitive overlays that appear on-click, preserving the dictionary-like view during curation.
- **Customizable CSS Mapping**: The layout and styling will be controlled by a customizable mapping from LIFT XML elements and attributes to CSS styles. This allows for project-specific visual conventions.
- Inline validation of entries with real-time feedback.
- Auto-save functionality to prevent data loss.
- Side-by-side comparison view for resolving duplicates or reviewing changes.

#### 7.2.1 UI/UX Standards and Consistency

**Homograph Number Field**:

- Only displays when entry has an actual homograph number
- No placeholder text for entries without homograph numbers
- Reduces visual clutter and confusion for non-homograph entries

**Tooltip Icon Standardization**:

- Primary tooltips use `fa-info-circle` icons consistently
- `fa-question-circle` reserved only for warning/error contexts in alerts
- Improved visual hierarchy and user experience

#### 7.2.2 Detailed Field Logic and Behavior

The entry editor implements the following logic to ensure data consistency and improve user experience:

- **Grammatical Category Inheritance**:
  - The entry-level grammatical category (Part of Speech) shall be automatically derived from the categories of its senses.
  - If all senses share the same grammatical category, the entry-level field will be automatically set to this value.
  - If there is a discrepancy in grammatical categories among the senses, the entry-level field will display a clear error message (e.g., highlighted in red) to prompt the lexicographer for manual resolution.

- **Obligatory Fields**
  - The system will not require any definitions or senses to be present in entries that are marked AS VARIANTS. If any content exists in such entries, there should be a warning message there that it won't be displayed.
  - Part of speech fields are _NOT_ obligatory. They can remain empty.

- **Automatic Morph Type Classification (for new entries)**:
  - The morphological type (`morph-type`) for new entries shall be automatically determined based on the headword's form:
    - Contains whitespace: `phrase`
    - Ends with a hyphen (`-`): `prefix`
    - Starts with a hyphen (`-`): `suffix`
    - Starts and ends with a hyphen (`-`): `infix`
    - Default: `stem`
  - For existing entries, the `morph-type` value from the LIFT data (`trait` element) will be preserved and displayed.

- **Homograph Number Handling**:
  - Homograph numbers shall be displayed within the entry form as subscripts.
  - Homograph numbers are extracted from and stored to the LIFT `order` attribute per LIFT specification standards.
  - The system must enforce uniqueness and automatically assign the next available homograph number upon the creation of a new entry that is a homograph of an existing one.
  - This field is typically read-only to prevent manual duplication errors.
  - In entry lists, homograph numbers appear as subscripts after the lexical unit (e.g., "bank₁", "bank₂").

- **Comprehensive Field Rendering**:
  - **Notes**: All notes must be displayed with their corresponding language attribute.
  - **Custom Fields**: All custom fields defined within the `<field>` tag in the LIFT data must be rendered and editable in the entry form.
  - **Example Translation Types**: The form must allow specifying a `type` for example translations (e.g., 'literal', 'free'), populated from the corresponding LIFT range.

- **Enhanced Relation Editor**:
  - The interface for adding/editing lexical relations must not require the user to know or enter an entry's GUID.
  - It must feature a progressive search component that allows the user to search for entries by their lexical form.
  - The search results will be displayed as a selectable list of matching entries and/or senses, simplifying the linking process.

- **Customizable Field Visibility**:
  - Users must have control over the visibility of fields within the entry editor. Each field or field group should support three visibility states:
    1.  **Always Visible**: The field is always displayed.
    2.  **Hide When Empty**: The field is automatically hidden if it contains no data, reducing clutter.
    3.  **Always Hidden**: The field is hidden by default, but can be toggled into view by the user via a UI control (e.g., a settings menu or a small handle next to the field group).

- **Real-time Pronunciation Validation**:
  - The pronunciation field must perform real-time validation against a set of admissible IPA characters and sequences.
  - This set of rules shall be configurable per dictionary, based on the definitions in Section 15.3.
  - Any characters or sequences that violate the rules must be visually marked as errors (e.g., underlined in red) to provide immediate feedback to the lexicographer.

### 7.1 UI Optimization and Accessibility

#### 7.1.1 Tooltip-Based Help System

The entry form UI has been optimized to use a compact, accessible tooltip-based help system that significantly reduces screen space usage while preserving all instructional content. This implementation follows modern UX best practices and accessibility guidelines.

**Key Features Implemented**:

- **Compact Tooltips**: Replaced large `alert alert-info` boxes with compact question mark icons that reveal help content on hover/focus
- **Accessibility Compliance**:
  - Full keyboard navigation support
  - Screen reader compatibility with proper ARIA labels
  - High contrast visual indicators
- **Responsive Design**: Tooltips adapt to screen size and positioning constraints
- **Content Preservation**: All original help text maintained with enhanced formatting using HTML markup
- **Dynamic Content Support**: JavaScript initialization ensures tooltips work with dynamically generated form elements

### 7.5 CSS Mapping for Display and Export

To ensure a consistent and customizable presentation of dictionary entries, the system implements a powerful mapping between LIFT XML elements/attributes and CSS styles. This mechanism is central to both the in-application entry view and various export formats.

- **Mapping Configuration**: A dedicated configuration interface will allow administrators to define rules that map specific LIFT elements (e.g., `lexical-unit`, `sense`, `definition`) and their attributes (e.g., `lang`) to CSS classes or inline styles.
- **UI Rendering**: The entry editor uses this mapping to render the dictionary-style view, transforming the underlying LIFT XML into formatted HTML for display.
- **Export Styling**: The same mapping is applied during export to HTML, ensuring that the exported dictionary is visually consistent with the application's view. For Kindle export, a simplified version of the CSS is used to comply with Kindle's formatting constraints while maintaining a clean, readable layout.

## 8. Workbench-Oriented API Design

### 8.1 Workset Management APIs

#### 8.1.1 Query-Based Workset Endpoints

**TDD Requirement**: All endpoints handle 1000+ entries with response times <5 seconds.

- **Workset Creation and Management**:
  - `POST /api/worksets` - Create filtered workset from query
  - `GET /api/worksets/{id}` - Retrieve workset with pagination
  - `PUT /api/worksets/{id}/query` - Update workset query criteria
  - `DELETE /api/worksets/{id}` - Remove workset

- **Bulk Operations on Worksets**:
  - `POST /api/worksets/{id}/bulk-update` - Apply changes to entire workset
  - `POST /api/worksets/{id}/bulk-validate` - Validate all entries in workset
  - `POST /api/worksets/{id}/ai-process` - Apply AI processing to workset
  - `GET /api/worksets/{id}/progress` - Track bulk operation progress

#### 8.1.2 Advanced Filtering and Querying

- **Dynamic Query Builder**:
  - `POST /api/queries/build` - Construct complex multi-criteria queries
  - `GET /api/queries/templates` - Retrieve predefined query templates
  - `POST /api/queries/validate` - Validate query syntax and performance

- **Semantic Querying**:
  - `POST /api/queries/semantic` - Semantic similarity-based filtering
  - `POST /api/queries/ml-classify` - ML-powered classification queries
  - `GET /api/queries/suggestions` - AI-suggested query refinements

### 8.2 AI-Augmented Content APIs

#### 8.2.1 Content Generation Endpoints

- **AI Content Generation**:
  - `POST /api/ai/generate-examples` - Generate example sentences for entries
  - `POST /api/ai/suggest-senses` - AI-powered sense suggestions
  - `POST /api/ai/enhance-definitions` - Definition improvement recommendations
  - `POST /api/ai/pronunciation-generate` - Automated IPA generation

- **Quality Assessment**:
  - `POST /api/ai/quality-score` - Score content quality and consistency
  - `POST /api/ai/validate-content` - AI-powered content validation
  - `GET /api/ai/confidence-metrics` - Retrieve confidence scores for AI content

#### 8.2.2 Batch Processing Pipeline

- **Task Management**:
  - `POST /api/tasks/submit` - Submit large-scale processing jobs
  - `GET /api/tasks/{id}/status` - Check task progress and results
  - `POST /api/tasks/{id}/approve` - Approve AI-generated content
  - `DELETE /api/tasks/{id}` - Cancel running tasks

## 10. Migration Strategy

### 10.1 Data Migration

- Incremental migration from Flex
- Data validation during migration
- Rollback capabilities

## 12. Future Enhancements

### 12.1 Collaboration Features

- Multi-user editing
- Commenting and discussion
- Workflow management

### 12.2 Advanced Analytics

- Machine learning for anomaly detection
- Pattern recognition in language data
- Automatic relation suggestion

### 12.3 Publishing

- Additional publishing formats beyond Kindle and Flutter
- Print-ready PDF output
- Web dictionary generation
- Integration with third-party publishing platforms

## 15.3 IPA Character Sets and Validation Rules

The following defines the admissible IPA characters and sequences for pronunciation validation:

#### 15.3.1 Primary IPA Symbols

- Vowels: `ɑ æ ɒ ə ɜ ɪ i ʊ u ʌ e ɛ o ɔ`
- Length markers: `ː`
- Consonants: `b d f g h j k l m n p r s t v w z ð θ ŋ ʃ ʒ tʃ dʒ`
- Stress markers: `ˈ ˌ`
- Special symbols: `ᵻ`

#### 15.3.2 Valid Diphthongs

- `eɪ aɪ ɔɪ əʊ aʊ ɪə eə ʊə oʊ`

#### 15.3.3 Invalid Character Sequences

- Double stress markers: `ˈˈ ˌˌ ˈˌ ˌˈ`
- Invalid consonant clusters: [list to be compiled from data]
- Other phonotactic constraints specific to English

#### 15.3.4 Dialect-Specific Rules

- British English specific patterns
- American English specific patterns
- Allowable dialectal variations

## 17. LCW v2.0 Architecture Summary

### 17.1 Paradigm Shift: From Single-Entry to Workbench-Driven

The LCW v2.0 represents a fundamental shift from traditional single-entry editing to a workbench-oriented, AI-augmented curation system:

#### 17.1.1 Key Architectural Innovations

**Hybrid Database Architecture**:

- BaseX for hierarchical XML storage (LIFT format preservation)
- PostgreSQL for analytical and relational data
- Unified repository pattern for seamless data access

**Workbench-Centered Design**:

- Query-driven entry collections replacing manual entry browsing
- Bulk operations as primary workflow (not secondary)
- AI-assisted curation workflows with human oversight

**Test-Driven Development Framework**:

- Mandatory 90%+ test coverage for all features
- Red-Green-Refactor cycle enforcement
- Performance benchmarks as acceptance criteria

## 18. Development Roadmap and Implementation Status

### 18.1 Current Implementation Status

Based on the existing codebase analysis, the following features have been implemented:

#### **COMPLETED FEATURES**

**Core Infrastructure (Foundation)**:

- Flask application structure with blueprints
- BaseX database connector with XQuery support
- Basic LIFT format parsing and XML handling
- Entry, Sense, Example, and Pronunciation models
- Dependency injection framework (injector)
- Basic error handling and validation framework
- Test infrastructure with pytest
- Development environment setup (.env, requirements.txt)

**Basic Dictionary Operations**:

- Entry CRUD operations (Create, Read, Update, Delete)
- Search functionality with pagination
- Basic entry display with formatted dictionary layout
- LIFT format import/export capabilities
- Basic grammatical information parsing
- Namespace handling for LIFT XML elements
- **User Management System** - Complete authentication and authorization framework
- **Security and Authentication** - Role-based access control with project permissions
- **Activity Logging and Audit Trails** - Comprehensive user action tracking
- **Message/Notification System** - Entry-level discussions and user notifications
- **Project Member Management** - ADMIN/MEMBER/VIEWER roles with fine-grained permissions

**Web Interface**:

- Dashboard with basic statistics
- Entry browsing and search interface
- Individual entry view and editing
- Search results display with pagination
- Basic responsive design framework
- **User Authentication UI** - Login, registration, profile pages with Bootstrap 5

**Export Capabilities**:

- Kindle dictionary export (.opf/.mobi format)
- SQLite export for Flutter mobile apps
- LIFT format export for interoperability

**Testing Framework**:

- Unit tests for core models and services
- Integration tests for database operations
- Search functionality tests
- Basic API endpoint tests
- Test fixtures and data management
- **User Management Tests** - Comprehensive test suite for authentication and authorization
- **Security Tests** - Authentication bypass attempts and permission enforcement
- **API Integration Tests** - All user management endpoints tested

### 18.2 User Management System Implementation Status

### 18.2.1 Complete Implementation

The User Management and Authentication System has been **fully implemented** as a core production feature, transforming LCW from single-user to multi-user collaborative platform.

#### Core Features Delivered

- **Authentication Framework**: Session-based auth with PBKDF2-SHA256 password security
- **Role-Based Access Control**: Hierarchical permissions (System Admin > Project Admin > Member > Viewer)
- **Project-Based Authorization**: Users can belong to multiple projects with different roles per project
- **Complete REST APIs**: 20+ endpoints for auth, users, messages, project management
- **Web UI Integration**: Login, registration, profile pages with Bootstrap 5 styling
- **Activity Logging**: Comprehensive audit trail for all user actions
- **Entry Messaging**: Threaded discussions on dictionary entries with notifications
- **Database Migration**: All tables created with proper relationships and indexing

#### Database Schema Implementation

```sql
-- Enhanced User Model
users (id, username, email, password_hash, first_name, last_name,
       is_admin, is_active, avatar_url, bio, preferences, timestamps)

-- Project Membership
project_roles (id, user_id, project_id, role, timestamps)

-- Activity Tracking
activity_logs (id, user_id, action, resource_type, details, ip_address, timestamps)

-- Entry Messaging
messages (id, entry_id, user_id, content, thread, read_status, timestamps)

-- User Notifications
notifications (id, user_id, title, message, type, read_status, timestamps)
```

#### Technical Implementation

- **Services**: AuthenticationService, UserManagementService, MessageService
- **Decorators**: @login_required, @admin_required, @role_required, @project_access_required
- **API Blueprints**: auth_api, users_api, messages_api, project_members_api
- **Web Routes**: Complete authentication workflow with form validation
- **Security**: CSRF protection, SQL injection prevention, input validation

### 18.2.2 Implementation Roadmap by Priority

**PHASE 2: Workbench Features** (Most completed)

**Week 5-6: Query Builder and Worksets**

- Dynamic Query Builder
- Project Language Settings
- Enhanced Entry Editing UI
- Dynamic Range Management
- Workset Management APIs

**Week 7-8: Enhanced Entry Editing UI**

- LIFT-Compliant Entry Editing Interface
- Pronunciation Display and LIFT Ranges Integration
- Audio File Upload System
- Field Rendering & Usability

**Week 9-10: CSS Mapping System**

- CSS Mapping Configuration
- Enhanced Entry Display

**Week 11-12: Search and Analysis Enhancement**

- Advanced Search Features
- Analysis Tools

**PHASE 3: AI Integration** (High priority - next focus)
**Week 13-14: AI Infrastructure**

- LLM Integration Framework
- Content Generation Pipeline

**Week 15-16: Machine Learning Models**

- POS Tagging Integration
- Pronunciation Systems

**Week 17-18: AI-Augmented Workflows**

- Content Review Workbench
- Quality Control Automation

**Week 19-20: Advanced Linguistic Analysis**

- Semantic Relationship Management
- Example-Sense Association

**PHASE 4: Production Features** (Medium priority)
**Week 21-22: Security and Authentication** ✅ **COMPLETED**

- ✅ **User Management System** - Full implementation with comprehensive authentication and authorization
- ✅ **Security Framework** - Session-based auth with role-based access control
- ✅ **Database Migration** - All user management tables successfully created and populated
- ✅ **Web UI Integration** - Login, registration, profile pages with Bootstrap 5
- ✅ **REST APIs** - 20+ endpoints for authentication, users, messages, project management
- ✅ **Activity Logging** - Complete audit trail system for all user actions
- ✅ **Project-Based Access Control** - ADMIN/MEMBER/VIEWER roles with fine-grained permissions

**Week 23-24: Enhanced Export System**

- Export Enhancement
- Publication Workflows

**Week 25-26: Collaboration Features**

- Multi-user Editing
- Project Management

## 19. PostgreSQL Integration: Status - Complete

PostgreSQL integration has been successfully completed with:

- PostgreSQL connector implemented with strict typing (`app/database/postgresql_connector.py`)
- Word sketch models and service implemented (`app/models/word_sketch.py`, `app/services/word_sketch_service.py`)
- Comprehensive TDD test suite with 12 passing tests (`tests/test_word_sketch_integration.py`)
- SUBTLEX frequency norms integration
- Sentence-aligned corpus processing with linguistic caching
- LogDice score calculation for collocation strength
- Sketch grammar pattern matching system

**Architecture Overview**:

- **BaseX**: Primary LIFT XML storage (dictionary structure integrity)
- **PostgreSQL**: Advanced analytics, word sketches, parallel corpus, SUBTLEX norms
- **Word Sketch Engine**: Grammatically enriched collocations using logDice scoring
- **Sentence-Aligned Optimization**: Leverage pre-aligned corpus for efficiency

## 20. User Management System - Complete Implementation

### 20.1 Overview

The User Management and Authentication System has been **fully implemented** as a core production feature, transforming LCW from single-user to multi-user collaborative platform with enterprise-grade security.

### 20.2 Implemented Features

#### 20.2.1 Authentication Framework

- **Session-Based Authentication**: Flask session management with secure cookie handling
- **Password Security**: PBKDF2-SHA256 hashing with salt rounds
- **Role-Based Access Control**: Hierarchical permissions (System Admin > Project Admin > Member > Viewer)
- **Project-Based Authorization**: Users can belong to multiple projects with different roles per project

#### 20.2.2 User Management System

- **Complete REST APIs**: 20+ endpoints for auth, users, messages, project management
- **Web UI Integration**: Login, registration, profile pages with Bootstrap 5 styling
- **Activity Logging**: Comprehensive audit trail for all user actions
- **Entry Messaging**: Threaded discussions on dictionary entries with notifications
- **Database Migration**: All tables created with proper relationships and indexing

#### 20.2.3 Database Schema

```sql
-- Enhanced User Model
users (id, username, email, password_hash, first_name, last_name,
       is_admin, is_active, avatar_url, bio, preferences, timestamps)

-- Project Membership
project_roles (id, user_id, project_id, role, timestamps)

-- Activity Tracking
activity_logs (id, user_id, action, resource_type, details, ip_address, timestamps)

-- Entry Messaging
messages (id, entry_id, user_id, content, thread, read_status, timestamps)

-- User Notifications
notifications (id, user_id, title, message, type, read_status, timestamps)
```

#### 20.2.4 Files Created

- `app/models/user_models.py` (170 lines) - User management models
- `app/services/auth_service.py` (380 lines) - Authentication business logic
- `app/services/user_service.py` (310 lines) - User management operations
- `app/services/message_service.py` (290 lines) - Messaging system
- `app/utils/auth_decorators.py` (180 lines) - Authorization decorators
- `app/api/auth_api.py` (230 lines) - Authentication REST API
- `app/api/users_api.py` (240 lines) - User management API
- `app/api/messages_api.py` (290 lines) - Messaging API
- `app/api/project_members_api.py` (230 lines) - Project membership API
- `app/routes/auth_routes.py` (new) - Web authentication routes
- `app/templates/auth/login.html` (new) - Login page template
- `app/templates/auth/register.html` (new) - Registration template
- `app/templates/auth/profile.html` (new) - User profile template
- `migrations/add_user_management_system.py` (410 lines) - Database migration

## 21. Namespace and XQuery Fixes (Completed)

## 21. Comprehensive LIFT Ranges Support (Complete)
