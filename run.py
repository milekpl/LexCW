"""
Main entry point for the Lexicographic Curation Workbench application.
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app


# Set Flask TESTING config if TESTING env var is set
app = create_app(os.getenv('FLASK_CONFIG') or 'default')
if os.getenv('TESTING') == 'true':
    app.config['TESTING'] = True
    app.config['DEBUG'] = False

if __name__ == '__main__':
    is_testing = os.getenv('TESTING') == 'true'
    app.run(host='0.0.0.0', port=5000, debug=not is_testing)
