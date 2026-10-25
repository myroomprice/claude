#!/usr/bin/env python3
"""Turn the booking links in a finished report into partner links.

Use it only on links you found yourself while checking prices, after the
ranking is final. It never changes which offer is cheapest, and it leaves a
link alone when it can't be a partner link:
  - the site isn't one the partner network covers (for example the hotel's
    own website, Super.com or Trip.com), or
  - no partner ID is set in settings.json yet.

Covered sites go through Stay22 (https://dev.stay22.com/docs/allez), which
sends the user to the same hotel page with the same dates.

Example:
  book_link.py --check-in 2026-12-10 --check-out 2026-12-12 --adults 2 \
      --url "https://www.booking.com/hotel/us/langham-boston.html?aid=123&label=x"
"""

import argparse
import json
import os
import re
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
SETTINGS = os.path.join(HERE, "..", "settings.json")
STAY22 = "https://www.stay22.com/allez/"

# Stay22 endpoint for each covered site, matched on the end of the host name.
PROVIDERS = [
    ("booking.com", "booking"),
    ("hotels.com", "hotelscom"),
    ("hoteles.com", "hotelscom"),
    ("hoteis.com", "hotelscom"),
    ("vrbo.com", "vrbo"),
    ("stayz.com.au", "vrbo"),
    ("abritel.fr", "vrbo"),
    ("fewo-direkt.de", "vrbo"),
    ("bookabach.co.nz", "vrbo"),
    ("agoda.com", "agoda"),
]
# Expedia and Kayak use many country domains (expedia.com.au, kayak.co.uk ...).
# The brand must be the registered name, so expedia.evil.com doesn't match.
COUNTRY_ENDING = r"(?:[a-z]{2,3}|co\.[a-z]{2}|com\.[a-z]{2})"
BRAND_PROVIDERS = [
    (re.compile(r"(?:^|\.)expedia\." + COUNTRY_ENDING + "$"), "expedia"),
    (re.compile(r"(?:^|\.)kayak\." + COUNTRY_ENDING + "$"), "kayak"),
]


def load_settings():
    try:
        with open(SETTINGS) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def provider_for(host):
    host = host.lower().split(":")[0]
    for domain, name in PROVIDERS:
        if host == domain or host.endswith("." + domain):
            return name
    for pattern, name in BRAND_PROVIDERS:
        if pattern.search(host):
            return name
    return None


def clean_hotel_url(url):
    """The hotel page alone: no query string, so no one else's tracking codes."""
    p = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((p.scheme or "https", p.netloc, p.path, "", ""))


def make_link(url, args, settings):
    parts = urllib.parse.urlsplit(url)
    result = {"original": url, "url": url, "affiliate": False, "provider": None}
    if parts.scheme not in ("http", "https") or not parts.netloc:
        result["note"] = "not a web link; left unchanged"
        return result
    provider = provider_for(parts.netloc)
    if not provider:
        result["note"] = "site not covered by the partner network; left unchanged"
        return result
    aid = (settings.get("stay22_aid") or "").strip()
    if not aid:
        result["provider"] = provider
        result["note"] = "no partner ID set in settings.json; left unchanged"
        return result

    params = [
        ("aid", aid),
        ("link", clean_hotel_url(url)),
        ("checkin", args.check_in),
        ("checkout", args.check_out),
        ("adults", str(args.adults)),
    ]
    if args.children_ages:
        ages = [a.strip() for a in args.children_ages.split(",") if a.strip()]
        params += [("children", str(len(ages))), ("childrenAges", ",".join(ages))]
    if args.currency:
        params.append(("currency", args.currency.upper()))
    if settings.get("campaign"):
        params.append(("campaign", settings["campaign"]))
    result.update({
        "url": STAY22 + provider + "?" + urllib.parse.urlencode(params),
        "affiliate": True,
        "provider": provider,
    })
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", action="append", required=True, help="a booking link; repeat for several")
    ap.add_argument("--check-in", required=True, help="YYYY-MM-DD")
    ap.add_argument("--check-out", required=True, help="YYYY-MM-DD")
    ap.add_argument("--adults", type=int, default=2)
    ap.add_argument("--children-ages", default="", help="comma-separated ages, e.g. 4,9")
    ap.add_argument("--currency", default="")
    args = ap.parse_args()

    settings = load_settings()
    links = [make_link(u, args, settings) for u in args.url]
    out = {"links": links}
    if any(l["affiliate"] for l in links):
        out["disclosure"] = settings.get("disclosure", "")
    json.dump(out, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
