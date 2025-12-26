
import pytest
from flask import Flask
from bs4 import BeautifulSoup

@pytest.mark.integration
def test_entry_form_layout_structure(client):
    """
    Test that the entry form has the correct 2-column layout.
    The basic info (col-md-4) and senses (col-md-8) should be siblings in a row.
    """
    response = client.get('/entries/add')
    assert response.status_code == 200
    
    soup = BeautifulSoup(response.data, 'html.parser')

    # Find the main row
    # We expect a row that contains both columns
    # Since there might be multiple rows, we look for the one containing basic-info-section

    basic_info = soup.find(class_='basic-info-section')
    assert basic_info is not None, "Basic info section not found"

    # Find the col-md-4 container of basic info
    col_4 = basic_info.find_parent(class_='col-md-4')
    assert col_4 is not None, "Basic info section should be inside col-md-4"

    senses_section = soup.find(class_='senses-section')
    assert senses_section is not None, "Senses section not found"

    # Find the col-md-8 container of senses
    col_8 = senses_section.find_parent(class_='col-md-8')
    assert col_8 is not None, "Senses section should be inside col-md-8"

    # Check if col-8 is inside col-4 (which would be the bug)
    if col_8 in col_4.descendants:
        pytest.fail("Layout Error: col-md-8 (senses) is nested inside col-md-4 (basic info). They should be siblings.")

    # Check if they are siblings
    assert col_4.parent == col_8.parent, "col-md-4 and col-md-8 should be in the same row (siblings)"
