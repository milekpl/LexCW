"""
Unit test for Jinja template validation.
Ensures all Jinja templates have properly balanced tags.
"""
from __future__ import annotations

import unittest
import subprocess
import sys
from pathlib import Path


class TestJinjaTemplates(unittest.TestCase):
    """Test suite for validating Jinja template syntax."""
    
    def test_entry_form_jinja_syntax(self) -> None:
        """Test that entry_form.html has valid Jinja syntax."""
        project_root = Path(__file__).parent.parent.parent
        check_script = project_root / "check_jinja.py"
        template_file = "app/templates/entry_form.html"
        
        # Run the check_jinja.py script
        result = subprocess.run(
            [sys.executable, str(check_script), template_file],
            capture_output=True,
            text=True,
            cwd=str(project_root)
        )
        
        # Return code should be 0 for success
        if result.returncode != 0:
            # Only fail if there was an actual error
            error_output = result.stdout + result.stderr
            self.fail(f"Jinja template validation failed:\n{error_output}")
        
        # Success - template is valid
    
    def test_all_templates_jinja_syntax(self) -> None:
        """Test that all HTML templates have valid Jinja syntax."""
        project_root = Path(__file__).parent.parent.parent
        templates_dir = project_root / "app" / "templates"
        
        if not templates_dir.exists():
            self.skipTest("Templates directory not found")
        
        # Find all .html files
        html_files = list(templates_dir.glob("**/*.html"))
        
        if not html_files:
            self.skipTest("No HTML templates found")
        
        errors = []
        for html_file in html_files:
            # Run check_jinja.py for each template
            # Note: check_jinja.py needs to be updated to accept file path as argument
            # For now, we'll do a simple check for balanced tags
            try:
                content = html_file.read_text(encoding='utf-8')
                if not self._check_balanced_tags(content):
                    errors.append(f"{html_file.name}: Unbalanced Jinja tags detected")
            except Exception as e:
                errors.append(f"{html_file.name}: Error reading file - {e}")
        
        if errors:
            self.fail("Template validation errors:\\n" + "\\n".join(errors))
    
    def _check_balanced_tags(self, content: str) -> bool:
        """Simple check for balanced Jinja tags."""
        import re
        
        # Stack to track opening tags
        stack = []
        
        # Regex for Jinja tags
        tag_pattern = re.compile(r'{%\\s*(\\w+)(?:\\s+.*?)?\\s*%}')
        
        for match in tag_pattern.finditer(content):
            tag_name = match.group(1)
            
            if tag_name in ['if', 'for', 'block', 'macro', 'call', 'filter', 'with']:
                stack.append(tag_name)
            elif tag_name.startswith('end'):
                expected = tag_name[3:]
                if not stack or stack[-1] != expected:
                    return False
                stack.pop()
        
        # Stack should be empty if all tags are balanced
        return len(stack) == 0


if __name__ == '__main__':
    unittest.main()
