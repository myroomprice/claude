// MyRoomPrice page reader. Run this whole file in a hotel's page on a booking site with the browser's
// JavaScript tool; it returns one short JSON string (it takes a few seconds while the rooms load):
//   hotel   - the page's main heading: check it's the right hotel
//   offers  - up to 4 rates, cheapest first, each [price, room, cancellation, taxes, payment],
//             every field copied word for word from the page ("" when the page doesn't say, and
//             left off the end when empty). "same" means the same as in "all".
//             The price ends in "per night" or "total" when the page says which it is.
//   all     - terms every rate shares, given once: {cancellation, taxes, payment}
//   flags   - short words for what the page shows: sold-out (no rates at all), sign-in, member,
//             captcha, no-rooms (no room list found, so the prices may be from elsewhere on the page)
// The text is exact, so it stands in for a screenshot. It scrolls the page to the rooms, because
// many sites only load them then, and it clicks nothing. The answer is kept short so that several
// sites can be read in one batch without the browser tool cutting it off.
await (async () => {
  const clean = (s) => (s || "").replace(/\s+/g, " ").trim();
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    const st = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && st.visibility !== "hidden" && st.display !== "none";
  };
  // Parts of a page whose prices aren't this hotel's rooms: menus, other hotels, tours, add-ons.
  const skip = (el) => el.closest("script, style, noscript, svg, header, footer, nav, select, option, [aria-hidden='true'], " +
    "[data-element-name*='cross-sell' i], [class*='cross-sell' i], [class*='crosssell' i], [class*='recommend' i], " +
    "[data-testid*='recommend' i], [class*='similar' i], [class*='nearby' i], [data-stid*='similar' i]");
  const PRICE = /(?:A\$|AU\$|NZ\$|US\$|S\$|HK\$|C\$|\$|£|€|¥|₹|฿|₫|RM|Rp|AUD|USD|NZD|EUR|GBP|SGD|THB|JPY|IDR|VND|MYR|PHP)\s?\d[\d,.]*\d|\d[\d,.]*\d\s?(?:AUD|USD|NZD|EUR|GBP|SGD|THB|JPY|IDR|VND|MYR|PHP|€)/;
  // A room type's name says what kind of room it is; a bed line ("1 extra-large double bed") doesn't count.
  const ROOM = /\b(room|suite|studio|villa|bungalow|apartment|chalet|cabin|loft|penthouse)\b/i;
  // ...and an amenity, a heading that only mentions rooms, or a guest's review doesn't either.
  const NOT_ROOM = /\b(dressing|bath|living|shower|powder|dining|sitting|laundry|fitness|meeting|board|smoking)\s?room\b|\broom (service|comfort|size|facilities|amenities|only|info|details|highlights)\b|^(?:select|choose|see|show|view|compare|filter|book|reserve)\b|\b(?:options|types|sold out|left)\b|\b(?:great|comfy|clean|friendly|staff|lovely|nice|excellent|amazing|perfect|good|stayed|value|price|recommend)\b/i;
  // Cancellation terms, ending at their deadline ("before 20 November 2026", "before 23:59, Nov 19").
  const DATE = String.raw`(?:\d{1,2}\s[A-Za-z]{3,9}\s\d{4}|[A-Za-z]{3,9}\s\d{1,2},?\s\d{4}|\d{1,2}:\d{2}(?:\s?[ap]m)?,?\s(?:on\s)?(?:[A-Za-z]{3,9}\s\d{1,2}|\d{1,2}\s[A-Za-z]{3,9})|[A-Za-z]{3,9}\s\d{1,2}\b|\d{1,2}\s[A-Za-z]{3,9}\b)`;
  const CANCEL = new RegExp(String.raw`free cancell?ation\s+(?:before|until|till|up to|by)\s+(?:[^•|·]{0,12}?\s)?` + DATE +
    String.raw`|fully refundable\s+(?:before|until|till|by)\s+(?:[^•|·]{0,12}?\s)?` + DATE +
    String.raw`|free cancell?ation(?:[^•|·]{0,45}?\d{4})?|cancel for free[^•|·]{0,30}?\d{4}|fully refundable|partially refundable|non-?refundable|no refunds?`, "i");
  const value = (p) => parseFloat(p.replace(/[^\d.]/g, "")) || 0;
  // "&" is written as "and": next to "=" the browser tool takes an answer for an address and hides it.
  const pick = (text, re) => { const m = text.match(re); return m ? clean(m[0]).replace(/\s*&\s*/g, " and ").slice(0, 50) : ""; };
  const hasPrice = (el) => el && PRICE.test(el.innerText || "");

  // Find the room list: the sites' own markers first, then a "Rooms"/"Availability" heading.
  const ROOM_LISTS = "#hprt-table, #available_rooms, #availability, [data-selenium='roomgrid'], [data-element-name='roomgrid'], " +
    "[data-stid='section-room-list'], [data-stid*='room-list' i], #Offers, [data-testid*='room-list' i], " +
    "[class*='roomlist' i], [class*='room-list' i], [id*='roomlist' i]";
  const findRooms = () => {
    for (const el of document.querySelectorAll(ROOM_LISTS)) if (visible(el)) return el;
    for (const h of document.querySelectorAll("h2, h3")) {
      if (/^(rooms?|availability|available rooms|choose (?:your )?room|select (?:your |a )?room|room types?)\b/i.test(clean(h.innerText)))
        return h.closest("section") || h.parentElement.parentElement || h.parentElement;
    }
    return null;
  };
  let rooms = findRooms();
  if (rooms) rooms.scrollIntoView({ block: "start" });
  // Give lazy room lists up to about 6 seconds to fill in.
  for (let i = 0; i < 20 && !hasPrice(rooms = findRooms() || rooms); i++) {
    window.scrollBy(0, 300);
    await wait(300);
  }
  if (hasPrice(rooms)) await wait(600);
  const scope = hasPrice(rooms) ? rooms : document.body;

  // Room names in page order, so each price can take the nearest room above it.
  const roomEls = [];
  for (const el of document.querySelectorAll("h2, h3, h4, h5, a, strong, b, span, [class*='room' i], [data-testid*='room' i]")) {
    if (el.children.length > 3 || skip(el) || !visible(el)) continue;
    const t = clean(el.innerText);
    if (t.length >= 6 && t.length <= 70 && ROOM.test(t) && !PRICE.test(t) && !/[?!]$/.test(t) && !/^[\d"'“‘«]/.test(t) &&
        !NOT_ROOM.test(t)) roomEls.push([el, t]);
  }
  const roomFor = (el) => {
    let found = [null, ""];
    for (const pair of roomEls) if (pair[0].compareDocumentPosition(el) & Node.DOCUMENT_POSITION_FOLLOWING) found = pair;
    return found;
  };
  const TAXES = /(?:includes?|incl\.?|including)\s+(?:all\s+)?tax(?:es)?(?:\s*(?:and|&)\s*(?:fees|charges))?|\+\s?\S{0,4}\s?[\d,.]+\s+(?:in\s+)?tax(?:es)?(?:\s*(?:and|&)\s*(?:fees|charges))?|excl(?:\.|uding)?\s+tax(?:es)?(?:\s*(?:and|&)\s*(?:fees|charges))?|before tax(?:es)?|tax(?:es)? (?:and fees )?(?:not )?included/i;
  const PAYMENT = /no prepayment needed|pay nothing until [^•|·]{0,20}?\d{4}|pay at the (?:property|hotel)|pay later|pay now|prepay(?:ment)?(?: required)?/i;

  const found = [];
  for (const el of scope.querySelectorAll("*")) {
    if (skip(el)) continue;
    const t = clean(el.textContent);
    if (t.length > 40 || !PRICE.test(t) || /^(?:\+|(?:from|starting|was|save|saving)\b)/i.test(t)) continue;
    if ([...el.children].some((c) => PRICE.test(c.textContent))) continue;  // a child holds the price
    if (!visible(el) || /line-through/.test(getComputedStyle(el).textDecorationLine)) continue;  // skip struck-out "was" prices
    let price = t.match(PRICE)[0];
    // The words around the price (sites often split "AUD" and "659" into separate tags).
    const near = clean((el.parentElement && el.parentElement.parentElement || el).innerText);
    const num = price.match(/\d[\d,.]*\d/)[0];
    const at = near.indexOf(num);
    const after = at < 0 ? "" : near.slice(at + num.length, at + num.length + 40);
    const before = at < 0 ? "" : near.slice(Math.max(0, at - 12), at);
    if (/\+\s?\D{0,4}$/.test(before)) continue;  // an extra on top ("+ AU$68"), not a room price
    if (/^\W{0,3}(?:\/\s?person|per person|per adult|pp\b)/i.test(after)) continue;  // add-ons such as breakfast
    if (/^\W{0,3}(?:per night|\/\s?night|a night|nightly|avg)/i.test(after)) price += " per night";
    else if (/^\W{0,3}(?:total|for \d+ nights|in total)/i.test(after)) price += " total";
    // The rate's own box (a table row or card part), then the room's whole card, which stops
    // before it would take in another room's name.
    let box = el.closest("tr, li, article, [role='row'], [role='listitem'], [data-testid*='rate' i], [data-testid*='offer' i], [class*='rate' i]") || el;
    while (box.parentElement && box !== scope && clean(box.innerText).length < 120) box = box.parentElement;
    const [roomEl, room] = roomFor(el);
    let card = box;
    for (let i = 0; i < 8 && card.parentElement && card !== scope; i++) {
      const up = card.parentElement;
      if (roomEls.some(([r]) => r !== roomEl && up.contains(r) && !card.contains(r))) break;
      card = up;
    }
    const text = clean(box.innerText).slice(0, 2000);
    const cardText = clean(card.innerText).slice(0, 4000);
    const offer = [
      price,
      room,
      pick(text, CANCEL) || pick(cardText, CANCEL),
      pick(text, TAXES) || pick(cardText, TAXES),
      pick(text, PAYMENT) || pick(cardText, PAYMENT),
    ];
    found.push({ offer, card, nightly: / per night$/.test(price) });
  }
  // Where a card shows a total, its per-night figure is the same rate again, so keep the total.
  const withTotal = new Set(found.filter((f) => !f.nightly).map((f) => f.card));
  const kept = found.filter((f) => !(f.nightly && withTotal.has(f.card))).map((f) => f.offer);
  // One line per price and room, keeping whichever copy says the most.
  const byKey = new Map();
  const filled = (o) => o.filter(Boolean).join("").length;
  for (const o of kept) {
    const key = o[0] + "|" + o[1];
    if (!byKey.has(key) || filled(o) > filled(byKey.get(key))) byKey.set(key, o);
  }
  // Leave out small sums that aren't rooms (a fee, a deposit): well under the typical price here.
  const sorted = [...byKey.values()].sort((a, b) => value(a[0]) - value(b[0]));
  const median = sorted.length ? value(sorted[Math.floor(sorted.length / 2)][0]) : 0;
  const offers = sorted.filter((o) => value(o[0]) >= median * 0.4).slice(0, 4);
  // Terms every rate shares are listed once, in "all", to keep the answer short: the browser tool
  // cuts long answers off, and several sites are read in one batch.
  const all = {};
  ["cancellation", "taxes", "payment"].forEach((name, i) => {
    const v = offers.length > 1 && offers[0][i + 2];
    if (v && offers.every((o) => o[i + 2] === v)) { all[name] = v; offers.forEach((o) => { o[i + 2] = "same"; }); }
  });
  offers.forEach((o) => {
    o[1] = o[1].replace(/\s*&\s*/g, " and ").replace(/=/g, "-");
    while (o.length > 2 && !o[o.length - 1]) o.pop();
  });

  const text = clean(document.body.innerText);
  const flags = [
    !offers.length && /sold out|no availability|not available for your dates|unavailable on our site|no rooms available/i.test(text) && "sold-out",
    /sign in to (?:see|unlock|get)|log in to see/i.test(text) && "sign-in",
    /member price|members save|member rate/i.test(text) && "member",
    /are you a human|verify you are human|captcha|unusual traffic|press and hold/i.test(text) && "captcha",
    scope === document.body && "no-rooms",
  ].filter(Boolean);
  return JSON.stringify({
    hotel: clean((document.querySelector("h1") || document.querySelector("h2") || {}).innerText).slice(0, 60),
    offers,
    all,
    flags,
  });
})();
