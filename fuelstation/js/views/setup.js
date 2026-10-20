import * as store from "../store.js";
import * as auth from "../auth.js";
import { html, raw, render, openForm, confirmBox, money, opts, num, todayKey, fmtDate, toast } from "../ui.js";
import { active, nameOf, priceOn } from "../calc.js";
import { INDIANOIL_CATALOGUE } from "../catalogue.js";

const TABS = [
  ["station", "Station"], ["products", "Products"], ["pumps", "Pumps"], ["prices", "Price"],
  ["shifts", "Shifts"], ["expenseTypes", "Expense types"], ["sources", "Payment sources"], ["team", "Team"], ["data", "Backup"],
];
const ROLES = [{ value: "attendant", label: "Attendant (daily entry only)" }, { value: "manager", label: "Manager" }, { value: "owner", label: "Owner" }];
const USED_BY = { products: [["nozzles", "productId"], ["prices", "productId"], ["credits", "productId"]], nozzles: [["readings", "nozzleId"]],
  shifts: [["readings", "shiftId"], ["credits", "shiftId"], ["payments", "shiftId"], ["expenses", "shiftId"]],
  expenseTypes: [["expenses", "typeId"]], sources: [["payments", "sourceId"], ["expenses", "sourceId"]] };

let tab = "station";

export function mount(root, param) {
  if (param && TABS.some(([k]) => k === param)) tab = param;
  const redraw = () => mount(root);
  const isOwner = store.currentUser().role === "owner";
  const tabs = TABS.filter(([k]) => isOwner || k !== "team");
  root.onclick = (e) => {
    const t = e.target.closest("[data-act]");
    if (!t) return;
    const { act, id } = t.dataset;
    if (act === "tab") { tab = id; return redraw(); }
    const h = handlers[tab]?.[act];
    if (h) h(id, redraw);
  };
  render(root, html`
    <h2>Setup</h2>
    <div class="chips scroll">${tabs.map(([k, l]) => html`<button class="chip slim ${tab === k ? "on" : ""}" data-act="tab" data-id="${k}">${l}</button>`)}</div>
    <div id="setupBody">${panel()}</div>`);
}

// ---------- panels ----------
function masterList({ col, title, hint, rowSub }) {
  const rows = store.list(col);
  return html`
    <div class="section-row"><div><h3>${title}</h3>${hint ? html`<p class="muted">${hint}</p>` : ""}</div><button class="btn primary small" data-act="add">+ Add</button></div>
    <div class="list">${rows.length ? rows.map((r) => html`
      <button class="row ${r.archived ? "off" : ""}" data-act="edit" data-id="${r.id}"><span class="row-main">${r.name}<small>${rowSub?.(r) || ""}${r.archived ? " · inactive" : ""}</small></span><span class="chev">›</span></button>`)
      : html`<p class="muted pad">Nothing here yet.</p>`}</div>`;
}

function panel() {
  switch (tab) {
    case "station": {
      const s = store.currentStation();
      return html`<div class="card"><h3>${s.name}</h3><p class="muted">Currency ${s.currency}</p><button class="btn small" data-act="edit">Edit station</button></div>
        <p class="muted pad">Signed in as <b>${store.currentUser().name}</b> (${store.currentUser().role}). <button class="link" data-act="logout">Sign out</button></p>`;
    }
    case "products": return productsPanel();
    case "pumps": return pumpsPanel();
    case "expenseTypes": return masterList({ col: "expenseTypes", title: "Expense types" });
    case "sources": return masterList({ col: "sources", title: "Online payment sources", hint: "UPI, cards, bank, fleet cards…" });
    case "shifts": return shiftsPanel();
    case "prices": return pricesPanel();
    case "team": return teamPanel();
    default: return html`<div class="card"><h3>Backup</h3><p class="muted">Data is saved on this device. Download a copy regularly until cloud sync is switched on.</p>
      <button class="btn" data-act="export">Download backup (JSON)</button></div>`;
  }
}

function shiftsPanel() {
  const shifts = store.list("shifts");
  return html`
    <div class="card"><h3>Number of shifts</h3><p class="muted">Pick how many shifts you run and when the first one starts — timings are split evenly. You can fine-tune each shift afterwards.</p>
      <button class="btn" data-act="quick">Set up shifts…</button></div>
    <div class="section-row"><h3>Shifts (${active("shifts").length} active)</h3><button class="btn primary small" data-act="add">+ Add</button></div>
    <div class="list">${shifts.map((s) => html`<button class="row ${s.archived ? "off" : ""}" data-act="edit" data-id="${s.id}">
      <span class="row-main">${s.name}<small>${s.start} – ${s.end}${s.archived ? " · inactive" : ""}</small></span><span class="chev">›</span></button>`)}</div>`;
}

function productsPanel() {
  const rows = store.list("products");
  return html`
    <div class="section-row"><div><h3>Products</h3><p class="muted">Fuels, gas and lubricants you sell.</p></div></div>
    <div class="two-btn"><button class="btn primary" data-act="catalogue">Add from Indian Oil list</button><button class="btn" data-act="add">+ Custom</button></div>
    <div class="list">${rows.length ? rows.map((r) => html`
      <button class="row ${r.archived ? "off" : ""}" data-act="edit" data-id="${r.id}"><span class="row-main">${r.name}<small>${r.category} · per ${r.unit}${r.archived ? " · inactive" : ""}</small></span><span class="chev">›</span></button>`)
      : html`<p class="muted pad">No products yet.</p>`}</div>`;
}

function pumpsPanel() {
  const pumps = store.list("pumps");
  const nozzlesOf = (id) => store.list("nozzles").filter((n) => n.pumpId === id);
  return html`
    <div class="section-row"><div><h3>Pumps &amp; nozzles</h3><p class="muted">Each nozzle has its own product and meter reading every shift.</p></div><button class="btn primary small" data-act="add">+ Pump</button></div>
    ${pumps.length ? pumps.map((p) => html`
      <div class="card pump-setup ${p.archived ? "off" : ""}">
        <div class="section-row"><b>${p.name}${p.archived ? " · inactive" : ""}</b><span><button class="btn small" data-act="edit" data-id="${p.id}">Edit</button> <button class="btn small primary" data-act="add-nozzle" data-id="${p.id}">+ Nozzle</button></span></div>
        <div class="list">${nozzlesOf(p.id).length ? nozzlesOf(p.id).map((n) => html`
          <button class="row ${n.archived ? "off" : ""}" data-act="edit-nozzle" data-id="${n.id}"><span class="row-main">${n.name}<small>${nameOf("products", n.productId)}${n.archived ? " · inactive" : ""}</small></span><span class="chev">›</span></button>`)
          : html`<p class="muted pad">No nozzles yet — add one.</p>`}</div>
      </div>`) : html`<p class="muted pad">No pumps yet. Add a pump, then its nozzles.</p>`}`;
}

// Price history per product: each entry is a price that applies from its date until the next entry.
function pricesPanel() {
  const today = todayKey();
  return html`
    <p class="muted">Each price applies from its start date until the next one. Add a new entry when the rate changes, or fix a past one.</p>
    ${active("products").map((p) => {
      const hist = store.list("prices").filter((x) => x.productId === p.id).sort((a, b) => b.date.localeCompare(a.date) || b.createdAt - a.createdAt);
      const cur = priceOn(p.id, today);
      return html`<div class="card price-card">
        <div class="section-row"><div><b>${p.name}</b><div class="muted">${cur == null ? "No price set" : "Now " + money(cur) + " per " + p.unit}</div></div>
          <button class="btn small primary" data-act="add" data-id="${p.id}">+ Add price</button></div>
        <div class="list">${hist.length ? hist.map((h, i) => {
          const next = hist[i - 1];     // newer entry ends this one
          const live = h.date <= today && (!next || next.date > today);
          return html`<button class="row" data-act="edit" data-id="${h.id}"><span class="row-main">${money(h.price)} <small>${fmtDate(h.date, { day: "numeric", month: "short", year: "numeric" })} → ${next ? fmtDate(next.date, { day: "numeric", month: "short", year: "numeric" }) : "ongoing"}${h.date > today ? " · upcoming" : ""}</small></span>${live ? html`<span class="badge">Current</span>` : html`<span class="chev">›</span>`}</button>`;
        }) : html`<p class="muted pad">No prices yet.</p>`}</div></div>`;
    })}`;
}

function teamPanel() {
  const me = store.currentUser();
  return html`<div class="section-row"><h3>Team</h3><button class="btn primary small" data-act="add">+ Add</button></div>
    <div class="list">${store.stationUsers().map((u) => html`<button class="row ${u.active === false ? "off" : ""}" data-act="edit" data-id="${u.id}">
      <span class="row-main">${u.name}${u.id === me.id ? " (you)" : ""}<small>@${u.username} · ${u.role}${u.active === false ? " · disabled" : ""}</small></span><span class="chev">›</span></button>`)}</div>`;
}

// ---------- forms ----------
const FORMS = {
  products: (e = {}) => [
    { name: "name", label: "Name", value: e.name, required: true },
    { name: "category", label: "Category", type: "select", value: e.category || "Fuel", options: ["Fuel", "Gas", "Lubricant", "Other"].map((v) => ({ value: v, label: v })) },
    { name: "unit", label: "Unit", type: "select", value: e.unit || "L", options: ["L", "Kg", "Piece"].map((v) => ({ value: v, label: v })) },
  ],
  pumps: (e = {}) => [
    { name: "name", label: "Pump name", value: e.name, required: true, placeholder: "e.g. Pump 1" },
    ...(e.id ? [] : [
      { name: "count", label: "Number of nozzles", type: "select", value: "2", options: [1, 2, 3, 4, 5, 6, 8].map((n) => ({ value: String(n), label: String(n) })) },
      { name: "productId", label: "Product for the nozzles", type: "select", options: opts(active("products")), hint: "You can change each nozzle's product afterwards." },
    ]),
  ],
  nozzles: (e = {}) => [
    { name: "name", label: "Nozzle name", value: e.name, required: true, placeholder: "e.g. Nozzle 1" },
    { name: "productId", label: "Dispenses", type: "select", value: e.productId, options: opts(active("products")) },
  ],
  expenseTypes: (e = {}) => [{ name: "name", label: "Expense type", value: e.name, required: true }],
  sources: (e = {}) => [{ name: "name", label: "Source name", value: e.name, required: true }],
  shifts: (e = {}) => [
    { name: "name", label: "Shift name", value: e.name, required: true },
    { name: "start", label: "Starts", type: "time", value: e.start || "06:00", required: true },
    { name: "end", label: "Ends", type: "time", value: e.end || "14:00", required: true },
  ],
};

function inUse(col, id) {
  return (USED_BY[col] || []).some(([c, key]) => store.list(c).some((r) => r[key] === id));
}

function addToggle(entry, col, redraw) {
  const foot = document.querySelector(".overlay .sheet-foot");
  const b = document.createElement("button");
  b.type = "button"; b.className = "btn"; b.textContent = entry.archived ? "Reactivate" : "Make inactive";
  b.onclick = () => { store.update(col, entry.id, { archived: !entry.archived }); document.querySelector(".overlay")?.remove(); document.body.classList.remove("no-scroll"); redraw(); };
  foot.prepend(b);
}

// Pick any number of Indian Oil products to add in one go; ones you already have are ticked and locked.
function openCatalogue(redraw) {
  const have = new Set(store.list("products").map((p) => p.name.toLowerCase()));
  const overlay = document.createElement("div");
  overlay.className = "overlay";
  overlay.innerHTML = html`<form class="sheet" novalidate>
    <div class="sheet-head"><h2>Indian Oil products</h2><button type="button" class="icon-btn" data-close aria-label="Close">✕</button></div>
    <p class="muted">Tick what your station sells. Anything missing can be added with “+ Custom”.</p>
    <div class="sheet-body">${INDIANOIL_CATALOGUE.map((g) => html`<div class="cat-group"><h3>${g.group}</h3>
      ${g.items.map((it, i) => html`<label class="check"><input type="checkbox" name="${g.group}|${i}" ${have.has(it.name.toLowerCase()) ? raw("checked disabled") : ""}> <span>${it.name}<small>${it.category} · per ${it.unit}</small></span></label>`)}</div>`)}</div>
    <div class="sheet-foot"><button type="submit" class="btn primary">Add selected</button></div></form>`.s;
  document.body.appendChild(overlay);
  document.body.classList.add("no-scroll");
  const close = () => { overlay.remove(); if (!document.querySelector(".overlay")) document.body.classList.remove("no-scroll"); };
  overlay.querySelector("[data-close]").onclick = close;
  overlay.addEventListener("mousedown", (e) => { if (e.target === overlay) close(); });
  overlay.querySelector("form").onsubmit = (e) => {
    e.preventDefault();
    let added = 0;
    for (const g of INDIANOIL_CATALOGUE) g.items.forEach((it, i) => {
      const box = e.target.elements[`${g.group}|${i}`];
      if (box && box.checked && !box.disabled) { store.add("products", { ...it }); added++; }
    });
    close(); toast(added ? `Added ${added} product${added > 1 ? "s" : ""}` : "Nothing selected"); redraw();
  };
}

function masterHandlers(col) {
  const edit = (entry, redraw) => {
    if (col === "pumps" && !active("products").length) { toast("Add a product first."); return; }
    openForm({
      title: `${entry ? "Edit" : "Add"} ${col === "expenseTypes" ? "expense type" : col.replace(/s$/, "")}`,
      fields: FORMS[col](entry || undefined),
      onSubmit(v) { entry ? store.update(col, entry.id, v) : store.add(col, v); redraw(); },
      onDelete: entry && !inUse(col, entry.id) && (() => { store.remove(col, entry.id); redraw(); }),
    });
    // Records with history can't be deleted — offer to hide them instead.
    if (entry && inUse(col, entry.id)) addToggle(entry, col, redraw);
  };
  return { add: (_, r) => edit(null, r), edit: (id, r) => edit(store.get(col, id), r) };
}

const handlers = {
  products: {
    ...masterHandlers("products"),
    catalogue(_, redraw) { openCatalogue(redraw); },
  },
  pumps: {
    add(_, redraw) {
      if (!active("products").length) { toast("Add a product first."); return; }
      openForm({
        title: "Add pump", fields: FORMS.pumps(),
        onSubmit(v) {
          const pump = store.add("pumps", { name: v.name });
          for (let i = 1; i <= Number(v.count); i++) store.add("nozzles", { pumpId: pump.id, name: `Nozzle ${i}`, productId: v.productId });
          redraw();
        },
      });
    },
    edit(id, redraw) {
      const pump = store.get("pumps", id);
      const used = store.list("nozzles").some((n) => n.pumpId === id);
      openForm({
        title: "Edit pump", fields: FORMS.pumps(pump),
        onSubmit(v) { store.update("pumps", id, { name: v.name }); redraw(); },
        onDelete: !used && (() => { store.remove("pumps", id); redraw(); }),
      });
      if (used) addToggle(pump, "pumps", redraw);
    },
    "add-nozzle"(pumpId, redraw) {
      if (!active("products").length) { toast("Add a product first."); return; }
      const n = store.list("nozzles").filter((x) => x.pumpId === pumpId).length + 1;
      const last = store.list("nozzles").filter((x) => x.pumpId === pumpId).at(-1);
      openForm({
        title: `Add nozzle to ${nameOf("pumps", pumpId)}`, fields: FORMS.nozzles({ name: `Nozzle ${n}`, productId: last?.productId }),
        onSubmit(v) { store.add("nozzles", { pumpId, name: v.name, productId: v.productId }); redraw(); },
      });
    },
    "edit-nozzle"(id, redraw) {
      const n = store.get("nozzles", id);
      const used = inUse("nozzles", id);
      openForm({
        title: `${nameOf("pumps", n.pumpId)} · ${n.name}`, fields: FORMS.nozzles(n),
        note: used ? "This nozzle has meter readings, so it can be made inactive but not deleted." : "",
        onSubmit(v) { store.update("nozzles", id, v); redraw(); },
        onDelete: !used && (() => { store.remove("nozzles", id); redraw(); }),
      });
      if (used) addToggle(n, "nozzles", redraw);
    },
  },
  expenseTypes: masterHandlers("expenseTypes"),
  sources: masterHandlers("sources"),
  shifts: {
    ...masterHandlers("shifts"),
    quick(_, redraw) {
      const first = active("shifts")[0]?.start || "06:00";
      openForm({
        title: "Set up shifts",
        fields: [
          { name: "count", label: "Number of shifts", type: "select", value: String(active("shifts").length || 2), options: [1, 2, 3, 4, 5, 6].map((n) => ({ value: String(n), label: String(n) })) },
          { name: "start", label: "First shift starts at", type: "time", value: first, required: true },
        ],
        note: "Existing shifts are re-timed in order; extra ones become inactive (their history is kept).",
        onSubmit(v) { applyShifts(Number(v.count), v.start); redraw(); },
      });
    },
  },
  prices: {
    add: (productId, redraw) => priceForm({ productId }, redraw),
    edit: (id, redraw) => priceForm({ entry: store.get("prices", id) }, redraw),
  },
  station: {
    edit(_, redraw) {
      const s = store.currentStation();
      openForm({
        title: "Station", fields: [
          { name: "name", label: "Station name", value: s.name, required: true },
          { name: "currency", label: "Currency symbol", value: s.currency, required: true },
        ],
        onSubmit(v) { store.updateStation(v); redraw(); },
      });
    },
    logout() { auth.logout(); location.reload(); },
  },
  team: {
    add(_, redraw) {
      openForm({
        title: "Add team member", fields: [
          { name: "name", label: "Name", required: true },
          { name: "username", label: "Username", required: true },
          { name: "password", label: "Password (min 6)", type: "password", required: true },
          { name: "role", label: "Role", type: "select", options: ROLES, value: "attendant" },
        ],
        async onSubmit(v) { await auth.addTeamMember(v); redraw(); },
      });
    },
    edit(id, redraw) {
      const u = store.stationUsers().find((x) => x.id === id);
      openForm({
        title: u.name, fields: [
          { name: "name", label: "Name", value: u.name, required: true },
          { name: "role", label: "Role", type: "select", options: ROLES, value: u.role },
          { name: "password", label: "New password (leave blank to keep)", type: "password" },
          { name: "active", label: "Account", type: "select", value: u.active === false ? "no" : "yes", options: [{ value: "yes", label: "Active" }, { value: "no", label: "Disabled" }] },
        ],
        async onSubmit(v) {
          await auth.updateTeamMember(id, { name: v.name, role: v.role, active: v.active === "yes", password: v.password });
          redraw();
        },
      });
    },
  },
  data: {
    export() {
      const a = document.createElement("a");
      a.href = URL.createObjectURL(new Blob([store.exportStation()], { type: "application/json" }));
      a.download = `fuel-station-backup-${todayKey()}.json`;
      a.click();
      URL.revokeObjectURL(a.href);
    },
  },
};

// Re-time/create `count` evenly spaced shifts starting at `start`; leftover shifts go inactive.
function applyShifts(count, start) {
  const [h, m] = start.split(":").map(Number);
  const startMin = h * 60 + m, len = Math.round(1440 / count);
  const fmt = (min) => { const x = ((min % 1440) + 1440) % 1440; return String(Math.floor(x / 60)).padStart(2, "0") + ":" + String(x % 60).padStart(2, "0"); };
  const all = store.list("shifts");
  for (let i = 0; i < Math.max(count, all.length); i++) {
    const slot = { start: fmt(startMin + i * len), end: fmt(startMin + (i + 1) * len) };
    if (i < count) {
      const ex = all[i];
      if (ex) store.update("shifts", ex.id, { ...slot, archived: false });
      else store.add("shifts", { name: `Shift ${i + 1}`, ...slot });
    } else store.update("shifts", all[i].id, { archived: true });
  }
}

function priceForm({ productId, entry }, redraw) {
  const p = store.get("products", entry ? entry.productId : productId);
  openForm({
    title: `${p.name} price`,
    note: entry ? "Change the rate or the date it started." : "The new price applies from this date until you add another.",
    fields: [
      { name: "price", label: `Price per ${p.unit}`, type: "number", value: entry ? entry.price : priceOn(p.id, todayKey()), required: true },
      { name: "date", label: "Applies from", type: "date", value: entry ? entry.date : todayKey(), required: true },
    ],
    onSubmit(v) {
      const clash = store.list("prices").find((x) => x.productId === p.id && x.date === v.date && x.id !== entry?.id);
      if (clash) store.remove("prices", clash.id);            // one price per product per start date
      if (entry) store.update("prices", entry.id, { date: v.date, price: num(v.price) });
      else store.add("prices", { productId: p.id, date: v.date, price: num(v.price) });
      redraw();
    },
    onDelete: entry && (() => { store.remove("prices", entry.id); redraw(); }),
  });
}
