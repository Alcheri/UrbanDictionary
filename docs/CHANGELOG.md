# Changelog

All notable changes to UrbanDictionary are documented in this file.

## Unreleased

### Added

- Added a security policy.
- Moved supporting project documentation into the `docs/` directory.

### Changed

- Standardised GitHub support files.
- Updated contribution terms.
- Normalised README badges and Black configuration.
- Applied Black formatting.
- Ignored the local `Documents/` directory.

### Fixed

- Hardened UrbanDictionary command handling.

## v1.0.0 - 2026-04-28

### Added

- Added PEP 621 package metadata in `pyproject.toml`.
- Added GitHub Actions testing, linting, and CodeQL workflow support.
- Added licence documentation for the original upstream MIT Licence and Barry Suridge's maintained contributions.
- Added Python source header policy documentation.

### Changed

- Updated the plugin version to `1.0.0`.
- Modernised the plugin structure, README, badges, and repository metadata.
- Standardised CI workflows and Black lint checks.
- Updated request headers for UrbanDictionary lookups.
- Ignored Supybot runtime directories, Codex files, and Python cache artefacts.

### Fixed

- Fixed HTML escaping and unescaping in UrbanDictionary output.
- Aligned `aiohttp` usage with the active virtual environment and type checks.
- Fixed package metadata.
