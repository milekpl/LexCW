"""
Test help page route and content.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flask.testing import FlaskClient


def test_help_route_exists(client: FlaskClient) -> None:
    """Test that the help route is accessible."""
    response = client.get('/help')
    assert response.status_code == 200


def test_help_page_title(client: FlaskClient) -> None:
    """Test that the help page has the correct title."""
    response = client.get('/help')
    assert b'Lexicographic Curation Workbench Help' in response.data


def test_help_page_has_lift_explanation(client: FlaskClient) -> None:
    """Test that the help page explains LIFT."""
    response = client.get('/help')
    assert b'LIFT (Lexicon Interchange FormaT)' in response.data
    assert b'What is LIFT?' in response.data


def test_help_page_has_feature_sections(client: FlaskClient) -> None:
    """Test that major feature sections are present."""
    response = client.get('/help')
    
    # Check for major sections (note: & is not auto-escaped in headers)
    assert b'Multilingual Support' in response.data
    assert b'Senses' in response.data and b'Subsenses' in response.data
    assert b'Examples' in response.data and b'Usage' in response.data
    assert b'Pronunciation' in response.data
    assert b'Etymology' in response.data
    assert b'Custom Fields' in response.data
    assert b'FieldWorks Compatibility' in response.data


def test_help_page_has_navigation(client: FlaskClient) -> None:
    """Test that the help page has sidebar navigation."""
    response = client.get('/help')
    assert b'id="help-nav"' in response.data
    assert b'href="#introduction"' in response.data
    assert b'href="#lift-overview"' in response.data


def test_help_page_has_examples(client: FlaskClient) -> None:
    """Test that the help page includes practical examples."""
    response = client.get('/help')
    assert b'example-box' in response.data
    assert b'Example:' in response.data


def test_help_page_has_fieldworks_info(client: FlaskClient) -> None:
    """Test that FieldWorks compatibility is explained."""
    response = client.get('/help')
    assert b'91% LIFT 0.13 compliance' in response.data
    assert b'FieldWorks' in response.data


def test_help_link_in_navbar(client: FlaskClient) -> None:
    """Test that help link appears in the navigation bar."""
    response = client.get('/')
    assert b'href="/help"' in response.data or b"url_for('main.help_page')" in response.data
