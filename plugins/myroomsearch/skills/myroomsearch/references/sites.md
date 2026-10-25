# Site notes for the browser check

Notes marked *Checked* were tested live in Oct 2026, from Australia. Sites change their layouts, so if something here stops matching what you see, trust the page.

## Contents
- Google Hotels: the way into every other site
- Trivago: the second price list
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
4. **Open each site from here.** Click "Visit site", or "Get price" for the official site. Use the rows under "All options", not rows marked "Sponsored" or "Ad". Even an "All options" row can be a paid placement (Trivago's was), so open a site at its own address when you can. The site opens in a **new background tab** with the dates, guests and currency already set; Google opens it with its own code, so it can't be made to open in the worker tab. List your tabs to find it (for example `tabs_context_mcp`), read it, then close it before opening the next site (*Checked*). The worker tab stays on Google Hotels, so you can go straight on to the next row.

## Trivago: the second price list

*Checked.* Trivago lists deals from many booking sites for one hotel, sometimes including smaller sites or lower prices than Google shows.
1. **Open it at its own address,** in the worker tab: Trivago's site for the user's country, for example `https://www.trivago.com.au` in Australia. Don't go through Google's Trivago row, which is often a paid ad.
2. **Find the hotel.** Type the hotel's name into the Destination box and pick the hotel itself from the suggestions, not the city. *(Not yet checked.)*
3. **Set the dates with the address.** Once the hotel is open, its address contains `search=100-<hotel number>`. Open `https://www.trivago.com.au/en-AU/lm?search=100-<hotel number>;dr-YYYYMMDD-YYYYMMDD;rc-<rooms>-<adults>`. For The Langham, Boston, 14 to 15 Jan for 2 adults, that's `search=100-8508;dr-20270114-20270115;rc-1-2` (*Checked*).
4. **Read the deals.** The hotel's card shows its best deal first (site and price), with two more sites under it. Expand "More deals" for the rest. Trivago says cheaper offers can sit under "More deals", so look there before you note the cheapest.
- **Prices** are per night. Check the price display setting, and confirm totals on the booking site itself.
- **Cookie banner:** use Settings to choose necessary cookies only, not "OK".
- **Sign-in prompt:** "Sign in to save more" appears for users who aren't signed in. Close it.

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

They redirect to the user's country site. "Member Price" deals need a free One Key sign-in. If the dates don't hold, use the site's own date picker, or reach the site through Google Hotels' "Visit site" instead.

## Other aggregators

- **Agoda, Trip.com, Priceline, Tripadvisor, Kayak:** their search links need internal city IDs, so reach them through Google Hotels' "Visit site", Trivago, or their own search box.
- **Super.com** (*Checked*): its headline price matched Google's. It also shows a lower "Member Price", but that needs a **paid Super+ subscription** (free 5-day trial, then a monthly fee). Don't count that as the price. Mention it only as "lower with a paid subscription".
- **SKYLARK** (*Checked*): its headline price is per night **before tax**. Click a rate to see the stay total including tax. Booking needs a SKYLARK membership ("become a friend"), and the page doesn't show what that costs. It charges in USD.
- **Qantas Hotels and Luxury Escapes:** treat them like any other booking site, and rank them by the price paid.

## Catches to watch for

- **Stale listings.** Feed and Google prices can be hours old. A site listed at a price may have no rooms when you open it. Only report prices you saw live, or label the rest "listed, not confirmed".
- **Check the important terms yourself.** A page summary (from `find`) once said a Booking.com rate had free cancellation when it was really non-refundable. Before you report a rate's cancellation terms or total, confirm them in a screenshot or the page text.
- **Subscriptions versus free memberships.** A hotel's own member rate, Booking Genius and Expedia One Key are free. Super+ and some "VIP" deal clubs charge a fee. Keep the two apart.
- **Fees paid at the hotel.** Resort, destination, parking and pet fees are often left out of aggregator totals. The hotel's own site or its policies section usually lists them.
- **Currency.** Sites pick the currency from the user's location, and the same applies to the feed if you pass `--currency`. Keep everything in one currency.
