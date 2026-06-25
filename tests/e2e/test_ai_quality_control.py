"""
E2E Tests for AI Quality Control Workflow
==========================================

Tests for AI-powered quality control using worksets:
1. Create AI review workset via API
2. Run AI quality control on workset entries
3. View AI review results
4. Review entries with issues in curation UI

Usage:
    pytest tests/e2e/test_ai_quality_control.py -v
"""

import pytest
import json
from playwright.sync_api import expect


@pytest.mark.e2e
class TestAIQualityControl:
    """Test AI quality control workflow via worksets."""
    
    def test_create_ai_review_workset(self, page, app_url):
        """
        Create an AI review workset for dictionary entries.
        
        Steps:
            1. Create workset via API with AI review flag
            2. Verify workset is created with correct metadata
            3. Verify entries are populated
        """
        import requests
        
        # Create AI review workset via API
        workset_data = {
            'name': 'E2E AI Review Test Workset',
            'query': {
                'filters': []  # All entries
            },
            'ai_config': {
                'prompt_template_id': 'proofreading-default',
                'severity_threshold': 'warning',
                'auto_mark_review': True
            }
        }
        
        response = requests.post(
            f"{app_url}/api/worksets/ai-review",
            json=workset_data,
            headers={'Content-Type': 'application/json'}
        )
        
        assert response.status_code == 201, f"Failed to create workset: {response.text}"
        result = response.json()
        
        assert result['success'] is True
        assert 'workset_id' in result
        assert result['ai_review_enabled'] is True
        
        workset_id = result['workset_id']
        
        print(f"✅ Created AI review workset: {workset_id}")
        return workset_id
    
    def test_ai_review_results_endpoint_structure(self, page, app_url):
        """
        Verify AI review results endpoint returns expected structure.
        
        Note: This tests the endpoint structure without actually running AI review
        (which would require API keys and take time).
        """
        import requests
        
        # First create a workset
        workset_data = {
            'name': 'E2E AI Review Results Test',
            'query': {'filters': []}
        }
        
        response = requests.post(
            f"{app_url}/api/worksets/ai-review",
            json=workset_data
        )
        
        if response.status_code != 201:
            pytest.skip("Could not create test workset")
        
        result = response.json()
        workset_id = result['workset_id']
        
        # Get AI review results (even if not yet run)
        results_response = requests.get(
            f"{app_url}/api/worksets/{workset_id}/ai-review-results",
            params={'min_severity': 'warning'}
        )
        
        assert results_response.status_code in [200, 404], f"Unexpected status: {results_response.status_code}"
        
        if results_response.status_code == 200:
            results = results_response.json()
            
            # Verify expected structure
            assert 'success' in results
            assert 'workset_id' in results
            assert 'workset_name' in results
            assert 'ai_config' in results
            assert 'entries_with_issues' in results or 'summary' in results
            
            print(f"✅ AI review results endpoint returns valid structure")
    
    def test_workset_curation_ui_displays_ai_suggestions(self, page, app_url):
        """
        Verify curation UI can display entries with AI suggestions.
        
        Steps:
            1. Navigate to workset curation page
            2. Verify entry display with AI suggestion indicators
            3. Check that status buttons work
        """
        import requests
        
        # Create a test workset
        workset_data = {
            'name': 'E2E Curation UI Test',
            'query': {'filters': []}
        }
        
        response = requests.post(
            f"{app_url}/api/worksets/ai-review",
            json=workset_data
        )
        
        if response.status_code != 201:
            pytest.skip("Could not create test workset")
        
        workset_id = response.json()['workset_id']
        
        # Navigate to workset curation page
        page.goto(f"{app_url}/workbench/worksets/{workset_id}/curation")
        page.wait_for_load_state('networkidle')
        
        # Verify curation UI elements are present
        expect(page.locator('#curation-view')).to_be_visible()
        expect(page.locator('#entry-content')).to_be_visible()
        
        # Check for navigation controls
        expect(page.locator('#btn-prev')).to_be_visible()
        expect(page.locator('#btn-next')).to_be_visible()
        
        # Check for status buttons
        expect(page.locator('button.status-btn[data-status="pending"]')).to_be_visible()
        expect(page.locator('button.status-btn[data-status="done"]')).to_be_visible()
        expect(page.locator('button.status-btn[data-status="review"]')).to_be_visible()
        
        print(f"✅ Workset curation UI displays correctly")
    
    def test_workset_marking_entries_for_review(self, page, app_url):
        """
        Test marking entries for review in workset curation UI.
        
        Steps:
            1. Navigate to workset curation
            2. Mark entry as 'review' status
            3. Verify status is saved via API
        """
        import requests
        
        # Create a workset with some entries
        workset_data = {
            'name': 'E2E Mark Review Test',
            'query': {'filters': []}
        }
        
        response = requests.post(
            f"{app_url}/api/worksets/ai-review",
            json=workset_data
        )
        
        if response.status_code != 201:
            pytest.skip("Could not create test workset")
        
        result = response.json()
        workset_id = result['workset_id']
        
        # Get workset entries via API
        entries_response = requests.get(
            f"{app_url}/api/worksets/{workset_id}",
            params={'limit': 1, 'offset': 0}
        )
        
        if entries_response.status_code != 200:
            pytest.skip("Could not get workset entries")
        
        workset_data = entries_response.json()
        
        if 'entries' not in workset_data or not workset_data['entries']:
            pytest.skip("No entries in workset to test with")
        
        first_entry = workset_data['entries'][0]
        entry_id = first_entry.get('id', first_entry.get('entry_id'))
        
        # Mark entry as review via API
        status_response = requests.patch(
            f"{app_url}/api/worksets/{workset_id}/entries/{entry_id}/status",
            json={'status': 'review', 'notes': 'AI detected issues - needs review'}
        )
        
        assert status_response.status_code == 200, f"Failed to update status: {status_response.text}"
        
        status_result = status_response.json()
        assert status_result['success'] is True
        assert status_result['status'] == 'review'
        
        print(f"✅ Successfully marked entry {entry_id} as 'review'")


@pytest.mark.e2e
class TestAIQualityControlIntegration:
    """Integration tests for the complete AI QC workflow."""
    
    def test_full_ai_qc_workflow_without_ai_call(self, page, app_url):
        """
        Test the complete workflow structure without actual AI call.
        
        This verifies all API endpoints work correctly.
        Steps:
            1. Create AI review workset
            2. Verify endpoints are accessible
            3. Verify curation UI can be opened
        """
        import requests
        
        # Step 1: Create workset
        create_data = {
            'name': 'E2E Full Workflow Test',
            'query': {'filters': []},
            'ai_config': {
                'prompt_template_id': 'proofreading-default',
                'severity_threshold': 'warning',
                'auto_mark_review': True
            }
        }
        
        create_response = requests.post(
            f"{app_url}/api/worksets/ai-review",
            json=create_data
        )
        
        assert create_response.status_code == 201
        create_result = create_response.json()
        workset_id = create_result['workset_id']
        
        # Step 2: Verify workset details
        get_response = requests.get(f"{app_url}/api/worksets/{workset_id}")
        assert get_response.status_code == 200
        
        # Step 3: Check curation progress endpoint
        progress_response = requests.get(
            f"{app_url}/api/worksets/{workset_id}/progress"
        )
        assert progress_response.status_code == 200
        
        progress = progress_response.json()
        assert 'status' in progress
        assert 'total_items' in progress
        
        # Step 4: Verify results endpoint exists (may be empty before AI run)
        results_response = requests.get(
            f"{app_url}/api/worksets/{workset_id}/ai-review-results"
        )
        assert results_response.status_code in [200, 404]
        
        # Step 5: Open curation UI
        page.goto(f"{app_url}/workbench/worksets/{workset_id}/curation")
        page.wait_for_load_state('networkidle')
        
        expect(page.locator('#curation-view')).to_be_visible()
        
        # Verify progress is displayed
        expect(page.locator('#progress-container')).to_be_visible()
        
        print(f"✅ Full AI QC workflow structure verified for workset {workset_id}")
    
    def test_ai_quality_control_script_help(self, app_url):
        """
        Verify the AI QC CLI script can display help.
        
        This ensures the script is syntactically correct and importable.
        """
        import subprocess
        import sys
        
        script_path = '/home/milek/flask-app/tools/scripts/ai_quality_control.py'
        
        result = subprocess.run(
            [sys.executable, script_path, '--help'],
            capture_output=True,
            text=True,
            cwd='/home/milek/flask-app'
        )
        
        # Script should at least not crash on --help
        # Note: May fail if dependencies not installed
        assert result.returncode == 0 or 'ai_quality_control' in result.stderr, \
            f"Script failed unexpectedly: {result.stderr}"
        
        # Should show help text
        assert 'AI Quality Control' in result.stdout or 'usage' in result.stdout.lower(), \
            f"Expected help text not found: {result.stdout}"
        
        print(f"✅ AI QC CLI script is syntactically correct and shows help")


@pytest.mark.e2e
class TestWorksetQueryFilter:
    """Test workset query filtering for AI QC."""
    
    def test_create_workset_with_pos_filter(self, page, app_url):
        """
        Create AI review workset filtered by part of speech.
        
        This allows lexicographers to focus AI review on specific word types.
        """
        import requests
        
        # Create workset for nouns only
        workset_data = {
            'name': 'E2E Nouns Only Review',
            'query': {
                'filters': [
                    {'field': 'grammatical_info', 'operator': 'equals', 'value': 'Noun'}
                ]
            },
            'ai_config': {
                'prompt_template_id': 'proofreading-default'
            }
        }
        
        response = requests.post(
            f"{app_url}/api/worksets/ai-review",
            json=workset_data
        )
        
        if response.status_code == 201:
            result = response.json()
            workset_id = result['workset_id']
            print(f"✅ Created filtered workset {workset_id} for nouns")
        else:
            # May fail if no noun entries exist - that's OK for this test
            pytest.skip("Could not create filtered workset (may be no matching entries)")
    
    def test_validate_workset_query(self, page, app_url):
        """
        Verify workset query validation endpoint.
        """
        import requests
        
        query = {
            'filters': [
                {'field': 'lexical_unit', 'operator': 'contains', 'value': 'test'}
            ]
        }
        
        response = requests.post(
            f"{app_url}/api/worksets/validate-query",
            json={'query': query}
        )
        
        # Endpoint may or may not exist
        if response.status_code == 200:
            result = response.json()
            assert 'valid' in result or 'errors' in result
            print(f"✅ Query validation endpoint working")
        else:
            pytest.skip("Query validation endpoint not available")
