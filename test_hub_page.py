"""Offline tests of the hub_page note of statement_template_check.py 0.6.0 (no network is used).

A page that names no WCAG version and gives no statement date but links to what looks like the
accessibility statement itself probably sits in front of the statement. MV2's comparison of two
automated censuses of UK council statements (title2-pdf-census, results/uk-councils/AGREE-RESULT.md)
found 12 such pages among the 23 one census scored lowest.

Apache-2.0. Made by MV2 of Munim, Inc. with AI agents.
"""

import io
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.join(HERE, "skills", "accessibility-statement-check")
sys.path.insert(0, SKILL_DIR)
sys.path.insert(0, HERE)
import statement_template_check as c  # noqa: E402
import action_run as a  # noqa: E402

BASE = "https://www.example.gov.uk"
HUB_URL = BASE + "/help/accessibility"
STATEMENT_URL = BASE + "/help/accessibility/accessibility-statement/"
INTRO = ("We want everyone who visits our website to feel welcome and find it easy to use. This "
         "page explains how to change colours, text size and other settings in your browser, and "
         "how to contact us if you have a problem using any part of the site.")
HUB = ("<html><body><main><h1>Accessibility</h1><p>" + INTRO + "</p><ul>"
       "<li><a href=\"/help/accessibility/accessibility-statement/\">Accessibility statement</a></li>"
       "<li><a href=\"/help/accessibility/tools\">Accessibility tools</a></li>"
       "<li><a href=\"mailto:web@example.gov.uk\">Email the web team</a></li>"
       "</ul></main></body></html>").encode("utf-8")
UK_FILLED = ("Accessibility statement for Example District Council. This accessibility statement "
             "applies to the www.example.gov.uk website. This website is run by Example District "
             "Council. We want as many people as possible to be able to use this website. This "
             "website is partially compliant with the Web Content Accessibility Guidelines version "
             "2.1 AA standard, due to the non-compliances listed below. This statement was prepared "
             "on 1 March 2021. It was last reviewed on 10 March 2026.")
STATEMENT = ("<html><body><main><p>" + UK_FILLED + "</p><p><a href=\"/apps/accessibility-statement\">"
             "Accessibility statement for our app</a></p></main></body></html>").encode("utf-8")
PLACEHOLDER = ("<html><body><main><p>[Your School] is committed to making its website accessible "
               "to everyone who uses it. " + INTRO + "</p><a href=\"/accessibility-statement-full\">"
               "Accessibility statement</a></main></body></html>").encode("utf-8")


def fake_get(pages):
    def get(url):
        if url in pages:
            return 200, url, "text/html; charset=utf-8", pages[url]
        return 404, url, "", b""
    return get


def note_ids(r):
    return [n["id"] for n in r["notes"]]


class LinkTests(unittest.TestCase):
    def test_link_rules(self):
        links = [("/one/AccessibilityStatement", "Read more"),
                 ("/two", "Datganiad hygyrchedd"),
                 ("/three", "Accessibility tools"),
                 ("mailto:web@example.org", "Accessibility statement"),
                 ("#main", "Accessibility statement"),
                 ("javascript:void(0)", "Accessibility statement"),
                 ("/one/AccessibilityStatement#top", "Accessibility statement"),
                 ("/four", ""),
                 ("https://other.example.net/accessibility_statement", "")]
        self.assertEqual(c.statement_links(links, "https://www.example.org/help"),
                         ["https://www.example.org/one/AccessibilityStatement",
                          "https://www.example.org/two",
                          "https://other.example.net/accessibility_statement"])

    def test_aria_label_counts_as_link_text(self):
        body = b'<p><a href="/x" aria-label="Accessibility statement"><svg></svg></a></p>'
        self.assertEqual(c.statement_links(c.find_links(body), "https://www.example.org/"),
                         ["https://www.example.org/x"])

    def test_the_page_itself_is_not_a_statement_link(self):
        page = "https://example.gov.uk/accessibility-statement"
        links = [("/accessibility-statement/", "Accessibility statement"),
                 ("https://www.example.gov.uk/Accessibility-Statement#top", "Accessibility statement"),
                 ("https://www.example.gov.uk/accessibility-statement?print=1", "Print")]
        self.assertEqual(c.statement_links(links, page), [])

    def test_at_most_five_and_no_long_addresses(self):
        links = [("/s%d/accessibility-statement" % i, "") for i in range(7)]
        links.insert(0, ("/" + "x" * 400 + "/accessibility-statement", ""))
        got = c.statement_links(links, "https://www.example.org/")
        self.assertEqual(len(got), c.MAX_STATEMENT_LINKS)
        self.assertEqual(got[0], "https://www.example.org/s0/accessibility-statement")

    def test_page_key(self):
        self.assertEqual(c.page_key("https://WWW.Example.org/A/b/?q=1#x"), "example.org/a/b")
        self.assertEqual(c.page_key(""), "")


class HubTests(unittest.TestCase):
    def test_hub_page(self):
        r = c.read_page(HUB_URL, get=fake_get({HUB_URL: HUB}))
        self.assertEqual(r["status"], "ok")
        self.assertIs(r["hub_page"], True)
        self.assertEqual(r["statement_links"], [STATEMENT_URL])
        self.assertEqual(note_ids(r), ["no_wcag", "hub_page"])
        self.assertIn("(%s)" % STATEMENT_URL, r["notes"][-1]["message"])
        self.assertIs(r["placeholder"], False)

    def test_a_statement_that_links_to_another_is_not_a_hub(self):
        url = BASE + "/accessibility-statement"
        r = c.read_page(url, get=fake_get({url: STATEMENT}))
        self.assertIs(r["hub_page"], False)
        self.assertEqual(r["statement_links"], [BASE + "/apps/accessibility-statement"])
        self.assertNotIn("hub_page", note_ids(r))

    def test_a_placeholder_page_is_not_a_hub(self):
        url = BASE + "/school"
        r = c.read_page(url, get=fake_get({url: PLACEHOLDER}))
        self.assertIs(r["placeholder"], True)
        self.assertIs(r["hub_page"], False)
        self.assertEqual(r["statement_links"], [BASE + "/accessibility-statement-full"])

    def test_text_has_no_links(self):
        r = c.check_text("Read our accessibility statement at https://www.example.gov.uk/"
                         "accessibility-statement. " + INTRO)
        self.assertEqual((r["statement_links"], r["hub_page"]), ([], False))

    def test_saved_file_counts_only_absolute_links(self):
        body = HUB.replace(b'href="/help/accessibility/tools"',
                           b'href="https://www.example.gov.uk/accessibility-statement"')
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "hub.html")
            with open(path, "wb") as f:
                f.write(body)
            r = c.check_file(path, html_file=True)
            t = c.check_file(path, html_file=False)
        self.assertEqual(r["statement_links"], [BASE + "/accessibility-statement"])
        self.assertIs(r["hub_page"], True)
        self.assertEqual((t["statement_links"], t["hub_page"]), ([], False))


class MainTests(unittest.TestCase):
    def test_text_output_and_exit_code(self):
        out = io.StringIO()
        code = c.main([HUB_URL], get=fake_get({HUB_URL: HUB}), out=out)
        text = out.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("  NOTE hub_page: names no WCAG version and gives no statement date", text)
        self.assertIn("  statement link: %s\n" % STATEMENT_URL, text)
        self.assertIn("0 of 1 page read with a template placeholder; 1 may sit in front of the "
                      "statement (hub_page)", text)

    def test_json(self):
        out = io.StringIO()
        c.main([HUB_URL, "--json"], get=fake_get({HUB_URL: HUB}), out=out)
        r = json.loads(out.getvalue())["results"][0]
        self.assertEqual((r["hub_page"], r["statement_links"]), (True, [STATEMENT_URL]))

    def test_no_hub_no_suffix(self):
        url = BASE + "/accessibility-statement"
        out = io.StringIO()
        c.main([url], get=fake_get({url: STATEMENT}), out=out)
        self.assertNotIn("hub_page", out.getvalue())
        self.assertNotIn("statement link:", out.getvalue())

    def test_action_gives_a_notice(self):
        with tempfile.TemporaryDirectory() as d:
            body = HUB.replace(b'href="/help/accessibility/accessibility-statement/"',
                               b'href="' + STATEMENT_URL.encode("ascii") + b'"')
            with open(os.path.join(d, "hub.html"), "wb") as f:
                f.write(body)
            out = io.StringIO()
            code = a.main(env={"GITHUB_WORKSPACE": d, "STC_HTML_FILES": "hub.html",
                               "STC_TODAY": "2026-11-11"}, out=out)
        self.assertEqual(code, 0)
        self.assertIn("::notice file=hub.html,title=Accessibility statement%3A hub_page::names no "
                      "WCAG version", out.getvalue())
        self.assertIn("  statement link: %s" % STATEMENT_URL, out.getvalue())


class DocTests(unittest.TestCase):
    def read(self, *parts):
        with open(os.path.join(*parts), encoding="utf-8") as f:
            return f.read()

    def test_documented(self):
        readme = self.read(HERE, "README.md")
        skill = self.read(SKILL_DIR, "SKILL.md")
        self.assertIn("`hub_page`", readme)
        self.assertIn("- **%s:**" % c.__version__, readme)
        self.assertIn("test_hub_page.py", readme)
        self.assertIn("NOTE hub_page", skill)
        self.assertIn("statement link:", skill)
        self.assertEqual(c.__version__, "0.6.0")


if __name__ == "__main__":
    unittest.main()
