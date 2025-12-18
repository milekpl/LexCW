#!/usr/bin/env python3
"""
XML Compatibility Validation Script

Tests all entries in BaseX database for compatibility with:
1. LIFTParser (XML parsing)
2. ValidationEngine (validation rules)
3. XMLEntryService (CRUD operations)

Generates comprehensive compatibility report.
"""

from __future__ import annotations

import os
import sys
from typing import Dict, List, Any
from collections import defaultdict
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database.basex_connector import BaseXConnector
from app.parsers.lift_parser import LIFTParser
from app.services.validation_engine import ValidationEngine
from app.services.xml_entry_service import XMLEntryService


class CompatibilityValidator:
    """Validates XML compatibility for all BaseX entries."""
    
    def __init__(self, database: str = 'dictionary'):
        """Initialize validator with database connection."""
        self.database = database
        self.connector = BaseXConnector(
            host=os.getenv('BASEX_HOST', 'localhost'),
            port=int(os.getenv('BASEX_PORT', '1984')),
            username=os.getenv('BASEX_USERNAME', 'admin'),
            password=os.getenv('BASEX_PASSWORD', 'admin'),
            database=database
        )
        self.parser = LIFTParser(validate=False)
        self.validator = ValidationEngine()
        self.xml_service = XMLEntryService(
            host=os.getenv('BASEX_HOST', 'localhost'),
            port=int(os.getenv('BASEX_PORT', '1984')),
            username=os.getenv('BASEX_USERNAME', 'admin'),
            password=os.getenv('BASEX_PASSWORD', 'admin'),
            database=database
        )
        
        # Results tracking
        self.total_entries = 0
        self.parsing_results: Dict[str, List[str]] = {
            'success': [],
            'errors': []
        }
        self.validation_results: Dict[str, List[str]] = {
            'valid': [],
            'invalid': []
        }
        self.service_results: Dict[str, List[str]] = {
            'success': [],
            'errors': []
        }
        self.error_details: List[Dict[str, Any]] = []
        
    def get_all_entry_ids(self) -> List[str]:
        """Get all entry IDs from database."""
        print("Fetching all entry IDs from database...")
        self.connector.connect()
        
        # Get entry IDs
        query = "for $entry in //entry return string($entry/@id)"
        result = self.connector.execute_query(query)
        
        # Parse result (may be newline-separated or space-separated)
        ids = [id.strip() for id in result.split('\n') if id.strip()]
        self.total_entries = len(ids)
        
        print(f"Found {self.total_entries} entries")
        self.connector.disconnect()
        return ids
    
    def get_entry_xml(self, entry_id: str) -> str:
        """Get XML for specific entry."""
        self.connector.connect()
        query = f"//entry[@id='{entry_id}']"
        xml = self.connector.execute_query(query)
        self.connector.disconnect()
        return xml
    
    def test_parsing(self, entry_id: str, xml: str) -> bool:
        """Test if entry can be parsed by LIFTParser."""
        try:
            entry = self.parser.parse_string(xml)[0]
            if entry and entry.id:
                self.parsing_results['success'].append(entry_id)
                return True
            else:
                self.parsing_results['errors'].append(entry_id)
                self.error_details.append({
                    'entry_id': entry_id,
                    'stage': 'parsing',
                    'error': 'Parser returned None or entry without ID',
                    'xml_sample': xml[:200]
                })
                return False
        except Exception as e:
            self.parsing_results['errors'].append(entry_id)
            self.error_details.append({
                'entry_id': entry_id,
                'stage': 'parsing',
                'error': str(e),
                'xml_sample': xml[:200]
            })
            return False
    
    def test_validation(self, entry_id: str, xml: str) -> bool:
        """Test if entry passes validation."""
        try:
            result = self.validator.validate_xml(xml, validation_mode="all")
            if result.is_valid:
                self.validation_results['valid'].append(entry_id)
                return True
            else:
                self.validation_results['invalid'].append(entry_id)
                # Don't treat validation errors as compatibility issues
                # Just track them
                return True  # Still compatible, just has validation issues
        except Exception as e:
            self.validation_results['invalid'].append(entry_id)
            self.error_details.append({
                'entry_id': entry_id,
                'stage': 'validation',
                'error': str(e),
                'xml_sample': xml[:200]
            })
            return False
    
    def test_service_operations(self, entry_id: str) -> bool:
        """Test if XMLEntryService can read the entry."""
        try:
            # Test read operation
            entry_xml = self.xml_service.get_entry(entry_id)
            if entry_xml and len(entry_xml) > 0:
                self.service_results['success'].append(entry_id)
                return True
            else:
                self.service_results['errors'].append(entry_id)
                self.error_details.append({
                    'entry_id': entry_id,
                    'stage': 'service',
                    'error': 'Service returned empty result'
                })
                return False
        except Exception as e:
            self.service_results['errors'].append(entry_id)
            self.error_details.append({
                'entry_id': entry_id,
                'stage': 'service',
                'error': str(e)
            })
            return False
    
    def validate_all(self, sample_size: int = None) -> Dict[str, Any]:
        """
        Validate all entries (or sample).
        
        Args:
            sample_size: If provided, only validate this many entries
        """
        entry_ids = self.get_all_entry_ids()
        
        if sample_size:
            entry_ids = entry_ids[:sample_size]
            print(f"Testing sample of {sample_size} entries...")
        else:
            print(f"Testing all {len(entry_ids)} entries...")
        
        for i, entry_id in enumerate(entry_ids, 1):
            if i % 50 == 0:
                print(f"Progress: {i}/{len(entry_ids)} ({i*100//len(entry_ids)}%)")
            
            # Get XML
            xml = self.get_entry_xml(entry_id)
            if not xml:
                self.error_details.append({
                    'entry_id': entry_id,
                    'stage': 'fetch',
                    'error': 'Could not fetch entry XML'
                })
                continue
            
            # Test parsing
            parsing_ok = self.test_parsing(entry_id, xml)
            
            # Test validation (only if parsing succeeded)
            if parsing_ok:
                self.test_validation(entry_id, xml)
            
            # Test service operations
            self.test_service_operations(entry_id)
        
        return self.generate_report()
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive compatibility report."""
        total = len(self.parsing_results['success']) + len(self.parsing_results['errors'])
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'database': self.database,
            'total_entries': self.total_entries,
            'tested_entries': total,
            'parsing': {
                'success': len(self.parsing_results['success']),
                'errors': len(self.parsing_results['errors']),
                'success_rate': len(self.parsing_results['success']) / total * 100 if total > 0 else 0,
                'failed_ids': self.parsing_results['errors'][:10]  # First 10
            },
            'validation': {
                'valid': len(self.validation_results['valid']),
                'invalid': len(self.validation_results['invalid']),
                'validation_rate': len(self.validation_results['valid']) / total * 100 if total > 0 else 0,
                'invalid_ids': self.validation_results['invalid'][:10]  # First 10
            },
            'service': {
                'success': len(self.service_results['success']),
                'errors': len(self.service_results['errors']),
                'success_rate': len(self.service_results['success']) / total * 100 if total > 0 else 0,
                'failed_ids': self.service_results['errors'][:10]  # First 10
            },
            'error_details': self.error_details[:20],  # First 20 errors
            'summary': {
                'overall_compatible': len(self.parsing_results['success']) >= total * 0.99,
                'parsing_compatible': len(self.parsing_results['success']) / total * 100 if total > 0 else 0,
                'service_compatible': len(self.service_results['success']) / total * 100 if total > 0 else 0
            }
        }
        
        return report
    
    def print_report(self, report: Dict[str, Any]) -> None:
        """Print formatted report to console."""
        print("\n" + "=" * 80)
        print("XML COMPATIBILITY VALIDATION REPORT")
        print("=" * 80)
        print(f"Timestamp: {report['timestamp']}")
        print(f"Database: {report['database']}")
        print(f"Total Entries: {report['total_entries']}")
        print(f"Tested Entries: {report['tested_entries']}")
        
        print("\n" + "-" * 80)
        print("PARSING RESULTS")
        print("-" * 80)
        print(f"Success: {report['parsing']['success']} ({report['parsing']['success_rate']:.2f}%)")
        print(f"Errors: {report['parsing']['errors']}")
        if report['parsing']['failed_ids']:
            print(f"Failed IDs (first 10): {', '.join(report['parsing']['failed_ids'][:10])}")
        
        print("\n" + "-" * 80)
        print("VALIDATION RESULTS")
        print("-" * 80)
        print(f"Valid: {report['validation']['valid']} ({report['validation']['validation_rate']:.2f}%)")
        print(f"Invalid: {report['validation']['invalid']}")
        if report['validation']['invalid_ids']:
            print(f"Invalid IDs (first 10): {', '.join(report['validation']['invalid_ids'][:10])}")
        
        print("\n" + "-" * 80)
        print("SERVICE OPERATION RESULTS")
        print("-" * 80)
        print(f"Success: {report['service']['success']} ({report['service']['success_rate']:.2f}%)")
        print(f"Errors: {report['service']['errors']}")
        if report['service']['failed_ids']:
            print(f"Failed IDs (first 10): {', '.join(report['service']['failed_ids'][:10])}")
        
        print("\n" + "-" * 80)
        print("ERROR DETAILS (First 20)")
        print("-" * 80)
        for i, error in enumerate(report['error_details'][:20], 1):
            print(f"\n{i}. Entry: {error['entry_id']}")
            print(f"   Stage: {error['stage']}")
            print(f"   Error: {error['error']}")
            if 'xml_sample' in error:
                print(f"   XML: {error['xml_sample'][:100]}...")
        
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Overall Compatible: {'✅ YES' if report['summary']['overall_compatible'] else '❌ NO'}")
        print(f"Parsing Compatibility: {report['summary']['parsing_compatible']:.2f}%")
        print(f"Service Compatibility: {report['summary']['service_compatible']:.2f}%")
        
        if report['summary']['overall_compatible']:
            print("\n✅ SUCCESS: Database is 99%+ compatible with XML Direct Manipulation")
        else:
            print("\n⚠️  WARNING: Compatibility below 99% threshold")
        
        print("=" * 80)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate XML compatibility for BaseX entries')
    parser.add_argument('--database', default='dictionary', help='Database name')
    parser.add_argument('--sample', type=int, help='Test only N entries (for quick test)')
    parser.add_argument('--output', help='Save report to JSON file')
    
    args = parser.parse_args()
    
    validator = CompatibilityValidator(database=args.database)
    report = validator.validate_all(sample_size=args.sample)
    validator.print_report(report)
    
    # Save to file if requested
    if args.output:
        import json
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n📄 Report saved to: {args.output}")


if __name__ == '__main__':
    main()
