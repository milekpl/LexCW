"""
Unit tests for SerializableMixin.

Tests the serialization mixin that provides standardized to_dict/from_dict
functionality for models, eliminating the 50+ duplicate implementations.
"""

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import List, Dict, Optional, Set

import pytest

from app.models.serializable import (
    SerializableMixin,
    serialize_value,
    _deserialize_value,
    ModelJSONEncoder,
    dataclass_serializable,
    is_serializable_type,
    serialize_list,
    deserialize_list
)


# Test data classes and regular classes
class TestEnum(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class SimpleModel(SerializableMixin):
    """Simple regular class model."""

    def __init__(self, name: str, value: int = 0):
        self.name = name
        self.value = value


class NestedModel(SerializableMixin):
    """Model with nested serializable."""

    def __init__(self, id: str, child: Optional[SimpleModel] = None):
        self.id = id
        self.child = child


class ModelWithSpecialTypes(SerializableMixin):
    """Model with special types requiring serialization."""

    def __init__(
        self,
        uuid_field: uuid.UUID,
        decimal_field: Decimal,
        datetime_field: datetime,
        date_field: date,
        enum_field: TestEnum
    ):
        self.uuid_field = uuid_field
        self.decimal_field = decimal_field
        self.datetime_field = datetime_field
        self.date_field = date_field
        self.enum_field = enum_field


class ModelWithCollections(SerializableMixin):
    """Model with list and dict collections."""

    def __init__(
        self,
        items: List[str],
        mapping: Dict[str, int],
        children: Optional[List[SimpleModel]] = None
    ):
        self.items = items
        self.mapping = mapping
        self.children = children or []


class ModelWithExcludedFields(SerializableMixin):
    """Model with fields to exclude."""

    _exclude_fields = {'password', '_internal'}

    def __init__(self, username: str, password: str, public_info: str):
        self.username = username
        self.password = password
        self.public_info = public_info
        self._internal = "secret"


@dataclass
class DataclassModel(SerializableMixin):
    """Dataclass model."""
    name: str
    value: int = 0


@dataclass
class DataclassWithNested(SerializableMixin):
    """Dataclass with nested serializable."""
    id: str
    child: Optional[DataclassModel] = None


# =====================================================================
# Tests for serialize_value helper (replaces old _serialize_value)
# =====================================================================

class TestSerializeValue:
    """Test serialize_value helper function."""

    def test_serialize_none(self):
        """None should serialize to None."""
        assert serialize_value(None) is None

    def test_serialize_primitives(self):
        """Primitives should serialize as-is."""
        assert serialize_value("string") == "string"
        assert serialize_value(123) == 123
        assert serialize_value(3.14) == 3.14
        assert serialize_value(True) is True
        assert serialize_value(False) is False

    def test_serialize_uuid(self):
        """UUID should serialize to string."""
        uid = uuid.uuid4()
        assert serialize_value(uid) == str(uid)

    def test_serialize_decimal(self):
        """Decimal should serialize to string."""
        dec = Decimal("3.14159")
        assert serialize_value(dec) == "3.14159"

    def test_serialize_datetime(self):
        """Datetime should serialize to ISO format."""
        dt = datetime(2023, 1, 15, 10, 30, 45)
        assert serialize_value(dt) == "2023-01-15T10:30:45"

    def test_serialize_date(self):
        """Date should serialize to string."""
        d = date(2023, 1, 15)
        assert serialize_value(d) == "2023-01-15"

    def test_serialize_enum(self):
        """Enum should serialize to value."""
        assert serialize_value(TestEnum.ACTIVE) == "active"

    def test_serialize_list(self):
        """List should serialize recursively."""
        data = [1, "two", 3.0, uuid.uuid4()]
        result = serialize_value(data)
        assert result[0] == 1
        assert result[1] == "two"
        assert result[2] == 3.0
        assert isinstance(result[3], str)  # UUID converted to string

    def test_serialize_dict(self):
        """Dict should serialize recursively."""
        data = {"name": "test", "id": uuid.uuid4()}
        result = serialize_value(data)
        assert result["name"] == "test"
        assert isinstance(result["id"], str)

    def test_serialize_set(self):
        """Set should serialize to list."""
        data = {3, 1, 2}
        result = serialize_value(data)
        assert sorted(result) == [1, 2, 3]

    def test_serialize_serializable_object(self):
        """Serializable object should call to_dict."""
        model = SimpleModel("test", 42)
        result = serialize_value(model)
        assert result == {"name": "test", "value": 42}

    def test_serialize_nested_list(self):
        """Nested lists should serialize recursively."""
        model1 = SimpleModel("one", 1)
        model2 = SimpleModel("two", 2)
        data = [model1, model2]
        result = serialize_value(data)
        assert result == [{"name": "one", "value": 1}, {"name": "two", "value": 2}]


# =====================================================================
# Tests for ModelJSONEncoder
# =====================================================================

class TestModelJSONEncoder:
    """Test ModelJSONEncoder."""

    def test_encoder_datetime(self):
        """Should encode datetime."""
        import json
        dt = datetime(2023, 1, 15, 10, 30, 45)
        result = json.dumps({"dt": dt}, cls=ModelJSONEncoder)
        assert "2023-01-15T10:30:45" in result

    def test_encoder_uuid(self):
        """Should encode UUID."""
        import json
        uid = uuid.uuid4()
        result = json.dumps({"uid": uid}, cls=ModelJSONEncoder)
        assert str(uid) in result

    def test_encoder_enum(self):
        """Should encode Enum."""
        import json
        result = json.dumps({"e": TestEnum.ACTIVE}, cls=ModelJSONEncoder)
        assert "active" in result


# =====================================================================
# Tests for _deserialize_value helper
# =====================================================================

class TestDeserializeValue:
    """Test _deserialize_value helper function."""

    def test_deserialize_none(self):
        """None should deserialize to None."""
        assert _deserialize_value(None) is None

    def test_deserialize_primitives(self):
        """Primitives should deserialize as-is."""
        assert _deserialize_value("string") == "string"
        assert _deserialize_value(123) == 123
        assert _deserialize_value(3.14) == 3.14
        assert _deserialize_value(True) is True

    def test_deserialize_datetime(self):
        """String should deserialize to datetime."""
        result = _deserialize_value("2023-01-15T10:30:45", datetime)
        assert isinstance(result, datetime)
        assert result.year == 2023

    def test_deserialize_date(self):
        """String should deserialize to date."""
        result = _deserialize_value("2023-01-15", date)
        assert isinstance(result, date)
        assert result.year == 2023

    def test_deserialize_uuid(self):
        """String should deserialize to UUID."""
        uid_str = "550e8400-e29b-41d4-a716-446655440000"
        result = _deserialize_value(uid_str, uuid.UUID)
        assert isinstance(result, uuid.UUID)
        assert str(result) == uid_str

    def test_deserialize_decimal(self):
        """Number should deserialize to Decimal."""
        result = _deserialize_value("3.14159", Decimal)
        assert isinstance(result, Decimal)
        assert result == Decimal("3.14159")

    def test_deserialize_list(self):
        """List should deserialize items."""
        data = [1, "two", 3.0]
        result = _deserialize_value(data)
        assert result == [1, "two", 3.0]

    def test_deserialize_dict(self):
        """Dict should deserialize values."""
        data = {"a": 1, "b": "two"}
        result = _deserialize_value(data)
        assert result == {"a": 1, "b": "two"}


# =====================================================================
# Tests for SerializableMixin with regular classes
# =====================================================================

class TestSerializableMixinRegularClasses:
    """Test SerializableMixin with regular classes."""

    def test_to_dict_basic(self):
        """Should serialize basic attributes."""
        model = SimpleModel("test", 42)
        result = model.to_dict()
        assert result == {"name": "test", "value": 42}

    def test_to_dict_excludes_private(self):
        """Should exclude private attributes."""
        model = SimpleModel("test", 42)
        model._private = "should not appear"
        result = model.to_dict()
        assert "_private" not in result
        assert "name" in result

    def test_to_dict_with_exclude(self):
        """Should exclude specified fields."""
        model = SimpleModel("test", 42)
        result = model.to_dict(exclude={"value"})
        assert result == {"name": "test"}
        assert "value" not in result

    def test_to_dict_with_include(self):
        """Should only include specified fields."""
        model = SimpleModel("test", 42)
        model.extra = "extra field"
        result = model.to_dict(include={"name"})
        assert result == {"name": "test"}
        assert "value" not in result
        assert "extra" not in result

    def test_to_dict_with_nested(self):
        """Should serialize nested serializable objects."""
        child = SimpleModel("child", 1)
        parent = NestedModel("parent", child)
        result = parent.to_dict()
        assert result["id"] == "parent"
        assert result["child"] == {"name": "child", "value": 1}

    def test_to_dict_with_special_types(self):
        """Should properly serialize special types."""
        uid = uuid.uuid4()
        dt = datetime(2023, 1, 15, 10, 30, 45)
        d = date(2023, 1, 15)
        dec = Decimal("3.14")

        model = ModelWithSpecialTypes(uid, dec, dt, d, TestEnum.ACTIVE)
        result = model.to_dict()

        assert result["uuid_field"] == str(uid)
        assert result["decimal_field"] == "3.14"
        assert result["datetime_field"] == "2023-01-15T10:30:45"
        assert result["date_field"] == "2023-01-15"
        assert result["enum_field"] == "active"

    def test_to_dict_with_collections(self):
        """Should serialize collections."""
        model = ModelWithCollections(
            items=["a", "b", "c"],
            mapping={"x": 1, "y": 2},
            children=[SimpleModel("child1", 1), SimpleModel("child2", 2)]
        )
        result = model.to_dict()

        assert result["items"] == ["a", "b", "c"]
        assert result["mapping"] == {"x": 1, "y": 2}
        assert len(result["children"]) == 2
        assert result["children"][0]["name"] == "child1"

    def test_to_dict_class_level_exclude(self):
        """Should respect class-level _exclude_fields."""
        model = ModelWithExcludedFields("user", "secret123", "public info")
        result = model.to_dict()

        assert result["username"] == "user"
        assert result["public_info"] == "public info"
        assert "password" not in result
        assert "_internal" not in result

    def test_to_json(self):
        """Should convert to JSON string."""
        model = SimpleModel("test", 42)
        json_str = model.to_json()

        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed == {"name": "test", "value": 42}

    def test_from_dict_basic(self):
        """Should deserialize basic dict."""
        data = {"name": "test", "value": 42}
        model = SimpleModel.from_dict(data)

        assert model.name == "test"
        assert model.value == 42

    def test_from_json(self):
        """Should deserialize from JSON string."""
        json_str = '{"name": "test", "value": 42}'
        model = SimpleModel.from_json(json_str)

        assert model.name == "test"
        assert model.value == 42

    def test_copy(self):
        """Should create deep copy."""
        original = SimpleModel("test", 42)
        copied = original.copy()

        assert copied.name == original.name
        assert copied.value == original.value
        assert copied is not original

    def test_update(self):
        """Should create updated copy."""
        original = SimpleModel("test", 42)
        updated = original.update(name="updated")

        assert updated.name == "updated"
        assert updated.value == 42
        assert original.name == "test"  # Original unchanged


# =====================================================================
# Tests for SerializableMixin with dataclasses
# =====================================================================

class TestSerializableMixinDataclasses:
    """Test SerializableMixin with dataclasses."""

    def test_dataclass_to_dict(self):
        """Should serialize dataclass."""
        model = DataclassModel("test", 42)
        result = model.to_dict()
        assert result == {"name": "test", "value": 42}

    def test_dataclass_from_dict(self):
        """Should deserialize dataclass."""
        data = {"name": "test", "value": 42}
        model = DataclassModel.from_dict(data)

        assert model.name == "test"
        assert model.value == 42

    def test_dataclass_with_defaults(self):
        """Should handle default values."""
        data = {"name": "test"}  # value has default
        model = DataclassModel.from_dict(data)

        assert model.name == "test"
        assert model.value == 0  # default value

    def test_dataclass_with_nested(self):
        """Should serialize nested dataclass."""
        child = DataclassModel("child", 1)
        parent = DataclassWithNested("parent", child)
        result = parent.to_dict()

        assert result["id"] == "parent"
        assert result["child"] == {"name": "child", "value": 1}


# =====================================================================
# Tests for dataclass_serializable decorator
# =====================================================================

class TestDataclassSerializableDecorator:
    """Test @dataclass_serializable decorator."""

    def test_decorator_creates_serializable_class(self):
        """Should create serializable dataclass."""
        @dataclass_serializable
        class MyModel:
            name: str
            value: int = 0

        model = MyModel("test", 42)
        result = model.to_dict()
        assert result == {"name": "test", "value": 42}
        assert hasattr(model, 'from_dict')

    def test_decorator_with_exclude(self):
        """Should support exclude parameter."""
        @dataclass_serializable(exclude={"secret"})
        class SecureModel:
            name: str
            secret: str

        model = SecureModel("public", "hidden")
        result = model.to_dict()
        assert "name" in result
        assert "secret" not in result

    def test_decorator_with_include_none(self):
        """Should support include_none parameter."""
        @dataclass_serializable(include_none={"optional_field"})
        class OptionalModel:
            name: str
            optional_field: str = None

        model = OptionalModel("test")
        result = model.to_dict()
        assert "optional_field" in result
        assert result["optional_field"] is None


# =====================================================================
# Tests for helper functions
# =====================================================================

class TestHelperFunctions:
    """Test helper functions."""

    def test_is_serializable_type_true(self):
        """Should return True for serializable types."""
        assert is_serializable_type(SerializableMixin)
        assert is_serializable_type(SimpleModel)

    def test_is_serializable_type_false(self):
        """Should return False for non-serializable types."""
        assert not is_serializable_type(str)
        assert not is_serializable_type(int)
        assert not is_serializable_type(dict)

    def test_serialize_list(self):
        """Should serialize list of objects."""
        models = [SimpleModel("one", 1), SimpleModel("two", 2)]
        result = serialize_list(models)

        assert len(result) == 2
        assert result[0]["name"] == "one"
        assert result[1]["name"] == "two"

    def test_deserialize_list(self):
        """Should deserialize list to objects."""
        data = [{"name": "one", "value": 1}, {"name": "two", "value": 2}]
        result = deserialize_list(data, SimpleModel)

        assert len(result) == 2
        assert result[0].name == "one"
        assert result[1].value == 2


# =====================================================================
# Integration tests
# =====================================================================

class TestSerializationRoundTrip:
    """Test complete serialization round trips."""

    def test_simple_round_trip(self):
        """Simple model should round-trip correctly."""
        original = SimpleModel("test", 42)
        data = original.to_dict()
        restored = SimpleModel.from_dict(data)

        assert restored.name == original.name
        assert restored.value == original.value

    def test_json_round_trip(self):
        """Should round-trip through JSON."""
        original = SimpleModel("test", 42)
        json_str = original.to_json()
        restored = SimpleModel.from_json(json_str)

        assert restored.name == original.name
        assert restored.value == original.value

    def test_dataclass_round_trip(self):
        """Dataclass should round-trip correctly."""
        original = DataclassModel("test", 42)
        data = original.to_dict()
        restored = DataclassModel.from_dict(data)

        assert restored.name == original.name
        assert restored.value == original.value

    def test_complex_round_trip(self):
        """Complex model with special types should round-trip."""
        original = ModelWithSpecialTypes(
            uuid_field=uuid.uuid4(),
            decimal_field=Decimal("3.14159"),
            datetime_field=datetime(2023, 1, 15, 10, 30, 45),
            date_field=date(2023, 1, 15),
            enum_field=TestEnum.ACTIVE
        )
        data = original.to_dict()
        restored = ModelWithSpecialTypes.from_dict(data)

        assert restored.uuid_field == str(original.uuid_field)
        assert restored.decimal_field == str(original.decimal_field)
        assert restored.datetime_field == "2023-01-15T10:30:45"
        assert restored.date_field == "2023-01-15"
        assert restored.enum_field == "active"
