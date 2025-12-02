"""Check Flask routes"""
from app import create_app

app = create_app()

print("\nAll registered routes:")
print("=" * 80)
for rule in sorted(app.url_map.iter_rules(), key=lambda r: str(r)):
    methods = ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
    print(f"{rule.endpoint:50s} {methods:15s} {rule.rule}")

print("\n" + "=" * 80)
print("\nXML API routes:")
for rule in app.url_map.iter_rules():
    if 'xml' in rule.rule.lower():
        methods = ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
        print(f"{methods:15s} {rule.rule}")
