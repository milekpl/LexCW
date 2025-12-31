"""Unit tests for CSS display aspect configuration.

Tests the ability to configure how relations and grammatical-info are displayed
in CSS profiles (full, label, or abbreviation).
"""

from __future__ import annotations

import pytest
from flask import Flask
from unittest.mock import patch, MagicMock

from app.models.display_profile import DisplayProfile, ProfileElement
from app.models.workset_models import db
from app.services.display_profile_service import DisplayProfileService
from app.services.css_mapping_service import CSSMappingService


class TestDisplayAspectConfiguration:
    """Test suite for configuring display aspects."""

    @pytest.fixture(autouse=True)
    def setup_cleanup(self, db_app):
        """Clean up database before and after tests."""
        with db_app.app_context():
            db.session.query(ProfileElement).delete()
            db.session.query(DisplayProfile).delete()
            db.session.commit()

    def test_profile_element_set_display_aspect(self, db_app: Flask) -> None:
        """Should set display aspect on ProfileElement."""
        with db_app.app_context():
            profile = DisplayProfile()
            profile.name = "Test Profile"
            db.session.add(profile)
            db.session.commit()
            
            elem = ProfileElement()
            elem.profile_id = profile.id
            elem.lift_element = 'relation'
            elem.css_class = 'relation'
            db.session.add(elem)
            db.session.commit()
            
            # Initially no config
            assert elem.get_display_aspect() is None
            
            # Set display aspect
            elem.set_display_aspect('abbr')
            assert elem.get_display_aspect() == 'abbr'
            
            # Change it
            elem.set_display_aspect('label')
            assert elem.get_display_aspect() == 'label'

    def test_profile_element_invalid_display_aspect(self, db_app: Flask) -> None:
        """Should reject invalid display aspects."""
        with db_app.app_context():
            profile = DisplayProfile()
            profile.name = "Test Profile"
            db.session.add(profile)
            db.session.commit()
            
            elem = ProfileElement()
            elem.profile_id = profile.id
            elem.lift_element = 'relation'
            elem.css_class = 'relation'
            
            with pytest.raises(ValueError, match="Invalid display aspect"):
                elem.set_display_aspect('invalid')

    def test_profile_element_set_display_language(self, db_app: Flask) -> None:
        """Should set display language on ProfileElement."""
        with db_app.app_context():
            profile = DisplayProfile()
            profile.name = "Test Profile"
            db.session.add(profile)
            db.session.commit()
            
            elem = ProfileElement()
            elem.profile_id = profile.id
            elem.lift_element = 'relation'
            elem.css_class = 'relation'
            db.session.add(elem)
            db.session.commit()
            
            # Initially no language configured
            assert elem.get_display_language() is None
            
            # Set language
            elem.set_display_language('en')
            assert elem.get_display_language() == 'en'
            
            # Change to all languages
            elem.set_display_language('*')
            assert elem.get_display_language() == '*'

    def test_profile_element_aspect_config_structure(self, db_app: Flask) -> None:
        """Should properly structure config with aspect and language."""
        with db_app.app_context():
            profile = DisplayProfile()
            profile.name = "Test Profile"
            db.session.add(profile)
            db.session.commit()
            
            elem = ProfileElement()
            elem.profile_id = profile.id
            elem.lift_element = 'relation'
            elem.css_class = 'relation'
            db.session.add(elem)
            db.session.commit()
            
            elem.set_display_aspect('abbr')
            elem.set_display_language('pl')
            
            assert elem.config is not None
            assert elem.config['display_aspect'] == 'abbr'
            assert elem.config['language'] == 'pl'

    def test_service_set_element_display_aspect(self, db_app: Flask) -> None:
        """Should set element display aspect via service."""
        with db_app.app_context():
            service = DisplayProfileService()
            profile = service.create_profile(name="Display Aspect Test")
            
            element = service.set_element_display_aspect(
                profile.id,
                'relation',
                'abbr'
            )
            
            # Verify display aspect
            assert element.get_display_aspect() == 'abbr'

    def test_service_get_element_display_aspect(self, db_app: Flask) -> None:
        """Should retrieve element display aspect via service."""
        with db_app.app_context():
            service = DisplayProfileService()
            profile = service.create_profile(name="Get Aspect Test")
            
            service.set_element_display_aspect(
                profile.id,
                'relation',
                'abbr',
                'en'
            )
            
            result = service.get_element_display_aspect(profile.id, 'relation')
            assert result is not None
            assert result['aspect'] == 'abbr'
            assert result['language'] == 'en'

    def test_aspect_full_is_valid(self, db_app: Flask) -> None:
        """Should accept 'full' as valid aspect."""
        with db_app.app_context():
            profile = DisplayProfile()
            profile.name = "Test Profile"
            db.session.add(profile)
            db.session.commit()
            
            elem = ProfileElement()
            elem.profile_id = profile.id
            elem.lift_element = 'grammatical-info'
            elem.css_class = 'grammatical-info'
            db.session.add(elem)
            db.session.commit()
            
            elem.set_display_aspect('full')
            assert elem.get_display_aspect() == 'full'

    def test_aspect_label_is_valid(self, db_app: Flask) -> None:
        """Should accept 'label' as valid aspect."""
        with db_app.app_context():
            profile = DisplayProfile()
            profile.name = "Test Profile"
            db.session.add(profile)
            db.session.commit()
            
            elem = ProfileElement()
            elem.profile_id = profile.id
            elem.lift_element = 'relation'
            elem.css_class = 'relation'
            db.session.add(elem)
            db.session.commit()
            
            elem.set_display_aspect('label')
            assert elem.get_display_aspect() == 'label'

    def test_aspect_abbr_is_valid(self, db_app: Flask) -> None:
        """Should accept 'abbr' as valid aspect."""
        with db_app.app_context():
            profile = DisplayProfile()
            profile.name = "Test Profile"
            db.session.add(profile)
            db.session.commit()
            
            elem = ProfileElement()
            elem.profile_id = profile.id
            elem.lift_element = 'relation'
            elem.css_class = 'relation'
            db.session.add(elem)
            db.session.commit()
            
            elem.set_display_aspect('abbr')
            assert elem.get_display_aspect() == 'abbr'


class TestCSSDisplayAspectApplication:
    """Test suite for applying display aspects during CSS rendering."""

    def test_css_mapping_service_apply_display_aspects_exists(
        self, db_app: Flask
    ) -> None:
        """Should have apply_display_aspects method."""
        with db_app.app_context():
            service = CSSMappingService()
            assert hasattr(service, 'apply_display_aspects')
            assert callable(getattr(service, 'apply_display_aspects'))

    def test_css_mapping_relation_display_aspect_method_exists(
        self, db_app: Flask
    ) -> None:
        """Should have _apply_relation_display_aspect method."""
        with db_app.app_context():
            service = CSSMappingService()
            assert hasattr(service, '_apply_relation_display_aspect')

    def test_css_mapping_grammatical_display_aspect_method_exists(
        self, db_app: Flask
    ) -> None:
        """Should have _apply_grammatical_display_aspect method."""
        with db_app.app_context():
            service = CSSMappingService()
            assert hasattr(service, '_apply_grammatical_display_aspect')

    def test_css_mapping_build_range_lookup_method_exists(
        self, db_app: Flask
    ) -> None:
        """Should have _build_range_lookup method."""
        with db_app.app_context():
            service = CSSMappingService()
            assert hasattr(service, '_build_range_lookup')


class TestProfileElementIntegration:
    """Integration tests for ProfileElement with DisplayProfile."""

    def test_profile_element_belongs_to_profile(self, db_app: Flask) -> None:
        """ProfileElement should be associated with DisplayProfile."""
        with db_app.app_context():
            profile = DisplayProfile()
            profile.name = "Test Profile"
            db.session.add(profile)
            db.session.commit()
            
            elem = ProfileElement()
            elem.profile_id = profile.id
            elem.lift_element = 'relation'
            elem.css_class = 'relation'
            db.session.add(elem)
            db.session.commit()
            
            # Verify association
            assert elem.profile_id == profile.id
            assert elem in profile.elements

    def test_multiple_elements_with_different_aspects(
        self, db_app: Flask
    ) -> None:
        """Profile should support multiple elements with different aspects."""
        with db_app.app_context():
            profile = DisplayProfile()
            profile.name = "Test Profile"
            db.session.add(profile)
            db.session.commit()
            
            # Create relation element with abbr aspect
            relation = ProfileElement()
            relation.profile_id = profile.id
            relation.lift_element = 'relation'
            relation.css_class = 'relation'
            relation.set_display_aspect('abbr')
            db.session.add(relation)
            
            # Create grammatical-info element with label aspect
            gram_info = ProfileElement()
            gram_info.profile_id = profile.id
            gram_info.lift_element = 'grammatical-info'
            gram_info.css_class = 'grammatical-info'
            gram_info.set_display_aspect('label')
            db.session.add(gram_info)
            
            db.session.commit()
            
            # Verify both elements
            assert relation.get_display_aspect() == 'abbr'
            assert gram_info.get_display_aspect() == 'label'

    def test_element_aspect_persistence(self, db_app: Flask) -> None:
        """Display aspect should persist across database sessions."""
        with db_app.app_context():
            profile = DisplayProfile()
            profile.name = "Test Profile"
            db.session.add(profile)
            db.session.commit()
            
            elem = ProfileElement()
            elem.profile_id = profile.id
            elem.lift_element = 'relation'
            elem.css_class = 'relation'
            db.session.add(elem)
            db.session.commit()
            
            elem.set_display_aspect('abbr')
            elem.set_display_language('en')
            db.session.commit()
            elem_id = elem.id
            
            # Retrieve in new session
            db.session.expunge_all()
            retrieved_elem = db.session.get(ProfileElement, elem_id)
            
            assert retrieved_elem is not None
            assert retrieved_elem.get_display_aspect() == 'abbr'
            assert retrieved_elem.get_display_language() == 'en'

    def test_relation_label_aspect_renders_full_label(self, db_app: Flask) -> None:
        """When a relation element is configured with display_aspect 'label',
        rendering should use the full label from ranges rather than the abbreviation.
        """
        with db_app.app_context():
            # Create a simple display profile with a relation element set to 'label'
            profile = DisplayProfile()
            profile.name = "Relation Label Profile"
            db.session.add(profile)
            db.session.commit()

            rel_elem = ProfileElement()
            rel_elem.profile_id = profile.id
            rel_elem.lift_element = 'relation'
            rel_elem.css_class = 'relation'
            rel_elem.set_display_aspect('label')
            db.session.add(rel_elem)
            db.session.commit()

            # Sample entry with a relation of type 'antonym'
            lift_xml = '''
            <entry id="test_entry">
                <sense id="sense1">
                    <relation type="antonym" ref="uuid-target-2" data-headword="slow"/>
                </sense>
            </entry>
            '''

            service = CSSMappingService()

            # Mock the dictionary service to provide ranges with lexical-relation mappings
            ranges = {
                'lexical-relation': {
                    'values': [
                        {'id': 'antonym', 'label': {'en': 'Antonym'}}
                    ]
                }
            }
            mock_dict_service = MagicMock()
            mock_dict_service.get_ranges.return_value = ranges

            with patch('flask.current_app') as mock_current_app:
                mock_injector = MagicMock()
                mock_injector.get.return_value = mock_dict_service
                mock_current_app.injector = mock_injector

                html = service.render_entry(lift_xml, profile)

                # Expect the full label 'Antonym' rather than abbreviation 'ant'
                assert 'Antonym' in html
                assert 'ant ' not in html or ' ant<' not in html