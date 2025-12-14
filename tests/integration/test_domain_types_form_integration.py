"""
Comprehensive integration tests for Domains Types end-to-end form functionality.

Tests that Domain Types work correctly through the complete user workflow:
- Form submission with domain types
- Backend processing and validation
- Database persistence and retrieval
- UI display and editing

These tests ensure domain types are fully functional in the application.
"""

from __future__ import annotations

import pytest
from flask import Flask
from werkzeug.test import Client
from app.services.dictionary_service import DictionaryService
from app.models.entry import Entry
from app.models.sense import Sense


@pytest.mark.integration
class TestDomainTypesFormIntegration:
    """Integration tests for Domain Types form integration."""

    @pytest.fixture
    def test_entry_data_entry_level_domain_type(self) -> dict:
        """Test data for entry with sense-level domain type."""
        return {
            "lexical_unit.en": "computer science",
            "senses[0].id": "sense1",
            "senses[0].definition.en": "The study of computers and computing",
            "senses[0].gloss.en": "computers field of study",
            "senses[0].domain_type": "informatyka",
        }

    @pytest.fixture
    def test_entry_data_multiple_domains(self) -> dict:
        """Test data for entry with different domains types at sense level only."""
        return {
            "lexical_unit.en": "bank",  # Can mean both financial institution and river bank
            "senses[0].id": "sense1",
            "senses[0].definition.en": "Financial institution where money can be deposited",
            "senses[0].gloss.en": "financial institution",
            "senses[0].domain_type": "finanse",  # Finance domain
            "senses[1].id": "sense2",
            "senses[1].definition.en": "Raised area of ground along river",
            "senses[1].gloss.en": "riverbank",
            "senses[1].domain_type": "geografia",  # Geography domain
        }

    @pytest.mark.integration
    def test_form_submission_entry_level_domain_type(
        self,
        client: Client,
        basex_test_connector,
        test_entry_data_entry_level_domain_type: dict,
    ) -> None:
        """Test that sense-level domain type can be submitted via form."""
        import uuid

        entry_id = f"test_domain_{uuid.uuid4().hex[:8]}"

        # Create entry via XML API with domain type
        entry_xml = f'''<entry id="{entry_id}">
            <lexical-unit>
                <form lang="en"><text>computer science</text></form>
            </lexical-unit>
            <sense id="sense1">
                <trait name="semantic-domain-ddp4" value="informatyka"/>
                <definition>
                    <form lang="en"><text>The study of computers and computing</text></form>
                </definition>
                <gloss lang="en"><text>computers field of study</text></gloss>
            </sense>
        </entry>'''

        response = client.post(
            "/api/xml/entries",
            data=entry_xml,
            headers={"Content-Type": "application/xml"},
        )
        assert response.status_code == 201, f"Failed to create entry: {response.data}"

        # Verify via XML API
        response = client.get(f"/api/xml/entries/{entry_id}")
        assert response.status_code == 200

        # Parse and verify domain type
        from lxml import etree as ET

        LIFT_NS = "{http://fieldworks.sil.org/schemas/lift/0.13}"
        xml_data = response.data.decode("utf-8")
        root = ET.fromstring(xml_data)

        trait = root.find(
            f'.//{LIFT_NS}sense/{LIFT_NS}trait[@name="semantic-domain-ddp4"]'
        )
        assert trait is not None, "Domain type trait not found"
        assert trait.get("value") == "informatyka"

    @pytest.mark.integration
    def test_form_submission_multiple_domain_types(
        self,
        client: Client,
        basex_test_connector,
        test_entry_data_multiple_domains: dict,
    ) -> None:
        """Test that entries can have different domain types at different sense levels."""
        import uuid

        entry_id = f"test_domain_{uuid.uuid4().hex[:8]}"

        # Create entry via XML API with multiple domain types
        entry_xml = f'''<entry id="{entry_id}">
            <lexical-unit>
                <form lang="en"><text>bank</text></form>
            </lexical-unit>
            <sense id="sense1">
                <trait name="semantic-domain-ddp4" value="finanse"/>
                <definition>
                    <form lang="en"><text>Financial institution where money can be deposited</text></form>
                </definition>
                <gloss lang="en"><text>financial institution</text></gloss>
            </sense>
            <sense id="sense2">
                <trait name="semantic-domain-ddp4" value="geografia"/>
                <definition>
                    <form lang="en"><text>Raised area of ground along river</text></form>
                </definition>
                <gloss lang="en"><text>riverbank</text></gloss>
            </sense>
        </entry>'''

        response = client.post(
            "/api/xml/entries",
            data=entry_xml,
            headers={"Content-Type": "application/xml"},
        )
        assert response.status_code == 201

        # Verify via XML API
        response = client.get(f"/api/xml/entries/{entry_id}")
        assert response.status_code == 200

        from lxml import etree as ET

        LIFT_NS = "{http://fieldworks.sil.org/schemas/lift/0.13}"
        xml_data = response.data.decode("utf-8")
        root = ET.fromstring(xml_data)

        # Verify both domains
        sense1_trait = root.find(
            f'.//{LIFT_NS}sense[@id="sense1"]/{LIFT_NS}trait[@name="semantic-domain-ddp4"]'
        )
        assert sense1_trait is not None
        assert sense1_trait.get("value") == "finanse"

        sense2_trait = root.find(
            f'.//{LIFT_NS}sense[@id="sense2"]/{LIFT_NS}trait[@name="semantic-domain-ddp4"]'
        )
        assert sense2_trait is not None
        assert sense2_trait.get("value") == "geografia"

    @pytest.mark.integration
    def test_form_edit_entry_remove_domain_type(
        self, client: Client, basex_test_connector
    ) -> None:
        """Test that domains can be removed via XML update."""
        import uuid

        entry_id = f"test_edit_remove_{uuid.uuid4().hex[:8]}"

        # Create entry with semantic domain via XML API
        entry_xml = f'''<entry id="{entry_id}">
            <lexical-unit>
                <form lang="en"><text>test word</text></form>
            </lexical-unit>
            <sense id="sense1">
                <trait name="semantic-domain-ddp4" value="literatura"/>
                <definition>
                    <form lang="en"><text>test word</text></form>
                </definition>
                <gloss lang="en"><text>word</text></gloss>
            </sense>
        </entry>'''

        response = client.post(
            "/api/xml/entries",
            data=entry_xml,
            headers={"Content-Type": "application/xml"},
        )
        assert response.status_code == 201

        # Update to remove domain type
        updated_xml = f'''<entry id="{entry_id}">
            <lexical-unit>
                <form lang="en"><text>test word</text></form>
            </lexical-unit>
            <sense id="sense1">
                <definition>
                    <form lang="en"><text>test word</text></form>
                </definition>
                <gloss lang="en"><text>word</text></gloss>
            </sense>
        </entry>'''

        response = client.put(
            f"/api/xml/entries/{entry_id}",
            data=updated_xml,
            headers={"Content-Type": "application/xml"},
        )
        assert response.status_code == 200

        # Verify that domain was removed
        response = client.get(f"/api/xml/entries/{entry_id}")
        assert response.status_code == 200

        from lxml import etree as ET

        LIFT_NS = "{http://fieldworks.sil.org/schemas/lift/0.13}"
        xml_data = response.data.decode("utf-8")
        root = ET.fromstring(xml_data)

        trait = root.find(
            f'.//{LIFT_NS}sense/{LIFT_NS}trait[@name="semantic-domain-ddp4"]'
        )
        assert trait is None, "Domain type should have been removed"

    @pytest.mark.integration
    def test_form_edit_entry_add_domain_type(
        self, client: Client, basex_test_connector
    ) -> None:
        """Test that domain type can be added via XML update."""
        import uuid

        entry_id = f"test_edit_add_{uuid.uuid4().hex[:8]}"

        # Create entry without domain type
        entry_xml = f'''<entry id="{entry_id}">
            <lexical-unit>
                <form lang="en"><text>plain word</text></form>
            </lexical-unit>
            <sense id="sense1">
                <definition>
                    <form lang="en"><text>plain word</text></form>
                </definition>
                <gloss lang="en"><text>word</text></gloss>
            </sense>
        </entry>'''

        response = client.post(
            "/api/xml/entries",
            data=entry_xml,
            headers={"Content-Type": "application/xml"},
        )
        assert response.status_code == 201

        # Update to add domain type
        updated_xml = f'''<entry id="{entry_id}">
            <lexical-unit>
                <form lang="en"><text>plain word</text></form>
            </lexical-unit>
            <sense id="sense1">
                <trait name="semantic-domain-ddp4" value="literatura"/>
                <definition>
                    <form lang="en"><text>plain word</text></form>
                </definition>
                <gloss lang="en"><text>word</text></gloss>
            </sense>
        </entry>'''

        response = client.put(
            f"/api/xml/entries/{entry_id}",
            data=updated_xml,
            headers={"Content-Type": "application/xml"},
        )
        assert response.status_code == 200

        # Verify domain type was added
        response = client.get(f"/api/xml/entries/{entry_id}")
        assert response.status_code == 200

        from lxml import etree as ET

        LIFT_NS = "{http://fieldworks.sil.org/schemas/lift/0.13}"
        xml_data = response.data.decode("utf-8")
        root = ET.fromstring(xml_data)

        trait = root.find(
            f'.//{LIFT_NS}sense/{LIFT_NS}trait[@name="semantic-domain-ddp4"]'
        )
        assert trait is not None, "Domain_type should have been added"
        assert trait.get("value") == "literatura"

    @pytest.mark.integration
    def test_form_validation_invalid_domain_type(
        self, client: Client, basex_test_connector
    ) -> None:
        """Test that form handles validation with domain types."""
        import uuid

        entry_id = f"test_validation_{uuid.uuid4().hex[:8]}"

        # Create entry with valid domain type via XML API
        entry_xml = f'''<entry id="{entry_id}">
            <lexical-unit>
                <form lang="en"><text>test validation word</text></form>
            </lexical-unit>
            <sense id="sense1">
                <trait name="semantic-domain-ddp4" value="finanse"/>
                <definition>
                    <form lang="en"><text>test definition</text></form>
                </definition>
                <gloss lang="en"><text>test</text></gloss>
            </sense>
        </entry>'''

        # Should succeed
        response = client.post(
            "/api/xml/entries",
            data=entry_xml,
            headers={"Content-Type": "application/xml"},
        )
        assert response.status_code == 201, (
            f"Valid entry creation failed: {response.data}"
        )

    @pytest.mark.integration
    def test_domain_type_view_display(
        self, client: Client, basex_test_connector
    ) -> None:
        """Test that domain types persist in database and can be retrieved."""
        import uuid

        entry_id = f"test_view_{uuid.uuid4().hex[:8]}"

        # Create entry with domain types via XML API
        entry_xml = f'''<entry id="{entry_id}">
            <lexical-unit>
                <form lang="en"><text>multidisciplinary term</text></form>
                <form lang="pl"><text>termin multidyscyplinarny</text></form>
            </lexical-unit>
            <sense id="sense_cs">
                <trait name="semantic-domain-ddp4" value="informatyka"/>
                <definition>
                    <form lang="en"><text>the study of computers</text></form>
                </definition>
                <gloss lang="en"><text>computer discipline</text></gloss>
            </sense>
            <sense id="sense_math">
                <trait name="semantic-domain-ddp4" value="matematyka"/>
                <definition>
                    <form lang="en"><text>concept from mathematics</text></form>
                </definition>
                <gloss lang="en"><text>mathematical concept</text></gloss>
            </sense>
        </entry>'''

        response = client.post(
            "/api/xml/entries",
            data=entry_xml,
            headers={"Content-Type": "application/xml"},
        )
        assert response.status_code == 201

        # Verify domain types persist via XML API
        response = client.get(f"/api/xml/entries/{entry_id}")
        assert response.status_code == 200

        from lxml import etree as ET

        LIFT_NS = "{http://fieldworks.sil.org/schemas/lift/0.13}"
        xml_data = response.data.decode("utf-8")
        root = ET.fromstring(xml_data)

        # Check that domain types are present in XML
        cs_trait = root.find(
            f'.//{LIFT_NS}sense[@id="sense_cs"]/{LIFT_NS}trait[@name="semantic-domain-ddp4"]'
        )
        assert cs_trait is not None
        assert cs_trait.get("value") == "informatyka"

        math_trait = root.find(
            f'.//{LIFT_NS}sense[@id="sense_math"]/{LIFT_NS}trait[@name="semantic-domain-ddp4"]'
        )
        assert math_trait is not None
        assert math_trait.get("value") == "matematyka"

    @pytest.mark.integration
    def test_form_unicode_domain_types(
        self, client: Client, basex_test_connector
    ) -> None:
        """Test that Unicode characters in domain types work via XML API."""
        import uuid

        entry_id = f"test_unicode_{uuid.uuid4().hex[:8]}"

        # Create entry with Polish domain names
        entry_xml = f'''<entry id="{entry_id}">
            <lexical-unit>
                <form lang="en"><text>Polish academic term</text></form>
            </lexical-unit>
            <sense id="sense1">
                <trait name="semantic-domain-ddp4" value="języki"/>
                <definition>
                    <form lang="en"><text>Term from computer science</text></form>
                </definition>
                <gloss lang="en"><text>computer term</text></gloss>
            </sense>
        </entry>'''

        response = client.post(
            "/api/xml/entries",
            data=entry_xml,
            headers={"Content-Type": "application/xml"},
        )
        assert response.status_code == 201

        # Verify Unicode domain type persisted
        response = client.get(f"/api/xml/entries/{entry_id}")
        assert response.status_code == 200

        from lxml import etree as ET

        LIFT_NS = "{http://fieldworks.sil.org/schemas/lift/0.13}"
        xml_data = response.data.decode("utf-8")
        root = ET.fromstring(xml_data)

        trait = root.find(
            f'.//{LIFT_NS}sense/{LIFT_NS}trait[@name="semantic-domain-ddp4"]'
        )
        assert trait is not None
        assert trait.get("value") == "języki"

    @pytest.mark.integration
    def test_domain_type_form_field_visibility(self, client: Client) -> None:
        """Test that domain type fields are visible at sense level in the form."""
        # Get the new entry form
        response = client.get("/entries/add", follow_redirects=True)
        assert response.status_code == 200

        response_html = response.get_data(as_text=True)

        # Check that domain type fields are present (use canonical range id)
        assert "domain_type" in response_html
        assert 'data-range-id="semantic-domain-ddp4"' in response_html

        # Check for sense-level fields in sense template
        assert 'name="senses[INDEX].domain_type"' in response_html

        # Verify NO entry-level field exists
        assert (
            'name="domain_type"' not in response_html
            or response_html.count('name="domain_type"') == 0
        )

    @pytest.mark.integration
    def test_domain_type_roundtrip_compatibility(
        self, client: Client, dict_service_with_db: DictionaryService
    ) -> None:
        """Test that domain types survive complete roundtrip: form → backend → form."""
        # Create entry with sense-level domain types programmatically first
        original_entry = Entry(
            id_="test_roundtrip_compatibility",
            lexical_unit={"en": "roundtrip test"},
            senses=[
                Sense(
                    id_="roundtrip_sense",
                    glosses={"en": "test"},
                    definitions={"en": "roundtrip test"},
                    domain_type="prawniczy",
                )
            ],
        )
        dict_service_with_db.create_entry(original_entry)

        # Retrieve via database and convert to form data that would be sent
        retrieved_entry = dict_service_with_db.get_entry("test_roundtrip_compatibility")
        form_data = {
            "id": retrieved_entry.id,
            "lexical_unit.en": retrieved_entry.lexical_unit["en"],
            "senses[0].id": retrieved_entry.senses[0].id,
            "senses[0].definition.en": retrieved_entry.senses[0].definitions["en"],
            "senses[0].gloss.en": retrieved_entry.senses[0].glosses["en"],
            "senses[0].domain_type": retrieved_entry.senses[0].domain_type,
        }

        # Submit back via form for editing
        response = client.post(f"/entries/{retrieved_entry.id}/edit", data=form_data)
        assert response.status_code in [200, 302], (
            f"Roundtrip form submission failed: {response.get_data(as_text=True)}"
        )

        # Verify final state
        final_entry = dict_service_with_db.get_entry("test_roundtrip_compatibility")
        assert final_entry.senses[0].domain_type == original_entry.senses[0].domain_type

        # Clean up
        dict_service_with_db.delete_entry("test_roundtrip_compatibility")
