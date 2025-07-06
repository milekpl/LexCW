import inspect
import os
from flask import Flask
from app import create_app, injector

def get_endpoint_definitions():
    """
    Inspects the Flask app to get details about all registered endpoints,
    including their source file and line number.
    """
    os.environ['FLASK_CONFIG'] = 'testing'  # Use a consistent config for inspection

    # Ensure BaseX connection is skipped during inspection if TESTING is true
    # or if BaseX is not available in the sandbox.
    # This might require adjusting app initialization if it tries to connect.
    os.environ['TESTING'] = 'true'

    app = create_app()
    definitions = []

    with app.app_context():
        rules = list(app.url_map.iter_rules())

        for rule in rules:
            if rule.endpoint == 'static':  # Skip static files
                continue

            try:
                view_func = app.view_functions[rule.endpoint]

                # Get the original function if it's wrapped (e.g., by decorators)
                closure = inspect.getclosurevars(view_func)
                if closure.nonlocals:
                    for _, val in closure.nonlocals.items():
                        if callable(val) and hasattr(val, '__name__') and not inspect.isclass(val):
                            # Heuristic: check if this non-local looks like the original view func
                            # This might need refinement depending on decorator patterns
                            if val.__name__ == view_func.__name__ or \
                               (hasattr(view_func, '__wrapped__') and val.__name__ == view_func.__wrapped__.__name__):
                                view_func = val
                                break

                while hasattr(view_func, '__wrapped__'): # Handle multiple decorators
                    view_func = view_func.__wrapped__

                source_file = inspect.getsourcefile(view_func)
                lines, start_line = inspect.getsourcelines(view_func)

                # Make source_file relative to repo root if possible
                if source_file:
                    try:
                        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
                        # In the sandbox, __file__ might be just 'inspect_routes.py'
                        # If so, adjust repo_root assumption
                        if os.path.basename(os.path.dirname(__file__)) == '': # Running from root
                             repo_root = os.path.abspath(os.path.dirname(__file__))
                        else: # Running from a subdirectory (less likely in sandbox)
                             repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))


                        relative_file = os.path.relpath(source_file, repo_root)
                        # If it didn't make it relative (e.g. different drive on windows), keep original
                        if '..' not in relative_file:
                             source_file = relative_file
                    except ValueError: # Handles cases like different drives on Windows
                        pass


                definitions.append({
                    'endpoint': rule.endpoint,
                    'url': str(rule),
                    'methods': sorted(list(rule.methods - {'HEAD', 'OPTIONS'})),
                    'function_name': view_func.__name__,
                    'source_file': source_file,
                    'start_line': start_line,
                    'end_line': start_line + len(lines) -1
                })
            except Exception as e:
                definitions.append({
                    'endpoint': rule.endpoint,
                    'url': str(rule),
                    'methods': sorted(list(rule.methods - {'HEAD', 'OPTIONS'})),
                    'function_name': 'Error inspecting',
                    'source_file': str(e),
                    'start_line': -1,
                    'end_line': -1
                })

    return definitions

if __name__ == '__main__':
    endpoint_data = get_endpoint_definitions()
    for entry in endpoint_data:
        print(f"URL: {entry['url']}")
        print(f"  Endpoint: {entry['endpoint']}")
        print(f"  Methods: {entry['methods']}")
        print(f"  Function: {entry['function_name']}")
        print(f"  Source: {entry['source_file']}:{entry['start_line']}-{entry['end_line']}")
        print("-" * 30)

    # Save to a JSON file for the next step
    import json
    output_file_path = 'endpoint_definitions.json'
    # Check if running in agent environment and adjust path
    if os.getenv('AGENT_SANDBOX'): # A hypothetical env var for agent's execution context
        output_file_path = os.path.join(os.getenv('AGENT_SANDBOX'), output_file_path)

    with open(output_file_path, 'w') as f:
        json.dump(endpoint_data, f, indent=2)
    print(f"Endpoint definitions saved to {os.path.abspath(output_file_path)}")
