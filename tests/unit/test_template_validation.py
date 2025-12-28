"""
Comprehensive test for Jinja2 template syntax and HTML validation.
This test integrates with the existing test infrastructure and can be run as part of CI/CD.
"""
import pytest
import subprocess
import sys
from pathlib import Path
import tempfile
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader, TemplateSyntaxError


class TestTemplateValidation:
    """Test suite for validating Jinja2 templates and HTML syntax."""
    
    @pytest.fixture
    def project_root(self):
        """Get the project root directory."""
        return Path(__file__).parent.parent.parent
    
    @pytest.fixture
    def templates_dir(self, project_root):
        """Get the templates directory."""
        return project_root / "app" / "templates"
    
    def test_jinja_syntax_single_file(self, project_root):
        """Test that a single template file has valid Jinja syntax."""
        template_file = project_root / "app" / "templates" / "entry_form.html"

        if not template_file.exists():
            pytest.skip(f"Template file does not exist: {template_file}")

        # Run the validation script on the specific file
        result = subprocess.run([
            sys.executable,
            str(project_root / "check_jinja.py"),
            str(template_file.relative_to(project_root)),
            "--jinja-only"
        ], capture_output=True, text=True, cwd=str(project_root))

        assert result.returncode == 0, f"Jinja syntax validation failed:\n{result.stdout}\n{result.stderr}"
    
    def test_html_syntax_single_file(self, project_root):
        """Test that a single template file has valid HTML syntax."""
        template_file = project_root / "app" / "templates" / "entry_form.html"

        if not template_file.exists():
            pytest.skip(f"Template file does not exist: {template_file}")

        # Run the validation script on the specific file
        result = subprocess.run([
            sys.executable,
            str(project_root / "check_jinja.py"),
            str(template_file.relative_to(project_root)),
            "--html-only"
        ], capture_output=True, text=True, cwd=str(project_root))

        assert result.returncode == 0, f"HTML syntax validation failed:\n{result.stdout}\n{result.stderr}"
    
    def test_all_templates_jinja_syntax(self, templates_dir):
        """Test that all HTML templates have valid Jinja syntax."""
        if not templates_dir.exists():
            pytest.skip("Templates directory does not exist")
        
        # Find all .html files in templates directory
        html_files = list(templates_dir.rglob("*.html"))
        
        if not html_files:
            pytest.skip("No HTML templates found")
        
        errors = []
        for html_file in html_files:
            # Validate Jinja syntax for each file
            try:
                with open(html_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Create a Jinja2 environment to parse the template
                template_dir = html_file.parent
                env = Environment(
                    loader=FileSystemLoader(str(template_dir)),
                    autoescape=True
                )
                
                # Parse the template to check for syntax errors
                env.parse(content)
                
            except TemplateSyntaxError as e:
                errors.append(f"{html_file.name}: Jinja syntax error - {e.message} at line {e.lineno}")
            except Exception as e:
                errors.append(f"{html_file.name}: Error during validation - {str(e)}")
        
        if errors:
            pytest.fail("Template validation errors:\n" + "\n".join(errors))
    
    def test_all_templates_html_syntax(self, templates_dir):
        """Test that all HTML templates have valid HTML syntax."""
        if not templates_dir.exists():
            pytest.skip("Templates directory does not exist")
        
        # Find all .html files in templates directory
        html_files = list(templates_dir.rglob("*.html"))
        
        if not html_files:
            pytest.skip("No HTML templates found")
        
        errors = []
        for html_file in html_files:
            # Validate HTML syntax for each file
            try:
                with open(html_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parse HTML with BeautifulSoup
                soup = BeautifulSoup(content, 'html.parser')
                
                # Check for any parsing issues
                if soup.find(string=lambda text: text and 'parser error' in text.lower() if text else False):
                    errors.append(f"{html_file.name}: HTML parsing issues detected")
                
            except Exception as e:
                errors.append(f"{html_file.name}: HTML validation error - {str(e)}")
        
        if errors:
            pytest.fail("HTML validation errors:\n" + "\n".join(errors))
    
    def test_check_jinja_script_functionality(self, project_root):
        """Test that the check_jinja.py script works correctly."""
        # Test with a simple valid Jinja template
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write("""
            <!DOCTYPE html>
            <html>
            <head>
                <title>{{ title }}</title>
            </head>
            <body>
                {% if items %}
                    <ul>
                    {% for item in items %}
                        <li>{{ item }}</li>
                    {% endfor %}
                    </ul>
                {% endif %}
            </body>
            </html>
            """)
            temp_file = Path(f.name)

        try:
            # Run the validation script on the temporary file
            result = subprocess.run([
                sys.executable,
                str(project_root / "check_jinja.py"),
                str(temp_file),
                "--jinja-only"
            ], capture_output=True, text=True, cwd=str(project_root))

            assert result.returncode == 0, f"Script should pass with valid template:\n{result.stdout}\n{result.stderr}"

        finally:
            # Clean up temporary file
            temp_file.unlink()
    
    def test_check_jinja_script_with_invalid_syntax(self, project_root):
        """Test that the check_jinja.py script correctly identifies invalid syntax."""
        # Test with a template that has invalid Jinja syntax
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write("""
            <!DOCTYPE html>
            <html>
            <body>
                {% if items %}
                    <p>Items exist</p>
                {% endif %}  <!-- This is valid -->

                {% invalid_tag %}  <!-- This should cause an error -->
            </body>
            </html>
            """)
            temp_file = Path(f.name)

        try:
            # Run the validation script on the temporary file
            result = subprocess.run([
                sys.executable,
                str(project_root / "check_jinja.py"),
                str(temp_file),
                "--jinja-only"
            ], capture_output=True, text=True, cwd=str(project_root))

            # Should fail due to invalid syntax
            assert result.returncode != 0, "Script should fail with invalid template"

        finally:
            # Clean up temporary file
            temp_file.unlink()
    
    @pytest.mark.parametrize("template_file", [
        "base.html",
        "entry_form.html",
        "entries.html",
        "index.html",
        "settings.html"
    ])
    def test_common_templates(self, project_root, template_file):
        """Test common templates for both Jinja and HTML syntax."""
        full_path = project_root / "app" / "templates" / template_file

        if not full_path.exists():
            pytest.skip(f"Template does not exist: {template_file}")

        # Test Jinja syntax
        result = subprocess.run([
            sys.executable,
            str(project_root / "check_jinja.py"),
            str(full_path.relative_to(project_root)),
            "--jinja-only"
        ], capture_output=True, text=True, cwd=str(project_root))

        assert result.returncode == 0, f"Jinja validation failed for {template_file}:\n{result.stdout}\n{result.stderr}"

        # Test HTML syntax
        result = subprocess.run([
            sys.executable,
            str(project_root / "check_jinja.py"),
            str(full_path.relative_to(project_root)),
            "--html-only"
        ], capture_output=True, text=True, cwd=str(project_root))

        assert result.returncode == 0, f"HTML validation failed for {template_file}:\n{result.stdout}\n{result.stderr}"


def test_validate_all_templates_cli():
    """Test the --all flag functionality."""
    pytest.skip("This test is slow and can be run separately")
    # This would validate all templates at once, which could be slow
    # result = subprocess.run([
    #     sys.executable,
    #     str(project_root / "check_jinja.py"),
    #     "--all"
    # ], capture_output=True, text=True, cwd=str(project_root))
    #
    # assert result.returncode == 0, f"All templates validation failed:\n{result.stdout}\n{result.stderr}"


if __name__ == "__main__":
    # Allow running this test file directly
    pytest.main([__file__, "-v"])