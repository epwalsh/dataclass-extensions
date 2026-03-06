from __future__ import annotations

import dataclasses
import typing
from typing import Any, TypeVar, cast, overload

import yaml

from .decode import DecodeError, _coerce, _get_type_hints
from .types import Dataclass

C = TypeVar("C", bound=Dataclass)


def merge(instance: C, *dicts: dict[str, Any]) -> C:
    """
    Merge one or more unstructured dictionaries into a dataclass, returning a new
    instance of the same type. The original instance is not modified.

    When a dictionary value is itself a dict and the corresponding field on the
    instance is already a dataclass, the merge is applied recursively. When the
    value is a dict with integer keys and the existing field is a sequence, the
    updates are applied by index.

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
            elif (
                isinstance(value, dict)
                and isinstance(existing, (list, tuple))
                and value
                and all(isinstance(k, int) for k in value)
            ):
                current[key] = _merge_sequence_by_index(existing, value, type_hints[key], key, cls)
            else:
                current[key] = _coerce(value, type_hints[key], {}, key, cls)

    return cls(**current)


def _merge_sequence_by_index(
    existing: list | tuple,
    updates: dict[int, Any],
    type_hint: Any,
    key: str,
    owner: Any,
) -> list | tuple:
    """Apply index-keyed updates to a list or tuple, returning the same container type."""
    items = list(existing)
    origin = typing.get_origin(type_hint)
    args = typing.get_args(type_hint)

    for idx, val in updates.items():
        if args:
            if origin is tuple:
                # tuple[T, ...] — all elements share args[0]
                if len(args) == 2 and args[1] is ...:
                    elem_type = args[0]
                elif idx < len(args):
                    elem_type = args[idx]
                else:
                    elem_type = Any
            else:
                # list[T], Sequence[T], etc. — single element type
                elem_type = args[0]
        else:
            elem_type = Any
        items[idx] = _coerce(val, elem_type, {}, f"{key}.{idx}", owner)

    return type(existing)(items)


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
    nested: dict[str, Any] = {}
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
        _set_nested(nested, key.split("."), value)
    return merge(instance, nested)


def _set_nested(d: dict, parts: list[str], value: Any) -> None:
    """Write *value* into *d* at the path described by *parts*, creating
    intermediate dicts as needed. Digit-only parts are stored as integer keys
    so that merge() can apply them as sequence indices."""
    for part in parts[:-1]:
        key: str | int = int(part) if part.isdigit() else part
        existing = d.get(key)
        if existing is None:
            d[key] = {}
            d = d[key]
        elif isinstance(existing, dict):
            d = existing
        else:
            raise ValueError(
                f"Conflicting overrides: '{part}' is set both as a leaf value "
                "and as a nested key"
            )
    last = parts[-1]
    d[int(last) if last.isdigit() else last] = value
