#!/usr/bin/env python3
"""Make the link that opens the results page for a finished price check.

Give it the results as JSON (a file, or - for standard input). It turns booking links into
partner links where it can (the same rules as book_link.py), adds the disclosure when any
link is a partner link, and prints one link to open in a new tab. The results travel in the
part of the link after #, which browsers never send to a server.

Results format (only "hotel", "stay" and "offers" are required):
{
  "hotel": {"name": "The Langham, Boston", "where": "Boston, USA"},
  "stay": {"checkin": "2026-12-10", "checkout": "2026-12-12", "adults": 2, "children": 0},
  "currency": "AUD",
  "checked": "2:30pm, 25 Oct",
  "summary": "One or two sentences: the answer and its main catch.",
  "offers": [
    {"site": "Super.com", "logo": "supercom", "kind": "aggregator",
     "room": "Superior Room, 1 Queen", "room_note": "smaller room", "total": 1434,
     "verified": "checked", "taxes": "included",
     "refundable": true, "cancel_until": "", "pay": "now", "member": "",
     "includes": ["breakfast for two"], "notes": "",
     "this_page": false, "link": "https://...", "keep_link": false}
  ],
  "couldnt_check": [{"site": "Agoda", "why": "CAPTCHA"}],
  "reviews": [
    {"kind": "video", "title": "The Langham Boston: full hotel tour", "source": "Travel with Sam",
     "url": "https://www.youtube.com/watch?v=...", "date": "Mar 2026", "verdict": "Grand rooms, slow check-in",
     "summary": "Two or three sentences in your own words.", "rating": ""}
  ],
  "fees": ["Valet parking USD 75 a day"]
}
Each review's "kind" is "video", "article" or "review" (an overall rating, given in "rating").
The page lists up to 8 and opens each in a viewer; YouTube videos play there.

"verified" says how sure the price is, and is never assumed:
  "checked"      seen on the booking site itself (the room, the total and the terms)
  "listed"       only seen on a comparison site (Google Hotels, Trivago, Kayak); the default
  "unavailable"  the site had no rooms, or the price couldn't be confirmed
Only "checked" prices count for Cheapest. Older links with "confirmed": true still read as "checked".

"taxes" is "included", "excluded" or "unknown" (the default). Say "included" only when the site
showed the total with taxes and fees. "refundable" is true (free cancellation), false (no refund),
or left out when the terms weren't checked; the page then says "Cancellation terms not checked".

"kind" is "official" for the hotel's own site, otherwise "aggregator". "pay" is "now",
"at hotel" or "". "total" is the whole stay including taxes and fees. Set "keep_link": true
for a link the user gave you, so it is passed through exactly as it was.

"logo" picks the site's logo in the app: google, trivago, booking, expedia, hotelscom, agoda,
trip, priceline, supercom, skylark, kayak, tripadvisor, vrbo, qantas, luxuryescapes, wotif,
webjet, lastminute, hoteltonight, or hotel for the hotel's own site. Without it, the app
guesses from the site's name, and shows a lettered badge for sites it doesn't know.

Before the check, while you work out the details or wait for the user's answer:
  "status": "thinking", with a "message" saying what you're doing, or
  "status": "question", with
  "question": {"id": "hotel", "text": "Which hotel did you mean? Several in Sydney share the name.",
               "options": [{"label": "Sheraton Grand Sydney Hyde Park", "detail": "161 Elizabeth St"},
                           {"label": "Hyde Park Inn", "detail": "271 Elizabeth St"}]}
  Options can also be plain strings, such as ["Yes", "No"]. The page adds "Try again" itself.

At the end, "status": "done" with "ready": true tells the page you're still watching it for a few
minutes, so another search sent from the page reaches you (see "Another search" in SKILL.md).

While the check is running, the same tab is updated with these as well:
  "status": "checking" (or "done" at the end, which is the default)
  "message": "Reading the Langham's own rates"
  "progress": [{"label": "Google Hotels", "logo": "google", "state": "done"},
               {"label": "Trivago", "logo": "trivago", "state": "done"},
               {"label": "The Langham's site", "logo": "hotel", "state": "checking"},
               {"label": "Super.com", "logo": "supercom", "state": "waiting"}]
     (states: waiting, checking, done, blocked)
  and on an offer still being opened: "checking": true
"""

import argparse
import base64
import json
import urllib.parse
import re
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import book_link  # noqa: E402

PAGE = os.path.join(HERE, "..", "assets", "results.html")


def add_partner_links(results, settings):
    stay = results.get("stay") or {}
    ages = stay.get("children_ages") or ""
    args = types.SimpleNamespace(
        check_in=stay.get("checkin", ""), check_out=stay.get("checkout", ""),
        adults=int(stay.get("adults") or 2), children_ages=ages,
        currency=results.get("currency", ""))
    any_partner = False
    for offer in results.get("offers") or []:
        link = offer.get("link")
        offer["partner"] = False
        if not link or offer.get("keep_link"):
            continue
        made = book_link.make_link(link, args, settings)
        offer["link"] = made["url"]
        offer["partner"] = made["affiliate"]
        any_partner = any_partner or made["affiliate"]
    if any_partner:
        results["disclosure"] = settings.get("disclosure", "")
    else:
        results.pop("disclosure", None)
    return results


def page_address(settings):
    hosted = (settings.get("results_page") or "").strip()
    if hosted:
        return hosted
    return "file://" + os.path.abspath(PAGE)


def make_url(results, settings):
    payload = json.dumps(results, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    encoded = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
    return page_address(settings) + "#d=" + encoded


# A booking link should open the hotel's own page. These path patterns mean a search or list page,
# which makes the user find the hotel again (see "Booking links" in references/sites.md).
LIST_PATH = re.compile(r"searchresults|hotel-search|/search|/hotels/list|/list\b", re.I)
HOTEL_PATH = re.compile(r"hotel-detail|/hotel/|hotel-information|-h\d+/", re.I)


def list_links(results):
    """Offers whose link is a search or list page rather than the hotel's own page."""
    found = []
    for o in results.get("offers") or []:
        link = (o or {}).get("link") or ""
        path = urllib.parse.urlsplit(link).path
        if link and LIST_PATH.search(path) and not HOTEL_PATH.search(path):
            found.append(o.get("site") or link)
    return found


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("results", help="results JSON file, or - for standard input")
    args = ap.parse_args()
    raw = sys.stdin.read() if args.results == "-" else open(args.results, encoding="utf-8").read()
    try:
        results = json.loads(raw)
    except ValueError as e:
        sys.exit("Results aren't valid JSON: %s" % e)
    for key in ("hotel", "stay", "offers"):
        if key not in results:
            sys.exit('Results need a "%s" field.' % key)
    settings = book_link.load_settings()
    for site in list_links(results):
        print("Warning: the link for %s opens a list, not the hotel's own page. Replace it with the hotel's page "
              "(see \"From a list to the hotel's page\" in references/sites.md)." % site, file=sys.stderr)
    print(make_url(add_partner_links(results, settings), settings))


if __name__ == "__main__":
    main()
