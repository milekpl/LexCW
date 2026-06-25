#!/usr/bin/env python3
"""
AI Quality Control Client for Lexicographic Curation Workbench
===============================================================

This script provides a command-line interface for running AI-powered
quality control on dictionary entries using worksets.

Features:
- Create worksets filtered by criteria (POS, date range, missing fields)
- Run AI proofreading on workset entries in batch
- Review AI-detected issues
- Export entries with issues for manual review

Prerequisites:
--------------
    pip install requests

    Set environment variables:
    - LCW_API_URL: Base URL of LCW instance (default: http://localhost:5000)
    - LCW_API_KEY: API key for authentication
    - OPENAI_API_KEY: OpenAI API key for AI review (or set in project settings)

Usage Examples:
--------------
    # Create an AI review workset for all entries
    python ai_quality_control.py create \
        --name "Full Dictionary Review" \
        --query '{}'

    # Create workset for nouns only
    python ai_quality_control.py create \
        --name "Review Nouns" \
        --query '{"filters": [{"field": "pos", "operator": "equals", "value": "noun"}]}'

    # Run AI quality control on a workset
    python ai_quality_control.py run --workset-id 123

    # Get AI review results with severity filtering
    python ai_quality_control.py results --workset-id 123 --min-severity error

    # Full workflow: create, run, and export results
    python ai_quality_control.py workflow \
        --name "Quick Quality Check" \
        --query '{"filters": []}' \
        --output report.json

Workflow:
---------
1. Create workset with query criteria
2. Run AI quality control (proofreads all entries)
3. Review results - entries with issues are marked
4. Open workset in LCW curation UI to fix issues

The AI will check for:
- Missing required fields (definitions, examples)
- Grammatical consistency
- Semantic clarity
- Cross-reference validity
- Formatting issues

"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests


class AIQualityControlClient:
    """Client for AI-powered quality control via LCW API."""
    
    def __init__(
        self, 
        api_url: Optional[str] = None, 
        api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None
    ):
        """
        Initialize AI quality control client.
        
        Args:
            api_url: LCW API base URL
            api_key: LCW API key for authentication
            openai_api_key: OpenAI API key for AI proofreading
        """
        self.api_url = api_url or os.getenv('LCW_API_URL', 'http://localhost:5000')
        self.api_key = api_key or os.getenv('LCW_API_KEY')
        self.openai_api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        self.session = requests.Session()
        
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        if self.api_key:
            self.session.headers['X-API-Key'] = self.api_key
    
    def _request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to API."""
        url = urljoin(self.api_url, f'/api/{endpoint}')
        
        try:
            if method == 'GET':
                response = self.session.get(url, params=params)
            elif method == 'POST':
                response = self.session.post(url, json=data)
            elif method == 'PATCH':
                response = self.session.patch(url, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"Error: API request failed - {e}", file=sys.stderr)
            if hasattr(e.response, 'text'):
                print(f"Response: {e.response.text}", file=sys.stderr)
            sys.exit(1)
    
    def create_ai_review_workset(
        self, 
        name: str, 
        query: Dict[str, Any],
        ai_config: Optional[Dict] = None
    ) -> int:
        """
        Create a workset for AI quality control.
        
        Args:
            name: Workset name
            query: Query criteria for selecting entries
            ai_config: AI review configuration
            
        Returns:
            Created workset ID
        """
        # Default AI config
        default_config = {
            'prompt_template_id': 'proofreading-default',
            'severity_threshold': 'warning',
            'auto_mark_review': True
        }
        
        if ai_config:
            default_config.update(ai_config)
        
        result = self._request(
            'POST',
            'worksets/ai-review',
            data={
                'name': name,
                'query': query,
                'ai_config': default_config
            }
        )
        
        if not result.get('success'):
            print(f"Error creating workset: {result.get('error')}", file=sys.stderr)
            sys.exit(1)
        
        workset_id = result['workset_id']
        total_entries = result['total_entries']
        
        print(f"✅ Created AI review workset '{name}' (ID: {workset_id})")
        print(f"   Total entries: {total_entries}")
        print(f"   AI config: {default_config}")
        
        return workset_id
    
    def run_ai_review(
        self, 
        workset_id: int,
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run AI quality control on a workset.
        
        Args:
            workset_id: Workset ID to review
            api_key: OpenAI API key (optional - uses project settings)
            
        Returns:
            Review summary
        """
        # Use provided API key or fall back to instance key
        ai_key = api_key or self.openai_api_key
        
        print(f"🔄 Running AI quality control on workset {workset_id}...")
        print(f"   This may take a few minutes depending on the number of entries.")
        print()
        
        data = {}
        if ai_key:
            data['api_key'] = ai_key
        
        start_time = time.time()
        result = self._request(
            'POST',
            f'worksets/{workset_id}/run-ai-review',
            data=data
        )
        elapsed = time.time() - start_time
        
        if not result.get('success'):
            print(f"Error: {result.get('error')}", file=sys.stderr)
            sys.exit(1)
        
        summary = result.get('summary', {})
        
        print(f"✅ AI review completed in {elapsed:.1f} seconds")
        print()
        print("Summary:")
        print(f"  Total entries: {summary.get('total_entries', 0)}")
        print(f"  Entries with issues: {summary.get('entries_with_issues', 0)}")
        print(f"  Severity breakdown:")
        
        severity = summary.get('severity_breakdown', {})
        for level in ['critical', 'error', 'warning', 'info']:
            count = severity.get(level, 0)
            if count > 0:
                icon = {'critical': '🔴', 'error': '⚠️', 'warning': '⚠️', 'info': 'ℹ️'}[level]
                print(f"    {icon} {level.capitalize()}: {count}")
        
        return result
    
    def get_review_results(
        self, 
        workset_id: int,
        min_severity: str = 'warning'
    ) -> Dict[str, Any]:
        """
        Get AI review results for a workset.
        
        Args:
            workset_id: Workset ID
            min_severity: Minimum severity to include (critical/error/warning/info)
            
        Returns:
            Review results with issues
        """
        result = self._request(
            'GET',
            f'worksets/{workset_id}/ai-review-results',
            params={'min_severity': min_severity}
        )
        
        if not result.get('success'):
            print(f"Error: {result.get('error')}", file=sys.stderr)
            sys.exit(1)
        
        return result
    
    def print_review_report(self, results: Dict[str, Any], detailed: bool = False):
        """Print a formatted review report."""
        workset_name = results.get('workset_name', 'Unknown')
        summary = results.get('summary', {})
        entries = results.get('entries_with_issues', [])
        
        print()
        print("=" * 70)
        print(f"AI QUALITY CONTROL REPORT: {workset_name}")
        print("=" * 70)
        print()
        
        print(f"Total entries reviewed: {summary.get('total_entries', 0)}")
        print(f"Entries with issues: {len(entries)}")
        print()
        
        if not entries:
            print("🎉 No issues found! Dictionary is in good shape.")
            return
        
        # Group by severity
        by_severity = {'critical': [], 'error': [], 'warning': [], 'info': []}
        for entry in entries:
            for issue in entry.get('issues', []):
                severity = issue.get('severity', 'warning').lower()
                if severity in by_severity:
                    by_severity[severity].append({
                        'entry_id': entry['entry_id'],
                        'issue': issue
                    })
        
        # Print issues by severity
        for level in ['critical', 'error', 'warning']:
            issues = by_severity.get(level, [])
            if issues:
                icon = {'critical': '🔴', 'error': '⚠️', 'warning': '⚠️'}[level]
                print(f"\n{icon} {level.upper()} ISSUES ({len(issues)}):")
                print("-" * 50)
                
                # Show first 10
                for i, item in enumerate(issues[:10], 1):
                    entry_id = item['entry_id']
                    issue = item['issue']
                    field = issue.get('field', 'unknown')
                    message = issue.get('message', 'No message')
                    suggestion = issue.get('suggestion', '')
                    
                    print(f"  {i}. Entry: {entry_id}")
                    print(f"     Field: {field}")
                    print(f"     Issue: {message}")
                    if suggestion:
                        print(f"     Suggestion: {suggestion}")
                    print()
                
                if len(issues) > 10:
                    print(f"  ... and {len(issues) - 10} more {level} issues")
        
        # Detailed view if requested
        if detailed:
            print("\n" + "=" * 70)
            print("DETAILED ENTRY LIST")
            print("=" * 70)
            
            for entry in entries[:20]:  # Limit to 20
                print(f"\nEntry: {entry['entry_id']}")
                print(f"  Status: {entry.get('workset_status', 'unknown')}")
                print(f"  AI Reviewed: {entry.get('ai_reviewed_at', 'N/A')}")
                print(f"  Issues: {entry.get('issue_count', 0)}")
                
                for issue in entry.get('issues', [])[:5]:  # Show first 5 issues
                    severity = issue.get('severity', 'warning')
                    message = issue.get('message', '')[:60]
                    print(f"    [{severity}] {message}...")


def cmd_create(client: AIQualityControlClient, args):
    """Handle 'create' command."""
    # Parse query JSON
    try:
        query = json.loads(args.query) if args.query else {'filters': []}
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in query - {e}", file=sys.stderr)
        sys.exit(1)
    
    # Parse AI config if provided
    ai_config = {}
    if args.prompt_template:
        ai_config['prompt_template_id'] = args.prompt_template
    if args.severity_threshold:
        ai_config['severity_threshold'] = args.severity_threshold
    if args.auto_mark is not None:
        ai_config['auto_mark_review'] = args.auto_mark
    
    # Create workset
    workset_id = client.create_ai_review_workset(
        name=args.name,
        query=query,
        ai_config=ai_config if ai_config else None
    )
    
    print()
    print(f"Next steps:")
    print(f"  1. Run AI review: python ai_quality_control.py run --workset-id {workset_id}")
    print(f"  2. Or open in LCW: {client.api_url}/workbench/worksets/{workset_id}")


def cmd_run(client: AIQualityControlClient, args):
    """Handle 'run' command."""
    result = client.run_ai_review(
        workset_id=args.workset_id,
        api_key=args.openai_key
    )
    
    print()
    print(f"To view results:")
    print(f"  python ai_quality_control.py results --workset-id {args.workset_id}")


def cmd_results(client: AIQualityControlClient, args):
    """Handle 'results' command."""
    results = client.get_review_results(
        workset_id=args.workset_id,
        min_severity=args.min_severity
    )
    
    client.print_review_report(results, detailed=args.detailed)
    
    # Save to file if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n✅ Full results saved to: {args.output}")


def cmd_workflow(client: AIQualityControlClient, args):
    """Handle 'workflow' command - complete create, run, and export."""
    # Parse query
    try:
        query = json.loads(args.query) if args.query else {'filters': []}
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in query - {e}", file=sys.stderr)
        sys.exit(1)
    
    # Step 1: Create workset
    print("📋 Step 1: Creating AI review workset...")
    workset_id = client.create_ai_review_workset(
        name=args.name,
        query=query
    )
    
    # Step 2: Run AI review
    print()
    print("🤖 Step 2: Running AI quality control...")
    client.run_ai_review(workset_id=workset_id, api_key=args.openai_key)
    
    # Step 3: Get and display results
    print()
    print("📊 Step 3: Generating report...")
    results = client.get_review_results(workset_id=workset_id, min_severity='warning')
    client.print_review_report(results, detailed=args.detailed)
    
    # Step 4: Save results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n✅ Full results saved to: {args.output}")
    
    # Summary
    print()
    print("=" * 70)
    print("WORKFLOW COMPLETE")
    print("=" * 70)
    print(f"Workset ID: {workset_id}")
    print(f"Workset URL: {client.api_url}/workbench/worksets/{workset_id}")
    print()
    print("Next steps:")
    print(f"  1. Open workset in LCW curation UI")
    print(f"  2. Review entries marked with issues")
    print(f"  3. Fix issues in entry editor")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='AI Quality Control for Lexicographic Curation Workbench',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables:
  LCW_API_URL         LCW API base URL (default: http://localhost:5000)
  LCW_API_KEY         API key for LCW authentication
  OPENAI_API_KEY      OpenAI API key for AI proofreading

Examples:
  # Create and review all entries
  python ai_quality_control.py workflow --name "Full Review" --query '{}'

  # Review only nouns
  python ai_quality_control.py create --name "Nouns" \\
      --query '{"filters": [{"field": "pos", "value": "noun"}]}'

  # Review entries with missing definitions
  python ai_quality_control.py create --name "Missing Definitions" \\
      --query '{"filters": [{"field": "has_definition", "operator": "equals", "value": false}]}'
        """
    )
    
    parser.add_argument(
        '--api-url',
        help='LCW API base URL'
    )
    parser.add_argument(
        '--api-key',
        help='LCW API key'
    )
    parser.add_argument(
        '--openai-key',
        help='OpenAI API key (or set OPENAI_API_KEY env var)'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # create command
    create_parser = subparsers.add_parser('create', help='Create AI review workset')
    create_parser.add_argument('--name', '-n', required=True, help='Workset name')
    create_parser.add_argument('--query', '-q', default='{"filters": []}', 
                               help='Query JSON for filtering entries')
    create_parser.add_argument('--prompt-template', default='proofreading-default',
                               help='AI prompt template to use')
    create_parser.add_argument('--severity-threshold', choices=['critical', 'error', 'warning', 'info'],
                               default='warning', help='Minimum severity to flag')
    create_parser.add_argument('--auto-mark', type=bool, default=True,
                               help='Auto-mark entries with issues for review')
    
    # run command
    run_parser = subparsers.add_parser('run', help='Run AI review on workset')
    run_parser.add_argument('--workset-id', '-w', type=int, required=True, help='Workset ID')
    
    # results command
    results_parser = subparsers.add_parser('results', help='Get AI review results')
    results_parser.add_argument('--workset-id', '-w', type=int, required=True, help='Workset ID')
    results_parser.add_argument('--min-severity', choices=['critical', 'error', 'warning', 'info'],
                                default='warning', help='Minimum severity to show')
    results_parser.add_argument('--detailed', '-d', action='store_true',
                                help='Show detailed entry list')
    results_parser.add_argument('--output', '-o', help='Save results to JSON file')
    
    # workflow command
    workflow_parser = subparsers.add_parser('workflow', help='Full workflow: create, run, and report')
    workflow_parser.add_argument('--name', '-n', required=True, help='Workset name')
    workflow_parser.add_argument('--query', '-q', default='{"filters": []}',
                                 help='Query JSON for filtering entries')
    workflow_parser.add_argument('--output', '-o', help='Save results to JSON file')
    workflow_parser.add_argument('--detailed', '-d', action='store_true',
                                 help='Show detailed report')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Initialize client
    client = AIQualityControlClient(
        api_url=args.api_url,
        api_key=args.api_key,
        openai_api_key=args.openai_key
    )
    
    # Dispatch
    if args.command == 'create':
        cmd_create(client, args)
    elif args.command == 'run':
        cmd_run(client, args)
    elif args.command == 'results':
        cmd_results(client, args)
    elif args.command == 'workflow':
        cmd_workflow(client, args)


if __name__ == '__main__':
    main()
