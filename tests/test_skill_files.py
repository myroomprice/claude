import os
import re
import shutil
import subprocess
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


class PageReaderTest(unittest.TestCase):
    """scripts/read_offers.js runs inside booking sites in the user's own browser."""

    def test_is_valid_javascript(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node not installed")
        # It uses top-level await, which the browser's JavaScript tool allows, so check it as a module.
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "reader.mjs")
            with open(path, "w") as f:
                f.write(read("scripts/read_offers.js"))
            result = subprocess.run([node, "--check", path], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_only_looks(self):
        # It must never click, type, submit or leave the page: the user is signed in there.
        code = re.sub(r"//.*", "", read("scripts/read_offers.js"))
        for bad in [".click(", ".submit(", ".focus(", "dispatchEvent", "location.href =", "location.assign",
                    "location.replace", ".value =", "fetch(", "XMLHttpRequest", "localStorage", "document.cookie"]:
            self.assertNotIn(bad, code)

    def test_returns_one_json_line(self):
        code = read("scripts/read_offers.js")
        self.assertIn("await (async () => {", code)
        self.assertIn("return JSON.stringify({", code)
        for field in ["hotel", "page", "offers", "flags"]:
            self.assertRegex(code, r"\b%s[,:]" % field)


if __name__ == "__main__":
    unittest.main()
