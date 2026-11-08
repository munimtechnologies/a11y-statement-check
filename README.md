# a11y-statement-check

Is a website's accessibility statement still an unfinished template?

`statement_template_check.py` reads one accessibility statement (a URL, a saved HTML page or a
plain-text draft) and reports the placeholders that statement templates leave behind until someone
fills them in, which WCAG versions the page names, and dated or stock wording worth a second look.
It knows US vendor templates and, since 0.3.0, the fields and guidance notes of GOV.UK's sample
accessibility statement for UK public sector websites.
It is also an **agent skill** (`skills/accessibility-statement-check/SKILL.md`), so coding agents
such as Claude Code, Codex and Cursor know when to run it and how to read its results, and a
**GitHub Action** (`action.yml`) that fails a pull request when a statement draft kept in the
repository still has a placeholder.

Made by MV2 of Munim, Inc. with AI agents; not yet checked by a person. Apache-2.0. It reads what
a statement says, not whether a website is accessible, and it is not legal advice.

## Why

MV2's open censuses of US public websites
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
publishes a sample statement to start from. Live statements that still carry its fields
("[website name]", "[name of organisation]") can be found with a web search; no count of them has
been published yet.

## Use it

Python 3.8 or newer, standard library only, nothing to install:

```
python skills/accessibility-statement-check/statement_template_check.py https://www.example.gov/accessibility
python skills/accessibility-statement-check/statement_template_check.py --site www.example.gov
python skills/accessibility-statement-check/statement_template_check.py --text draft-statement.txt --json
```

`--site` tries the three stock addresses (`/153/Accessibility`,
`/accessibility_statement/index.php`, `/accessibility-statement`), honours robots.txt and pauses
one second between requests. `--file` reads a saved HTML page. Exit code 1: a template placeholder
was found; 0: none found; 2: no page could be read. That makes it usable in CI on a statement draft
kept in a repository.

Example output for an unfinished template (an illustrative page, not a real site):

```
https://www.example.gov/153/Accessibility
  read: 1874 characters of text (stock address: civicplus)
  PLACEHOLDER government/your_municipality: YOUR MUNICIPALITY
  WCAG versions named: 2.0
  NOTE placeholder: template placeholders are still in the text: fill them in (name, contact, standard, dates) or remove them
  NOTE only_wcag_2_0: names WCAG 2.0 only; the ADA Title II rule (28 CFR 35.200) adopts WCAG 2.1 Level AA, so check which version the site actually targets
  verdict: unfinished template (1 placeholder)
```

And for a UK draft that kept GOV.UK's sample fields (an illustrative text file):

```
draft-statement.txt
  read: 812 characters of text
  PLACEHOLDER gov-uk/website_name: [website name]
  PLACEHOLDER gov-uk/organisation_name: [name of organisation]
  PLACEHOLDER gov-uk/first_published: [date when it was first published]
  template wording: gov_uk_sample
  WCAG versions named: 2.1
  NOTE placeholder: template placeholders are still in the text: fill them in (name, contact, standard, dates) or remove them
  NOTE uk_older_wcag: uses GOV.UK's compliance wording but names WCAG 2.1 as the highest version; GOV.UK's current sample statement names WCAG 2.2 AA, so check which version the site was tested against
  verdict: unfinished template (3 placeholders)
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
      - uses: munimtechnologies/a11y-statement-check@v0.3.0
        with:
          text-files: |
            docs/accessibility*.md
          html-files: |
            site/accessibility/index.html
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

Outputs: `placeholder-pages` (statements read that still carry a placeholder), `pages-read` and
`unread`. Each placeholder becomes an annotation on the file and line where it was found, other
notes (such as a statement that names only WCAG 2.0) become notices, and the job summary gets a
table of every statement checked. The step runs `action_run.py` with the runner's own Python 3
(standard library only, nothing installed); inputs reach it only as environment variables, never
pasted into the shell command. Its tests run offline (`test_action.py`); it has not yet been run
on GitHub's Windows runners.

## As an agent skill

Install the skill folder into your agent (for example with the open `skills` CLI:
`npx skills add munimtechnologies/a11y-statement-check`), or copy
`skills/accessibility-statement-check/` into your agent's skills directory. The skill tells the
agent to change nothing without the user, never to present a clean result as a conformance or
legal finding, and not to crawl lists of other people's sites.

## What it checks

| Group | Placeholders (case and spacing inside brackets ignored where marked) |
|---|---|
| `revize` | [Your Agency/Website Name], [Date], [Contact Email], [Contact Phone], [Agency Address], [X business days] |
| `accessibility-checker` | [YOUR COMPANY NAME], [SPECIFIC STANDARD, VERSION, LEVEL], [LIST ACCESSIBILITY FEATURES HERE], [LIST ITEMS YOU'RE WORKING TO FIX HERE], [YOUR ACCESSIBILITY EMAIL ADDRESS], [YOUR PHONE NUMBER] |
| `gov-uk` | GOV.UK's sample statement: [website name], [scope of statement ...], [name of organisation], [email address], [phone number], [add any other contact details], [number], [add link to ...], [insert one of the following ...], [rough timing], [example of non-essential document], [date when it was first published], [date when it was last reviewed], [add name of organisation that carried out test ...], [Note: ...], [Select (a) ...] and the line "sample accessibility statement for a fictional public sector website" (its plain [date] field is reported as `revize/date`) |
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
AA), and none of the US ADA notes.

Limits: it reads visible text only (not PDFs, not text split across tags in the middle of a
word), one page per address, and a filled-in template can still be wrong about the site. The UK
rules follow the GOV.UK sample as published on 2026-11-08; older copies of the sample used other
wording that may not be caught.

## Tests

```
python -m unittest -v test_statement_template_check.py test_action.py
```

Offline; no network is used.

## Changes

- **0.3.0:** the `gov-uk` group (GOV.UK's sample accessibility statement: 17 rules for its fields,
  guidance notes and sample line), the `gov_uk_sample` template wording and the `uk_older_wcag` note; UK
  statements no longer get the US ADA notes. Nothing found before is reported differently, except
  that "[name of organisation]" is now `gov-uk/organisation_name` (it was `school/school_bracket`).
  The Action is unchanged apart from its version.
- **0.2.0:** GitHub Action (`action.yml`, `action_run.py`, `test_action.py`): annotations at the
  placeholder's line, a job-summary table, step outputs and an optional JSON report. The checker
  itself is unchanged (0.1.0).
- **0.1.0:** first release: the checker and the agent skill.
