# Changelog

## 1.4.4 — 26 November 2026

### Added

- **CISA SSVC decisions** now drive the ranking. The engine used to infer exploitation from
  wording — "exploitation active", "dans la nature" — and missed any source phrasing it
  differently. CISA Vulnrichment states it per CVE: Exploitation (none / poc / active),
  Automatable, Technical Impact. Entries carrying an `active` decision gain five points and a
  ⚔️ badge, a proof of concept two points and 🧪, automatable and total impact one point each.
  On the first real run: 27 CVEs read, 12 articles raised.

The lookup is bounded to forty CVEs per run, taken from the highest-scoring articles, and
cached — including "the CISA has not ruled", so a silent CVE is not asked twice.

## 1.4.3 — 25 November 2026

### Added

- **Ubuntu and Red Hat** join the collected sources, the first distributions in the engine. A
  brief answering "is this version affected" was silent on the two platforms most server fleets
  run. Ubuntu publishes a numbered advisory feed; Red Hat publishes none, so the engine queries
  its security data API and keeps the CVEs published inside the window.

### Changed

- A KEV entry now opens its detail with the **CISA remediation deadline** when the catalogue
  gives one, and with the first two CWEs otherwise. Both fields were fetched and cached, and
  neither reached the report.

### Fixed

- The ENISA EUVD source pasted its raw exception into the daily error line; it now uses the
  same short reason as every other source.

## 1.4.2 — 25 November 2026

### Added

- **NCSC Ireland** joins the national CERT feeds. It publishes in English, with CVE
  identifiers, which makes it the simplest source added so far: no phrase table, no
  translation to keep up.

## 1.4.1 — 25 November 2026

### Added

- **Nine national CERT feeds** reach the application: Italy, Luxembourg, Austria, Norway,
  Finland, Hungary, Romania, Slovakia and Spain. Their titles are translated to English —
  eleven phrase tables, plus pattern rewriting where the product sits in the middle of the
  sentence (Hungarian, Romanian, Slovak).
- The **first `SHA256SUMS` file** is attached by the release workflow: one file, produced from
  the archives themselves, instead of checksums typed into the release notes.

### Changed

- The engine is re-pinned to `92e752d`, which carries the CERT work, the corrected source
  error messages, and `SOURCES.md` — the inventory of which CERT is covered and why the others
  are not.

### Fixed

- An accented character from the engine lost its accent in the journal (`NVD (�diteurs)`). The
  child's output is decoded as UTF-8, then as the Windows code page when that fails, instead
  of being replaced silently.
- A source in error now says **why** — "délai dépassé", "injoignable", "HTTP 403" — instead of
  pasting a Python exception into the daily mail.

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
