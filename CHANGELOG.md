# Changelog

All notable changes to ACAN Studio are documented here. The project follows a
lightweight versioning scheme: patch releases fix regressions, minor releases
add creator-facing capabilities, and major releases may change workflows.

## [Unreleased]

Further changes after 1.3.1 will be recorded here.

## [1.3.1] — 2026-09-08

### Fixed

- Keep MangoTV's initial metadata request compatible with the public web player
  so valid videos are not incorrectly rejected as geo-blocked.
- Preserve the logged-in browser device identity for the stream request and add
  a specific Chinese message for genuine region or copyright restrictions.

## [1.3.0] — 2026-09-08

### Added

- Add an MP3-to-WAV action that writes broadly compatible 16-bit PCM audio,
  preserves the source sample rate and channel layout, and avoids overwriting
  existing files in the Audio library.

## [1.2.1] — 2026-09-07

### Fixed

- Include and explicitly load CA certificates for HTTPS short-link resolution
  and Weibo link checks in frozen apps; keep certificate and hostname checks enabled.
- Recognize Douyin's exact `Fresh cookies (not necessarily logged in)` failure.
  Explain that HTTP 403 may persist even with browser cookies and is not proof of missing login.
- Log the running app version and loaded CA count; add `--check-https URL` for
  diagnosing packaged HTTPS without opening a window.

### Known limitations

- The reported Douyin video still returns HTTP 403 with the current bundled
  yt-dlp and Chrome cookies. This release fixes link resolution, not that platform refusal.

## [1.2.0] — 2026-08-31

### Added

- Dependency-light `acan_studio.core` modules for URL and content detection,
  media formatting, SRT conversion, download command construction, and failure
  suggestions.
- A first automated core test suite and GitHub Actions workflow.
- `CONTRIBUTING.md`, issue templates, a pull request template, and
  `ROADMAP.md`.

### Changed

- The desktop application now delegates pure media and downloader logic to
  the reusable core modules while keeping the existing GUI workflow.
- Project version is centralized in `VERSION` and packaging scripts default to
  1.2.0.

### Fixed

- Douyin and Weibo download attempts no longer read Chrome cookies unless a
  cookie source is explicitly enabled in Settings.
- Pasted URLs have surrounding share-text punctuation removed.
- SRT timestamps correctly carry rounded milliseconds into the next second.

## [1.1.8] — 2026-08-29

- Improved YouTube JavaScript challenge support with bundled Deno and EJS
  components in the compatibility build.
- Added resilient YouTube transport fallbacks and Apple Silicon/Intel macOS
  compatibility packaging.

[Unreleased]: https://github.com/fanxiaoyu7220/ACAN-Studio/compare/v1.3.1...HEAD
[1.3.1]: https://github.com/fanxiaoyu7220/ACAN-Studio/releases/tag/v1.3.1
[1.3.0]: https://github.com/fanxiaoyu7220/ACAN-Studio/releases/tag/v1.3.0
[1.2.1]: https://github.com/fanxiaoyu7220/ACAN-Studio/releases/tag/v1.2.1
[1.2.0]: https://github.com/fanxiaoyu7220/ACAN-Studio/releases/tag/v1.2.0
[1.1.8]: https://github.com/fanxiaoyu7220/ACAN-Studio/releases/tag/v1.1.8
