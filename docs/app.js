/*
  The website's logic. It loads data/listings.json (written by the daily
  run) and draws the cards. Nothing here talks to any server: your
  Saved / Contacted / Viewing / Pass marks live in this browser only.
*/

const AREAS = ["All", "★ Overtoom (1054)", "Noord", "Centrum", "Oost", "West", "Sloterdijk"];
const MARKS = [["saved", "Saved"], ["contacted", "Contacted"], ["viewing", "Viewing"], ["pass", "Pass"]];
const STORE_KEY = "flat-tracker-marks";

let data = { listings: [], sources: [], not_included: [], updated: null };
let state = { tab: "rent", area: "All" };
const TABS = ["rent", "rent_stretch", "buy"];
// Which tab a listing is in. The daily run decides (rules in config.py);
// each listing is in exactly one tab.
const tabOf = (item) => item.tab || item.kind;
let marks = loadMarks();

// ---------------------------------------------------------------- helpers
const $ = (id) => document.getElementById(id);

// Small helper to build page elements safely (text is never read as HTML).
function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function loadMarks() {
  try { return JSON.parse(localStorage.getItem(STORE_KEY)) || {}; }
  catch (error) { return {}; }
}
function saveMarks() {
  try { localStorage.setItem(STORE_KEY, JSON.stringify(marks)); }
  catch (error) { /* private browsing: marks last until the tab closes */ }
}

const euro = (amount) => "€" + Math.round(amount).toLocaleString("en-GB");
const perM2 = (item) => (item.price && item.m2 ? item.price / item.m2 : Infinity);

function daysAgo(isoDate) {
  const then = new Date(isoDate + "T00:00:00Z");
  const days = Math.floor((Date.now() - then.getTime()) / 86400000);
  if (days <= 0) return "today";
  if (days === 1) return "yesterday";
  return days + " days ago";
}

const isNew = (item) => data.updated && item.first_seen === data.updated.slice(0, 10);

// ---------------------------------------------------------------- filtering
function visibleListings() {
  const maxPrice = Number($("max-price").value) || Infinity;
  const minSize = Number($("min-size").value) || 0;
  const bedrooms = $("bedrooms").value;
  const show = $("show").value;

  const items = data.listings.filter((item) => {
    if (tabOf(item) !== state.tab) return false;
    if (state.area === AREAS[1] ? !item.favourite : state.area !== "All" && item.area !== state.area) return false;
    if (item.price > maxPrice) return false;
    if ((item.m2 || 0) < minSize) return false;
    if (bedrooms && String(item.bedrooms) !== bedrooms) return false;
    const mark = marks[item.url];
    if (show === "open") return mark !== "pass";
    if (show === "new") return isNew(item) && mark !== "pass";
    if (show === "all") return true;
    return mark === show;
  });

  const sort = $("sort").value;
  if (sort === "price") items.sort((a, b) => a.price - b.price);
  else if (sort === "per-m2") items.sort((a, b) => perM2(a) - perM2(b));
  else items.sort((a, b) =>
    (b.first_seen || "").localeCompare(a.first_seen || "") ||
    (b.posted || "").localeCompare(a.posted || ""));
  return items;
}

// ---------------------------------------------------------------- drawing
function card(item) {
  const mark = marks[item.url];
  const box = el("article", "card" + (item.favourite ? " favourite" : "") + (mark === "pass" ? " pass" : ""));

  const badges = el("div", "badges");
  if (isNew(item)) badges.append(el("span", "badge new", "New today"));
  if (item.favourite) badges.append(el("span", "badge fav", "★ Overtoom"));
  if (badges.children.length) box.append(badges);

  box.append(el("h2", "address", item.address));
  box.append(el("p", "where",
    [item.type, item.postcode, item.area, item.neighbourhood].filter(Boolean).join(" · ")));

  const facts = el("div", "facts");
  facts.append(el("span", "price", euro(item.price) + (item.kind === "rent" ? " /month" : " k.k.")));
  if (item.m2) facts.append(el("span", "fact", item.m2 + " m²"));
  if (item.bedrooms != null) {
    facts.append(el("span", "fact", item.bedrooms + (item.bedrooms === 1 ? " bedroom" : " bedrooms")));
  }
  if (item.m2) facts.append(el("span", "fact", euro(perM2(item)) + " per m²"));
  box.append(facts);

  // "First found" is the day this tracker first saw the ad.
  let when = "First found " + daysAgo(item.first_seen);
  if (item.posted) when += " · posted " + daysAgo(item.posted);
  box.append(el("p", "meta", item.source + " · " + when));
  if (item.kind === "rent") {
    box.append(el("p", "meta", "Rental period: " + (item.rental_period || "Not stated")));
  }

  // Tags come ready-made from the daily run (wording is in config.py).
  const cautious = /^(Check|Private landlord|No registration)/;
  const tags = el("div", "tags");
  (item.tags || []).forEach((text) => tags.append(el("span",
    "tag" + (cautious.test(text) ? " warn" : text === "Registration allowed" ? " good" : ""), text)));
  box.append(tags);

  // The big button. Only real web addresses are ever linked.
  const open = el("a", "open", "Open the ad ↗");
  if (/^https?:\/\//.test(item.url)) open.href = item.url;
  open.target = "_blank";
  open.rel = "noopener noreferrer";
  box.append(open);

  const row = el("div", "marks");
  MARKS.forEach(([key, label]) => {
    const button = el("button", "mark", label);
    button.type = "button";
    button.setAttribute("aria-pressed", String(mark === key));
    button.addEventListener("click", () => {
      if (marks[item.url] === key) delete marks[item.url]; else marks[item.url] = key;
      saveMarks();
      draw();
    });
    row.append(button);
  });
  box.append(row);
  return box;
}

function draw() {
  const items = visibleListings();
  const list = $("list");
  list.replaceChildren(...items.map(card));
  if (!items.length) {
    list.append(el("p", "empty", data.listings.length
      ? "Nothing matches these filters right now."
      : "No listings yet. They appear after the first daily run."));
  }

  const ofKind = data.listings.filter((item) => tabOf(item) === state.tab);
  const passes = ofKind.filter((item) => marks[item.url] === "pass").length;
  const fresh = ofKind.filter(isNew).length;
  $("summary").textContent = items.length + " shown · " + fresh + " new today" +
    (passes ? " · " + passes + " passed" + ($("show").value === "open" ? " (hidden)" : "") : "");

  for (const name of TABS) {
    $("count-" + name).textContent = "(" + data.listings.filter((item) => tabOf(item) === name).length + ")";
  }
  document.querySelectorAll(".tab").forEach((tab) =>
    tab.setAttribute("aria-selected", String(tab.dataset.tab === state.tab)));
  document.querySelectorAll(".chip").forEach((chip) =>
    chip.setAttribute("aria-pressed", String(chip.textContent === state.area)));
}

function when(isoTime) {
  return new Date(isoTime).toLocaleString("en-GB", {
    timeZone: "Europe/Amsterdam", weekday: "short", day: "numeric", month: "short",
    hour: "2-digit", minute: "2-digit",
  });
}

function drawHeader() {
  if (!data.updated) { $("updated").textContent = "Not updated yet."; return; }
  $("updated").textContent = "Last successful update: " + when(data.updated) + " (Amsterdam time)";
  if (data.last_attempt) {
    $("attempt").textContent = "Last attempt: " + when(data.last_attempt) + " — " +
      (data.last_attempt_ok ? "worked" : "did not work") +
      (data.last_attempt_note ? ". " + data.last_attempt_note : "");
  }
  // Clear warning when the listings are more than a day old.
  const hours = (Date.now() - new Date(data.updated).getTime()) / 3600000;
  if (hours > 24) {
    $("updated").classList.add("stale");
    $("warning").hidden = false;
    $("warning").textContent = "⚠ No successful update for " + Math.floor(hours) +
      " hours. Listings below may be out of date. Check the Actions tab on GitHub.";
  }
}

function drawSources() {
  const stateOf = (source) => source.state || (source.ok ? "ok" : "failed");
  const labels = { ok: ["ok", "✓ Worked"], failed: ["fail", "✗ Failed"], setup: ["setup", "○ Not set up"] };
  const working = data.sources.filter((source) => stateOf(source) === "ok").length;
  const waiting = data.sources.filter((source) => stateOf(source) === "setup").length;
  $("sources-short").textContent = "— " + working + " of " + data.sources.length + " worked" +
    (waiting ? ", " + waiting + " not set up yet" : "");
  $("sources").replaceChildren(...data.sources.map((source) => {
    const row = el("tr");
    const name = el("td", "", source.name);
    if (source.note) name.append(el("span", "note", source.note));
    const [style, label] = labels[stateOf(source)];
    row.append(name, el("td", style, label),
      el("td", "", String(source.found)), el("td", "", String(source.shown)));
    return row;
  }));
  $("not-included").replaceChildren(...(data.not_included || []).map((source) =>
    el("li", "", source.name + ": " + source.note)));
}

// ---------------------------------------------------------------- start-up
AREAS.forEach((name) => {
  const chip = el("button", "chip", name);
  chip.type = "button";
  chip.addEventListener("click", () => { state.area = name; draw(); });
  $("areas").append(chip);
});
document.querySelectorAll(".tab").forEach((tab) =>
  tab.addEventListener("click", () => { state.tab = tab.dataset.tab; draw(); }));
["max-price", "min-size", "bedrooms", "sort", "show"].forEach((id) =>
  $(id).addEventListener("input", draw));

// "?t=" makes sure the browser never shows yesterday's copy of the data.
fetch("data/listings.json?t=" + Date.now())
  .then((reply) => reply.json())
  .then((json) => { data = json; drawHeader(); drawSources(); draw(); })
  .catch(() => { $("updated").textContent = "Could not load the listings. Try reloading the page."; });
