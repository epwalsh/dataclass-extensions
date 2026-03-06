from __future__ import annotations

import dataclasses
import pathlib
import warnings
from datetime import datetime
from enum import Enum
from typing import Any, Callable, ClassVar, Generator, Literal, Type, TypeVar

from .registrable import Registrable
from .types import *

C = TypeVar("C", bound=Dataclass)


class Encoder:
    custom_handlers: ClassVar[dict[Type, Callable[[Any], Any]]] = {}

    def register_encoder(self, encoder_fun: Callable[[Any], Any], *target_types: Type):
        for type in target_types:
            self.custom_handlers[type] = encoder_fun

    def __call__(
        self,
        data: Any,
        *,
        exclude_none: bool = False,
        exclude_private_fields: bool = False,
        recurse: bool = True,
        errors: Literal["raise", "ignore", "stringify"] = "raise",
        strict: bool | None = None,
    ) -> Any:
        """
        Encode a Python object into JSON-safe dictionary. The inverse of :func:`decode()`.

        :param exclude_none: Don't include values that are ``None``.
        :param exclude_private_fields: Don't include private fields.
        :param recurse: Recurse into fields that are also configs/dataclasses.
        :param errors: How to handle values that don't have a safe encoding method.
            If ``"raise"`` a ``TypeError`` is raised.
            If ``"ignore"`` the value is returned as-is.
            If ``"stringify"`` the value is converted to a string.
        :param strict: Deprecated. Use ``errors`` instead.
            ``True`` is equivalent to ``errors="raise"`` and ``False`` is equivalent to ``errors="ignore"``.
        """

        if strict is not None:
            warnings.warn(
                "Passing 'strict' is deprecated. Use 'errors' instead.",
                DeprecationWarning,
                stacklevel=2,
            )
            errors = "raise" if strict else "stringify"

        def iter_fields(d) -> Generator[tuple[str, Any], None, None]:
            for field in dataclasses.fields(d):
                value = getattr(d, field.name)
                if not field.init:
                    continue
                elif exclude_none and value is None:
                    continue
                elif exclude_private_fields and field.name.startswith("_"):
                    continue
                else:
                    yield (field.name, value)

        def as_dict(d: Any, recurse: bool = True) -> Any:
            if type(d) in self.custom_handlers:
                return self.custom_handlers[type(d)](d)
            elif dataclasses.is_dataclass(d):
                if recurse:
                    out = {k: as_dict(v) for k, v in iter_fields(d)}
                else:
                    out = {k: v for k, v in iter_fields(d)}
                if isinstance(d, Registrable):
                    try:
                        registered_name = d.get_registered_name()
                        out["type"] = registered_name
                    except ValueError:
                        pass
                return out
            elif isinstance(d, dict):
                return {k: as_dict(v) for k, v in d.items()}
            elif isinstance(d, (list, tuple, set)):
                return [as_dict(x) for x in d]
            elif isinstance(d, datetime):
                return d.timestamp()
            elif isinstance(d, pathlib.Path):
                return str(d)
            elif isinstance(d, Enum):
                return d.value
            elif d is None or isinstance(d, (float, int, bool, str)):
                return d

            for t, h in self.custom_handlers.items():
                try:
                    if isinstance(d, t):
                        return h(d)
                except TypeError:
                    continue

            if errors == "raise":
                raise TypeError(f"not sure how to encode '{d}' of type {type(d)}")
            elif errors == "stringify":
                return str(d)
            elif errors == "ignore":
                return d
            else:
                raise ValueError(f"Invalid value for 'errors': {errors!r}")

        return as_dict(data, recurse=recurse)


encode = Encoder()
