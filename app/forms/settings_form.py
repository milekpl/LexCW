from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length
from app.utils.language_utils import load_available_languages

class SettingsForm(FlaskForm):
    """Form for updating project settings."""
    project_name = StringField(
        'Project Name',
        validators=[DataRequired(), Length(min=2, max=100)],
        description="The name of the current lexicography project."
    )

    source_language_code = SelectField(
        'Source Language (Vernacular)',
        # Choices will be set in __init__
        validators=[DataRequired()],
        description="The primary language of the dictionary entries (often the local or indigenous language)."
    )
    source_language_name = StringField(
        'Source Language Display Name',
        validators=[DataRequired(), Length(min=2, max=50)],
        description="How the source language name will be displayed (e.g., 'Sena', 'English')."
    )

    target_language_code = SelectField(
        'Target Language',
        # Choices will be set in __init__
        validators=[DataRequired()],
        description="The language used for definitions and translations (often a national or international language)."
    )
    target_language_name = StringField(
        'Target Language Display Name',
        validators=[DataRequired(), Length(min=2, max=50)],
        description="How the target language name will be displayed (e.g., 'Portuguese', 'English')."
    )

    submit = SubmitField('Save Settings')

    def __init__(self, *args, **kwargs):
        super(SettingsForm, self).__init__(*args, **kwargs)
        available_languages = load_available_languages()
        self.source_language_code.choices = available_languages
        self.target_language_code.choices = available_languages

    def populate_from_config(self, config_manager):
        """Populates the form fields from the ConfigManager."""
        settings = config_manager.get_all_settings()
        self.project_name.data = settings.get('project_name')

        source_lang = settings.get('source_language', {})
        self.source_language_code.data = source_lang.get('code')
        self.source_language_name.data = source_lang.get('name')

        target_lang = settings.get('target_language', {})
        self.target_language_code.data = target_lang.get('code')
        self.target_language_name.data = target_lang.get('name')

    def to_dict(self) -> dict:
        """Converts form data to a dictionary suitable for ConfigManager."""
        return {
            'project_name': self.project_name.data,
            'source_language': {
                'code': self.source_language_code.data,
                'name': self.source_language_name.data
            },
            'target_language': {
                'code': self.target_language_code.data,
                'name': self.target_language_name.data
            }
        }
