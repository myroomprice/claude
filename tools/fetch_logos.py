#!/usr/bin/env python3
"""Fetch the small site icons the app shows while it checks, and save them in page/brand/sites/.

Each icon is the site's own favicon, fetched once through Google's favicon service, checked to be
a real image, and saved as a 64x64 PNG. The build step then bakes them into the page, so the app
itself never loads anything from another site. Run:  python3 tools/fetch_logos.py
"""

import io
import os
import sys
import urllib.request

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "page", "brand", "sites")

# key used by the page and the skill: the site's main domain
SITES = {
    "google": "google.com",
    "booking": "booking.com",
    "expedia": "expedia.com",
    "hotelscom": "hotels.com",
    "agoda": "agoda.com",
    "trip": "trip.com",
    "priceline": "priceline.com",
    "supercom": "super.com",
    "skylark": "skylark.com",
    "kayak": "kayak.com",
    "trivago": "trivago.com",
    "tripadvisor": "tripadvisor.com",
    "vrbo": "vrbo.com",
    "qantas": "qantas.com",
    "luxuryescapes": "luxuryescapes.com",
    "wotif": "wotif.com",
    "webjet": "webjet.com.au",
    "lastminute": "lastminute.com",
    "hoteltonight": "hoteltonight.com",
}


def fetch(domain):
    url = "https://www.google.com/s2/favicons?sz=64&domain=" + domain
    req = urllib.request.Request(url, headers={"User-Agent": "MyRoomPrice logo fetcher"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = resp.read()
    img = Image.open(io.BytesIO(data))
    img.load()
    return img.convert("RGBA").resize((64, 64), Image.LANCZOS)


def main():
    os.makedirs(OUT, exist_ok=True)
    failed = []
    for key, domain in SITES.items():
        try:
            img = fetch(domain)
        except Exception as e:  # noqa: BLE001 - report every failure and carry on
            failed.append("%s (%s)" % (key, e))
            continue
        path = os.path.join(OUT, key + ".png")
        img.save(path, optimize=True)
        print("%-14s %-20s %5d bytes" % (key, domain, os.path.getsize(path)))
    if failed:
        sys.exit("Couldn't fetch: " + ", ".join(failed))


if __name__ == "__main__":
    main()
