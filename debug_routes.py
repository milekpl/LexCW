#!/usr/bin/env python3

"""
Debug available routes
"""

from app import create_app

def debug_routes():
    """Debug available routes."""
    app = create_app('testing')
    
    print("Available routes:")
    for rule in app.url_map.iter_rules():
        print(f"  {rule.rule} -> {rule.endpoint} [{','.join(rule.methods)}]")
    
    print("\nCorpus related routes:")
    for rule in app.url_map.iter_rules():
        if 'corpus' in rule.rule:
            print(f"  {rule.rule} -> {rule.endpoint} [{','.join(rule.methods)}]")

if __name__ == '__main__':
    debug_routes()
