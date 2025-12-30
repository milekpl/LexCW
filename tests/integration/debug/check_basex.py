"""Simple script to check BaseX availability using BaseXConnector."""
import os, sys
# Ensure project root is in sys.path for ad-hoc scripts
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))
from app.database.basex_connector import BaseXConnector

host = os.getenv('BASEX_HOST', 'localhost')
port = int(os.getenv('BASEX_PORT', '1984'))
user = os.getenv('BASEX_USERNAME', 'admin')
pw = os.getenv('BASEX_PASSWORD', 'admin')

print(f"Attempting BaseX connect to {host}:{port} as {user} (DB env: {os.getenv('TEST_DB_NAME') or os.getenv('BASEX_DATABASE')})")
conn = BaseXConnector(host=host, port=port, username=user, password=pw, database=None)
import time
last_exc = None
for attempt in range(1, 6):
    try:
        print(f"Attempt {attempt} to connect...")
        conn.connect()
        print("Connected OK")
        try:
            l = conn.execute_command('LIST')
            print('LIST OK, sample:', str(l)[:200])
        except Exception as e:
            print('LIST failed:', e)
        conn.disconnect()
        sys.exit(0)
    except Exception as e:
        last_exc = e
        print(f"Connect attempt {attempt} failed: {repr(e)}")
        time.sleep(1)
print('Connection failed after retries:', repr(last_exc))
sys.exit(2)