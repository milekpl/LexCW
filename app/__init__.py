"""
Lexicographic Curation Workbench - Main application module.

This module initializes the Flask application and registers all blueprints.
"""

import os
import logging
from pathlib import Path
from flask import Flask, session, g, request, redirect, url_for
from flasgger import Swagger
from injector import Injector, singleton
import psycopg2

from app.database.basex_connector import BaseXConnector
from app.database.workset_db import create_workset_tables


# Create a global injector
injector = Injector()

# The injector will be configured inside create_app, once the app is initialized.


def create_app(config_name=None):
    """
    Create and configure the Flask application.

    Args:
        config_name: The name of the configuration to use.
                    Default is to use the APP_CONFIG_FILE environment variable.

    Returns:
        Flask application instance
    """
    # Moved imports inside to avoid circular dependency with models/services
    from app.services.dictionary_service import DictionaryService
    from app.services.merge_split_service import MergeSplitService
    from app.config_manager import ConfigManager
    from app.services.cache_service import CacheService

    app = Flask(__name__, instance_relative_config=True)  # type: Flask
    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Load configuration
    if config_name is None:
        config_name = os.getenv("FLASK_CONFIG", "development")

    # Load configuration
    if config_name == "testing":
        app.config.from_object("config.TestingConfig")
    elif config_name == "production":
        app.config.from_object("config.ProductionConfig")
    else:
        app.config.from_object("config.DevelopmentConfig")

    # Force debug mode for detailed error reporting during development/testing
    app.debug = True
    app.config["DEBUG"] = True

    # Load instance config if it exists
    app.config.from_pyfile("config.py", silent=True)

    # === Ensure TEST_DB_NAME / BASEX_DATABASE are synchronized ===
    # This helps when tests or modules instantiate the app before test fixtures
    # set environment variables. Prefer explicit env var if present, otherwise
    # propagate app config value into the environment so other modules see it.
    try:
        env_db = os.environ.get("TEST_DB_NAME") or os.environ.get("BASEX_DATABASE")
        cfg_db = app.config.get("BASEX_DATABASE")
        if env_db and cfg_db and env_db != cfg_db:
            app.logger.warning(
                "TEST_DB_NAME '%s' differs from app BASEX_DATABASE '%s' - sync to TEST_DB_NAME",
                env_db,
                cfg_db,
            )
            app.config["BASEX_DATABASE"] = env_db
        elif env_db and not cfg_db:
            app.logger.info(
                "Setting app BASEX_DATABASE from TEST_DB_NAME env: '%s'", env_db
            )
            app.config["BASEX_DATABASE"] = env_db
        elif not env_db and cfg_db:
            # Export config value to environment so other imports see it
            os.environ["TEST_DB_NAME"] = cfg_db
            os.environ["BASEX_DATABASE"] = cfg_db
            app.logger.info(
                "Exported BASEX_DATABASE '%s' to TEST_DB_NAME env vars", cfg_db
            )
    except Exception as e:
        app.logger.debug(f"Error during TEST_DB_NAME sync: {e}")

    # Ensure SQLAlchemy is registered with the Flask app after config is loaded
    from app.models.project_settings import db

    db.init_app(app)

    # Initialize Flask-WTF CSRF protection
    from flask_wtf import CSRFProtect

    csrf = CSRFProtect(app)

    # Create database tables if they don't exist
    with app.app_context():
        from app import models as _models  # noqa: F401

        db.create_all()

    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if app.debug else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # File-based logging is disabled to prevent file locking issues
    # with the Werkzeug reloader on Windows. Logging will go to the console.

    # Create instance directories
    os.makedirs(os.path.join(app.instance_path, "audio"), exist_ok=True)
    os.makedirs(os.path.join(app.instance_path, "images"), exist_ok=True)
    os.makedirs(os.path.join(app.instance_path, "exports"), exist_ok=True)

    # Ensure static subdirectories exist for uploads
    os.makedirs(os.path.join(app.static_folder, "audio"), exist_ok=True)
    os.makedirs(os.path.join(app.static_folder, "images"), exist_ok=True)

    # Register blueprints
    from app.api import api_bp

    app.register_blueprint(api_bp)

    from app.api.validation import validation_bp

    app.register_blueprint(validation_bp)

    from app.api.ranges import ranges_bp

    app.register_blueprint(ranges_bp)
    from app.api.setup import setup_bp

    app.register_blueprint(setup_bp)

    from app.api.ranges_editor import ranges_editor_bp

    app.register_blueprint(ranges_editor_bp)

    from app.api.pronunciation import pronunciation_bp

    app.register_blueprint(pronunciation_bp)

    from app.api.illustration import illustration_bp

    app.register_blueprint(illustration_bp)

    from app.views import main_bp

    app.register_blueprint(main_bp)

    from app.routes.corpus_routes import corpus_bp

    app.register_blueprint(corpus_bp)

    # Register corpus search API
    from app.api.corpus_search import corpus_search_bp
    app.register_blueprint(corpus_search_bp, url_prefix='/api/corpus')

    # Register additional API routes
    from app.routes.api_routes import api_bp as additional_api_bp

    app.register_blueprint(additional_api_bp)

    from app.api.worksets import worksets_bp

    app.register_blueprint(worksets_bp)

    from app.api.query_builder import query_builder_bp

    app.register_blueprint(query_builder_bp)

    from app.views import workbench_bp

    app.register_blueprint(workbench_bp)

    # Register auto-save API for Phase 3
    from app.api.entry_autosave_working import autosave_bp

    app.register_blueprint(autosave_bp)

    # Register real-time validation API for Phase 4
    from app.api.validation_endpoints import validation_api

    app.register_blueprint(validation_api, url_prefix="/api/validation")

    # Register validation service API (includes /api/validation/xml endpoint)
    from app.api.validation_service import validation_service_bp

    app.register_blueprint(validation_service_bp)

    # Register validation rules API for project-specific rules
    from app.api.validation_rules_api import validation_rules_bp

    app.register_blueprint(validation_rules_bp)

    # Register entries API
    from app.api.entries import entries_bp

    app.register_blueprint(entries_bp, url_prefix="/api/entries")

    # Register XML entries API
    from app.api.xml_entries import xml_entries_bp

    app.register_blueprint(xml_entries_bp)

    # Register display API
    from app.api.display import display_bp

    app.register_blueprint(display_bp)

    # Register LIFT element registry API
    from app.api.lift_registry import registry_bp

    app.register_blueprint(registry_bp)

    # Register display profile management API
    from app.api.display_profiles import profiles_bp

    app.register_blueprint(profiles_bp)

    # Register settings blueprint
    from app.routes.settings_routes_clean import settings_bp

    app.register_blueprint(settings_bp)

    # Register merge/split operations API
    from app.api.merge_split import merge_split_bp

    app.register_blueprint(merge_split_bp)

    # Register backup API
    from app.api.backup_api import backup_api

    app.register_blueprint(backup_api)

    # Register backup management routes
    from app.routes.backup_routes import backup_bp

    app.register_blueprint(backup_bp)

    # Register user management API blueprints
    from app.api.auth_api import auth_api_bp

    app.register_blueprint(auth_api_bp)

    from app.api.users_api import users_api_bp

    app.register_blueprint(users_api_bp)

    from app.api.messages_api import messages_api_bp

    app.register_blueprint(messages_api_bp)

    from app.api.project_members_api import project_members_api_bp

    app.register_blueprint(project_members_api_bp)

    # Register authentication web routes
    from app.routes.auth_routes import auth_bp

    app.register_blueprint(auth_bp)

    # Create PostgreSQL connection pool and create tables
    app.pg_pool = None

    # Skip PostgreSQL connection in testing mode (uses SQLite in-memory)
    # BUT allow PostgreSQL for E2E tests which need workset functionality
    is_testing = app.config.get("TESTING") and not app.config.get("E2E_TESTING")
    if not is_testing:
        try:
            # Add connection timeout to prevent hanging
            pg_pool = psycopg2.pool.SimpleConnectionPool(
                1,
                20,
                user=app.config.get("PG_USER"),
                password=app.config.get("PG_PASSWORD"),
                host=app.config.get("PG_HOST"),
                port=app.config.get("PG_PORT"),
                database=app.config.get("PG_DATABASE"),
                connect_timeout=3,  # Add 3 second timeout
            )
            app.pg_pool = pg_pool
            create_workset_tables(pg_pool)
            app.logger.info(
                f"Successfully connected to PostgreSQL at {app.config.get('PG_HOST')}:{app.config.get('PG_PORT')}"
            )
        except (Exception, psycopg2.DatabaseError) as error:
            app.logger.error(f"Error while connecting to PostgreSQL: {error}")
            app.logger.warning(
                "PostgreSQL features will be unavailable. See docs/POSTGRESQL_WSL_SETUP.md for setup instructions."
            )

    # Initialize Swagger documentation
    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": "apispec",
                "route": "/apispec.json",
                "rule_filter": lambda rule: True,  # All endpoints
                "model_filter": lambda tag: True,  # All models
            }
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/apidocs/",
        "title": "Dictionary API Documentation",
        "description": "API documentation for the Lexicographic Curation Workbench",
        "version": "1.0.0",
        "termsOfService": "",
        "contact": {
            "name": "Dictionary API Support",
            "url": "http://localhost:5000",
            "email": "support@example.com",
        },
    }

    swagger = Swagger(app, config=swagger_config)
    app.swagger = swagger  # Store reference to avoid unused variable warning

    # Register error handlers
    @app.errorhandler(404)
    def not_found(_error):
        """Handle 404 errors."""
        return {"error": "Not found"}, 404

    @app.errorhandler(500)
    def server_error(_error):
        """Handle 500 errors."""
        return {"error": "Server error"}, 500

    @app.before_request
    def load_project_context():
        """Load project context from session if available."""
        import uuid

        # Ensure each request has a unique ID for tracing across logs
        try:
            g.request_id = uuid.uuid4().hex
            app.logger.debug(
                f"Assigned request_id {g.request_id} for path {request.path}"
            )
        except Exception:
            # Non-request contexts or tests without request may fail here; ignore
            pass

        # If running under per-test DB mode, prefer TEST_DB_NAME for every request
        # This prevents session project_id from leaking across test runs and causing
        # cross-test database access when the server is reused across tests.
        test_db = os.environ.get("TEST_DB_NAME")
        if test_db:
            g.project_db_name = test_db
            return

        # Exempt certain paths from mandatory project context
        exempt_paths = [
            "/settings/",
            "/static/",
            "/health",
            "/apidocs/",
            "/apispec.json",
            "/flasgger_static/",
            "/favicon.ico",
        ]

        # Also exempt the root index if it's just a status check
        if request.path == "/":
            return

        if any(request.path.startswith(path) for path in exempt_paths):
            return

        project_id = session.get("project_id")
        if project_id:
            try:
                # Access config_manager from app context via injector
                config_manager = app.injector.get(ConfigManager)
                settings = config_manager.get_settings_by_id(project_id)
                if settings:
                    g.project_settings = settings
                    db_name = getattr(settings, "basex_db_name", None)
                    # Guard against tests or misconfigured settings that return non-string values (e.g., Mock objects)
                    if not isinstance(db_name, str):
                        app.logger.warning(
                            "Invalid basex_db_name from settings (type=%s); falling back to app.config['BASEX_DATABASE']",
                            type(db_name),
                        )
                        db_name = app.config.get("BASEX_DATABASE")
                    g.project_db_name = db_name
                else:
                    # Invalid project ID in session
                    session.pop("project_id", None)
                    return redirect(url_for("settings.list_projects", next=request.url))
            except Exception as e:
                app.logger.error(f"Error loading project context: {e}")
        else:
            # No project selected. Prefer to set request-local DB from TEST_DB_NAME in
            # testing/e2e scenarios so API calls can still be executed against the
            # intended per-test database when the session doesn't carry a project.
            test_db = os.environ.get("TEST_DB_NAME")
            if test_db:
                g.project_db_name = test_db
            else:
                # Skip redirect for API calls to avoid breaking external clients;
                # they will fail later with "no database configured" if they don't provide context
                if not request.path.startswith("/api/"):
                    return redirect(url_for("settings.list_projects", next=request.url))

    # Per-request BaseX connector logging: capture DB/session status early for diagnostics
    @app.before_request
    def log_basex_status():
        try:
            from app.database.basex_connector import BaseXConnector
            from flask import has_request_context, g, request

            try:
                connector = app.injector.get(BaseXConnector)
            except Exception:
                connector = None

            if connector:
                try:
                    status = connector.get_status()
                    # Include the intended per-request DB name if present
                    req_db = getattr(g, "project_db_name", None)
                    app.logger.info(
                        "BaseX status at request start [request_id=%s path=%s project_db=%s]: %s",
                        getattr(g, "request_id", None),
                        request.path,
                        req_db,
                        status,
                    )
                except Exception:
                    app.logger.exception("Failed to obtain BaseX connector status")
        except Exception:
            # Defensive: avoid breaking request processing if logging fails
            app.logger.debug("Per-request BaseX status logging skipped (init failure)")

    # In testing mode, log redirects to help triage UI auth/redirect issues
    # (This includes E2E mode)
    is_testing = app.config.get("TESTING") or app.config.get("E2E_TESTING")
    if is_testing:

        @app.after_request
        def log_redirects(response):
            try:
                if response.status_code in (301, 302, 303, 307, 308):
                    loc = response.headers.get("Location")
                    app.logger.warning(
                        "Redirect detected: %s %s -> %s",
                        response.status_code,
                        request.path,
                        loc,
                    )
            except Exception:
                app.logger.exception("Failed to log redirect")
            return response

    # Create simple index route
    @app.route("/")
    def index():
        """Index route."""
        return {
            "app": "Lexicographic Curation Workbench",
            "status": "running",
            "api_version": "1.0",
        }

    # Health check endpoint
    @app.route("/health")
    def health_check():
        """Health check endpoint."""
        return {"status": "ok"}

    # Configure dependency injection
    def configure_dependencies(binder):
        """Configure dependencies for the application."""
        # Create a singleton instance of BaseXConnector
        # Prefer any explicit TEST_DB_NAME / BASEX_DATABASE env var if present so
        # that connectors use the DB created by test fixtures; fall back to app
        # config otherwise.
        env_db = os.environ.get("TEST_DB_NAME") or os.environ.get("BASEX_DATABASE")
        basex_database = env_db or app.config.get("BASEX_DATABASE", "dictionary")
        basex_connector = BaseXConnector(
            host=app.config.get("BASEX_HOST", "localhost"),
            port=app.config.get("BASEX_PORT", 1984),
            username=app.config.get("BASEX_USERNAME", "admin"),
            password=app.config.get("BASEX_PASSWORD", "admin"),
            database=basex_database,
        )

        # Only connect during non-test environments (but allow E2E tests to connect)
        is_testing = app.testing and not app.config.get("E2E_TESTING")
        if not is_testing:
            try:
                basex_connector.connect()
                app.logger.info("Successfully connected to BaseX server")
            except Exception as e:
                app.logger.error(f"Failed to connect to BaseX server on startup: {e}")

        # Initialize and bind OperationHistoryService
        from app.services.operation_history_service import OperationHistoryService

        is_testing = app.testing and not app.config.get("E2E_TESTING")
        history_path = (
            os.path.join(app.instance_path, "operation_history_test.json")
            if is_testing
            else os.path.join(app.instance_path, "operation_history.json")
        )
        operation_history_service = OperationHistoryService(
            history_file_path=history_path
        )
        binder.bind(
            OperationHistoryService, to=operation_history_service, scope=singleton
        )

        # Initialize backup-related services first for DictionaryService
        from app.services.basex_backup_manager import BaseXBackupManager
        from app.services.backup_scheduler import BackupScheduler

        backup_manager = BaseXBackupManager(
            basex_connector,
            backup_directory=os.path.join(app.instance_path, "backups"),
        )
        backup_scheduler = BackupScheduler(backup_manager, app=app)

        # Load backup settings: moved after ConfigManager is initialized to avoid
        # accessing the database before an application context is active.
        # (Actual load happens after ConfigManager binding below.)

        # Start the backup scheduler only in non-testing environments (but allow E2E tests)
        is_testing = app.config.get("TESTING") and not app.config.get("E2E_TESTING")
        if not is_testing:
            backup_scheduler.start()
            app.logger.info("Backup scheduler started")

            # Debug: Check if scheduler has any scheduled backups after our setup
            scheduled_after_setup = backup_scheduler.get_scheduled_backups()
            app.logger.info(
                f"Scheduled backups after setup: {len(scheduled_after_setup)}"
            )
            if scheduled_after_setup:
                for backup in scheduled_after_setup:
                    app.logger.info(
                        f"  - {backup.get('schedule_id')}: {backup.get('trigger')}"
                    )
        else:
            app.logger.info("Backup scheduler disabled during testing")

        # Create and bind DictionaryService
        dictionary_service = DictionaryService(
            db_connector=basex_connector, history_service=operation_history_service
        )

        # Initialize and bind ConfigManager
        config_manager = ConfigManager(app.instance_path)
        try:
            app.config["PROJECT_SETTINGS"] = [
                s.settings_json for s in config_manager.get_all_settings()
            ]
        except Exception:
            # If database not initialized yet, set to empty list
            app.config["PROJECT_SETTINGS"] = []

        # Bind all services
        binder.bind(BaseXConnector, to=basex_connector, scope=singleton)
        binder.bind(DictionaryService, to=dictionary_service, scope=singleton)
        binder.bind(ConfigManager, to=config_manager, scope=singleton)
        binder.bind(BaseXBackupManager, to=backup_manager, scope=singleton)
        binder.bind(BackupScheduler, to=backup_scheduler, scope=singleton)

        # Load backup settings and schedule backups if configured (only in non-testing, allow E2E)
        is_testing = app.config.get("TESTING") and not app.config.get("E2E_TESTING")
        if not is_testing:
            try:
                from app.models.project_settings import ProjectSettings
                from app.models.backup_models import ScheduledBackup
                import traceback
                from datetime import datetime, timedelta, timezone

                backup_config = None

                # Query ProjectSettings inside app context to avoid "Working outside of application context"
                try:
                    with app.app_context():
                        settings = ProjectSettings.query.first()
                except Exception as e:
                    app.logger.error(f"Failed to query ProjectSettings: {e}")
                    app.logger.debug(traceback.format_exc())
                    settings = None

                if settings and getattr(settings, "backup_settings", None):
                    backup_config = settings.backup_settings
                    app.logger.info(
                        "Using backup settings from ProjectSettings (project id=%s)",
                        getattr(settings, "id", None),
                    )
                else:
                    # Fallback to ConfigManager defaults
                    try:
                        # Ensure we're in app context when calling get_backup_settings
                        with app.app_context():
                            backup_config = config_manager.get_backup_settings()
                        app.logger.info(
                            "Using default backup settings from ConfigManager"
                        )
                    except Exception as e:
                        app.logger.error(
                            f"Failed to get backup settings from ConfigManager: {e}"
                        )
                        app.logger.debug(traceback.format_exc())

                def compute_next_run(time_str: str, interval: str) -> datetime:
                    now = datetime.now(timezone.utc)
                    try:
                        hh, mm = map(int, time_str.split(":"))
                        candidate = now.replace(
                            hour=hh, minute=mm, second=0, microsecond=0
                        )
                    except Exception:
                        candidate = now + timedelta(minutes=1)
                    if candidate <= now:
                        if interval == "daily":
                            candidate += timedelta(days=1)
                        elif interval == "weekly":
                            candidate += timedelta(days=7)
                        elif interval == "hourly":
                            candidate += timedelta(hours=1)
                        else:
                            candidate += timedelta(days=1)
                    return candidate

                if backup_config:
                    schedule_interval = backup_config.get("schedule", "daily")
                    if schedule_interval and schedule_interval != "none":
                        time_str = backup_config.get("time", "02:00")
                        db_name = (
                            getattr(settings, "basex_db_name", None) or basex_database
                        )
                        next_run = compute_next_run(time_str, schedule_interval)

                        scheduled_backup = ScheduledBackup(
                            db_name=db_name,
                            interval=schedule_interval,
                            time_=time_str,
                            type_=backup_config.get("backup_type", "full"),
                            next_run=next_run,
                            active=True,
                        )

                        backup_scheduler.schedule_backup(scheduled_backup)
                        app.logger.info(
                            f"Scheduled {schedule_interval} backup at {time_str}"
                        )
                    else:
                        app.logger.info("Backup schedule is set to 'none' in settings")
                else:
                    app.logger.info("No backup settings found")
            except Exception as e:
                app.logger.error(f"Error loading backup settings: {e}")
                app.logger.debug(traceback.format_exc())
        else:
            app.logger.info("Skipping backup scheduler setup during testing")

        # Initialize and bind CacheService
        from app.services.cache_service import CacheService

        cache_service = CacheService()
        binder.bind(CacheService, to=cache_service, scope=singleton)

        # Initialize and bind RangesService
        from app.services.ranges_service import RangesService

        ranges_service = RangesService(db_connector=basex_connector)
        binder.bind(RangesService, to=ranges_service, scope=singleton)

        # After services are configured, attempt an initial scan to populate
        # custom ranges derived from LIFT data. Do this only when not in testing
        # mode to avoid noise in unit tests (but allow E2E tests).
        try:
            is_testing = app.testing and not app.config.get("E2E_TESTING")
            if not is_testing:
                # Ensure application context is active for DB access during scan
                with app.app_context():
                    dictionary_service.scan_and_create_custom_ranges(project_id=1)
        except Exception:
            app.logger.exception("Initial scan for undefined ranges failed")

        # Initialize and bind CSSMappingService
        from app.services.css_mapping_service import CSSMappingService

        # Use instance path for display profiles storage
        storage_path = Path(app.instance_path) / "display_profiles.json"
        css_mapping_service = CSSMappingService(storage_path=storage_path)
        binder.bind(CSSMappingService, to=css_mapping_service, scope=singleton)

        # Initialize and bind MergeSplitService
        from app.services.merge_split_service import MergeSplitService

        merge_split_service = MergeSplitService(
            dictionary_service=dictionary_service,
            history_service=operation_history_service,
        )
        binder.bind(MergeSplitService, to=merge_split_service, scope=singleton)

        # Initialize ValidationRulesService with Flask app
        from app.services.validation_rules_service import ValidationRulesService

        validation_rules_service = ValidationRulesService(app=app)
        binder.bind(
            ValidationRulesService, to=validation_rules_service, scope=singleton
        )

        # Initialize and bind EventBus for service coordination
        from app.services.event_bus import EventBus

        event_bus = EventBus()
        binder.bind(EventBus, to=event_bus, scope=singleton)

        # Initialize and bind BulkOperationsService for bulk entry operations
        from app.services.bulk_operations_service import BulkOperationsService
        from app.services.workset_service import WorksetService

        workset_service = WorksetService()
        binder.bind(WorksetService, to=workset_service, scope=singleton)
        bulk_operations_service = BulkOperationsService(
            dictionary_service=dictionary_service,
            workset_service=workset_service,
            history_service=operation_history_service,
        )
        binder.bind(BulkOperationsService, to=bulk_operations_service, scope=singleton)

        # Initialize and bind BulkQueryService and BulkActionService for advanced bulk operations
        from app.services.bulk_query_service import BulkQueryService
        from app.services.bulk_action_service import BulkActionService

        bulk_query_service = BulkQueryService(dictionary_service=dictionary_service)
        bulk_action_service = BulkActionService(dictionary_service=dictionary_service)
        binder.bind(BulkQueryService, to=bulk_query_service, scope=singleton)
        binder.bind(BulkActionService, to=bulk_action_service, scope=singleton)

    # After DI, set a flag if this is a first-run (no project settings configured)
    with app.app_context():
        try:
            config_manager = app.injector.get(ConfigManager)
            settings = config_manager.get_all_settings()
            app.config["FIRST_RUN_SETUP"] = False if settings else True
        except Exception:
            app.config["FIRST_RUN_SETUP"] = False

    # Inject FIRST_RUN flag into templates
    @app.context_processor
    def inject_first_run_flag():
        return {"FIRST_RUN_SETUP": app.config.get("FIRST_RUN_SETUP", False)}

    # Create and attach injector
    injector = Injector()
    injector.binder.install(configure_dependencies)
    app.injector = injector

    # Import ValidationRulesService for app context
    from app.services.validation_rules_service import ValidationRulesService

    # Add services to app context for easier access in views and tests
    app.dict_service = injector.get(DictionaryService)
    app.config_manager = injector.get(ConfigManager)
    app.cache_service = injector.get(CacheService)
    app.merge_split_service = injector.get(MergeSplitService)
    app.validation_rules_service = injector.get(ValidationRulesService)

    # Initialize Lucene corpus client
    from app.services.lucene_corpus_client import LuceneCorpusClient

    app.lucene_corpus_client = LuceneCorpusClient(
        base_url=app.config.get("LUCENE_CORPUS_URL", "http://localhost:8082")
    )

    return app
