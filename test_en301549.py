"""Offline tests of the EN 301 549 editions read by statement_template_check.py 0.8.0 (no network).

EN 301 549 is the European standard for accessible ICT. V3.2.1 (2021-03) is the edition cited in
the EU's Official Journal for the Web Accessibility Directive since 2021 (Implementing Decision
(EU) 2021/1339); V4.1.1 (2026-09), whose web clause covers WCAG 2.2, was published on 2 September
2026. A statement whose highest edition named is older than V3.2.1 gets the note older_en301549.

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

EU_OLD = ("Accessibility statement. The Municipality of Example is committed to making its website "
          "accessible in accordance with Directive (EU) 2016/2102. This website is partially "
          "conformant with EN 301 549 V2.1.2 (2018-08) because of the non-conformities listed "
          "below. We follow the Web Content Accessibility Guidelines (WCAG) 2.1 Level AA.")
EU_CITED = EU_OLD.replace("V2.1.2 (2018-08)", "V3.2.1 (2021-03)")
EU_NEW = EU_OLD.replace("V2.1.2 (2018-08)", "v4.1.1 (2026-09)").replace("2.1 Level AA", "2.2 Level AA")
EU_BARE = EU_OLD.replace(" V2.1.2 (2018-08)", "")


def note_ids(r):
    return [n["id"] for n in r["notes"]]


class EditionTests(unittest.TestCase):
    def test_older_edition_gets_a_note(self):
        r = c.check_text(EU_OLD)
        self.assertIs(r["en301549_named"], True)
        self.assertEqual(r["en301549_versions"], ["2.1.2"])
        self.assertEqual(r["en301549_highest"], "2.1.2")
        self.assertEqual(note_ids(r), ["older_en301549"])
        msg = r["notes"][0]["message"]
        self.assertTrue(msg.startswith("names EN 301 549 V2.1.2 as the highest edition"))
        self.assertIn("V3.2.1", msg)
        self.assertIn("V4.1.1", msg)
        self.assertIn("2 September 2026", msg)
        self.assertIs(r["placeholder"], False)

    def test_cited_and_newer_editions_get_no_note(self):
        for text, want in ((EU_CITED, ["3.2.1"]), (EU_NEW, ["4.1.1"])):
            r = c.check_text(text)
            self.assertEqual(r["en301549_versions"], want)
            self.assertEqual(r["notes"], [], text)

    def test_named_without_an_edition(self):
        r = c.check_text(EU_BARE)
        self.assertEqual((r["en301549_named"], r["en301549_versions"], r["en301549_highest"]),
                         (True, [], ""))
        self.assertEqual(r["notes"], [])

    def test_not_named(self):
        r = c.check_text("We follow the Web Content Accessibility Guidelines (WCAG) 2.2 Level AA.")
        self.assertEqual((r["en301549_named"], r["en301549_versions"]), (False, []))
        self.assertEqual(r["notes"], [])

    def test_wordings(self):
        self.assertEqual(c.en301549_versions("ETSI EN 301-549 version 2.1.2 applies."),
                         (True, ["2.1.2"]))
        self.assertEqual(c.en301549_versions("We meet EN 301 549 v.1.1.2 and WCAG 2.0."),
                         (True, ["1.1.2"]))
        self.assertEqual(c.en301549_versions("en 301 549 (V3.2.1) and, later, EN 301 549, "
                                             "version 4.1.1"), (True, ["3.2.1", "4.1.1"]))
        self.assertEqual(c.en301549_versions("EN301549 V3.2.1"), (True, ["3.2.1"]))

    def test_clause_numbers_are_not_editions(self):
        self.assertEqual(c.en301549_versions("See EN 301 549 clause 9.1.1.1 and EN 301 549 "
                                             "9.2.1.1 for details."), (True, []))
        self.assertEqual(c.en301549_versions("EN 301 549 V3.2.1.1"), (True, []))

    def test_highest_edition_decides(self):
        r = c.check_text("We tested against EN 301 549 V1.1.2 in 2016 and against EN 301 549 "
                         "V3.2.1 in 2025, with WCAG 2.1 AA.")
        self.assertEqual((r["en301549_versions"], r["en301549_highest"]),
                         (["1.1.2", "3.2.1"], "3.2.1"))
        self.assertNotIn("older_en301549", note_ids(r))

    def test_en_key(self):
        self.assertLess(c.en_key("2.1.2"), c.EN_CITED)
        self.assertFalse(c.en_key("3.2.1") < c.EN_CITED)
        self.assertGreater(c.en_key("4.1.1"), c.EN_CITED)
        self.assertEqual(c.en_key("3.10.1"), (3, 10, 1))


class OutputTests(unittest.TestCase):
    def run_main(self, text, *extra):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "statement.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            out = io.StringIO()
            code = c.main(["--text", path] + list(extra), out=out)
        return code, out.getvalue()

    def test_text_output(self):
        code, text = self.run_main(EU_OLD)
        self.assertEqual(code, 0)
        self.assertIn("  EN 301 549 editions named: V2.1.2\n", text)
        self.assertIn("  NOTE older_en301549: names EN 301 549 V2.1.2 as the highest edition", text)
        code, text = self.run_main(EU_BARE)
        self.assertIn("  EN 301 549 editions named: none (named without an edition)\n", text)
        self.assertNotIn("NOTE older_en301549", text)

    def test_no_line_when_not_named(self):
        _, text = self.run_main("We follow the Web Content Accessibility Guidelines (WCAG) 2.2 "
                                "Level AA on every page of this website, and we test new pages.")
        self.assertNotIn("EN 301 549", text)

    def test_json(self):
        code, text = self.run_main(EU_OLD, "--json")
        r = json.loads(text)["results"][0]
        self.assertEqual((r["en301549_named"], r["en301549_versions"], r["en301549_highest"]),
                         (True, ["2.1.2"], "2.1.2"))
        self.assertEqual(json.loads(text)["version"], c.__version__)

    def test_action_gives_a_notice(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "eu.md"), "w", encoding="utf-8") as f:
                f.write(EU_OLD)
            out = io.StringIO()
            code = a.main(env={"GITHUB_WORKSPACE": d, "STC_TEXT_FILES": "eu.md",
                               "STC_TODAY": "2026-11-12"}, out=out)
        self.assertEqual(code, 0)
        self.assertIn("::notice file=eu.md,title=Accessibility statement%3A older_en301549::names "
                      "EN 301 549 V2.1.2 as the highest edition", out.getvalue())
        self.assertIn("a11y-statement-check %s (statement_template_check %s)"
                      % (a.__version__, c.__version__), out.getvalue())


class DocTests(unittest.TestCase):
    def read(self, *parts):
        with open(os.path.join(*parts), encoding="utf-8") as f:
            return f.read()

    def test_documented(self):
        readme = self.read(HERE, "README.md")
        skill = self.read(SKILL_DIR, "SKILL.md")
        self.assertIn("`older_en301549`", readme)
        self.assertIn("test_en301549.py", readme)
        self.assertIn("- **%s:**" % c.__version__, readme)
        self.assertIn("NOTE older_en301549", skill)
        self.assertIn("EN 301 549 editions named", skill)
        self.assertGreaterEqual(c.en_key(c.__version__), (0, 8, 0))


if __name__ == "__main__":
    unittest.main()
