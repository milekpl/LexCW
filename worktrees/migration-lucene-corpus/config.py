"""
Configuration settings for the Lexicographic Curation Workbench.
"""

import os


class Config:
    """Base configuration class."""
    
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard-to-guess-string'
    
    # BaseX configuration
    BASEX_HOST = os.environ.get('BASEX_HOST') or 'localhost'
    BASEX_PORT = int(os.environ.get('BASEX_PORT') or 1984)
    BASEX_USERNAME = os.environ.get('BASEX_USERNAME') or 'admin'
    BASEX_PASSWORD = os.environ.get('BASEX_PASSWORD') or 'admin'
    BASEX_DATABASE = os.environ.get('BASEX_DATABASE') or 'dictionary'
    
    # Force BaseX connection (disable mock database)
    DEVELOPMENT_MODE = os.environ.get('DEVELOPMENT_MODE', 'false').lower() == 'true'
    USE_MOCK_DATABASE = os.environ.get('USE_MOCK_DATABASE', 'false').lower() == 'true'
    
    # PostgreSQL configuration
    PG_HOST = os.environ.get('POSTGRES_HOST') or 'localhost'
    PG_PORT = int(os.environ.get('POSTGRES_PORT') or 5432)
    PG_USER = os.environ.get('POSTGRES_USER') or 'dict_user'
    PG_PASSWORD = os.environ.get('POSTGRES_PASSWORD') or 'dict_pass'
    PG_DATABASE = os.environ.get('POSTGRES_DB') or 'dictionary_analytics'
    
    # SQLAlchemy configuration
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
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
    
    # SQLAlchemy configuration
    SQLALCHEMY_DATABASE_URI = (
        f"postgresql://{os.environ.get('POSTGRES_USER') or 'dict_user'}:"
        f"{os.environ.get('POSTGRES_PASSWORD') or 'dict_pass'}@"
        f"{os.environ.get('POSTGRES_HOST') or 'localhost'}:"
        f"{int(os.environ.get('POSTGRES_PORT') or 5432)}/"
        f"{os.environ.get('POSTGRES_DB') or 'dictionary_analytics'}"
    )


class TestingConfig(Config):
    """Testing configuration."""

    DEBUG = False
    TESTING = True
    # Use a safe database name that passes the safety check (starts with 'test_', no protected patterns)
    BASEX_DATABASE = os.environ.get('TEST_DB_NAME') or 'test_entries_db'
    
    # Disable Redis caching during tests to ensure test isolation
    # Each test should start with a clean state without cached data from previous tests
    REDIS_ENABLED = False
    
    # PostgreSQL test configuration
    PG_HOST = os.environ.get('POSTGRES_TEST_HOST') or 'localhost'
    PG_PORT = int(os.environ.get('POSTGRES_TEST_PORT') or 5432)
    PG_USER = os.environ.get('POSTGRES_TEST_USER') or 'dict_user'
    PG_PASSWORD = os.environ.get('POSTGRES_TEST_PASSWORD') or 'dict_pass'
    PG_DATABASE = os.environ.get('POSTGRES_TEST_DB') or 'dictionary_test'
    
    # SQLAlchemy test configuration - use in-memory SQLite for testing
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    
    # Disable CSRF for testing
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    """Production configuration."""
    
    DEBUG = False
    TESTING = False
    
    # SQLAlchemy configuration
    SQLALCHEMY_DATABASE_URI = (
        f"postgresql://{os.environ.get('POSTGRES_USER') or 'dict_user'}:"
        f"{os.environ.get('POSTGRES_PASSWORD') or 'dict_pass'}@"
        f"{os.environ.get('POSTGRES_HOST') or 'localhost'}:"
        f"{int(os.environ.get('POSTGRES_PORT') or 5432)}/"
        f"{os.environ.get('POSTGRES_DB') or 'dictionary_analytics'}"
    )
    
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
