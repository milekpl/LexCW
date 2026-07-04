"""
Unit tests for DataCopier utility.

Tests the thin wrapper around ``copy.deepcopy``.
"""

import copy
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

import pytest

from app.utils.data_copier import (
    DataCopier,
    get_copier, deepcopy, copy_entry, copy_sense
)


# Test data classes
@dataclass
class TestDataclass:
    id: str
    name: str
    value: int = 0


@dataclass
class NestedDataclass:
    id: str
    child: Optional[TestDataclass] = None


class SimpleModel:
    """Simple class without special copy methods."""
    def __init__(self, id: str, name: str):
        self.id = id
        self.name = name


class SerializableModel:
    """Class with to_dict/from_dict methods."""
    def __init__(self, id: str, name: str, items: List[str] = None):
        self.id = id
        self.name = name
        self.items = items or []

    def to_dict(self) -> Dict[str, Any]:
        return {'id': self.id, 'name': self.name, 'items': list(self.items)}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SerializableModel':
        return cls(
            id=data['id'],
            name=data['name'],
            items=data.get('items', [])
        )


class TestDataCopierInitialization:
    """Test DataCopier initialization"""

    def test_default_initialization(self):
        """Should initialize without error."""
        copier = DataCopier()
        assert isinstance(copier, DataCopier)


class TestDataCopierBasicCopying:
    """Test basic copying functionality"""

    def test_copy_none(self):
        """Should handle None."""
        copier = DataCopier()
        result = copier.copy(None)
        assert result is None

    def test_copy_primitives(self):
        """Should return primitives as-is."""
        copier = DataCopier()
        assert copier.copy(42) == 42
        assert copier.copy(3.14) == 3.14
        assert copier.copy("hello") == "hello"
        assert copier.copy(True) is True
        assert copier.copy(False) is False

    def test_copy_bytes(self):
        """Should handle bytes."""
        copier = DataCopier()
        data = b"hello"
        result = copier.copy(data)
        assert result == data

    def test_copy_simple_dict(self):
        """Should copy simple dictionary."""
        copier = DataCopier()
        data = {'a': 1, 'b': 'hello', 'c': True}
        result = copier.copy(data)
        assert result == data
        assert result is not data

    def test_copy_simple_list(self):
        """Should copy simple list."""
        copier = DataCopier()
        data = [1, 2, 3]
        result = copier.copy(data)
        assert result == data
        assert result is not data

    def test_copy_nested_dict(self):
        """Should copy nested dictionary."""
        copier = DataCopier()
        data = {'outer': {'inner': {'value': 42}}}
        result = copier.copy(data)
        assert result == data
        assert result is not data
        assert result['outer'] is not data['outer']

    def test_copy_nested_list(self):
        """Should copy nested list."""
        copier = DataCopier()
        data = [[1, 2], [3, 4]]
        result = copier.copy(data)
        assert result == data
        assert result is not data
        assert result[0] is not data[0]

    def test_copy_mixed_nested(self):
        """Should copy mixed nested structures."""
        copier = DataCopier()
        data = {
            'items': [1, 2, 3],
            'nested': {'list': [4, 5, 6]},
            'simple': 'value'
        }
        result = copier.copy(data)
        assert result == data
        assert result is not data
        assert result['items'] is not data['items']
        assert result['nested'] is not data['nested']


class TestDataCopierEntryCopying:
    """Test entry dictionary copying"""

    def test_copy_simple_entry(self):
        """Should copy simple entry dict."""
        copier = DataCopier()
        entry = {
            'id': 'entry-1',
            'lexical_unit': {'en': 'test'},
            'senses': []
        }
        result = copier.copy(entry)
        assert result['id'] == 'entry-1'
        assert result['lexical_unit'] == {'en': 'test'}
        assert result['senses'] == []

    def test_copy_entry_deep(self):
        """Should deep-copy nested fields."""
        copier = DataCopier()
        entry = {
            'id': 'entry-1',
            'senses': [
                {'id': 'sense-1', 'definition': {'en': 'test 1'}},
                {'id': 'sense-2', 'definition': {'en': 'test 2'}}
            ]
        }
        result = copier.copy(entry)
        assert len(result['senses']) == 2
        # Should be deep copied
        result['senses'][0]['definition']['en'] = 'modified'
        assert entry['senses'][0]['definition']['en'] == 'test 1'


class TestDataCopierSetsAndTuples:
    """Test copying sets and tuples"""

    def test_copy_set(self):
        """Should copy set."""
        copier = DataCopier()
        data = {1, 2, 3}
        result = copier.copy(data)
        assert result == data
        assert result is not data

    def test_copy_tuple(self):
        """Should copy tuple contents."""
        copier = DataCopier()
        data = ({'nested': 'value'}, [1, 2, 3])
        result = copier.copy(data)
        assert result[0] == {'nested': 'value'}
        assert result[1] == [1, 2, 3]
        assert result[0] is not data[0]
        assert result[1] is not data[1]


class TestDataCopierDataclasses:
    """Test copying dataclasses"""

    def test_copy_dataclass(self):
        """Should copy dataclass instance via copy.deepcopy."""
        copier = DataCopier()
        obj = TestDataclass(id='test-1', name='Test', value=42)
        result = copier.copy(obj)
        assert result.id == 'test-1'
        assert result.name == 'Test'
        assert result.value == 42
        assert result is not obj

    def test_copy_nested_dataclass(self):
        """Should copy nested dataclasses."""
        copier = DataCopier()
        child = TestDataclass(id='child-1', name='Child')
        parent = NestedDataclass(id='parent-1', child=child)
        result = copier.copy(parent)
        assert result.id == 'parent-1'
        assert result.child.id == 'child-1'
        assert result.child is not child


class TestDataCopierSerializableObjects:
    """Test copying objects with to_dict/from_dict"""

    def test_copy_serializable_model(self):
        """Should copy using to_dict/from_dict (via deepcopy fallback)."""
        copier = DataCopier()
        obj = SerializableModel(id='test-1', name='Test', items=['a', 'b', 'c'])
        result = copier.copy(obj)
        assert result.id == 'test-1'
        assert result.name == 'Test'
        assert result.items == ['a', 'b', 'c']
        assert result is not obj


class TestDataCopierCircularReferences:
    """Test circular reference handling"""

    def test_handles_simple_circular_reference(self):
        """Should handle simple circular reference."""
        copier = DataCopier()
        data = {'name': 'parent'}
        data['self'] = data

        result = copier.copy(data)
        assert result['name'] == 'parent'
        assert result['self'] is result


class TestDataCopierEdgeCases:
    """Test edge cases"""

    def test_copy_empty_dict(self):
        """Should handle empty dict."""
        copier = DataCopier()
        result = copier.copy({})
        assert result == {}

    def test_copy_empty_list(self):
        """Should handle empty list."""
        copier = DataCopier()
        result = copier.copy([])
        assert result == []

    def test_copy_empty_set(self):
        """Should handle empty set."""
        copier = DataCopier()
        result = copier.copy(set())
        assert result == set()

    def test_copy_empty_tuple(self):
        """Should handle empty tuple."""
        copier = DataCopier()
        result = copier.copy(())
        assert result == ()

    def test_copy_list_with_none(self):
        """Should handle None in lists."""
        copier = DataCopier()
        data = [1, None, 'test', None]
        result = copier.copy(data)
        assert result == [1, None, 'test', None]

    def test_copy_dict_with_none_values(self):
        """Should handle None values in dicts."""
        copier = DataCopier()
        data = {'a': None, 'b': 'value', 'c': None}
        result = copier.copy(data)
        assert result['a'] is None
        assert result['b'] == 'value'
        assert result['c'] is None

    def test_copy_object_without_copy_method(self):
        """Should handle objects without copy methods."""
        copier = DataCopier()
        obj = SimpleModel(id='test', name='Test')
        result = copier.copy(obj)
        assert result.id == 'test'
        assert result.name == 'Test'


class TestConvenienceFunctions:
    """Test module-level convenience functions"""

    def test_get_copier_singleton(self):
        """Should return same copier instance."""
        copier1 = get_copier()
        copier2 = get_copier()
        assert copier1 is copier2

    def test_deepcopy_convenience(self):
        """Deepcopy convenience function should work."""
        data = {'nested': {'value': 42}}
        result = deepcopy(data)
        assert result == data
        assert result is not data
        assert result['nested'] is not data['nested']

    def test_copy_entry_convenience(self):
        """Copy entry convenience function should work."""
        entry = {
            'id': 'entry-1',
            'senses': [{'id': 'sense-1', 'definition': {'en': 'test'}}]
        }
        result = copy_entry(entry)
        assert result['id'] == 'entry-1'
        assert result['senses'][0]['id'] == 'sense-1'

    def test_copy_sense_convenience(self):
        """Copy sense convenience function should work."""
        sense = {
            'id': 'sense-1',
            'definition': {'en': 'test'},
            'examples': [{'form': {'en': 'example'}}]
        }
        result = copy_sense(sense)
        assert result['id'] == 'sense-1'
        assert result['definition']['en'] == 'test'
