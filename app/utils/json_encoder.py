"""
Custom JSON encoder for Flask to handle our model classes.
"""

import json
from flask.json.provider import JSONEncoder
from app.models.base import BaseModel

class ModelJSONEncoder(JSONEncoder):
    """
    Custom JSON encoder that knows how to encode model classes.
    """
    def default(self, obj):
        if isinstance(obj, BaseModel):
            return obj.to_dict()
        return super().default(obj)
