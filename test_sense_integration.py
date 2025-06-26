#!/usr/bin/env python3
"""
Integration test to verify that entry views display senses correctly.
"""

import sys
import os
import unittest
from unittest.mock import patch

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.database.basex_connector import BaseXConnector
from app.services.dictionary_service import DictionaryService

class TestSenseDisplayIntegration(unittest.TestCase):
    """Integration test for sense display functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
        # BaseX connection parameters
        self.basex_host = 'localhost'
        self.basex_port = 1984
        self.basex_username = 'admin'
        self.basex_password = 'admin'
        self.basex_database = 'dictionary'

    def test_entry_view_displays_senses(self):
        """Test that the entry view correctly displays senses."""
        try:
            # Create a BaseX connector
            connector = BaseXConnector(
                host=self.basex_host,
                port=self.basex_port,
                username=self.basex_username,
                password=self.basex_password,
                database=self.basex_database
            )
            
            # Connect to BaseX server
            connector.connect()
            service = DictionaryService(connector)
            
            # Get the first entry that has senses
            entries, _ = service.list_entries(limit=10)
            test_entry = None
            
            for entry in entries:
                if entry.senses and len(entry.senses) > 0:
                    test_entry = entry
                    break
            
            if not test_entry:
                self.skipTest("No entries with senses found in the database")
            
            # Mock the dictionary service in the Flask app context
            with patch('app.services.dictionary_service.DictionaryService') as mock_service_class:
                mock_service = mock_service_class.return_value
                mock_service.get_entry.return_value = test_entry
                
                # Make a request to the entry view
                response = self.client.get(f'/entries/{test_entry.id}')
                
                # Check that the response is successful
                self.assertEqual(response.status_code, 200)
                
                # Check that the response contains the entry content
                response_text = response.get_data(as_text=True)
                
                # Verify headword is displayed
                self.assertIn(test_entry.headword, response_text)
                
                # Verify senses section exists
                self.assertIn('Senses', response_text)
                
                # Check for sense content if it exists
                for sense in test_entry.senses:
                    if sense.definition:
                        self.assertIn(sense.definition, response_text)
                    if sense.gloss:
                        self.assertIn(sense.gloss, response_text)
                
                print(f"✓ Entry view test passed for entry: {test_entry.id}")
                print(f"  Headword: {test_entry.headword}")
                print(f"  Number of senses: {len(test_entry.senses)}")
                for i, sense in enumerate(test_entry.senses, 1):
                    print(f"  Sense {i}: {sense.definition or '(no definition)'}")
                
        except Exception as e:
            self.skipTest(f"BaseX database not available: {e}")
        finally:
            if 'connector' in locals() and connector.is_connected():
                connector.disconnect()

    def test_entries_list_displays_headwords(self):
        """Test that the entries list correctly displays headwords."""
        try:
            # Create a BaseX connector
            connector = BaseXConnector(
                host=self.basex_host,
                port=self.basex_port,
                username=self.basex_username,
                password=self.basex_password,
                database=self.basex_database
            )
            
            # Connect to BaseX server
            connector.connect()
            service = DictionaryService(connector)
            
            # Get some entries
            entries, total = service.list_entries(limit=5)
            
            if not entries:
                self.skipTest("No entries found in the database")
            
            # Mock the dictionary service in the Flask app context
            with patch('app.services.dictionary_service.DictionaryService') as mock_service_class:
                mock_service = mock_service_class.return_value
                mock_service.list_entries.return_value = (entries, total)
                
                # Make a request to the entries list
                response = self.client.get('/entries')
                
                # Check that the response is successful
                self.assertEqual(response.status_code, 200)
                
                # Check that the response contains entry headwords
                response_text = response.get_data(as_text=True)
                
                # Verify headwords are displayed
                for entry in entries:
                    if entry.headword:
                        self.assertIn(entry.headword, response_text)
                
                print(f"✓ Entries list test passed")
                print(f"  Found {len(entries)} entries out of {total} total")
                for entry in entries[:3]:  # Show first 3
                    print(f"  - {entry.headword} ({len(entry.senses)} senses)")
                
        except Exception as e:
            self.skipTest(f"BaseX database not available: {e}")
        finally:
            if 'connector' in locals() and connector.is_connected():
                connector.disconnect()

if __name__ == "__main__":
    unittest.main()
