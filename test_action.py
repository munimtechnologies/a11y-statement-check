# Copyright 2026 Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
"""Offline tests of the GitHub Action (action.yml + action_run.py). No network is used.
Made by MV2 of Munim, Inc. with AI agents."""

import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import action_run as a  # noqa: E402

FILLER = (" We want everyone who visits this website to feel welcome and find the information they "
          "need. We are working to meet the Web Content Accessibility Guidelines (WCAG) 2.1 Level AA "
          "and we test new pages before they go live.")
DRAFT = ("# Accessibility statement\n\n"
         "[Your Agency/Website Name] is committed to accessibility.\n"
         "Please contact us at [Contact Email] and we will reply within\n"
         "[X business\n  days].\n" + FILLER + "\n")
CLEAN = "# Accessibility statement\n\nThe Town of Example is committed to accessibility." + FILLER + "\n"
HTML = ("<!doctype html><html><head><title>Accessibility</title><script>var x = '[Insert name]';"
        "</script></head><body><h1>Accessibility</h1><p>To help us make the Your School website a "
        "positive place for everyone, we've been using the Web Content Accessibility Guidelines "
        "(WCAG) 2.0.</p><p>Call 555-555-5555.</p><p>We want everyone who visits this website to "
        "feel welcome and find the information they need.</p></body></html>")


def fake_get(pages):
    def get(url, timeout=20):
        if url in pages:
            return 200, url, "text/html; charset=utf-8", pages[url].encode("utf-8")
        return 404, url, "", b""
    return get


class Repo(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.dir, "docs", "old"))
        self.write("docs/draft.md", DRAFT)
        self.write("docs/clean.md", CLEAN)
        self.write("docs/old/page.html", HTML)
        self.summary = os.path.join(self.dir, "summary.md")
        self.outputs = os.path.join(self.dir, "outputs.txt")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def write(self, rel, text):
        with open(os.path.join(self.dir, *rel.split("/")), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)

    def run_action(self, get=None, **inputs):
        env = {"GITHUB_WORKSPACE": self.dir, "GITHUB_STEP_SUMMARY": self.summary,
               "GITHUB_OUTPUT": self.outputs}
        for k, v in inputs.items():
            env["STC_" + k.upper()] = v
        out = io.StringIO()
        code = a.main(env=env, out=out, get=get or fake_get({}))
        return code, out.getvalue()

    def outputs_dict(self):
        with open(self.outputs, encoding="utf-8") as f:
            return dict(line.split("=", 1) for line in f.read().splitlines())

    def read(self, path):
        with open(path, encoding="utf-8") as f:
            return f.read()


class ActionRunTests(Repo):
    def test_placeholder_fails_with_annotations_at_the_right_lines(self):
        code, log = self.run_action(text_files="docs/draft.md\ndocs/clean.md")
        self.assertEqual(code, 1)
        self.assertIn("::error file=docs/draft.md,line=3,title=Accessibility statement placeholder::"
                      "'[Your Agency/Website Name]' is still a template placeholder (revize/agency_name)",
                      log)
        self.assertIn("file=docs/draft.md,line=4,", log)
        self.assertIn("file=docs/draft.md,line=5,", log)  # [X business / days] spans two lines
        self.assertEqual(log.count("::error "), 3)
        self.assertIn("1 of 2 statements read with a template placeholder; 0 not read", log)
        self.assertEqual(self.outputs_dict(),
                         {"placeholder-pages": "1", "pages-read": "2", "unread": "0"})
        summary = self.read(self.summary)
        self.assertIn("| docs/draft.md | unfinished template (3 placeholders) |", summary)
        self.assertIn("| docs/clean.md | no template placeholder found | none | 2.1 |", summary)
        self.assertIn("not legal advice", summary)

    def test_clean_draft_passes(self):
        code, log = self.run_action(text_files="docs/clean.md")
        self.assertEqual(code, 0)
        self.assertNotIn("::error", log)
        self.assertEqual(self.outputs_dict()["placeholder-pages"], "0")

    def test_warning_only(self):
        code, log = self.run_action(text_files="docs/draft.md", fail_on_placeholder="false")
        self.assertEqual(code, 0)
        self.assertNotIn("::error", log)
        self.assertEqual(log.count("::warning "), 3)

    def test_glob_and_html(self):
        code, log = self.run_action(text_files="docs/*.md", html_files="docs/**/*.html")
        self.assertEqual(code, 1)
        self.assertIn("docs/old/page.html", log)
        self.assertIn("school/your_school", log)
        self.assertIn("school/fake_phone", log)
        self.assertIn("file=docs/old/page.html,line=1,", log)
        self.assertNotIn("Insert name", log)  # script text is not visible text
        self.assertIn("::notice file=docs/old/page.html,title=Accessibility statement%3A only_wcag_2_0::",
                      log)
        self.assertEqual(self.outputs_dict()["pages-read"], "3")

    def test_unmatched_pattern(self):
        code, log = self.run_action(text_files="docs/clean.md\nnope/*.md")
        self.assertEqual(code, 2)
        self.assertIn("::error title=a11y-statement-check::no file matches 'nope/*.md'", log)
        self.assertEqual(self.outputs_dict()["unread"], "1")
        code, log = self.run_action(text_files="docs/clean.md\nnope/*.md", fail_on_unread="no")
        self.assertEqual(code, 0)
        self.assertIn("::warning title=a11y-statement-check::no file matches", log)

    def test_placeholder_wins_over_unread(self):
        code, _ = self.run_action(text_files="docs/draft.md\nmissing.md")
        self.assertEqual(code, 1)

    def test_urls(self):
        page = "<html><body><p>[YOUR COMPANY NAME] is committed." + FILLER + "</p></body></html>"
        get = fake_get({"https://example.org/accessibility": page})
        code, log = self.run_action(get=get,
                                    urls="https://example.org/accessibility\nhttps://example.org/gone")
        self.assertEqual(code, 1)
        self.assertIn("::error title=Accessibility statement placeholder::"
                      "https://example.org/accessibility: '[YOUR COMPANY NAME]'", log)
        self.assertIn("https://example.org/gone not read: http_404", log)
        self.assertEqual(self.outputs_dict(), {"placeholder-pages": "1", "pages-read": "1", "unread": "1"})

    def test_nothing_given(self):
        code, log = self.run_action(text_files="\n# just a comment\n")
        self.assertEqual(code, 2)
        self.assertIn("give at least one of text-files, html-files or urls", log)

    def test_json_report(self):
        code, _ = self.run_action(text_files="docs/draft.md", json_report="report.json")
        self.assertEqual(code, 1)
        with open(os.path.join(self.dir, "report.json"), encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["version"], a.__version__)
        self.assertEqual(data["results"][0]["source"], "docs/draft.md")
        self.assertEqual(len(data["results"][0]["placeholders"]), 3)

    def test_escaping(self):
        self.assertEqual(a.esc_data("50%\r\nx"), "50%25%0D%0Ax")
        self.assertEqual(a.esc_prop("a:b,c%"), "a%3Ab%2Cc%25")
        line = a.command("error", "bad\nnews", file="dir/a,b.md", line=7)
        self.assertEqual(line, "::error file=dir/a%2Cb.md,line=7,title=Accessibility statement "
                               "placeholder::bad%0Anews")

    def test_flags_and_entries(self):
        self.assertEqual(a.entries(" a \n\n# c\n b\n"), ["a", "b"])
        self.assertTrue(a.flag("", True))
        self.assertFalse(a.flag("False", True))
        self.assertTrue(a.flag("YES", False))


class ActionFileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(HERE, "action.yml"), encoding="utf-8") as f:
            cls.text = f.read()
        cls.lines = cls.text.splitlines()

    def section(self, name):
        start = self.lines.index(name + ":") + 1
        keys = []
        for line in self.lines[start:]:
            if line and not line.startswith(" "):
                break
            m = re.match(r"^  ([a-z][a-z-]*):\s*$", line)
            if m:
                keys.append(m.group(1))
        return keys

    def test_composite_runs_the_entry_point(self):
        self.assertIn("  using: composite", self.lines)
        self.assertIn('"$PY" -I "$GITHUB_ACTION_PATH/action_run.py"', self.text)
        self.assertTrue(os.path.isfile(os.path.join(HERE, "action_run.py")))

    def test_inputs_reach_the_script_only_through_env(self):
        inputs = self.section("inputs")
        self.assertEqual(inputs, ["text-files", "html-files", "urls", "fail-on-placeholder",
                                  "fail-on-unread", "json-report"])
        used = re.findall(r"\$\{\{ inputs\.([a-z-]+) \}\}", self.text)
        self.assertEqual(sorted(used), sorted(inputs))
        for name in inputs:
            env = "STC_" + name.upper().replace("-", "_")
            self.assertIn("        %s: ${{ inputs.%s }}" % (env, name), self.lines)
            self.assertIn(env, a.__doc__)
        run = self.text[self.text.index("      run: |"):]
        self.assertNotIn("${{", run)  # no expression is pasted into the shell script

    def test_outputs_match_what_the_script_writes(self):
        outputs = self.section("outputs")
        self.assertEqual(outputs, ["placeholder-pages", "pages-read", "unread"])
        with open(a.__file__, encoding="utf-8") as f:
            source = f.read()
        for name in outputs:
            self.assertIn("${{ steps.check.outputs.%s }}" % name, self.text)
            self.assertIn(name + "=", source)

    def test_metadata(self):
        self.assertIn("name: Accessibility statement template check", self.lines)
        self.assertIn("author: MV2 of Munim, Inc.", self.lines)
        self.assertIn("Apache-2.0", self.text)
        self.assertNotIn("\t", self.text)

    def test_readme_documents_every_input(self):
        with open(os.path.join(HERE, "README.md"), encoding="utf-8") as f:
            readme = f.read()
        for name in self.section("inputs") + self.section("outputs"):
            self.assertIn("`%s`" % name, readme)
        self.assertIn("uses: munimtechnologies/a11y-statement-check@v0.2.0", readme)


if __name__ == "__main__":
    unittest.main()
