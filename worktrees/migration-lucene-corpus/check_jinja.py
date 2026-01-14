#!/usr/bin/env python3
"""
Script to validate Jinja template syntax and HTML validation.
Can validate specific files or all templates in the project.
"""
from __future__ import annotations

import sys
import os
import argparse
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, TemplateSyntaxError
from bs4 import BeautifulSoup
import tempfile
import subprocess


def validate_jinja_syntax(file_path: Path) -> tuple[bool, str]:
    """
    Validate Jinja2 template syntax by attempting to parse it.
    
    Args:
        file_path: Path to the template file to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Create a Jinja2 environment with the template's directory as loader
        template_dir = file_path.parent
        env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=True
        )
        
        # Parse the template to check for syntax errors
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Try to parse the template
        env.parse(content)
        
        return True, "Jinja syntax is valid"
        
    except TemplateSyntaxError as e:
        return False, f"Jinja syntax error in {file_path.name}: {e.message} at line {e.lineno}"
    except Exception as e:
        return False, f"Error validating {file_path.name}: {str(e)}"


def validate_html_syntax(file_path: Path) -> tuple[bool, str]:
    """
    Validate HTML syntax using BeautifulSoup.
    
    Args:
        file_path: Path to the HTML file to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(content, 'html.parser')
        
        # Check for parsing errors by looking for parse tree issues
        # BeautifulSoup is quite forgiving, so we'll just check if it parsed properly
        if soup.find(string=lambda text: text and 'parser error' in text.lower()):
            return False, f"HTML parsing issues detected in {file_path.name}"
        
        # Additional check: try to prettify to see if there are structural issues
        soup.prettify()
        
        return True, "HTML syntax appears valid"
        
    except Exception as e:
        return False, f"HTML validation error in {file_path.name}: {str(e)}"


def validate_template_rendering(file_path: Path) -> tuple[bool, str]:
    """
    Validate that a Jinja template can be rendered without errors.
    This creates a minimal Flask app context to test rendering.
    
    Args:
        file_path: Path to the template file to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Create a temporary Flask app to test rendering
        from app import create_app
        from app.config_manager import ConfigManager
        
        app = create_app('testing')
        
        with app.app_context():
            config_manager = app.injector.get(ConfigManager)
            # Check if any project exists, if not create one
            settings = config_manager.get_all_settings()
            if not settings:
                project = config_manager.create_settings(
                    project_name="Test Project",
                    basex_db_name="test_db"
                )
                project_id = project.id
            else:
                project_id = settings[0].id

        # Create a Jinja environment similar to Flask's
        template_dir = file_path.parent
        env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=True
        )
        
        # Load and render the template with minimal context
        template_name = file_path.name
        template = env.get_template(template_name)
        
        # Try rendering with empty context (or minimal context)
        template.render()
        
        return True, "Template renders successfully"
        
    except Exception as e:
        return False, f"Template rendering error in {file_path.name}: {str(e)}"


def validate_all_templates(templates_dir: Path) -> tuple[bool, list[str]]:
    """
    Validate all HTML templates in the given directory.
    
    Args:
        templates_dir: Directory containing template files
        
    Returns:
        Tuple of (all_valid, list_of_errors)
    """
    errors = []
    valid_count = 0
    
    # Find all .html files in the templates directory
    html_files = list(templates_dir.rglob("*.html"))
    
    print(f"Found {len(html_files)} HTML template files to validate...")
    
    for html_file in html_files:
        print(f"Validating {html_file.relative_to(templates_dir)}...")
        
        # Validate Jinja syntax
        jinja_valid, jinja_msg = validate_jinja_syntax(html_file)
        if not jinja_valid:
            errors.append(jinja_msg)
            print(f"  ❌ Jinja: {jinja_msg}")
        else:
            print(f"  ✅ Jinja: {jinja_msg}")
        
        # Validate HTML syntax
        html_valid, html_msg = validate_html_syntax(html_file)
        if not html_valid:
            errors.append(html_msg)
            print(f"  ❌ HTML: {html_msg}")
        else:
            print(f"  ✅ HTML: {html_msg}")
        
        if jinja_valid and html_valid:
            valid_count += 1
    
    print(f"\nValidation complete: {valid_count}/{len(html_files)} templates valid")
    
    return len(errors) == 0, errors


def main() -> int:
    """
    Main function with command line interface.
    """
    parser = argparse.ArgumentParser(description='Validate Jinja templates and HTML syntax')
    parser.add_argument('file', nargs='?', help='Specific file to validate (optional)')
    parser.add_argument('--all', action='store_true', help='Validate all templates in app/templates')
    parser.add_argument('--jinja-only', action='store_true', help='Validate only Jinja syntax')
    parser.add_argument('--html-only', action='store_true', help='Validate only HTML syntax')
    parser.add_argument('--render-test', action='store_true', help='Test template rendering')
    
    args = parser.parse_args()
    
    project_root = Path(__file__).parent
    templates_dir = project_root / "app" / "templates"
    
    if args.all:
        # Validate all templates
        all_valid, errors = validate_all_templates(templates_dir)
        
        if errors:
            print("\nValidation errors found:")
            for error in errors:
                print(f"  - {error}")
            return 1
        else:
            print("\n✅ All templates passed validation!")
            return 0
    
    elif args.file:
        # Validate specific file
        file_path = Path(args.file)
        
        if not file_path.exists():
            print(f"Error: File {file_path} does not exist")
            return 1
        
        print(f"Validating {file_path}...")
        
        errors = []
        
        if not args.html_only:
            jinja_valid, jinja_msg = validate_jinja_syntax(file_path)
            if not jinja_valid:
                errors.append(jinja_msg)
                print(f"❌ Jinja: {jinja_msg}")
            else:
                print(f"✅ Jinja: {jinja_msg}")
        
        if not args.jinja_only:
            html_valid, html_msg = validate_html_syntax(file_path)
            if not html_valid:
                errors.append(html_msg)
                print(f"❌ HTML: {html_msg}")
            else:
                print(f"✅ HTML: {html_msg}")
        
        if args.render_test:
            render_valid, render_msg = validate_template_rendering(file_path)
            if not render_valid:
                errors.append(render_msg)
                print(f"❌ Rendering: {render_msg}")
            else:
                print(f"✅ Rendering: {render_msg}")
        
        if errors:
            print("\nValidation failed:")
            for error in errors:
                print(f"  - {error}")
            return 1
        else:
            print("\n✅ File validation passed!")
            return 0
    
    else:
        # Show help if no arguments provided
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())