from __future__ import annotations

import pytest
from app.services.ranges_service import RangesService


@pytest.mark.integration
class TestRangesResolvedIntegration:
    def test_resolved_range_inherits_abbrev_and_label(self, dict_service_with_db, app):
        """Integration test: create a hierarchical range in BaseX and verify resolved view."""
        dict_service = dict_service_with_db
        ranges_service = RangesService(dict_service.db_connector)

        range_id = 'integration-range'
        # Ensure we don't have it lingering
        try:
            ranges_service.delete_range(range_id)
        except Exception:
            pass

        # Create base range
        guid = ranges_service.create_range({'id': range_id, 'labels': {'en': 'Integration Range'}})

        try:
            # Prepare hierarchical values: parent with abbrev, child without
            parent = {
                'id': 'parentX',
                'labels': {'en': 'Parent X'},
                'abbrevs': {'en': 'PX'}
            }
            child = {
                'id': 'childX',
                'parent': 'parentX'
            }

            # Update range to include elements
            ranges_service.update_range(range_id, {
                'id': range_id,
                'guid': guid,
                'values': [parent, child]
            })

            # Request resolved view from service
            resolved = ranges_service.get_range(range_id, resolved=True)
            vals = resolved.get('values', [])

            # Find parent and child
            p = next((v for v in vals if v['id'] == 'parentX'), None)
            assert p is not None
            assert p['effective_label'] == 'Parent X'
            assert p['effective_abbrev'] == 'PX'

            c = None
            # Depending on whether parent-based or direct hierarchy, child may be nested
            for v in vals:
                if v.get('children'):
                    for ch in v['children']:
                        if ch['id'] == 'childX':
                            c = ch
            if not c:
                # Could be top-level if parent attribute not respected during update
                c = next((v for v in vals if v['id'] == 'childX'), None)

            assert c is not None
            assert c['effective_label'] == 'Parent X'
            assert c['effective_abbrev'] == 'PX'
        finally:
            # Clean up range from DB
            try:
                ranges_service.delete_range(range_id)
            except Exception:
                pass

    def test_ranges_api_returns_resolved_view(self, client):
        # Use the application's injector to ensure the service uses the same test DB
        service = client.application.injector.get(RangesService)
        range_id = 'integration-range'
        try:
            service.delete_range(range_id)
        except Exception:
            pass

        # Reduce noisy debug logging from parser/db for this test to speed runs
        import logging
        logging.getLogger('app.parsers.lift_parser').setLevel(logging.WARNING)
        logging.getLogger('app.services.dictionary_service').setLevel(logging.WARNING)

        guid = service.create_range({'id': range_id, 'labels': {'en': 'Integration Range'}})
        try:
            parent = {'id': 'parentX', 'labels': {'en': 'Parent X'}, 'abbrevs': {'en': 'PX'}}
            child = {'id': 'childX', 'parent': 'parentX'}
            service.update_range(range_id, {'id': range_id, 'guid': guid, 'values': [parent, child]})

            # Ensure the application-level DictionaryService refreshes its ranges cache
            from app.services.dictionary_service import DictionaryService
            dict_service = client.application.injector.get(DictionaryService)
            dict_service.get_ranges(force_reload=True, resolved=False)

            resp = client.get(f'/api/ranges/{range_id}?resolved=true')
            assert resp.status_code == 200, resp.get_data(as_text=True)
            data = resp.get_json()
            assert data['success'] is True
            payload = data['data']
            assert 'values' in payload

            # Recursive search helpers to find nodes regardless of nesting
            def find_node(nodes, node_id):
                for n in nodes:
                    if n.get('id') == node_id:
                        return n
                    if n.get('children'):
                        found = find_node(n['children'], node_id)
                        if found:
                            return found
                return None

            vals = payload['values']
            pnode = find_node(vals, 'parentX')
            cnode = find_node(vals, 'childX')

            assert pnode is not None, "Parent node not found in returned values"
            assert cnode is not None, "Child node not found in returned values"

            assert pnode.get('effective_abbrev') == 'PX'
            assert pnode.get('effective_label') == 'Parent X'
            # Child should inherit effective label/abbrev from parent
            assert cnode.get('effective_abbrev') == 'PX'
            assert cnode.get('effective_label') == 'Parent X'
        finally:
            try:
                service.delete_range(range_id)
            except Exception:
                pass
