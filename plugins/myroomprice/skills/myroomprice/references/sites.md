# Site notes for the browser check

Notes marked *Checked* were tested live in Oct 2026, from Australia. Sites change their layouts, so if something here stops matching what you see, trust the page.

## Contents
- Google Hotels: the way into every other site
- Trivago: the second price list
- Kayak: the third price list
- Reaching each site in the worker tab
- Booking links: the hotel's own page, with the dates
- YouTube and blogs: reviews
- The hotel's own booking page
- Booking.com
- Expedia and Hotels.com
- Other aggregators
- Catches to watch for

## Google Hotels: the way into every other site

*Checked.* This is the quickest route to every site with the right dates already filled in.

1. **Open the hotel.** Go to `https://www.google.com/travel/search?q=<hotel name and city>&hl=en`. A specific name opens that hotel's panel directly.
2. **Set the dates by hand.** Date parameters in the URL are ignored, and putting dates in the search words turns it into a city search.
   - Click the Check-in box. A two-month calendar opens. Use the arrows to reach the right month, then click the check-in day and then the check-out day.
   - Read the day numbers carefully: rows are weeks, so 10 Dec sits in the 6-12 row, not the 13-19 row.
   - Zoom into the two date boxes and confirm the dates before you click Done. Typing into the date box does not work reliably.
3. **Read the prices.** Open the **Prices** tab.
   - "Featured options" lists the hotel's own site (with an "Official Site" badge) and its room rates. "All options" below lists every booking site.
   - The dropdown above the list says whether prices are per night or total, and with or without tax. "Nightly total" means per night *including* tax.
   - Text like "Get a lower price with free enrolment" next to the official site means a member rate exists.
   - Notes such as "Free cancellation until Dec 9" appear under a site's name.
   - `get_page_text` returns nothing on this page, so read it from screenshots or with `find`.
4. **Don't click through to the sites from here.** "Visit site" and "Get price" always open a new tab, which Google opens with its own code, so it can't be kept in the worker tab (*Checked*). Even an "All options" row can be a paid placement (Trivago's was). Read each site's price from the list, then go to the sites yourself in the worker tab (see "Reaching each site"). The only exception is the hotel's own booking page; see "Tabs" in SKILL.md.
5. **The hotel's website** is under the Overview tab ("Website"), or in the "Official site" row. Note its address for later.

## Trivago: the second price list

*Checked.* Trivago lists deals from many booking sites for one hotel, sometimes including smaller sites or lower prices than Google shows.
1. **Open it at its own address,** in the worker tab: Trivago's site for the user's country, for example `https://www.trivago.com.au` in Australia. Don't go through Google's Trivago row, which is often a paid ad.
2. **Find the hotel.** Type the hotel's name into the Destination box and pick the hotel itself from the suggestions, not the city. *(Not yet checked.)*
3. **Set the dates with the address.** Once the hotel is open, its address contains `search=100-<hotel number>`. Open `https://www.trivago.com.au/en-AU/lm?search=100-<hotel number>;dr-YYYYMMDD-YYYYMMDD;rc-<rooms>-<adults>`. For The Langham, Boston, 14 to 15 Jan for 2 adults, that's `search=100-8508;dr-20270114-20270115;rc-1-2` (*Checked*).
4. **Read the deals.** The hotel's card shows its best deal first (site and price), with two more sites under it. Expand "More deals" for the rest. Trivago says cheaper offers can sit under "More deals", so look there before you note the cheapest. Don't click a deal: each opens a new tab.
- **Prices** are per night. Check the price display setting, and confirm totals on the booking site itself.
- **Cookie banner:** use Settings to choose necessary cookies only, not "OK".
- **Sign-in prompt:** "Sign in to save more" appears for users who aren't signed in. Close it.

## Kayak: the third price list

*Checked (no bot check in testing).* Kayak lists deals from many booking sites, like Trivago.
1. **Open its hotels page** for the user's country in the worker tab, for example `https://www.kayak.com.au/hotels`. Don't guess a city address: the city code in Kayak's links is internal, and a wrong one opens a different town.
2. **Search by the hotel's name.** Click the destination box, type the hotel's name, and pick the hotel itself (bed icon) from the suggestions. The dates and guests carry over; check them in the box below before you click Search. Leave "Compare vs KAYAK" boxes unticked: they open other sites in new tabs.
3. **Read the result, without clicking "View Deal"** (it opens a new tab). The hotel's own address then looks like `/hotels/Sheraton-Grand-Sydney-Hyde-Park,Sydney,New-South-Wales,Australia-p24040-h11749/2026-11-20/2026-11-22/2adults`, with the hotel first in the list. Its price is the **total for the stay including estimated taxes** ("Total includes estimated local taxes & fees payable on check out"), with the number of sites under it. "View Deal" lists each site. Kayak also shows the hotel's rating and review count.
- **Order isn't a guide:** Kayak says payments affect its ranking, so read the prices, not the order.
- **Bot checks:** if Kayak shows a "please confirm you're a human" page, stop and list Kayak under "couldn't check".
- **Cookie banner:** choose reject, or necessary only.

## Reaching each site in the worker tab

**Search each site for the hotel yourself, and confirm on that site's own hotel page.** Never take a site's price or link from somewhere else (Google Hotels, Trivago, Kayak or a results list): those only tell you which sites to check. On each site:
1. Search the site for the hotel, in the worker tab, with the dates (the addresses below put them in for you).
2. Find the hotel in the results and read the address of its own page from the link on its name (see "From a list to the hotel's page"). Don't click it; on several sites that opens a new tab.
3. Go to that hotel page in the worker tab, with the dates added (see "Booking links").
4. Read the room, the total with taxes and fees, and the cancellation terms there, on the hotel's page, with the page reader (`scripts/read_offers.js`; see "Reading a hotel page" in SKILL.md). *Checked* on Booking.com, Agoda, Expedia and Trip.com hotel pages: Agoda shows prices per night (the reader marks them "per night"), the others show the total for the stay.
5. Use that page, with the dates, as the offer's `link`.

How to search each site:
- **Booking.com** (*Checked*): `https://www.booking.com/searchresults.html?ss=<hotel+name+and+city>&checkin=YYYY-MM-DD&checkout=YYYY-MM-DD&group_adults=2&no_rooms=1&group_children=0`. The hotel is usually first in the list; take its page address from its name and go to it.
- **Expedia, Hotels.com and Wotif** (*Not yet checked*): `https://www.expedia.com.au/Hotel-Search?destination=<hotel name>&startDate=YYYY-MM-DD&endDate=YYYY-MM-DD&adults=2&rooms=1` (and the same path on hotels.com or wotif.com). If the dates don't hold, use the site's own date picker. Take the hotel's page address from its name in the list and go to it.
- **Agoda and Trip.com:** open the home page, type the hotel's name into the search box, pick the hotel from the suggestions, and set the dates. If that lands on a list, take the hotel's page address from its name and go to it.
- **Kayak** (*Checked*): see "Kayak" above.
- **The hotel's own site:** search for the hotel's official website (or use the address Google Hotels shows for it), go to it, and use its own "Book" or "Check availability" box, so the price comes from the hotel's own booking page. If its booking page only opens through Google's "Get price" button, use that, last (see "Tabs" in SKILL.md).
- **A link the user pasted:** open it directly; it's usually the quickest page of all.

## Booking links: the hotel's own page, with the dates

Each offer's `link` must open **that hotel's own page on that site, with the dates and guests filled in**, never a search-results page. A search link makes the user find the hotel again, and in testing a Trip.com search link did exactly that.

Your browser tools can hide everything after the `?` in an address, so don't rely on copying the address bar. Build the link instead: take the hotel's page address (the part before `?`, which you can see) and add the dates in that site's own format. All of these were *Checked* for The Sheraton Grand Sydney Hyde Park, 20 to 22 Nov 2026, 2 adults; each opened the hotel's page with those dates set.

| Site | Hotel page with dates |
|---|---|
| Booking.com | `https://www.booking.com/hotel/au/sheraton-on-the-park-sydney.en-gb.html?checkin=2026-11-20&checkout=2026-11-22&group_adults=2&no_rooms=1&group_children=0` |
| Agoda | `https://www.agoda.com/sheraton-grand-sydney-hyde-park/hotel/sydney-au.html?checkIn=2026-11-20&los=2&adults=2&rooms=1&children=0` (`los` is the number of nights) |
| Expedia (and Wotif) | `https://www.expedia.com.au/Sydney-Hotels-Sheraton-Grand-Sydney-Hyde-Park.h4807.Hotel-Information?chkin=2026-11-20&chkout=2026-11-22&rm1=a2` (`rm1=a2` is one room, 2 adults; add `:c7` per child aged 7) |
| Trip.com | `https://au.trip.com/hotels/sydney-hotel-detail-826040/sheraton-grand-sydney-hyde-park/?checkIn=2026-11-20&checkOut=2026-11-22&adult=2&children=0&crn=1` |
| Kayak | the hotel's address from "Kayak" above, with the dates in the path |
| The hotel's own site | the booking page you read the price on; if its dates are hidden after the `?`, use the hotel's booking page address and say the user may need to re-enter the dates |

How to find the hotel's page address on each site: open the hotel from the site's own search (in the worker tab), then read the address up to the `?`. Booking.com's is `/hotel/<country>/<name>.html`, Agoda's `/<name>/hotel/<city>.html`, Expedia's ends `.h<number>.Hotel-Information`, and Trip.com's is `/hotels/<city>-hotel-detail-<number>/<name>/`. If you only have a search page, don't save it as the link: open the hotel from the results first.

## From a list to the hotel's page

Search pages list hotels; each hotel's name is a link to its own page. **Don't click it** (on Booking.com and Expedia it opens a new tab). Read its address instead: find the link on the hotel's name (for example with a find for "<hotel name> link", or the page's accessibility tree) and take the address up to the `?`. That's the hotel's page; add the dates as in "Booking links" above. What it looks like on each site:
- Booking.com: `https://www.booking.com/hotel/au/sheraton-on-the-park-sydney.html`
- Expedia: `https://www.expedia.com.au/Sydney-Hotels-Sheraton-Grand-Sydney-Hyde-Park.h4807.Hotel-Information`
- Agoda: `https://www.agoda.com/sheraton-grand-sydney-hyde-park/hotel/sydney-au.html`
- Trip.com: `https://au.trip.com/hotels/sydney-hotel-detail-826040/sheraton-grand-sydney-hyde-park/`

If you can't find the hotel's own address, say so in the offer's `notes` ("link opens a list"), rather than passing a list off as the hotel.

## YouTube and blogs: reviews

*Not yet checked.*
- **YouTube search:** `https://www.youtube.com/results?search_query=the+langham+boston+review`. Read titles, channels and upload dates from the results; open a video only if you need to confirm it's about this hotel. Use the video's `watch?v=` address as its link.
- **Blogs:** a Google search for the hotel's name and "review" finds travel blogs and newspaper reviews. Prefer recent ones and independent writers over the hotel's own pages or booking sites.
- **Ratings:** Google Hotels' Reviews tab, or Tripadvisor, shows an overall rating and count.

## The hotel's own booking page

*Checked on The Langham's booking page; most hotel booking pages work the same way.*
- **Taxes.** Room prices are usually shown per night **before tax** ("Excluding Taxes and Fees"). Look for a "Price with Taxes & Fees" switch, or open the room to find the total. US city taxes and fees are often 15% or more.
- **Rate options.** Clicking a room's SELECT button only shows its rate options (nothing is booked). That list is where you find:
  - **Advance purchase:** cheaper, but prepaid and non-refundable.
  - **Flexible rate:** free cancellation until a deadline.
  - **Member rates:** these come with a "sign up" prompt. Joining the hotel's own member program is free, so count the member rate as reachable, and say it needs a free sign-up.
- **Wrong switch.** There may be a "Points Redemption" switch right next to the tax switch. If prices suddenly show in points, you've clicked the wrong one, so switch it back off.
- **Room sizes.** The cheapest room type on the hotel's own site may be bigger or smaller than the cheapest room on an aggregator. Note the room name and size.

## Booking.com

*Checked.* Link pattern that keeps the dates:
`https://www.booking.com/searchresults.html?ss=<hotel+name>&checkin=YYYY-MM-DD&checkout=YYYY-MM-DD&group_adults=2&no_rooms=1&group_children=0`
- **Genius pop-up.** A "Sign in, save money" pop-up appears for users who aren't signed in. Close it with the X and don't sign in. If the user is signed in, Genius prices show up on their own.
- **Taxes.** Whether prices include tax depends on the user's country. Read the small line under the price ("Includes taxes and charges" or "+ AUD x taxes and charges").
- **Unavailable dates.** "Unavailable on our site for your selected dates" means Booking.com has no rooms, even if Google Hotels still lists it. Record it as unavailable, not as a price.

## Expedia and Hotels.com

*Not yet checked.* These link patterns are commonly used:
- `https://www.expedia.com/Hotel-Search?destination=<hotel name>&startDate=YYYY-MM-DD&endDate=YYYY-MM-DD&adults=2&rooms=1`
- `https://www.hotels.com/Hotel-Search?destination=<hotel name>&startDate=YYYY-MM-DD&endDate=YYYY-MM-DD&adults=2`

They redirect to the user's country site. "Member Price" deals need a free One Key sign-in. If the dates don't hold, use the site's own date picker.

## Other aggregators

- **Agoda, Trip.com, Priceline, Tripadvisor:** their search links need internal city IDs, so use their own search box (see "Reaching each site").
- **Super.com** (*Checked*): its headline price matched Google's. It also shows a lower "Member Price", but that needs a **paid Super+ subscription** (free 5-day trial, then a monthly fee). Don't count that as the price. Mention it only as "lower with a paid subscription".
- **SKYLARK** (*Checked*): its headline price is per night **before tax**. Click a rate to see the stay total including tax. Booking needs a SKYLARK membership ("become a friend"), and the page doesn't show what that costs. It charges in USD.
- **Qantas Hotels and Luxury Escapes:** treat them like any other booking site, and rank them by the price paid.

## Catches to watch for

- **Stale listings.** Feed and Google prices can be hours old. A site listed at a price may have no rooms when you open it. Only report prices you saw live, or label the rest "listed, not confirmed".
- **Check the important terms yourself.** A page summary (from `find`) once said a Booking.com rate had free cancellation when it was really non-refundable. Take a rate's total and cancellation terms from the page reader, which copies the page's own words, or from the page text, never from a summary.
- **Subscriptions versus free memberships.** A hotel's own member rate, Booking Genius and Expedia One Key are free. Super+ and some "VIP" deal clubs charge a fee. Keep the two apart.
- **Fees paid at the hotel.** Resort, destination, parking and pet fees are often left out of aggregator totals. The hotel's own site or its policies section usually lists them.
- **Currency.** Sites pick the currency from the user's location, and the same applies to the feed if you pass `--currency`. Keep everything in one currency.
