# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

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

- Added initial verison.
