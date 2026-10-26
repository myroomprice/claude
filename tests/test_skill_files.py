import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.join(HERE, "..", "plugins", "myroomprice", "skills", "myroomprice")


def read(name):
    with open(os.path.join(SKILL_DIR, name)) as f:
        return f.read()


class SkillFileTest(unittest.TestCase):
    def test_no_dollar_digit_text(self):
        # Skills fill $1, $2 ... with the words the user typed, so "A$1,434"
        # turned into "Aprice,434" in testing. Money must be written as "AUD 1,434".
        bad = re.findall(r".{0,20}\$\d.{0,10}", read("SKILL.md"))
        self.assertEqual(bad, [], "dollar sign followed by a digit in SKILL.md")

    def test_description_fits(self):
        front = re.match(r"^---\n(.*?)\n---\n", read("SKILL.md"), re.S).group(1)
        description = re.search(r"^description: (.*)$", front, re.M).group(1)
        self.assertLessEqual(len(description), 1024)

    def test_referenced_files_exist(self):
        text = read("SKILL.md")
        for path in set(re.findall(r"(references/[\w.-]+\.md|scripts/[\w.-]+\.(?:py|js))", text)):
            self.assertTrue(os.path.exists(os.path.join(SKILL_DIR, path)), path)


class BrowserScriptTest(unittest.TestCase):
    """The scripts in scripts/*.js run inside web pages in the user's own, signed-in browser.
    They're built short from readable sources in browser/ (tools/build_scripts.py)."""

    SCRIPTS = {
        "scripts/find_pages.js": ["sites", "official"],
        "scripts/watch_page.js": ["request", "page"],
        "scripts/load_rooms.js": ["rooms"],
    }

    def test_are_valid_javascript(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node not installed")
        # They use top-level await, which the browser's JavaScript tool allows, so check them as modules.
        with tempfile.TemporaryDirectory() as tmp:
            for name in self.SCRIPTS:
                path = os.path.join(tmp, os.path.basename(name) + ".mjs")
                with open(path, "w") as f:
                    f.write(read(name))
                result = subprocess.run([node, "--check", path], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, name + ": " + result.stderr)

    def test_built_copies_are_up_to_date(self):
        if not shutil.which("npx"):
            self.skipTest("node not installed")
        result = subprocess.run([sys.executable, os.path.join(HERE, "..", "tools", "build_scripts.py"), "--check"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def test_are_short(self):
        # Claude types each one out every time it runs it; keep them small.
        for name in self.SCRIPTS:
            self.assertLess(len(read(name)), 2600, name)

    def test_only_look(self):
        # They must never click, type, submit or leave the page, or send anything anywhere.
        for name in self.SCRIPTS:
            code = read(name)
            for bad in [".click(", ".submit(", ".focus(", "dispatchEvent", "location.href=", "location.href =", "location.assign",
                        "location.replace", ".value=", ".value =", "fetch(", "XMLHttpRequest", "localStorage", "document.cookie"]:
                self.assertNotIn(bad, code, name)

    def test_return_one_short_json_line(self):
        for name, fields in self.SCRIPTS.items():
            code = read(name)
            self.assertRegex(code, r'^await\(async\((?:WANT="HOTEL NAME")?\)=>\{', name)
            answer = code[code.rindex("JSON.stringify({"):]
            for field in fields:
                self.assertRegex(answer, r"\b%s\b" % field, name)

    def test_watcher_and_page_use_the_same_marks(self):
        # The page counts Claude as connected from the watcher's check-ins; the names must match.
        with open(os.path.join(HERE, "..", "browser", "watch_page.js"), encoding="utf-8") as f:
            watcher = f.read()
        with open(os.path.join(HERE, "..", "page", "results.html"), encoding="utf-8") as f:
            page = f.read()
        for mark in ("data-claude-seen", "data-claude-took"):
            self.assertIn('"%s"' % mark, read("scripts/watch_page.js"))
            self.assertIn('"%s"' % mark, page)
        # It waits well under the browser tool's 45-second limit.
        self.assertIn("i < 60", watcher)
        self.assertIn("await wait(500)", watcher)

    def test_room_text_goes_where_get_page_text_looks(self):
        # get_page_text reads the first <article> (or <main>) on the page; the loader puts the rooms there.
        code = read("scripts/load_rooms.js")
        self.assertIn('createElement("article")', code)
        self.assertIn("document.body.prepend(", code)

    def test_no_dated_addresses_returned(self):
        # Claude in Chrome hides any answer carrying a ?query, so the finder returns bare addresses.
        self.assertIn('split("?")[0]', read("scripts/find_pages.js"))


if __name__ == "__main__":
    unittest.main()
