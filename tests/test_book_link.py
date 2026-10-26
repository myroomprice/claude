import os
import sys
import types
import unittest
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "plugins", "myroomprice", "skills", "myroomprice", "scripts"))
import book_link  # noqa: E402

ARGS = types.SimpleNamespace(check_in="2026-12-10", check_out="2026-12-12", adults=2,
                             children_ages="", currency="aud")
WITH_ID = {"stay22_aid": "TESTAID", "campaign": "myroomprice", "disclosure": "d"}


def query(url):
    return dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))


class BookLinkTest(unittest.TestCase):
    def test_booking_link_becomes_partner_link_with_dates(self):
        url = "https://www.booking.com/hotel/us/langham-boston.html?aid=356980&label=gog235&checkin=2026-12-10"
        r = book_link.make_link(url, ARGS, WITH_ID)
        self.assertTrue(r["affiliate"])
        self.assertTrue(r["url"].startswith("https://www.stay22.com/allez/booking?"))
        q = query(r["url"])
        self.assertEqual(q["aid"], "TESTAID")
        # Other parties' affiliate codes are dropped; the booking details stay.
        self.assertEqual(q["link"], "https://www.booking.com/hotel/us/langham-boston.html?checkin=2026-12-10")
        self.assertEqual((q["checkin"], q["checkout"], q["adults"], q["currency"]),
                         ("2026-12-10", "2026-12-12", "2", "AUD"))
        self.assertEqual(q["campaign"], "myroomprice")

    def test_booking_details_survive_cleaning(self):
        # Hotel, dates, guests and the chosen room stay in the link; tracking and other
        # affiliates' IDs go. (Example links written for the test, not live pages.)
        url = ("https://www.booking.com/hotel/au/sheraton-on-the-park.html?aid=304142&label=gen173nr&sid=abc"
               "&checkin=2026-11-20&checkout=2026-11-22&group_adults=2&group_children=1&age=7&no_rooms=1"
               "&highlighted_blocks=12345_67_2_1_0&utm_source=news&gclid=xyz#RD12345")
        q = query(book_link.clean_hotel_url(url))
        for kept, value in [("checkin", "2026-11-20"), ("checkout", "2026-11-22"), ("group_adults", "2"),
                            ("group_children", "1"), ("age", "7"), ("no_rooms", "1"), ("highlighted_blocks", "12345_67_2_1_0")]:
            self.assertEqual(q.get(kept), value, kept)
        for gone in ("aid", "label", "sid", "utm_source", "gclid"):
            self.assertNotIn(gone, q, gone)
        self.assertTrue(book_link.clean_hotel_url(url).endswith("#RD12345"))

    def test_other_sites_affiliate_codes_are_dropped(self):
        agoda = "https://www.agoda.com/park-hyatt-tokyo/hotel/tokyo-jp.html?cid=1844104&tag=abc&checkIn=2027-03-01&los=3&adults=2&rooms=1"
        q = query(book_link.clean_hotel_url(agoda))
        self.assertEqual((q["checkIn"], q["los"], q["adults"], q["rooms"]), ("2027-03-01", "3", "2", "1"))
        self.assertNotIn("cid", q)
        self.assertNotIn("tag", q)
        expedia = "https://www.expedia.com.au/Sydney-Hotels.h123.Hotel-Information?chkin=2026-11-20&chkout=2026-11-22&rm1=a2&AFFCID=x&afflid=y&my_ad=z"
        q = query(book_link.clean_hotel_url(expedia))
        self.assertEqual((q["chkin"], q["chkout"], q["rm1"]), ("2026-11-20", "2026-11-22", "a2"))
        for gone in ("AFFCID", "afflid", "my_ad"):
            self.assertNotIn(gone, q)

    def test_partner_link_encodes_the_cleaned_page(self):
        url = "https://www.booking.com/hotel/au/x.html?checkin=2026-11-20&checkout=2026-11-22&group_adults=2&aid=1"
        r = book_link.make_link(url, ARGS, WITH_ID)
        # The page link travels as one encoded parameter, so its own & and = can't leak into Stay22's.
        self.assertIn("link=https%3A%2F%2Fwww.booking.com%2Fhotel%2Fau%2Fx.html%3Fcheckin%3D2026-11-20%26checkout%3D2026-11-22%26group_adults%3D2", r["url"])
        self.assertEqual(query(r["url"])["aid"], "TESTAID")

    def test_no_partner_id_leaves_the_link_untouched(self):
        url = "https://www.booking.com/hotel/au/x.html?aid=1&checkin=2026-11-20"
        r = book_link.make_link(url, ARGS, {"stay22_aid": ""})
        self.assertFalse(r["affiliate"])
        self.assertEqual(r["url"], url)

    def test_country_domains_are_recognised(self):
        cases = {
            "https://www.expedia.com.au/Boston-Hotels-The-Langham.h1.Hotel-Information": "expedia",
            "https://au.hotels.com/ho123/": "hotelscom",
            "https://www.agoda.com/the-langham-boston/hotel/boston-ma-us.html": "agoda",
            "https://www.stayz.com.au/12345": "vrbo",
            "https://www.kayak.co.uk/hotels/x": "kayak",
        }
        for url, provider in cases.items():
            self.assertEqual(book_link.make_link(url, ARGS, WITH_ID)["provider"], provider, url)

    def test_hotel_own_site_and_uncovered_sites_are_left_alone(self):
        for url in ["https://reservations.brilliantbylangham.com/en-US/booking/rooms?hotel=27423",
                    "https://www.super.com/travel/x?checkin_at=2026-12-10",
                    "https://www.trip.com/hotels/detail/?hotelId=1",
                    "https://notbooking.com.evil.example/hotel"]:
            r = book_link.make_link(url, ARGS, WITH_ID)
            self.assertFalse(r["affiliate"], url)
            self.assertEqual(r["url"], url)

    def test_lookalike_domains_are_not_matched(self):
        for host in ["fakebooking.com", "booking.com.example.net", "expedia.evil.com",
                     "myexpedia.com", "kayak.deals.example.org"]:
            self.assertIsNone(book_link.provider_for(host), host)
        for host in ["www.expedia.com", "expedia.co.uk", "www.expedia.com.au", "www.kayak.com"]:
            self.assertIsNotNone(book_link.provider_for(host), host)

    def test_no_partner_id_means_no_change(self):
        url = "https://www.booking.com/hotel/us/langham-boston.html"
        r = book_link.make_link(url, ARGS, {"stay22_aid": ""})
        self.assertFalse(r["affiliate"])
        self.assertEqual(r["url"], url)

    def test_children_are_passed_through(self):
        args = types.SimpleNamespace(**{**vars(ARGS), "children_ages": "4, 9"})
        q = query(book_link.make_link("https://www.booking.com/hotel/us/x.html", args, WITH_ID)["url"])
        self.assertEqual((q["children"], q["childrenAges"]), ("2", "4,9"))


if __name__ == "__main__":
    unittest.main()


class ResultsJsonTest(unittest.TestCase):
    def test_results_json_option(self):
        # --json prints the results with partner fields added, for handing to the page with a short script.
        import json, subprocess, sys, os
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "plugins", "myroomprice", "skills", "myroomprice", "scripts", "results_link.py")
        data = {"hotel": {"name": "Apollo Hotel"}, "stay": {"checkin": "2026-12-23", "checkout": "2026-12-24", "adults": 2},
                "offers": [{"site": "Booking.com", "total": 219, "link": "https://www.booking.com/hotel/au/quality-apollo-international.html?checkin=2026-12-23&checkout=2026-12-24"}]}
        out = subprocess.run([sys.executable, script, "--json", "-"], input=json.dumps(data), capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        back = json.loads(out.stdout)
        self.assertEqual(back["hotel"]["name"], "Apollo Hotel")
        self.assertIn("partner", back["offers"][0])
        self.assertTrue(back["offers"][0]["link"].startswith("https://www.booking.com/hotel/au/quality-apollo-international.html"))
