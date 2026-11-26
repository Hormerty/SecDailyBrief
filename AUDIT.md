# Audit — 26 November 2026

Two repositories, two programs: the engine (`veille.py`) and the desktop application that wraps
it. This audit records what was measured, not what was intended. Every figure below comes from a
command run on the day.

## What the two repositories contain

| | `Hormerty/SecDailyBrief` | `Hormerty/Sec_Daily_report-` |
|---|---|---|
| Role | desktop application, packaging, releases | the engine alone, used by GitHub Actions |
| Language | Python 3.12 | Python 3.12 |
| Size | 21 modules, 4 002 lines | one file, 238 KB |
| Tests | 135 test functions | 65 functions, 103 cases once parametrised |
| Branches | `main` = `95f2db3` | `main` = `42272bd` |
| Latest release | `v1.6.0`, two Windows archives + `SHA256SUMS` | none — the engine ships inside the application |
| Licence | MIT | MIT |
| Stars | 9 | 7 |
| Open issues / PRs | 0 / 0 | 0 / 0 |

The engine is pinned inside the application by commit **and** SHA256 (`vendor/engine.json`,
`42272bd`, 238 208 bytes), and `--verify` refuses a file that does not match. That mechanism is
what keeps the two repositories honest with each other.

## State of the code

- **Versions agree** in all three places that carry one: `__init__.py`, `pyproject.toml`,
  `build/version.txt` (`1.6.0`).
- **No secret was ever committed.** Searching the full history of both repositories for
  `github_pat_` and `ghp_` returns zero occurrences.
- **Runtime artefacts stay out of git.** `seen.json`, `stats.db`, `kev_cache.json`,
  `ssvc_cache.json`, `alertes_envoyees.json` and `metasploit_cache.json` are ignored; only
  `config.example.json` is tracked, deliberately.
- **No dead `TODO`** in the engine: the seven matches were folder names (`26xxx`).
- **Windows references left in the application** are the intended ones: `schtasks` inside the
  Windows branch of `schedule.py`, and the `%APPDATA%` fallback in `paths.py`.
- **21 broad `except Exception`** in the application, each annotated `noqa: BLE001`. Most are
  justified — a failing doctor check must not stop the others — but three swallow a failure
  completely (see finding 5).

## Findings

### 1. The Linux binary has never been run — high

The abstraction, the systemd units and `build.sh` are written and their tests pass on
`ubuntu-latest`, but no binary has ever been produced for Linux, and nothing has run under
`systemctl --user`. The build script and the release workflow exist; neither has been exercised.

**Consequence:** publishing a 1.7.0 today would ship an untested Linux archive. That is the
1.4.3 mistake — an archive without `cacert.pem` — waiting to happen again.

**Recommendation:** install WSL2, run `build/build.sh` there, launch the application, check the
wizard and `systemctl --user list-timers`. Only then cut the release.

### 2. A plain-text token, and backup codes, on the system drive — high

`D:\jeton-secdailybrief.txt.txt` holds a fine-grained token with `Contents: write` and
`Pull requests: write`. Next to it, `D:\stripe_backup_code.txt` and `D:\bmc-backup-codes.txt`
hold recovery codes in clear text.

**Recommendation:** revoke the token once the Linux port is published, and move the backup codes
into a password manager. Nothing here belongs to the repositories, but both are one screenshot
away from being exposed.

### 3. No dependency monitoring in the application — medium

The engine repository has a `dependabot.yml`; the application has none, and `tzdata` is declared
without a version. Dependencies are `requests==2.34.2`, `feedparser==6.0.14`, `tzdata`,
`pytest==9.1.1`, `pyinstaller==6.22.3`.

**Recommendation:** copy the engine's `dependabot.yml`, and pin `tzdata`.

### 4. No code scanning in either repository — medium

Neither repository runs CodeQL, and only the engine has a secrets scanner (gitleaks, wired as a
pre-commit hook and in `verifier.yml`).

**Recommendation:** add CodeQL to both. It costs nothing on public repositories and catches the
class of defect that unit tests do not.

### 5. Three failures are swallowed without a trace — medium

`app.py::_programmer` wraps task installation in a bare `except Exception: pass`, twice. If
`scheduled tasks` refuses the task, the user sees nothing; the wizard closes and the application
looks configured. The doctor partially compensates — it reports whether the task exists — but
only if the user opens it.

**Recommendation:** journal the exception before swallowing, and show the alert state in the
panel rather than only in the doctor.

### 6. The Linux secret fallback is weaker, and the doctor does not say so — medium

Under Linux, `secret-tool` is used when present; otherwise the secret is stored base64 with
`0600` permissions. That is reversible by anyone who can read the file, unlike DPAPI. The
behaviour is documented in `plateforme/linux.py`, but the diagnostic still announces
`Certificats TLS` and `Mot de passe` without saying which backend is in use.

**Recommendation:** add a doctor check naming the backend (`DPAPI`, `Secret Service`, `fichier
0600`).

### 7. Cosmetic naming — low

`paths.chemin_secret()` still returns `secret.dpapi` on every system. The name now describes a
Windows mechanism only.

## What is healthy

- **CI runs on both systems** since today, with `xvfb` so the interface tests open a window on
  Linux. 135 tests pass on Windows and on Linux.
- **Releases are reproducible**: built on a runner, the tag must equal the package version, and
  `SHA256SUMS` is computed from the artefacts rather than typed by hand.
- **The engine cannot drift**: pinned by commit and checksum, verified before every build.
- **The source inventory is written down** (`SOURCES.md`): 124 feeds, the 20 covered countries,
  the four gaps, and every aggregator examined and refused with its measurements.
- **Alerting is redundant by design**: mail, Slack, Discord and Telegram, each optional, with
  mail as the fallback when no channel is configured.

## Priority order

1. Test the Linux build in WSL, then publish or do not publish.
2. Revoke the merge token; move the backup codes.
3. Add `dependabot.yml` to the application; pin `tzdata`.
4. Journal the swallowed failures in `_programmer`.
5. Add a doctor line naming the secret backend.
6. Add CodeQL to both repositories.
