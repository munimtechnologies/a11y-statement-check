# Copyright 2026 Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""action_run 0.6.0: the GitHub Action entry point of a11y-statement-check.

Checks accessibility statement drafts kept in a repository (plain text or Markdown, saved HTML)
and, if asked, published statement URLs, with statement_template_check.py's rules (since 0.3.0
also GOV.UK's sample statement fields, since 0.4.0 the Juniper Websites school template's). It
writes the usual text report to the log, one annotation per template placeholder (with the file
and line where it can find them), a table in the job summary, and the step outputs
placeholder-pages, pages-read, unread and (since 0.5.0) old-statements: statements whose own
latest "last reviewed" or "prepared on" date is more than max-age-days old (default 365; each
also gets a notice). Since 0.6.0 a page that names no WCAG version and gives no date but links to
an accessibility statement gets the notice hub_page, with that link's address in the log. Exit
code 1 when a placeholder is found (unless fail-on-placeholder is false), 2 when a file or URL
given could not be read (unless fail-on-unread is false), else 0; an old date or a hub page never
changes it (use the old-statements output to act on an old date).

Inputs come from environment variables set by action.yml (never from the shell command line):
STC_TEXT_FILES, STC_HTML_FILES, STC_URLS (one entry per line; file entries may be glob patterns
such as docs/**/*.md), STC_FAIL_ON_PLACEHOLDER, STC_FAIL_ON_UNREAD, STC_JSON_REPORT,
STC_MAX_AGE_DAYS. STC_TODAY (YYYY-MM-DD, default today) fixes the date ages are measured from.

Standard library only. Made by MV2 of Munim, Inc. with AI agents. It reads what a statement
says, not whether a website is accessible, and it is not legal advice.
"""

import datetime
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "skills", "accessibility-statement-check"))
import statement_template_check as stc  # noqa: E402

__version__ = "0.6.0"
TRUE = ("true", "yes", "on", "1")
TITLE = "Accessibility statement placeholder"


def entries(value):
    """Non-empty lines of a multi-line input, '#' comment lines left out."""
    out = []
    for line in (value or "").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(line)
    return out


def flag(value, default):
    value = (value or "").strip().lower()
    if not value:
        return default
    return value in TRUE


def whole_number(value, default):
    """(number, problem): a whole-number input, or the default and a message when it is not one."""
    value = (value or "").strip()
    if not value:
        return default, ""
    try:
        return int(value), ""
    except ValueError:
        return default, "max-age-days '%s' is not a whole number; using %d" % (value, default)


def expand(patterns, base):
    """(files, patterns that matched no file). Relative patterns are read from base."""
    files, missing = [], []
    for pattern in patterns:
        full = pattern if os.path.isabs(pattern) else os.path.join(base, pattern)
        if glob.has_magic(pattern):
            hits = sorted(h for h in glob.glob(full, recursive=True) if os.path.isfile(h))
        else:
            hits = [full] if os.path.isfile(full) else []
        if not hits:
            missing.append(pattern)
        for h in hits:
            if h not in files:
                files.append(h)
    return files, missing


def esc_data(s):
    return str(s).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def esc_prop(s):
    return esc_data(s).replace(":", "%3A").replace(",", "%2C")


def find_line(path, found_text):
    """The 1-based line of a file where a placeholder's text starts, or 0 if not found."""
    words = found_text.split()
    if not words:
        return 0
    try:
        with open(path, "rb") as f:
            raw = f.read().decode("utf-8", "replace")
    except OSError:
        return 0
    rx = re.compile(r"\s+".join(re.escape(w) for w in words), re.I)
    m = rx.search(raw)
    return raw.count("\n", 0, m.start()) + 1 if m else 0


def command(kind, message, file="", line=0, title=TITLE):
    props = []
    if file:
        props.append("file=" + esc_prop(file))
        if line:
            props.append("line=%d" % line)
    props.append("title=" + esc_prop(title))
    return "::%s %s::%s" % (kind, ",".join(props), esc_data(message))


def cell(s):
    return str(s).replace("|", "\\|").replace("\n", " ")


def check_one(kind, source, shown, get, today=None, max_age_days=stc.MAX_AGE_DAYS):
    if kind == "url":
        r = stc.read_page(source, get=get, today=today, max_age_days=max_age_days)
    else:
        try:
            r = stc.check_file(source, html_file=(kind == "html"), today=today,
                               max_age_days=max_age_days)
        except OSError as e:
            r = {"source": source, "final_url": "", "status": "unreadable (%s)" % e.__class__.__name__,
                 "stock_address": ""}
    r["source"] = shown
    r["kind"] = kind
    return r


def is_old(r):
    return any(n["id"] == "old_statement_date" for n in r.get("notes", []))


def main(env=None, out=None, get=stc.http_get):
    env = os.environ if env is None else env
    out = out or sys.stdout
    base = env.get("GITHUB_WORKSPACE") or os.getcwd()
    fail_placeholder = flag(env.get("STC_FAIL_ON_PLACEHOLDER"), True)
    fail_unread = flag(env.get("STC_FAIL_ON_UNREAD"), True)
    max_age_days, age_problem = whole_number(env.get("STC_MAX_AGE_DAYS"), stc.MAX_AGE_DAYS)
    today_text = (env.get("STC_TODAY") or "").strip()
    today = datetime.date.fromisoformat(today_text) if today_text else datetime.date.today()
    text_files, missing_text = expand(entries(env.get("STC_TEXT_FILES")), base)
    html_files, missing_html = expand(entries(env.get("STC_HTML_FILES")), base)
    urls = entries(env.get("STC_URLS"))
    missing = missing_text + missing_html
    lines = []
    if age_problem:
        lines.append(command("warning", age_problem, title="a11y-statement-check"))

    if not (text_files or html_files or urls or missing):
        lines.append(command("error", "give at least one of text-files, html-files or urls",
                             title="a11y-statement-check"))
        out.write("\n".join(lines) + "\n")
        return 2

    age = {"today": today, "max_age_days": max_age_days}
    jobs = [("text", p) for p in text_files] + [("html", p) for p in html_files]
    results, where = [], {}
    for kind, path in jobs:
        shown = os.path.relpath(path, base).replace(os.sep, "/")
        r = check_one(kind, path, shown, get, **age)
        where[id(r)] = path
        results.append(r)
    for url in urls:
        results.append(check_one("url", url, url, get, **age))

    for r in results:
        lines.extend(stc.format_result(r))
    for pattern in missing:
        lines.append(command("error" if fail_unread else "warning",
                             "no file matches '%s'" % pattern, title="a11y-statement-check"))
    kind = "error" if fail_placeholder else "warning"
    for r in results:
        if r.get("status") != "ok":
            if r["kind"] == "url" or r["status"].startswith("unreadable"):
                lines.append(command("error" if fail_unread else "warning",
                                     "%s not read: %s" % (r["source"], r["status"]),
                                     title="a11y-statement-check"))
            continue
        path = where.get(id(r), "")
        for p in r["placeholders"]:
            msg = ("'%s' is still a template placeholder (%s/%s): fill it in or remove it"
                   % (p["text"], p["group"], p["id"]))
            if path:
                lines.append(command(kind, msg, file=r["source"], line=find_line(path, p["text"])))
            else:
                lines.append(command(kind, "%s: %s" % (r["source"], msg)))
        for n in r["notes"]:
            if n["id"] != "placeholder":
                lines.append(command("notice", n["message"], file=r["source"] if path else "",
                                     title="Accessibility statement: %s" % n["id"]))

    read = [r for r in results if r.get("status") == "ok"]
    flagged = [r for r in read if r.get("placeholder")]
    old = [r for r in read if is_old(r)]
    unread = len(missing) + sum(1 for r in results if r.get("status") != "ok")
    lines.append("a11y-statement-check %s (statement_template_check %s): %d of %d statement%s read "
                 "with a template placeholder; %d not read; %d dated more than %d days before %s"
                 % (__version__, stc.__version__, len(flagged), len(read),
                    "" if len(read) == 1 else "s", unread, len(old), max_age_days,
                    today.isoformat()))
    out.write("\n".join(lines) + "\n")

    summary = ["## Accessibility statement check", "",
               "%d of %d statement%s read still carry a template placeholder; %d not read; %d "
               "carry a latest date more than %d days before %s."
               % (len(flagged), len(read), "" if len(read) == 1 else "s", unread, len(old),
                  max_age_days, today.isoformat()), "",
               "| Statement | Verdict | Placeholders | WCAG versions named | Statement date |",
               "|---|---|---|---|---|"]
    for r in results:
        if r.get("status") == "ok":
            ph = ", ".join("`%s`" % p["text"].replace("`", "'") for p in r["placeholders"]) or "none"
            date = ("%s (%s)" % (r["statement_date"], r["date_source"])
                    if r.get("statement_date") else "none found")
            if is_old(r):
                date += ", %d days old" % r["statement_age_days"]
            summary.append("| %s | %s | %s | %s | %s |"
                           % (cell(r["source"]), cell(r["verdict"]), cell(ph),
                              cell("+".join(r["wcag_versions"]) or "none"), cell(date)))
        else:
            summary.append("| %s | not read: %s | | | |" % (cell(r["source"]), cell(r["status"])))
    for pattern in missing:
        summary.append("| %s | no file matches | | | |" % cell(pattern))
    summary += ["", "It reads what a statement says, not whether a website is accessible, and it is "
                "not legal advice. [a11y-statement-check](https://github.com/munimtechnologies/"
                "a11y-statement-check), made by MV2 of Munim, Inc. with AI agents.", ""]
    if env.get("GITHUB_STEP_SUMMARY"):
        with open(env["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write("\n".join(summary) + "\n")
    if env.get("GITHUB_OUTPUT"):
        with open(env["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
            f.write("placeholder-pages=%d\npages-read=%d\nunread=%d\nold-statements=%d\n"
                    % (len(flagged), len(read), unread, len(old)))
    report = (env.get("STC_JSON_REPORT") or "").strip()
    if report:
        if not os.path.isabs(report):
            report = os.path.join(base, report)
        with open(report, "w", encoding="utf-8") as f:
            json.dump({"version": __version__, "checker_version": stc.__version__,
                       "today": today.isoformat(), "max_age_days": max_age_days,
                       "results": results, "unmatched_patterns": missing}, f, indent=1)
            f.write("\n")

    if flagged and fail_placeholder:
        return 1
    if unread and fail_unread:
        return 2
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass
    sys.exit(main())
