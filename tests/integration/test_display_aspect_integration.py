"""Integration tests for display aspect functionality.

Tests the full rendering pipeline with different display aspects (abbr, label, full)
for various LIFT elements including relations, grammatical-info, variants, and traits.
"""

from __future__ import annotations

import pytest
from flask import Flask

from app.services.css_mapping_service import CSSMappingService
from app.models.display_profile import DisplayProfile, ProfileElement
from app.models.workset_models import db


class TestDisplayAspectIntegration:
    """Integration tests for display aspect rendering."""

    @pytest.fixture
    def css_service(self, tmp_path):
        return CSSMappingService(storage_path=tmp_path / "profiles.json")

    @pytest.fixture
    def db_app(self):
        """Create a test Flask app with database."""
        from app import create_app
        from app.models.workset_models import db
        
        app = create_app('testing')
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()

    def test_relation_display_aspect_abbr_vs_label(self, css_service, db_app):
        """Test that relations can be displayed with abbreviations vs full labels.

        Note: This test uses relation types that exist in minimal.lift-ranges
        ('Part' and 'Specific') rather than 'antonym'/'synonym' which only
        exist in the full sample-lift-file.lift-ranges.
        """
        with db_app.app_context():
            # Create profile with relation element set to 'label' aspect
            profile = DisplayProfile(name="Label Test")
            db.session.add(profile)
            db.session.commit()

            rel_elem = ProfileElement(
                profile_id=profile.id,
                lift_element='relation',
                css_class='relation'
            )
            rel_elem.set_display_aspect('label')
            db.session.add(rel_elem)
            db.session.commit()

            # Sample entry with relations using types from minimal.lift-ranges
            entry_xml = '''
            <entry id="test_entry">
                <lexical-unit>
                    <form lang="en"><text>test-word</text></form>
                </lexical-unit>
                <sense id="sense1">
                    <relation type="Specific" ref="uuid-target-2" data-headword="slow"/>
                    <relation type="Part" ref="uuid-target-3" data-headword="fast"/>
                </sense>
            </entry>
            '''

            # Render with label aspect
            html_label = css_service.render_entry(entry_xml, profile)

            # Should contain full labels, not abbreviations
            # 'Specific' should appear (label aspect uses the type value when no label exists in ranges)
            assert 'Specific' in html_label
            assert 'Part' in html_label

            # Now test with abbreviation aspect
            rel_elem.set_display_aspect('abbr')
            db.session.commit()

            html_abbr = css_service.render_entry(entry_xml, profile)

            # Should contain abbreviations (pt for Part, spec for Specific)
            assert 'pt' in html_abbr or 'spec' in html_abbr

    def test_grammatical_info_display_aspect(self, css_service, db_app):
        """Test that grammatical-info can be displayed with different aspects."""
        with db_app.app_context():
            # Create profile with grammatical-info element
            profile = DisplayProfile(name="Grammar Test")
            db.session.add(profile)
            db.session.commit()
            
            gram_elem = ProfileElement(
                profile_id=profile.id,
                lift_element='grammatical-info',
                css_class='grammatical-info'
            )
            gram_elem.set_display_aspect('label')
            db.session.add(gram_elem)
            db.session.commit()
            
            # Sample entry with grammatical info
            entry_xml = '''
            <entry id="test_entry">
                <lexical-unit>
                    <form lang="en"><text>test-word</text></form>
                </lexical-unit>
                <sense id="sense1">
                    <grammatical-info value="noun"/>
                </sense>
            </entry>
            '''
            
            # Render with label aspect
            html_label = css_service.render_entry(entry_xml, profile)
            
            # Should contain full label
            assert 'Noun' in html_label or 'noun' in html_label
            
            # Test with abbreviation aspect
            gram_elem.set_display_aspect('abbr')
            db.session.commit()
            
            html_abbr = css_service.render_entry(entry_xml, profile)
            
            # Should contain abbreviation
            assert 'n' in html_abbr or 'N' in html_abbr

    def test_variant_display_aspect(self, css_service, db_app):
        """Test that variants can be displayed with different aspects."""
        with db_app.app_context():
            # Create profile with variant element
            profile = DisplayProfile(name="Variant Test")
            db.session.add(profile)
            db.session.commit()
            
            variant_elem = ProfileElement(
                profile_id=profile.id,
                lift_element='variant',
                css_class='variant'
            )
            variant_elem.set_display_aspect('label')
            db.session.add(variant_elem)
            db.session.commit()
            
            # Sample entry with variant
            entry_xml = '''
            <entry id="test_entry">
                <lexical-unit>
                    <form lang="en"><text>test-word</text></form>
                    <variant type="spelling">
                        <form lang="en"><text>alternate-spelling</text></form>
                    </variant>
                </lexical-unit>
            </entry>
            '''
            
            # Render with label aspect
            html_label = css_service.render_entry(entry_xml, profile)
            
            # Should contain full label
            assert 'Spelling' in html_label or 'spelling' in html_label
            
            # Test with abbreviation aspect
            variant_elem.set_display_aspect('abbr')
            db.session.commit()
            
            html_abbr = css_service.render_entry(entry_xml, profile)
            
            # Should contain abbreviation
            assert 'spell' in html_abbr or 'Spell' in html_abbr

    def test_trait_display_aspect(self, css_service, db_app):
        """Test that traits can be displayed with different aspects."""
        with db_app.app_context():
            # Create profile with trait element
            profile = DisplayProfile(name="Trait Test")
            db.session.add(profile)
            db.session.commit()
            
            trait_elem = ProfileElement(
                profile_id=profile.id,
                lift_element='trait',
                css_class='trait'
            )
            trait_elem.set_display_aspect('label')
            db.session.add(trait_elem)
            db.session.commit()
            
            # Sample entry with trait
            entry_xml = '''
            <entry id="test_entry">
                <lexical-unit>
                    <form lang="en"><text>test-word</text></form>
                </lexical-unit>
                <sense id="sense1">
                    <trait name="semantic-domain" value="science"/>
                </sense>
            </entry>
            '''
            
            # Render with label aspect
            html_label = css_service.render_entry(entry_xml, profile)
            
            # Should contain full label
            assert 'Science' in html_label or 'science' in html_label
            
            # Test with abbreviation aspect
            trait_elem.set_display_aspect('abbr')
            db.session.commit()
            
            html_abbr = css_service.render_entry(entry_xml, profile)
            
            # Should contain abbreviation
            assert 'sci' in html_abbr or 'Sci' in html_abbr

    def test_mixed_display_aspects(self, css_service, db_app):
        """Test that different elements can have different display aspects.

        Note: Uses 'Specific' (from minimal.lift-ranges) instead of 'antonym'.
        """
        with db_app.app_context():
            # Create profile with multiple elements with different aspects
            profile = DisplayProfile(name="Mixed Test")
            db.session.add(profile)
            db.session.commit()

            # Relation with label aspect
            rel_elem = ProfileElement(
                profile_id=profile.id,
                lift_element='relation',
                css_class='relation'
            )
            rel_elem.set_display_aspect('label')
            db.session.add(rel_elem)

            # Grammatical-info with abbreviation aspect
            gram_elem = ProfileElement(
                profile_id=profile.id,
                lift_element='grammatical-info',
                css_class='grammatical-info'
            )
            gram_elem.set_display_aspect('abbr')
            db.session.add(gram_elem)
            db.session.commit()

            # Sample entry with both elements
            entry_xml = '''
            <entry id="test_entry">
                <lexical-unit>
                    <form lang="en"><text>test-word</text></form>
                </lexical-unit>
                <sense id="sense1">
                    <grammatical-info value="noun"/>
                    <relation type="Specific" ref="uuid-target-2" data-headword="slow"/>
                </sense>
            </entry>
            '''

            html = css_service.render_entry(entry_xml, profile)

            # Should have full label for relation
            assert 'Specific' in html

            # Should have abbreviation for grammatical-info
            assert 'n' in html or 'N' in html

    def test_display_aspect_fallback_behavior(self, css_service, db_app):
        """Test fallback behavior when range mappings are missing."""
        with db_app.app_context():
            # Create profile with relation element set to label aspect
            profile = DisplayProfile(name="Fallback Test")
            db.session.add(profile)
            db.session.commit()
            
            rel_elem = ProfileElement(
                profile_id=profile.id,
                lift_element='relation',
                css_class='relation'
            )
            rel_elem.set_display_aspect('label')
            db.session.add(rel_elem)
            db.session.commit()
            
            # Sample entry with a relation type that might not have a label mapping
            entry_xml = '''
            <entry id="test_entry">
                <lexical-unit>
                    <form lang="en"><text>test-word</text></form>
                </lexical-unit>
                <sense id="sense1">
                    <relation type="unknown-lexical-relation" ref="uuid-target-2" data-headword="something"/>
                </sense>
            </entry>
            '''
            
            html = css_service.render_entry(entry_xml, profile)
            
            # Should fall back to humanized label for lexical relation
            assert 'Unknown Lexical Relation' in html or 'unknown-lexical-relation' in html

    def test_display_aspect_default_behavior(self, css_service, db_app):
        """Test that elements without display_aspect use default behavior (abbreviations)."""
        with db_app.app_context():
            # Create profile with relation element but no display_aspect set
            profile = DisplayProfile(name="Default Test")
            db.session.add(profile)
            db.session.commit()
            
            rel_elem = ProfileElement(
                profile_id=profile.id,
                lift_element='relation',
                css_class='relation'
                # No display_aspect set
            )
            db.session.add(rel_elem)
            db.session.commit()
            
            # Sample entry with relation
            entry_xml = '''
            <entry id="test_entry">
                <lexical-unit>
                    <form lang="en"><text>test-word</text></form>
                </lexical-unit>
                <sense id="sense1">
                    <relation type="antonym" ref="uuid-target-2" data-headword="slow"/>
                </sense>
            </entry>
            '''
            
            html = css_service.render_entry(entry_xml, profile)
            
            # Should use default behavior (abbreviations)
            assert 'ant' in html or 'Ant' in html
