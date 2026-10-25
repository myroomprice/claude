#!/usr/bin/env python3
"""Quick price sweep for one hotel and one set of dates.

Asks two price feeds and prints every offer found, cheapest first:
  - Google Hotels via SerpApi (needs a key; lists most booking sites plus the
    hotel's own site, flagged "official", with totals including tax)
  - Xotelo (free, no key; TripAdvisor partner rates, per night before tax)

Either source can be missing; the script reports what it skipped and why.
Standard library only, so it runs on the stock macOS Python 3.9.

Examples:
  sweep.py --hotel "The Langham Boston" --check-in 2026-12-10 --check-out 2026-12-12
  sweep.py --hotel "The Langham Boston" --check-in 2026-12-10 --check-out 2026-12-12 \
      --tripadvisor-url "https://www.tripadvisor.com/Hotel_Review-g60745-d89575-Reviews-..." --json
"""

import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

CONFIG_DIR = os.path.expanduser("~/.config/myroomprice")
# Before the rename the key lived here; still read it so an existing setup keeps working.
OLD_CONFIG_DIR = os.path.expanduser("~/.config/myroomsearch")
KEY_FILE = os.path.join(CONFIG_DIR, "serpapi_key")
USER_AGENT = "MyRoomPrice/1.0 (personal price comparison)"
TIMEOUT = 40


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def serpapi_key():
    key = os.environ.get("SERPAPI_KEY", "").strip()
    if key:
        return key
    for path in (KEY_FILE, os.path.join(OLD_CONFIG_DIR, "serpapi_key")):
        if os.path.exists(path):
            with open(path) as f:
                return f.read().strip()
    return ""


# ---------- Google Hotels via SerpApi ----------

def words(text):
    return set(re.findall(r"[a-z0-9]+", (text or "").lower()))


def best_match(properties, hotel):
    """Pick the property whose name shares the most words with the query."""
    wanted = words(hotel)
    best, best_score = None, -1.0
    for p in properties:
        if p.get("type") not in (None, "hotel"):
            continue
        have = words(p.get("name"))
        if not have:
            continue
        score = len(wanted & have) / len(wanted | have)
        if score > best_score:
            best, best_score = p, score
    return best


def num(rate, *keys):
    """First numeric value found under the given keys of a SerpApi rate object."""
    if not isinstance(rate, dict):
        return None
    for k in keys:
        v = rate.get(k)
        if isinstance(v, (int, float)):
            return float(v)
    return None


def serpapi_offer(entry, nights, featured):
    total_rate = entry.get("total_rate") or {}
    night_rate = entry.get("rate_per_night") or {}
    total_after = num(total_rate, "extracted_after_taxes_fees")
    total_before = num(total_rate, "extracted_before_taxes_fees")
    total_any = num(total_rate, "extracted_lowest", "extracted_display_price")
    night_after = num(night_rate, "extracted_after_taxes_fees")
    night_before = num(night_rate, "extracted_before_taxes_fees")
    night_any = num(night_rate, "extracted_lowest", "extracted_display_price")

    total = total_after
    if total is None and night_after is not None:
        total = night_after * nights
    if total is None:
        total = total_any if total_any is not None else (night_any * nights if night_any else None)

    offer = {
        "source": entry.get("source") or "unknown",
        "official": bool(entry.get("official")),
        "total": round(total, 2) if total is not None else None,
        "total_includes_tax": total_after is not None or night_after is not None,
        "total_before_tax": round(total_before, 2) if total_before is not None
        else (round(night_before * nights, 2) if night_before is not None else None),
        "per_night": round(total / nights, 2) if total is not None else None,
        "free_cancellation": entry.get("free_cancellation"),
        "free_cancellation_until": " ".join(
            x for x in (entry.get("free_cancellation_until_date"),
                        entry.get("free_cancellation_until_time")) if x) or None,
        "room": None,
        "link": entry.get("link"),
        "feed": "google_hotels",
    }
    if entry.get("discount_remarks"):
        offer["notes"] = "; ".join(entry["discount_remarks"])

    # Featured offers list room-level rates: pull out the cheapest room name and
    # the cheapest rate you can cancel for free.
    if featured:
        cheapest_room, cheapest_room_total = None, None
        refundable_total = None
        for room in entry.get("rooms") or []:
            for r in room.get("rates") or [room]:
                rt = num(r.get("total_rate") or {}, "extracted_after_taxes_fees",
                         "extracted_lowest", "extracted_display_price")
                if rt is None:
                    continue
                if cheapest_room_total is None or rt < cheapest_room_total:
                    cheapest_room, cheapest_room_total = room.get("name"), rt
                if r.get("free_cancellation") and (refundable_total is None or rt < refundable_total):
                    refundable_total = rt
        if cheapest_room:
            offer["room"] = cheapest_room
        if refundable_total is not None:
            offer["cheapest_refundable_total"] = round(refundable_total, 2)
    return offer


def sweep_serpapi(args, nights, result):
    key = serpapi_key()
    if not key:
        result["skipped"].append({"feed": "google_hotels", "reason":
                                  "no SerpApi key (set SERPAPI_KEY or save it to " + KEY_FILE + ")"})
        return
    params = {
        "engine": "google_hotels",
        "q": args.hotel,
        "check_in_date": args.check_in,
        "check_out_date": args.check_out,
        "adults": args.adults,
        "currency": args.currency,
        "gl": args.gl,
        "hl": "en",
        "api_key": key,
    }
    if args.children_ages:
        params["children"] = len(args.children_ages.split(","))
        params["children_ages"] = args.children_ages
    base = "https://serpapi.com/search.json?"
    try:
        data = get_json(base + urllib.parse.urlencode(params))
        searches = 1
        if data.get("error"):
            raise RuntimeError(data["error"])
        # A specific hotel name usually lands straight on the property details.
        # A vaguer one returns a list, so pick the closest name and ask again.
        if not (data.get("featured_prices") or data.get("prices")) and data.get("properties"):
            match = best_match(data["properties"], args.hotel)
            if not match or not match.get("property_token"):
                raise RuntimeError("no matching hotel in Google Hotels results")
            params["property_token"] = match["property_token"]
            data = get_json(base + urllib.parse.urlencode(params))
            searches += 1
            if data.get("error"):
                raise RuntimeError(data["error"])
    except (urllib.error.URLError, RuntimeError, ValueError) as e:
        result["skipped"].append({"feed": "google_hotels", "reason": str(e)})
        return

    result["feeds_used"].append({"feed": "google_hotels", "serpapi_searches_used": searches})
    result["hotel"] = {
        "name": data.get("name"),
        "address": data.get("address"),
        "phone": data.get("phone"),
        "website": data.get("link"),
        "hotel_class": data.get("hotel_class"),
    }
    seen = set()
    for featured, entries in ((True, data.get("featured_prices") or []), (False, data.get("prices") or [])):
        for entry in entries:
            name = (entry.get("source") or "").lower()
            if name in seen:
                continue
            seen.add(name)
            result["offers"].append(serpapi_offer(entry, nights, featured))


# ---------- Xotelo (TripAdvisor partner rates) ----------

def tripadvisor_key(args):
    if args.tripadvisor_key:
        return args.tripadvisor_key
    if args.tripadvisor_url:
        m = re.search(r"-(g\d+-d\d+)-", args.tripadvisor_url)
        if m:
            return m.group(1)
    return None


def sweep_xotelo(args, nights, result):
    key = tripadvisor_key(args)
    if not key:
        result["skipped"].append({"feed": "xotelo", "reason":
                                  "no TripAdvisor ID (pass --tripadvisor-url with the hotel's TripAdvisor page)"})
        return
    params = {
        "hotel_key": key,
        "chk_in": args.check_in,
        "chk_out": args.check_out,
        "adults": args.adults,
        "rooms": args.rooms,
        "currency": args.currency,
    }
    if args.children_ages:
        params["age_of_children"] = args.children_ages
    try:
        data = get_json("https://data.xotelo.com/api/rates?" + urllib.parse.urlencode(params))
    except (urllib.error.URLError, ValueError) as e:
        result["skipped"].append({"feed": "xotelo", "reason": str(e)})
        return
    if data.get("error"):
        err = data["error"]
        result["skipped"].append({"feed": "xotelo", "reason": err.get("message", str(err))
                                  if isinstance(err, dict) else str(err)})
        return
    rates = ((data.get("result") or {}).get("rates")) or []
    result["feeds_used"].append({"feed": "xotelo", "tripadvisor_id": key, "offers": len(rates)})
    for r in rates:
        # Xotelo's docs call "rate" a nightly price, but it is the total for the
        # stay before tax (tested Oct 2026: 1 night $506, 2 nights $936, 4 nights $1,560).
        stay = r.get("rate")
        if not isinstance(stay, (int, float)):
            continue
        tax = r.get("tax") if isinstance(r.get("tax"), (int, float)) else None
        name = r.get("name") or r.get("code") or "unknown"
        total = stay + (tax or 0)
        result["offers"].append({
            "source": name,
            "official": "official" in name.lower(),
            "total": round(total, 2),
            "total_includes_tax": tax is not None,
            "total_before_tax": round(stay, 2),
            "per_night": round(total / nights, 2),
            "free_cancellation": None,
            "room": None,
            "link": None,
            "feed": "xotelo",
        })


# ---------- output ----------

def sort_key(o):
    # Totals that include tax come first, then pre-tax totals, then unknowns,
    # so a pre-tax number never looks cheaper than an all-in one.
    return (o["total"] is None, not o["total_includes_tax"], o["total"] or 0)


def print_table(result):
    q = result["query"]
    print("Hotel:   " + ((result.get("hotel") or {}).get("name") or q["hotel"] + " (not confirmed)"))
    print("Dates:   {} to {} ({} night{}), {} adult{}, {}".format(
        q["check_in"], q["check_out"], result["nights"], "" if result["nights"] == 1 else "s",
        q["adults"], "" if q["adults"] == 1 else "s", q["currency"]))
    print("Checked: " + result["checked_at"])
    print()
    if not result["offers"]:
        print("No offers found.")
    else:
        print("{:<36} {:>10} {:>9} {:>10}  {:<9} {}".format(
            "Where", "Total", "Tax incl", "Per night", "Cancel", "Room / notes"))
        for o in result["offers"]:
            name = o["source"] + (" (official)" if o["official"] else "")
            total = "{:,.0f}".format(o["total"]) if o["total"] is not None else "?"
            pn = "{:,.0f}".format(o["per_night"]) if o["per_night"] is not None else "?"
            cancel = {True: "free", False: "no", None: "?"}[o.get("free_cancellation")]
            extra = o.get("room") or ""
            if o.get("cheapest_refundable_total") is not None:
                extra += (" | " if extra else "") + "refundable from {:,.0f}".format(o["cheapest_refundable_total"])
            if o.get("notes"):
                extra += (" | " if extra else "") + o["notes"]
            print("{:<36} {:>10} {:>9} {:>10}  {:<9} {}".format(
                name[:36], total, "yes" if o["total_includes_tax"] else "no", pn, cancel, extra))
    for s in result["skipped"]:
        print("\nSkipped {}: {}".format(s["feed"], s["reason"]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hotel", required=True, help='hotel name with city, e.g. "The Langham Boston"')
    ap.add_argument("--check-in", required=True, help="YYYY-MM-DD")
    ap.add_argument("--check-out", required=True, help="YYYY-MM-DD")
    ap.add_argument("--adults", type=int, default=2)
    ap.add_argument("--rooms", type=int, default=1)
    ap.add_argument("--children-ages", default="", help="comma-separated ages, e.g. 4,9")
    ap.add_argument("--currency", default="USD")
    ap.add_argument("--gl", default="us", help="country Google searches from (affects tax display)")
    ap.add_argument("--tripadvisor-url", help="the hotel's TripAdvisor page (for Xotelo)")
    ap.add_argument("--tripadvisor-key", help="TripAdvisor ID like g60745-d89575 (for Xotelo)")
    ap.add_argument("--json", action="store_true", help="print JSON instead of a table")
    args = ap.parse_args()

    try:
        d_in = dt.date.fromisoformat(args.check_in)
        d_out = dt.date.fromisoformat(args.check_out)
    except ValueError:
        sys.exit("Dates must be YYYY-MM-DD.")
    nights = (d_out - d_in).days
    if nights < 1:
        sys.exit("Check-out must be after check-in.")
    if d_in < dt.date.today():
        sys.exit("Check-in is in the past.")

    result = {
        "query": {"hotel": args.hotel, "check_in": args.check_in, "check_out": args.check_out,
                  "adults": args.adults, "rooms": args.rooms, "children_ages": args.children_ages,
                  "currency": args.currency},
        "nights": nights,
        "checked_at": dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z"),
        "hotel": None,
        "feeds_used": [],
        "skipped": [],
        "offers": [],
    }
    sweep_serpapi(args, nights, result)
    sweep_xotelo(args, nights, result)
    result["offers"].sort(key=sort_key)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print_table(result)


if __name__ == "__main__":
    main()
