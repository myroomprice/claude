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
                      '"status": "thinking"', 'Use `"hotel"`', "Check-in: YYYY-MM-DD", '"Link: (address)"', '**A pasted link.**',
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
        for words in ("myroomprice/myroomprice", "Add from a repository", "/myroomprice", "Claude started debugging this browser",
                      "data:image/webp;base64,", "@font-face"):
            self.assertIn(words, guide, words)
        self.assertNotIn("<script", guide)
        self.assertNotIn('src="brand/', guide)
        self.assertIn('href="https://myroomprice.com/setup/"', self.html)

    def test_nothing_is_assumed_about_a_price(self):
        # A price is only "checked" when Claude says so; cancellation and taxes have an unknown state.
        self.assertIn('o.confirmed === true ? "checked" : "listed"', self.script)
        self.assertNotIn("o.confirmed !== false", self.script)
        self.assertIn('o.refundable === true ? true : o.refundable === false ? false : null', self.script)
        self.assertIn('"Cancellation terms not checked"', self.script)
        self.assertIn('o.taxes_included === false ? "excluded" : "unknown"', self.script)
        self.assertIn('unknown: "total, taxes not confirmed"', self.script)
        # Only checked prices, and only confirmed free cancellation, make the highlight tiles.
        self.assertIn("const confirmedOffers = () => state.data.offers.filter((o) => o.confirmed && !o.checking && o.total !== null);", self.script)
        self.assertIn("conf.filter((o) => o.refundable === true)", self.script)
        self.assertIn('offer.confirmed = offer.verified === "checked";', self.script)
        # A price before tax never beats an all-in total.
        self.assertIn("const TAX_RANK = { included: 0, unknown: 1, excluded: 2 };", self.script)
        self.assertIn("(TAX_RANK[a.taxes] - TAX_RANK[b.taxes]) || (a[key] - b[key])", self.script)

    def read_links(self, links):
        """Run the page's own link reader in Node on example links (written for the test, not live pages)."""
        node = subprocess.run(["which", "node"], capture_output=True, text=True).stdout.strip()
        if not node:
            self.skipTest("node not installed")
        script = self.script
        reader = script[script.index("  const COUNTRIES = {"):script.index("  function applyLink(text) {")]
        helpers = "\n".join(re.search(r"^  function %s\(.*$" % name, script, re.M).group(0) for name in ("parseDay",))
        helpers += "\n" + re.search(r"^  const isoDay = .*$", script, re.M).group(0)
        code = helpers + "\n" + reader + "\nconsole.log(JSON.stringify(" + json.dumps(links) + ".map(readHotelLink)));"
        result = subprocess.run([node, "-e", code], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_pasted_links_fill_in_the_search(self):
        booking, agoda, expedia, hotels, trip, other, junk = self.read_links([
            "https://www.booking.com/hotel/au/sheraton-on-the-park.en-gb.html?aid=304142&label=x&checkin=2026-11-20&checkout=2026-11-23&group_adults=2&group_children=1&age=7&no_rooms=1",
            "https://www.agoda.com/park-hyatt-tokyo/hotel/tokyo-jp.html?checkIn=2027-03-01&los=3&adults=2&rooms=1&children=0&cid=1844104",
            "https://www.expedia.com.au/Sydney-Hotels-Sheraton-Grand-Sydney-Hyde-Park.h17004.Hotel-Information?chkin=20%2F11%2F2026&chkout=22%2F11%2F2026&rm1=a2%3Ac7",
            "https://au.hotels.com/ho123456/the-langham-sydney-sydney-australia/?chkin=2026-12-10&chkout=2026-12-12&rm1=a2",
            "https://www.trip.com/hotels/bangkok-hotel-detail-1234567/mandarin-oriental-bangkok/?checkIn=2027-01-05&checkOut=2027-01-08&adult=2&children=0",
            "https://www.marriott.com/en-us/hotels/sydsi-sheraton-grand-sydney-hyde-park/overview/?arrivalDate=x&checkin=2026-11-20&checkout=2026-11-22&adults=2",
            "not a link at all",
        ])
        self.assertEqual((booking["hotel"], booking["where"], booking["checkin"], booking["checkout"], booking["adults"], booking["children"], booking["site"]),
                         ("Sheraton on the Park", "Australia", "2026-11-20", "2026-11-23", 2, 1, "Booking.com"))
        self.assertEqual((agoda["hotel"], agoda["where"], agoda["checkin"], agoda["checkout"], agoda["adults"]),
                         ("Park Hyatt Tokyo", "Tokyo, Japan", "2027-03-01", "2027-03-04", 2))
        self.assertEqual((expedia["hotel"], expedia["where"], expedia["checkin"], expedia["checkout"], expedia["adults"], expedia["children"]),
                         ("Sheraton Grand Sydney Hyde Park", "Sydney", "2026-11-20", "2026-11-22", 2, 1))
        self.assertEqual((hotels["checkin"], hotels["checkout"], hotels["adults"], hotels["site"]), ("2026-12-10", "2026-12-12", 2, "Hotels.com"))
        self.assertEqual((trip["hotel"], trip["where"], trip["checkin"], trip["checkout"]), ("Mandarin Oriental Bangkok", "Bangkok", "2027-01-05", "2027-01-08"))
        self.assertEqual((other["hotel"], other["checkin"], other["checkout"], other["site"]),
                         ("Sydsi Sheraton Grand Sydney Hyde Park", "2026-11-20", "2026-11-22", "marriott.com"))
        self.assertIsNone(junk)
        # The link travels to Claude in the request line, and only web links are accepted.
        self.assertIn('(state.link ? " Link: " + state.link.link : "")', self.script)
        self.assertIn('if (u.protocol !== "https:" && u.protocol !== "http:") return null;', self.script)

    def test_recent_searches_stay_in_the_browser(self):
        # Kept in localStorage only, every access allowed to fail, capped, and hidden while results show.
        self.assertIn('const RECENT_KEY = "myroomprice.recent.v1";', self.script)
        self.assertIn("const RECENT_MAX = 5;", self.script)
        self.assertIn('try { localStorage.setItem(RECENT_KEY', self.script)
        self.assertIn('JSON.parse(localStorage.getItem(RECENT_KEY) || "[]")', self.script)
        self.assertNotIn("fetch(", self.script)
        self.assertNotIn("XMLHttpRequest", self.script)
        self.assertIn("box.hidden = !!state.data || !list.length;", self.script)
        self.assertIn("Your recent searches are kept only in this browser", self.html)

    def test_share_uses_the_pages_own_link(self):
        self.assertIn("navigator.share({ title: d.hotel.name + \" · MyRoomPrice\", text, url: location.href })", self.script)
        self.assertIn("navigator.clipboard.writeText(text + ", self.script)

    def test_one_worker_tab_and_the_debugging_bar(self):
        with open(os.path.join(SCRIPTS, "..", "SKILL.md"), encoding="utf-8") as f:
            skill = f.read()
        for words in ("**two tabs at most**", "**Don't click anything that opens a new tab.**", "## Keep it quick", "## Pop-ups",
                      "Press Escape first", "Claude started debugging this browser"):
            self.assertIn(words, skill, words)
        self.assertNotIn('Click "Visit site", or "Get price" for the official site.', skill)
        # The page tells the user the bar is normal, while Claude is working and in the FAQ.
        self.assertIn("don't click Cancel or close the background tab until the check is finished", self.html)
        self.assertIn('$("keep-open").hidden = !(live() || watching());', self.script)
        self.assertIn("Why does Chrome say", self.html)

    def test_built_page_is_up_to_date(self):
        result = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "build_page.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)


if __name__ == "__main__":
    unittest.main()
