// MyRoomPrice page finder (readable source; tools/build_scripts.py makes the short copy in the skill's scripts/). Run this whole file on a Google search results page with the browser's
// JavaScript tool, after putting the hotel's name in place of HOTEL NAME on the first line of code.
// It returns one short JSON string with the hotel's own page on each booking site Google found, and
// the hotel's official website:
//   sites    - {booking, agoda, expedia, hotels, trip, priceline, kayak, tripadvisor, wotif, qantas, ...}: each the page's
//              address without its ? part, and the result's title, as [address, title]
//   official - [address, title] of the result that looks like the hotel's own website, or null
//   score    - for each entry, how well its title matched the name, 0 to 1 (below 0.5, check it)
// Add the dates to each address yourself (see "Booking links" in references/sites.md): the browser
// tool hides results that carry dates after a ?. Nothing is clicked or changed.
await (async (WANT = "HOTEL NAME") => {
  const clean = (s) => (s || "").replace(/\s+/g, " ").trim();
  const words = (s) => clean(s).toLowerCase().normalize("NFKD").replace(/[\u0300-\u036f]/g, "")
    .replace(/&/g, " and ").split(/[^a-z0-9]+/).filter((w) => w.length > 1);
  // Words that don't tell one hotel from another.
  const GENERIC = new Set(["hotel", "hotels", "the", "and", "resort", "spa", "inn", "by", "at", "of", "on", "in", "suites", "apartments"]);
  const want = words(WANT).filter((w) => !GENERIC.has(w));
  const score = (text) => {
    const have = new Set(words(text));
    return want.length ? want.filter((w) => have.has(w)).length / want.length : 0;
  };
  // A link to one hotel's own page on each site (not a list, a map or a city page).
  const SITES = {
    booking: /^https:\/\/[^/]*booking\.com\/hotel\/[a-z]{2}\/[^/?#]+\.html/i,
    agoda: /^https:\/\/[^/]*agoda\.com\/(?:[a-z]{2}-[a-z]{2}\/)?[^/?#]+\/hotel\/[^/?#]+\.html/i,
    expedia: /^https:\/\/[^/]*expedia\.[a-z.]+\/[^?#]*\.h\d+\.Hotel-Information/i,
    hotels: /^https:\/\/[^/]*hotels\.com\/ho\d+/i,
    trip: /^https:\/\/[^/]*trip\.com\/hotels\/[^?#]*hotel-detail-\d+/i,
    priceline: /^https:\/\/[^/]*priceline\.com\/relax\/at\/\d+/i,
    kayak: /^https:\/\/[^/]*kayak\.[a-z.]+\/hotels\/[^?#]+-h\d+/i,
    tripadvisor: /^https:\/\/[^/]*tripadvisor\.[a-z.]+\/Hotel_Review-/i,
    // The "More sites" row. Not yet checked in testing: check the title matches before using one.
    wotif: /^https:\/\/[^/]*wotif\.com\/[^?#]*\.h\d+\.Hotel-Information/i,
    qantas: /^https:\/\/[^/]*qantas\.com\/hotels\/properties\//i,
    luxuryescapes: /^https:\/\/[^/]*luxuryescapes\.com\/[^?#]*\/offer\//i,
    webjet: /^https:\/\/[^/]*webjet\.com(\.au)?\/hotels?\/[^?#]+/i,
    lastminute: /^https:\/\/[^/]*lastminute\.com\/[^?#]*hotel[^?#]*/i,
    vrbo: /^https:\/\/[^/]*vrbo\.com\/(?:[a-z-]+\/)?\d+/i,
    hoteltonight: /^https:\/\/[^/]*hoteltonight\.com\/[^?#]*hotel[^?#]*/i,
  };
  // Hosts that are never the hotel's own website.
  const NOT_OFFICIAL = new Set(("google booking agoda expedia hotels trip priceline kayak tripadvisor trivago wotif orbitz " +
    "travelocity hostelworld airbnb vrbo lastminute ebookers hotelscombined momondo skyscanner guestreservations " +
    "reservations hotelplanner facebook instagram youtube linkedin tiktok x twitter wikipedia yelp lonelyplanet " +
    "timeout news herald smh abc bbc cnn travelweekly luxuryescapes qantas webjet zenhotels ostrovok klook " +
    "traveloka makemytrip goibibo yatra hrs ctrip tiket pegipegi").split(" "));
  const results = [];
  for (const a of document.querySelectorAll("#search a[href], #rso a[href], a[href]")) {
    let href = a.href;
    try {
      const u = new URL(href);
      if (/google\./.test(u.host)) {
        const q = u.searchParams.get("url") || u.searchParams.get("q");  // Google's own redirect links
        if (!q || !/^https?:/.test(q)) continue;
        href = q;
      }
    } catch (e) { continue; }
    const title = clean((a.querySelector("h3") || a).innerText).slice(0, 90);
    results.push([href.split("?")[0].split("#")[0], title]);
  }
  const sites = {};
  for (const [key, re] of Object.entries(SITES)) {
    const hit = results.filter(([h]) => re.test(h)).sort((x, y) => score(y[1] + " " + y[0]) - score(x[1] + " " + x[0]))[0];
    if (hit) sites[key] = [hit[0], hit[1], +score(hit[1] + " " + hit[0].replace(/[-_/.]/g, " ")).toFixed(2)];
  }
  let official = null;
  for (const [h, t] of results) {
    const host = new URL(h).host.replace(/^www\./, "");
    if (host.split(".").some((part) => NOT_OFFICIAL.has(part)) || !t) continue;
    const s = Math.max(score(t), score(host.replace(/[-.]/g, " ")));
    if (s >= 0.5) { official = [h, t, +s.toFixed(2)]; break; }
  }
  return JSON.stringify({ sites, official });
})();
