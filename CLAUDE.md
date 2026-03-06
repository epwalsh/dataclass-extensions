# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run a single test file
pytest src/test/encode_test.py

# Run a single test by name
pytest src/test/encode_test.py -k "test_name"

# Lint
ruff check src/

# Type check
mypy src/

# Format
black src/
isort src/
```

## Architecture

This is a small Python library (`src/dataclass_extensions/`) that adds encode/decode, merge, and polymorphism capabilities to standard Python dataclasses. Requires Python 3.10+.

### Public API (all exported from `__init__.py`)

- **`encode`** (`encode.py`) — Singleton `Encoder` instance. Converts dataclasses (recursively) to JSON-safe dicts. Handles `datetime`, `pathlib.Path`, `Enum`, lists, dicts, sets. Supports `Registrable` subclasses by injecting a `"type"` key. Custom encoders registered via `encode.register_encoder(fn, *types)`.

- **`decode`** (`decode.py`) — Singleton `Decoder` instance. Reconstructs typed dataclasses from dicts using `typing.get_type_hints()`. Handles union types, generic containers (`list`, `set`, `tuple`, `dict`, `Sequence`, `Mapping`), forward references, `typing_extensions.Self`, `TypeAliasType` (3.12+), `Literal`, and `Registrable` dispatch via the `"type"` key. Raises `DecodeError` (subclass of `TypeError`) with chained failure messages. Custom decoders registered via `decode.register_decoder(fn, *types)`.

- **`merge`** (`merge.py`) — Creates a new dataclass instance by overlaying dict values onto an existing instance. Recurses into nested dataclass fields when the incoming value is a dict. Uses `_coerce` from `decode.py` for type coercion.

- **`merge_from_dotlist`** (`merge.py`) — Like `merge`, but accepts strings of the form `"field=value"` or `"--field=value"`. Values parsed as YAML. Dot notation targets nested fields (`"optimizer.lr=0.001"`).

- **`Registrable`** (`registrable.py`) — Base class enabling polymorphic encode/decode. Subclasses register with `@MyBase.register("name")`. Encoded with a `"type"` field; decoded by dispatching on that field.

- **`required_field`** (`utils.py`) — Helper for required dataclass fields without defaults.

- **`Dataclass`** (`types.py`) — Protocol type for type-checking dataclass instances.

### Key design patterns

- `encode` and `decode` are module-level singleton instances of `Encoder`/`Decoder` classes, not plain functions. Custom handlers are stored as class variables (`ClassVar`), so they're shared across all uses.
- `decode.py`'s `_coerce` function is internal but reused by `merge.py` — avoid changing its signature.
- Tests live in `src/test/` and are discovered by pytest via `testpaths = "src/test/"` in `pyproject.toml`.
- `src/test/_type_alias.py` is intentionally excluded from ruff and mypy (it uses syntax only valid on newer Python versions).
