"""Quick script to verify importing the app package doesn't raise TypeErrors."""

import importlib

try:
    import app
    print("imported app successfully")
except Exception as e:
    print("import failed:", type(e).__name__, e)
    raise
