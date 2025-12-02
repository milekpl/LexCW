"""Test script to check registered routes"""
from app import create_app

app = create_app()

print("=" * 80)
print("Registered Routes:")
print("=" * 80)

for rule in app.url_map.iter_rules():
    if 'xml' in rule.rule or 'entries' in rule.rule:
        print(f"{rule.methods} {rule.rule} -> {rule.endpoint}")

print("=" * 80)
