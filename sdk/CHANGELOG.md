# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-07-14

### Fixed
- `getDecision()` no longer passes a non-2xx `/api/predict` error body through
  as if it were a decision result (previously crashed downstream callers with
  `Cannot read properties of undefined (reading 'toLowerCase')`). Now returns
  a clean `{ action: 'block', error: '<reason>' }`.
- Default endpoint changed from `http://localhost:8001` to the production API
  (`https://next-captcha-sdk.onrender.com`) so the SDK works out of the box
  without an explicit `endpoint` config.
- `package.json` `exports` map now lists `types` first in each condition
  block (required for correct TypeScript resolution).
- `repository`/`bugs`/`homepage` metadata corrected to point at the real repo.

### Added
- `LICENSE` file (MIT, matching `package.json`).

### Changed
- Collector start/stop calls are now wrapped so an internal collector bug logs
  a warning instead of throwing into the host page.
- `SDK_VERSION` kept in sync with `package.json`.

## [0.1.0] - 2026-07-04

### Added
- Initial release of SmartCaptcha SDK
- Behavioral telemetry collection (mouse, keyboard, scroll, click, focus, touch events)
- Session management with unique session IDs
- Event buffering and batch transmission
- `init()` method for SDK initialization
- `getDecision()` method for bot detection decisions
- `getSessionId()` and `getSessionMeta()` methods
- Support for custom backend endpoints
- Debug mode for development
- Multiple build formats (UMD, ESM, CJS)
- Package exports map for automatic format selection
- Risk Engine integration with fingerprint detection

### Technical Details
- Bundle size: 11.7KB (minified UMD)
- Dependencies: esbuild for bundling
- Compatible with modern browsers and bundlers

### Known Limitations
- TypeScript types not yet included (planned for 0.2.0)
- CDN distribution not yet available (planned for 0.2.0)
- Framework wrappers (React, Vue) not yet available (planned for 0.3.0)

## [Unreleased]

### Planned
- TypeScript type definitions
- CDN distribution
- Enhanced error handling
- Debug mode improvements
- Framework wrappers
