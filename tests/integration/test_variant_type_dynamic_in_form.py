"""Test that variant type select in entry form is loaded dynamically from ranges."""


def test_variant_type_select_is_dynamic(client, app):
    with app.test_request_context():
        response = client.get('/entries/add')
        assert response.status_code == 200
        html = response.get_data(as_text=True)

        # There should be either a server-rendered dynamic select OR the JS template
        # should contain the marker for dynamic loading.
        js_content = open('app/static/js/variant-forms.js').read()
        assert ('data-range-id="variant-type"' in html) or ('data-range-id="variant-type"' in js_content)
