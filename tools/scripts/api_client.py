#!/usr/bin/env python3
"""
Lexicographic Curation Workbench - External API Client
=====================================================

This script provides a command-line interface for interacting with the 
Lexicographic Curation Workbench via its REST API. Useful for:

- Bulk importing entries from external sources
- Exporting dictionary data in various formats
- Automating dictionary workflows
- Integration with external tools (e.g., corpus analysis, Kindle generation)

Usage Examples:
--------------
    # List all entries
    python api_client.py entries list

    # Get a specific entry
    python api_client.py entries get <entry_id>

    # Create a new entry from JSON file
    python api_client.py entries create --file new_entry.json

    # Export to LIFT format
    python api_client.py export lift --output my_dictionary.lift

    # Search entries
    python api_client.py search --query "word" --grammatical "noun"

Configuration:
-------------
Set environment variables or create a .env file:
    LCW_API_URL=http://localhost:5000
    LCW_API_KEY=your_api_key_here
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from urllib.parse import urljoin


class LCWApiClient:
    """Client for interacting with the Lexicographic Curation Workbench API."""
    
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize API client.
        
        Args:
            base_url: Base URL of the LCW instance (defaults to env var LCW_API_URL)
            api_key: API key for authentication (defaults to env var LCW_API_KEY)
        """
        self.base_url = base_url or os.getenv('LCW_API_URL', 'http://localhost:5000')
        self.api_key = api_key or os.getenv('LCW_API_KEY')
        self.session = requests.Session()
        
        # Set default headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        # Add API key if provided
        if self.api_key:
            self.session.headers['X-API-Key'] = self.api_key
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make an HTTP request to the API."""
        url = urljoin(self.base_url, f'/api/{endpoint}')
        
        try:
            if method == 'GET':
                response = self.session.get(url, params=params)
            elif method == 'POST':
                response = self.session.post(url, json=data)
            elif method == 'PUT':
                response = self.session.put(url, json=data)
            elif method == 'DELETE':
                response = self.session.delete(url)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"Error: API request failed - {e}", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON response from {url}", file=sys.stderr)
            sys.exit(1)
    
    # === Entry Operations ===
    
    def list_entries(self, page: int = 1, per_page: int = 20) -> List[Dict]:
        """List all dictionary entries with pagination."""
        result = self._make_request('GET', 'entries', params={
            'page': page,
            'per_page': per_page
        })
        return result.get('entries', [])
    
    def get_entry(self, entry_id: str) -> Dict:
        """Get a single entry by ID."""
        result = self._make_request('GET', f'entries/{entry_id}')
        return result
    
    def create_entry(self, entry_data: Dict) -> Dict:
        """Create a new dictionary entry."""
        result = self._make_request('POST', 'entries', data=entry_data)
        return result
    
    def update_entry(self, entry_id: str, entry_data: Dict) -> Dict:
        """Update an existing entry."""
        result = self._make_request('PUT', f'entries/{entry_id}', data=entry_data)
        return result
    
    def delete_entry(self, entry_id: str) -> bool:
        """Delete an entry."""
        result = self._make_request('DELETE', f'entries/{entry_id}')
        return result.get('success', False)
    
    # === Search Operations ===
    
    def search(
        self, 
        query: Optional[str] = None,
        grammatical: Optional[str] = None,
        semantic_domain: Optional[str] = None
    ) -> List[Dict]:
        """Search dictionary entries."""
        params = {}
        if query:
            params['q'] = query
        if grammatical:
            params['grammatical'] = grammatical
        if semantic_domain:
            params['semantic_domain'] = semantic_domain
            
        result = self._make_request('GET', 'search', params=params)
        return result.get('results', [])
    
    # === Range Operations ===
    
    def get_ranges(self) -> Dict:
        """Get all LIFT ranges (grammatical info, semantic domains, etc.)."""
        result = self._make_request('GET', 'ranges')
        return result.get('data', {})
    
    def get_range(self, range_id: str) -> Dict:
        """Get a specific range by ID."""
        result = self._make_request('GET', f'ranges/{range_id}')
        return result.get('data', {})
    
    # === Export Operations ===
    
    def export_lift(self, output_file: str) -> str:
        """Export dictionary to LIFT format."""
        url = urljoin(self.base_url, '/api/export/lift')
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            
            with open(output_file, 'wb') as f:
                f.write(response.content)
            
            return output_file
            
        except requests.exceptions.RequestException as e:
            print(f"Error: Export failed - {e}", file=sys.stderr)
            sys.exit(1)
    
    # === Stats ===
    
    def get_stats(self) -> Dict:
        """Get dictionary statistics."""
        result = self._make_request('GET', 'stats')
        return result


def cmd_entries_list(client: LCWApiClient, args):
    """Handle 'entries list' command."""
    entries = client.list_entries(page=args.page, per_page=args.per_page)
    
    if args.json:
        print(json.dumps(entries, indent=2))
    else:
        print(f"{'ID':<30} {'Headword':<30} {'POS':<15}")
        print("-" * 75)
        for entry in entries:
            entry_id = entry.get('id', 'N/A')[:30]
            headword = entry.get('lexical_unit', {}).get('en', 'N/A')[:30]
            pos = entry.get('grammatical_info', 'N/A')[:15]
            print(f"{entry_id:<30} {headword:<30} {pos:<15}")


def cmd_entries_get(client: LCWApiClient, args):
    """Handle 'entries get' command."""
    entry = client.get_entry(args.entry_id)
    print(json.dumps(entry, indent=2))


def cmd_entries_create(client: LCWApiClient, args):
    """Handle 'entries create' command."""
    # Load entry data from file
    with open(args.file, 'r') as f:
        entry_data = json.load(f)
    
    result = client.create_entry(entry_data)
    
    if result.get('success'):
        print(f"Entry created successfully: {result.get('id')}")
    else:
        print(f"Error: {result.get('error', 'Unknown error')}", file=sys.stderr)
        sys.exit(1)


def cmd_entries_update(client: LCWApiClient, args):
    """Handle 'entries update' command."""
    # Load entry data from file
    with open(args.file, 'r') as f:
        entry_data = json.load(f)
    
    result = client.update_entry(args.entry_id, entry_data)
    
    if result.get('success'):
        print(f"Entry updated successfully: {args.entry_id}")
    else:
        print(f"Error: {result.get('error', 'Unknown error')}", file=sys.stderr)
        sys.exit(1)


def cmd_entries_delete(client: LCWApiClient, args):
    """Handle 'entries delete' command."""
    if not args.force:
        confirm = input(f"Delete entry {args.entry_id}? [y/N]: ")
        if confirm.lower() != 'y':
            print("Cancelled")
            return
    
    success = client.delete_entry(args.entry_id)
    
    if success:
        print(f"Entry deleted: {args.entry_id}")
    else:
        print("Error: Failed to delete entry", file=sys.stderr)
        sys.exit(1)


def cmd_search(client: LCWApiClient, args):
    """Handle 'search' command."""
    results = client.search(
        query=args.query,
        grammatical=args.grammatical,
        semantic_domain=args.semantic_domain
    )
    
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"Found {len(results)} results:")
        print()
        for entry in results:
            entry_id = entry.get('id', 'N/A')
            headword = entry.get('lexical_unit', {}).get('en', 'N/A')
            print(f"  {entry_id}: {headword}")


def cmd_export_lift(client: LCWApiClient, args):
    """Handle 'export lift' command."""
    output_path = client.export_lift(args.output)
    print(f"Dictionary exported to: {output_path}")


def cmd_ranges_list(client: LCWApiClient, args):
    """Handle 'ranges list' command."""
    ranges = client.get_ranges()
    
    if args.json:
        print(json.dumps(ranges, indent=2))
    else:
        print("Available ranges:")
        for range_id, range_data in ranges.items():
            label = range_data.get('label', range_id)
            values_count = len(range_data.get('values', []))
            print(f"  {range_id}: {label} ({values_count} values)")


def cmd_stats(client: LCWApiClient, args):
    """Handle 'stats' command."""
    stats = client.get_stats()
    
    if args.json:
        print(json.dumps(stats, indent=2))
    else:
        print(f"Dictionary Statistics:")
        print(f"  Total entries: {stats.get('total_entries', 'N/A')}")
        print(f"  Total senses: {stats.get('total_senses', 'N/A')}")
        print(f"  Total examples: {stats.get('total_examples', 'N/A')}")


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description='Lexicographic Curation Workbench API Client',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables:
  LCW_API_URL    Base URL of LCW instance (default: http://localhost:5000)
  LCW_API_KEY    API key for authentication

Examples:
  %(prog)s entries list
  %(prog)s entries get abc123
  %(prog)s search --query "test"
  %(prog)s export lift --output dict.lift
        """
    )
    
    parser.add_argument(
        '--api-url',
        help='Base URL of LCW instance (or set LCW_API_URL env var)'
    )
    parser.add_argument(
        '--api-key',
        help='API key for authentication (or set LCW_API_KEY env var)'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output raw JSON instead of formatted text'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # entries command
    entries_parser = subparsers.add_parser('entries', help='Entry operations')
    entries_subparsers = entries_parser.add_subparsers(dest='entries_action')
    
    # entries list
    list_parser = entries_subparsers.add_parser('list', help='List all entries')
    list_parser.add_argument('--page', type=int, default=1, help='Page number')
    list_parser.add_argument('--per-page', type=int, default=20, help='Items per page')
    
    # entries get
    get_parser = entries_subparsers.add_parser('get', help='Get a specific entry')
    get_parser.add_argument('entry_id', help='Entry ID')
    
    # entries create
    create_parser = entries_subparsers.add_parser('create', help='Create new entry')
    create_parser.add_argument('--file', '-f', required=True, help='JSON file with entry data')
    
    # entries update
    update_parser = entries_subparsers.add_parser('update', help='Update existing entry')
    update_parser.add_argument('entry_id', help='Entry ID')
    update_parser.add_argument('--file', '-f', required=True, help='JSON file with entry data')
    
    # entries delete
    delete_parser = entries_subparsers.add_parser('delete', help='Delete an entry')
    delete_parser.add_argument('entry_id', help='Entry ID')
    delete_parser.add_argument('--force', action='store_true', help='Skip confirmation')
    
    # search command
    search_parser = subparsers.add_parser('search', help='Search entries')
    search_parser.add_argument('--query', '-q', help='Search query text')
    search_parser.add_argument('--grammatical', '-g', help='Filter by grammatical info')
    search_parser.add_argument('--semantic-domain', '-s', help='Filter by semantic domain')
    
    # export command
    export_parser = subparsers.add_parser('export', help='Export dictionary')
    export_subparsers = export_parser.add_subparsers(dest='export_format')
    
    # export lift
    export_lift_parser = export_subparsers.add_parser('lift', help='Export to LIFT format')
    export_lift_parser.add_argument('--output', '-o', required=True, help='Output file path')
    
    # ranges command
    ranges_parser = subparsers.add_parser('ranges', help='Range operations')
    ranges_subparsers = ranges_parser.add_subparsers(dest='ranges_action')
    
    # ranges list
    ranges_list_parser = ranges_subparsers.add_parser('list', help='List all ranges')
    
    # stats command
    stats_parser = subparsers.add_parser('stats', help='Get dictionary statistics')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Initialize client
    client = LCWApiClient(
        base_url=args.api_url,
        api_key=args.api_key
    )
    
    # Dispatch to appropriate handler
    if args.command == 'entries':
        if args.entries_action == 'list':
            cmd_entries_list(client, args)
        elif args.entries_action == 'get':
            cmd_entries_get(client, args)
        elif args.entries_action == 'create':
            cmd_entries_create(client, args)
        elif args.entries_action == 'update':
            cmd_entries_update(client, args)
        elif args.entries_action == 'delete':
            cmd_entries_delete(client, args)
        else:
            entries_parser.print_help()
    
    elif args.command == 'search':
        cmd_search(client, args)
    
    elif args.command == 'export':
        if args.export_format == 'lift':
            cmd_export_lift(client, args)
        else:
            export_parser.print_help()
    
    elif args.command == 'ranges':
        if args.ranges_action == 'list':
            cmd_ranges_list(client, args)
        else:
            ranges_parser.print_help()
    
    elif args.command == 'stats':
        cmd_stats(client, args)


if __name__ == '__main__':
    main()
