// MyRoomPrice room loader (readable source; tools/build_scripts.py makes the short copy in the skill's scripts/).
// Claude runs it on a hotel's page on a booking site, then reads the page with the browser's "get page text" tool.
// It scrolls to the room list and waits for its prices (many sites only load rooms on scroll), then puts a copy
// of the room list's text in a hidden <article> at the top of the page, so "get page text" returns just the rooms,
// word for word, instead of the whole page. Nothing is clicked; nothing is sent anywhere.
// It returns {"rooms": true} when it found a room list with prices, {"rooms": false} when it didn't (the page text
// is then the whole page, or the site's own article).
await (async () => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  // The room list on each site: Booking.com, Agoda, Expedia and Hotels.com, then common names elsewhere.
  const LIST = "#hprt-table,#available_rooms,[data-selenium=roomgrid],[data-element-name=roomgrid],[data-stid=section-room-list]," +
    "#Offers,[class*=roomlist i],[class*=room-list i]";
  const PRICE = /(\$|£|€|¥|฿|₹|AUD|USD|EUR|GBP|NZD|SGD|THB|JPY|IDR|MYR|VND|HKD|CAD)\s?\d/;
  let list = null;
  for (let i = 0; i < 24; i++) {
    list = document.querySelector(LIST);
    if (list) {
      list.scrollIntoView();
      if (PRICE.test(list.innerText)) break;
    } else scrollBy(0, 400);
    await wait(300);
  }
  await wait(700);  // let the last rates fill in
  const rooms = !!list && PRICE.test(list.innerText);
  if (rooms) {
    const old = document.getElementById("mrp-rooms");
    if (old) old.remove();
    const copy = document.createElement("article");
    copy.id = "mrp-rooms";
    copy.style.cssText = "position:absolute;left:-9999px;top:0;width:600px";
    copy.innerText = ((document.querySelector("h1") || {}).innerText || "") + "\n" + list.innerText.slice(0, 12000);
    document.body.prepend(copy);
  }
  return JSON.stringify({ rooms });
})();
