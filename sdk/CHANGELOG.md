# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
