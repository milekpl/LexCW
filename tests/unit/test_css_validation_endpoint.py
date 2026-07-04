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
        # Regression: the old per-line validator emitted a spurious "extra
        # semicolon" warning on every normal declaration. Valid CSS must be clean.
        assert data['warnings'] == []

    def test_validate_unclosed_brace_returns_invalid(self, client):
        """CSS with an unclosed brace followed by more rules should error.

        Note: cssutils (like a browser) tolerates a *trailing* unclosed brace at
        end-of-input and auto-closes it. It flags the mistake when the missing
        ``}`` causes the following rule to be misparsed, which is the common case.
        """
        invalid_css = """
        .sense {
            margin-left: 10px;
        }
        .lexical-unit {
            font-weight: bold;
        /* missing closing brace here */
        .example {
            font-style: italic;
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
        # cssutils reports a structural parse error for the dangling block.
        for error in data['errors']:
            assert error['line'] >= 1

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
        # An unterminated string produces an INVALID token / syntax error.
        assert data['valid'] is False
        assert len(data['errors']) > 0

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
        # An unterminated string produces an INVALID token / syntax error.
        assert data['valid'] is False
        assert len(data['errors']) > 0

    def test_validate_empty_declaration_returns_invalid(self, client):
        """An empty value (':;' with a stray token) is a real syntax error."""
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
        # cssutils treats the empty declaration + stray token as errors.
        assert data['valid'] is False
        assert len(data['errors']) > 0

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

    def test_validate_modern_css_returns_valid(self, client):
        """Modern CSS (flexbox, custom properties) must not be rejected.

        cssutils only knows CSS 2.1, so validation is run with ``validate=False``
        to check syntax only - property-level checks would wrongly flag these.
        """
        modern_css = """
        .entry {
            display: flex;
            gap: 1rem;
            color: var(--accent, #333);
        }
        """
        response = client.post(
            '/api/profiles/validate-css',
            json={'custom_css': modern_css},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['valid'] is True
        assert data['errors'] == []


class TestValidateCssString:
    """Direct unit tests for the ``validate_css_string`` helper (no HTTP)."""

    def test_valid_css_has_no_findings(self):
        from app.api.display_profiles import validate_css_string
        errors, warnings = validate_css_string(".a { color: red; }")
        assert errors == []
        assert warnings == []

    def test_unclosed_brace_is_error_with_line(self):
        from app.api.display_profiles import validate_css_string
        errors, _ = validate_css_string(".a {\n  color: red;\n.b {\n  color: blue;\n")
        assert len(errors) > 0
        assert all(e['line'] >= 1 for e in errors)

    def test_apostrophe_inside_double_quotes_is_valid(self):
        """Regression: the old per-line counter mis-flagged content: "it's"
        as an unclosed single quote."""
        from app.api.display_profiles import validate_css_string
        errors, _ = validate_css_string(".a::before { content: \"it's\"; }")
        assert errors == []
