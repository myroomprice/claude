import os
import sys
import types
import unittest
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "plugins", "myroomsearch", "skills", "myroomsearch", "scripts"))
import book_link  # noqa: E402

ARGS = types.SimpleNamespace(check_in="2026-12-10", check_out="2026-12-12", adults=2,
                             children_ages="", currency="aud")
WITH_ID = {"stay22_aid": "TESTAID", "campaign": "myroomsearch", "disclosure": "d"}


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
        # Other parties' tracking codes are dropped from the hotel page link.
        self.assertEqual(q["link"], "https://www.booking.com/hotel/us/langham-boston.html")
        self.assertEqual((q["checkin"], q["checkout"], q["adults"], q["currency"]),
                         ("2026-12-10", "2026-12-12", "2", "AUD"))
        self.assertEqual(q["campaign"], "myroomsearch")

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
