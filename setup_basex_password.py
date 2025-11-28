#!/usr/bin/env python3
"""Set BaseX admin password"""

import sys
sys.path.insert(0, '/mnt/d/Dokumenty/slownik-wielki/flask-app')

from BaseXClient import BaseXClient

# Try to connect with empty password (default for fresh BaseX)
try:
    session = BaseXClient.Session('localhost', 1984, 'admin', '')
    print("✓ Connected with empty password")
    
    # Set the password to 'admin'
    session.execute('ALTER PASSWORD admin admin')
    print("✓ Password set to 'admin'")
    
    session.close()
    print("✓ BaseX admin user configured")
except Exception as e:
    print(f"Failed with empty password: {e}")
    
    # Try with 'admin' password
    try:
        session = BaseXClient.Session('localhost', 1984, 'admin', 'admin')
        print("✓ Already configured with admin/admin")
        session.close()
    except Exception as e2:
        print(f"Failed with admin password: {e2}")
        print("\nTrying to reset password via command line...")
        import subprocess
        result = subprocess.run([
            'java', '-cp', '/mnt/d/Dokumenty/slownik-wielki/flask-app/BaseX120.jar',
            'org.basex.BaseX', '-c', 'ALTER PASSWORD admin admin'
        ], capture_output=True, text=True)
        print(result.stdout)
        print(result.stderr)
