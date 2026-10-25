import os
import sys
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "plugins", "myroomprice", "skills", "myroomprice", "scripts"))
import sweep  # noqa: E402


def rate(after, before):
    return {"extracted_lowest": before, "extracted_before_taxes_fees": before,
            "extracted_after_taxes_fees": after}


ARGS = types.SimpleNamespace(hotel="The Langham Boston", check_in="2026-12-10", check_out="2026-12-12",
                             adults=2, rooms=1, children_ages="", currency="USD", gl="us",
                             tripadvisor_key="g60745-d114149", tripadvisor_url=None)


def empty_result():
    return {"query": {}, "nights": 2, "checked_at": "now", "hotel": None,
            "feeds_used": [], "skipped": [], "offers": []}


class SerpApiTest(unittest.TestCase):
    """Google Hotels via SerpApi, using responses shaped like SerpApi's documented ones."""

    def setUp(self):
        self.listing = {"properties": [
            {"type": "hotel", "name": "Langham Place Fifth Avenue", "property_token": "WRONG"},
            {"type": "hotel", "name": "The Langham, Boston", "property_token": "RIGHT"},
        ]}
        self.details = {
            "name": "The Langham, Boston", "address": "250 Franklin St",
            "featured_prices": [{
                "source": "The Langham, Boston", "official": True, "link": "https://official",
                "rate_per_night": rate(560, 480), "total_rate": rate(1120, 960),
                "rooms": [
                    {"name": "Superior King", "rates": [
                        {"free_cancellation": False, "total_rate": rate(1120, 960)},
                        {"free_cancellation": True, "total_rate": rate(1240, 1060)}]},
                    {"name": "Deluxe King", "rates": [
                        {"free_cancellation": True, "total_rate": rate(1400, 1200)}]},
                ]}],
            "prices": [
                {"source": "The Langham, Boston", "official": True,
                 "rate_per_night": rate(560, 480), "total_rate": rate(1120, 960)},
                {"source": "Booking.com", "link": "https://booking", "rate_per_night": rate(540, 465),
                 "total_rate": rate(1080, 930), "free_cancellation": True,
                 "free_cancellation_until_date": "Dec 8", "free_cancellation_until_time": "11:59 PM"},
                {"source": "Expedia.com", "rate_per_night": {"extracted_lowest": 470}},
            ],
        }
        self.calls = []

        def fake_get_json(url):
            self.calls.append(url)
            return self.details if "property_token=RIGHT" in url else self.listing

        self._saved = (sweep.get_json, sweep.serpapi_key)
        sweep.get_json = fake_get_json
        sweep.serpapi_key = lambda: "TEST"

    def tearDown(self):
        sweep.get_json, sweep.serpapi_key = self._saved

    def test_picks_matching_hotel_and_ranks_all_in_prices_first(self):
        result = empty_result()
        sweep.sweep_serpapi(ARGS, 2, result)
        result["offers"].sort(key=sweep.sort_key)
        self.assertEqual(len(self.calls), 2)
        self.assertIn("property_token=RIGHT", self.calls[1])
        offers = {o["source"]: o for o in result["offers"]}
        self.assertEqual(len(result["offers"]), 3, "the official site should appear once")
        official = offers["The Langham, Boston"]
        self.assertTrue(official["official"])
        self.assertEqual((official["total"], official["room"], official["cheapest_refundable_total"]),
                         (1120, "Superior King", 1240))
        self.assertEqual(offers["Booking.com"]["free_cancellation_until"], "Dec 8 11:59 PM")
        self.assertFalse(offers["Expedia.com"]["total_includes_tax"])
        self.assertEqual([o["source"] for o in result["offers"]],
                         ["Booking.com", "The Langham, Boston", "Expedia.com"])


class XoteloTest(unittest.TestCase):
    def test_rate_is_the_whole_stay_not_per_night(self):
        saved = sweep.get_json
        sweep.get_json = lambda url: {"error": None, "result": {"rates": [
            {"code": "BookingCom", "name": "Booking.com", "rate": 936, "tax": None},
            {"code": "WIHP", "name": "Official Site", "rate": 936, "tax": None}]}}
        try:
            result = empty_result()
            sweep.sweep_xotelo(ARGS, 2, result)
        finally:
            sweep.get_json = saved
        booking = result["offers"][0]
        self.assertEqual((booking["total"], booking["per_night"]), (936, 468))
        self.assertTrue(result["offers"][1]["official"])


if __name__ == "__main__":
    unittest.main()
