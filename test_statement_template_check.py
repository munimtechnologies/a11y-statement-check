"""Offline tests of statement_template_check.py and its agent skill (no network is used).

Apache-2.0. Made by MV2 of Munim, Inc. with AI agents.
"""

import io
import json
import os
import re
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.join(HERE, "skills", "accessibility-statement-check")
sys.path.insert(0, SKILL_DIR)
import statement_template_check as c  # noqa: E402

GOV = ("Accessibility Statement. YOUR MUNICIPALITY is committed to making its website accessible. "
       "This page is only meant as a template and should be edited. For help, contact NAME, "
       "TITLE, EMAIL, PHONE or [INSERT CONTACT INFORMATION]. We follow the Web Content "
       "Accessibility Guidelines (WCAG) 2.0 Level AA wherever we can.")
REVIZE = ("Accessibility Statement. Our Commitment: We aim to follow the Web Content Accessibility "
          "Guidelines (WCAG) 2.1 Level AA. [Your Agency/Website Name] is committed to ensuring "
          "digital accessibility for all users. This statement was last reviewed on [Date]. "
          "Contact us at [Contact Email] or [Contact Phone], or write to [Agency Address]. We aim "
          "to respond within [X business days].")
EQUALIZE = ("Accessibility Statement. [YOUR COMPANY NAME] is committed to providing a fully "
            "accessible website experience for all users of all abilities. We follow the Web "
            "Content Accessibility Guidelines (WCAG) version [SPECIFIC STANDARD, VERSION, LEVEL]. "
            "Accessibility features: [LIST ACCESSIBILITY FEATURES HERE]. Please contact "
            "[YOUR ACCESSIBILITY EMAIL ADDRESS] or call [YOUR PHONE NUMBER].")
T2017 = ("Accessibility Statement To help us make the Your School website a positive place for "
         "everyone, we've been using the Web Content Accessibility Guidelines (WCAG) 2.0. These "
         "guidelines explain how to make web content more accessible for people with "
         "disabilities, and user friendly for everyone. Let us know if you have any problems "
         "accessing the site: email us at accessibility@yourschool.com - call us on "
         "555-555-5555 ext:555. This accessibility statement was generated on 16th May 2017 "
         "using the Accessibility Statement Generator.")
T2026 = ("Accessibility Statement [Your School] is committed to ensuring digital accessibility "
         "for people with disabilities. [Your School] is built with WCAG 2.1 AA guidelines in "
         "mind. Accessibility is never a one-time checkbox. If you have trouble using this site, "
         "please contact us: Phone: 555-555-5555 ext:555 - Email: accessibility@yourschool.com. "
         "We aim to respond within # business days.")
FILLED = ("Accessibility Statement To help us make the Springfield Public Schools website a "
          "positive place for everyone, we've been using the Web Content Accessibility "
          "Guidelines (WCAG) 2.1. These guidelines explain how to make web content more "
          "accessible for people with disabilities, and user friendly for everyone. Let us know "
          "if you have any problems accessing the site: email the webmaster of the district or "
          "call the district office during school hours.")


def page(text):
    return ("<html><body><main><p>" + text + "</p></main></body></html>").encode("utf-8")


def ids(r):
    return [p["id"] for p in r["placeholders"]]


def note_ids(r):
    return [n["id"] for n in r["notes"]]


def fake_get(pages, robots=None, calls=None):
    """pages: url -> (status, final url or '', body)."""
    robots = robots or {}

    def get(url):
        if calls is not None:
            calls.append(url)
        if url.endswith("/robots.txt"):
            body = robots.get(url)
            return (200, url, "text/plain", body) if body else (404, url, "", b"")
        if url in pages:
            status, final, body = pages[url]
            return (status, final or url, "text/html; charset=utf-8" if status == 200 else "",
                    body)
        return 404, url, "", b""
    return get


class Sleeps(list):
    def __call__(self, seconds):
        self.append(seconds)


class TemplateTests(unittest.TestCase):
    def test_government_template(self):
        r = c.check_text(GOV)
        self.assertEqual(ids(r), ["your_municipality", "template_note", "contact_block",
                                  "caps_bracket"])
        self.assertEqual(r["groups"], ["government"])
        self.assertEqual(r["placeholders"][3]["text"], "[INSERT CONTACT INFORMATION]")
        self.assertEqual(r["wcag_versions"], ["2.0"])
        self.assertIn("only_wcag_2_0", note_ids(r))
        self.assertEqual(r["verdict"], "unfinished template (4 placeholders)")

    def test_revize_template(self):
        r = c.check_text(REVIZE)
        self.assertEqual(ids(r), ["agency_name", "date", "contact_email", "contact_phone",
                                  "agency_address", "x_business_days"])
        self.assertEqual(r["groups"], ["revize"])
        self.assertEqual(r["templates"], ["revize"])
        self.assertEqual((r["wcag_versions"], r["highest"]), (["2.1"], "2.1"))
        self.assertEqual(note_ids(r), ["placeholder"])

    def test_accessibility_checker_template(self):
        r = c.check_text(EQUALIZE)
        self.assertEqual(ids(r), ["company_name", "specific_standard", "features",
                                  "accessibility_email", "phone_number"])
        self.assertEqual(r["groups"], ["accessibility-checker"])
        self.assertEqual(r["templates"], ["accessibility_checker"])
        self.assertEqual(r["wcag_versions"], [])
        self.assertEqual(note_ids(r), ["placeholder", "no_wcag_version"])

    def test_2017_school_template(self):
        r = c.check_text(T2017)
        self.assertEqual(ids(r), ["your_school", "your_domain", "fake_phone"])
        self.assertEqual(r["groups"], ["school"])
        self.assertEqual(r["placeholders"][0]["text"], "the Your School")
        self.assertEqual(r["templates"], ["t2017_your_school"])
        self.assertEqual(note_ids(r), ["placeholder", "only_wcag_2_0", "generator"])

    def test_2026_school_template(self):
        r = c.check_text(T2026)
        self.assertEqual(ids(r), ["school_bracket", "your_domain", "fake_phone", "hash_days"])
        self.assertEqual(r["templates"], ["finalsite_2026"])
        self.assertEqual(r["wcag_versions"], ["2.1"])

    def test_filled_statement(self):
        r = c.check_text(FILLED)
        self.assertIs(r["placeholder"], False)
        self.assertEqual(r["placeholders"], [])
        self.assertEqual(r["possible_placeholder"], "")
        self.assertEqual(r["templates"], ["t2017_your_school"])
        self.assertEqual(r["notes"], [])
        self.assertEqual(r["verdict"], "no template placeholder found")


class NoteTests(unittest.TestCase):
    def test_possible_placeholder_skips_hidden_email(self):
        r = c.check_text("Questions about the Web Content Accessibility Guidelines 2.1 AA: write "
                         "to [email protected] or ask [Name of department].")
        self.assertIs(r["placeholder"], False)
        self.assertEqual(r["possible_placeholder"], "[Name of department]")
        self.assertEqual(note_ids(r), ["possible_placeholder"])
        r = c.check_text("Write to [email protected] about the Web Content Accessibility "
                         "Guidelines 2.1 AA.")
        self.assertEqual(r["possible_placeholder"], "")
        self.assertEqual(r["notes"], [])

    def test_versions_and_dates(self):
        r = c.check_text("Our website follows WCAG 2.0 and 2.1 Level AA, as the ADA Title II "
                         "rule requires by April 24, 2026.")
        self.assertEqual((r["wcag_versions"], r["highest"]), (["2.0", "2.1"], "2.1"))
        self.assertEqual(note_ids(r), ["old_title2_date"])
        r = c.check_text("We follow WCAG 2.1 AA. The dates moved from April 24, 2026 to April "
                         "26, 2027.")
        self.assertEqual(r["notes"], [])
        self.assertIs(r["dates"]["2027-04-26"], True)
        r = c.check_text("We want everyone to be able to use our website.")
        self.assertEqual(note_ids(r), ["no_wcag"])

    def test_stock_sentence(self):
        r = c.check_text("We work to comply with Section 508 as well as the Web Content "
                         "Accessibility Guidelines (WCAG) 2.1 AA.")
        self.assertEqual(r["templates"], ["stock_508"])
        self.assertEqual(note_ids(r), ["stock_508"])


class HtmlTests(unittest.TestCase):
    def test_visible_text(self):
        body = (b"<html><head><script>var x='[YOUR COMPANY NAME]';</script>"
                b"<style>p{color:red}</style></head><body><p>Hello&nbsp;world</p>"
                b"<svg><text>hidden</text></svg></body></html>")
        self.assertEqual(c.visible_text(body), "Hello world")
        self.assertEqual(c.visible_text("<p>caf\xe9</p>".encode("latin-1"),
                                        "text/html; charset=iso-8859-1"), "caf\xe9")

    def test_read_page(self):
        get = fake_get({"https://x.org/a": (200, "", page(T2026)),
                        "https://x.org/short": (200, "", page("Hi"))})
        r = c.read_page("https://x.org/a", get=get)
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["groups"], ["school"])
        self.assertEqual(c.read_page("https://x.org/b", get=get)["status"], "http_404")
        self.assertEqual(c.read_page("https://x.org/short", get=get)["status"], "short")


class SiteTests(unittest.TestCase):
    BASE = "https://www.example.gov"

    def test_stock_addresses(self):
        calls, sleeps = [], Sleeps()
        get = fake_get({self.BASE + "/153/Accessibility": (200, "", page(GOV)),
                        self.BASE + "/accessibility-statement": (200, self.BASE + "/",
                                                                 page(FILLED))}, calls=calls)
        rs = c.check_site("www.example.gov", get=get, sleep=sleeps, delay=0.5)
        self.assertEqual([r["status"] for r in rs], ["ok", "http_404", "redirect_home"])
        self.assertEqual([r["stock_address"] for r in rs],
                         ["civicplus", "revize", "accessibility-statement"])
        self.assertEqual(rs[0]["groups"], ["government"])
        self.assertEqual(sleeps, [0.5, 0.5])
        self.assertEqual(calls.count(self.BASE + "/robots.txt"), 1)
        self.assertEqual(c.exit_code(rs), 1)

    def test_robots_txt_is_honoured(self):
        get = fake_get({self.BASE + "/153/Accessibility": (200, "", page(GOV))},
                       robots={self.BASE + "/robots.txt": b"User-agent: *\nDisallow: /153/\n"})
        rs = c.check_site(self.BASE, get=get, sleep=Sleeps())
        self.assertEqual([r["status"] for r in rs], ["robots", "http_404", "http_404"])
        self.assertEqual(c.exit_code(rs), 2)


class MainTests(unittest.TestCase):
    def test_text_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "statement.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(T2017)
            out = io.StringIO()
            code = c.main(["--text", path], out=out)
        self.assertEqual(code, 1)
        self.assertIn("PLACEHOLDER school/your_school: the Your School", out.getvalue())
        self.assertIn("1 of 1 page read with a template placeholder", out.getvalue())

    def test_html_file_json(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "statement.html")
            with open(path, "wb") as f:
                f.write(page(FILLED))
            out = io.StringIO()
            code = c.main(["--file", path, "--json"], out=out)
        data = json.loads(out.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual((data["exit_code"], data["version"]), (0, c.__version__))
        self.assertIs(data["results"][0]["placeholder"], False)

    def test_nothing_read(self):
        out = io.StringIO()
        self.assertEqual(c.main(["https://x.org/none"], get=fake_get({}), out=out), 2)
        self.assertIn("not read: http_404", out.getvalue())
        self.assertEqual(c.main([], out=io.StringIO()), 2)


class SkillTests(unittest.TestCase):
    def read(self, *parts):
        with open(os.path.join(*parts), encoding="utf-8") as f:
            return f.read()

    def test_frontmatter(self):
        text = self.read(SKILL_DIR, "SKILL.md")
        self.assertTrue(text.startswith("---\n"))
        end = text.index("\n---\n", 4)
        meta = dict(line.split(": ", 1) for line in text[4:end].splitlines())
        self.assertEqual(meta["name"], os.path.basename(SKILL_DIR))
        self.assertLess(len(meta["description"]), 1024)
        for bad in (": ", " #"):
            self.assertNotIn(bad, meta["description"])

    def test_documented_flags_exist(self):
        options = set(c.build_parser()._option_string_actions)
        for name in (os.path.join(SKILL_DIR, "SKILL.md"), os.path.join(HERE, "README.md")):
            with open(name, encoding="utf-8") as f:
                lines = [l for l in f if "statement_template_check.py" in l]
            self.assertTrue(lines, name)
            for line in lines:
                for flag in re.findall(r"(?<![\w-])--[a-z][a-z-]*", line):
                    self.assertIn(flag, options, (name, flag))


if __name__ == "__main__":
    unittest.main()
