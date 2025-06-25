"""
Dictionary Writing System - Main application module.

This module initializes the Flask application and registers all blueprints.
"""

import os
import logging
from flask import Flask


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
    
    from app.views import main_bp
    app.register_blueprint(main_bp)
    
    # Register error handlers
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors."""
        return {'error': 'Not found'}, 404
    
    @app.errorhandler(500)
    def server_error(error):
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
    
    return app
