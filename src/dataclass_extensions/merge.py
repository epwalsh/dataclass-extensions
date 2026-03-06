from __future__ import annotations

from typing import Any, TypeVar, cast, overload

import yaml

from .decode import DecodeError, decode
from .encode import encode
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

    # Encode current instance.
    current = encode(instance, errors="ignore")

    # Apply updates from each dict to the raw/encoded values.
    for d in dicts:
        current = _merge_dicts(current, d)

    # Then decode back to the correct types, applying any custom handlers and validating field names.
    return decode(cls, current)


@overload
def merge_from_dotlist(instance: C, overrides: list[str], /) -> C:
    ...


@overload
def merge_from_dotlist(instance: C, *overrides: str) -> C:
    ...


def merge_from_dotlist(instance: C, *overrides: str | list[str]) -> C:
    """
    Merge field overrides expressed as dot-notation strings into a dataclass,
    returning a new instance of the same type. The original instance is not modified.

    Each override has the form ``"field=value"`` where the value is parsed as YAML.
    Nested fields can be targeted with dot notation: ``"optimizer.lr=0.001"``.

    Multiple overrides that share a common prefix are merged together, so
    ``"optimizer.lr=0.001"`` and ``"optimizer.steps=500"`` both update the same
    nested ``optimizer`` field.

    Can be called with variadic string arguments or a single list of strings::

        result = merge_from_dotlist(config, "optimizer.lr=0.001", "name=run2")
        result = merge_from_dotlist(config, ["optimizer.lr=0.001", "name=run2"])

    :raises ValueError: If an override string does not contain ``=``.
    :raises DecodeError: If a key is not a valid field name, or if a value cannot
        be coerced to the expected type.
    """
    if len(overrides) == 1 and isinstance(overrides[0], list):
        resolved: tuple[str, ...] = tuple(overrides[0])
    else:
        resolved = cast(tuple[str, ...], overrides)

    # Encode current instance.
    current = encode(instance, errors="ignore")

    # Override raw encoded values.
    for override in resolved:
        if override.startswith("--"):
            override = override[2:]
        if override.startswith("-"):
            raise ValueError(
                f"Invalid override {override!r}: expected the form 'field=value' or '--field=value'"
            )
        if "=" not in override:
            raise ValueError(f"Invalid override {override!r}: expected the form 'field=value'")
        key, _, raw_value = override.partition("=")
        value = yaml.safe_load(raw_value)
        _set_nested(current, key, value)

    # Decode back to the correct types, applying any custom handlers and validating field names.
    return decode(type(instance), current)


def _merge_dicts(base: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    for key, value in updates.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            base[key] = _merge_dicts(base[key], value)
        else:
            base[key] = value
    return base


def _set_nested(data: Any, key: str, value: Any):
    if "." in key:
        key, child_keys = key.split(".", 1)
        if isinstance(data, dict):
            _set_nested(data[key], child_keys, value)
        elif isinstance(data, list):
            _set_nested(data[int(key)], child_keys, value)
        else:
            raise DecodeError(data)
    else:
        if isinstance(data, dict):
            data[key] = value
        elif isinstance(data, list):
            try:
                idx = int(key)
            except ValueError:
                raise DecodeError(f"Expected integer index for list but got '{key}'")
            if idx < 0:
                idx += len(data)
            if idx < 0 or idx >= len(data):
                raise DecodeError(f"Index {idx} is out of bounds for list of length {len(data)}")
            data[idx] = value
        else:
            raise DecodeError(
                f"Can't set value '{value}' at key '{key}' for object {data} of type {type(data)}"
            )
