"""
Lexicographic Curation Workbench - Main application module.

This module initializes the Flask application and registers all blueprints.
"""

import os
import logging
from flask import Flask
from flasgger import Swagger
from injector import Injector, singleton
import psycopg2

from app.database.basex_connector import BaseXConnector
from app.services.dictionary_service import DictionaryService
from app.config_manager import ConfigManager
from app.services.cache_service import CacheService
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
    app = Flask(__name__, instance_relative_config=True)  # type: Flask
    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Load configuration
    if config_name is None:
        config_name = os.getenv('FLASK_CONFIG', 'development')

    # Load configuration
    if config_name == 'testing':
        app.config.from_object('config.TestingConfig')
    elif config_name == 'production':
        app.config.from_object('config.ProductionConfig')
    else:
        app.config.from_object('config.DevelopmentConfig')

    # Force debug mode for detailed error reporting during development/testing
    app.debug = True
    app.config['DEBUG'] = True

    # Load instance config if it exists
    app.config.from_pyfile('config.py', silent=True)

    # Ensure SQLAlchemy is registered with the Flask app after config is loaded
    from app.models.project_settings import db
    db.init_app(app)
    
    # Create database tables if they don't exist
    with app.app_context():
        db.create_all()
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if app.debug else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    # File-based logging is disabled to prevent file locking issues
    # with the Werkzeug reloader on Windows. Logging will go to the console.
    
    # Create instance directories
    os.makedirs(os.path.join(app.instance_path, 'audio'), exist_ok=True)
    os.makedirs(os.path.join(app.instance_path, 'exports'), exist_ok=True)
    
    # Register blueprints
    from app.api import api_bp
    app.register_blueprint(api_bp)
    
    from app.api.validation import validation_bp
    app.register_blueprint(validation_bp)
    
    from app.api.ranges import ranges_bp
    app.register_blueprint(ranges_bp)
    
    from app.api.pronunciation import pronunciation_bp
    app.register_blueprint(pronunciation_bp)
    
    from app.views import main_bp
    app.register_blueprint(main_bp)
    
    from app.routes.corpus_routes import corpus_bp
    app.register_blueprint(corpus_bp)
    
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
    app.register_blueprint(validation_api, url_prefix='/api/validation')
    
    # Register entries API
    from app.api.entries import entries_bp
    app.register_blueprint(entries_bp, url_prefix='/api/entries')
    
    # Register XML entries API
    from app.api.xml_entries import xml_entries_bp
    app.register_blueprint(xml_entries_bp)
    
    # Register display API
    from app.api.display import display_bp
    app.register_blueprint(display_bp)
    
    # Register settings blueprint
    from app.routes.settings_routes import settings_bp
    app.register_blueprint(settings_bp)

    # Create PostgreSQL connection pool and create tables
    app.pg_pool = None
    
    # Skip PostgreSQL connection in testing mode (uses SQLite in-memory)
    if not app.config.get('TESTING'):
        try:
            # Add connection timeout to prevent hanging
            pg_pool = psycopg2.pool.SimpleConnectionPool(
                1, 20,
                user=app.config.get("PG_USER"),
                password=app.config.get("PG_PASSWORD"),
                host=app.config.get("PG_HOST"),
                port=app.config.get("PG_PORT"),
                database=app.config.get("PG_DATABASE"),
                connect_timeout=3  # Add 3 second timeout
            )
            app.pg_pool = pg_pool
            create_workset_tables(pg_pool)
            app.logger.info(f"Successfully connected to PostgreSQL at {app.config.get('PG_HOST')}:{app.config.get('PG_PORT')}")
        except (Exception, psycopg2.DatabaseError) as error:
            app.logger.error(f"Error while connecting to PostgreSQL: {error}")
            app.logger.warning("PostgreSQL features will be unavailable. See docs/POSTGRESQL_WSL_SETUP.md for setup instructions.")
    
    # Initialize Swagger documentation
    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": 'apispec',
                "route": '/apispec.json',
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
            "email": "support@example.com"
        },
    }
    
    swagger = Swagger(app, config=swagger_config)
    app.swagger = swagger  # Store reference to avoid unused variable warning
    
    # Register error handlers
    @app.errorhandler(404)
    def not_found(_error):
        """Handle 404 errors."""
        return {'error': 'Not found'}, 404
    
    @app.errorhandler(500)
    def server_error(_error):
        """Handle 500 errors."""
        return {'error': 'Server error'}, 500
    
    # Create simple index route
    @app.route('/')
    def index():
        """Index route."""
        return {
            'app': 'Lexicographic Curation Workbench',
            'status': 'running',
            'api_version': '1.0'
        }
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        """Health check endpoint."""
        return {'status': 'ok'}
    
    # Configure dependency injection
    def configure_dependencies(binder):
        """Configure dependencies for the application."""
        # Create a singleton instance of BaseXConnector
        # Use TEST_DB_NAME from environment ONLY during testing
        test_db_name = os.environ.get('TEST_DB_NAME') if app.testing else None
        basex_database = test_db_name if test_db_name else app.config.get('BASEX_DATABASE', 'dictionary')
        basex_connector = BaseXConnector(
            host=app.config.get('BASEX_HOST', 'localhost'),
            port=app.config.get('BASEX_PORT', 1984),
            username=app.config.get('BASEX_USERNAME', 'admin'),
            password=app.config.get('BASEX_PASSWORD', 'admin'),
            database=basex_database
        )
        
        # Only connect during non-test environments
        if not app.testing:
            try:
                basex_connector.connect()
                app.logger.info("Successfully connected to BaseX server")
            except Exception as e:
                app.logger.error(f"Failed to connect to BaseX server on startup: {e}")

        # Create and bind DictionaryService
        dictionary_service = DictionaryService(db_connector=basex_connector)
        
        # Initialize and bind ConfigManager
        config_manager = ConfigManager(app.instance_path)
        try:
            app.config['PROJECT_SETTINGS'] = [s.settings_json for s in config_manager.get_all_settings()]
        except Exception:
            # If database not initialized yet, set to empty list
            app.config['PROJECT_SETTINGS'] = []

        # Bind all services
        binder.bind(BaseXConnector, to=basex_connector, scope=singleton)
        binder.bind(DictionaryService, to=dictionary_service, scope=singleton)
        binder.bind(ConfigManager, to=config_manager, scope=singleton)
        
        # Initialize and bind CacheService
        from app.services.cache_service import CacheService
        cache_service = CacheService()
        binder.bind(CacheService, to=cache_service, scope=singleton)

    # Create and attach injector
    injector = Injector()
    injector.binder.install(configure_dependencies)
    app.injector = injector
    
    # Add services to app context for easier access in views and tests
    app.dict_service = injector.get(DictionaryService)
    app.config_manager = injector.get(ConfigManager)
    app.cache_service = injector.get(CacheService)
    
    return app
