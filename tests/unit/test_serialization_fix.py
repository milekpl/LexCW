
import pytest
from app.models.sense import Sense
from app.models.example import Example
from flask import Flask, jsonify

def test_sense_serialization_with_examples():
    """Test that Sense with Example objects can be serialized to JSON."""
    app = Flask(__name__)
    
    # Create an example and a sense
    example = Example(id_="ex1", form_text="test example")
    sense = Sense(id_="sense1", examples=[example])
    
    # Get dict representation
    sense_dict = sense.to_dict()
    
    # Check that examples are converted to dicts
    assert isinstance(sense_dict['examples'], list)
    assert len(sense_dict['examples']) == 1
    assert isinstance(sense_dict['examples'][0], dict)
    assert sense_dict['examples'][0]['id'] == 'ex1'
    assert sense_dict['examples'][0]['form_text'] == 'test example'
    
    # Check JSON serialization
    with app.app_context():
        # This should not raise TypeError
        json_response = jsonify(sense_dict)
        assert json_response.status_code == 200
