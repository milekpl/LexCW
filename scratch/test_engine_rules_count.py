import sys
sys.path.insert(0, '/home/milek/flask-app')
from app import create_app

app = create_app()

with app.app_context():
    from app.services.validation_engine import ValidationEngine
    # No project ID (default)
    e_default = ValidationEngine()
    print("Default rules count:", len(e_default.rules))
    
    # Project 1
    e_p1 = ValidationEngine(project_id="1")
    print("Project 1 rules count:", len(e_p1.rules))
    print("Project 1 rules:", list(e_p1.rules.keys()))
