"""statement_template_check 0.4.0: is a website's accessibility statement still an unfinished template?

Reads one accessibility statement (a URL, a saved HTML file or a plain-text file) and reports:

  * placeholders that statement templates leave behind until someone fills them in, with the
    rules of MV2's published censuses of US government and school-district accessibility pages
    (https://github.com/munimtechnologies/title2-pdf-census): Revize's stock statement
    ("[Your Agency/Website Name]", "[X business days]"), the statement draft of the Accessibility
    Checker WordPress plugin ("[YOUR COMPANY NAME]", "[SPECIFIC STANDARD, VERSION, LEVEL]"),
    school-website templates ("the Your School website", "[Your School]",
    accessibility@yourschool.com, 555-555-5555, "within # business days") and the government
    template's "YOUR MUNICIPALITY", "NAME, TITLE, EMAIL, PHONE" and capitalised bracketed fields;
    since 0.3.0 also the fields and guidance notes of GOV.UK's sample accessibility statement for
    UK public sector websites ("[website name]", "[name of organisation]", "[scope of statement
    ...]", "[number]", "[date when it was first published]", "[Note: ...]", "[Select (a) ...]");
    since 0.4.0 also the fields and editing notes of the school statement template served on
    UK school websites built by Juniper Websites (formerly e4education): "[Website Link and
    Date]", "[Accessibility Email Address]", "[School Phone Number]", "[School Mailing Address]",
    "(School Name)", "[This is a sample accessibility statement ...", "[Delete as appropriate]";
  * which WCAG versions the page names (the ADA Title II rule for state and local governments,
    28 CFR 35.200, adopts WCAG 2.1 Level AA; GOV.UK's sample statement names WCAG 2.2 AA), and
    dated or stock wording worth a second look.

With --site it asks a site for the three stock addresses where those censuses found most
unfinished templates (/153/Accessibility, /accessibility_statement/index.php and
/accessibility-statement), honouring robots.txt, one request at a time with a pause between.

It reads what a statement says, not whether the website is accessible, and it is not legal
advice. Exit code: 1 if any page read has a template placeholder, 0 if none does, 2 if no page
could be read. Standard library only. Apache-2.0. Made by MV2 of Munim, Inc. with AI agents.
"""

import argparse
import html.parser
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser

__version__ = "0.4.0"

UA = ("statement-template-check/%s (MV2, Munim, Inc.; mv2@munimtech.com; reads public pages only)"
      % __version__)
MIN_TEXT = 200
MAX_BYTES = 3_000_000
STOCK_PATHS = (("civicplus", "/153/Accessibility"),
               ("revize", "/accessibility_statement/index.php"),
               ("accessibility-statement", "/accessibility-statement"))

# (group, id, pattern, ignore case). Vendor-specific rules come first: a stretch of text matched
# by an earlier rule is not counted again by a later, more general one. The GOV.UK sample's
# "[date]" field is the same text as Revize's "[Date]" and is reported as revize/date; so is the
# Juniper template's "[Date]", and its "[School Name]" is reported as school/school_bracket.
PLACEHOLDER_RULES = (
    ("revize", "agency_name", r"\[\s*your\s+agency\s*/\s*website\s+name\s*\]", True),
    ("revize", "date", r"\[\s*date\s*\]", True),
    ("revize", "contact_email", r"\[\s*contact\s+email\s*\]", True),
    ("revize", "contact_phone", r"\[\s*contact\s+phone\s*\]", True),
    ("revize", "agency_address", r"\[\s*agency\s+address\s*\]", True),
    ("revize", "x_business_days", r"\[\s*x\s+business\s+days\s*\]", True),
    ("accessibility-checker", "company_name", r"\[\s*(?:your\s+)?company\s+name\s*\]", True),
    ("accessibility-checker", "specific_standard",
     r"\[\s*specific\s+standard\s*,\s*version\s*,\s*level\s*\]", True),
    ("accessibility-checker", "features", r"\[\s*list\s+accessibility\s+features\s+here\s*\]", True),
    ("accessibility-checker", "working_to_fix",
     r"\[\s*list\s+items\s+you\s*['\u2019]?\s*re\s+working\s+to\s+fix\s+here\s*\]", True),
    ("accessibility-checker", "open_issues", r"\[\s*it\s+may\s+help\s+to\s+review\s+the\s+open\s+issues\s+tab", True),
    ("accessibility-checker", "accessibility_email",
     r"\[\s*your\s+accessibility\s+email\s+address\s*\]", True),
    ("accessibility-checker", "phone_number", r"\[\s*your\s+phone\s+number\s*\]", True),
    # GOV.UK's sample accessibility statement (for a fictional public sector website), as published
    # at gov.uk/government/publications/sample-accessibility-statement (read 2026-11-08).
    ("gov-uk", "sample_notice",
     r"\bsample\s+accessibility\s+statement\s+for\s+a\s+fictional\s+public\s+sector\s+website\b", True),
    ("gov-uk", "website_name", r"\[\s*website\s+name\s*\]", True),
    ("gov-uk", "scope", r"\[\s*scope\s+of\s+(?:the\s+)?statement\b[^\[\]]{0,100}\]", True),
    ("gov-uk", "organisation_name",
     r"\[\s*(?:the\s+)?name\s+of\s+(?:the\s+|your\s+)?organi[sz]ation\s*\]", True),
    ("gov-uk", "email_address", r"\[\s*email\s+address\s*\]", True),
    ("gov-uk", "phone", r"\[\s*(?:tele)?phone\s+number\s*\]", True),
    ("gov-uk", "other_contact", r"\[\s*add\s+any\s+other\s+contact\s+details\s*\]", True),
    ("gov-uk", "number_of_days", r"\[\s*number\s*\]", True),
    ("gov-uk", "add_link", r"\[\s*add\s+(?:a\s+)?link\s+to\b[^\[\]]{0,60}\]", True),
    ("gov-uk", "insert_one_of", r"\[\s*insert\s+one\s+of\s+the\s+following\b[^\[\]]{0,120}\]", True),
    ("gov-uk", "rough_timing", r"\[\s*rough\s+timing\s*\]", True),
    ("gov-uk", "example_document", r"\[\s*example\s+of\s+(?:a\s+)?non-essential\s+document\s*\]", True),
    ("gov-uk", "first_published", r"\[\s*date\s+when\s+it\s+was\s+first\s+published\s*\]", True),
    ("gov-uk", "last_reviewed", r"\[\s*date\s+when\s+it\s+was\s+last\s+reviewed\s*\]", True),
    ("gov-uk", "tester",
     r"\[\s*add\s+name\s+of\s+(?:the\s+)?organi[sz]ation\s+that\s+carried\s+out\b[^\[\]]{0,80}\]", True),
    ("gov-uk", "guidance_note", r"\[\s*note\s*:[^\[\]]{0,60}", True),
    ("gov-uk", "select_option", r"\[\s*select\s+\([abc]\)[^\[\]]{0,60}", True),
    # The school statement template served at /accessibility-statement/ on UK school websites built
    # by Juniper Websites (formerly e4education), read on live pages on 2026-11-09. The same rules
    # as JUNIPER_FIELD_RULES in title2-pdf-census's school_stock.py 0.1.0.
    ("juniper", "website_link_and_date", r"\[\s*website\s+link\s+and\s+date\s*\]", True),
    ("juniper", "accessibility_email", r"\[\s*accessibility\s+email\s+address\s*\]", True),
    ("juniper", "school_phone", r"\[\s*school\s+phone\s+number\s*\]", True),
    ("juniper", "school_address", r"\[\s*school\s+(?:mailing\s+)?address\s*\]", True),
    ("juniper", "school_name_round", r"\(\s*school\s+name\s*\)", True),
    ("juniper", "sample_notice", r"\[\s*this\s+is\s+a\s+sample\s+accessibility\s+statement\b", True),
    ("juniper", "prior_to_publication",
     r"\bprior\s+to\s+publication\s*,?\s+please\s+remove\s+this\s+text\b", True),
    ("juniper", "delete_as_appropriate", r"\[\s*delete\s+as\s+appropriate\b", True),
    ("juniper", "examples_only", r"\[\s*the\s+above\s+are\s+examples\s+only\b", True),
    ("juniper", "please_instruction", r"\[\s*please\s+(?:add|refer|use|remove)\b", True),
    ("juniper", "method_note", r"\[\s*set\s+out\s+the\s+method\b", True),
    ("juniper", "review_note", r"\[\s*it\s+is\s+recommended\s+that\s+statements\b", True),
    ("school", "school_bracket",
     r"\[\s*(?:(?:your|the|insert|name\s+of(?:\s+the)?)\s+)?(?:school|district|school\s+district|"
     r"organi[sz]ation|campus)(?:\s+(?:name|district|website|url))?\s*\]", True),
    ("school", "your_school", r"\bthe Your (?:School|District)\b", False),
    ("school", "your_domain",
     r"\byour(?:school|district|website|domain|site|organi[sz]ation)\.(?:com|org|net|edu|us)\b", True),
    ("school", "fake_phone", r"\b555[\s.-]555[\s.-]5555\b", False),
    ("school", "hash_days", r"\bwithin\s+#\s+(?:business\s+|working\s+)?days\b", True),
    ("government", "your_municipality", r"\bYOUR ?MUNICIPALITY\b", False),
    ("government", "template_note", r"only meant as a template", True),
    ("government", "contact_block", r"\bNAME\W{0,10}TITLE\W{0,10}EMAIL\W{0,10}PHONE\b", False),
    ("government", "caps_bracket",
     r"\[[^\[\]]{0,40}?\b(?:INSERT [A-Z]|NAME OF\b|URL OF\b|(?:CITY|COUNTY|TOWN|VILLAGE|AGENCY|"
     r"ORGANI[SZ]ATION|ENTITY) NAME\b|PHONE NUMBER\b|EMAIL ADDRESS\b|YOUR [A-Z]{3,})[^\[\]]{0,60}\]",
     False),
    ("generic", "insert_bracket", r"\[\s*insert\b[^\[\]]{0,60}\]", True),
)
PLACEHOLDER_RES = tuple((g, i, re.compile(p, re.I if ic else 0)) for g, i, p, ic in PLACEHOLDER_RULES)
GROUPS = ("revize", "accessibility-checker", "gov-uk", "juniper", "school", "government", "generic")

# Bracketed text that may be a placeholder (reported as "possible", never counted). Cloudflare's
# "[email protected]" (an email address hidden from scrapers) is not one.
POSSIBLE_RE = re.compile(r"\[\s*(?:your|insert|enter|contact|agency|organi[sz]ation|company|name|"
                         r"website|phone|email|address|date|list|summarize|official)\b[^\]\n]{0,60}\]",
                         re.I)
EMAIL_PROTECTED_RE = re.compile(r"\[\s*email\s+protected\s*\]", re.I)

# Template wording, filled in or not (described only). gov_uk_sample is the compliance sentence
# that UK public sector bodies must keep unchanged ("This website is partially compliant with the
# Web Content Accessibility Guidelines version 2.2 AA standard ..."); juniper_school is the closing
# sentence of the Juniper Websites school template ("... values diversity and inclusion and is
# committed to providing an accessible online experience ...").
TEMPLATE_RULES = (
    ("t2017_your_school", r"a\s+positive\s+place\s+for\s+everyone"),
    ("finalsite_2026", r"\bbuilt\s+with\s+WCAG\s+2\.1\s+AA\s+guidelines\s+in\s+mind\b"),
    ("revize", r"our commitment\s*:?\s*we aim to follow the\s*web content accessibility guidelines"),
    ("accessibility_checker", r"is\s+committed\s+to\s+providing\s+a\s+fully\s+accessible\s+website\s+"
                              r"experience\s+for\s+all\s+users\s+of\s+all\s+abilities"),
    ("stock_508", r"We work to comply with Section 508 as well as"),
    ("gov_uk_sample", r"\bThis\s+(?:website|app|application)\s+is\s+(?:fully|partially|not)\s+compliant\s+"
                      r"with\s+the\s+Web\s+Content\s+Accessibility\s+Guidelines\b"),
    ("juniper_school", r"values\s+diversity\s+and\s+inclusion\s+and\s+is\s+committed\s+to\s+"
                       r"providing\s+an\s+accessible\s+online\s+experience"),
)
TEMPLATE_RES = tuple((t, re.compile(p, re.I)) for t, p in TEMPLATE_RULES)

V = r"2\.[0-2](?!\.?\d)"
VERSION_RE = re.compile(
    r"(?:\bWCAG|\bWeb\s+Content\s+Accessibility\s+Guidelines)\s*(?:\(WCAG\)\s*)?,?\s*"
    r"(?:version\s*|v\.?\s*)?(" + V + r"(?:\s*(?:,\s*(?:and|or)?|and|or|&|/|-)\s*(?:WCAG\s*)?"
    + V + r")*)", re.I)
WCAG_ANY_RE = re.compile(r"\bWCAG|\bWeb\s+Content\s+Accessibility\s+Guidelines", re.I)
DATE_2026_RE = re.compile(r"\bApr(?:il|\.)?\s+24(?:th)?,?\s+2026\b|\b24\s+April,?\s+2026\b|"
                          r"\b0?4/24/(?:20)?26\b|\b2026-04-24\b", re.I)
DATE_2027_RE = re.compile(r"\bApr(?:il|\.)?\s+26(?:th)?,?\s+2027\b|\b26\s+April,?\s+2027\b|"
                          r"\b0?4/26/(?:20)?27\b|\b2027-04-26\b", re.I)
DATE_2028_RE = re.compile(r"\bApr(?:il|\.)?\s+26(?:th)?,?\s+2028\b|\b26\s+April,?\s+2028\b|"
                          r"\b0?4/26/(?:20)?28\b|\b2028-04-26\b", re.I)
GENERATOR_RE = re.compile(r"\bAccessibility\s+Statement\s+Generator\b", re.I)

NOTES = {
    "placeholder": "template placeholders are still in the text: fill them in (name, contact, "
                   "standard, dates) or remove them",
    "possible_placeholder": "bracketed text that may be an unfilled placeholder: %s",
    "only_wcag_2_0": "names WCAG 2.0 only; the ADA Title II rule (28 CFR 35.200) adopts WCAG 2.1 "
                     "Level AA, so check which version the site actually targets",
    "uk_older_wcag": "uses GOV.UK's compliance wording but names WCAG %s as the highest version; "
                     "GOV.UK's current sample statement names WCAG 2.2 AA, so check which version "
                     "the site was tested against",
    "no_wcag_version": "mentions WCAG without naming a version",
    "no_wcag": "does not mention WCAG at all",
    "old_title2_date": "names April 24, 2026 (the first ADA Title II date of the 2024 rule) and no "
                       "later date; an interim final rule of 2026-04-20 moved the dates to April "
                       "26, 2027 (50,000 or more people) and April 26, 2028 (under 50,000, and "
                       "special districts)",
    "generator": "keeps the 'Accessibility Statement Generator' credit line of a 2017 template",
    "stock_508": "keeps a vendor's stock sentence 'We work to comply with Section 508 as well "
                 "as ...'",
}


# ---------------------------------------------------------------- reading text

def check_text(text):
    """What one statement's visible text says (see the module docstring)."""
    text = " ".join(text.replace("\xa0", " ").split())
    found, spans = [], []
    for group, rid, rx in PLACEHOLDER_RES:
        for m in rx.finditer(text):
            if not any(m.start() < e and s < m.end() for s, e in spans):
                spans.append((m.start(), m.end()))
                found.append({"group": group, "id": rid, "text": m.group(0)[:100]})
                break
    possible = ""
    if not found:
        for m in POSSIBLE_RE.finditer(text):
            if not EMAIL_PROTECTED_RE.fullmatch(m.group(0)):
                possible = m.group(0)[:100]
                break
    versions = set()
    for m in VERSION_RE.finditer(text):
        versions.update(re.findall(r"2\.[0-2]", m.group(1)))
    wcag_named = bool(WCAG_ANY_RE.search(text))
    templates = [t for t, rx in TEMPLATE_RES if rx.search(text)]
    uk = "gov_uk_sample" in templates
    highest = max(versions) if versions else ""
    dates = {"2026-04-24": bool(DATE_2026_RE.search(text)),
             "2027-04-26": bool(DATE_2027_RE.search(text)),
             "2028-04-26": bool(DATE_2028_RE.search(text))}
    notes = []

    def note(key, *args):
        notes.append({"id": key, "message": NOTES[key] % args if args else NOTES[key]})
    if found:
        note("placeholder")
    if possible:
        note("possible_placeholder", possible)
    if uk:
        if highest in ("2.0", "2.1"):
            note("uk_older_wcag", highest)
    elif versions == {"2.0"}:
        note("only_wcag_2_0")
    if wcag_named and not versions:
        note("no_wcag_version")
    if not wcag_named:
        note("no_wcag")
    if (not uk and dates["2026-04-24"]
            and not (dates["2027-04-26"] or dates["2028-04-26"])):
        note("old_title2_date")
    if GENERATOR_RE.search(text):
        note("generator")
    if "stock_508" in templates:
        note("stock_508")
    return {"placeholder": bool(found), "placeholders": found,
            "groups": [g for g in GROUPS if any(p["group"] == g for p in found)],
            "possible_placeholder": possible, "templates": templates,
            "wcag_named": wcag_named, "wcag_versions": sorted(versions),
            "highest": highest, "dates": dates,
            "notes": notes, "text_chars": len(text),
            "verdict": ("unfinished template (%d placeholder%s)"
                        % (len(found), "" if len(found) == 1 else "s")) if found
                       else "no template placeholder found"}


# ---------------------------------------------------------------- reading HTML

class _Text(html.parser.HTMLParser):
    SKIP = ("script", "style", "noscript", "template", "svg")

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self._skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def visible_text(body, ctype=""):
    """The visible text of an HTML page (bytes or str), scripts and styles left out."""
    if isinstance(body, bytes):
        m = re.search(r"charset=([\w-]+)", ctype or "", re.I)
        try:
            body = body.decode(m.group(1) if m else "utf-8", "replace")
        except LookupError:
            body = body.decode("utf-8", "replace")
    p = _Text()
    try:
        p.feed(body)
        p.close()
    except Exception:  # a broken page keeps what was parsed before the error
        pass
    return " ".join(" ".join(p.parts).replace("\xa0", " ").split())


def is_html(ctype, body):
    if "html" in (ctype or "").lower():
        return True
    head = body[:300].lstrip().lower()
    return head.startswith(b"<!doctype html") or head.startswith(b"<html")


# ---------------------------------------------------------------- reading the web

def http_get(url, timeout=20):
    """(status, final url, content type, body); never raises (status 0 on network errors)."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.geturl(), r.headers.get("Content-Type", ""), r.read(MAX_BYTES)
    except urllib.error.HTTPError as e:
        return e.code, url, "", b""
    except Exception:  # DNS, TLS, timeouts, resets
        return 0, url, "", b""


def robots_checker(get):
    """allowed(url): each host's robots.txt is read once (401 or 403 means nothing allowed)."""
    cache = {}

    def allowed(url):
        p = urllib.parse.urlsplit(url)
        key = "%s://%s" % (p.scheme, p.netloc)
        if key not in cache:
            status, _, _, body = get(key + "/robots.txt")
            rp = urllib.robotparser.RobotFileParser()
            if status == 200 and body:
                rp.parse(body.decode("utf-8", "replace").splitlines())
            elif status in (401, 403):
                rp.disallow_all = True
            else:
                rp.allow_all = True
            cache[key] = rp
        return cache[key].can_fetch(UA, url)
    return allowed


def read_page(url, get=http_get, allowed=None, stock=""):
    """Read one page and check it. stock: the stock address's name when the address was not given
    by the user (a redirect from it to the home page is then not read as a statement)."""
    out = {"source": url, "final_url": "", "status": "", "stock_address": stock}
    if allowed is not None and not allowed(url):
        out["status"] = "robots"
        return out
    status, final, ctype, body = get(url)
    out["final_url"] = final or url
    if status != 200:
        out["status"] = "http_%d" % status
        return out
    if not is_html(ctype, body):
        out["status"] = "not_html"
        return out
    if stock and urllib.parse.urlsplit(out["final_url"]).path in ("", "/"):
        out["status"] = "redirect_home"
        return out
    text = visible_text(body, ctype)
    if len(text) < MIN_TEXT:
        out.update(status="short", text_chars=len(text))
        return out
    out["status"] = "ok"
    out.update(check_text(text))
    return out


def site_base(site):
    s = site.strip()
    if not re.match(r"https?://", s, re.I):
        s = "https://" + s
    p = urllib.parse.urlsplit(s)
    return "%s://%s" % (p.scheme.lower(), p.netloc.lower())


def check_site(site, get=http_get, sleep=time.sleep, delay=1.0):
    """The three stock addresses of one site, robots.txt honoured, one request at a time."""
    allowed = robots_checker(get)
    base = site_base(site)
    pages = []
    for i, (name, path) in enumerate(STOCK_PATHS):
        if i:
            sleep(delay)
        pages.append(read_page(base + path, get=get, allowed=allowed, stock=name))
    return pages


def check_file(path, html_file=True):
    """A saved HTML page (html_file) or a plain-text statement on disk."""
    with open(path, "rb") as f:
        body = f.read()
    text = visible_text(body) if html_file else body.decode("utf-8", "replace")
    out = {"source": path, "final_url": "", "status": "ok", "stock_address": ""}
    out.update(check_text(text))
    return out


# ---------------------------------------------------------------- output

def format_result(r):
    lines = [r["source"]]
    if r["status"] != "ok":
        lines.append("  not read: %s" % r["status"])
        return lines
    where = " (stock address: %s)" % r["stock_address"] if r.get("stock_address") else ""
    lines.append("  read: %d characters of text%s" % (r["text_chars"], where))
    for p in r["placeholders"]:
        lines.append("  PLACEHOLDER %s/%s: %s" % (p["group"], p["id"], p["text"]))
    if r["templates"]:
        lines.append("  template wording: %s" % ", ".join(r["templates"]))
    lines.append("  WCAG versions named: %s" % ("+".join(r["wcag_versions"]) or "none"))
    for n in r["notes"]:
        lines.append("  NOTE %s: %s" % (n["id"], n["message"]))
    lines.append("  verdict: %s" % r["verdict"])
    return lines


def exit_code(results):
    if any(r.get("placeholder") for r in results):
        return 1
    return 0 if any(r.get("status") == "ok" for r in results) else 2


def build_parser():
    parser = argparse.ArgumentParser(
        prog="statement_template_check.py", description=__doc__.splitlines()[0],
        epilog="Exit code 1: a template placeholder was found; 0: none found; 2: nothing read.")
    parser.add_argument("urls", nargs="*", help="accessibility statement URLs to read")
    parser.add_argument("--site", action="append", default=[],
                        help="a site (example.gov) whose three stock statement addresses to try")
    parser.add_argument("--file", action="append", default=[], help="a saved HTML page")
    parser.add_argument("--text", action="append", default=[], help="a plain-text statement")
    parser.add_argument("--json", action="store_true", help="print JSON instead of text")
    parser.add_argument("--delay", type=float, default=1.0,
                        help="seconds between requests to one site (default 1)")
    parser.add_argument("--version", action="version", version=__version__)
    return parser


def main(argv=None, get=http_get, sleep=time.sleep, out=None):
    out = out or sys.stdout
    args = build_parser().parse_args(argv)
    if not (args.urls or args.site or args.file or args.text):
        build_parser().print_usage(out)
        return 2
    results = []
    for url in args.urls:
        results.append(read_page(url, get=get))
    for site in args.site:
        results.extend(check_site(site, get=get, sleep=sleep, delay=args.delay))
    for path in args.file:
        results.append(check_file(path, html_file=True))
    for path in args.text:
        results.append(check_file(path, html_file=False))
    code = exit_code(results)
    if args.json:
        json.dump({"version": __version__, "exit_code": code, "results": results}, out, indent=1)
        out.write("\n")
    else:
        for r in results:
            out.write("\n".join(format_result(r)) + "\n")
        n = sum(1 for r in results if r.get("placeholder"))
        out.write("statement_template_check %s: %d of %d page%s read with a template placeholder\n"
                  % (__version__, n, sum(1 for r in results if r.get("status") == "ok"),
                     "" if len(results) == 1 else "s"))
    return code


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass
    sys.exit(main())
