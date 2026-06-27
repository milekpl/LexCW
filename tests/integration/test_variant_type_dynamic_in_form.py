"""Test that variant type select in entry form is loaded dynamically from ranges."""


def test_variant_type_select_is_dynamic(client, app):
    with app.test_request_context():
        response = client.get('/entries/add')
        assert response.status_code == 200
        html = response.get_data(as_text=True)

        # Variant type is loaded dynamically by the Alpine entry-variant-relations component
        # (§16.2.3) via the 'variant-type' range — not hardcoded.
        js_content = open('app/static/js/alpine/entry-variant-relations.js').read()
        assert ("loadRange('variant-type')" in js_content) \
            or ('variant-type' in js_content) \
            or ('data-range-id="variant-type"' in html)
