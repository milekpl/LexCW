"""
Dictionary Writing System - Main application module.

This module initializes the Flask application and registers all blueprints.
"""

import os
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
    
    # Register blueprints
    from app.api.entries import entries_bp
    app.register_blueprint(entries_bp, url_prefix='/api/entries')
    
    from app.api.search import search_bp
    app.register_blueprint(search_bp, url_prefix='/api/search')
    
    from app.api.pronunciation import pronunciation_bp
    app.register_blueprint(pronunciation_bp, url_prefix='/api/pronunciation')
    
    # Register error handlers
    from app.api.errors import register_error_handlers
    register_error_handlers(app)
    
    # Register CLI commands
    from app.cli import register_commands
    register_commands(app)
    
    @app.route('/health')
    def health_check():
        """Health check endpoint."""
        return {'status': 'ok'}
    
    return app
