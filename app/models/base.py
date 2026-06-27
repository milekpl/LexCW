"""
Base model class for all data models.

Extends SerializableMixin for standardized serialization/deserialization
while preserving backward compatibility with the original simple __dict__ dump.
"""

from typing import Dict, Any, Optional, Set
import json
import uuid

from app.models.serializable import SerializableMixin


class BaseModel(SerializableMixin):
    """Base model class with common functionality."""
    
    _exclude_fields: Set[str] = set()
    
    def __init__(self, id_: Optional[str] = None, **kwargs):
        """
        Initialize a base model.
        
        Args:
            id_: Unique identifier for the model. If not provided, a UUID will be generated.
            **kwargs: Additional attributes to set on the model.
        """
        self.id = id_ if id_ is not None else str(uuid.uuid4())
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def to_dict(self, exclude: Optional[Set[str]] = None, include: Optional[Set[str]] = None, **kwargs) -> Dict[str, Any]:
        """
        Convert the model to a dictionary.
        
        Delegates to SerializableMixin for datetime isoformat conversion,
        None-value filtering, and recursive serialization of nested objects.
        
        Args:
            exclude: Additional fields to exclude from serialization
            include: If specified, only include these fields
            **kwargs: Additional arguments (for compatibility with SerializableMixin)
            
        Returns:
            Dictionary representation of the model.
        """
        return SerializableMixin.to_dict(self, exclude=exclude, include=include, **kwargs)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseModel':
        """
        Create a model instance from a dictionary.
        
        Args:
            data: Dictionary containing model data.
            
        Returns:
            Model instance.
        """
        return cls(**data)
    
    def to_json(self) -> str:
        """
        Convert the model to a JSON string.
        
        Returns:
            JSON string representation of the model.
        """
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'BaseModel':
        """
        Create a model instance from a JSON string.
        
        Args:
            json_str: JSON string containing model data.
            
        Returns:
            Model instance.
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def validate(self) -> bool:
        """
        Validate the model.
        
        Returns:
            True if the model is valid, False otherwise.
        
        Raises:
            ValidationError: If the model is invalid.
        """
        return True
    
    def __repr__(self) -> str:
        """
        Get a string representation of the model.
        
        Returns:
            String representation of the model.
        """
        return f"{self.__class__.__name__}(id={self.id})"
