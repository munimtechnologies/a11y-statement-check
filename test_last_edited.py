"""Offline tests of statement_template_check.py 0.10.2: a "last edited" date is not a Title II date.

April 24, 2026 was the first ADA Title II web compliance date before the Justice Department's
interim final rule of 2026-04-20 moved it. Since 0.10.1 an April 24, 2026 inside a "last reviewed /
updated" or "prepared / published on" phrase no longer gets the note old_title2_date. MV2's
pre-registered census of US cities and counties of 50,000 or more (title2-pdf-census,
results/a11y-pages) also found a page "Last Edited: April 24, 2026", which 0.10.1 still flagged;
since 0.10.2 a "last edited" or "last modified" date does not count either. It is not read as the
statement's own date, so statement_date and the JSON's dates are unchanged.

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

# Illustrative statements in the wording found by the census (not a copy of any page).
EDITED = ("Accessibility Statement. Last Edited: April 24, 2026. Our water district is committed "
          "to ensuring digital accessibility for all. We aim to follow the Web Content "
          "Accessibility Guidelines (WCAG) 2.1, Level AA.")
MODIFIED = "Page last modified on 04/24/2026. We follow WCAG 2.1 AA."
EDITED_AND_RULE = EDITED + (" Under the ADA Title II rule, our website must meet WCAG 2.1 AA by "
                            "April 24, 2026.")


def note_ids(r):
    return [n["id"] for n in r["notes"]]


class LastEditedTests(unittest.TestCase):
    def test_last_edited_is_not_a_title2_date(self):
        r = c.check_text(EDITED)
        self.assertEqual(note_ids(r), [])
        self.assertIs(r["dates"]["2026-04-24"], True)
        self.assertEqual((r["statement_date"], r["date_source"]), ("", ""))
        self.assertEqual(r["wcag_versions"], ["2.1"])

    def test_last_modified_numeric(self):
        r = c.check_text(MODIFIED)
        self.assertEqual(note_ids(r), [])
        self.assertIs(r["dates"]["2026-04-24"], True)
        self.assertEqual(r["statement_date"], "")

    def test_a_second_april_24_still_counts(self):
        self.assertEqual(note_ids(c.check_text(EDITED_AND_RULE)), ["old_title2_date"])

    def test_title2_2026(self):
        self.assertIs(c.title2_2026("Last Edited: April 24, 2026"), False)
        self.assertIs(c.title2_2026("Page last modified on 04/24/2026"), False)
        self.assertIs(c.title2_2026("Last edited: 3 June 2025. We must comply by 4/24/26."), True)
        self.assertIs(c.title2_2026("Content created before April 24, 2026 is archived."), True)
        self.assertIs(c.title2_2026("Last updated: April 24, 2026"), False)


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
        code, text = self.run_action("edited.md", EDITED)
        self.assertEqual(code, 0)
        self.assertNotIn("old_title2_date", text)
        self.assertIn("a11y-statement-check %s (statement_template_check %s)"
                      % (a.__version__, c.__version__), text)


class DocTests(unittest.TestCase):
    def read(self, *parts):
        with open(os.path.join(*parts), encoding="utf-8") as f:
            return f.read()

    def test_documented(self):
        readme = self.read(HERE, "README.md")
        skill = self.read(SKILL_DIR, "SKILL.md")
        self.assertIn("test_last_edited.py", readme)
        self.assertIn("- **%s:**" % c.__version__, readme)
        self.assertIn("@v%s" % a.__version__, readme)
        self.assertIn("Since 0.10.2", skill)
        self.assertIn("Last Edited: April 24, 2026", readme)
        self.assertGreaterEqual(tuple(int(x) for x in c.__version__.split(".")), (0, 10, 2))
        self.assertEqual(a.__version__.split(".")[:2], c.__version__.split(".")[:2])


if __name__ == "__main__":
    unittest.main()
