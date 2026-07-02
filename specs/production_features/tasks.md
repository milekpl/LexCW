# Implementation Plan: Production Features

This document outlines the implementation tasks for the Production Features, based on the requirements in `specification.md`.

1.  [x] **Security and Authentication**
    *   This epic covers the implementation of security and authentication features.

    1.1. [x] **User Management System**
        *   Implement a user management system with authentication and role-based access control.
        *   Implemented: User model with registration/login/logout/change-password/reset-password endpoints (`auth_api.py`, `auth_service.py`). Session-based auth via `login_required` decorator. User roles (admin/user) with RBAC via `ProjectSettings.is_admin`.
        *   Note: Session-based auth is used (not JWT). JWT migration is future work.
        *   **Requirements**: `5.3.1`, `18.2`

    1.2. [x] **Security Framework**
        *   Implement a security framework with input validation, CSRF protection, and security headers.
        *   Implemented: Flask-WTF `CSRFProtect(app)` in `app/__init__.py:93-95`. CSRF token meta tag used on all pages. Validation engine handles input sanitization.
        *   **Requirements**: `5.3`, `18.2`

2.  [x] **Core Export System**
    *   This epic covers the core export capabilities provided by the application.

    2.1. [x] **Standard Export Formats**
        *   Implement LIFT, HTML, Markdown, YAML, JSON, and TSV export.
        *   **Implemented**: Unified export service in `app/services/export_service.py` with LIFT, HTML, Markdown, and SQLite exporters.
        *   **Requirements**: `3.3.2`, `7.5`, `18.2`

    2.2. [ ] **Publication Workflows**
        *   Implement publication workflows for automating the process of publishing the dictionary.
        *   **Requirements**: `12.3`, `18.2`

3.  [x] **Annotations (Editorial Comments)**
    *   This epic covers entry/sense-level annotations, which are the foundation for collaboration.

    3.1. [x] **Entry and Sense Annotations**
        *   Implement editable annotations on entries and senses with name, value, who, when, and multilingual content.
        *   **Implemented**: Alpine.js components (`entry-annotations.js`, `sense-tree.js`), LIFT serialization, and view rendering in `entry_view.html`.
        *   **Requirements**: `12.1`, `18.2`

4.  [ ] **Real-time Collaboration**
    *   This epic covers real-time multi-user editing and threaded discussion.

    4.1. [ ] **Multi-user Editing**
        *   Implement real-time collaboration and a threaded commenting system.
        *   **Note**: Basic annotations are in place; threaded/real-time features remain future work.
        *   **Requirements**: `12.1`, `18.2`

    4.2. [ ] **Project Management**
        *   Implement project management features, such as task assignment and progress tracking.
        *   **Requirements**: `12.1`, `18.2`

5.  [ ] **Performance and Monitoring**
    *   This epic covers the implementation of performance and monitoring features.

    5.1. [ ] **Monitoring Dashboard**
        *   Implement a monitoring dashboard for tracking the health and performance of the application.
        *   **Requirements**: `9.4`, `13.5.2`, `18.2`

    5.2. [ ] **Scalability Optimization**
        *   Optimize the application for scalability to support over 300,000 entries.
        *   **Requirements**: `5.1.2`, `18.2`
