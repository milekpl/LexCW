"""
Integration tests for variant relations bidirectional API endpoints.

Tests both "Has Variant" (outgoing) and "Is a Variant of" (incoming) directions
for variant relations between dictionary entries.

API endpoints:
- POST /api/entries/<entry_id>/variants - Create variant relation (with direction param)
- GET /api/entries/<entry_id>/variants - List all variants (outgoing and incoming)
- DELETE /api/entries/<entry_id>/variants/<target_id> - Delete variant relation
"""

from __future__ import annotations

import json
import pytest
from flask import Flask
from flask.testing import FlaskClient


@pytest.mark.integration
class TestVariantBidirectionalAPI:
    """Test bidirectional variant relations API endpoints."""

    @pytest.fixture
    def test_entries(self, client: FlaskClient):
        """Create test entries for variant relation tests."""
        # Create test entries with at least one sense (required by validation)
        entry1_data = {
            'id': 'test_entry_1',
            'lexical_unit': {'en': 'fast'},
            'senses': [{'id': 'sense1', 'definition': {'en': 'moving quickly'}}]
        }
        entry2_data = {
            'id': 'test_entry_2',
            'lexical_unit': {'en': 'faster'},
            'senses': [{'id': 'sense2', 'definition': {'en': 'more fast'}}]
        }
        entry3_data = {
            'id': 'test_entry_3',
            'lexical_unit': {'en': 'fastest'},
            'senses': [{'id': 'sense3', 'definition': {'en': 'most fast'}}]
        }

        # Clean up any existing entries first
        for entry_id in ['test_entry_1', 'test_entry_2', 'test_entry_3']:
            try:
                client.delete(f'/api/entries/{entry_id}')
            except Exception:
                pass

        # Create entries via the API
        response1 = client.post('/api/entries',
                                data=json.dumps(entry1_data),
                                content_type='application/json')
        response2 = client.post('/api/entries',
                                data=json.dumps(entry2_data),
                                content_type='application/json')
        response3 = client.post('/api/entries',
                                data=json.dumps(entry3_data),
                                content_type='application/json')

        # Verify entries were created
        assert response1.status_code == 201, f"Failed to create entry1: {response1.data}"
        assert response2.status_code == 201, f"Failed to create entry2: {response2.data}"
        assert response3.status_code == 201, f"Failed to create entry3: {response3.data}"

        yield {
            'entry1': 'test_entry_1',
            'entry2': 'test_entry_2',
            'entry3': 'test_entry_3'
        }

        # Cleanup after tests
        for entry_id in ['test_entry_1', 'test_entry_2', 'test_entry_3']:
            try:
                client.delete(f'/api/entries/{entry_id}')
            except Exception:
                pass

    @pytest.mark.integration
    def test_get_variants_empty_list(self, client: FlaskClient, test_entries):
        """Test GET variants returns empty list when no relations exist."""
        entry_id = test_entries['entry1']

        response = client.get(f'/api/entries/{entry_id}/variants')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'variants' in data
        assert data['variants'] == []

    @pytest.mark.integration
    def test_create_has_variant_relation(self, client: FlaskClient, test_entries):
        """Test POST to create 'Has Variant' relation (outgoing direction)."""
        entry_id = test_entries['entry1']
        target_id = test_entries['entry2']
        variant_type = "Spelling Variant"

        # Create "Has Variant" relation using direction='outgoing'
        relation_data = {
            'target_entry_id': target_id,
            'variant_type': variant_type,
            'direction': 'outgoing'
        }

        response = client.post(
            f'/api/entries/{entry_id}/variants',
            data=json.dumps(relation_data),
            content_type='application/json'
        )

        assert response.status_code == 201, f"Failed to create relation: {response.data}"

        data = json.loads(response.data)
        assert 'success' in data
        assert data['success'] is True
        assert 'relation' in data
        assert data['relation']['target_entry_id'] == target_id
        assert data['relation']['variant_type'] == variant_type

        # Verify the relation appears in the source entry's variants list with direction='outgoing'
        get_response = client.get(f'/api/entries/{entry_id}/variants')
        assert get_response.status_code == 200

        get_data = json.loads(get_response.data)
        variants = get_data.get('variants', [])
        outgoing_variants = [v for v in variants if v.get('direction') == 'outgoing']
        assert len(outgoing_variants) == 1
        assert outgoing_variants[0]['ref'] == target_id

    @pytest.mark.integration
    def test_create_is_variant_of_relation(self, client: FlaskClient, test_entries):
        """Test POST to create 'Is a Variant of' relation (incoming direction)."""
        entry_id = test_entries['entry2']
        source_id = test_entries['entry1']
        variant_type = "Spelling Variant"

        # Create "Is a Variant of" relation using direction='incoming'
        # The target_entry_id is the entry that entry_id is a variant of (source_id)
        relation_data = {
            'target_entry_id': source_id,
            'variant_type': variant_type,
            'direction': 'incoming'
        }

        response = client.post(
            f'/api/entries/{entry_id}/variants',
            data=json.dumps(relation_data),
            content_type='application/json'
        )

        assert response.status_code == 201, f"Failed to create relation: {response.data}"

        data = json.loads(response.data)
        assert 'success' in data
        assert data['success'] is True

        # Verify the relation appears in the target entry's variants list with direction='incoming'
        get_response = client.get(f'/api/entries/{entry_id}/variants')
        assert get_response.status_code == 200

        get_data = json.loads(get_response.data)
        variants = get_data.get('variants', [])
        incoming_variants = [v for v in variants if v.get('direction') == 'incoming']
        assert len(incoming_variants) == 1
        assert incoming_variants[0]['ref'] == source_id

        # Verify the reverse "outgoing" variant on source entry
        source_response = client.get(f'/api/entries/{source_id}/variants')
        source_data = json.loads(source_response.data)
        source_variants = source_data.get('variants', [])
        outgoing_from_source = [v for v in source_variants if v.get('direction') == 'outgoing']
        assert len(outgoing_from_source) == 1
        assert outgoing_from_source[0]['ref'] == entry_id

    @pytest.mark.integration
    def test_bidirectional_variants(self, client: FlaskClient, test_entries):
        """Test that creating a variant relation updates both directions."""
        entry1 = test_entries['entry1']
        entry2 = test_entries['entry2']

        # Create "Has Variant" from entry1 to entry2 using direction='outgoing'
        relation_data = {
            'target_entry_id': entry2,
            'variant_type': "Morphological Variant",
            'direction': 'outgoing'
        }

        response = client.post(
            f'/api/entries/{entry1}/variants',
            data=json.dumps(relation_data),
            content_type='application/json'
        )

        assert response.status_code == 201

        # Check entry1's outgoing variants
        entry1_response = client.get(f'/api/entries/{entry1}/variants')
        entry1_data = json.loads(entry1_response.data)
        entry1_variants = entry1_data.get('variants', [])
        outgoing_from_entry1 = [v for v in entry1_variants if v.get('direction') == 'outgoing']
        assert len(outgoing_from_entry1) == 1
        assert outgoing_from_entry1[0]['ref'] == entry2

        # Check entry2's incoming variants
        entry2_response = client.get(f'/api/entries/{entry2}/variants')
        entry2_data = json.loads(entry2_response.data)
        entry2_variants = entry2_data.get('variants', [])
        incoming_to_entry2 = [v for v in entry2_variants if v.get('direction') == 'incoming']
        assert len(incoming_to_entry2) == 1
        assert incoming_to_entry2[0]['ref'] == entry1

    @pytest.mark.integration
    def test_multiple_variants(self, client: FlaskClient, test_entries):
        """Test entry with multiple variant relations."""
        entry1 = test_entries['entry1']
        entry2 = test_entries['entry2']
        entry3 = test_entries['entry3']

        # Create first variant relation
        relation_data1 = {
            'target_entry_id': entry2,
            'variant_type': "Spelling Variant",
            'direction': 'outgoing'
        }
        response1 = client.post(
            f'/api/entries/{entry1}/variants',
            data=json.dumps(relation_data1),
            content_type='application/json'
        )
        assert response1.status_code == 201

        # Create second variant relation
        relation_data2 = {
            'target_entry_id': entry3,
            'variant_type': "Inflected Form",
            'direction': 'outgoing'
        }
        response2 = client.post(
            f'/api/entries/{entry1}/variants',
            data=json.dumps(relation_data2),
            content_type='application/json'
        )
        assert response2.status_code == 201

        # Verify both variants are listed
        get_response = client.get(f'/api/entries/{entry1}/variants')
        get_data = json.loads(get_response.data)
        variants = get_data.get('variants', [])
        outgoing_variants = [v for v in variants if v.get('direction') == 'outgoing']
        assert len(outgoing_variants) == 2
        variant_targets = [v['ref'] for v in outgoing_variants]
        assert entry2 in variant_targets
        assert entry3 in variant_targets

    @pytest.mark.integration
    def test_delete_variant_relation(self, client: FlaskClient, test_entries):
        """Test DELETE variant relation."""
        entry1 = test_entries['entry1']
        entry2 = test_entries['entry2']

        # First create a relation
        relation_data = {
            'target_entry_id': entry2,
            'variant_type': "Spelling Variant",
            'direction': 'outgoing'
        }
        create_response = client.post(
            f'/api/entries/{entry1}/variants',
            data=json.dumps(relation_data),
            content_type='application/json'
        )
        assert create_response.status_code == 201

        # Verify relation exists
        get_response = client.get(f'/api/entries/{entry1}/variants')
        get_data = json.loads(get_response.data)
        variants = get_data.get('variants', [])
        assert len([v for v in variants if v.get('direction') == 'outgoing']) == 1

        # Delete the relation
        delete_response = client.delete(
            f'/api/entries/{entry1}/variants/{entry2}'
        )
        assert delete_response.status_code == 200

        delete_data = json.loads(delete_response.data)
        assert delete_data['success'] is True

        # Verify relation is removed
        get_response2 = client.get(f'/api/entries/{entry1}/variants')
        get_data2 = json.loads(get_response2.data)
        variants2 = get_data2.get('variants', [])
        outgoing_after_delete = [v for v in variants2 if v.get('direction') == 'outgoing']
        assert len(outgoing_after_delete) == 0

        # Verify reverse relation is also removed
        entry2_response = client.get(f'/api/entries/{entry2}/variants')
        entry2_data = json.loads(entry2_response.data)
        entry2_variants = entry2_data.get('variants', [])
        incoming_to_entry2 = [v for v in entry2_variants if v.get('direction') == 'incoming']
        assert len(incoming_to_entry2) == 0

    @pytest.mark.integration
    def test_delete_nonexistent_relation(self, client: FlaskClient, test_entries):
        """Test DELETE variant relation that doesn't exist returns 404."""
        entry1 = test_entries['entry1']
        entry2 = test_entries['entry2']

        # Try to delete a relation that was never created
        delete_response = client.delete(
            f'/api/entries/{entry1}/variants/{entry2}'
        )

        assert delete_response.status_code == 404

    @pytest.mark.integration
    def test_create_relation_missing_target(self, client: FlaskClient, test_entries):
        """Test creating relation with non-existent target entry returns 404."""
        entry1 = test_entries['entry1']

        relation_data = {
            'target_entry_id': 'nonexistent_entry',
            'variant_type': "Spelling Variant",
            'direction': 'outgoing'
        }

        response = client.post(
            f'/api/entries/{entry1}/variants',
            data=json.dumps(relation_data),
            content_type='application/json'
        )

        assert response.status_code == 404

    @pytest.mark.integration
    def test_circular_reference_detection(self, client: FlaskClient, test_entries):
        """Test that circular references are detected and prevented."""
        entry1 = test_entries['entry1']
        entry2 = test_entries['entry2']

        # First create a relation from entry1 to entry2
        relation_data = {
            'target_entry_id': entry2,
            'variant_type': "Spelling Variant",
            'direction': 'outgoing'
        }
        create_response = client.post(
            f'/api/entries/{entry1}/variants',
            data=json.dumps(relation_data),
            content_type='application/json'
        )
        assert create_response.status_code == 201

        # Try to create a relation from entry2 to entry1 (circular)
        reverse_relation_data = {
            'target_entry_id': entry1,
            'variant_type': "Spelling Variant",
            'direction': 'outgoing'
        }
        reverse_response = client.post(
            f'/api/entries/{entry2}/variants',
            data=json.dumps(reverse_relation_data),
            content_type='application/json'
        )

        # Should return 400 for circular reference
        assert reverse_response.status_code == 400

        response_data = json.loads(reverse_response.data)
        assert 'error' in response_data
        assert 'circular' in response_data['error'].lower()

    @pytest.mark.integration
    def test_self_reference_detection(self, client: FlaskClient, test_entries):
        """Test that self-references (entry variant of itself) are detected."""
        entry1 = test_entries['entry1']

        relation_data = {
            'target_entry_id': entry1,  # Same as source
            'variant_type': "Spelling Variant",
            'direction': 'outgoing'
        }

        response = client.post(
            f'/api/entries/{entry1}/variants',
            data=json.dumps(relation_data),
            content_type='application/json'
        )

        # Should return 400 for self-reference
        assert response.status_code == 400

        response_data = json.loads(response.data)
        assert 'error' in response_data

    @pytest.mark.integration
    def test_duplicate_relation_not_allowed(self, client: FlaskClient, test_entries):
        """Test that duplicate variant relations are not created."""
        entry1 = test_entries['entry1']
        entry2 = test_entries['entry2']

        # Create first relation
        relation_data = {
            'target_entry_id': entry2,
            'variant_type': "Spelling Variant",
            'direction': 'outgoing'
        }
        response1 = client.post(
            f'/api/entries/{entry1}/variants',
            data=json.dumps(relation_data),
            content_type='application/json'
        )
        assert response1.status_code == 201

        # Try to create duplicate
        response2 = client.post(
            f'/api/entries/{entry1}/variants',
            data=json.dumps(relation_data),
            content_type='application/json'
        )

        # Should return 400 for duplicate
        assert response2.status_code == 400

        response_data = json.loads(response2.data)
        assert 'error' in response_data
        assert 'duplicate' in response_data['error'].lower()

    @pytest.mark.integration
    def test_get_entry_not_found(self, client: FlaskClient):
        """Test GET variants for non-existent entry returns 404."""
        response = client.get('/api/entries/nonexistent_entry/variants')
        assert response.status_code == 404

    @pytest.mark.integration
    def test_variant_relation_with_traits(self, client: FlaskClient, test_entries):
        """Test variant relation with additional traits."""
        entry1 = test_entries['entry1']
        entry2 = test_entries['entry2']

        relation_data = {
            'target_entry_id': entry2,
            'variant_type': "Stopień najwyższy",
            'direction': 'outgoing',
            'traits': {
                'is-primary': 'true',
                'comment': 'Informal form'
            }
        }

        response = client.post(
            f'/api/entries/{entry1}/variants',
            data=json.dumps(relation_data),
            content_type='application/json'
        )

        assert response.status_code == 201

        # Verify traits are stored
        get_response = client.get(f'/api/entries/{entry1}/variants')
        get_data = json.loads(get_response.data)
        variants = get_data.get('variants', [])
        outgoing = [v for v in variants if v.get('direction') == 'outgoing']
        assert len(outgoing) == 1
        variant = outgoing[0]
        assert 'traits' in variant
        assert variant['traits'].get('is-primary') == 'true'

    @pytest.mark.integration
    def test_variant_ordering(self, client: FlaskClient, test_entries):
        """Test that variant relations maintain order."""
        entry1 = test_entries['entry1']
        entry2 = test_entries['entry2']
        entry3 = test_entries['entry3']

        # Create multiple variants
        for target_id in [entry2, entry3]:
            relation_data = {
                'target_entry_id': target_id,
                'variant_type': "Variant",
                'direction': 'outgoing'
            }
            response = client.post(
                f'/api/entries/{entry1}/variants',
                data=json.dumps(relation_data),
                content_type='application/json'
            )
            assert response.status_code == 201

        # Verify order is maintained
        get_response = client.get(f'/api/entries/{entry1}/variants')
        get_data = json.loads(get_response.data)
        variants = get_data.get('variants', [])
        outgoing_variants = [v for v in variants if v.get('direction') == 'outgoing']
        assert len(outgoing_variants) == 2
        # First created should be first in list
        assert outgoing_variants[0]['ref'] == entry2
        assert outgoing_variants[1]['ref'] == entry3

    @pytest.mark.integration
    def test_create_is_variant_of_with_source_not_found(self, client: FlaskClient, test_entries):
        """Test POST is-variant-of with non-existent source returns 404."""
        entry_id = test_entries['entry1']

        relation_data = {
            'target_entry_id': 'nonexistent_source',
            'variant_type': "Spelling Variant",
            'direction': 'incoming'
        }

        response = client.post(
            f'/api/entries/{entry_id}/variants',
            data=json.dumps(relation_data),
            content_type='application/json'
        )

        assert response.status_code == 404


@pytest.mark.integration
class TestVariantRelationsAPIValidation:
    """Test validation and error handling for variant relations API."""

    @pytest.fixture
    def test_entry(self, client: FlaskClient):
        """Create a single test entry."""
        entry_id = 'validation_test_entry'

        # Clean up any existing entry first
        try:
            client.delete(f'/api/entries/{entry_id}')
        except Exception:
            pass

        entry_data = {
            'id': entry_id,
            'lexical_unit': {'en': 'test'},
            'senses': [{'id': 'sense1', 'definition': {'en': 'a test entry'}}]
        }

        response = client.post('/api/entries',
                               data=json.dumps(entry_data),
                               content_type='application/json')
        assert response.status_code == 201

        yield entry_id

        # Cleanup after tests
        try:
            client.delete(f'/api/entries/{entry_id}')
        except Exception:
            pass

    @pytest.mark.integration
    def test_missing_required_fields(self, client: FlaskClient, test_entry):
        """Test POST with missing required fields returns 400."""
        # Missing target_entry_id
        relation_data = {
            'variant_type': "Spelling Variant",
            'direction': 'outgoing'
        }

        response = client.post(
            f'/api/entries/{test_entry}/variants',
            data=json.dumps(relation_data),
            content_type='application/json'
        )

        assert response.status_code == 400

        data = json.loads(response.data)
        assert 'error' in data

    @pytest.mark.integration
    def test_invalid_json(self, client: FlaskClient, test_entry):
        """Test POST with invalid JSON returns 400."""
        response = client.post(
            f'/api/entries/{test_entry}/variants',
            data='not valid json',
            content_type='application/json'
        )

        assert response.status_code == 400

    @pytest.mark.integration
    def test_empty_target_id(self, client: FlaskClient, test_entry):
        """Test POST with empty target_entry_id returns 400."""
        relation_data = {
            'target_entry_id': '',
            'variant_type': "Spelling Variant",
            'direction': 'outgoing'
        }

        response = client.post(
            f'/api/entries/{test_entry}/variants',
            data=json.dumps(relation_data),
            content_type='application/json'
        )

        assert response.status_code == 400

    @pytest.mark.integration
    def test_get_variants_response_format(self, client: FlaskClient, test_entry):
        """Test GET variants response has expected format."""
        response = client.get(f'/api/entries/{test_entry}/variants')

        assert response.status_code == 200

        data = json.loads(response.data)

        # Should have these keys
        assert 'variants' in data
        assert 'entry_id' in data

        # variants should be a list
        assert isinstance(data['variants'], list)
