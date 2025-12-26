### **Specification & Implementation Plan: Per-Project BaseX Databases**

#### **1. Executive Summary**

The goal is to refactor the application from using a single, shared BaseX database to a model where each project has its own dedicated BaseX database. This will be achieved by making the application's data access layer context-aware, determining the active project from the user's session, and dynamically managing connections to the appropriate BaseX database. This change will provide true data isolation, eliminate test collisions, and align the application with its intended multi-user, multi-project design.

#### **2. Guiding Principles**

*   **Explicit is Better than Implicit:** The application must always be explicitly aware of which project context it is operating in.
*   **Centralized Connection Management:** All BaseX database connections should be managed through a single, refactored service that handles database selection.
*   **Stateless Request Cycle:** The application should, as much as possible, determine the project context at the beginning of each request, rather than relying on a persistent global state.

#### **3. Specification: The Target Architecture**

**3.1. Database Lifecycle Management**
*   **Creation:** When a new project is created via the application UI/API, a corresponding new, empty database will be created in BaseX. The name of this BaseX database (e.g., `project_a1b2c3d4`) will be generated and stored in the `project_settings.basex_db_name` column in the primary PostgreSQL database.
*   **Deletion:** When a project is deleted, the application will issue a `DROP DB` command to BaseX to remove the associated database, ensuring no orphaned data.

**3.2. Project-Aware Request Handling**
*   The application must identify the active `project_id` for every incoming HTTP request.
*   This `project_id` will be retrieved from the user's server-side session, which is established after login and project selection.
*   A `before_request` hook in Flask will be used to fetch the project's settings (including its `basex_db_name`) and make them available throughout the request lifecycle (e.g., via Flask's `g` object).

**3.3. Dynamic Connection Management**
*   The `BaseXConnector` service will be refactored. Instead of holding a single connection to a hardcoded database, it will provide a method to get a connection/session for a *specific* `basex_db_name`.
*   This service will be responsible for opening the correct database for the given context. For performance, it could implement a simple connection pool (e.g., a dictionary of active sessions per database name) to avoid reconnecting on every query.

#### **4. Implementation Plan: Step-by-Step**

**Step 1: Un-hardcode the Configuration Manager**
*   **File:** `app/config_manager.py`
*   **Action:** Modify the `get_setting` function. It currently fetches the first project's settings. It must be updated to accept a `project_id` and fetch the settings for that specific project.
*   **Action:** Modify the `create_settings` function in the same file. When creating a new project, it must generate a unique `basex_db_name` (e.g., `f"project_{uuid.uuid4().hex}"`) and store it.

**Step 2: Implement BaseX Database Lifecycle Functions**
*   **File:** `app/database/basex_connector.py`
*   **Action:** Create two new internal methods:
    *   `_create_database(db_name: str)`: Executes the `CREATE DB [db_name]` command in BaseX.
    *   `_drop_database(db_name: str)`: Executes the `DROP DB [db_name]` command.
*   These methods will be called by the project creation and deletion routes.

**Step 3: Refactor the `BaseXConnector` for Dynamic Sessions**
*   **File:** `app/database/basex_connector.py`
*   **Action:** The `__init__` method should no longer open a default database.
*   **Action:** Create a new primary method, `get_session(db_name: str) -> BaseXClient.Session`.
    *   This method will be responsible for creating a `BaseXClient.Session`.
    *   It will execute the `OPEN [db_name]` command on that session.
    *   It will return the prepared session object.
*   **Action:** Update all query methods (e.g., `execute_query`) to accept a `db_name` parameter, which they will use to call `get_session(db_name)` before running the query.

**Step 4: Implement Request-Level Project Context**
*   **File:** `app/__init__.py` or a new `app/hooks.py`.
*   **Action:** Create a `@app.before_request` function.
    1.  Check if `session.get('project_id')` exists.
    2.  If it does, use the refactored `config_manager` to fetch the `ProjectSettings` for that `project_id`.
    3.  Store the settings, especially `basex_db_name`, in Flask's request-global `g` object (e.g., `g.project_db_name = settings.basex_db_name`).
    4.  If no `project_id` is in the session (and the user is not accessing a public/auth page), redirect them to a project selection page.

**Step 5: Update All Data Access Call Sites**
*   **Action:** This is the most widespread change. Use `grep` or your IDE to find every location where `basex_connector.execute_query` (or similar) is called.
*   **Action:** Modify each call to pass the database name from the request context: `basex_connector.execute_query(db_name=g.project_db_name, query=...)`.

**Step 6: Update Project Creation/Deletion Routes**
*   **File:** `app/routes/settings_routes_clean.py`
*   **Action:**
    *   In the `create_project` route, after successfully creating the project entry in PostgreSQL, call the new `basex_connector._create_database(new_db_name)`.
    *   Create a `delete_project` route. It must first delete the PostgreSQL entry and then call `basex_connector._drop_database(db_name_to_delete)`.

**Step 7: Refactor Unit and Integration Tests**
*   **Action:** Test setup fixtures should now programmatically create a new project and get its unique `basex_db_name`.
*   **Action:** All test functions that interact with the database must now operate within a request context that has the correct `project_id` and `basex_db_name` set.
*   **Action:** Test teardown fixtures must delete the created project, which will trigger the deletion of its BaseX database. This solves the test collision problem permanently.

#### **5. Sketch of User & Session Management**

This architecture connects directly to user management. The flow is as follows:

1.  **Authentication:** A user logs in. Upon successful authentication, their `user_id` is stored in the Flask `session`.
    *   `session['user_id'] = user.id`
2.  **Project Listing:** The user is presented with a list of projects they have access to. This list is queried from the PostgreSQL database (`SELECT * FROM projects WHERE user_id = :user_id`).
3.  **Project Selection:** The user clicks on a project to work on.
    *   The application sets the chosen `project_id` in the session: `session['project_id'] = selected_project_id`.
4.  **Work Session:** On every subsequent request, the `@app.before_request` hook (Step 4) sees `session['project_id']`, looks up the corresponding `basex_db_name`, and prepares the request context `g`. All database operations for that request are now correctly and automatically routed to the right database.
5.  **Switching Projects:** If the user wants to switch projects, they navigate back to the project list and select a different one. This simply overwrites the `session['project_id']` value, and the very next request will seamlessly connect to the new project's database.
