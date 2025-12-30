from __future__ import annotations

import pytest


@pytest.mark.integration
class TestRangesEditorElementsResolved:
    def test_elements_editor_resolved_includes_children_and_effective(self, client):
        service = client.application.injector.get('RangesService') if False else client.application.injector.get(__import__('app.services.ranges_service', fromlist=['RangesService']).RangesService)
        range_id = 'editor-range'
        try:
            # Ensure not present
            try:
                service.delete_range(range_id)
            except Exception:
                pass

            guid = service.create_range({'id': range_id, 'labels': {'en': 'Editor Range'}})

            # Create parent and child via API to exercise controller cache invalidation
            parent = {
                'id': 'parentX',
                'labels': {'en': 'Parent X'},
                'abbrevs': {'en': 'PX'}
            }
            child = {
                'id': 'childX',
                'parent': 'parentX'
            }

            resp1 = client.post(f'/api/ranges-editor/{range_id}/elements', json=parent)
            assert resp1.status_code == 201, resp1.get_data(as_text=True)
            resp2 = client.post(f'/api/ranges-editor/{range_id}/elements', json=child)
            assert resp2.status_code == 201, resp2.get_data(as_text=True)

            # Request resolved view from editor endpoint
            resp = client.get(f'/api/ranges-editor/{range_id}/elements?resolved=true')
            assert resp.status_code == 200, resp.get_data(as_text=True)
            data = resp.get_json()
            assert data['success'] is True
            vals = data['data']

            # Find parent and child recursively
            def find_node(nodes, nid):
                for n in nodes:
                    if n.get('id') == nid:
                        return n
                    if n.get('children'):
                        found = find_node(n['children'], nid)
                        if found:
                            return found
                return None

            p = find_node(vals, 'parentX')
            c = find_node(vals, 'childX')
            assert p is not None, 'Parent not found in resolved values'
            assert c is not None, 'Child not found in resolved values'

            assert p.get('effective_abbrev') == 'PX'
            assert p.get('effective_label') == 'Parent X'
            assert c.get('effective_abbrev') == 'PX', f"Child effective_abbrev missing: {c}"
            assert c.get('effective_label') == 'Parent X'

        finally:
            try:
                service.delete_range(range_id)
            except Exception:
                pass

    def test_elements_editor_unresolved_has_no_effective(self, client):
        service = client.application.injector.get('RangesService') if False else client.application.injector.get(__import__('app.services.ranges_service', fromlist=['RangesService']).RangesService)
        range_id = 'editor-range-unresolved'
        try:
            try:
                service.delete_range(range_id)
            except Exception:
                pass

            guid = service.create_range({'id': range_id, 'labels': {'en': 'Editor Range Unresolved'}})
            parent = {'id': 'p2', 'labels': {'en': 'P2'}, 'abbrevs': {'en': 'P2'}}
            child = {'id': 'c2', 'parent': 'p2'}
            client.post(f'/api/ranges-editor/{range_id}/elements', json=parent)
            client.post(f'/api/ranges-editor/{range_id}/elements', json=child)

            resp = client.get(f'/api/ranges-editor/{range_id}/elements')
            assert resp.status_code == 200
            data = resp.get_json()
            vals = data['data']
            # ensure no effective fields present
            def any_effective(nodes):
                for n in nodes:
                    if 'effective_abbrev' in n or 'effective_label' in n:
                        return True
                    if n.get('children') and any_effective(n['children']):
                        return True
                return False
            assert not any_effective(vals)
        finally:
            try:
                service.delete_range(range_id)
            except Exception:
                pass
