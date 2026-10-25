# MyRoomSearch

![MyRoomSearch, by Londoner in Sydney](brand/myroomsearch-logo-horizontal-dark-text.png)

MyRoomSearch, by Londoner in Sydney, is a Claude plugin that finds the cheapest way to book a hotel for your dates. It compares Booking.com, Expedia, Hotels.com, Agoda, Google Hotels, Trivago and more against the hotel's own website, then checks the live totals in your own Chrome, so member rates you're signed in for are included.

Open the Claude side panel while you're looking at a hotel and ask:

> Is this the best price?

Or ask anywhere: "best price for The Langham Boston, 10–12 Dec, 2 adults". You get back:

- the cheapest confirmed total for the whole stay, including taxes and fees
- the cheapest price you can still cancel for free
- whether booking direct with the hotel is worth it, including its member rates
- the catches: smaller rooms, prices that can't be refunded, "member prices" that need a paid subscription, and listings that turn out to have no rooms

## Install in Chrome

You need a paid Claude plan (Pro, Max, Team or Enterprise). You don't need the desktop app or Claude Code.

1. Install [Claude in Chrome](https://chromewebstore.google.com/detail/fcoeoabgfenejglbffodgkkbkcdhcgfn) and sign in.
2. In Claude, open **Customize → Plugins → Add marketplace** and enter `steveRepo/myroomsearch`.
3. Install **myroomsearch**. It's then available in the Chrome side panel, and everywhere else you use Claude.

## Install in Claude Code

```
/plugin marketplace add steveRepo/myroomsearch
/plugin install myroomsearch@myroomsearch
```

This needs Claude in Chrome connected, plus Python 3 (already on macOS). In Claude Code the plugin also runs a quick price scan before the browser check.

**Optional:** a free [SerpApi](https://serpapi.com) key adds Google Hotels prices to that scan. The free plan gives 250 searches a month, and each hotel check uses one or two. To add your key:

```bash
mkdir -p ~/.config/myroomsearch && printf '%s' 'YOUR_KEY' > ~/.config/myroomsearch/serpapi_key && chmod 600 ~/.config/myroomsearch/serpapi_key
```

## What it does, and what it won't do

1. **Quick scan** (Claude Code only). A short script asks public price feeds what each booking site charges for your dates.
2. **Live check.** Claude works in a single background tab in your Chrome. It reads the price lists on Google Hotels and Trivago, then visits the hotel's own site and the two or three cheapest booking sites one at a time, reading the real totals, cancellation terms and member rates and closing each site as soon as it's read.
3. **The MyRoomSearch tab.** Results appear in one tab that works like a booking web app. It opens as soon as the check starts and shows the logo of each site as it's checked, with a spinner on the one in progress. Prices fill in as they're confirmed, without reloading. Then you can filter by free cancellation or pay at the hotel, sort by price, pick an option to see its terms, then continue to that site. Results are ranked by the total you pay for the whole stay, including tax. The results travel in the page's own link and never reach a server.

It only looks. It never books, signs in, creates accounts, or types your details. It stops at any "are you human" check instead of trying to get past it. It doesn't click Google's sponsored ads. It leaves your own tabs alone and closes its working tab when it's done, so only the MyRoomSearch tab stays open.

## How this plugin is paid for

Some booking links in the report go through our partner [Stay22](https://www.stay22.com). If you book through one, we may earn a commission at no extra cost to you. When that happens, the report says so in its last line.

Commissions never change the ranking. The cheapest confirmed price always comes first, even when it pays us nothing. That is often the hotel's own website, which we link to directly. Links you paste in yourself are never changed. Everything is open source in this repository, so you can check.

## Privacy

Nothing is sent to us. The quick scan sends only the hotel name, dates and guest count to the price feeds (SerpApi, if you add a key, and Xotelo). The live check happens in your own browser. Stay22 only sees you if you click one of its links.

## Development

```bash
python3 -m unittest discover -s tests
claude plugin validate --strict .
```

The partner ID, the disclosure text and the results page's web address are in `plugins/myroomsearch/skills/myroomsearch/settings.json`. With the ID left empty, every link stays a plain link.

The results page is `page/results.html`. After editing it, run `python3 tools/build_page.py`, which bakes the fonts and images into the copy the skill ships (`assets/results.html`) and into `docs/index.html`, the copy the website serves.

The website is https://myroomsearch.com/, a Cloudflare Worker that serves the `docs/` folder (set up in `wrangler.jsonc`, with security headers in `docs/_headers`). That address is `results_page` in `settings.json`. To publish a new build, run `npx wrangler deploy`. Search results travel after the `#` in the address, which browsers never send to the server, so the site never sees them.

The logo files are in `brand/`. To re-render them after changing `brand/logo.html`, run `python3 tools/build_logos.py`, which needs Google Chrome and Pillow.

The search page's hero photo is Palm Bay Resort in the Whitsundays, from East Coast Guide's own photos (`page/brand/hero.webp`, cropped and compressed from the original).

The site logos in the app are each site's own small icon, fetched once with `python3 tools/fetch_logos.py` and built into the page; they're shown only to identify the sites being checked.

## Licence

The code is under the MIT licence (see `LICENSE`). The MyRoomSearch name, logo and hero photo belong to Londoner in Sydney and aren't covered by it. The fonts (Fraunces and DM Sans) are under the SIL Open Font License. The site icons belong to their owners and are shown only to identify each site.
