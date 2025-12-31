"""Unit tests for CSS validation endpoint.

Tests the /api/profiles/validate-css endpoint for validating
custom CSS syntax before saving display profiles.
"""

from __future__ import annotations

import pytest
from flask import Flask


class TestCSSValidationEndpoint:
    """Test suite for CSS validation API endpoint."""

    def test_validate_empty_css_returns_valid(self, client):
        """Empty CSS should be considered valid."""
        response = client.post(
            '/api/profiles/validate-css',
            json={'custom_css': ''},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['valid'] is True
        assert data['errors'] == []
        assert data['warnings'] == []

    def test_validate_whitespace_css_returns_valid(self, client):
        """CSS with only whitespace should be valid."""
        response = client.post(
            '/api/profiles/validate-css',
            json={'custom_css': '   \n\n   \n  '},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['valid'] is True

    def test_validate_valid_css_returns_valid(self, client):
        """Valid CSS should return valid=true with no errors."""
        valid_css = """
        .sense {
            margin-left: 10px;
            color: #333;
        }
        .lexical-unit {
            font-weight: bold;
        }
        """
        response = client.post(
            '/api/profiles/validate-css',
            json={'custom_css': valid_css},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['valid'] is True
        assert len(data['errors']) == 0

    def test_validate_unclosed_brace_returns_invalid(self, client):
        """CSS with unclosed braces should return errors."""
        invalid_css = """
        .sense {
            margin-left: 10px;
        }
        .lexical-unit {
            font-weight: bold;
        /* missing closing brace */
        """
        response = client.post(
            '/api/profiles/validate-css',
            json={'custom_css': invalid_css},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['valid'] is False
        assert len(data['errors']) > 0
        # Should detect missing closing brace
        error_messages = [e['message'] for e in data['errors']]
        assert any('missing closing brace' in msg.lower() for msg in error_messages)

    def test_validate_extra_closing_brace_returns_invalid(self, client):
        """CSS with extra closing brace should return errors."""
        invalid_css = """
        .sense {
            margin-left: 10px;
        }}
        .lexical-unit {
            font-weight: bold;
        }
        """
        response = client.post(
            '/api/profiles/validate-css',
            json={'custom_css': invalid_css},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['valid'] is False
        assert len(data['errors']) > 0

    def test_validate_unclosed_single_quote_returns_error(self, client):
        """CSS with unclosed single quote should return error."""
        invalid_css = """
        .sense {
            font-family: 'Arial;
            color: blue;
        }
        """
        response = client.post(
            '/api/profiles/validate-css',
            json={'custom_css': invalid_css},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['valid'] is False
        error_messages = [e['message'] for e in data['errors']]
        assert any('single quote' in msg.lower() for msg in error_messages)

    def test_validate_unclosed_double_quote_returns_error(self, client):
        """CSS with unclosed double quote should return error."""
        invalid_css = """
        .sense {
            background: url("image.png);
            color: red;
        }
        """
        response = client.post(
            '/api/profiles/validate-css',
            json={'custom_css': invalid_css},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['valid'] is False
        error_messages = [e['message'] for e in data['errors']]
        assert any('double quote' in msg.lower() for msg in error_messages)

    def test_validate_suspicious_colon_semicolon_warns(self, client):
        """Suspicious ':;' pattern should generate a warning."""
        css_with_typo = """
        .sense {
            color:; red;
        }
        """
        response = client.post(
            '/api/profiles/validate-css',
            json={'custom_css': css_with_typo},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        # Should still be valid but with warnings
        warning_messages = [w['message'] for w in data['warnings']]
        assert any('typo' in msg.lower() or 'suspicious' in msg.lower() for msg in warning_messages)

    def test_validate_missing_request_body_returns_valid(self, client):
        """Missing request body should return valid (empty CSS)."""
        # Send JSON content-type with empty body
        response = client.post(
            '/api/profiles/validate-css',
            data='',
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['valid'] is True

    def test_validate_empty_json_returns_valid(self, client):
        """Empty JSON object should return valid (empty CSS)."""
        response = client.post(
            '/api/profiles/validate-css',
            json={},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['valid'] is True

    def test_validate_nested_selectors(self, client):
        """Nested selectors should be valid."""
        valid_css = """
        .entry .sense {
            margin-left: 15px;
        }
        .entry .sense .example {
            font-style: italic;
        }
        """
        response = client.post(
            '/api/profiles/validate-css',
            json={'custom_css': valid_css},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['valid'] is True

    def test_validate_pseudo_selectors(self, client):
        """Pseudo-classes and pseudo-elements should be valid."""
        valid_css = """
        .sense:first-child {
            margin-top: 0;
        }
        .lexical-unit::before {
            content: '\\2014';
        }
        a:hover {
            color: blue;
        }
        """
        response = client.post(
            '/api/profiles/validate-css',
            json={'custom_css': valid_css},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['valid'] is True

    def test_validate_media_query(self, client):
        """Media queries should be valid."""
        valid_css = """
        .sense {
            font-size: 14px;
        }
        @media (min-width: 768px) {
            .sense {
                font-size: 16px;
            }
        }
        """
        response = client.post(
            '/api/profiles/validate-css',
            json={'custom_css': valid_css},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['valid'] is True

    def test_validate_css_comments(self, client):
        """CSS comments should be handled correctly."""
        valid_css = """
        /* This is a comment */
        .sense {
            margin-left: 10px; /* inline comment */
        }
        /* Multi-line
           comment */
        .lexical-unit {
            font-weight: bold;
        }
        """
        response = client.post(
            '/api/profiles/validate-css',
            json={'custom_css': valid_css},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['valid'] is True

    def test_validate_error_includes_line_number(self, client):
        """Errors should include line number information."""
        invalid_css = """\
.sense {
    margin-left: 10px;
.lexical-unit {
    font-weight: bold;
}
"""
        response = client.post(
            '/api/profiles/validate-css',
            json={'custom_css': invalid_css},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['valid'] is False
        for error in data['errors']:
            assert 'line' in error
            assert error['line'] >= 1
