"""Offline tests of the May 11, 2028 note of statement_template_check.py 0.10.0 (no network).

45 CFR 84.84(b) as amended by HHS's interim final rule published on 11 May 2026 (91 FR 25507)
gives May 11, 2027 (recipients with fifteen or more employees) and May 10, 2028 (fewer than
fifteen). Guides read on 2026-11-12 gave May 11, 2028 for the second date. A page that names
Section 504, 45 CFR part 84 or HHS and gives May 11, 2028 without May 10, 2028 gets the note
may_11_2028, and no longer gets old_504_date.

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

MISQUOTE = ("Section 504 web accessibility. HHS's Office for Civil Rights extended the compliance "
            "dates for WCAG 2.1 Level AA to May 11, 2027 for recipients with 15 or more employees "
            "and May 11, 2028 for recipients with fewer than 15 employees.")
OLD_AND_MISQUOTE = ("Under Section 504 of the Rehabilitation Act, our clinic's website will meet "
                    "WCAG 2.1 AA. The first date was May 11, 2026; small providers now have until "
                    "5/11/2028.")
BOTH_2028 = MISQUOTE + " (Some guides say May 11, 2028; the rule says May 10, 2028.)"
NO_CONTEXT = "Our new website will meet WCAG 2.1 AA by May 11, 2028, after the redesign is done."
CORRECT = MISQUOTE.replace("May 11, 2028", "May 10, 2028")


def note_ids(r):
    return [n["id"] for n in r["notes"]]


class May11Tests(unittest.TestCase):
    def test_misquote_gets_a_note(self):
        r = c.check_text(MISQUOTE)
        self.assertIs(r["section_504_named"], True)
        self.assertIs(r["hhs504_may_11_2028"], True)
        self.assertIs(r["hhs504_dates"]["2027-05-11"], True)
        self.assertIs(r["hhs504_dates"]["2028-05-10"], False)
        self.assertEqual(note_ids(r), ["may_11_2028"])
        msg = r["notes"][0]["message"]
        self.assertTrue(msg.startswith("names May 11, 2028, which is not a date of HHS's "
                                       "Section 504 web rule"), msg)
        for words in ("May 11, 2027", "May 10, 2028", "91 FR 25507", "45 CFR 84.84(b)"):
            self.assertIn(words, msg)

    def test_misquote_replaces_old_date_note(self):
        r = c.check_text(OLD_AND_MISQUOTE)
        self.assertIs(r["hhs504_dates"]["2026-05-11"], True)
        self.assertIs(r["hhs504_may_11_2028"], True)
        self.assertEqual(note_ids(r), ["may_11_2028"])

    def test_correct_date_no_note(self):
        r = c.check_text(CORRECT)
        self.assertIs(r["hhs504_may_11_2028"], False)
        self.assertEqual(r["notes"], [])
        r = c.check_text(BOTH_2028)
        self.assertIs(r["hhs504_may_11_2028"], True)
        self.assertEqual(r["notes"], [])

    def test_no_section_504_context_no_note(self):
        r = c.check_text(NO_CONTEXT)
        self.assertIs(r["section_504_named"], False)
        self.assertIs(r["hhs504_may_11_2028"], True)
        self.assertEqual(r["notes"], [])

    def test_wordings(self):
        for s in ("May 11, 2028", "May 11th 2028", "11 May 2028", "05/11/2028", "5/11/28",
                  "2028-05-11"):
            self.assertIs(c.gives_may_11_2028("by " + s + "."), True, s)
        for s in ("May 10, 2028", "May 11, 2027", "May 1, 2028", "2028-05-110"):
            self.assertIs(c.gives_may_11_2028("by " + s + "."), False, s)


class OutputTests(unittest.TestCase):
    def run_main(self, text, *extra):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "statement.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            out = io.StringIO()
            code = c.main(["--text", path] + list(extra), out=out)
        return code, out.getvalue()

    def test_text_and_json(self):
        code, text = self.run_main(MISQUOTE)
        self.assertEqual(code, 0)
        self.assertIn("  NOTE may_11_2028: names May 11, 2028, which is not a date", text)
        code, text = self.run_main(MISQUOTE, "--json")
        data = json.loads(text)
        self.assertIs(data["results"][0]["hhs504_may_11_2028"], True)
        self.assertEqual(data["version"], c.__version__)

    def test_action_gives_a_notice(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "hc.md"), "w", encoding="utf-8") as f:
                f.write(MISQUOTE)
            out = io.StringIO()
            code = a.main(env={"GITHUB_WORKSPACE": d, "STC_TEXT_FILES": "hc.md",
                               "STC_TODAY": "2026-11-12"}, out=out)
        self.assertEqual(code, 0)
        self.assertIn("::notice file=hc.md,title=Accessibility statement%3A may_11_2028::names "
                      "May 11, 2028, which is not a date", out.getvalue())


class DocTests(unittest.TestCase):
    def read(self, *parts):
        with open(os.path.join(*parts), encoding="utf-8") as f:
            return f.read()

    def test_documented(self):
        readme = self.read(HERE, "README.md")
        skill = self.read(SKILL_DIR, "SKILL.md")
        self.assertIn("`may_11_2028`", readme)
        self.assertIn("`hhs504_may_11_2028`", readme)
        self.assertIn("test_may_11_2028.py", readme)
        self.assertIn("- **%s:**" % c.__version__, readme)
        self.assertIn("@v%s" % a.__version__, readme)
        self.assertIn("NOTE may_11_2028", skill)
        self.assertGreaterEqual(tuple(int(x) for x in c.__version__.split(".")), (0, 10, 0))
        self.assertEqual(a.__version__.split(".")[:2], c.__version__.split(".")[:2])


if __name__ == "__main__":
    unittest.main()
