"""
Field Visibility Defaults Routes

Routes for managing field visibility defaults at the project level.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, g
from app.services.user_preferences_service import UserPreferencesService
from app.models.project_settings import ProjectSettings

field_visibility_bp = Blueprint('field_visibility', __name__, url_prefix='/settings')


@field_visibility_bp.route('/projects/<int:project_id>/field-visibility', methods=['GET', 'POST'])
def field_visibility_defaults(project_id: int):
    """Manage field visibility defaults for a project (admin only)."""
    # Check admin access
    user_id = g.current_user.id if hasattr(g, 'current_user') and g.current_user else None
    if not user_id:
        flash('Please log in to access this page', 'warning')
        return redirect(url_for('auth.login'))

    if not (g.current_user.is_admin if hasattr(g, 'current_user') and g.current_user else False):
        flash('Admin access required', 'danger')
        return redirect(url_for('main.index'))

    project = ProjectSettings.query.get(project_id)
    if not project:
        flash('Project not found', 'danger')
        return redirect(url_for('settings.list_projects'))

    # Section and field definitions
    sections = {
        'basic-info': 'Basic Information',
        'custom-fields': 'Custom Fields',
        'notes': 'Entry Notes',
        'pronunciation': 'Pronunciation',
        'variants': 'Variants',
        'direct-variants': 'Direct Variants',
        'relations': 'Relations',
        'annotations': 'Annotations',
        'senses': 'Senses & Definitions'
    }

    fields = {
        'basic-info': {
            'lexical-unit': 'Lexical Unit',
            'pronunciation': 'Pronunciation',
            'variants': 'Variants'
        },
        'custom-fields': {
            'custom-fields-all': 'All Custom Fields'
        },
        'notes': {
            'notes-all': 'All Notes'
        },
        'pronunciation': {
            'pronunciation-all': 'All Pronunciations'
        },
        'variants': {
            'variants-all': 'All Variants'
        },
        'direct-variants': {
            'direct-variants-all': 'All Direct Variants'
        },
        'relations': {
            'relations-all': 'All Relations'
        },
        'annotations': {
            'annotations-all': 'All Entry Annotations'
        },
        'senses': {
            'sense-definition': 'Definition',
            'sense-gloss': 'Gloss',
            'sense-grammatical': 'Part of Speech',
            'sense-domain': 'Domain/Usage',
            'sense-examples': 'Examples',
            'sense-illustrations': 'Illustrations',
            'sense-relations': 'Sense Relations',
            'sense-variants': 'Variant Relations',
            'sense-reversals': 'Reversals',
            'sense-annotations': 'Sense Annotations'
        }
    }

    if request.method == 'POST':
        # Build settings from form data
        settings = {'sections': {}, 'fields': {}}

        # Get section settings
        for section_id in sections:
            checkbox_name = f'section_{section_id}'
            settings['sections'][section_id] = checkbox_name in request.form

        # Get field settings
        for section_id, section_fields in fields.items():
            settings['fields'][section_id] = {}
            for field_id in section_fields:
                checkbox_name = f'field_{section_id}_{field_id}'
                settings['fields'][section_id][field_id] = checkbox_name in request.form

        # Save to database
        success, error = UserPreferencesService.save_project_defaults(
            project_id=project_id,
            settings=settings,
            admin_user_id=user_id
        )

        if success:
            flash('Field visibility defaults saved successfully', 'success')
            return redirect(url_for('field_visibility.field_visibility_defaults', project_id=project_id))
        else:
            flash(f'Error saving defaults: {error}', 'danger')

    # Get current defaults
    current_defaults = UserPreferencesService.get_project_defaults(project_id)
    defaults = {
        'sections': current_defaults.get('sections', {}),
        'fields': current_defaults.get('fields', {})
    }

    return render_template(
        'field_visibility_defaults.html',
        title='Field Visibility Defaults',
        project_id=project_id,
        project_name=project.project_name,
        sections=sections,
        fields=fields,
        defaults=defaults
    )


def register_blueprints(app):
    app.register_blueprint(field_visibility_bp)
