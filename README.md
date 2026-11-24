# SecDailyBrief

A daily security brief by e-mail, built for your own stack.

This Windows application drives the watch engine of the
[`Sec_Daily_report-`](https://github.com/Hormerty/Sec_Daily_report-) repository **without
modifying it**: the engine is fetched at a pinned commit, its checksum is verified, and the
configuration is injected from the outside.

> **Version 1.4.0** — in two archives:
> `SecDailyBrief-1.4.0-win64.zip` (data in the Windows profile) and
> `SecDailyBrief-1.4.0-win64-portable.zip` (data beside the executable).
> The interface speaks French, English, Dutch, German, Spanish, Italian, Portuguese, Hindi and Chinese.

## Installation

1. Download an archive from the [published releases](../../releases/latest).
2. Extract it wherever you like, then run `SecDailyBrief.exe`.
3. The wizard asks for your language, your sending address and an app password — not your
   usual password. For Gmail: <https://myaccount.google.com/apppasswords>.
4. The **Test sending** button checks the configuration before saving it, then **Finish**
   creates the daily scheduled task.

The executable is not code-signed: Windows will show "Windows protected your PC" on first
launch. This is accepted, and documented in the `README.txt` inside the archive.

No Python installation is required: the executable embeds its own interpreter. The archive
has been installed and run end to end on a clean Windows, without Python and without any
development tooling.

### Antivirus

The executable is not code-signed — a deliberate choice — and a PyInstaller binary that
relaunches itself to do its work trips several heuristic rules at once. Some scanners hold or
block it on first launch; Avast calls this CyberCapture, or a false positive.

Nothing is hidden in the file, and every release publishes the checksums of its archives.
Three ways out, in order of preference:

1. **Report a false positive** to the vendor. For Avast:
   <https://www.avast.com/false-positive-file-form.php>. This fixes it for every user, not
   only for you.
2. **Add an exclusion** for the folder holding `SecDailyBrief.exe`. The scheduled task runs
   that same file, so one exclusion covers both the manual runs and the daily one.
3. **Check the checksum** before allowing it. Every release carries a `SHA256SUMS` file
   produced by the build itself:

   ```powershell
   Get-FileHash .\SecDailyBrief-1.4.0-win64.zip -Algorithm SHA256
   ```

   Compare it with the line in `SHA256SUMS`. Download only from the
   [official releases page](../../releases) — a copy hosted elsewhere may have been altered.

## What it does

Every morning, an e-mail that gathers the day's security advisories, ranks the most critical
ones, and keeps only what touches your stack. The engine queries around a hundred public
sources, deduplicates, and produces both an HTML and a text report.

The program does not run continuously: it wakes up, works for one to two minutes, then stops.
No account, no intermediary server, no telemetry.

## Principles

- **Nothing is changed on the engine side.** `vendor/veille.py` is downloaded at a precise SHA
  and watched by a checksum; the stack and the configuration are injected from the
  application, before `main()` is called.
- **No monitoring of your machine.** The application reads public feeds and sends an e-mail.
  It reads no document, captures nothing, and transmits nothing to its author.
- **Your settings stay with you**, in `%APPDATA%\SecDailyBrief`, and are erased from the
  application itself.

## Development

```bash
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt

.venv\Scripts\python.exe tools\fetch_engine.py --sha <commit>   # fetch the pinned engine
.venv\Scripts\python.exe tools\fetch_engine.py --verify         # replay the checksum check

.venv\Scripts\python.exe -m pytest -q
```

### Packaging

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File build\build.ps1
```

The script first verifies the engine checksum — a binary embedding an altered engine would be
undetectable once shipped — then produces `dist\SecDailyBrief\` and **two** archives:
`SecDailyBrief-<version>-win64.zip` and `SecDailyBrief-<version>-win64-portable.zip`.
The second one contains a `portable.flag` file that makes the data live in a `data\` folder
beside the executable. Both contain the executable, `README.txt`, `uninstall.ps1`, `LICENSE`
and `CHANGELOG.md`.

The script refuses to build if the three version declarations disagree — the package, the
Windows properties of the `.exe` file, and `pyproject.toml`.

### Versioning

Three numbers, one rule each:

| Bump | When | Command |
|---|---|---|
| **patch** — `1.4.0` → `1.4.1` | a fix, or added translations | `tools/bump_version.py patch` |
| **minor** — `1.4.1` → `1.5.0` | a new visible capability | `tools/bump_version.py minor` |
| **major** — `1.5.0` → `2.0.0` | a change that breaks existing data or configuration | `tools/bump_version.py major` |

Language additions are patches, not minor releases: the interface gains a dictionary, the
program does not change.

```powershell
.venv\Scripts\python.exe tools\bump_version.py patch --dry-run
.venv\Scripts\python.exe tools\bump_version.py patch
```

The script writes the version in all four places that carry it — the package, `pyproject.toml`,
the Windows properties of the executable, and the title of the archive README. Hand-editing
those four is how 1.2.0 shipped with a README announcing 1.1.0.

### Continuous integration

Two workflows live in `.github/workflows/`:

- **`tests.yml`** runs the suite on every push and pull request, after checking the engine
  checksum.
- **`release.yml`** runs on a `v*` tag: it rebuilds both archives on a Windows runner,
  refuses to continue when the tag and the package version disagree, and attaches them to the
  release.

Publishing therefore does not depend on a particular workstation. `SDB_PYTHON` and
`SDB_SORTIE` let `build.ps1` use another interpreter and write elsewhere.

### Encoding

Everything is read and written as explicit UTF-8. Two traps met for real, and how each was
handled:

- **Windows PowerShell 5.1** — the one Windows still ships — reads and writes ANSI by
  default. A `Get-Content` / `Set-Content` round trip on a UTF-8 file corrupts it
  (`é` becomes `Ã©`). A source file is never rewritten through this shell: use an editor, or
  an explicit `-Encoding UTF8`.
- **The BOM** — Notepad and `Out-File` produce one, and `json` rejects it. The configuration
  file is therefore read as `utf-8-sig`, which accepts it as well as its absence.

In the code, every `read_text` / `write_text` carries its encoding, and console output goes
through `PYTHONIOENCODING=utf-8` whenever it contains anything beyond ASCII.

## Licence

MIT — see `LICENSE`.

Developed by Hormerty · © 2026
