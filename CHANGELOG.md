# Changelog

## Unreleased

### Changed

- The engine is re-pinned to 7d6bc40, which carries five commits: sources ranked by what they
  contribute rather than by volume, an honest trend, a dead computation removed, an alert counted
  only when posted, and an HTTP check on webhook addresses.

### Fixed

- **A stale keyring entry no longer overrides the secret file** on Linux. The keyring was queried as
  soon as `secret-tool` existed, even when the file held clear text, so an old entry won and the SMTP
  password was refused without explanation. It is consulted only when the file holds the
  `secret-service` marker, which is what designates it.
- **The Linux instance lock is per user.** It lived in the shared temporary directory with mode
  `0600`: a second account could not open it, an uncaught `PermissionError` at startup, and both
  contended for the same lock. It now sits in `XDG_RUNTIME_DIR` or a `sdb-<uid>` folder, opened with
  `O_NOFOLLOW`.
- **"Next run" showed sixteen digits on Linux.** systemd answers in microseconds; the value is
  converted once, in the planner, instead of being printed raw.
- **The time zone was only detected on Windows.** `zone_iana()` returned the default everywhere
  else, so the assistant proposed Brussels to any user outside Western Europe. `TZ` and the
  `/etc/localtime` link are read first.
- **The history held six days and a half.** A 60-entry bound for a seven-day window, while the report
  plus eight alerts write nine entries a day. The bound is 200.
- **A newline in an address could inject a mail header.** The test message is assembled by hand and
  accepted it in the sender or recipient, where the engine refuses it. Both are refused now.
- **A callback could fire after the window closed**, printing a `TclError` in a console nobody reads.
- **The Linux archive carried neither the MIT licence nor the changelog**, and no uninstaller: the
  copy of a `build/uninstall.sh` that did not exist was hidden by `|| true`. It now gets `LICENSE`,
  `CHANGELOG.md` and a real `uninstall.sh`, and the build refuses to continue without it.
- **The build rewrote a tracked file.** `sed -i` on `build/README.txt` dirtied the working tree after
  every build, and the next commit carried the previous version. The versioned copy is generated.
- **`docs/ALERTES.md` documented a command that no longer works**: `SLACK_WEBHOOK=… python
  veille.py --alerte` sends nothing, since the engine reads `WEBHOOKS` as a JSON list.

- **A corrupted state file no longer closes the door.** config.json truncated, secret.dpapi
  copied from another machine or written by another account, perimetre.json invalid: three
  ValueError, inascii.Error or OSError raised while the window was still being built, so the
  application refused to open and the user had no way to fix anything from the interface.

  The secret stays strict, deliberately: an altered blob must be visible. It is the caller that
  gives way. Settings fall back to the defaults, which brings the wizard back; secrets fall back to
  none, which makes the assistant ask for the password; an unreadable perimeter falls back to empty,
  which the page already knows how to report. Each fallback is journalled with its cause.

### Fixed

- **The immediate alert task stopped after one day on Windows.** Its trigger was a TimeTrigger
  with a repetition bounded to P1D: a time trigger fires once, so that duration bounded the only
  series it would ever start. Measured on 28 November 2026 with a two-minute equivalent: two runs,
  then Next run: N/A, and the task stays registered but never fires again. The alert task is
  installed for eight runs every three hours, so alerts would have died after its first day.

  The repetition is now unbounded, which the same experiment confirms: five runs in five minutes,
  next run still scheduled. The daily task keeps its two-hour retry window, since a
  CalendarTrigger renews it every day. The task installed on this machine was regenerated.

### Fixed

- **Five remarks from a Reddit review of `app.py`, all confirmed in the code.** The Slack webhook,
  the Discord webhook and the Telegram token were plain entries, readable on a shared screen or in
  a screenshot, while the SMTP password was masked; all four are masked now. A channel switched on
  with an empty address, a webhook without `https://`, or a Telegram token that does not look like
  one, is refused at save time instead of failing silently three days later; the rule lives in
  `config.canaux_invalides` so it can be tested without a window. `SDB_PAGE` replaces
  `SECDailyBrief_PAGE`, the old name still being read for existing scripts. "Erase my data" now
  erases what makes a reset a reset: history, seen articles, statistics and the generated reports,
  which it used to leave behind. And a comment said `endor/` where it meant `vendor/`.


- **The history showed every run twice, once finished and once failed.** The journal named the
  cause of the failure: Could not find a suitable TLS CA certificate bundle, six times in two
  days. The engine child process inherited the environment and 
equests did not always find its
  certificate bundle, so the run died in 0.1 s and nothing was sent.

  - the runner now sets REQUESTS_CA_BUNDLE and SSL_CERT_FILE from the certifi file the
    diagnostic already validates, and warns when it is absent;
  - two runs written in the same second with the same mode are merged, the worst status winning:
    they come from one launch seen by two processes;
  - the duplicates were not two processes at all: a test that walked through main() wrote into
    the real journal and the real history, because no conftest.py isolated the data directory.
    One now does, for every test: after a full suite, both files are byte-for-byte unchanged;
  - history entries carry their **origin** (interface, planificateur, ligne de commande),
    shown as a fifth column. The scheduled task now passes --planifie, so an automatic send can
    be told apart from a manual one. Without it, the duplicate was impossible to attribute.

Changes accumulate here between two versions. When one is cut, this section becomes the release notes and a new empty one takes its place: nothing gets lost, and nobody has to reconstruct what happened since the last tag.

## 1.7.7 , 27 November 2026

Changes accumulate here between two versions. When one is cut, this section becomes the release
notes and a new empty one takes its place: nothing gets lost, and nobody has to reconstruct what
happened since the last tag.

### Fixed

- **The daily report no longer accepts `javascript:` or `data:` links.** The alert renderer
  checked the scheme; the report did not, and rendered hrefs from five lists straight out of feed
  content. Escaping stops an attribute breakout, not a scheme: and the report opens in the
  browser. A crafted feed link now appears as plain text, and a test renders one to prove it.
- **A scheduling failure is no longer silent.** `_programmer` swallowed both exceptions: the user
  believed the task was installed, the panel said "no run yet", and nothing explained why. The
  failure now reaches the journal and the status line, in nine languages.
- **The diagnostic stopped announcing DPAPI on Linux**, where the secret lives in the desktop
  keyring or a `0600` file.
- **Hackmageddon failed on every run** with `unreadable feed`, and the report said so in its
  warning line. The feed is fine: its host closes the connection when the client accepts gzip,
  and answers normally when it asks for `identity`. The fetcher already retried with a reader
  agent; it now retries once more without compression. The source reads again.
- **The silent-source banner cried wolf on blogs.** A PSIRT that stops for two weeks is a
  problem; Bellingcat, DoublePulsar or watchTowr publishing monthly is not. Blogs now get 45 days
  before being reported, advisories keep 14. The line that listed six names for the wrong reason
  now lists only real silence.
- **The About window spoke English inside the French interface.** Its title and three labels had
  never been translated, and the title doubles as the panel button: so the bottom bar read
  `About` next to `Réglages` and `Faire un don`. It now reads `À propos`, `Moteur`, `Licence`,
  `Dépôt`, and a test fails if one of them goes back to the English string.

### Added

- **Dependabot and CodeQL.** Dependabot opens one grouped pull request a week for the Python
  dependencies and for the actions, so a vulnerable version is reported instead of being waited
  for. CodeQL reads the code on every push, every pull request and weekly, with
  `security-and-quality` queries: a dangerous pattern is now caught by a machine rather than by a
  reader's attention.

### Changed

- **The report gives the important five the room the unimportant ones were taking.** Measured on a
  real run: 126.5 KB of HTML before, 100.3 KB after, and the five priorities now fill 5 % of the
  message instead of 2 %.
  - the legend and the twenty-eight-country list became one footer link to `SOURCES.md`;
  - an item already listed under *Top priorities* is marked `↑ listed above` in its section
    instead of being detailed twice;
  - the IBM footprint keeps every country and its count, plus three examples, instead of 45 titles
    that all came from the sections above;
  - a description is printed only for a red item, and only when it says something the title does
    not; Red Hat repeated its title word for word;
  - commercial items (Black Friday, −78 %, robot vacuums) are filtered like any other off-topic.
- **Two off-topic articles the brief should never have carried.** *« Oui, on peut faire tourner
  macOS sur une base Linux »* passed because the relevance filter read the summary, where the word
  "securite" appeared; a CNIL guide passed because `cnil` was itself one of the threat keywords.
  Relevance is now judged on the title, `cnil` left the keyword list, and a new source option
  `require_any` admits a CNIL item only when it speaks of a sanction, a fine, a formal notice or a
  breach. Measured: 95.5 KB of HTML before, 90.2 KB after.
- The engine is re-pinned to `337b4f2`, which carries the relevance fix. It also reads the silence
  banner from the run in progress
  rather than from the database: the first run after the measurement change still named four busy
  feeds, because only a completed run could have written the new dates. With this, the banner is
  empty on a day when every feed answers.
- The previous re-pin, `1983983`, carries the report changes above and the
  silent-source and compression fixes (`e4932ae`). It also stops measuring a feed's silence on
  what we keep: CERT-EU, Microsoft Security, Dark Reading, SANS ISC and Unit 42 were reported
  silent for 33 days while all five had published within 48 hours: their items are filtered out,
  so no row was ever written, so a busy feed looked dead.

## 1.7.6 , 27 November 2026

This release exists because 1.7.5 does not say everything it should. Three defects shared one
cause: the interface knew a fact and looked for it in the wrong place.

### Fixed

- **"Check for updates" now hands you the checksum.** The dialog said a version was available and
  offered to open the releases page, leaving the reader to find `SHA256SUMS` alone: the step
  everyone skips. The GitHub API publishes a digest per asset, so the dialog now shows the SHA256
  of the archive built for this machine (Windows or Linux, portable or not), in a **selectable
  field**, because a message box cannot be copied from. When no digest is published, it points at
  `SHA256SUMS` instead of showing an empty box.
- **The About window read `Engine:?` in every released binary.** It looked for
  `vendor/engine.json` next to the executable, while PyInstaller stores it under `_internal/`.
  `engine.dossier()` knows the difference: the diagnostic used it, the window did not. The line
  now carries the pinned commit, and **disappears entirely** when the lock is unreadable: a line
  that announces "unknown" is a defect wearing a translation.
- **The About window pointed at the engine's repository.** `Repository` now opens this one.
- The French sentence in the update dialog no longer carries an em dash.

## 1.7.5 , 27 November 2026

### Added

- **The alert channels now explain themselves.** Discord, Slack and Telegram each carry a blue
  question mark: hovering shows one sentence about what to paste, in the nine interface
  languages, and clicking opens [docs/ALERTES.md](docs/ALERTES.md) at the right section. That
  page gives the exact menu path, three illustrations, and the errors that go with each channel:
  `401` for a wrong token, `403` for a bot that is not in the chat, and `discord.gg` addresses
  that look like webhooks but are invitations.
- The chat alert header now carries the time it was sent and no longer uses an em dash:
  `SecDailyBrief · 3 alerte(s) · 27/11 11:48`. Three days later in a channel, nothing said when
  the alert had gone out. (Engine commit `4e076dd`, re-pinned below.)

### Fixed

- **The About window announced version 1.0.0.** The number had been written by hand and never
  touched again, so the window contradicted the panel, the badge and the archive names. It now
  reads the package version, through a method that a test can check without opening a window.

### Changed

- The engine is re-pinned to `4e076dd` (238 453 bytes,
  `5f9d18f8f0c014b50406f07de1de161d084f7355e3b2cd5825db34db90705552`).

## 1.7.4 , 27 November 2026

### Fixed

- **The Linux archive would not start on Debian 13.** The frozen binary asked for `GLIBC_2.42`,
  which Debian 13 (2.41) does not provide: `ImportError: libc.so.6: version GLIBC_2.42 not found`,
  raised by the bundled `libtcl8.6.so`. The glibc a binary requires is the one of the machine that
  builds it, and the release job ran on `ubuntu-latest`, which has moved to 26.04 (glibc 2.42).
  The Linux job now builds on **ubuntu-22.04** (glibc 2.35), so the archive runs on Debian 12 and
  13, Ubuntu 22.04 and later, and any distribution with glibc ≥ 2.35.
- The build script now **measures** the glibc the binary requires and refuses to ship when it
  exceeds the ceiling set by `SDB_GLIBC_MAX` (2.35 in CI). A runner upgrade can no longer
  reintroduce this in silence: it breaks the build instead of the user's first launch.

Reported by CoreInfini7y in [#5](https://github.com/Hormerty/SecDailyBrief/issues/5), with the
exact traceback and operating system.

### Fixed: navigation

- **"Back" no longer leads deeper into the wizard.** Opened from **Settings**, the assistant
  started on the mail page and its "Back" button went up to the consent page, then to the
  language page, which has no way out: the panel became unreachable, and the alert channels,
  which sit at the end of the walkthrough, could not be reached at all.
- **An "Alerts" button in the panel** opens the channel page directly. Changing a Discord
  webhook took a full walkthrough before; it now takes one click.
- **Going back from the channels page keeps what was typed.** The webhook addresses were re-read
  from the secret file, which had not been written yet, so leaving and returning emptied them.

## 1.7.3 , 26 November 2026

### Fixed

- The panel's **« Sources »** and **« Liens »** buttons did nothing in the released binary. The
  frozen application passes `--check-feeds` or `--check-links` to itself before handing the work
  to the engine, but its argument parser did not know those flags and rejected them with
  *unrecognized arguments*. They are now accepted and dispatched to `check_feeds()` or
  `check_links()`. Verified on the rebuilt binary: the check starts and queries the feeds.
- Those two buttons also demanded an SMTP password before running, although neither sends
  anything: and a missing password showed a mail error. Only `--run` and `--alerte` ask for it
  now; the rule lives in `runner.exige_mot_de_passe` and is tested.
- Building the environment no longer raises when no configuration exists yet: the sources check
  must be usable on a fresh install.

## 1.7.2 , 26 November 2026

### Fixed

- The Linux archive weighed twice the Windows one: 30,9 MB against 15,9 MB. The cause was not
  the platform: the Python shared library shipped by the CI runner (3.12) is not stripped, and
  carried 28 MB of symbol tables, most of the archive. `build.sh` now passes `--strip`, which
  takes that same library to 6 MB. The frozen binary is still executed after the build, so a
  broken library would be caught before the archive is published.

## 1.7.1 , 26 November 2026

### Added

- The diagnostic gained an eleventh check on Linux: **does the user systemd manager outlive the
  session?** A timer for 06:00 is installed, enabled and reported "active": and never fires,
  because `systemctl --user` stops its manager as soon as no session is open. `Linger=no` is
  silent, so the check says it, with the command that fixes it
  (`loginctl enable-linger <user>`).
- Inside WSL the check takes another tone: the distribution stops itself when nothing runs, so
  no setting makes scheduling reliable there. WSL is a place to test, not to plan.

## 1.7.0 , 26 November 2026

### Added

- **Linux**, built and tested on a real Ubuntu 26.04 inside WSL: not merely compiled in CI.
  The platform layer holds one implementation per system: DPAPI or the desktop keyring for
  secrets, a named mutex or `flock` for the single-instance lock, `%APPDATA%` or XDG for the
  data folder, `schtasks` or systemd timers for the schedule.
- The scheduler converts the same task XML into systemd units, so the two platforms share one
  description. The conversion knows that the daily task's `Repetition` of `PT15M` is Windows'
  catch-up window, not a quarter-hourly cadence: only a `TimeTrigger` becomes a periodic timer.
- `build/build.sh`, mirroring `build.ps1` with the same guards: including the refusal to
  produce an archive without `cacert.pem`.
- The release workflow now builds on both systems and publishes four archives with a single
  `SHA256SUMS`.

### Fixed

- The diagnostic announced "profil Windows" as the data folder whatever the system.
- `prochaine_execution()` called PowerShell with Windows creation flags on Linux, raising
  `ValueError` the first time a timer was actually installed.
- `.gitattributes` protected `.py`, `.md` and `.txt` from the CRLF conversion but not `.sh`:
  `build.sh` arrived with Windows line endings and bash refused `set -euo pipefail`.

All three were found by running the application on Linux, and were invisible to 135 passing
tests.

## 1.6.0 , 26 November 2026

### Added

- **Alerts can now reach Slack, Discord or Telegram**, not only the mailbox. Each channel is a
  checkbox of its own, and the wizard grew the fields they need: a webhook URL for Slack and
  Discord, a bot token and a chat id for Telegram.
- The chat message is short by design: a heading, one line per flaw with its score and source,
  the link underneath, and how many remain for the next pass. The daily report stays on mail: a
  144 KB digest in a chat window would only be scrolled past.
- Webhooks travel in the same DPAPI file as the SMTP password, never in `config.json`, because a
  webhook URL is enough to post.

### Notes

- If the mailbox is unchecked while no webhook is configured, the mail takes over again: a lost
  alert is worse than a redundant one.
- Slack wants `{"text": …}`, Discord wants `{"content": …}`, Telegram wants a token and a chat
  id: three shapes for one message, each covered by a test.

## 1.5.1 , 26 November 2026

### Changed

- The alert run no longer reads all 124 feeds. Measured over a real pass, it cost **43,5 MB**
  and about four minutes every three hours, two thirds of it for three hosts (elastic.co
  8,26 MB, MSRC 3,13, a FeedBurner aggregator 2,79) and a hundred blogs.
- It now reads the national CERT feeds, the three technical bodies without a country, and the
  services that feed its scoring: **10,94 MB** measured.
- Restricting it to CERTs was not enough: of the eleven report lines naming the author's stack,
  none came from a CERT; they came from Cisco PSIRT and Microsoft MSRC. The alert therefore
  also keeps the **vendor advisory feeds whose name matches a product in the stack**: PSIRTs,
  never blogs. Two feeds for this stack, 3,3 MB, so **14,2 MB** per run: two thirds less than
  before, with the keywords still covered.

## 1.5.0 , 26 November 2026

### Added

- **Immediate alerts, every three hours.** The engine has carried this mode since the bot's
  first version: a higher threshold, an eight-hour window, five items per mail, its own state
  file and a first-run seed that avoids a burst of messages. When the watching moved into this
  application, only the daily report was carried over: the alert workflow was left behind, and
  a critical flaw waited for the next morning. A second scheduled task,
  `SecDailyBrief-Alerte`, now runs the mode every three hours, and the wizard gained a checkbox
  to turn it on or off.

  The cost is real and deliberate: a full collection lasts about five minutes, so eight runs a
  day. In exchange, a flaw above the alert threshold reaches the mailbox within three hours.

- The diagnostic now says whether the alert task exists, so a user cannot believe they receive
  alerts that were never scheduled.

### Fixed

- `--alerte` called the engine's daily-report function. The engine chooses between the two in
  its own `__main__` block, which the frozen executable never enters, so the choice has to be
  made by the application: and it was not. The consequence was not cosmetic: testing the mode
  on a fresh data directory **sent a real daily report to the author's mailbox** on 26 November.
  The application now calls `main_alert()` explicitly, and a regression test asserts which
  function each mode reaches.

## 1.4.4 , 26 November 2026

### Added

- **CISA SSVC decisions** now drive the ranking. The engine used to infer exploitation from
  wording ("exploitation active", "dans la nature") and missed any source phrasing it
  differently. CISA Vulnrichment states it per CVE: Exploitation (none / poc / active),
  Automatable, Technical Impact. Entries carrying an `active` decision gain five points and a
  ⚔️ badge, a proof of concept two points and 🧪, automatable and total impact one point each.
  On the first real run: 27 CVEs read, 12 articles raised.

The lookup is bounded to forty CVEs per run, taken from the highest-scoring articles, and
cached: including "the CISA has not ruled", so a silent CVE is not asked twice.

## 1.4.3 , 25 November 2026

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

## 1.4.2 , 25 November 2026

### Added

- **NCSC Ireland** joins the national CERT feeds. It publishes in English, with CVE
  identifiers, which makes it the simplest source added so far: no phrase table, no
  translation to keep up.

## 1.4.1 , 25 November 2026

### Added

- **Nine national CERT feeds** reach the application: Italy, Luxembourg, Austria, Norway,
  Finland, Hungary, Romania, Slovakia and Spain. Their titles are translated to English:
  eleven phrase tables, plus pattern rewriting where the product sits in the middle of the
  sentence (Hungarian, Romanian, Slovak).
- The **first `SHA256SUMS` file** is attached by the release workflow: one file, produced from
  the archives themselves, instead of checksums typed into the release notes.

### Changed

- The engine is re-pinned to `92e752d`, which carries the CERT work, the corrected source
  error messages, and `SOURCES.md`: the inventory of which CERT is covered and why the others
  are not.

### Fixed

- An accented character from the engine lost its accent in the journal (`NVD (�diteurs)`). The
  child's output is decoded as UTF-8, then as the Windows code page when that fails, instead
  of being replaced silently.
- A source in error now says **why** ("délai dépassé", "injoignable", "HTTP 403") instead of
  pasting a Python exception into the daily mail.

## 1.4.0 , 24 November 2026

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

## 1.3.0 , 24 November 2026

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

## 1.2.1 , 24 November 2026

### Fixed

- The `README.txt` inside the archive announced version 1.1.0 in the 1.2.0 package. The
  title is now written by the build script from the package version, and the script reads
  the copied file back before packaging: a line maintained by hand does not follow the
  version, and this one did not.

## 1.2.0 , 24 November 2026

### Added

- **German, Spanish and Italian.** The interface now speaks six languages; a system set to
  any of them lands on it directly instead of falling back to English. The report itself is
  still written in English: only the application is translated.
- **Saved settings are checked at startup**, like the perimeter file. A `config.json` edited
  by hand used to stay wrong until the next run; it is now named at launch, with an offer to
  open the page that fixes it. The settings are never reset: that would erase the address.

### Changed

- The version is checked at build time across the package, the Windows properties and
  `pyproject.toml`, and publishing is done by a workflow rather than from a workstation.

## 1.1.0 , 24 November 2026

### Added

- **Portable mode**: a second archive, marked with `portable.flag`, whose data lives in a
  `data` folder next to the executable instead of the Windows profile. The diagnostic reports
  the current mode, because the difference matters: in portable mode, deleting the folder
  also deletes the settings.
- **Seven-day history**, reachable from the panel: date, mode, status and duration of each
  run, without digging through the log.
- **Strict validation of the perimeter file** at startup. The faulty section is named:
  unknown section, `stack` as a list, empty keywords: and the example values can be
  restored. The faulty file is kept as `.invalide` rather than destroyed.
- Run statuses are translated in the status line and in the history.

### Changed

- **The version is checked at build time**: the package, the Windows properties and
  `pyproject.toml` must agree, or the build stops. Three copies of the same truth always end
  up diverging.
- The "Buy me a coffee" button uses the normal weight, like the others.

### Fixed

- The consent setting is no longer asked again on every return to the page.

## 1.0.0 , 23 November 2026

First usable version.

- Five-page wizard: language (FR/EN/NL), consent, sending account, stack, schedule.
- Control panel: run, preview, open the report, test sources, check links, log, diagnostic,
  history.
- Sending verified by a real message before saving; password encrypted by Windows.
- Daily scheduled task, with catch-up if the machine was off.
- Ten-point diagnostic, including the engine's ability to actually import and the presence
  of the TLS certificates.
- Engine embedded at a pinned commit, with its checksum verified on every build.
