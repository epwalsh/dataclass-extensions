# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

## [v0.2.5](https://github.com/epwalsh/dataclass-extensions/releases/tag/v0.2.5) - 2026-01-26

### Fixed

- Fixed a bug with decoding optional enum types.

## [v0.2.4](https://github.com/epwalsh/dataclass-extensions/releases/tag/v0.2.4) - 2025-10-27

### Fixed

- Fixed decoding directly from a registered subclass with different fields.

## [v0.2.3](https://github.com/epwalsh/dataclass-extensions/releases/tag/v0.2.3) - 2025-09-03

### Changed

- `decode()` will raise an `AttributeError` instead of a `KeyError` when the data contains a field not defined by the class.

### Fixed

- Handle enum types in `encode()`.

## [v0.2.2](https://github.com/epwalsh/dataclass-extensions/releases/tag/v0.2.2) - 2025-06-23

### Fixed

- Provide a better error message when types can't be resolved due to `from __future__ import annotations`.
- Allow decoding integers as floats.

## [v0.2.1](https://github.com/epwalsh/dataclass-extensions/releases/tag/v0.2.1) - 2025-06-11

### Fixed

- Fixed decoding registrable types with sub-types that have fields that are not in the base type.

## [v0.2.0](https://github.com/epwalsh/dataclass-extensions/releases/tag/v0.2.0) - 2025-06-11

### Added

- Added `default: bool` option to `Registrable.register()` for defining a default implementation.

## [v0.1.0](https://github.com/epwalsh/dataclass-extensions/releases/tag/v0.1.0) - 2025-06-10

## Added

- Added initial version.
