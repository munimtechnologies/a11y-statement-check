"""Offline tests of statement_template_check.py 0.10.1: a statement's own date is not a Title II date.

April 24, 2026 was the first ADA Title II web compliance date before the Justice Department's
interim final rule of 2026-04-20 moved it. A statement "Last updated: April 24, 2026" gives the day
it was written, not that date, so it no longer gets the note old_title2_date. MV2's pre-registered
census of US special districts' accessibility pages (title2-pdf-census, results/special-districts)
found such a statement, which 0.10.0 flagged. The JSON's dates still report the April 24, 2026.

Apache-2.0. Made by MV2 of Munim, Inc. with AI agents.
"""

import io
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

# An illustrative statement in the wording found by the census (not a copy of any page).
UPDATED = ("Accessibility Statement. Last updated: April 24, 2026. Our water district is committed "
           "to ensuring digital accessibility for all. We aim to follow the Web Content "
           "Accessibility Guidelines (WCAG) 2.1, Level AA.")
BOTH = UPDATED + (" Under the ADA Title II rule, our website must meet WCAG 2.1 AA by April 24, "
                  "2026.")
PREPARED = "This statement was prepared on 24 April 2026. We follow WCAG 2.1 Level AA on every page."
NUMERIC = "Page updated on 04/24/2026. We follow WCAG 2.1 AA."
PLAIN = "Our website follows WCAG 2.1 AA, as the ADA Title II rule requires by April 24, 2026."


def note_ids(r):
    return [n["id"] for n in r["notes"]]


class StatementDateTests(unittest.TestCase):
    def test_last_updated_is_not_a_title2_date(self):
        r = c.check_text(UPDATED)
        self.assertEqual(note_ids(r), [])
        self.assertIs(r["dates"]["2026-04-24"], True)
        self.assertEqual((r["statement_date"], r["date_source"]), ("2026-04-24", "reviewed"))
        self.assertEqual(r["wcag_versions"], ["2.1"])

    def test_a_second_april_24_still_counts(self):
        self.assertEqual(note_ids(c.check_text(BOTH)), ["old_title2_date"])

    def test_prepared_and_numeric_wordings(self):
        r = c.check_text(PREPARED)
        self.assertEqual(note_ids(r), [])
        self.assertEqual((r["statement_date"], r["date_source"]), ("2026-04-24", "prepared"))
        r = c.check_text(NUMERIC)
        self.assertEqual(note_ids(r), [])
        self.assertIs(r["dates"]["2026-04-24"], True)
        self.assertEqual(r["statement_date"], "2026-04-24")

    def test_plain_title2_date_unchanged(self):
        self.assertEqual(note_ids(c.check_text(PLAIN)), ["old_title2_date"])

    def test_title2_2026(self):
        self.assertIs(c.title2_2026("Last updated: April 24, 2026"), False)
        self.assertIs(c.title2_2026("We must comply by April 24, 2026."), True)
        self.assertIs(c.title2_2026("Last updated: 3 June 2025. We must comply by 4/24/26."), True)
        self.assertIs(c.title2_2026("No dates here."), False)


class OutputTests(unittest.TestCase):
    def run_action(self, name, text):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, name), "w", encoding="utf-8") as f:
                f.write(text)
            out = io.StringIO()
            code = a.main(env={"GITHUB_WORKSPACE": d, "STC_TEXT_FILES": name,
                               "STC_TODAY": "2026-11-12"}, out=out)
        return code, out.getvalue()

    def test_action(self):
        code, text = self.run_action("updated.md", UPDATED)
        self.assertEqual(code, 0)
        self.assertNotIn("old_title2_date", text)
        self.assertIn("a11y-statement-check %s (statement_template_check %s)"
                      % (a.__version__, c.__version__), text)
        code, text = self.run_action("both.md", BOTH)
        self.assertEqual(code, 0)
        self.assertIn("::notice file=both.md,title=Accessibility statement%3A old_title2_date::"
                      "names April 24, 2026", text)


class DocTests(unittest.TestCase):
    def read(self, *parts):
        with open(os.path.join(*parts), encoding="utf-8") as f:
            return f.read()

    def test_documented(self):
        readme = self.read(HERE, "README.md")
        skill = self.read(SKILL_DIR, "SKILL.md")
        self.assertIn("`old_title2_date`", readme)
        self.assertIn("test_title2_statement_date.py", readme)
        self.assertIn("- **%s:**" % c.__version__, readme)
        self.assertIn("@v%s" % a.__version__, readme)
        self.assertIn("Since 0.10.1", skill)
        self.assertGreaterEqual(tuple(int(x) for x in c.__version__.split(".")), (0, 10, 1))
        self.assertEqual(a.__version__.split(".")[:2], c.__version__.split(".")[:2])


if __name__ == "__main__":
    unittest.main()
