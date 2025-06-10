import os
from typing import Any, ClassVar, Protocol

__all__ = [
    "MISSING",
    "PathOrStr",
    "Dataclass",
]

MISSING = object()
PathOrStr = os.PathLike | str


class Dataclass(Protocol):
    __dataclass_fields__: ClassVar[dict[str, Any]]
