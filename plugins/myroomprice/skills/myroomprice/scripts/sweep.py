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
import unicodedata
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

# Words that say what kind of place it is, not which one. They don't help tell hotels apart.
GENERIC = {"the", "a", "an", "and", "of", "at", "in", "on", "by", "hotel", "hotels", "resort", "resorts",
           "inn", "suites", "suite", "spa", "apartments", "apartment", "lodge", "collection", "boutique"}
# How sure a name match must be before its prices are used (see match_hotel).
MIN_SCORE = 0.7      # overall: half how much of the query the hotel covers, half how much of its name the query has
MIN_COVERAGE = 0.75  # share of the query's distinctive words found in the hotel's name or address
CLOSE_CALL = 0.15    # another hotel within this score is a real alternative, so ask


def words(text):
    text = unicodedata.normalize("NFKD", (text or "").lower().replace("&", " and "))
    text = "".join(c for c in text if not unicodedata.combining(c))
    return set(re.findall(r"[a-z0-9]+", text))


def match_score(query, name, address="", place=()):
    """How well a hotel matches what the user asked for: (score, coverage), both 0 to 1.

    coverage: the share of the query's distinctive words found in the hotel's name or address
    (so "Langham Boston" covers "The Langham" at 250 Franklin St, Boston).
    precision: the share of the hotel name's distinctive words that the query mentions
    (so "Hyde Park" doesn't fully match "Sheraton Grand Sydney Hyde Park").
    Words of the place (from --where) are left out here; in_place checks them separately.
    """
    wanted = words(query) - GENERIC - set(place)
    name_words = words(name) - GENERIC - set(place)
    if not wanted or not name_words:
        return 0.0, 0.0
    coverage = len(wanted & (name_words | words(address))) / len(wanted)
    precision = len(name_words & wanted) / len(name_words)
    return round((coverage + precision) / 2, 3), round(coverage, 3)


def in_place(where, name, address):
    """True when the place the user gave (a city, town or country) appears in the hotel's name or address,
    or when there's nothing to check it against."""
    place = words(where) - GENERIC
    known = words(name) | words(address)
    return not place or not words(address) or bool(place & known)


def match_hotel(candidates, hotel, where=""):
    """Choose the hotel the user meant from a list of {"name", "address", ...}, or decide it isn't clear.

    Returns {"confident": bool, "best": candidate or None, "score", "coverage", "reason",
    "alternatives": [candidates worth asking about]}. Prices are only used when confident.
    """
    place = words(where) - GENERIC
    scored = []
    for c in candidates:
        if c.get("type") not in (None, "hotel"):
            continue
        score, coverage = match_score(hotel, c.get("name"), c.get("address") or "", place)
        if not in_place(where, c.get("name"), c.get("address") or ""):
            score, coverage = score / 2, coverage / 2
        scored.append((score, coverage, c))
    scored.sort(key=lambda t: (-t[0], -t[1]))
    if not scored:
        return {"confident": False, "best": None, "score": 0, "coverage": 0, "alternatives": [],
                "reason": "no hotels found"}
    score, coverage, best = scored[0]
    # A rival is another hotel that also contains what the user typed, and scores close or covers as much.
    rivals = [c for sc, cov, c in scored[1:] if cov >= MIN_COVERAGE and (sc >= score - CLOSE_CALL or cov >= coverage)]
    result = {"best": best, "score": score, "coverage": coverage,
              "alternatives": [c for sc, cov, c in scored[:6] if sc >= 0.4]}
    if score < MIN_SCORE or coverage < MIN_COVERAGE:
        result.update(confident=False, reason="no hotel matches the name closely enough")
    elif rivals:
        result.update(confident=False, reason="several hotels match the name about equally well")
    else:
        result.update(confident=True, reason="")
    return result


def candidate(p):
    """The parts of a Google Hotels property that matter for choosing one."""
    return {"name": p.get("name"), "address": p.get("address") or "", "type": p.get("type"),
            "property_token": p.get("property_token"), "rating": p.get("overall_rating"),
            "hotel_class": p.get("hotel_class") or p.get("extracted_hotel_class")}


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


class Unsure(Exception):
    """The hotel can't be identified for sure, so its prices mustn't be used."""


def public_match(match):
    """The match result as reported in the output."""
    def show(c):
        return {k: v for k, v in c.items() if k != "type" and v not in (None, "")}
    return {"confident": match["confident"], "reason": match["reason"], "score": match["score"],
            "chosen": show(match["best"]) if match["confident"] and match["best"] else None,
            "candidates": [show(c) for c in match["alternatives"]] if not match["confident"] else []}


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
    token, where = getattr(args, "property_token", ""), getattr(args, "where", "")
    if token:
        # The user, or an earlier question on the page, already picked the exact property.
        params["property_token"] = args.property_token
    try:
        data = get_json(base + urllib.parse.urlencode(params))
        searches = 1
        if data.get("error"):
            raise RuntimeError(data["error"])
        if not (data.get("featured_prices") or data.get("prices")) and data.get("properties"):
            # A list of hotels came back: pick the one meant, or stop and ask.
            match = match_hotel([candidate(p) for p in data["properties"]], args.hotel, where)
            result["hotel_match"] = public_match(match)
            if not match["confident"] or not match["best"].get("property_token"):
                raise Unsure(match["reason"])
            params["property_token"] = match["best"]["property_token"]
            data = get_json(base + urllib.parse.urlencode(params))
            searches += 1
            if data.get("error"):
                raise RuntimeError(data["error"])
        if not token:
            # Google can also jump straight to one hotel. Check it's the one asked for.
            match = match_hotel([{"name": data.get("name"), "address": data.get("address") or "",
                                  "property_token": data.get("property_token")}], args.hotel, where)
            result["hotel_match"] = public_match(match)
            if not match["confident"]:
                raise Unsure("Google Hotels found " + str(data.get("name")) + ", which may not be the hotel asked for")
    except Unsure as e:
        result["skipped"].append({"feed": "google_hotels", "reason": "hotel not identified for sure: " + str(e) +
                                  ". Ask the user which hotel they mean (see hotel_match), then run again with --property-token."})
        return
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
    match = result.get("hotel_match") or {}
    if match.get("candidates"):
        print("\nWhich hotel? Candidates:")
        for c in match["candidates"]:
            print("  - {}{}  (property_token {})".format(c.get("name"), " | " + c["address"] if c.get("address") else "",
                                                       c.get("property_token", "?")))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hotel", required=True, help='hotel name, e.g. "The Langham Boston"')
    ap.add_argument("--where", default="", help='city, town or country, e.g. "Boston, USA"; checked against the hotel found')
    ap.add_argument("--property-token", default="", help="Google Hotels property_token of the exact hotel, e.g. from hotel_match.candidates")
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
        "query": {"hotel": args.hotel, "where": args.where, "check_in": args.check_in, "check_out": args.check_out,
                  "adults": args.adults, "rooms": args.rooms, "children_ages": args.children_ages,
                  "currency": args.currency},
        "nights": nights,
        "checked_at": dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z"),
        "hotel": None,
        "hotel_match": None,
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
