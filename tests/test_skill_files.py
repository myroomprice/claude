import os
import re
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
        for path in set(re.findall(r"(references/[\w.-]+\.md|scripts/[\w.-]+\.py)", text)):
            self.assertTrue(os.path.exists(os.path.join(SKILL_DIR, path)), path)


if __name__ == "__main__":
    unittest.main()
