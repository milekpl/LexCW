"""
Dictionary Writing System - Main application module.

This module initializes the Flask application and registers all blueprints.
"""

import os
import logging
from flask import Flask
from injector import Injector, singleton

from app.database.basex_connector import BaseXConnector
from app.services.dictionary_service import DictionaryService


# Create a global injector
injector = Injector()

# Create a singleton instance of BaseXConnector directly
basex_connector = BaseXConnector(
    host=os.getenv('BASEX_HOST', 'localhost'),
    port=int(os.getenv('BASEX_PORT', '1984')),
    username=os.getenv('BASEX_USERNAME', 'admin'),
    password=os.getenv('BASEX_PASSWORD', 'admin'),
    database=os.getenv('BASEX_DATABASE', 'dictionary')
)

# Make sure the connection is established
try:
    basex_connector.connect()
    logging.getLogger(__name__).info("Successfully connected to BaseX server")
except Exception as e:
    logging.getLogger(__name__).error(f"Failed to connect to BaseX server on startup: {e}")

# Create a DictionaryService instance using the BaseXConnector
dictionary_service = DictionaryService(db_connector=basex_connector)

def configure_dependencies(binder):
    """Configure dependencies for the application."""
    # Bind the pre-created instances as singletons
    binder.bind(BaseXConnector, to=basex_connector, scope=singleton)
    binder.bind(DictionaryService, to=dictionary_service, scope=singleton)

injector.binder.install(configure_dependencies)


def create_app(config_name=None):
    """
    Create and configure the Flask application.
    
    Args:
        config_name: The name of the configuration to use.
                    Default is to use the APP_CONFIG_FILE environment variable.
    
    Returns:
        Flask application instance
    """
    app = Flask(__name__, instance_relative_config=True)
    
    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    # Load configuration
    if config_name is None:
        config_name = os.getenv('FLASK_CONFIG', 'development')
    
    if config_name == 'testing':
        app.config.from_object('config.TestingConfig')
    elif config_name == 'production':
        app.config.from_object('config.ProductionConfig')
    else:
        app.config.from_object('config.DevelopmentConfig')
    
    # Load instance config if it exists
    app.config.from_pyfile('config.py', silent=True)
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if app.debug else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create instance directories
    os.makedirs(os.path.join(app.instance_path, 'audio'), exist_ok=True)
    os.makedirs(os.path.join(app.instance_path, 'exports'), exist_ok=True)
    
    # Register blueprints
    from app.api import api_bp
    app.register_blueprint(api_bp)

    from app.api.validation import validation_bp
    app.register_blueprint(validation_bp)
    
    from app.views import main_bp
    app.register_blueprint(main_bp)
    
    from app.routes.corpus_routes import corpus_bp
    app.register_blueprint(corpus_bp)
    
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
            'app': 'Dictionary Writing System',
            'status': 'running',
            'api_version': '1.0'
        }
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        """Health check endpoint."""
        return {'status': 'ok'}
    
    # Add dict_service to app for testing compatibility
    app.dict_service = dictionary_service
    app.dict_service_with_db = dictionary_service  # Alias for test compatibility
    
    return app
