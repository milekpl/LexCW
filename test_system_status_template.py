#!/usr/bin/env python
"""
Test script to check system status rendering in the template.
"""

import sys
import os
import logging
from flask import Flask, render_template
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Create a test Flask app
app = Flask(__name__, template_folder='app/templates')
app.logger.setLevel(logging.INFO)

@app.route('/test')
def test_system_status():
    """Test endpoint to render system status with different values."""
    # Test with actual values (should display correctly)
    system_status = {
        'db_connected': True,
        'last_backup': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'storage_percent': 42
    }
    
    # Setup other required template variables
    stats = {
        'entries': 315,
        'senses': 500,
        'examples': 200
    }
    
    recent_activity = [
        {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'action': 'Test Entry Created',
            'description': 'Added test entry'
        }
    ]
    
    app.logger.info(f"Rendering template with system_status: {system_status}")
    
    return render_template('index.html', 
                           stats=stats, 
                           system_status=system_status, 
                           recent_activity=recent_activity)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
