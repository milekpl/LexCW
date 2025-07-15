"""
Configuration settings for the Dictionary Writing System.
"""

import os


class Config:
    """Base configuration class."""
    
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard-to-guess-string'    # BaseX configuration
    BASEX_HOST = os.environ.get('BASEX_HOST') or 'localhost'
    BASEX_PORT = int(os.environ.get('BASEX_PORT') or 1984)
    BASEX_USERNAME = os.environ.get('BASEX_USERNAME') or 'admin'
    BASEX_PASSWORD = os.environ.get('BASEX_PASSWORD') or 'admin'
    BASEX_DATABASE = os.environ.get('BASEX_DATABASE') or 'dictionary'
    
    # Force BaseX connection (disable mock database)
    DEVELOPMENT_MODE = os.environ.get('DEVELOPMENT_MODE', 'false').lower() == 'true'
    USE_MOCK_DATABASE = os.environ.get('USE_MOCK_DATABASE', 'false').lower() == 'true'
    
    # Pronunciation configuration
    GOOGLE_APPLICATION_CREDENTIALS = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    AUDIO_STORAGE_PATH = os.environ.get('AUDIO_STORAGE_PATH') or 'instance/audio'
    
    # LLM configuration
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    LLM_MODEL = os.environ.get('LLM_MODEL') or 'gpt-4'
    
    # Export configuration
    EXPORT_PATH = os.environ.get('EXPORT_PATH') or 'instance/exports'
    
    @staticmethod
    def init_app(app):
        """Initialize application with this configuration."""
        # Create necessary directories
        os.makedirs(os.path.join(app.instance_path, 'audio'), exist_ok=True)
        os.makedirs(os.path.join(app.instance_path, 'exports'), exist_ok=True)


class DevelopmentConfig(Config):
    """Development configuration."""
    
    DEBUG = True
    TESTING = False


class TestingConfig(Config):
    """Testing configuration."""
    
    DEBUG = False
    TESTING = True
    BASEX_DATABASE = os.environ.get('TEST_DB_NAME') or 'dictionary_test'
    
    # Use in-memory database for testing
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    """Production configuration."""
    
    DEBUG = False
    TESTING = False
    
    # Use more secure settings in production
    @classmethod
    def init_app(cls, app):
        """Initialize application with production settings."""
        Config.init_app(app)
        
        # Log to syslog
        import logging
        from logging.handlers import SysLogHandler
        syslog_handler = SysLogHandler()
        syslog_handler.setLevel(logging.WARNING)
        app.logger.addHandler(syslog_handler)


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
