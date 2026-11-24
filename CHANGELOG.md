# Changelog

## 1.4.0 — 24 November 2026

### Added

- **Portuguese, Hindi and Mandarin Chinese.** The interface now speaks nine languages. The
  Devanagari and CJK glyphs rely on the Windows font fallback, which was checked on captures
  rather than assumed: both render without missing-glyph boxes, and the labels fit the
  buttons.
- Traditional Chinese is not distinguished from Simplified: a `zh-TW` system lands on the
  Simplified strings. Adding a `zh-Hant` variant would be a separate dictionary.

### Changed

- The test that checks an unsupported language now uses a code that can never be added
  (`xx-XX`). It had twice failed because it named a real language that later got translated.

## 1.3.0 — 24 November 2026

### Added

- **The time zone is detected on first run.** Until now the wizard offered Brussels, the
  author's zone, to everyone. Windows zone names are now translated to their IANA equivalent;
  a zone outside the table keeps the default, and a zone the user has chosen is never
  overwritten.
- **"Check for updates" button** in the panel. It asks GitHub on demand, reports whether the
  installed version is current, and offers to open the download page when a newer one exists.

### Fixed

- The diagnostic and the startup update banner updated the interface from their worker
  thread. Tk rejects this with "main thread is not in main loop", so the diagnostic report
  could fail to appear while the window stayed on its waiting state. All background work now
  goes through a single helper that polls from the main thread, and the test suite treats
  unhandled thread exceptions as errors.

## 1.2.1 — 24 November 2026

### Fixed

- The `README.txt` inside the archive announced version 1.1.0 in the 1.2.0 package. The
  title is now written by the build script from the package version, and the script reads
  the copied file back before packaging: a line maintained by hand does not follow the
  version, and this one did not.

## 1.2.0 — 24 November 2026

### Added

- **German, Spanish and Italian.** The interface now speaks six languages; a system set to
  any of them lands on it directly instead of falling back to English. The report itself is
  still written in English: only the application is translated.
- **Saved settings are checked at startup**, like the perimeter file. A `config.json` edited
  by hand used to stay wrong until the next run; it is now named at launch, with an offer to
  open the page that fixes it. The settings are never reset — that would erase the address.

### Changed

- The version is checked at build time across the package, the Windows properties and
  `pyproject.toml`, and publishing is done by a workflow rather than from a workstation.

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
