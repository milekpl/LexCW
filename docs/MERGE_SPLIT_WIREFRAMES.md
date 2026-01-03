# Merge/Split Operations Wireframes and Component Diagrams

## 🎨 Wireframes

### 1. Entries List with Merge/Split Actions

```mermaid
graph TD
    A[Entries List Table] --> B[Headword: Clickable Link]
    A --> C[POS: Badge]
    A --> D[Senses: Count]
    A --> E[Examples: Count]
    A --> F[Date: Formatted]
    A --> G[Actions: Button Group]

    G --> G1[Edit: fas fa-edit]
    G --> G2[Merge: fas fa-code-merge]
    G --> G3[Split: fas fa-code-branch]
    G --> G4[Delete: fas fa-trash]

    style G2 fill:#0d6efd,color:white
    style G3 fill:#198754,color:white
```

### 2. Merge Entries Flow - Entry Search Dialog

```mermaid
graph TD
    A[Merge Entry Search Dialog] --> B[Modal Header: Select Target Entry]
    A --> C[Search Input with Button]
    A --> D[Search Results List]
    A --> E[Info Message]
    A --> F[Action Buttons]

    C --> C1[Autocomplete Input]
    C --> C2[Search Button]

    D --> D1[Entry 1: match result]
    D --> D2[Entry 2: match result]
    D --> D3[Entry 3: match result]

    F --> F1[Cancel Button]
    F --> F2[Continue Button]

    style A fill:#f8f9fa,stroke:#dee2e6
    style B fill:#0d6efd,color:white
    style F2 fill:#0d6efd,color:white
```

### 3. Merge Entries Flow - Sense Selection Dialog

```mermaid
graph TD
    A[Sense Selection Dialog] --> B[Header: Select Senses to Merge]
    A --> C[Select All Checkbox]
    A --> D[Sense List with Checkboxes]
    A --> E[Conflict Resolution Options]
    A --> F[Action Buttons]

    D --> D1[Sense 1: Primary meaning]
    D --> D2[Sense 2: Secondary meaning]
    D --> D3[Sense 3: Tertiary meaning]

    E --> E1[Rename conflicting senses]
    E --> E2[Skip conflicting senses]
    E --> E3[Overwrite existing senses]

    F --> F1[Cancel Button]
    F --> F2[Merge Entries Button]

    style A fill:#f8f9fa,stroke:#dee2e6
    style B fill:#0d6efd,color:white
    style F2 fill:#0d6efd,color:white
```

### 4. Split Entry Dialog

```mermaid
graph TD
    A[Split Entry Dialog] --> B[Header: Split Entry]
    A --> C[New Entry Lexical Unit Input]
    A --> D[Part of Speech Select]
    A --> E[Select All Senses Checkbox]
    A --> F[Sense List with Checkboxes]
    A --> G[Action Buttons]

    F --> F1[Sense 1: Primary meaning]
    F --> F2[Sense 2: Secondary meaning]

    G --> G1[Cancel Button]
    G --> G2[Split Entry Button]

    style A fill:#f8f9fa,stroke:#dee2e6
    style B fill:#198754,color:white
    style G2 fill:#198754,color:white
```

### 5. Merge Senses Dialog

```mermaid
graph TD
    A[Merge Senses Dialog] --> B[Header: Merge Senses]
    A --> C[Target Sense Select]
    A --> D[Source Senses with Checkboxes]
    A --> E[Merge Strategy Options]
    A --> F[Action Buttons]

    C --> C1[Select target sense dropdown]

    D --> D1[Source Sense 1]
    D --> D2[Source Sense 2]

    E --> E1[Combine all content]
    E --> E2[Keep target sense]
    E --> E3[Keep source sense]

    F --> F1[Cancel Button]
    F --> F2[Merge Senses Button]

    style A fill:#f8f9fa,stroke:#dee2e6
    style B fill:#0dcaf0,color:white
    style F2 fill:#0dcaf0,color:white
```

## 🔧 Component Architecture

### 1. Action Button Component

```mermaid
classDiagram
    class ActionButton {
        +icon: string
        +label: string
        +tooltip: string
        +onClick: function
        +disabled: boolean
        +color: string
        +render()
        +handleClick()
    }

    class MergeButton {
        +extends ActionButton
        +icon: "fa-code-merge"
        +color: "primary"
        +onClick: openMergeDialog()
    }

    class SplitButton {
        +extends ActionButton
        +icon: "fa-code-branch"
        +color: "success"
        +onClick: openSplitDialog()
    }

    ActionButton <|-- MergeButton
    ActionButton <|-- SplitButton
```

### 2. Modal Dialog Component

```mermaid
classDiagram
    class ModalDialog {
        +title: string
        +size: string
        +show: boolean
        +onClose: function
        +onConfirm: function
        +renderHeader()
        +renderBody()
        +renderFooter()
        +show()
        +hide()
    }

    class EntrySearchModal {
        +extends ModalDialog
        +searchQuery: string
        +searchResults: array
        +onSelect: function
        +handleSearch()
        +renderResults()
    }

    class SenseSelectionModal {
        +extends ModalDialog
        +senses: array
        +selectedSenses: array
        +conflictResolution: string
        +toggleSelectAll()
        +toggleSense()
        +updateConflictResolution()
    }

    ModalDialog <|-- EntrySearchModal
    ModalDialog <|-- SenseSelectionModal
```

### 3. Sense List Component

```mermaid
classDiagram
    class SenseList {
        +senses: array
        +selectedSenses: array
        +showCheckboxes: boolean
        +onSelect: function
        +renderSense()
        +toggleSense()
        +selectAll()
        +deselectAll()
    }

    class SenseItem {
        +id: string
        +gloss: string
        +definition: string
        +exampleCount: number
        +selected: boolean
        +render()
    }

    SenseList "1" *-- "0..*" SenseItem
```

### 4. Conflict Resolution Component

```mermaid
classDiagram
    class ConflictResolution {
        +strategies: array
        +selectedStrategy: string
        +onChange: function
        +renderStrategy()
        +selectStrategy()
    }

    class ConflictStrategy {
        +id: string
        +label: string
        +description: string
        +icon: string
        +render()
    }

    ConflictResolution "1" *-- "0..*" ConflictStrategy
```

## 📊 State Management Diagram

```mermaid
stateDiagram-v2
    [*] --> Idle
    Idle --> EntrySearch: User clicks merge button
    EntrySearch --> SenseSelection: User selects target entry
    SenseSelection --> Processing: User confirms selection
    Processing --> Success: Operation succeeds
    Processing --> Error: Operation fails
    Success --> Idle: User dismisses success
    Error --> Idle: User dismisses error
    Error --> SenseSelection: User tries again

    state EntrySearch {
        [*] --> Searching
        Searching --> ResultsFound: Results available
        Searching --> NoResults: No results
        ResultsFound --> Selecting: User selects entry
        Selecting --> SenseSelection: User confirms
        NoResults --> EntrySearch: User modifies search
    }

    state SenseSelection {
        [*] --> Loading
        Loading --> Ready: Senses loaded
        Ready --> Selecting: User selects senses
        Selecting --> Confirming: User confirms
        Confirming --> Processing: User submits
    }
```

## 🔗 Component Interaction Flow

### Merge Entries Flow

```mermaid
sequenceDiagram
    participant User
    participant EntriesList
    participant EntrySearchModal
    participant SenseSelectionModal
    participant API
    participant Service

    User->>EntriesList: Clicks merge button
    EntriesList->>EntrySearchModal: Open with source entry ID
    User->>EntrySearchModal: Searches for target entry
    EntrySearchModal->>API: GET /api/entries?filter_text=...
    API->>EntrySearchModal: Returns search results
    User->>EntrySearchModal: Selects target entry
    EntrySearchModal->>SenseSelectionModal: Open with entries and senses
    User->>SenseSelectionModal: Selects senses and resolution
    SenseSelectionModal->>API: POST /api/merge-split/entries/{target}/merge
    API->>Service: merge_entries()
    Service->>API: Returns operation result
    API->>SenseSelectionModal: Shows success
    SenseSelectionModal->>EntriesList: Refresh list
```

### Split Entry Flow

```mermaid
sequenceDiagram
    participant User
    participant EntriesList
    participant SplitEntryModal
    participant API
    participant Service

    User->>EntriesList: Clicks split button
    EntriesList->>SplitEntryModal: Open with source entry
    User->>SplitEntryModal: Enters new entry data
    User->>SplitEntryModal: Selects senses to split
    SplitEntryModal->>API: POST /api/merge-split/entries/{source}/split
    API->>Service: split_entry()
    Service->>API: Returns operation result with new entry
    API->>SplitEntryModal: Shows success
    SplitEntryModal->>EntriesList: Refresh list and open new entry
```

## 🎨 Visual Design System

### Color Palette

```mermaid
pie
    title Merge/Split Color System
    "Primary (Merge)" : 30
    "Success (Split)" : 30
    "Info (Senses)" : 20
    "Warning (Conflicts)" : 10
    "Danger (Errors)" : 10
```

### Typography Scale

```mermaid
classDiagram
    class Typography {
        +h1: 2.5rem (40px) - Page titles
        +h2: 2rem (32px) - Section titles
        +h3: 1.75rem (28px) - Subsection titles
        +h4: 1.5rem (24px) - Modal titles
        +h5: 1.25rem (20px) - Card titles
        +h6: 1rem (16px) - Section headers
        +body: 0.9375rem (15px) - Body text
        +small: 0.875rem (14px) - Captions, labels
        +button: 0.875rem (14px) - Button text
    }
```

## 📋 Implementation Checklist

### UI Components to Implement

- [ ] `ActionButton` component with icon support
- [ ] `ModalDialog` base component
- [ ] `EntrySearchModal` for target entry selection
- [ ] `SenseSelectionModal` for sense selection
- [ ] `SplitEntryModal` for split operations
- [ ] `MergeSensesModal` for sense merging
- [ ] `SenseList` component with checkboxes
- [ ] `ConflictResolution` component
- [ ] `LoadingSpinner` component
- [ ] `SuccessAlert` component
- [ ] `ErrorAlert` component

### Integration Points

- [ ] Update entries list template with merge/split buttons
- [ ] Add modal containers to base template
- [ ] Connect UI events to API endpoints
- [ ] Implement state management
- [ ] Add accessibility features
- [ ] Implement responsive design

### Testing Requirements

- [ ] Unit tests for all components
- [ ] Integration tests for workflows
- [ ] Accessibility testing
- [ ] Responsive design testing
- [ ] Performance testing
- [ ] User acceptance testing

## 🎯 Conclusion

This wireframe and component documentation provides a comprehensive blueprint for implementing the merge/split operations UI. The design follows modern UI/UX best practices while integrating seamlessly with the existing Lexicographic Curation Workbench architecture.

Key features include:

1. **Intuitive Workflows**: Step-by-step dialogs guide users through complex operations
2. **Visual Feedback**: Clear indicators of selection states and operation results
3. **Accessibility**: Full keyboard navigation and screen reader support
4. **Responsive Design**: Works on desktop and tablet devices
5. **Consistent Design**: Follows existing LCW design patterns

The implementation will significantly enhance the user experience for lexicographers by providing intuitive tools for reorganizing dictionary content while maintaining data integrity.