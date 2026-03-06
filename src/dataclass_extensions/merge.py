from __future__ import annotations

import dataclasses
from typing import Any, TypeVar

import yaml

from .decode import DecodeError, _coerce, _get_type_hints
from .types import Dataclass

C = TypeVar("C", bound=Dataclass)


def merge(instance: C, *dicts: dict[str, Any]) -> C:
    """
    Merge one or more unstructured dictionaries into a dataclass, returning a new
    instance of the same type. The original instance is not modified.

    When a dictionary value is itself a dict and the corresponding field on the
    instance is already a dataclass, the merge is applied recursively.

    :raises DecodeError: If a key in a dictionary is not a valid field name, or if
        a value cannot be coerced to the expected type.
    """
    cls = type(instance)
    type_hints = _get_type_hints(cls)

    # Collect current values for all init fields.
    current: dict[str, Any] = {}
    for f in dataclasses.fields(instance):  # type: ignore[arg-type]
        if f.init:
            current[f.name] = getattr(instance, f.name)

    for d in dicts:
        for key, value in d.items():
            if key not in type_hints:
                raise DecodeError(f"class '{cls.__qualname__}' has no attribute '{key}'")

            existing = current[key]

            # Recursively merge when the incoming value is a dict and the existing
            # value is a dataclass instance (not a dataclass class/type).
            if (
                isinstance(value, dict)
                and dataclasses.is_dataclass(existing)
                and not isinstance(existing, type)
            ):
                current[key] = merge(existing, value)
            else:
                current[key] = _coerce(value, type_hints[key], {}, key, cls)

    return cls(**current)


def merge_from_dotlist(instance: C, *overrides: str) -> C:
    """
    Merge field overrides expressed as dot-notation strings into a dataclass,
    returning a new instance of the same type. The original instance is not modified.

    Each override has the form ``"field=value"`` where the value is parsed as YAML.
    Nested fields can be targeted with dot notation: ``"optimizer.lr=0.001"``.

    Multiple overrides that share a common prefix are merged together, so
    ``"optimizer.lr=0.001"`` and ``"optimizer.steps=500"`` both update the same
    nested ``optimizer`` field.

    Example::

        result = merge_from_dotlist(config, "optimizer.lr=0.001", "name=run2")

    :raises ValueError: If an override string does not contain ``=``.
    :raises DecodeError: If a key is not a valid field name, or if a value cannot
        be coerced to the expected type.
    """
    nested: dict[str, Any] = {}
    for override in overrides:
        if "=" not in override:
            raise ValueError(f"Invalid override {override!r}: expected the form 'field=value'")
        key, _, raw_value = override.partition("=")
        value = yaml.safe_load(raw_value)
        _set_nested(nested, key.split("."), value)
    return merge(instance, nested)


def _set_nested(d: dict[str, Any], parts: list[str], value: Any) -> None:
    """Write *value* into *d* at the path described by *parts*, creating
    intermediate dicts as needed."""
    for part in parts[:-1]:
        existing = d.get(part)
        if existing is None:
            d[part] = {}
            d = d[part]
        elif isinstance(existing, dict):
            d = existing
        else:
            raise ValueError(
                f"Conflicting overrides: '{part}' is set both as a leaf value "
                "and as a nested key"
            )
    d[parts[-1]] = value
