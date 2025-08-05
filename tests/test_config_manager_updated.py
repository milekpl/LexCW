import pytest
from flask import Flask
from app.models.project_settings import db, ProjectSettings
from app.config_manager_updated import ConfigManager

@pytest.fixture
def app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["TESTING"] = True
    
    # Initialize extensions
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def config_manager(app):
    manager = ConfigManager(app)
    return manager

def test_default_settings(config_manager):
    """Test that default settings are created."""
    # Default settings should be created during initialization
    assert config_manager.get_current_settings() is not None
    
    # Default project name
    assert config_manager.get_project_name() == "Lexicographic Curation Workbench"
    
    # Default source language
    source_lang = config_manager.get_source_language()
    assert source_lang["code"] == "en"
    assert source_lang["name"] == "English"
    
    # Default target language (singular, for backward compatibility)
    target_lang = config_manager.get_target_language()
    assert target_lang["code"] == "fr"
    assert target_lang["name"] == "French"
    
    # Default target languages (plural, new functionality)
    target_langs = config_manager.get_target_languages()
    assert len(target_langs) == 1
    assert target_langs[0]["code"] == "fr"
    assert target_langs[0]["name"] == "French"

def test_update_project_settings(config_manager):
    """Test updating project settings."""
    # Update with new values
    config_manager.update_project_settings(
        project_name="Test Dictionary",
        source_language={"code": "de", "name": "German"},
        target_languages=[
            {"code": "en", "name": "English"},
            {"code": "fr", "name": "French"},
            {"code": "es", "name": "Spanish"}
        ]
    )
    
    # Check updated values
    assert config_manager.get_project_name() == "Test Dictionary"
    
    source_lang = config_manager.get_source_language()
    assert source_lang["code"] == "de"
    assert source_lang["name"] == "German"
    
    # Check backward compatibility
    target_lang = config_manager.get_target_language()
    assert target_lang["code"] == "en"
    assert target_lang["name"] == "English"
    
    # Check new functionality
    target_langs = config_manager.get_target_languages()
    assert len(target_langs) == 3
    assert target_langs[0]["code"] == "en"
    assert target_langs[1]["code"] == "fr"
    assert target_langs[2]["code"] == "es"
