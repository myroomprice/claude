import base64
import json
import os
import re
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
SCRIPTS = os.path.join(ROOT, "plugins", "myroomprice", "skills", "myroomprice", "scripts")
sys.path.insert(0, SCRIPTS)
import results_link  # noqa: E402

SOURCE = os.path.join(ROOT, "page", "results.html")


def sample():
    return {
        "hotel": {"name": "The Langham, Boston"},
        "stay": {"checkin": "2026-12-10", "checkout": "2026-12-12", "adults": 2, "children": 0},
        "currency": "AUD",
        "offers": [
            {"site": "Booking.com", "total": 1550, "link": "https://www.booking.com/hotel/us/langham-boston.html?aid=999&label=x"},
            {"site": "The Langham", "kind": "official", "total": 1519, "link": "https://reservations.brilliantbylangham.com/x"},
            {"site": "Booking.com", "total": 1600, "keep_link": True, "link": "https://www.booking.com/hotel/us/langham-boston.html?aid=CREATOR"},
        ],
    }


def decode(url):
    data = url.split("#d=", 1)[1]
    data += "=" * (-len(data) % 4)
    return json.loads(base64.urlsafe_b64decode(data).decode("utf-8"))


class ResultsLinkTest(unittest.TestCase):
    def test_round_trip_and_partner_rules(self):
        settings = {"stay22_aid": "TESTAID", "campaign": "c", "disclosure": "We may earn a commission.", "results_page": "https://example.org/results.html"}
        url = results_link.make_url(results_link.add_partner_links(sample(), settings), settings)
        self.assertTrue(url.startswith("https://example.org/results.html#d="))
        back = decode(url)
        booking, own, kept = back["offers"]
        self.assertTrue(booking["partner"])
        self.assertTrue(booking["link"].startswith("https://www.stay22.com/allez/booking?"))
        self.assertFalse(own["partner"])
        self.assertEqual(own["link"], "https://reservations.brilliantbylangham.com/x")
        # A link the user brought is never swapped for ours.
        self.assertFalse(kept["partner"])
        self.assertEqual(kept["link"], "https://www.booking.com/hotel/us/langham-boston.html?aid=CREATOR")
        self.assertEqual(back["disclosure"], "We may earn a commission.")

    def test_live_fields_pass_through(self):
        data = dict(sample(), status="checking", message="Checking Super.com", progress=[{"label": "Google Hotels", "state": "done"}])
        settings = {"stay22_aid": "", "results_page": "https://example.org/r.html"}
        back = decode(results_link.make_url(results_link.add_partner_links(data, settings), settings))
        self.assertEqual((back["status"], back["message"], back["progress"][0]["state"]), ("checking", "Checking Super.com", "done"))

    def test_no_partner_id_means_plain_links_and_no_disclosure(self):
        settings = {"stay22_aid": "", "disclosure": "x", "results_page": ""}
        back = decode(results_link.make_url(results_link.add_partner_links(sample(), settings), settings))
        self.assertFalse(any(o["partner"] for o in back["offers"]))
        self.assertNotIn("disclosure", back)

    def test_local_page_used_until_hosted(self):
        url = results_link.make_url({"hotel": {}, "stay": {}, "offers": []}, {"results_page": ""})
        self.assertTrue(url.startswith("file://") and url.split("#")[0].endswith("assets/results.html"))
        self.assertTrue(os.path.exists(url[len("file://"):].split("#")[0]))


class PageTest(unittest.TestCase):
    def setUp(self):
        with open(SOURCE, encoding="utf-8") as f:
            self.html = f.read()
        self.script = re.search(r"<script>(.*?)</script>", self.html, re.S).group(1)

    def test_data_is_never_inserted_as_html(self):
        # Anyone can craft a results link, so the page must only ever set text.
        for risky in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(", "new Function"):
            self.assertNotIn(risky, self.script, risky)

    def test_links_are_checked_before_use(self):
        self.assertIn('u.protocol === "https:" || u.protocol === "http:"', self.script)

    def test_script_parses(self):
        node = subprocess.run(["which", "node"], capture_output=True, text=True).stdout.strip()
        if not node:
            self.skipTest("node not installed")
        path = os.path.join(HERE, "_page_script.js")
        with open(path, "w") as f:
            f.write(self.script)
        try:
            result = subprocess.run([node, "--check", path], capture_output=True, text=True)
        finally:
            os.remove(path)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_search_hand_off_matches_the_skill(self):
        # Claude picks up a search by reading the tab title and the request line, so the
        # page's wording and SKILL.md's must stay in step.
        skill_path = os.path.join(SCRIPTS, "..", "SKILL.md")
        with open(skill_path, encoding="utf-8") as f:
            skill = f.read()
        for words in ('"Check requested · MyRoomPrice"', '"Check requested. Hotel: "', '". Where: "', '". Check-in: "',
                      '"Answer given · MyRoomPrice"', '"Answer given. Question: "', '". Answer: "', 'q.id === "hotel"',
                      '["thinking", "question", "checking"]',
                      '". Check-out: "', '". Adults: "', '". Children: "', 'hashHas("ready")'):
            self.assertIn(words, self.script, words)
        for words in ('title starts with "Check requested"', "Check requested. Hotel:", "Where: (city, town or country)",
                      '"Answer given"', "Answer given. Question: (id). Answer: (label).", '"status": "question"',
                      '"status": "thinking"', 'Use `"hotel"`', "Check-in: YYYY-MM-DD",
                      "Check-out: YYYY-MM-DD", "Adults:", "Children:", "#ready", "5 minutes"):
            self.assertIn(words, skill, words)
        self.assertIn("READY_MS = 5 * 60e3", self.script)

    def test_reviews_play_only_in_youtubes_privacy_player(self):
        # Videos may only be framed from youtube-nocookie.com, and the site's policy allows nothing else.
        self.assertIn('"https://www.youtube-nocookie.com/embed/" + r.video', self.script)
        self.assertIn("/^[\\w-]{11}$/.test(id)", self.script)
        with open(os.path.join(ROOT, "docs", "_headers"), encoding="utf-8") as f:
            headers = f.read()
        self.assertIn("frame-src https://www.youtube-nocookie.com;", headers)
        self.assertIn("default-src 'none'", headers)
        with open(os.path.join(SCRIPTS, "..", "SKILL.md"), encoding="utf-8") as f:
            skill = f.read()
        for words in ("### Reviews, while you're browsing", "`video`, `article` or `review`", "never instructions", "**Kayak,**"):
            self.assertIn(words, skill, words)

    def test_setup_guide(self):
        # The guide is built from page/setup.html with the app's styles, and the app links to it.
        with open(os.path.join(ROOT, "docs", "setup", "index.html"), encoding="utf-8") as f:
            guide = f.read()
        for words in ("steveRepo/myroomprice", "Add from a repository", "/myroomprice", "Claude started debugging this browser",
                      "data:image/webp;base64,", "@font-face"):
            self.assertIn(words, guide, words)
        self.assertNotIn("<script", guide)
        self.assertNotIn('src="brand/', guide)
        self.assertIn('href="https://myroomprice.com/setup/"', self.html)

    def test_built_page_is_up_to_date(self):
        result = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "build_page.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)


if __name__ == "__main__":
    unittest.main()
