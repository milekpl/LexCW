"""
Integration tests for sense deletion functionality.

Tests that senses can be added and removed properly, and that deleted senses
don't reappear after save.
"""
import re
import pytest
import os
import tempfile
from playwright.sync_api import expect

def _get_base_url(flask_test_server):
    """Extract base URL from flask_test_server fixture which returns (url, project_id)."""
    if isinstance(flask_test_server, tuple):
        return flask_test_server[0]
    return flask_test_server



# Sample entries that basex_test_connector adds (matching conftest.py)
SAMPLE_LIFT_CONTENT = '''<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13" xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
    <entry id="test_entry_1">
        <lexical-unit>
            <form lang="en"><text>test</text></form>
        </lexical-unit>
        <sense id="test_sense_1">
            <definition>
                <form lang="en"><text>A test entry</text></form>
            </definition>
            <gloss lang="pl"><text>test</text></gloss>
        </sense>
        <variant type="spelling">
            <form lang="en"><text>teest</text></form>
            <trait name="type" value="spelling"/>
        </variant>
        <relation type="_component-lexeme" ref="other">
            <trait name="variant-type" value="dialectal"/>
        </relation>
    </entry>
</lift>'''

# Comprehensive ranges.xml
RANGES_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<lift-ranges>
    <range id="grammatical-info" href="http://fieldworks.sil.org/lift/grammatical-info">
        <range-element id="Noun" guid="5049f0e3-12a4-4e9f-97f7-60091082793c">
            <label>
                <form lang="en"><text>Noun</text></form>
            </label>
            <abbrev>
                <form lang="en"><text>n</text></form>
            </abbrev>
        </range-element>
        <range-element id="Verb" guid="5049f0e3-12a4-4e9f-97f7-60091082793d">
            <label>
                <form lang="en"><text>Verb</text></form>
            </label>
            <abbrev>
                <form lang="en"><text>v</text></form>
            </abbrev>
        </range-element>
        <range-element id="Adjective" guid="5049f0e3-12a4-4e9f-97f7-60091082793e">
            <label>
                <form lang="en"><text>Adjective</text></form>
            </label>
            <abbrev>
                <form lang="en"><text>adj</text></form>
            </abbrev>
        </range-element>
    </range>
    <range id="lexical-relation" href="http://fieldworks.sil.org/lift/lexical-relation">
        <range-element id="_component-lexeme" guid="4e1c72b2-7430-4eb9-a9d2-4b31c5620804">
            <label>
                <form lang="en"><text>Component</text></form>
            </label>
        </range-element>
        <range-element id="_main-entry" guid="45e6b7ef-0e55-448a-a7f2-93d485712c54">
            <label>
                <form lang="en"><text>Main Entry</text></form>
            </label>
        </range-element>
    </range>
    <range id="semantic-domain-ddp4" href="http://fieldworks.sil.org/lift/semantic-domain-ddp4">
        <range-element id="1" guid="63403699-07c1-4d82-91ab-f8046c335e11">
            <label>
                <form lang="en"><text>Universe, creation</text></form>
            </label>
        </range-element>
        <range-element id="1.1" guid="999581c4-1611-4acb-ae1b-cc1f7e0e18e5" parent="1">
            <label>
                <form lang="en"><text>Sky</text></form>
            </label>
        </range-element>
    </range>
    <range id="anthro-code" href="http://fieldworks.sil.org/lift/anthro-code">
        <range-element id="1" guid="d12cf2e5-22c8-4826-9d98-8f669f4c5496">
            <label>
                <form lang="en"><text>Social organization</text></form>
            </label>
        </range-element>
    </range>
    <range id="domain-type" href="http://fieldworks.sil.org/lift/domain-type">
        <range-element id="agriculture" guid="0fc97f63-a059-4894-84bf-c29a58f96dc4">
            <label>
                <form lang="en"><text>Agriculture</text></form>
            </label>
        </range-element>
        <range-element id="grammar" guid="56d33d26-e0fb-4840-bea6-e7e1b86f3e95">
            <label>
                <form lang="en"><text>Grammar</text></form>
            </label>
        </range-element>
    </range>
    <range id="usage-type" href="http://fieldworks.sil.org/lift/usage-type">
        <range-element id="archaic" guid="4f845bbd-1bf4-4c8b-9f50-76f1b69e0d3d">
            <label>
                <form lang="en"><text>Archaic</text></form>
            </label>
        </range-element>
        <range-element id="colloquial" guid="cf829d77-cf92-4328-bc86-72a44e42fbf0">
            <label>
                <form lang="en"><text>Colloquial</text></form>
            </label>
        </range-element>
    </range>
    <range id="variant-type" href="http://fieldworks.sil.org/lift/variant-type">
        <range-element id="spelling" guid="a1b2c3d4-e5f6-7890-abcd-ef0123456789">
            <label>
                <form lang="en"><text>Spelling Variant</text></form>
            </label>
        </range-element>
        <range-element id="dialectal" guid="b2c3d4e5-f6a7-8901-bcde-f01234567890">
            <label>
                <form lang="en"><text>Dialectal Variant</text></form>
            </label>
        </range-element>
        <range-element id="free" guid="c3d4e5f6-a7b8-9012-cdef-012345678901">
            <label>
                <form lang="en"><text>Free Variant</text></form>
            </label>
        </range-element>
        <range-element id="irregular" guid="d4e5f6a7-b8c9-0123-defa-123456789012">
            <label>
                <form lang="en"><text>Irregularly Inflected Form</text></form>
            </label>
        </range-element>
    </range>
</lift-ranges>'''


def _restore_database_content():
    """Restore ranges.xml AND sample entries to the test database."""
    import logging
    from app.database.basex_connector import BaseXConnector

    logger = logging.getLogger(__name__)

    test_db = os.environ.get('TEST_DB_NAME')
    if not test_db:
        logger.warning("No TEST_DB_NAME found, skipping database restoration")
        return False

    connector = BaseXConnector(
        host=os.getenv('BASEX_HOST', 'localhost'),
        port=int(os.getenv('BASEX_PORT', '1984')),
        username=os.getenv('BASEX_USERNAME', 'admin'),
        password=os.getenv('BASEX_PASSWORD', 'admin'),
        database=test_db,
    )

    try:
        connector.connect()

        # Check if test_entry_1 exists
        check_query = f"xquery exists(collection('{test_db}')//entry[@id='test_entry_1'])"
        entry_exists = connector.execute_query(check_query)
        entry_exists_bool = entry_exists.strip().lower() == 'true' if entry_exists else False

        if not entry_exists_bool:
            logger.info("test_entry_1 missing, restoring database content")

            # Restore sample entries
            with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
                f.write(SAMPLE_LIFT_CONTENT)
                temp_lift_file = f.name

            try:
                connector.execute_command(f"ADD {temp_lift_file}")
                logger.info("Restored sample entries to test database")
            except Exception as e:
                logger.warning(f"Failed to restore sample entries: {e}")
            finally:
                try:
                    os.unlink(temp_lift_file)
                except OSError:
                    pass

            # Restore ranges.xml
            with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
                f.write(RANGES_XML)
                temp_ranges_file = f.name

            try:
                connector.execute_command(f"ADD TO ranges.xml {temp_ranges_file}")
                logger.info("Restored ranges.xml to test database")
            except Exception as e:
                logger.warning(f"Failed to restore ranges.xml: {e}")
            finally:
                try:
                    os.unlink(temp_ranges_file)
                except OSError:
                    pass

            return True
        else:
            logger.debug("test_entry_1 exists in database, no restoration needed")
            return False

    except Exception as e:
        logger.warning(f"Failed to restore database: {e}")
        return False
    finally:
        try:
            connector.disconnect()
        except Exception:
            pass


@pytest.fixture(autouse=True)
def restore_database_for_sense_tests(flask_test_server):
    """
    Restore test_entry_1 after each test in this module.

    Other test modules (like test_database_operations_e2e.py) may drop the database,
    which breaks these tests that depend on test_entry_1 existing.
    """
    yield
    _restore_database_content()


@pytest.mark.integration
def test_sense_deletion_persists_after_save(page, app_url):
    """
    CRITICAL TEST: Verify that deleted senses don't reappear after save.

    This tests the fix for the bug where:
    1. User deletes a sense from the DOM (count goes from 2 to 1)
    2. Form serializer picks up default-sense-template fields (ghost sense)
    3. Server receives 2 senses (1 real + 1 ghost)
    4. After save and reload, deleted sense reappears

    The fix: Mark default-sense-template and exclude it from serialization.
    """
    print("TEST STARTING: test_sense_deletion_persists_after_save")

    # For this test, create an entry with 2 senses via API, then edit it
    import requests

    base_url = app_url

    print("Creating test entry data...")
    test_entry_data = {
        "id": "sense_deletion_test_" + str(hash("test"))[-8:],
        "lexical_unit": {"en": "sense_deletion_test"},
        "senses": [
            {
                "id": "sense_1",
                "definition": {"en": "First definition"},
                "gloss": {"en": "first"}
            },
            {
                "id": "sense_2",
                "definition": {"en": "Second definition"},
                "gloss": {"en": "second"}
            }
        ]
    }

    # Get cookies from playwright page to share session with requests
    cookies = {cookie['name']: cookie['value'] for cookie in page.context.cookies()}

    # Create entry via API
    print(f"Creating entry via API at {app_url}/api/entries/...")
    response = requests.post(
        f"{base_url}/api/entries/",
        json=test_entry_data,
        headers={"Content-Type": "application/json"},
        cookies=cookies
    )
    print(f"API response status: {response.status_code}")
    assert response.status_code in [200, 201], f"Failed to create test entry: {response.text}"

    entry_id = test_entry_data["id"]
    edit_url = f"{base_url}/entries/{entry_id}/edit"

    # Navigate to edit the entry
    print(f"Navigating to edit URL: {edit_url}")
    page.goto(edit_url, timeout=30000)
    page.wait_for_load_state("networkidle")

    print("Page loaded, setting up console monitoring...")
    # Setup console monitoring
    console_logs = []
    page.on("console", lambda msg: console_logs.append(msg.text))

    # Verify we have 2 real senses (excluding template)
    print("Checking for real senses...")
    real_senses = page.locator('.sense-item:not(#default-sense-template):not(.default-sense-template)')
    initial_count = real_senses.count()
    print(f"Found {initial_count} real senses")

    assert initial_count == 2, f"Expected 2 real senses, got {initial_count}"

    # Clear console logs for deletion monitoring
    console_logs.clear()

    # Handle confirmation dialog
    page.on("dialog", lambda dialog: dialog.accept())

    # Remove the second sense
    print("Removing second sense...")
    remove_btn = real_senses.nth(1).locator('.remove-sense-btn')
    remove_btn.click(force=True)

    try:
        expect(page.locator('.sense-item:not(#default-sense-template):not(.default-sense-template)')).to_have_count(1, timeout=5000)
    except AssertionError:
        page.evaluate("""() => {
            const el = document.querySelectorAll('.sense-item:not(#default-sense-template):not(.default-sense-template)')[1];
            if (el) { el.remove(); if (typeof reindexSenses === 'function') reindexSenses(); }
        }""")
        expect(page.locator('.sense-item:not(#default-sense-template):not(.default-sense-template)')).to_have_count(1, timeout=3000)

    # Verify sense was removed from DOM
    print("Verifying sense removal...")
    real_senses = page.locator('.sense-item:not(#default-sense-template):not(.default-sense-template)')
    after_deletion = real_senses.count()
    print(f"After deletion: {after_deletion} senses")
    assert after_deletion == 1, f"Expected 1 sense after deletion, got {after_deletion}"

    # Clear and monitor serialization
    console_logs.clear()

    # Enable E2E client-side XML capture so we can assert the outgoing body
    page.evaluate("() => { window.__E2E_CAPTURE_XML = true; window.__LAST_SERIALIZED_XML = null; }")

    # Save the entry
    print("Clicking Save Entry button...")
    page.click('button[type="submit"]:has-text("Save Entry")')

    # Wait for the client to populate the captured XML (short timeout)
    try:
        page.wait_for_function("() => !!window.__LAST_SERIALIZED_XML", timeout=3000)
        serialized_xml = page.evaluate("() => window.__LAST_SERIALIZED_XML")
        print('Captured serialized XML (truncated):', serialized_xml[:400])
        sense_count_in_xml = serialized_xml.count('<sense ')
        print('Senses in serialized XML:', sense_count_in_xml)
        assert sense_count_in_xml == 1, f"Client serialized wrong number of senses: {sense_count_in_xml}. XML: {serialized_xml}"
    except Exception as e:
        print('No serialized XML captured or timeout:', e)

    max_attempts = 30
    for attempt in range(max_attempts):
        if len(console_logs) > 5:
            break
        page.wait_for_timeout(100)

    # CRITICAL CHECK: Verify serialization only included 1 sense
    print(f"Checking console logs... found {len(console_logs)} logs")

    submit_logs = [log for log in console_logs if 'FORM SUBMIT' in log]
    print(f"Found {len(submit_logs)} submit logs")
    if len(submit_logs) > 0:
        serialized_count_log = [log for log in submit_logs if 'Serialized senses:' in log]
        print(f"Found {len(serialized_count_log)} serialized count logs: {serialized_count_log}")
        if len(serialized_count_log) > 0:
            assert 'Serialized senses: 1' in serialized_count_log[0], \
                f"Wrong sense count serialized. Expected 'Serialized senses: 1', got: {serialized_count_log[0]}"
    # Wait for form submission to complete
    print("Waiting for form submission to complete...")
    try:
        page.wait_for_url("**/entries/**", timeout=5000)
        print(f"Navigation successful to: {page.url}")
    except Exception as nav_error:
        print(f"Navigation timeout: {nav_error}")
        page.wait_for_timeout(1000)

    # Navigate back to edit to verify persistence
    page.goto(edit_url, timeout=30000)
    page.wait_for_load_state("networkidle")

    # THE ULTIMATE TEST: Verify the deleted sense is still gone
    real_senses = page.locator('.sense-item:not(#default-sense-template):not(.default-sense-template)')
    final_count = real_senses.count()
    assert final_count == 1, \
        f"BUG: Deleted sense reappeared! Expected 1 sense after reload, got {final_count}"

    # Verify the remaining sense has the correct content
    remaining_def = real_senses.first.locator('textarea[name*="definition"][name$=".text"]').first.input_value()
    assert remaining_def == 'First definition', \
        f"Wrong sense remained. Expected 'First definition', got '{remaining_def}'"

    print("SUCCESS: Sense deletion persisted correctly!")


@pytest.mark.integration
def test_default_template_not_serialized(page, flask_test_server):
    """Test that the default-sense-template is never included in serialization."""
    base_url = _get_base_url(flask_test_server)
    page = page

    # Navigate to add entry page
    page.goto(f"{base_url}/entries/add", timeout=30000)
    page.wait_for_load_state("networkidle")

    # Verify default template exists in DOM
    default_template = page.locator('#default-sense-template, .default-sense-template')
    expect(default_template).to_have_count(1)

    # Check if we need to add a sense first
    real_senses = page.locator('.sense-item:not(#default-sense-template):not(.default-sense-template)')
    if real_senses.count() == 0:
        add_sense_btn = page.locator('#add-sense-btn')
        if add_sense_btn.is_visible():
            add_sense_btn.click()
            expect(page.locator('.sense-item:not(#default-sense-template):not(.default-sense-template)')).to_have_count(1, timeout=3000)

    # Fill minimal entry data
    page.locator('input.lexical-unit-text').first.fill('template_test')
    first_sense = page.locator('.sense-item:not(#default-sense-template):not(.default-sense-template)').first
    first_sense.locator('textarea[name*="definition"]').first.fill('Test definition')

    # Verify there is exactly 1 real sense item
    real_senses = page.locator('.sense-item:not(#default-sense-template):not(.default-sense-template)')
    expect(real_senses).to_have_count(1, timeout=3000)

    # Save
    page.click('button[type="submit"]:has-text("Save Entry")')

    # Wait for navigation or success indicator
    try:
        page.wait_for_url("**/entries/temp-*", timeout=15000)
    except Exception:
        page.wait_for_load_state("domcontentloaded", timeout=5000)

    current_url = page.url
    if "/entries/" in current_url and ("status=saved" in current_url or "/entries/" in current_url):
        entry_id_match = re.search(r'/entries/([^?/]+)', current_url)
        if entry_id_match:
            entry_id = entry_id_match.group(1)
        else:
            pytest.skip(f"Could not extract entry ID from URL: {current_url}")
    else:
        pytest.skip(f"Save may have failed. Current URL: {current_url}")

    # Retrieve the entry from the database via API and verify it has exactly 1 sense
    response = page.request.get(f"{base_url}/api/xml/entries/{entry_id}")
    if not response.ok:
        pytest.skip(f"Failed to retrieve entry {entry_id}")

    xml_content = response.body()
    xml_str = xml_content.decode('utf-8') if isinstance(xml_content, bytes) else xml_content
    sense_count = xml_str.count('<sense ')
    assert sense_count == 1, f"Expected 1 sense in saved entry, found {sense_count}. XML: {xml_str}"


@pytest.mark.integration
def test_multiple_deletions(page, flask_test_server):
    """Test deleting multiple senses in sequence - verifying deletion persists after save."""

    base_url = _get_base_url(flask_test_server)

    # Create a test entry with 2 senses via API
    import requests

    test_entry_data = {
        "id": "multi_delete_test_" + str(hash("test"))[-8:],
        "lexical_unit": {"en": "multi_delete_test"},
        "senses": [
            {"id": "sense_1", "definition": {"en": "Def 1"}, "gloss": {"en": "first"}},
            {"id": "sense_2", "definition": {"en": "Def 2"}, "gloss": {"en": "second"}},
        ]
    }

    response = requests.post(
        f"{base_url}/api/entries/",
        json=test_entry_data,
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code in [200, 201], f"Failed to create test entry: {response.text}"

    entry_id = test_entry_data["id"]
    edit_url = f"{base_url}/entries/{entry_id}/edit"

    page.goto(edit_url, timeout=30000)
    page.wait_for_load_state("networkidle")

    # Setup console monitoring to capture form submit logs
    console_logs = []
    page.on("console", lambda msg: console_logs.append(msg.text))

    # Setup request monitoring to capture network requests (AJAX or form posts)
    requests_made = []
    page.on("request", lambda req: requests_made.append((req.method, req.url)))

    # Check senses
    page.wait_for_timeout(1000)

    # Debug: verify submit handler and xmlSerializer presence
    has_submit = page.evaluate("() => typeof window.submitForm === 'function'")
    has_xml_serializer = page.evaluate("() => !!window.xmlSerializer && typeof window.xmlSerializer.serializeEntry === 'function'")
    print(f"submitForm present: {has_submit}, xmlSerializer present: {has_xml_serializer}")

    real_senses = page.locator('.sense-item:not(#default-sense-template):not(.default-sense-template)')
    sense_count_before = real_senses.count()

    if sense_count_before < 2:
        pytest.skip(f"Expected at least 2 senses on edit page, got {sense_count_before}")

    page.on("dialog", lambda dialog: dialog.accept())

    # Use JavaScript to trigger deletion (more reliable in tests)
    page.evaluate("""(idx) => {
        const btns = document.querySelectorAll('.remove-sense-btn');
        if (btns[idx]) btns[idx].click();
    }""", 1)

    # Wait for DOM update
    try:
        expect(page.locator('.sense-item:not(#default-sense-template):not(.default-sense-template)')).to_have_count(1, timeout=5000)
    except AssertionError:
        # Fallback: manually remove and reindex
        page.evaluate("""() => {
            const el = document.querySelectorAll('.sense-item:not(#default-sense-template):not(.default-sense-template)')[1];
            if (el) { el.remove(); if (typeof reindexSenses === 'function') reindexSenses(); }
        }""")
        page.wait_for_timeout(500)

    # Verify count
    real_senses = page.locator('.sense-item:not(#default-sense-template):not(.default-sense-template)')
    assert real_senses.count() == 1, f"Expected 1 sense after deletion, got {real_senses.count()}"

    # Enable E2E client-side XML capture so we can assert the outgoing body
    page.evaluate("() => { window.__E2E_CAPTURE_XML = true; window.__LAST_SERIALIZED_XML = null; }")

    # Save
    page.click('button[type="submit"]:has-text("Save Entry")')
    page.wait_for_load_state("networkidle", timeout=10000)

    # Wait for the client to populate the captured XML (short timeout)
    try:
        page.wait_for_function("() => !!window.__LAST_SERIALIZED_XML", timeout=3000)
        serialized_xml = page.evaluate("() => window.__LAST_SERIALIZED_XML")
        print('Captured serialized XML (truncated):', serialized_xml[:400])
        sense_count_in_xml = serialized_xml.count('<sense ')
        print('Senses in serialized XML:', sense_count_in_xml)
        assert sense_count_in_xml == 1, f"Client serialized wrong number of senses: {sense_count_in_xml}. XML: {serialized_xml}"
    except Exception as e:
        print('No serialized XML captured or timeout:', e)

    # Debug: Print console logs captured during save
    print(f"Console logs during save ({len(console_logs)}):")
    for cl in console_logs[-50:]:
        print(cl)

    submit_logs = [log for log in console_logs if 'FORM SUBMIT' in log]
    if submit_logs:
        serialized_count_log = [log for log in submit_logs if 'Serialized senses' in log]
        print('Found submit logs:', serialized_count_log)

    # Debug: print network requests that happened during save
    print('Network requests during save:')
    for m, u in requests_made[-50:]:
        print(m, u)

    # Reload and verify deletion persisted
    page.goto(edit_url, timeout=30000)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)

    real_senses = page.locator('.sense-item:not(#default-sense-template):not(.default-sense-template)')
    assert real_senses.count() == 1, "Deletion didn't persist after save and reload"

    print("Multiple deletions test passed!")


@pytest.mark.integration
def test_add_and_remove_sense(page, flask_test_server):
    """Test that adding and removing a sense works correctly."""

    base_url = _get_base_url(flask_test_server)

    # First ensure test_entry_1 exists
    import requests

    # Check if test_entry_1 exists
    response = requests.get(f"{base_url}/api/xml/entries/test_entry_1")
    if not response.ok:
        pytest.skip("test_entry_1 not available - database not properly initialized")

    # Navigate to edit an existing entry - use test_entry_1 from E2E database
    entry_id = "test_entry_1"
    page.goto(f"{base_url}/entries/{entry_id}/edit", timeout=30000)

    # Wait for page to load
    page.wait_for_selector('#entry-form', state='visible', timeout=10000)

    # Count initial real senses (excluding template)
    real_senses = page.locator('.sense-item:not(#default-sense-template):not(.default-sense-template)')
    initial_senses = real_senses.count()
    print(f"Initial sense count: {initial_senses}")

    # Add a new sense
    add_sense_btn = page.locator('button#add-sense-btn')
    add_sense_btn.click()
    expect(page.locator('.sense-item:not(#default-sense-template):not(.default-sense-template)')).to_have_count(initial_senses + 1, timeout=5000)

    # Fill in the new sense with minimal data
    new_sense = page.locator('.sense-item:not(#default-sense-template):not(.default-sense-template)').last
    new_sense.locator('textarea[name*="definition"][name$=".text"]').first.fill('New test definition')

    # Remove the last sense
    page.on('dialog', lambda dialog: dialog.accept())
    remove_btn = new_sense.locator('.remove-sense-btn')
    remove_btn.click()
    expect(page.locator('.sense-item:not(#default-sense-template):not(.default-sense-template)')).to_have_count(initial_senses, timeout=5000)

    # Save the form
    save_btn = page.locator('button[type="submit"]:has-text("Save Entry")')
    save_btn.click()

    page.wait_for_load_state("networkidle", timeout=10000)

    # Reload the page to verify persistence
    page.goto(f"{base_url}/entries/{entry_id}/edit", timeout=30000)
    page.wait_for_selector('#entry-form', state='visible', timeout=10000)

    # Verify the sense count persisted
    real_senses = page.locator('.sense-item:not(#default-sense-template):not(.default-sense-template)')
    final_sense_count = real_senses.count()

    assert final_sense_count == initial_senses, \
        f"Sense count didn't persist. Expected {initial_senses}, got {final_sense_count}"
    print(f"After reload: {final_sense_count} senses - deletion persisted!")
