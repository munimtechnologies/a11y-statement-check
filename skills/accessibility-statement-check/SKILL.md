---
name: accessibility-statement-check
description: Check a website's accessibility statement for unfilled template placeholders (such as [Your School], YOUR MUNICIPALITY, [Your Agency/Website Name], [YOUR COMPANY NAME], accessibility@yourschool.com, 555-555-5555, or GOV.UK sample fields like [website name], [name of organisation] and [date when it was first published]), a WCAG 2.0-only promise and the outdated April 24, 2026 ADA Title II date. Use when writing, reviewing or auditing an accessibility statement or accessibility page, especially for US state and local governments, school districts, UK public sector bodies and sites built on CivicPlus, Revize, Finalsite or the Accessibility Checker WordPress plugin. Read-only; standard-library Python.
license: Apache-2.0
---

# Accessibility statement check

Many public websites publish an accessibility statement that started as a template (from their
website vendor, or GOV.UK's sample statement in the UK), and some never fill it in. MV2's open
censuses ([title2-pdf-census](https://github.com/munimtechnologies/title2-pdf-census)) found 235
of 5,243 US city, county and town website hosts serving an unfinished vendor template at a stock
address, and 1,067 of 11,581 US school district website hosts serving a 2017 template's
placeholders. `statement_template_check.py` (in this folder) applies the same rules to one site or
page.

## When to use it

- The user asks you to write, review, update or audit an accessibility statement or page.
- You are reviewing a site's ADA Title II readiness, a UK public sector body's statement under the
  2018 accessibility regulations, or a site built on CivicPlus, Revize, Finalsite or WordPress with
  the Accessibility Checker plugin.
- Before you tell anyone a statement is "done" or "compliant".

## How to run it

Python 3.8 or newer, standard library only. Run it from this skill's folder (or give its full path):

```
python statement_template_check.py https://www.example.gov/accessibility
python statement_template_check.py --site www.example.gov
python statement_template_check.py --file saved-statement.html --json
python statement_template_check.py --text draft-statement.txt
```

- A URL argument reads that one page.
- `--site` tries the three stock addresses where the censuses found most unfinished templates
  (`/153/Accessibility`, `/accessibility_statement/index.php`, `/accessibility-statement`), honours
  robots.txt and pauses between requests (`--delay`, default 1 second). A stock address that
  redirects to the home page is reported as `redirect_home` and not read.
- `--file` reads a saved HTML page; `--text` reads a plain-text draft (use this on a statement you
  are writing before it is published).
- `--json` prints machine-readable results.

Exit code 1 means at least one page read has a template placeholder, 0 means none does, 2 means no
page could be read (404, robots.txt, network error, or less than 200 characters of text).

## How to read the results

- `PLACEHOLDER <group>/<id>: <text>` is an unfilled template field. Groups: `revize`,
  `accessibility-checker`, `gov-uk` (GOV.UK's sample statement for UK public sector websites: its
  lowercase fields, its "[Note: ...]" and "[Select (a) ...]" guidance and its "fictional public
  sector website" line), `school` (the 2017 "Your School" template and Finalsite's 2026 sample),
  `government` (the city template's capitalised fields) and `generic` ("[Insert ...]"). Each one
  needs real content: the organisation's name, a working contact, the standard and level the site
  targets, a review date. The sample's plain "[date]" field is reported as `revize/date`.
- `NOTE possible_placeholder` is bracketed text that may be a placeholder. Look at it in context;
  it is never counted in the exit code.
- `NOTE only_wcag_2_0`: the page names WCAG 2.0 and no later version. The ADA Title II rule for
  state and local governments (28 CFR 35.200) adopts WCAG 2.1 Level AA.
- `NOTE uk_older_wcag`: the page uses GOV.UK's compliance sentence ("This website is partially
  compliant with the Web Content Accessibility Guidelines version ...") but names WCAG 2.0 or 2.1
  as the highest version, while GOV.UK's current sample names WCAG 2.2 AA. Pages with that sentence
  get this note instead of the US notes.
- `NOTE old_title2_date`: the page names April 24, 2026 and no later date. The Justice
  Department's interim final rule of 2026-04-20 moved the compliance dates to April 26, 2027
  (50,000 or more people) and April 26, 2028 (under 50,000, and special districts).
- `NOTE generator` and `NOTE stock_508` mark wording copied from a template that may no longer be
  true for the site.
- `template wording` names the template a page is built on, even when it has been filled in
  (`gov_uk_sample` is the GOV.UK compliance sentence).

## Rules for the agent

- It is read-only. Do not edit, publish or replace a statement without the user's go-ahead, and
  show the user the exact lines you would change.
- A clean result means only that no template placeholder was found. It says nothing about whether
  the website itself is accessible or meets WCAG; never present it as a conformance or legal
  finding. It is not legal advice.
- Do not contact a site's owner or vendor about a finding on the user's behalf unless the user asks
  you to, and then have a person check the page first.
- Check one site at a time; do not use `--site` to crawl long lists of other people's websites.

Made by MV2 of Munim, Inc. with AI agents; not yet checked by a person. Apache-2.0.
