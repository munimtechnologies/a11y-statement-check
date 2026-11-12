"""Offline tests of planned review dates in statement_template_check.py (since 0.7.0; no network).

A date right after "will be", "is due to be", "next" and the like ("It will be reviewed in March
2027") is a planned review, not the latest one, so since 0.7.0 it is not read as the statement's
date. MV2's census of UK government organisations' accessibility statements (title2-pdf-census,
results/govuk-orgs/GOVUK-STOCK-RESULT.md) found one statement whose date was such a planned review.

Apache-2.0. Made by MV2 of Munim, Inc. with AI agents.
"""

import datetime
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.join(HERE, "skills", "accessibility-statement-check")
sys.path.insert(0, SKILL_DIR)
sys.path.insert(0, HERE)
import statement_template_check as c  # noqa: E402

TODAY = datetime.date(2026, 11, 11)


class PlannedDateTests(unittest.TestCase):
    def test_planned_review_is_not_the_statement_date(self):
        text = ("This statement was prepared in March 2026. It will be reviewed in March 2027. "
                "This website was last tested in March 2026.")
        self.assertEqual(c.statement_dates(text), ("", "2026-03-31", "2026-03-31", "prepared"))

    def test_past_review_kept_and_planned_update_left_out(self):
        text = "It was last reviewed on 1 May 2026 and is due to be updated in May 2027."
        self.assertEqual(c.statement_dates(text), ("2026-05-01", "", "2026-05-01", "reviewed"))

    def test_other_planned_wordings(self):
        for text in ("This statement will next be reviewed in June 2027.",
                     "This statement should be reviewed on 1 June 2027.",
                     "It must be updated in June 2027.",
                     "The statement is next reviewed in June 2027.",
                     "A new statement will be published on 1 January 2027."):
            self.assertEqual(c.statement_dates(text), ("", "", "", ""), text)

    def test_past_dates_still_read(self):
        self.assertEqual(c.statement_dates("The statement was updated in July 2025."),
                         ("2025-07-31", "", "2025-07-31", "reviewed"))
        self.assertEqual(c.statement_dates("This statement was last reviewed on 3 June 2024."),
                         ("2024-06-03", "", "2024-06-03", "reviewed"))
        self.assertEqual(c.statement_dates("This statement was prepared on 23 September 2020. "
                                           "It was last reviewed on 14 March 2025."),
                         ("2025-03-14", "2020-09-23", "2025-03-14", "reviewed"))

    def test_planned_date_no_longer_hides_an_old_statement(self):
        text = ("This statement was prepared on 1 June 2024. It will be reviewed in June 2026. "
                "We tested the website against the Web Content Accessibility Guidelines version "
                "2.2 AA standard.")
        r = c.check_text(text, today=TODAY)
        self.assertEqual((r["statement_date"], r["date_source"]), ("2024-06-01", "prepared"))
        self.assertEqual(r["statement_age_days"], (TODAY - datetime.date(2024, 6, 1)).days)
        self.assertIn("old_statement_date", [n["id"] for n in r["notes"]])

    def test_planned_helper(self):
        flat = "It was prepared in 2020. It will be reviewed in March 2027."
        m = c.REVIEW_RE.search(flat)
        self.assertTrue(c._planned(flat, m))
        flat = "It was last reviewed on 1 May 2026."
        self.assertFalse(c._planned(flat, c.REVIEW_RE.search(flat)))


class DocTests(unittest.TestCase):
    def read(self, *parts):
        with open(os.path.join(*parts), encoding="utf-8") as f:
            return f.read()

    def test_documented(self):
        readme = self.read(HERE, "README.md")
        skill = self.read(SKILL_DIR, "SKILL.md")
        self.assertGreaterEqual(tuple(int(x) for x in c.__version__.split(".")), (0, 7, 0))
        self.assertIn("- **%s:**" % c.__version__, readme)
        self.assertIn("@v%s" % c.__version__, readme)
        self.assertNotIn("@v0.6.0", readme)
        self.assertIn("test_planned_review.py", readme)
        self.assertIn("It will be reviewed in March 2027", readme)
        self.assertIn("planned date", skill)


if __name__ == "__main__":
    unittest.main()
