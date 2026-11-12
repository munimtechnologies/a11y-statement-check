"""Offline tests of the Section 504 dates read by statement_template_check.py 0.9.0 (no network).

HHS's 2024 Section 504 rule (45 CFR 84.84(b)) asked recipients of HHS funding to meet WCAG 2.1
Level AA on the web by May 11, 2026 (fifteen or more employees) and May 10, 2027 (fewer than
fifteen). An HHS interim final rule published on 11 May 2026 (91 FR 25507) moved the dates to May
11, 2027 and May 10, 2028. A page that names Section 504, 45 CFR part 84 or HHS and gives only an
old date gets the note old_504_date.

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

HC_OLD = ("Accessibility statement. Example Community Health Center receives federal financial "
          "assistance from the U.S. Department of Health and Human Services (HHS). Under Section "
          "504 of the Rehabilitation Act and the HHS rule at 45 CFR 84.84, our website will "
          "conform to the Web Content Accessibility Guidelines (WCAG) 2.1 Level AA by May 11, 2026.")
HC_NEW = HC_OLD.replace("May 11, 2026", "May 11, 2027")
HC_MOVED = HC_OLD + " An HHS interim final rule moved that date to May 11, 2027."
HC_SMALL = ("Under Section 504, as a health care provider with fewer than fifteen employees, we will "
            "meet WCAG 2.1 AA on our website by 5/10/2027.")
HC_BOTH = ("Section 504 of the Rehabilitation Act: large providers must meet WCAG 2.1 AA by May 11, "
           "2026 and small providers by May 10, 2027.")
NO_CONTEXT = "Our new website will meet WCAG 2.1 AA by May 11, 2026."
BOTH_RULES = ("Under ADA Title II and Section 504, our website will meet WCAG 2.1 AA by April 24, "
              "2026 and May 11, 2026.")
NONE_GIVEN = {"2026-05-11": False, "2027-05-10": False, "2027-05-11": False, "2028-05-10": False}


def note_ids(r):
    return [n["id"] for n in r["notes"]]


class Section504Tests(unittest.TestCase):
    def test_old_large_date_gets_a_note(self):
        r = c.check_text(HC_OLD)
        self.assertIs(r["section_504_named"], True)
        self.assertEqual(r["hhs504_dates"], dict(NONE_GIVEN, **{"2026-05-11": True}))
        self.assertEqual(note_ids(r), ["old_504_date"])
        msg = r["notes"][0]["message"]
        self.assertTrue(msg.startswith("names May 11, 2026, a web compliance date of HHS's 2024 "
                                       "Section 504 rule"), msg)
        for words in ("May 11, 2027", "May 10, 2028", "91 FR 25507", "45 CFR 84.84"):
            self.assertIn(words, msg)
        self.assertIs(r["placeholder"], False)

    def test_new_or_both_dates_get_no_note(self):
        r = c.check_text(HC_NEW)
        self.assertEqual(r["hhs504_dates"], dict(NONE_GIVEN, **{"2027-05-11": True}))
        self.assertEqual(r["notes"], [])
        r = c.check_text(HC_MOVED)
        self.assertEqual(r["hhs504_dates"],
                         dict(NONE_GIVEN, **{"2026-05-11": True, "2027-05-11": True}))
        self.assertEqual(r["notes"], [])

    def test_old_small_date(self):
        r = c.check_text(HC_SMALL)
        self.assertEqual(r["hhs504_dates"], dict(NONE_GIVEN, **{"2027-05-10": True}))
        self.assertEqual(note_ids(r), ["old_504_date"])
        self.assertTrue(r["notes"][0]["message"].startswith("names May 10, 2027, a web"))

    def test_both_old_dates(self):
        r = c.check_text(HC_BOTH)
        self.assertEqual(note_ids(r), ["old_504_date"])
        self.assertTrue(r["notes"][0]["message"].startswith(
            "names May 11, 2026 and May 10, 2027, a web"))

    def test_no_section_504_context_no_note(self):
        r = c.check_text(NO_CONTEXT)
        self.assertIs(r["section_504_named"], False)
        self.assertIs(r["hhs504_dates"]["2026-05-11"], True)
        self.assertEqual(r["notes"], [])

    def test_title_ii_and_504_notes_together(self):
        self.assertEqual(note_ids(c.check_text(BOTH_RULES)), ["old_title2_date", "old_504_date"])

    def test_hhs504_helper(self):
        self.assertEqual(c.hhs504(HC_OLD), (True, dict(NONE_GIVEN, **{"2026-05-11": True})))
        self.assertEqual(c.hhs504("We follow WCAG 2.2 AA."), (False, NONE_GIVEN))

    def test_date_wordings(self):
        rx = c.may_date_re(11, 2026)
        for s in ("May 11, 2026", "May 11th, 2026", "May 11 2026", "11 May 2026", "11th May, 2026",
                  "05/11/2026", "5/11/26", "2026-05-11", "MAY 11, 2026"):
            self.assertTrue(rx.search(s), s)
        for s in ("May 1, 2026", "May 11, 20260", "15/11/2026", "2026-05-110", "May 11, 2025"):
            self.assertIsNone(rx.search(s), s)
        self.assertTrue(c.may_date_re(10, 2028).search("by May 10, 2028."))
        self.assertTrue(c.may_date_re(10, 2028).search("2028-05-10"))

    def test_context_wordings(self):
        for s in ("Section 504", "section 504 of the Rehabilitation Act", "Sec. 504", "§ 504",
                  "45 CFR 84.84", "45 C.F.R. § 84.84", "45 CFR Part 84", "HHS",
                  "the Department of Health & Human Services"):
            self.assertTrue(c.SECTION_504_RE.search(s), s)
        for s in ("Section 508", "Section 5040", "45 CFR 35.200", "hhsa.example.org"):
            self.assertIsNone(c.SECTION_504_RE.search(s), s)


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
        code, text = self.run_main(HC_OLD)
        self.assertEqual(code, 0)
        self.assertIn("  NOTE old_504_date: names May 11, 2026, a web compliance date", text)
        code, text = self.run_main(HC_NEW)
        self.assertEqual(code, 0)
        self.assertNotIn("old_504_date", text)

    def test_json(self):
        code, text = self.run_main(HC_OLD, "--json")
        data = json.loads(text)
        r = data["results"][0]
        self.assertIs(r["section_504_named"], True)
        self.assertIs(r["hhs504_dates"]["2026-05-11"], True)
        self.assertEqual(data["version"], c.__version__)

    def test_action_gives_a_notice(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "hc.md"), "w", encoding="utf-8") as f:
                f.write(HC_OLD)
            out = io.StringIO()
            code = a.main(env={"GITHUB_WORKSPACE": d, "STC_TEXT_FILES": "hc.md",
                               "STC_TODAY": "2026-11-12"}, out=out)
        self.assertEqual(code, 0)
        self.assertIn("::notice file=hc.md,title=Accessibility statement%3A old_504_date::names "
                      "May 11, 2026, a web compliance date", out.getvalue())


class DocTests(unittest.TestCase):
    def read(self, *parts):
        with open(os.path.join(*parts), encoding="utf-8") as f:
            return f.read()

    def test_documented(self):
        readme = self.read(HERE, "README.md")
        skill = self.read(SKILL_DIR, "SKILL.md")
        self.assertIn("`old_504_date`", readme)
        self.assertIn("test_section504.py", readme)
        self.assertIn("- **%s:**" % c.__version__, readme)
        self.assertIn("@v%s" % a.__version__, readme)
        self.assertIn("NOTE old_504_date", skill)
        self.assertGreaterEqual(tuple(int(x) for x in c.__version__.split(".")), (0, 9, 0))
        self.assertEqual(a.__version__.split(".")[:2], c.__version__.split(".")[:2])


if __name__ == "__main__":
    unittest.main()
