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

## Read the diff, as a stranger

The gate runs code. It cannot see a webhook shown in clear on a shared screen, a field saved
without validation, or a comment that no longer describes the function under it. Five such remarks
arrived from a Reddit review of pp.py and none of them would ever fail a test.

So before the tag, read what changed since the last one, with this checklist in hand:

1. a secret that can become visible (an entry without show, a token in a log line, a value in
   config.json instead of the encrypted file);
2. a field saved without validation, where a typo fails silently three days later;
3. an inconsistency with the file's own conventions;
4. a destructive operation that does not destroy what its label promises;
5. a typo, or a comment that no longer matches the code;
6. a swallowed exception that hides a real failure.

Everything mechanisable in that list is already a test: 	ests/test_relecture.py refuses an entry
of a secret without show=, a credential in a log line, an environment variable in mixed case, an
except Exception: pass without its 
oqa, and a known typo in a comment. It runs with the suite,
so it runs on every commit and, therefore, before any tag. The six categories that remain need a
reader: not a linter, a person or an agent who has not written the lines.

Delegating that read to a fresh agent is worth the two minutes: whoever wrote the line will read
what they meant, not what is written.

## A test must fail when the intent breaks

A test that asserts the value the code currently produces protects the code, including its defects.
This one did:

```python
assert "<Duration>P1D</Duration>" in xml      # it required the bound that killed the task
```

It stayed green while the Windows alert task stopped after one day. The corrected test asserts the
property that matters, `assert "<Duration>" not in xml`, and the reason is in its docstring.

So the rule is not "write a test", it is: **break the intent once and watch the test fail**. Revert
the fix in a scratch copy, run the suite, require a red line. A test that stays green when the
behaviour it describes is removed is a comment with a syntax.

Two habits follow:

- assert the **property**, not the output. `assert "<Duration>" not in xml` survives a change of
  interval, version or order; `assert "<Duration>P1D</Duration>" in xml` does not.
- when a literal is unavoidable, derive it from an exported constant (`schedule.HEURES_ALERTE`)
  rather than retyping it. A retyped value drifts silently.

`tools/relire_tests.py` lists the assertions that still copy a value or a sentence from the source.
It is a triage report, not a verdict: an environment variable name, an XML element name or a footer
belong to the contract and appear on both sides legitimately.

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
