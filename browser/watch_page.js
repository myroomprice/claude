// MyRoomPrice watcher (readable source; tools/build_scripts.py makes the short copy in the skill's scripts/). Run this whole file in the MyRoomPrice tab with the browser's JavaScript tool
// whenever you're waiting for the user there (for Check prices, or an answer to a question). It:
//   - tells the page Claude is connected, so the page doesn't ask the user to type /myroomprice
//     (the page counts Claude as connected while these check-ins keep coming, about once a minute);
//   - waits up to about 30 seconds, and returns the moment the user clicks Check prices or answers.
// It returns one short JSON string:
//   request - the request line ("Check requested. Hotel: ..." or "Answer given. Question: ..."),
//             or "" if nothing came in. A pasted link's details after its "?" are left out (the browser
//             tool hides answers that carry them); read the page text if you need the full link.
//   page    - "myroomprice" while the tab still shows MyRoomPrice, "other" if the user left it.
// Run it again straight away when request is "": the page stays connected as long as you keep going.
// Nothing on the page is clicked or changed, apart from the two marks it sets (data-claude-seen, data-claude-took).
await (async () => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const request = document.getElementById("request");
  if (!request || !/MyRoomPrice/.test(document.title)) return JSON.stringify({ request: "", page: "other" });
  // The page watches this mark (see "Claude's check-ins" in the page's script).
  const checkIn = () => document.documentElement.setAttribute("data-claude-seen", String(Date.now()));
  const read = () => {
    const line = (request.textContent || "").replace(/\s+/g, " ").trim();
    return /^(Check requested|Answer given)\b/.test(document.title) && line ? line : "";
  };
  checkIn();
  for (let i = 0; i < 60; i++) {
    const line = read();
    if (line) {
      checkIn();
      document.documentElement.setAttribute("data-claude-took", String(Date.now()));  // the page shows "Claude has your search"
      return JSON.stringify({ request: line.replace(/(Link: \S+?)\?\S*/, "$1"), page: "myroomprice" });
    }
    if (i % 10 === 9) checkIn();
    await wait(500);
  }
  checkIn();
  return JSON.stringify({ request: "", page: "myroomprice" });
})();
