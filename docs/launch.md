# Launch kit

Texts ready to post, and the exact patch for the awesome list. Everything is in English, because
the audience is.

## Status

| What | Where | Since |
|---|---|---|
| awesome-threat-intelligence | [PR #519](https://github.com/hslatman/awesome-threat-intelligence/pull/519) — 2 commits, +8/−0, no conflict | 26 November 2026 |
| Reddit announcement | not posted yet | — |

The list merges roughly one pull request per quarter and has 154 open: the PR is likely to sit for
months. The link from its README only exists once merged — until then, the announcement is what
brings visitors.

## Reddit — r/cybersecurity (or r/blueteamsec)

**Title**

```
I got tired of reading 124 security feeds every morning, so I wrote the brief I wanted to receive
```

**Body**

```
Every morning I opened the same twenty tabs: CERT-FR, BSI, the Dutch NCSC, CISA, the vendor
PSIRTs. Half of it never concerned me, and the one advisory that did was buried under yesterday's
news.

So I built SecDailyBrief. It reads 124 feeds — including 20 national CERTs — ranks what it finds
against the products I actually run, and sends one e-mail at 06:00.

Three things ended up mattering more than I expected:

- **Foreign CERTs are translated.** CERT-FR, CERT Polska, SI-CERT, SK-CERT and the others publish
  in their own language. The tables were written from real titles, not guessed vocabulary, so a
  product name survives the translation.
- **The CISA KEV entry carries its remediation deadline.** "Known exploited" tells you to panic;
  "due 28 November" tells you when.
- **CISA's SSVC decision ranks the list**, not my gut feeling: exploitation, automatable,
  technical impact. Forty CVEs per run, cached.

Alerts also go to Slack, Discord or Telegram if you want them within the three hours rather than
the next morning.

It runs on Windows and Linux, needs no Python, and no account anywhere: it reads public feeds and
sends you an e-mail. Source (MIT) and a binary in the releases.

Windows will say "Windows protected your PC" — the executable is not code-signed, which is a
deliberate choice and documented in the archive.

github.com/Hormerty/SecDailyBrief

Happy to answer anything about the feed list, the scoring, or what I refused to include.
```

## Hacker News — Show HN

**Title** (80 characters max)

```
Show HN: A daily security brief that reads 124 feeds and translates the CERTs
```

**First comment**

```
The problem was not finding advisories, it was reading them. I wanted one e-mail, at 06:00, with
the ten things that mattered for the products I run, and nothing else.

What it does: reads 124 public feeds (20 national CERTs, CISA KEV, EPSS, GitHub advisories,
vendor PSIRTs), translates the non-English advisory titles with phrase tables written from real
titles, ranks against a stack list, and enriches the top CVEs with CISA's SSVC decision.

Two design choices worth mentioning:

- The engine is a separate repository, pinned by commit and SHA-256, and the application never
  modifies it. The checksum is verified before every build and every run.
- Every source examined and refused is documented with its measurements in SOURCES.md — including
  the aggregators I turned down, and why.

Windows and Linux, MIT, no telemetry, no account.
```

## Mastodon / LinkedIn (short)

```
A daily security brief by e-mail: 124 feeds including 20 national CERTs, CISA KEV deadlines, SSVC
decisions, and alerts to mail, Slack, Discord or Telegram. Windows and Linux, MIT.
github.com/Hormerty/SecDailyBrief
```

## Pull request — hslatman/awesome-threat-intelligence

The list uses HTML tables. The row goes in the **Tools** table, alphabetically under **S**.

**The row to insert**

```html
    <tr>
        <td>
            <a href="https://github.com/Hormerty/SecDailyBrief" target="_blank">SecDailyBrief</a>
        </td>
        <td>
            A daily security brief by e-mail: reads 124 public feeds — including 20 national CERTs — translates foreign advisory titles to English, ranks them against the reader's own stack, and enriches the highest-scoring CVEs with CISA's KEV deadline and SSVC decision. Windows and Linux; alerts can also go to Slack, Discord or Telegram.
        </td>
    </tr>
```

**PR title**

```
Add SecDailyBrief to Tools
```

**PR body**

```
Adds SecDailyBrief, a desktop application that aggregates public security feeds into a single
daily brief, with CISA KEV and SSVC enrichment. MIT, Windows and Linux.

It follows the table formatting of the Tools section and is placed alphabetically.
```

### How to submit it

1. Fork the repository.
2. Edit `README.md`: find the `<tr>` for the last entry whose name starts with **S** in the Tools
   table, and paste the row above after its `</tr>`.
3. Commit as `Add SecDailyBrief to Tools`, push, open the pull request with the title and body
   above.

One pull request per suggestion, as their CONTRIBUTING.md asks.
