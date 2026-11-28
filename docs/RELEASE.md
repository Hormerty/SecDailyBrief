# Before publishing a version

The audit is not a report written after the fact. It is a gate: a version does not leave while a
check fails, and a failed check is fixed or explained in the changelog before the tag exists.

Three defects reached a published release because this page did not exist: an update that showed
no checksum, a report that named four busy feeds as silent, and a history window that listed every
run twice. Each was visible in a place nobody read.

## The order matters

The application vendors the engine and verifies its SHA-256, so the engine goes first. A re-pin of
an unpushed commit is impossible: `fetch_engine` reads GitHub, not the working tree.

```powershell
# 1. the engine: commit, push, note the short SHA
cd "D:\Security Code GitHub\Sec_Daily_report-"
git status --short          # must be empty
git push origin main
git rev-parse --short HEAD

# 2. the application: re-pin and verify
cd "D:\Security Code GitHub\SecDailyBrief"
.venv\Scripts\python.exe tools\fetch_engine.py --sha <sha>
.venv\Scripts\python.exe tools\fetch_engine.py --verify

# 3. both suites
.venv\Scripts\python.exe -m pytest -q
cd "D:\Security Code GitHub\Sec_Daily_report-"
"D:\Security Code GitHub\SecDailyBrief\.venv\Scripts\python.exe" -m pytest tests/test_veille.py -q
```

## The gate

```powershell
cd "D:\Security Code GitHub\SecDailyBrief"
$env:PYTHONPATH = "D:\Security Code GitHub\Sec_Daily_report-"
.venv\Scripts\python.exe tools\audit_sortie.py            # journal, documentation, dead sources
.venv\Scripts\python.exe tools\audit_sortie.py --reseau   # plus every feed
```

It answers three questions no test asks:

| Question | Why it exists |
|---|---|
| Does an error repeat in the seven-day journal? | 83 traces of a certificate failure had accumulated unnoticed |
| Does `SOURCES.md` still describe the code? | it claimed EUVD was refused while `collect_euvd` runs |
| Has a source stopped producing? | 01net kept 0 of 30 items and nothing said so |

Exit code 1 means something must be read before publishing, not necessarily something broken: an
error whose last occurrence predates its fix is history, an error whose last occurrence is today is
a defect.

## What cannot be automated, and is therefore read by hand

- **A preview.** Run the engine and open the HTML. Numbers that look wrong are found by looking,
  not by asserting.
- **The changelog.** Read the `Unreleased` section as a user would: does each line say what
  changed for them, not what file was touched?
- **The four archives**, after publication: `SHA256SUMS` matches, and both Linux archives answer
  `--doctor` with the new engine commit.

## After the tag

```powershell
git tag -a vX.Y.Z -m "SecDailyBrief X.Y.Z" && git push origin vX.Y.Z
gh run watch                      # linux, windows, publier
gh release view vX.Y.Z --json assets
```

The release turns into a draft when a tag is moved after publication. If that happens,
`gh release edit vX.Y.Z --draft=false` and republish with `upload --clobber`.
