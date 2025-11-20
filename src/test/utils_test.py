from __future__ import annotations

import dataclasses

import pytest

from dataclass_extensions.decode import decode
from dataclass_extensions.types import MISSING
from dataclass_extensions.utils import required_field


def test_required_field_strict_with_name():
    """Test required_field() with strict=True and name provided."""

    @dataclasses.dataclass
    class Config:
        x: int = required_field("x", strict=True)
        y: str = required_field("y", strict=True)

    # Field should have a default_factory that raises ValueError
    field_x = dataclasses.fields(Config)[0]
    assert field_x.default is dataclasses.MISSING
    assert field_x.default_factory is not dataclasses.MISSING
    assert callable(field_x.default_factory)

    # Calling the factory should raise ValueError with the field name
    with pytest.raises(ValueError, match="missing required field 'x'"):
        Config(y="y")

    with pytest.raises(ValueError, match="missing required field 'y'"):
        Config(x=1)


def test_required_field_strict_without_name():
    """Test that required_field() raises ValueError when strict=True but name is not provided."""
    with pytest.raises(
        ValueError, match="'name' is required for a required_field with 'strict=True'"
    ):

        @dataclasses.dataclass
        class Config:
            x: int = required_field(strict=True)  # type: ignore


def test_required_field_in_dataclass_creation():
    """Test that dataclass creation works with required_field."""

    @dataclasses.dataclass
    class Config:
        x: int = required_field()
        y: str = required_field("y")

    # Should be able to create with values provided
    config = Config(x=1, y="test")
    assert config.x == 1
    assert config.y == "test"

    # When fields are missing, dataclass will use MISSING as default
    # (dataclasses don't raise errors on creation, they just use defaults)
    config_missing_x = Config(y="test")
    assert config_missing_x.x is MISSING
    assert config_missing_x.y == "test"

    config_missing_y = Config(x=1)
    assert config_missing_y.x == 1
    assert config_missing_y.y is MISSING


def test_required_field_strict_in_dataclass_creation():
    """Test that dataclass creation with strict=True raises ValueError during initialization."""

    @dataclasses.dataclass
    class Config:
        x: int = required_field("x", strict=True)
        y: str = required_field("y", strict=True)

    # Should be able to create with values provided
    config = Config(x=1, y="test")
    assert config.x == 1
    assert config.y == "test"

    # When creating without required fields, ValueError is raised during initialization
    # because the default_factory is called
    with pytest.raises(ValueError, match="missing required field 'x'"):
        Config(y="test")  # Missing x

    with pytest.raises(ValueError, match="missing required field 'y'"):
        Config(x=1)  # Missing y

    # When all fields are missing, ValueError is raised during initialization
    with pytest.raises(ValueError, match="missing required field 'x'"):
        Config()


def test_required_field_with_decode():
    """Test integration with decode() - missing required fields will have MISSING values."""

    @dataclasses.dataclass
    class Config:
        x: int = required_field()
        y: str = required_field("y")

    # Should decode successfully when all fields are provided
    config = decode(Config, {"x": 1, "y": "test"})
    assert config.x == 1
    assert config.y == "test"

    # When fields are missing from data, decode will create instance with MISSING values
    # (decode doesn't check for missing fields, it just processes what's in the dict)
    config_missing_y = decode(Config, {"x": 1})
    assert config_missing_y.x == 1
    assert config_missing_y.y is MISSING

    config_missing_x = decode(Config, {"y": "test"})
    assert config_missing_x.x is MISSING
    assert config_missing_x.y == "test"


def test_required_field_strict_with_decode():
    """Test integration with decode() when using strict=True."""

    @dataclasses.dataclass
    class Config:
        x: int = required_field("x", strict=True)
        y: str = required_field("y", strict=True)

    # Should decode successfully when all fields are provided
    config = decode(Config, {"x": 1, "y": "test"})
    assert config.x == 1
    assert config.y == "test"

    # When fields are missing, decode will raise ValueError during initialization
    # because the default_factory is called for missing fields
    with pytest.raises(ValueError, match="missing required field 'y'"):
        decode(Config, {"x": 1})  # Missing y

    with pytest.raises(ValueError, match="missing required field 'x'"):
        decode(Config, {"y": "test"})  # Missing x


def test_required_field_with_optional_fields():
    """Test that required_field works alongside optional fields."""

    @dataclasses.dataclass
    class Config:
        required: int = required_field()
        optional: str | None = None

    # Should work with both provided
    config1 = Config(required=1, optional="test")
    assert config1.required == 1
    assert config1.optional == "test"

    # Should work with optional as None
    config2 = Config(required=1, optional=None)
    assert config2.required == 1
    assert config2.optional is None

    # Should work with optional omitted (uses default)
    config3 = Config(required=1)
    assert config3.required == 1
    assert config3.optional is None

    # When required is missing, it will use MISSING as default
    config4 = Config(optional="test")
    assert config4.required is MISSING
    assert config4.optional == "test"


def test_required_field_type_hints():
    """Test that required_field preserves type hints correctly."""

    @dataclasses.dataclass
    class Config:
        x: int = required_field()
        y: list[str] = required_field("y")
        z: dict[str, int] = required_field("z", strict=True)

    import typing

    type_hints = typing.get_type_hints(Config)
    assert type_hints["x"] == int  # noqa
    assert type_hints["y"] == list[str]
    assert type_hints["z"] == dict[str, int]
