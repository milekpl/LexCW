#!/usr/bin/env python3
"""
Script to validate Jinja template syntax.
Checks that all Jinja tags are properly balanced and syntactically correct.
"""
from __future__ import annotations

import sys
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, TemplateSyntaxError


def check_template(template_path: str) -> bool:
    """
    Check if a Jinja template has valid syntax.
    
    Args:
        template_path: Path to the template file relative to project root
        
    Returns:
        True if template is valid, False otherwise
    """
    project_root = Path(__file__).parent
    template_file = Path(template_path)
    
    # Get template directory and filename
    if template_file.is_absolute():
        template_dir = template_file.parent
        template_name = template_file.name
    else:
        template_full_path = project_root / template_file
        template_dir = template_full_path.parent
        template_name = template_full_path.name
    
    if not template_full_path.exists():
        print(f"Error: Template file not found: {template_full_path}")
        return False
    
    # Create Jinja environment
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    
    try:
        # Try to load and parse the template
        env.get_template(template_name)
        print(f"✓ Template syntax is valid: {template_path}")
        return True
    except TemplateSyntaxError as e:
        print(f"✗ Jinja syntax error in {template_path}:")
        print(f"  Line {e.lineno}: {e.message}")
        return False
    except Exception as e:
        print(f"✗ Error checking template {template_path}:")
        print(f"  {type(e).__name__}: {e}")
        return False


def main() -> int:
    """
    Main function to check template files.
    
    Returns:
        0 if all templates are valid, 1 otherwise
    """
    if len(sys.argv) < 2:
        print("Usage: python check_jinja.py <template_file>")
        print("Example: python check_jinja.py app/templates/entry_form.html")
        return 1
    
    template_path = sys.argv[1]
    
    if check_template(template_path):
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
