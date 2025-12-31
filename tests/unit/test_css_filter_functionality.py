"""Unit tests for CSS filter checking functionality.

Tests the _check_filter method and filter-based element matching
in the CSS mapping service.
"""

from __future__ import annotations

import pytest
from flask import Flask
import xml.etree.ElementTree as ET

from app.models.display_profile import DisplayProfile, ProfileElement
from app.models.workset_models import db
from app.services.css_mapping_service import CSSMappingService


class TestCSSFilterFunctionality:
    """Test suite for CSS filter checking functionality."""

    def test_check_filter_empty_string_matches_all(self, db_app: Flask) -> None:
        """Empty filter string should match all elements."""
        with db_app.app_context():
            service = CSSMappingService()
            elem = ET.Element('relation')
            elem.set('type', 'synonym')

            # Empty string should match
            assert service._check_filter(elem, '', 'relation') is True
            # None should match
            assert service._check_filter(elem, None, 'relation') is True
            # Whitespace should match
            assert service._check_filter(elem, '   ', 'relation') is True

    def test_check_filter_inclusion_matching(self, db_app: Flask) -> None:
        """Filter with comma-separated values should match any."""
        with db_app.app_context():
            service = CSSMappingService()
            elem = ET.Element('relation')
            elem.set('type', 'synonym')

            # synonym should match the filter synonym,antonym
            assert service._check_filter(elem, 'synonym,antonym', 'relation') is True

            # hypernym should not match synonym,antonym
            elem.set('type', 'hypernym')
            assert service._check_filter(elem, 'synonym,antonym', 'relation') is False

    def test_check_filter_exclusion_matching(self, db_app: Flask) -> None:
        """Filter starting with ! should exclude matching elements."""
        with db_app.app_context():
            service = CSSMappingService()
            elem = ET.Element('relation')
            elem.set('type', 'synonym')

            # synonym should not match !synonym
            assert service._check_filter(elem, '!synonym', 'relation') is False

            # hypernym should match !synonym
            elem.set('type', 'hypernym')
            assert service._check_filter(elem, '!synonym', 'relation') is True

    def test_check_filter_case_insensitive(self, db_app: Flask) -> None:
        """Filter matching should be case insensitive."""
        with db_app.app_context():
            service = CSSMappingService()
            elem = ET.Element('relation')
            elem.set('type', 'SYNONYM')

            # Should match regardless of case
            assert service._check_filter(elem, 'synonym', 'relation') is True
            assert service._check_filter(elem, 'SYNONYM', 'relation') is True
            assert service._check_filter(elem, 'Synonym', 'relation') is True

    def test_check_filter_exclusion_case_insensitive(self, db_app: Flask) -> None:
        """Exclusion filter should also be case insensitive."""
        with db_app.app_context():
            service = CSSMappingService()
            elem = ET.Element('relation')
            elem.set('type', 'synonym')

            # Should be excluded regardless of case
            assert service._check_filter(elem, '!SYNONYM', 'relation') is False
            assert service._check_filter(elem, '!synonym', 'relation') is False

    def test_check_filter_mixed_inclusion_exclusion(self, db_app: Flask) -> None:
        """Filter can have both inclusions and exclusions."""
        with db_app.app_context():
            service = CSSMappingService()

            elem = ET.Element('relation')

            # Match synonym but exclude hypernym
            elem.set('type', 'synonym')
            assert service._check_filter(elem, 'synonym,antonym,!hypernym', 'relation') is True

            elem.set('type', 'hypernym')
            assert service._check_filter(elem, 'synonym,antonym,!hypernym', 'relation') is False

    def test_check_filter_trait_matching(self, db_app: Flask) -> None:
        """Filter should match trait elements by name."""
        with db_app.app_context():
            service = CSSMappingService()
            elem = ET.Element('trait')
            elem.set('name', 'morph-type')
            elem.set('value', 'phr')

            # Should match exact trait name
            assert service._check_filter(elem, 'morph-type', 'trait') is True

            # Should not match different trait name
            elem.set('name', 'domain-type')
            assert service._check_filter(elem, 'morph-type', 'trait') is False

    def test_check_filter_field_matching(self, db_app: Flask) -> None:
        """Filter should match field elements by type."""
        with db_app.app_context():
            service = CSSMappingService()
            elem = ET.Element('field')
            elem.set('type', 'lexical-unit')
            elem.set('value', 'test')

            # Should match exact field type
            assert service._check_filter(elem, 'lexical-unit', 'field') is True

            # Should not match different field type
            elem.set('type', 'definition')
            assert service._check_filter(elem, 'lexical-unit', 'field') is False

    def test_check_filter_preserves_original_type(self, db_app: Flask) -> None:
        """Filter should use original type if preserved."""
        with db_app.app_context():
            service = CSSMappingService()
            elem = ET.Element('relation')
            elem.set('type', 'new-synonym')  # Changed type
            elem.set('data-original-type', 'synonym')  # Original preserved

            # Should use original type for matching
            assert service._check_filter(elem, 'synonym', 'relation') is True
            assert service._check_filter(elem, 'new-synonym', 'relation') is False


class TestCSSMappingServiceProfileManagement:
    """Test profile management in CSS mapping service."""

    @pytest.fixture(autouse=True)
    def setup_cleanup(self, db_app):
        """Clean up database before and after tests."""
        with db_app.app_context():
            db.session.query(ProfileElement).delete()
            db.session.query(DisplayProfile).delete()
            db.session.commit()

    def test_create_profile_via_db(self, db_app: Flask) -> None:
        """Should create a new profile via database."""
        with db_app.app_context():
            profile = DisplayProfile()
            profile.name = 'Test Profile'
            profile.description = 'A test profile'
            db.session.add(profile)
            db.session.commit()
            profile_id = profile.id

            # Retrieve and verify
            retrieved = db.session.get(DisplayProfile, profile_id)
            assert retrieved is not None
            assert retrieved.name == 'Test Profile'
            assert retrieved.description == 'A test profile'

    def test_get_profile_via_db(self, db_app: Flask) -> None:
        """Should retrieve a profile by ID via database."""
        with db_app.app_context():
            profile = DisplayProfile()
            profile.name = 'Get Test'
            db.session.add(profile)
            db.session.commit()
            profile_id = profile.id

            retrieved = db.session.get(DisplayProfile, profile_id)
            assert retrieved is not None
            assert retrieved.id == profile_id
            assert retrieved.name == 'Get Test'

    def test_get_nonexistent_profile(self, db_app: Flask) -> None:
        """Should return None for nonexistent profile."""
        with db_app.app_context():
            result = db.session.get(DisplayProfile, 99999)
            assert result is None

    def test_list_profiles(self, db_app: Flask) -> None:
        """Should list all profiles."""
        with db_app.app_context():
            profile1 = DisplayProfile()
            profile1.name = 'Profile 1'
            db.session.add(profile1)

            profile2 = DisplayProfile()
            profile2.name = 'Profile 2'
            db.session.add(profile2)

            db.session.commit()

            profiles = db.session.query(DisplayProfile).all()

            assert len(profiles) == 2
            names = [p.name for p in profiles]
            assert 'Profile 1' in names
            assert 'Profile 2' in names

    def test_update_profile(self, db_app: Flask) -> None:
        """Should update an existing profile."""
        with db_app.app_context():
            profile = DisplayProfile()
            profile.name = 'Original Name'
            db.session.add(profile)
            db.session.commit()

            profile.name = 'New Name'
            db.session.commit()

            # Refresh and verify
            db.session.refresh(profile)
            assert profile.name == 'New Name'

    def test_delete_profile(self, db_app: Flask) -> None:
        """Should delete a profile."""
        with db_app.app_context():
            profile = DisplayProfile()
            profile.name = 'To Delete'
            db.session.add(profile)
            db.session.commit()
            profile_id = profile.id

            db.session.delete(profile)
            db.session.commit()

            result = db.session.get(DisplayProfile, profile_id)
            assert result is None

    def test_delete_nonexistent_profile(self, db_app: Flask) -> None:
        """Should not error when deleting nonexistent profile."""
        with db_app.app_context():
            # Should not raise
            profile = DisplayProfile.query.filter_by(id=99999).first()
            assert profile is None


class TestCSSRangeLookupBuilding:
    """Test range lookup building functionality."""

    def test_build_range_lookup_empty_ranges(self, db_app: Flask) -> None:
        """Should handle empty ranges gracefully."""
        with db_app.app_context():
            service = CSSMappingService()
            # Mock the dictionary service to return empty ranges
            from unittest.mock import patch, MagicMock
            mock_dict_service = MagicMock()
            mock_dict_service.get_ranges.return_value = {}

            with patch('flask.current_app'):
                result = service._build_range_lookup()

                assert result == {}

    def test_build_range_lookup_with_values(self, db_app: Flask) -> None:
        """Should build lookup map from range values."""
        with db_app.app_context():
            service = CSSMappingService()

            ranges = {
                'grammatical-info': {
                    'values': [
                        {'id': 'Noun', 'abbrev': 'n', 'label': {'en': 'Noun'}},
                        {'id': 'Verb', 'abbrev': 'v', 'label': {'en': 'Verb'}}
                    ]
                }
            }

            from unittest.mock import patch, MagicMock
            mock_dict_service = MagicMock()
            mock_dict_service.get_ranges.return_value = ranges

            with patch('flask.current_app') as mock_current_app:
                mock_injector = MagicMock()
                mock_injector.get.return_value = mock_dict_service
                mock_current_app.injector = mock_injector

                result = service._build_range_lookup(lang='en')

                assert 'grammatical-info' in result
                assert result['grammatical-info'].get('Noun') == 'n'
                assert result['grammatical-info'].get('Verb') == 'v'

    def test_build_range_label_lookup(self, db_app: Flask) -> None:
        """Should build label lookup map."""
        with db_app.app_context():
            service = CSSMappingService()

            ranges = {
                'lexical-relation': {
                    'values': [
                        {'id': 'synonym', 'label': {'en': 'Synonym'}},
                        {'id': 'antonym', 'label': {'en': 'Antonym'}}
                    ]
                }
            }

            from unittest.mock import patch, MagicMock
            mock_dict_service = MagicMock()
            mock_dict_service.get_ranges.return_value = ranges

            with patch('flask.current_app') as mock_current_app:
                mock_injector = MagicMock()
                mock_injector.get.return_value = mock_dict_service
                mock_current_app.injector = mock_injector

                result = service._build_range_label_lookup(lang='en')

                assert 'lexical-relation' in result
                assert result['lexical-relation'].get('synonym') == 'Synonym'
                assert result['lexical-relation'].get('antonym') == 'Antonym'
