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
     "refundable": true, "cancel_until": "", "pay": "now", "member": "",
     "includes": ["breakfast for two"], "notes": "", "confirmed": true,
     "this_page": false, "link": "https://...", "keep_link": false}
  ],
  "couldnt_check": [{"site": "Agoda", "why": "CAPTCHA"}],
  "fees": ["Valet parking USD 75 a day"]
}
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
    print(make_url(add_partner_links(results, settings), settings))


if __name__ == "__main__":
    main()
