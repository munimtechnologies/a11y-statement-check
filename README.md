# a11y-statement-check

Is a website's accessibility statement still an unfinished template, and when was it last reviewed?

`statement_template_check.py` reads one accessibility statement (a URL, a saved HTML page or a
plain-text draft) and reports the placeholders that statement templates leave behind until someone
fills them in, which WCAG versions the page names, the statement's own latest "last reviewed" or
"prepared on" date (since 0.5.0, with a note when it is more than a year old), and dated or stock
wording worth a second look. Since 0.6.0 it also notes when the page you gave it is probably not
the statement at all but a page in front of it, and prints the address of the statement it links to.
Since 0.8.0 it reports which editions of EN 301 549, the European standard for accessible ICT, a
statement names, with a note when the highest one is older than V3.2.1.
It knows US vendor templates, the fields and guidance notes of GOV.UK's sample accessibility
statement for UK public sector websites (since 0.3.0) and the school statement template served on
UK school websites built by Juniper Websites, formerly e4education (since 0.4.0).
It is also an **agent skill** (`skills/accessibility-statement-check/SKILL.md`), so coding agents
such as Claude Code, Codex and Cursor know when to run it and how to read its results, and a
**GitHub Action** (`action.yml`) that fails a pull request when a statement draft kept in the
repository still has a placeholder, and can check a published statement on a schedule.

Made by MV2 of Munim, Inc. with AI agents; not yet checked by a person. Apache-2.0. It reads what
a statement says, not whether a website is accessible, and it is not legal advice.

## Why

MV2's open censuses of public websites
([title2-pdf-census](https://github.com/munimtechnologies/title2-pdf-census)) found:

- **1,067 of 11,581** US public school district website hosts (9.21%) serve an accessibility
  statement that still carries a 2017 template's placeholders ("the Your School website",
  accessibility@yourschool.com, 555-555-5555) at `/accessibility-statement`, 1,066 of them on
  sites with Finalsite markup; 1,044 of the 1,067 name WCAG 2.0 as the highest version
  ([district-stock](https://github.com/munimtechnologies/title2-pdf-census/tree/main/results/district-stock),
  a pre-registered study; all four predictions held).
- **235 of 5,243** city, county and town website hosts (4.48%) serve an unfinished vendor statement
  template at a stock address: 222 at CivicPlus's `/153/Accessibility` and 13 at Revize's
  `/accessibility_statement/index.php`
  ([stock-153](https://github.com/munimtechnologies/title2-pdf-census/tree/main/results/stock-153),
  [stock-revize](https://github.com/munimtechnologies/title2-pdf-census/tree/main/results/stock-revize)).
- Only **6** of the same 5,243 hosts serve the Accessibility Checker WordPress plugin's statement
  draft at `/accessibility-statement/`, 3 of them unfinished
  ([stock-equalize](https://github.com/munimtechnologies/title2-pdf-census/tree/main/results/stock-equalize)).
- Among accessibility pages of governments of 50,000 or more people that name a WCAG version,
  55.71% name only WCAG 2.0
  ([a11y-pages](https://github.com/munimtechnologies/title2-pdf-census/tree/main/results/a11y-pages)),
  while the ADA Title II rule (28 CFR 35.200) adopts WCAG 2.1 Level AA.

In the UK, public sector bodies must publish an accessibility statement under the Public Sector
Bodies (Websites and Mobile Applications) (No. 2) Accessibility Regulations 2018, and GOV.UK
publishes a sample statement to start from, which asks for a review at least once a year. The
same censuses found:

- **667 of 23,802** school website hosts in England (2.80%) serve a statement at
  `/accessibility-statement/` that still carries template placeholders, such as GOV.UK's sample
  fields "[email address]" and "[phone number]" or the Juniper Websites template's "[Accessibility
  Email Address]"
  ([uk-schools](https://github.com/munimtechnologies/title2-pdf-census/tree/main/results/uk-schools),
  a pre-registered study).
- Of the statements of the UK's principal councils that its reader found (284 of 379 website
  hosts), **105 of the 271 dated ones (38.75%)** carry a latest date more than a year before the
  census month (November 2026), and 86 of the 284 name WCAG 2.1 rather than 2.2 as the highest
  version; only one keeps a template field
  ([uk-councils](https://github.com/munimtechnologies/title2-pdf-census/tree/main/results/uk-councils),
  a pre-registered study). A date is what a statement says; that study calls no council in breach.
- Comparing that census council by council with another open, automated census (Accessibility.build's
  September 2026 council table, CC BY 4.0), **12 of the 23 council pages it scored lowest link
  straight to a statement** that MV2's reader found; none of the 13 low-score pages read again
  named a WCAG version or gave a date
  ([AGREE-RESULT.md](https://github.com/munimtechnologies/title2-pdf-census/blob/main/results/uk-councils/AGREE-RESULT.md),
  pre-registered; all four predictions held). A checker that scores the page in front of the
  statement scores the wrong page; the `hub_page` note (since 0.6.0) catches that pattern.

In the EU, statements under the Web Accessibility Directive and the European Accessibility Act
often name an edition of EN 301 549. ETSI, CEN and CENELEC published EN 301 549 V4.1.1 (2026-09),
whose web clause covers WCAG 2.2, on 2 September 2026; V3.2.1 (2021-03), on WCAG 2.1, is still the
edition cited in the EU's Official Journal for the Web Accessibility Directive (Implementing
Decision (EU) 2021/1339, which withdrew V2.1.2 from 12 February 2022). The `older_en301549` note
(since 0.8.0) flags a statement whose newest edition named is older than V3.2.1.

## Use it

Python 3.8 or newer, standard library only, nothing to install:

```
python skills/accessibility-statement-check/statement_template_check.py https://www.example.gov/accessibility
python skills/accessibility-statement-check/statement_template_check.py --site www.example.gov
python skills/accessibility-statement-check/statement_template_check.py --text draft-statement.txt --json
python skills/accessibility-statement-check/statement_template_check.py --text draft-statement.txt --max-age-days 180 --today 2026-11-10
```

`--site` tries the three stock addresses (`/153/Accessibility`,
`/accessibility_statement/index.php`, `/accessibility-statement`), honours robots.txt and pauses
one second between requests. `--file` reads a saved HTML page. `--max-age-days` (default 365; 0
turns it off) sets when a statement's latest date counts as old, and `--today` (YYYY-MM-DD) fixes
the date it is measured from. Exit code 1: a template placeholder was found; 0: none found; 2: no
page could be read. An old date, an older EN 301 549 edition or a hub page is a note only and never
changes the exit code. That makes it usable in CI on a statement draft kept in a repository.

Example output for an unfinished template (an illustrative page, not a real site):

```
https://www.example.gov/153/Accessibility
  read: 1874 characters of text (stock address: civicplus)
  PLACEHOLDER government/your_municipality: YOUR MUNICIPALITY
  WCAG versions named: 2.0
  statement date: none found
  NOTE placeholder: template placeholders are still in the text: fill them in (name, contact, standard, dates) or remove them
  NOTE only_wcag_2_0: names WCAG 2.0 only; the ADA Title II rule (28 CFR 35.200) adopts WCAG 2.1 Level AA, so check which version the site actually targets
  verdict: unfinished template (1 placeholder)
```

And for a filled-in UK statement last reviewed more than a year ago (an illustrative text file,
checked on 2026-11-10):

```
statement.txt
  read: 1240 characters of text
  template wording: gov_uk_sample
  WCAG versions named: 2.1
  statement date: 2025-03-10 (reviewed)
  NOTE uk_older_wcag: uses GOV.UK's compliance wording but names WCAG 2.1 as the highest version; GOV.UK's current sample statement names WCAG 2.2 AA, so check which version the site was tested against
  NOTE old_statement_date: the statement's latest date (reviewed 2025-03-10) is 610 days before 2026-11-10; GOV.UK's sample statement asks public sector bodies to review their statement at least once a year, so check that it is still current
  verdict: no template placeholder found
```

And for a page in front of the statement (an illustrative page, not a real site):

```
https://www.example.gov.uk/help/accessibility
  read: 642 characters of text
  WCAG versions named: none
  statement date: none found
  NOTE no_wcag: does not mention WCAG at all
  NOTE hub_page: names no WCAG version and gives no statement date, but links to what looks like the accessibility statement itself (https://www.example.gov.uk/help/accessibility/accessibility-statement/); this page probably sits in front of the statement, so check that address too (this tool never follows it by itself)
  statement link: https://www.example.gov.uk/help/accessibility/accessibility-statement/
  verdict: no template placeholder found
```

And for an EU statement that names an older EN 301 549 edition (an illustrative text file, the
one in `test_en301549.py`):

```
statement.txt
  read: 331 characters of text
  WCAG versions named: 2.1
  EN 301 549 editions named: V2.1.2
  statement date: none found
  NOTE older_en301549: names EN 301 549 V2.1.2 as the highest edition; since 2021 the edition cited in the EU's Official Journal for the Web Accessibility Directive is V3.2.1 (2021-03, on WCAG 2.1; Implementing Decision (EU) 2021/1339), and V4.1.1 (2026-09, on WCAG 2.2) was published on 2 September 2026, so check which edition the site was tested against
  verdict: no template placeholder found
```

## In CI (GitHub Action, since v0.2.0)

Keep your statement draft in the repository and let a pull request fail while it still has a
placeholder:

```yaml
name: accessibility statement
on: [pull_request]
jobs:
  statement:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: munimtechnologies/a11y-statement-check@v0.8.0
        with:
          text-files: |
            docs/accessibility*.md
          html-files: |
            site/accessibility/index.html
```

Or check your published statement once a month and get a notice when its latest stated review
date is more than a year old (one request to your own page per run):

```yaml
name: statement review date
on:
  schedule:
    - cron: "0 7 1 * *"
jobs:
  statement:
    runs-on: ubuntu-latest
    steps:
      - id: statement
        uses: munimtechnologies/a11y-statement-check@v0.8.0
        with:
          urls: https://www.example.gov.uk/accessibility-statement
      - if: steps.statement.outputs.old-statements != '0'
        run: echo "The accessibility statement is due for its yearly review." && exit 1
```

Inputs (all optional, but give at least one of the first three):

| Input | What it does |
|---|---|
| `text-files` | Plain-text or Markdown drafts, one path or glob pattern per line (`docs/**/*.md` works) |
| `html-files` | Saved or built HTML pages, one path or glob pattern per line |
| `urls` | Published statement URLs, one per line; each is read once, with no crawling |
| `fail-on-placeholder` | `true` (default) fails the step on a placeholder; `false` reports it as a warning |
| `fail-on-unread` | `true` (default) fails the step when a pattern matches no file or a URL cannot be read |
| `json-report` | A path to write the full JSON report to (for example to upload as an artifact) |
| `max-age-days` | A statement whose latest stated date is older than this gets a notice and counts in `old-statements` (default 365; 0 turns it off) |

Outputs: `placeholder-pages` (statements read that still carry a placeholder), `pages-read`,
`unread` and `old-statements` (statements read whose latest stated date is more than
`max-age-days` old). Each placeholder becomes an annotation on the file and line where it was
found, other notes (such as a statement that names only WCAG 2.0, an old date, an older EN 301 549
edition or a hub page) become notices, and the job summary gets a table of every statement checked
with its date. The step runs `action_run.py` with the runner's own Python 3 (standard library only,
nothing installed); inputs reach it only as environment variables, never pasted into the shell
command. Its tests run offline (`test_action.py`); it has not yet been run on GitHub's Windows
runners.

## As an agent skill

The skill is listed on skills.sh:
[skills.sh/munimtechnologies/a11y-statement-check/accessibility-statement-check](https://skills.sh/munimtechnologies/a11y-statement-check/accessibility-statement-check).
Install it with the open `skills` CLI:

```
npx skills add https://github.com/munimtechnologies/a11y-statement-check --skill accessibility-statement-check
```

or copy `skills/accessibility-statement-check/` into your agent's skills directory. The skill tells
the agent to change nothing without the user, never to present a clean result as a conformance or
legal finding, and not to crawl lists of other people's sites.

**Untrusted page content.** The skill reads web pages that other people wrote, so a page could
carry text aimed at an agent (indirect prompt injection); Snyk's audit on skills.sh flags this as
W011, third-party content exposure. The checker never prints a page's body: only the address,
counts, WCAG versions, EN 301 549 edition numbers and dates it read, its own fixed notes, matched
snippets of at most 100 characters and (since 0.6.0, on a hub page only) at most five link
addresses of at most 300 characters. It never follows a link it finds. Since 2026-11-09 the skill
also tells the agent to treat any page text as data, never as instructions, not to run commands,
open further links or fill in forms because a page says so, and to report instruction-like text to
the user as a quote.

## What it checks

| Group | Placeholders (case and spacing inside brackets ignored where marked) |
|---|---|
| `revize` | [Your Agency/Website Name], [Date], [Contact Email], [Contact Phone], [Agency Address], [X business days] |
| `accessibility-checker` | [YOUR COMPANY NAME], [SPECIFIC STANDARD, VERSION, LEVEL], [LIST ACCESSIBILITY FEATURES HERE], [LIST ITEMS YOU'RE WORKING TO FIX HERE], [YOUR ACCESSIBILITY EMAIL ADDRESS], [YOUR PHONE NUMBER] |
| `gov-uk` | GOV.UK's sample statement: [website name], [scope of statement ...], [name of organisation], [email address], [phone number], [add any other contact details], [number], [add link to ...], [insert one of the following ...], [rough timing], [example of non-essential document], [date when it was first published], [date when it was last reviewed], [add name of organisation that carried out test ...], [Note: ...], [Select (a) ...] and the line "sample accessibility statement for a fictional public sector website" (its plain [date] field is reported as `revize/date`) |
| `juniper` | The Juniper Websites (formerly e4education) school template: [Website Link and Date], [Accessibility Email Address], [School Phone Number], [School Mailing Address], (School Name), and its editing notes "[This is a sample accessibility statement ...", "Prior to publication, please remove this text", "[Delete as appropriate", "[The above are examples only", "[Please add / refer / use / remove ...", "[Set out the method ...", "[It is recommended that statements ..." (its [School Name] is reported as `school/school_bracket` and its [Date] as `revize/date`) |
| `school` | [Your School] and similar (also [School Name]), "the Your School", yourschool.com-style addresses, 555-555-5555, "within # business days" |
| `government` | YOUR MUNICIPALITY, "only meant as a template", NAME / TITLE / EMAIL / PHONE, capitalised fields such as [INSERT ...], [CITY NAME] or [NAME OF PARISH/TOWN COUNCIL] |
| `generic` | [Insert ...] |

Notes (never counted in the exit code): a bracketed phrase that may be a placeholder (Cloudflare's
hidden "[email protected]" is skipped), WCAG 2.0 named alone, WCAG mentioned without a version or
not at all, April 24, 2026 named without a later Title II date (an interim final rule of
2026-04-20 moved the dates to April 26, 2027 and April 26, 2028), a 2017 "Accessibility Statement
Generator" credit, and a vendor's stock "We work to comply with Section 508 as well as ..."
sentence. A page that uses GOV.UK's legally required compliance sentence ("This website is fully /
partially / not compliant with the Web Content Accessibility Guidelines ...") gets the UK note
`uk_older_wcag` when its highest WCAG version is 2.0 or 2.1 (GOV.UK's current sample names WCAG 2.2
AA), and none of the US ADA notes. Template wording `juniper_school` marks the Juniper template's
closing sentence ("... values diversity and inclusion and is committed to providing an accessible
online experience ..."), filled in or not.

**Statement dates (since 0.5.0).** The checker reads the dates a statement gives after "last
reviewed / updated / revised", "reviewed / updated / revised on / in" and "prepared / published /
created / written / produced on / in", in the forms "3 June 2024", "June 3, 2024", "June 2024"
(read as the month's last day), "03/06/2024" and "2024-06-03". The later of the latest review date
and the latest prepared date is the statement's date; when it is more than `--max-age-days` before
today (default 365), the note `old_statement_date` says so. It is the date reader of the UK council
census (title2-pdf-census's `council_stock.py`). A statement with no such date gets no note
("statement date: none found"). Since 0.7.0 a date right after "will be", "is due to be", "next"
and the like ("It will be reviewed in March 2027") is a planned review, not the latest one, and is
not read.

**Hub pages (since 0.6.0).** An HTML page (a URL or `--file`) that names no WCAG version, gives no
statement date, has no placeholder and does not use GOV.UK's compliance sentence, but links to what
looks like the accessibility statement (the link text says "accessibility statement" or "datganiad
hygyrchedd", or the address says accessibility-statement, accessibility_statement or
AccessibilityStatement), gets the note `hub_page` and a line `statement link:` for each such link
(at most five, in page order, the page itself left out). The JSON gains `statement_links` and
`hub_page` on every page read. The tool never follows the link: run it again on that address. In a
saved file only absolute links count. These are the two strongest link rules of the UK council
census's reader.

**EN 301 549 editions (since 0.8.0).** When a page names EN 301 549 (or EN 301-549), the output
gains a line `EN 301 549 editions named:` with each edition read, and the JSON gains
`en301549_named`, `en301549_versions` and `en301549_highest` on every page read. An edition is read
only when "V" or "version" comes right before its number, after "EN 301 549" and at most 25 other
characters with no full stop or digit ("EN 301 549 V3.2.1 (2021-03)", "ETSI EN 301 549 v.2.1.2",
"EN 301-549, version 3.2.1"), so a clause number such as "EN 301 549 clause 9.1.1.1" is never read
as an edition. When the highest edition named is older than V3.2.1 (for example V2.1.2 (2018-08)
or V1.1.2 (2015-04)), the note `older_en301549` says so. A statement on V3.2.1 gets no note: it is
still the edition cited in the Official Journal, even though V4.1.1 is published.

Limits: it reads visible text only (not PDFs, not text split across tags in the middle of a
word), one page per address, and a filled-in template can still be wrong about the site. The UK
rules follow the GOV.UK sample as published on 2026-11-08 and the Juniper template as seen on live
school pages on 2026-11-09; older copies of either used other wording that may not be caught. A
numeric date such as 03/06/2024 is read day first, as in the UK (unless the second number is above
12), so a US statement's 03/06/2024 is read as 3 June; dates in other words ("as of", "valid
from") are not read; a planned date is left out only when "will be", "shall be", "should be",
"must be", "to be" or "next" comes right before "reviewed", "updated", "prepared" and the like
(since 0.7.0), so other wording for a plan can still be read as a review date; and a review date is what the statement says, not proof that
anyone reviewed it. A short statement that names no WCAG version and no date but links to another
statement (for example an app's) also gets `hub_page`; read it as "check the linked page too". An
EN 301 549 edition is read only in the wording above: "EN 301 549:2018", a second edition listed
after the first without its own "EN 301 549" ("EN 301 549 V2.1.2 and V3.2.1") and statements in
other languages that put the edition before the standard's name are not read in full.

## Tests

```
python -m unittest -v test_statement_template_check.py test_action.py test_hub_page.py test_planned_review.py test_en301549.py
```

Offline; no network is used.

## Changes

- **0.8.0:** EN 301 549 editions. A page that names EN 301 549 gets a line `EN 301 549 editions
  named:` and, in the JSON, `en301549_named`, `en301549_versions` and `en301549_highest`; when its
  highest edition is older than V3.2.1 (2021-03), the edition cited in the EU's Official Journal
  for the Web Accessibility Directive since 2021, it gets the note `older_en301549`. ETSI, CEN and
  CENELEC published V4.1.1 (2026-09), whose web clause covers WCAG 2.2, on 2 September 2026. A
  clause number is never read as an edition. Every placeholder rule, earlier note, input, output
  and exit code is unchanged; the Action (`action_run` 0.8.0) passes the new note on as a notice.
  New offline tests: `test_en301549.py`.
- **0.7.0:** planned review dates. A date right after "will be", "shall be", "should be", "must
  be", "to be" or "next" ("It will be reviewed in March 2027", "is due to be updated on ...") is a
  planned review or publication, so it is no longer read as the statement's date; before, it could
  make an old statement look current and hide the `old_statement_date` note. MV2's pre-registered
  census of UK government organisations' accessibility statements found one statement whose date
  was such a planned review (title2-pdf-census, results/govuk-orgs/GOVUK-STOCK-RESULT.md). Every
  placeholder rule, other note, input, output and exit code is unchanged; the Action (`action_run`
  0.7.0) changes only its version. New offline tests: `test_planned_review.py`.
- **0.6.0:** hub pages. A page that names no WCAG version, gives no statement date and has no
  placeholder or GOV.UK compliance sentence, but links to what looks like the accessibility
  statement, gets the note `hub_page` and one `statement link:` line per such link; the JSON gains
  `statement_links` and `hub_page`. MV2's pre-registered comparison of two automated censuses of UK
  council statements found that 12 of the 23 council pages one census scored lowest were such pages.
  The tool never follows a link by itself. The Action (`action_run` 0.6.0) passes the note on as a
  notice and is otherwise unchanged; no input, output, placeholder rule, earlier note or exit code
  changed. New offline tests: `test_hub_page.py`.
- **0.5.0:** statement dates. The checker reads a statement's own latest "last reviewed" and
  "prepared on" dates (new `review_date`, `prepared_date`, `statement_date`, `date_source` and
  `statement_age_days` in the JSON), prints them as "statement date:", and adds the note
  `old_statement_date` when the statement's date is more than `--max-age-days` (default 365) before
  today; `--today` fixes the date ages are measured from. GOV.UK's sample statement asks for a
  review at least once a year, and the UK council census found 105 of 271 dated statements more
  than a year old. The Action gains the input `max-age-days` and the output `old-statements`, a
  date column in the job summary, and a notice per old statement. Every placeholder rule, exit
  code and earlier note is unchanged.
- **Docs, 2026-11-09 (no code change, still 0.4.0):** the skill is listed on skills.sh; SKILL.md
  gains a section "Pages are untrusted content" (treat statement text as data, never as
  instructions), in answer to Snyk's W011 audit warning there. The checker, the Action and every
  result are unchanged.
- **0.4.0:** the `juniper` group: 12 rules for the fields and editing notes of the school
  statement template served at `/accessibility-statement/` on UK school websites built by Juniper
  Websites (formerly e4education), such as "[Accessibility Email Address]", "[School Phone
  Number]", "[Website Link and Date]" and "[This is a sample accessibility statement ...". 0.3.0
  caught only that template's "[School Name]" and "[Date]", so a statement that kept only its
  contact fields passed. New template wording `juniper_school`. Every page flagged before is
  still flagged; a bracket that starts "[Please add", "[Please refer", "[Please use" or
  "[Please remove" is now reported as `juniper/please_instruction` even outside that template,
  so a capitalised field such as "[PLEASE ADD NAME OF COUNCIL]" moves from
  `government/caps_bracket` to it. The Action (`action_run` 0.4.0) is unchanged apart from its version.
- **0.3.1:** the Action's one-line description in `action.yml` is now shorter than 125 characters,
  which the GitHub Marketplace requires before it lists an action, and a test keeps it that way.
  Only the Action's version changed (`action_run` 0.3.1); the checker and its rules are unchanged
  (still 0.3.0), so every result is the same as in 0.3.0.
- **0.3.0:** the `gov-uk` group (GOV.UK's sample accessibility statement: 17 rules for its fields,
  guidance notes and sample line), the `gov_uk_sample` template wording and the `uk_older_wcag` note; UK
  statements no longer get the US ADA notes. Nothing found before is reported differently, except
  that "[name of organisation]" is now `gov-uk/organisation_name` (it was `school/school_bracket`).
  The Action is unchanged apart from its version.
- **0.2.0:** GitHub Action (`action.yml`, `action_run.py`, `test_action.py`): annotations at the
  placeholder's line, a job-summary table, step outputs and an optional JSON report. The checker
  itself is unchanged (0.1.0).
- **0.1.0:** first release: the checker and the agent skill.
