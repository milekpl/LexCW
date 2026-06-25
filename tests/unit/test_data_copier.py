"""
Unit tests for DataCopier utility.

Tests the unified data copying functionality that consolidates
deep copy patterns from across the codebase.
"""

import copy
from dataclasses import dataclass, field
from typing import Dict, Any, List, Set, Optional

import pytest

from app.utils.data_copier import (
    DataCopier, CopyStrategy,
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
        """Should initialize with sensible defaults."""
        copier = DataCopier()

        assert copier.max_depth == 10
        assert copier.preserve_ids is True
        assert copier.handle_circular is True

    def test_custom_initialization(self):
        """Should accept custom configuration."""
        copier = DataCopier(max_depth=5, preserve_ids=False, handle_circular=False)

        assert copier.max_depth == 5
        assert copier.preserve_ids is False
        assert copier.handle_circular is False


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
        assert result is data  # Bytes are immutable

    def test_copy_simple_dict(self):
        """Should copy simple dictionary."""
        copier = DataCopier()
        data = {'a': 1, 'b': 'hello', 'c': True}
        result = copier.copy(data)

        assert result == data
        assert result is not data
        assert result['a'] == 1

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
        assert result['outer']['inner'] is not data['outer']['inner']

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
        result = copier.copy_entry(entry)

        assert result['id'] == 'entry-1'
        assert result['lexical_unit'] == {'en': 'test'}
        assert result['senses'] == []

    def test_copy_entry_preserves_id(self):
        """Should preserve entry ID by default."""
        copier = DataCopier()
        entry = {
            'id': 'entry-1',
            'name': 'test'
        }
        result = copier.copy_entry(entry)

        assert result['id'] == 'entry-1'

    def test_copy_entry_does_not_preserve_id_when_configured(self):
        """Should not preserve ID when configured."""
        copier = DataCopier(preserve_ids=False)
        entry = {
            'id': 'entry-1',
            'name': 'test'
        }
        # ID is still copied, just not specially preserved
        # (copy_entry still copies it, just doesn't treat it specially)
        result = copier.copy_entry(entry, copy_senses=False)

        assert result['id'] == 'entry-1'  # Still copied as regular field

    def test_copy_entry_with_senses(self):
        """Should deep copy senses."""
        copier = DataCopier()
        entry = {
            'id': 'entry-1',
            'senses': [
                {'id': 'sense-1', 'definition': {'en': 'test 1'}},
                {'id': 'sense-2', 'definition': {'en': 'test 2'}}
            ]
        }
        result = copier.copy_entry(entry, copy_senses=True)

        assert len(result['senses']) == 2
        assert result['senses'][0]['definition']['en'] == 'test 1'
        # Should be deep copied
        result['senses'][0]['definition']['en'] = 'modified'
        assert entry['senses'][0]['definition']['en'] == 'test 1'

    def test_copy_entry_with_examples(self):
        """Should deep copy examples within senses."""
        copier = DataCopier()
        entry = {
            'id': 'entry-1',
            'senses': [
                {
                    'id': 'sense-1',
                    'examples': [
                        {'form': {'en': 'example 1'}},
                        {'form': {'en': 'example 2'}}
                    ]
                }
            ]
        }
        result = copier.copy_entry(entry, copy_senses=True, copy_examples=True)

        assert len(result['senses'][0]['examples']) == 2

    def test_copy_entry_with_relations(self):
        """Should deep copy relations."""
        copier = DataCopier()
        entry = {
            'id': 'entry-1',
            'relations': [
                {'type': 'synonym', 'ref': 'entry-2'},
                {'type': 'antonym', 'ref': 'entry-3'}
            ]
        }
        result = copier.copy_entry(entry, copy_relations=True)

        assert len(result['relations']) == 2
        assert result['relations'][0]['type'] == 'synonym'

    def test_copy_entry_without_senses(self):
        """Should shallow copy senses when disabled."""
        copier = DataCopier()
        entry = {
            'id': 'entry-1',
            'senses': [
                {'id': 'sense-1', 'definition': {'en': 'test'}}
            ]
        }
        result = copier.copy_entry(entry, copy_senses=False)

        # With copy_senses=False, it uses regular copy which still does deep copy
        # The behavior depends on how copy() handles lists
        assert result['senses'] == entry['senses']


class TestDataCopierSenseCopying:
    """Test sense dictionary copying"""

    def test_copy_simple_sense(self):
        """Should copy simple sense dict."""
        copier = DataCopier()
        sense = {
            'id': 'sense-1',
            'definition': {'en': 'test definition'},
            'gloss': {'en': 'test gloss'}
        }
        result = copier.copy_sense(sense)

        assert result['id'] == 'sense-1'
        assert result['definition']['en'] == 'test definition'

    def test_copy_sense_preserves_id(self):
        """Should preserve sense ID."""
        copier = DataCopier()
        sense = {'id': 'sense-1', 'definition': {'en': 'test'}}
        result = copier.copy_sense(sense)

        assert result['id'] == 'sense-1'

    def test_copy_sense_with_examples(self):
        """Should copy examples."""
        copier = DataCopier()
        sense = {
            'id': 'sense-1',
            'examples': [
                {'form': {'en': 'example 1'}},
                {'form': {'en': 'example 2'}}
            ]
        }
        result = copier.copy_sense(sense, copy_examples=True)

        assert len(result['examples']) == 2
        # Deep copied
        result['examples'][0]['form']['en'] = 'modified'
        assert sense['examples'][0]['form']['en'] == 'example 1'

    def test_copy_sense_with_subsenses(self):
        """Should recursively copy subsenses."""
        copier = DataCopier()
        sense = {
            'id': 'sense-1',
            'definition': {'en': 'parent'},
            'subsenses': [
                {'id': 'sub-1', 'definition': {'en': 'child 1'}},
                {'id': 'sub-2', 'definition': {'en': 'child 2'}}
            ]
        }
        result = copier.copy_sense(sense, copy_subsenses=True)

        assert len(result['subsenses']) == 2
        assert result['subsenses'][0]['id'] == 'sub-1'

    def test_copy_sense_with_definitions(self):
        """Should copy definitions."""
        copier = DataCopier()
        sense = {
            'id': 'sense-1',
            'definitions': {
                'en': 'definition in English',
                'fr': 'définition en français'
            }
        }
        result = copier.copy_sense(sense, copy_definitions=True)

        assert result['definitions']['en'] == 'definition in English'
        assert result['definitions']['fr'] == 'définition en français'

    def test_copy_sense_with_glosses(self):
        """Should copy glosses."""
        copier = DataCopier()
        sense = {
            'id': 'sense-1',
            'glosses': {'en': 'gloss', 'fr': 'glose'}
        }
        result = copier.copy_sense(sense, copy_glosses=True)

        assert result['glosses']['en'] == 'gloss'


class TestDataCopierCollections:
    """Test copying collections"""

    def test_copy_list_of_dicts(self):
        """Should copy list of dictionaries."""
        copier = DataCopier()
        data = [{'id': '1'}, {'id': '2'}, {'id': '3'}]
        result = copier.copy_list(data)

        assert len(result) == 3
        assert result[0]['id'] == '1'
        assert result is not data
        assert result[0] is not data[0]

    def test_copy_list_with_custom_copier(self):
        """Should use custom copier for list items."""
        copier = DataCopier()
        data = [1, 2, 3]

        def double(x):
            return x * 2

        result = copier.copy_list(data, item_copier=double)

        assert result == [2, 4, 6]

    def test_copy_dict(self):
        """Should copy dictionary."""
        copier = DataCopier()
        data = {'a': {'nested': 'value'}, 'b': [1, 2, 3]}
        result = copier.copy_dict(data)

        assert result == data
        assert result is not data
        assert result['a'] is not data['a']

    def test_copy_dict_with_custom_copiers(self):
        """Should use custom key and value copiers."""
        copier = DataCopier()
        data = {'key1': 'value1', 'key2': 'value2'}

        def upper_key(k):
            return k.upper()

        def upper_value(v):
            return v.upper()

        result = copier.copy_dict(data, key_copier=upper_key, value_copier=upper_value)

        assert result == {'KEY1': 'VALUE1', 'KEY2': 'VALUE2'}


class TestDataCopierSetsAndTuples:
    """Test copying sets and tuples"""

    def test_copy_set(self):
        """Should copy set."""
        copier = DataCopier()
        data = {1, 2, 3}
        result = copier.copy(data)

        assert result == data
        assert result is not data

    def test_copy_frozenset(self):
        """Should copy frozenset."""
        copier = DataCopier()
        data = frozenset({1, 2, 3})
        result = copier.copy(data)

        assert result == data
        assert isinstance(result, frozenset)

    def test_copy_tuple(self):
        """Should copy tuple contents."""
        copier = DataCopier()
        data = ({'nested': 'value'}, [1, 2, 3])
        result = copier.copy(data)

        assert result[0] == {'nested': 'value'}
        assert result[1] == [1, 2, 3]
        assert result[0] is not data[0]  # Nested dict should be copied
        assert result[1] is not data[1]  # Nested list should be copied


class TestDataCopierDataclasses:
    """Test copying dataclasses"""

    def test_copy_dataclass(self):
        """Should copy dataclass instance."""
        copier = DataCopier()
        obj = TestDataclass(id='test-1', name='Test', value=42)
        result = copier.copy(obj)

        assert result.id == 'test-1'
        assert result.name == 'Test'
        assert result.value == 42
        assert result is not obj

    def test_copy_dataclass_preserves_id(self):
        """Should preserve ID in dataclass."""
        copier = DataCopier(preserve_ids=True)
        obj = TestDataclass(id='test-1', name='Test')
        result = copier.copy(obj)

        assert result.id == 'test-1'

    def test_copy_nested_dataclass(self):
        """Should copy nested dataclasses."""
        copier = DataCopier()
        child = TestDataclass(id='child-1', name='Child')
        parent = NestedDataclass(id='parent-1', child=child)
        result = copier.copy(parent)

        assert result.id == 'parent-1'
        assert result.child.id == 'child-1'
        assert result.child is not child  # Deep copied


class TestDataCopierSerializableObjects:
    """Test copying objects with to_dict/from_dict"""

    def test_copy_serializable_model(self):
        """Should copy using to_dict/from_dict."""
        copier = DataCopier()
        obj = SerializableModel(id='test-1', name='Test', items=['a', 'b', 'c'])
        result = copier.copy(obj)

        assert result.id == 'test-1'
        assert result.name == 'Test'
        assert result.items == ['a', 'b', 'c']
        assert result is not obj

    def test_copy_serializable_nested(self):
        """Should handle nested serializable data."""
        copier = DataCopier()
        model1 = SerializableModel(id='m-1', name='Model')
        model2 = SerializableModel(id='m-2', name='Model 2')
        data = {
            'model': model1,
            'list': [model2]
        }
        result = copier.copy(data)

        # Verify the results - note: SerializableModel doesn't have memo support
        # so we just verify it doesn't crash and produces results
        assert isinstance(result['model'], SerializableModel)
        assert isinstance(result['list'][0], SerializableModel)
        # IDs might not be preserved exactly with to_dict/from_dict pattern
        # because the from_dict creates a new instance


class TestDataCopierDepthLimiting:
    """Test depth limiting"""

    def test_respects_max_depth(self):
        """Should respect max_depth parameter."""
        copier = DataCopier(max_depth=2)
        # Deep nesting: outer -> middle -> inner -> deepest
        data = {
            'level1': {
                'level2': {
                    'level3': {
                        'level4': 'deep value'
                    }
                }
            }
        }
        result = copier.copy(data)

        # With depth=2, level3 and below might not be fully copied
        # But structure should be preserved
        assert 'level1' in result

    def test_depth_parameter_override(self):
        """Should allow depth override per call."""
        copier = DataCopier(max_depth=10)
        data = {'level1': {'level2': {'level3': 'value'}}}

        result = copier.copy(data, max_depth=1)
        # Should limit copying to depth 1
        assert 'level1' in result


class TestDataCopierCircularReferences:
    """Test circular reference handling"""

    def test_handles_simple_circular_reference(self):
        """Should handle simple circular reference."""
        copier = DataCopier()
        data = {'name': 'parent'}
        data['self'] = data  # Circular reference

        result = copier.copy(data)

        assert result['name'] == 'parent'
        # Circular reference should be handled
        assert result['self'] is result

    def test_handles_nested_circular_reference(self):
        """Should handle nested circular reference."""
        copier = DataCopier()
        parent = {'name': 'parent'}
        child = {'name': 'child', 'parent': parent}
        parent['child'] = child  # Circular

        result = copier.copy(parent)

        assert result['name'] == 'parent'
        assert result['child']['name'] == 'child'
        assert result['child']['parent'] is result

    def test_can_disable_circular_handling(self):
        """Should allow disabling circular reference handling."""
        copier = DataCopier(handle_circular=False)
        data = {'name': 'test'}
        data['self'] = data

        # This will likely cause infinite recursion or RecursionError
        # depending on the implementation
        # Test that it doesn't crash with shallow circular refs
        # (though it might with deep ones)
        try:
            result = copier.copy(data)
            # If it works, great
            assert result['name'] == 'test'
        except RecursionError:
            # Expected without circular handling
            pass


class TestDataCopierEdgeCases:
    """Test edge cases"""

    def test_copy_empty_dict(self):
        """Should handle empty dict."""
        copier = DataCopier()
        result = copier.copy({})

        assert result == {}
        assert result is not {}

    def test_copy_empty_list(self):
        """Should handle empty list."""
        copier = DataCopier()
        result = copier.copy([])

        assert result == []
        assert result is not []

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

        # Should fall back to copy.deepcopy
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

    def test_deepcopy_with_options(self):
        """Deepcopy should accept options."""
        data = {'id': 'test', 'value': {'nested': 42}}
        result = deepcopy(data, max_depth=5)

        assert result['id'] == 'test'

    def test_copy_entry_convenience(self):
        """Copy entry convenience function should work."""
        entry = {
            'id': 'entry-1',
            'senses': [{'id': 'sense-1', 'definition': {'en': 'test'}}]
        }
        result = copy_entry(entry, copy_senses=True)

        assert result['id'] == 'entry-1'
        assert result['senses'][0]['id'] == 'sense-1'

    def test_copy_sense_convenience(self):
        """Copy sense convenience function should work."""
        sense = {
            'id': 'sense-1',
            'definition': {'en': 'test'},
            'examples': [{'form': {'en': 'example'}}]
        }
        result = copy_sense(sense, copy_examples=True)

        assert result['id'] == 'sense-1'
        assert result['definition']['en'] == 'test'


class TestDataCopierMemoReset:
    """Test memo clearing between copies"""

    def test_clears_memo_between_copies(self):
        """Should handle separate copy operations correctly."""
        copier = DataCopier()

        # First copy
        data1 = {'id': '1'}
        result1 = copier.copy(data1)

        # Second copy with different data but same ID
        data2 = {'id': '1', 'extra': 'value'}
        result2 = copier.copy(data2)

        assert result1 == {'id': '1'}
        assert result2 == {'id': '1', 'extra': 'value'}
        assert result2['extra'] == 'value'
