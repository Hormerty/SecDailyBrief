# Changelog

## 1.1.0 — 24 November 2026

### Added

- **Portable mode**: a second archive, marked with `portable.flag`, whose data lives in a
  `data` folder next to the executable instead of the Windows profile. The diagnostic reports
  the current mode, because the difference matters: in portable mode, deleting the folder
  also deletes the settings.
- **Seven-day history**, reachable from the panel: date, mode, status and duration of each
  run, without digging through the log.
- **Strict validation of the perimeter file** at startup. The faulty section is named —
  unknown section, `stack` as a list, empty keywords — and the example values can be
  restored. The faulty file is kept as `.invalide` rather than destroyed.
- Run statuses are translated in the status line and in the history.

### Changed

- **The version is checked at build time**: the package, the Windows properties and
  `pyproject.toml` must agree, or the build stops. Three copies of the same truth always end
  up diverging.
- The "Buy me a coffee" button uses the normal weight, like the others.

### Fixed

- The consent setting is no longer asked again on every return to the page.

## 1.0.0 — 23 November 2026

First usable version.

- Five-page wizard: language (FR/EN/NL), consent, sending account, stack, schedule.
- Control panel: run, preview, open the report, test sources, check links, log, diagnostic,
  history.
- Sending verified by a real message before saving; password encrypted by Windows.
- Daily scheduled task, with catch-up if the machine was off.
- Ten-point diagnostic, including the engine's ability to actually import and the presence
  of the TLS certificates.
- Engine embedded at a pinned commit, with its checksum verified on every build.
