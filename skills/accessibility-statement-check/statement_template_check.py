"""statement_template_check 0.10.1: is a website's accessibility statement still an unfinished template?

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
    dated or stock wording worth a second look;
  * since 0.5.0, the statement's own latest "last reviewed / updated" and "prepared / published
    on" dates, with a note when the later of them is more than --max-age-days (default 365) old:
    GOV.UK's sample statement asks public sector bodies to review their statement at least once a
    year, and MV2's census of UK council statements (November 2026) found 105 of 271 dated ones
    carrying a date more than a year old. The date reader is the one of title2-pdf-census's
    council_stock.py 0.1.0;
  * since 0.6.0, a note (hub_page) when an HTML page names no WCAG version and gives no statement
    date but links to what looks like the accessibility statement itself, with that link's
    address: the page probably sits in front of the statement. MV2's comparison of two automated
    censuses of UK council statements (November 2026) found that 12 of the 23 council pages one
    census scored lowest were such pages, each linking straight to a statement the other census
    read; none of the 13 low-score pages read again named a WCAG version or gave a date.
  * since 0.7.0, a date right after "will be", "is due to be", "next" and the like ("It will be
    reviewed in March 2027") is a planned review, not the latest one, and is no longer read as the
    statement's date. MV2's census of UK government organisations' statements (November 2026)
    found one statement whose date was such a planned review.
  * since 0.8.0, which editions of EN 301 549 (the European standard for accessible ICT) the page
    names ("EN 301 549 V3.2.1 (2021-03)", "EN 301-549 version 2.1.2"), with a note
    (older_en301549) when the highest one named is older than V3.2.1 (2021-03), the edition cited
    in the EU's Official Journal for the Web Accessibility Directive since 2021 (Implementing
    Decision (EU) 2021/1339). ETSI, CEN and CENELEC published V4.1.1 (2026-09), whose web clause
    covers WCAG 2.2, on 2 September 2026.
  * since 0.9.0, a note (old_504_date) when a page that names Section 504, 45 CFR part 84 or the
    US Department of Health and Human Services (HHS) gives May 11, 2026 or May 10, 2027, the web
    compliance dates of HHS's 2024 Section 504 rule (45 CFR 84.84(b)), and neither later date: an
    HHS interim final rule published on 11 May 2026 (91 FR 25507) moved them to May 11, 2027
    (recipients with fifteen or more employees) and May 10, 2028 (fewer than fifteen). Hospitals,
    health centres and other recipients of HHS funding fall under that rule.
  * since 0.10.0, a note (may_11_2028) when such a page gives May 11, 2028 and not May 10, 2028:
    the date in 45 CFR 84.84(b)(2) for recipients with fewer than fifteen employees is May 10,
    2028, and published guides were found giving May 11, 2028 instead (read on 2026-11-12). A page
    that gives May 11, 2028 no longer gets old_504_date, since it was written after the change.
  * since 0.10.1, an April 24, 2026 that is only the statement's own "last updated / reviewed" or
    "prepared / published on" date no longer counts as the first ADA Title II date for the note
    old_title2_date (the JSON's dates still report every April 24, 2026). MV2's census of US
    special districts' accessibility pages (November 2026) found a statement "Last updated: April
    24, 2026" read as the old Title II date.

With --site it asks a site for the three stock addresses where those censuses found most
unfinished templates (/153/Accessibility, /accessibility_statement/index.php and
/accessibility-statement), honouring robots.txt, one request at a time with a pause between. It
never follows a link it finds on a page.

It reads what a statement says, not whether the website is accessible, and it is not legal
advice. Exit code: 1 if any page read has a template placeholder, 0 if none does, 2 if no page
could be read (an old date, an older EN 301 549 edition, an old or misquoted Section 504 date or a
hub page is a note only and never changes the exit code).
Standard library only. Apache-2.0. Made by MV2 of Munim, Inc. with AI agents.
"""

import argparse
import calendar
import datetime
import html.parser
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser

__version__ = "0.10.1"

UA = ("statement-template-check/%s (MV2, Munim, Inc.; mv2@munimtech.com; reads public pages only)"
      % __version__)
MIN_TEXT = 200
MAX_BYTES = 3_000_000
MAX_AGE_DAYS = 365
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


# HHS's Section 504 rule (since 0.9.0). The rule of 9 May 2024 (89 FR 40193; 45 CFR 84.84(b))
# asked recipients of HHS funding to meet WCAG 2.1 Level AA on the web and in mobile apps by May
# 11, 2026 (fifteen or more employees) and May 10, 2027 (fewer than fifteen). An interim final
# rule published on 11 May 2026 (91 FR 25507) moved both dates by a year: May 11, 2027 and May
# 10, 2028 (45 CFR 84.84(b)(1) and (2) as amended; read on eCFR on 2026-11-12). The note is given
# only when the page also names Section 504, 45 CFR part 84 or HHS, so a date on a page about
# something else is never read as one of these.
def may_date_re(day, year):
    """May <day>, <year> as "May 11, 2026", "May 11th 2026", "11 May 2026", "05/11/2026",
    "5/11/26" or "2026-05-11" (month first in the numeric form, as on US pages)."""
    return re.compile(r"\bMay\.?\s+%d(?:th)?,?\s+%d\b|\b%d(?:th)?\s+(?:of\s+)?May,?\s+%d\b|"
                      r"\b0?5/%d/(?:20)?%02d\b|\b%d-05-%d\b"
                      % (day, year, day, year, day, year % 100, year, day), re.I)


SECTION_504_RE = re.compile(r"\bSec(?:tion|\.)\s*504\b|\u00a7\s*504\b|"
                            r"\b45\s*C\.?\s*F\.?\s*R\.?\s*(?:Part\s*|\u00a7+\s*)?84\b|"
                            r"\bHHS\b|\bHealth\s+(?:and|&)\s+Human\s+Services\b", re.I)
HHS504_DATES = (("2026-05-11", may_date_re(11, 2026)), ("2027-05-10", may_date_re(10, 2027)),
                ("2027-05-11", may_date_re(11, 2027)), ("2028-05-10", may_date_re(10, 2028)))
HHS504_OLD = (("2026-05-11", "May 11, 2026"), ("2027-05-10", "May 10, 2027"))
HHS504_NEW = ("2027-05-11", "2028-05-10")
# May 11, 2028 is no date of the rule: the small-recipient date is May 10, 2028 (since 0.10.0).
# Guides read on 2026-11-12 gave May 11, 2028 for it, by carrying the large-recipient day over.
# Only a page written after the 2026 change can give it, so it also silences old_504_date.
MAY_11_2028_RE = may_date_re(11, 2028)

# EN 301 549, the European standard for accessible ICT (since 0.8.0). An edition is read only when
# "V" or "version" comes right before its number, after "EN 301 549" (or "EN 301-549") and at most
# 25 other characters with no full stop or digit in them: "EN 301 549 V3.2.1 (2021-03)", "ETSI EN
# 301 549 v.2.1.2", "EN 301-549, version 3.2.1". A bare clause number ("EN 301 549 clause 9.1.1.1")
# is not an edition. V3.2.1 (2021-03), whose web clause follows WCAG 2.1, is the edition cited in
# the EU's Official Journal for the Web Accessibility Directive since 2021 (Implementing Decision
# (EU) 2021/1339, which withdrew V2.1.2 (2018-08) from 12 February 2022); V4.1.1 (2026-09), whose
# web clause covers WCAG 2.2, was published on 2 September 2026.
EN_RE = re.compile(r"\bEN\s*301[\s-]?549\b", re.I)
EN_VERSION_RE = re.compile(r"\bEN\s*301[\s-]?549\b[^.\d]{0,25}?(?:\bv\.?\s*|\bversion\s*)"
                           r"([1-9])\.(\d{1,2})\.(\d{1,2})(?!\.?\d)", re.I)
EN_CITED = (3, 2, 1)

# The statement's own dates (since 0.5.0; the reader of title2-pdf-census's council_stock.py
# 0.1.0, with a wider range of years). "3 June 2024", "June 3, 2024", "June 2024" (read as the
# month's last day), "03/06/2024" (day first, as in the UK, unless the second number is above
# 12) and "2024-06-03" are read after "last reviewed / updated / revised", "reviewed / updated /
# revised on / in" or "prepared / published / created / written / produced on / in".
MON = (r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|"
       r"sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?")
YEAR = r"(?:19|20)\d\d"
DATE = (r"(?:\b(?P<d1>\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(?P<m1>" + MON + r")\s*,?\s*(?P<y1>" + YEAR
        + r")\b|\b(?P<m2>" + MON + r")\s+(?P<d2>\d{1,2})(?:st|nd|rd|th)?\s*,?\s*(?P<y2>" + YEAR
        + r")\b|\b(?P<m3>" + MON + r")\s*,?\s*(?P<y3>" + YEAR
        + r")\b|\b(?P<d4>\d{1,2})[/.](?P<m4>\d{1,2})[/.](?P<y4>" + YEAR
        + r")\b|\b(?P<y5>" + YEAR + r")-(?P<m5>\d{1,2})-(?P<d5>\d{1,2})\b)")
REVIEW_RE = re.compile(r"\b(?:last\s+(?:reviewed|updated|revised|review)|(?:reviewed|updated|revised)"
                       r"\s+(?:on|in))\b[^.\d]{0,30}?" + DATE, re.I)
PREPARED_RE = re.compile(r"\b(?:prepared|published|created|written|produced)\s+(?:on|in)\b"
                         r"[^.\d]{0,30}?" + DATE, re.I)
MONTHS = {m: i for i, m in enumerate(("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug",
                                      "sep", "oct", "nov", "dec"), 1)}
DATE_YEARS = (2000, 2099)  # dates outside these years are not read as statement dates
# A date right after "will be", "shall be", "should be", "must be", "to be" or "next" ("It will be
# reviewed in March 2027", "is due to be updated on ...") is a planned review or publication, not
# the latest one, so it is not read as a statement date (since 0.7.0).
PLANNED_RE = re.compile(r"\b(?:will|shall|should|must|to|next)\s+(?:be\s+)?(?:next\s+)?$", re.I)
PLANNED_WINDOW = 25

# Links to a statement (since 0.6.0): the link text says "accessibility statement" (or the Welsh
# "datganiad hygyrchedd"), or the address does ("accessibility-statement", "accessibility_statement",
# "AccessibilityStatement"). These are the two strongest link scores of title2-pdf-census's
# council_stock.py 0.1.0. At most MAX_STATEMENT_LINKS addresses are kept, in page order.
STATEMENT_TEXT_RE = re.compile(r"accessibility\s+statement|datganiad\s+hygyrchedd", re.I)
STATEMENT_HREF_RE = re.compile(r"accessibility[-_ ]?statement", re.I)
MAX_STATEMENT_LINKS = 5
MAX_LINK_CHARS = 300

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
    "old_504_date": "names %s, a web compliance date of HHS's 2024 Section 504 rule (45 CFR "
                    "84.84), and neither later date; an HHS interim final rule published on "
                    "2026-05-11 (91 FR 25507) moved the dates to May 11, 2027 (recipients with "
                    "fifteen or more employees) and May 10, 2028 (fewer than fifteen), so check "
                    "which date the page means",
    "may_11_2028": "names May 11, 2028, which is not a date of HHS's Section 504 web rule; 45 CFR "
                   "84.84(b) as amended (91 FR 25507) gives May 11, 2027 for recipients with "
                   "fifteen or more employees and May 10, 2028 for fewer than fifteen, so check "
                   "which date the page means",
    "generator": "keeps the 'Accessibility Statement Generator' credit line of a 2017 template",
    "stock_508": "keeps a vendor's stock sentence 'We work to comply with Section 508 as well "
                 "as ...'",
    "older_en301549": "names EN 301 549 V%s as the highest edition; since 2021 the edition cited "
                      "in the EU's Official Journal for the Web Accessibility Directive is V3.2.1 "
                      "(2021-03, on WCAG 2.1; Implementing Decision (EU) 2021/1339), and V4.1.1 "
                      "(2026-09, on WCAG 2.2) was published on 2 September 2026, so check which "
                      "edition the site was tested against",
    "old_statement_date": "the statement's latest date (%s %s) is %d days before %s; GOV.UK's "
                          "sample statement asks public sector bodies to review their statement "
                          "at least once a year, so check that it is still current",
    "hub_page": "names no WCAG version and gives no statement date, but links to what looks like "
                "the accessibility statement itself (%s); this page probably sits in front of the "
                "statement, so check that address too (this tool never follows it by itself)",
}


# ---------------------------------------------------------------- HHS Section 504 dates

def hhs504(text):
    """(named, dates): whether the text names Section 504, 45 CFR part 84 or HHS, and for each of
    the four Section 504 web dates (ISO keys) whether the text gives it. Since 0.9.0."""
    flat = " ".join(text.split())
    return (bool(SECTION_504_RE.search(flat)),
            {key: bool(rx.search(flat)) for key, rx in HHS504_DATES})


def gives_may_11_2028(text):
    """Whether the text gives May 11, 2028 (in any wording may_date_re reads). Since 0.10.0."""
    return bool(MAY_11_2028_RE.search(" ".join(text.split())))


# ---------------------------------------------------------------- EN 301 549 editions

def en_key(version):
    """A sortable tuple from an edition number such as '3.2.1'."""
    return tuple(int(x) for x in version.split("."))


def en301549_versions(text):
    """(named, editions): whether the text names EN 301 549 at all, and the editions it names
    ('3.2.1' and the like, oldest first, no repeats). Since 0.8.0."""
    flat = " ".join(text.split())
    found = {"%s.%s.%s" % m.groups() for m in EN_VERSION_RE.finditer(flat)}
    return bool(EN_RE.search(flat)), sorted(found, key=en_key)


# ---------------------------------------------------------------- statement dates

def _date(m):
    """A datetime.date from one DATE match (a month without a day reads as its last day), or None."""
    g = m.groupdict()
    try:
        if g["y1"]:
            y, mo, d = int(g["y1"]), MONTHS[g["m1"].lower().rstrip(".")[:3]], int(g["d1"])
        elif g["y2"]:
            y, mo, d = int(g["y2"]), MONTHS[g["m2"].lower().rstrip(".")[:3]], int(g["d2"])
        elif g["y3"]:
            y, mo = int(g["y3"]), MONTHS[g["m3"].lower().rstrip(".")[:3]]
            d = calendar.monthrange(y, mo)[1]
        elif g["y4"]:
            y, mo, d = int(g["y4"]), int(g["m4"]), int(g["d4"])
            if mo > 12 and d <= 12:  # month/day/year
                mo, d = d, mo
        else:
            y, mo, d = int(g["y5"]), int(g["m5"]), int(g["d5"])
        if not DATE_YEARS[0] <= y <= DATE_YEARS[1]:
            return None
        return datetime.date(y, mo, d)
    except (KeyError, ValueError):
        return None


def _planned(flat, m):
    """True when the words right before a date phrase make it a planned date (since 0.7.0)."""
    return bool(PLANNED_RE.search(flat[max(0, m.start() - PLANNED_WINDOW):m.start()]))


def statement_dates(text):
    """(review_date, prepared_date, statement_date, source) as ISO strings ('' when none): the
    latest 'last reviewed / updated' date, the latest 'prepared / published on' date, and the
    later of the two ('reviewed' or 'prepared')."""
    flat = " ".join(text.split())
    reviews = [d for d in (_date(m) for m in REVIEW_RE.finditer(flat)
                           if not _planned(flat, m)) if d]
    prepared = [d for d in (_date(m) for m in PREPARED_RE.finditer(flat)
                            if not _planned(flat, m)) if d]
    r = max(reviews) if reviews else None
    p = max(prepared) if prepared else None
    if r and (not p or r >= p):
        s, src = r, "reviewed"
    elif p:
        s, src = p, "prepared"
    else:
        s, src = None, ""
    iso = lambda d: d.isoformat() if d else ""  # noqa: E731
    return iso(r), iso(p), iso(s), src


def title2_2026(text):
    """Whether the text gives April 24, 2026 other than as the statement's own date (since
    0.10.1): an April 24, 2026 that lies inside a 'last reviewed / updated' or 'prepared /
    published on' date phrase ("Last updated: April 24, 2026") is the day the statement was
    written or reviewed, not the first ADA Title II compliance date, so it does not count."""
    flat = " ".join(text.split())
    own = [m.span() for rx in (REVIEW_RE, PREPARED_RE) for m in rx.finditer(flat)]
    return any(not any(s <= m.start() and m.end() <= e for s, e in own)
               for m in DATE_2026_RE.finditer(flat))


# ---------------------------------------------------------------- reading text

def check_text(text, today=None, max_age_days=MAX_AGE_DAYS):
    """What one statement's visible text says (see the module docstring). With today (a
    datetime.date), a statement whose latest date is more than max_age_days before it gets the
    note old_statement_date (max_age_days 0 or less turns that note off)."""
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
    old_title2 = title2_2026(text)
    named_504, dates_504 = hhs504(text)
    may_11_2028 = gives_may_11_2028(text)
    review, prepared, stated, source = statement_dates(text)
    en_named, en_versions = en301549_versions(text)
    en_highest = en_versions[-1] if en_versions else ""
    age = None
    if today is not None and stated:
        age = (today - datetime.date.fromisoformat(stated)).days
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
    if (not uk and old_title2
            and not (dates["2027-04-26"] or dates["2028-04-26"])):
        note("old_title2_date")
    old_504 = [words for key, words in HHS504_OLD if dates_504[key]]
    if (named_504 and old_504 and not may_11_2028
            and not any(dates_504[key] for key in HHS504_NEW)):
        note("old_504_date", " and ".join(old_504))
    if named_504 and may_11_2028 and not dates_504["2028-05-10"]:
        note("may_11_2028")
    if GENERATOR_RE.search(text):
        note("generator")
    if "stock_508" in templates:
        note("stock_508")
    if en_highest and en_key(en_highest) < EN_CITED:
        note("older_en301549", en_highest)
    if age is not None and max_age_days > 0 and age > max_age_days:
        note("old_statement_date", source, stated, age, today.isoformat())
    return {"placeholder": bool(found), "placeholders": found,
            "groups": [g for g in GROUPS if any(p["group"] == g for p in found)],
            "possible_placeholder": possible, "templates": templates,
            "wcag_named": wcag_named, "wcag_versions": sorted(versions),
            "highest": highest, "dates": dates,
            "section_504_named": named_504, "hhs504_dates": dates_504,
            "hhs504_may_11_2028": may_11_2028,
            "review_date": review, "prepared_date": prepared, "statement_date": stated,
            "date_source": source, "statement_age_days": age,
            "en301549_named": en_named, "en301549_versions": en_versions,
            "en301549_highest": en_highest,
            "statement_links": [], "hub_page": False,
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


def _decode(body, ctype=""):
    if isinstance(body, bytes):
        m = re.search(r"charset=([\w-]+)", ctype or "", re.I)
        try:
            body = body.decode(m.group(1) if m else "utf-8", "replace")
        except LookupError:
            body = body.decode("utf-8", "replace")
    return body


def visible_text(body, ctype=""):
    """The visible text of an HTML page (bytes or str), scripts and styles left out."""
    body = _decode(body, ctype)
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


class _Links(html.parser.HTMLParser):
    """(href, text) of every <a href>, the text including aria-label and title (since 0.6.0)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links, self._href, self._text = [], None, []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        if self._href is not None:
            self.close_link()
        a = dict(attrs)
        if a.get("href") is None:
            return
        self._href = a.get("href") or ""
        self._text = [a.get("aria-label") or "", a.get("title") or ""]

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self.close_link()

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def close_link(self):
        self.links.append((self._href, " ".join(" ".join(self._text).split())))
        self._href, self._text = None, []


def find_links(body, ctype=""):
    """(href, text) of every link on an HTML page (bytes or str), in page order."""
    p = _Links()
    try:
        p.feed(_decode(body, ctype))
        p.close()
    except Exception:  # a broken page keeps what was parsed before the error
        pass
    if p._href is not None:
        p.close_link()
    return p.links


def page_key(url):
    """host without 'www.' plus path, lower case, without a trailing slash, query or fragment."""
    try:
        p = urllib.parse.urlsplit((url or "").strip())
        host = (p.hostname or "").lower().rstrip(".")
    except ValueError:
        return ""
    if host.startswith("www."):
        host = host[4:]
    return host + urllib.parse.unquote(p.path).lower().rstrip("/")


def statement_links(links, page_url=""):
    """The absolute addresses (page order, no repeats, at most MAX_STATEMENT_LINKS) of the links
    whose text or address says accessibility statement, other than the page itself. Relative links
    are resolved against page_url; a saved file has none, so only its absolute links count."""
    own, out = page_key(page_url), []
    for href, text in links:
        href = (href or "").strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        try:
            url = urllib.parse.urldefrag(urllib.parse.urljoin(page_url or "", href))[0]
        except ValueError:
            continue
        if not url.lower().startswith(("http://", "https://")) or len(url) > MAX_LINK_CHARS:
            continue
        if not (STATEMENT_TEXT_RE.search(text or "")
                or STATEMENT_HREF_RE.search(urllib.parse.unquote(href))):
            continue
        if (own and page_key(url) == own) or url in out:
            continue
        out.append(url)
        if len(out) == MAX_STATEMENT_LINKS:
            break
    return out


def add_links(r, body, ctype="", page_url=""):
    """Adds statement_links and, when the page names no WCAG version, gives no statement date,
    uses no GOV.UK compliance sentence, has no placeholder and links to a statement, hub_page
    and its note (since 0.6.0)."""
    links = statement_links(find_links(body, ctype), page_url)
    hub = bool(links and not r["wcag_versions"] and not r["statement_date"]
               and "gov_uk_sample" not in r["templates"] and not r["placeholder"])
    r["statement_links"], r["hub_page"] = links, hub
    if hub:
        r["notes"].append({"id": "hub_page", "message": NOTES["hub_page"] % links[0]})
    return r


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


def read_page(url, get=http_get, allowed=None, stock="", today=None, max_age_days=MAX_AGE_DAYS):
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
    out.update(check_text(text, today=today, max_age_days=max_age_days))
    return add_links(out, body, ctype, out["final_url"])


def site_base(site):
    s = site.strip()
    if not re.match(r"https?://", s, re.I):
        s = "https://" + s
    p = urllib.parse.urlsplit(s)
    return "%s://%s" % (p.scheme.lower(), p.netloc.lower())


def check_site(site, get=http_get, sleep=time.sleep, delay=1.0, today=None,
               max_age_days=MAX_AGE_DAYS):
    """The three stock addresses of one site, robots.txt honoured, one request at a time."""
    allowed = robots_checker(get)
    base = site_base(site)
    pages = []
    for i, (name, path) in enumerate(STOCK_PATHS):
        if i:
            sleep(delay)
        pages.append(read_page(base + path, get=get, allowed=allowed, stock=name, today=today,
                               max_age_days=max_age_days))
    return pages


def check_file(path, html_file=True, today=None, max_age_days=MAX_AGE_DAYS):
    """A saved HTML page (html_file) or a plain-text statement on disk."""
    with open(path, "rb") as f:
        body = f.read()
    text = visible_text(body) if html_file else body.decode("utf-8", "replace")
    out = {"source": path, "final_url": "", "status": "ok", "stock_address": ""}
    out.update(check_text(text, today=today, max_age_days=max_age_days))
    if html_file:
        add_links(out, body)
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
    if r.get("en301549_named"):
        lines.append("  EN 301 549 editions named: %s"
                     % ("+".join("V" + v for v in r.get("en301549_versions", []))
                        or "none (named without an edition)"))
    if r.get("statement_date"):
        lines.append("  statement date: %s (%s)" % (r["statement_date"], r["date_source"]))
    else:
        lines.append("  statement date: none found")
    for n in r["notes"]:
        lines.append("  NOTE %s: %s" % (n["id"], n["message"]))
    if r.get("hub_page"):
        for link in r.get("statement_links", []):
            lines.append("  statement link: %s" % link)
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
    parser.add_argument("--max-age-days", type=int, default=MAX_AGE_DAYS,
                        help="note a statement whose latest 'last reviewed' or 'prepared on' date "
                             "is more than this many days old (default 365; 0 turns it off)")
    parser.add_argument("--today", type=datetime.date.fromisoformat, default=None,
                        help="the date to measure a statement's age from, as YYYY-MM-DD "
                             "(default: today)")
    parser.add_argument("--version", action="version", version=__version__)
    return parser


def main(argv=None, get=http_get, sleep=time.sleep, out=None):
    out = out or sys.stdout
    args = build_parser().parse_args(argv)
    if not (args.urls or args.site or args.file or args.text):
        build_parser().print_usage(out)
        return 2
    today = args.today or datetime.date.today()
    age = {"today": today, "max_age_days": args.max_age_days}
    results = []
    for url in args.urls:
        results.append(read_page(url, get=get, **age))
    for site in args.site:
        results.extend(check_site(site, get=get, sleep=sleep, delay=args.delay, **age))
    for path in args.file:
        results.append(check_file(path, html_file=True, **age))
    for path in args.text:
        results.append(check_file(path, html_file=False, **age))
    code = exit_code(results)
    if args.json:
        json.dump({"version": __version__, "exit_code": code, "today": today.isoformat(),
                   "max_age_days": args.max_age_days, "results": results}, out, indent=1)
        out.write("\n")
    else:
        for r in results:
            out.write("\n".join(format_result(r)) + "\n")
        n = sum(1 for r in results if r.get("status") == "ok" and r.get("placeholder"))
        hubs = sum(1 for r in results if r.get("hub_page"))
        out.write("statement_template_check %s: %d of %d page%s read with a template placeholder%s\n"
                  % (__version__, n, sum(1 for r in results if r.get("status") == "ok"),
                     "" if len(results) == 1 else "s",
                     "; %d may sit in front of the statement (hub_page)" % hubs if hubs else ""))
    return code


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass
    sys.exit(main())
