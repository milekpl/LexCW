import json
import os

def generate_markdown_docs(json_file_path, output_markdown_file):
    """
    Generates a Markdown document from the endpoint definitions JSON file.
    """
    try:
        with open(json_file_path, 'r') as f:
            endpoints = json.load(f)
    except FileNotFoundError:
        print(f"Error: JSON file not found at {json_file_path}")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {json_file_path}")
        return

    # Group endpoints by source file for better organization
    endpoints_by_file = {}
    for endpoint in endpoints:
        source_file = endpoint.get('source_file', 'Unknown Source File')
        # Normalize paths for consistent grouping (e.g. handle potential absolute paths from inspect)
        if os.path.isabs(source_file) and 'site-packages' not in source_file:
             # Attempt to make it relative if it's within a recognizable project structure
            try:
                # Assuming the script runs from repo root or one level down (like a 'scripts' folder)
                # This might need adjustment if script execution context is different
                possible_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
                if not os.path.exists(os.path.join(possible_repo_root, "app")): # if 'app' isn't in parent, assume current dir is root
                    possible_repo_root = os.path.abspath(os.path.dirname(__file__))

                rel_path = os.path.relpath(source_file, possible_repo_root)
                if not rel_path.startswith('..'): # Check if it's truly relative to our assumed root
                    source_file = rel_path
            except ValueError:
                pass # Keep absolute path if relpath fails (e.g. different drives)


        if source_file not in endpoints_by_file:
            endpoints_by_file[source_file] = []
        endpoints_by_file[source_file].append(endpoint)

    with open(output_markdown_file, 'w') as md_file:
        md_file.write("# API Endpoint Definitions\n\n")
        md_file.write("This document lists all the API endpoints, their HTTP methods, and where they are defined in the codebase.\n\n")

        # Sort files for consistent output, putting app files first
        sorted_files = sorted(
            endpoints_by_file.keys(),
            key=lambda x: (not x.startswith('app/'), x) # Prioritize 'app/' files, then sort alphabetically
        )


        for source_file in sorted_files:
            md_file.write(f"## File: `{source_file}`\n\n")

            # Sort endpoints within a file by URL for consistency
            sorted_endpoints = sorted(endpoints_by_file[source_file], key=lambda x: x['url'])

            for endpoint in sorted_endpoints:
                md_file.write(f"### `{endpoint['url']}`\n\n")
                md_file.write(f"- **Endpoint Name:** `{endpoint['endpoint']}`\n")
                md_file.write(f"- **HTTP Methods:** `{', '.join(endpoint['methods'])}`\n")
                md_file.write(f"- **Handler Function:** `{endpoint['function_name']}`\n")
                if endpoint['start_line'] != -1:
                    md_file.write(f"- **Defined at:** `{source_file}:{endpoint['start_line']}-{endpoint['end_line']}`\n")
                else:
                    md_file.write(f"- **Defined at:** Error inspecting source location ({endpoint['source_file']})\n")
                md_file.write("\n---\n\n")

    print(f"Markdown documentation generated at {output_markdown_file}")

if __name__ == '__main__':
    json_path = 'endpoint_definitions.json'
    # Check if running in agent environment and adjust path
    if os.getenv('AGENT_SANDBOX'): # A hypothetical env var for agent's execution context
        json_path = os.path.join(os.getenv('AGENT_SANDBOX'), json_path)

    output_md_path = 'API_DOCUMENTATION.md'
    if os.getenv('AGENT_SANDBOX'):
        output_md_path = os.path.join(os.getenv('AGENT_SANDBOX'), output_md_path)

    generate_markdown_docs(json_path, output_md_path)
