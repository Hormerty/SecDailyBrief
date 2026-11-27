# Audit

Second pass, 27 November 2026. The first was on 26 November and is summarised here with its
outcome; findings 5 and 6 are closed, one new vulnerability class was found and fixed.

## What the two repositories contain

| | `Sec_Daily_report-` | `SecDailyBrief` |
|---|---|---|
| Role | watch engine: 124 feeds, collectors, report, alerts | desktop application: wizard, panel, scheduling |
| Tests | 110 | 160 |
| Language | Python | Python, tkinter |
| Licence | MIT | MIT |

The application pins the engine by commit and SHA-256 (`vendor/engine.json`), verifies the checksum
before every build and every run, and never writes to it.

## State of the code

- Three releases on 27 November (1.7.4, 1.7.5, 1.7.6), 19 tags in total.
- CI: `tests.yml` runs on Windows and Linux for every push; `release.yml` builds four archives on
  two runners, refuses to publish below glibc 2.35, and makes the publication re-runnable.
- 66 tracked files, 92 commits, three stale local branches left from the Linux port.

## Findings at a glance

| # | Finding | Severity | Status |
|---|---|---|---|
| 1 | The Linux binary had never been run | high | resolved 26 Nov |
| 2 | A plain-text PAT and backup codes in a pCloud-synced folder | high | **resolved 27 Nov** |
| 3 | No dependency monitoring | medium | **fixed 27 Nov** |
| 4 | No code scanning in either repository | medium | **fixed 27 Nov** |
| 5 | Scheduling failures swallowed in silence | medium | **fixed 27 Nov** |
| 6 | Doctor announced DPAPI on Linux | medium | **fixed 27 Nov** |
| 7 | `secret.dpapi` names a Windows mechanism | low | open |
| 8 | `javascript:` and `data:` links in the daily report | low to medium | **fixed 27 Nov** |
| 9 | Secrets passed to the child process in its environment | low | open, documented |
| 10 | `tzdata` is not pinned | low | open |
| 11 | No `SECURITY.md` | process | open |
| 12 | Three stale local branches | housekeeping | open |

### 3 and 4. Dependency monitoring and code scanning, fixed

dependabot.yml opens one grouped pull request a week for pip and for the actions, in this
repository; the engine already had its own. codeql.yml runs on push, on pull requests and
weekly, with security-and-quality queries, in both repositories.

Both analyses ran on 27 November. Once a fine-grained token with **Code scanning alerts: Read**
was in place, the alerts could be read:

| | Alerts | Errors | Warnings | Notes |
|---|---|---|---|---|
| SecDailyBrief | 13 | **0** | 3 | 10 |
| Sec_Daily_report- | 10 | **0** | 2 | 8 |

Two errors were found and fixed the same day: a secret-tool call with a keyword argument the
function does not take (a TypeError on every Linux desktop with libsecret, when saving the
password), and a test fixture's possibly-uninitialised variable.

What remains is note-level, except three warnings which are false positives or test-only:
py/implicit-string-concatenation-in-list (long strings split across lines inside one list
element, with their commas), and py/incomplete-url-substring-sanitization in a test.

### 2. Credentials in a cloud-synced folder, partly resolved

D:\ is a data drive **synchronised with pCloud** — the first version of this audit called it the
system drive, which was wrong, and missed the part that matters. The drive's inherited ACL also
gave Authenticated Users and BUILTIN\Users the right to **modify** whatever it contained.

So the personal access token and the two sets of recovery codes were being uploaded to a cloud
account, on files any local account could read and rewrite.

What was done on 27 November:

- the token was revoked in GitHub, and the API answers 401 since;
- stripe_backup_code.txt and mc-backup-codes.txt were moved to
  C:\Users\itsan\AppData\Roaming\clefs-sensibles\, whose ACL now grants the owner alone;
- the revoked token file was left in place for its owner to clean, since the token inside is dead.

Then the codes were regenerated, stored in **Proton Pass**, and both local copies deleted: the
files in clefs-sensibles were only a staging area. The token is the last plain-text secret on
disk, deliberately, because it is what pushes to GitHub; its ACL names the owner alone and it sits
outside any synced folder.

Moving a file out of a synced folder does not remove it from pCloud's trash or version history, so
the regeneration was the fix, not the move — and the old GitHub token is dead, not merely deleted.

### 5. Scheduling failures swallowed, fixed

`_programmer` wrapped both task installations in `except Exception: pass`. A failure meant the user
believed the brief was scheduled, the panel displayed "no run yet", and nothing said why. Each
failure now goes to the journal and to the status line, in the nine interface languages.

### 6. Doctor announced DPAPI on Linux, fixed

The diagnostic reported "chiffré DPAPI" whatever the platform, while Linux stores the secret in the
desktop keyring or, failing that, a `0600` file. It now says what is actually there.

### 8. Link schemes, fixed

The alert renderer checked that a link started with `http://` or `https://`; the daily report did
not, and rendered `href="{escaped}"` for five different lists. Escaping protects against breaking
out of the attribute, not against the scheme itself: a feed announcing
`javascript:alert(document.domain)` produced a working link in the report, which the application
opens in the browser ("Ouvrir le dernier rapport"). The origin is `file://`, so the impact is
limited — but the content came from outside, and the defence existed ten lines away.

`_lien_html()` now guards every site; a test renders an article whose link is `javascript:` and an
`also_covered` entry with `data:text/html`, and asserts neither appears.

### 9. Secrets in the child environment

`runner.environnement()` passes `EMAIL_PASSWORD`, `WEBHOOKS` (which contains Discord and Slack
URLs and the Telegram token), `NVD_API_KEY`, `RANSOMWARE_API_KEY` and `GITHUB_TOKEN` to the engine
process through its environment. On Linux, `/proc/<pid>/environ` is readable by the same user
while the run lasts; on Windows, another process of the same user can read the block.

Severity is low because that attacker already has the encrypted secret file *and* the DPAPI or
keyring material to open it. It matters for crash dumps and process monitors, not for privilege
escalation. A pipe or a `0600` temporary file would remove the exposure; not done.

## Security testing performed on 27 November

| What | Method | Result |
|---|---|---|
| Dependencies | OSV query for `requests==2.34.2`, `feedparser==6.0.14`, `pyinstaller==6.22.3`, `pytest==9.1.1` | 0 known vulnerabilities |
| Link injection | crafted feed entry, rendered report | vulnerable, now fixed and tested |
| Shell injection | review of the 6 `subprocess` sites | all use argument lists, no `shell=True` |
| HTML injection | review of every feed-derived string | escaped, except the scheme gap above |
| Secrets in history | scan of 92 commits for tokens and webhook URLs | nothing but a documentation example |
| Secret storage | DPAPI on Windows, `0600` file or keyring on Linux | confirmed by the diagnostic |

## What this audit does not cover

- **No fuzzing**, no black-box network testing, no Windows kernel-level review.
- **No certification about unknown flaws.** The exposed surface is a network client that parses
  remote XML and a local GUI; both are small, but "no 0-day" is not a claim anyone can make.
- The engine's parsers trust `feedparser` for XML: no explicit XXE or entity-expansion review was
  performed.

## What is healthy

- No secret in the repository or its history; webhooks stay in the encrypted file and never reach
  `config.json`.
- No `shell=True`, no `eval`, no `pickle`, no `yaml.load`.
- Every HTML insertion escapes; every SQL statement is parameterised.
- The engine is pinned by checksum, and a modified `vendor/veille.py` is detected.
- The update check downloads nothing: it opens the releases page and shows the checksum of the
  archive built for the machine.

## Priority order

1. Finding 2 (move the token and the backup codes off the system drive) — the only high one.
2. Findings 3 and 4 (Dependabot, CodeQL) — mechanical, and they catch the next two findings.
3. Findings 9 and 10 — small, and they close the "secrets" chapter.
4. Findings 7, 11, 12 — naming and housekeeping.
