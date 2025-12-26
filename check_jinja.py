#!/usr/bin/env python3
"""
Script to validate Jinja template rendering within a Flask app context.
"""
from __future__ import annotations

import sys
from app import create_app

def check_template_render() -> bool:
    """
    Check if the entry_form.html template renders correctly by making a request
    to the /entries/add endpoint in a test Flask application.
    """
    print("Creating Flask app for testing...")
    app = create_app('testing')
    
    # Create a dummy project to satisfy the load_project_context requirement
    from app.config_manager import ConfigManager
    with app.app_context():
        config_manager = app.injector.get(ConfigManager)
        # Check if any project exists, if not create one
        settings = config_manager.get_all_settings()
        if not settings:
            print("Creating dummy project for testing...")
            project = config_manager.create_settings(
                project_name="Test Project", 
                basex_db_name="test_db"
            )
            project_id = project.id
        else:
            project_id = settings[0].id
    
    with app.test_client() as client:
        # Set the project_id in the session
        with client.session_transaction() as sess:
            sess['project_id'] = project_id
            
        print("Making request to /entries/add to render the template...")
        try:
            # The /entries/add route renders the entry_form.html template
            response = client.get('/entries/add')
            
            if response.status_code == 200:
                print("✓ Template rendered successfully (HTTP 200 OK)")
                return True
            else:
                print(f"✗ Template rendering failed with status code: {response.status_code}")
                # Print response data to see error message from Flask/Jinja
                print("Response Data:")
                print(response.data.decode('utf-8'))
                return False
        except Exception as e:
            print(f"✗ An exception occurred during template rendering:")
            import traceback
            print(f"  {type(e).__name__}: {e}")
            traceback.print_exc()
            return False

def main() -> int:
    """
    Main function.
    """
    if check_template_render():
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main())
