#!/usr/bin/env python
"""
Test script to check system status template rendering using a minimal Flask app.
"""

import os
import sys
import logging
from datetime import datetime
from flask import Flask, render_template_string

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create a test Flask app
app = Flask(__name__)

# Simple template with just the system status widget
TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>System Status Test</title>
</head>
<body>
    <h1>System Status Test</h1>
    
    <div class="card">
        <div class="card-header">
            <h5>System Status</h5>
        </div>
        <div class="card-body">
            <ul class="list-group list-group-flush">
                <li class="list-group-item d-flex justify-content-between align-items-center">
                    Database Connection
                    <span class="badge bg-{{ 'success' if system_status.db_connected else 'danger' }} rounded-pill">
                        {{ 'Connected' if system_status.db_connected else 'Disconnected' }}
                    </span>
                </li>
                <li class="list-group-item d-flex justify-content-between align-items-center">
                    Last Backup
                    <span class="badge bg-secondary rounded-pill">{{ system_status.last_backup if system_status.last_backup else 'Never' }}</span>
                </li>
                <li class="list-group-item d-flex justify-content-between align-items-center">
                    Storage Usage
                    <span class="badge bg-{{ 'success' if system_status.storage_percent < 80 else 'warning' }} rounded-pill">
                        {{ system_status.storage_percent if system_status.storage_percent is not none else 0 }}%
                    </span>
                </li>
            </ul>
        </div>
    </div>
    
    <hr>
    
    <h2>Debug Information</h2>
    <pre>{{ system_status | tojson(indent=4) }}</pre>
</body>
</html>
"""

@app.route('/')
def test_system_status():
    """Test endpoint to render system status with actual values."""
    # Test with actual values (should display correctly)
    system_status = {
        'db_connected': True,
        'last_backup': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'storage_percent': 42
    }
    
    logger.info("Rendering template with system_status: %s", system_status)
    
    return render_template_string(TEMPLATE, system_status=system_status)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5002, debug=True)
