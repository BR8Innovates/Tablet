import * as store from "../store.js";
import * as auth from "../auth.js";
import { html, render, openForm, confirmBox, money, opts, num, todayKey, fmtDate, toast } from "../ui.js";
import { active, nameOf, priceOn } from "../calc.js";

const TABS = [
  ["station", "Station"], ["products", "Products"], ["pumps", "Pumps"], ["prices", "Daily price"],
  ["shifts", "Shifts"], ["expenseTypes", "Expense types"], ["sources", "Payment sources"], ["team", "Team"], ["data", "Backup"],
];
const ROLES = [{ value: "attendant", label: "Attendant (daily entry only)" }, { value: "manager", label: "Manager" }, { value: "owner", label: "Owner" }];
const USED_BY = { products: [["pumps", "productId"], ["prices", "productId"], ["credits", "productId"]], pumps: [["readings", "pumpId"]],
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
    case "products": return masterList({ col: "products", title: "Products", hint: "Fuels and other items you sell.", rowSub: (r) => `${r.category} · per ${r.unit}` });
    case "pumps": return masterList({ col: "pumps", title: "Pumps / nozzles", hint: "Each one gets its own meter reading every shift.", rowSub: (r) => nameOf("products", r.productId) });
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

function pricesPanel() {
  const fuels = active("products");
  const hist = [...store.list("prices")].sort((a, b) => b.date.localeCompare(a.date) || b.createdAt - a.createdAt).slice(0, 12);
  return html`
    <h3>Today's prices</h3>
    <div class="list">${fuels.map((p) => { const cur = priceOn(p.id, todayKey()); return html`
      <button class="row" data-act="set" data-id="${p.id}"><span class="row-main">${p.name}<small>${cur == null ? "No price set" : "per " + p.unit}</small></span>
        <b>${cur == null ? "Set price" : money(cur)}</b></button>`; })}</div>
    <h3 class="section">Recent changes</h3>
    <div class="list">${hist.length ? hist.map((h) => html`<div class="row static"><span class="row-main">${nameOf("products", h.productId)}<small>from ${fmtDate(h.date)}</small></span><b>${money(h.price)}</b></div>`)
      : html`<p class="muted pad">No prices yet.</p>`}</div>`;
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
    { name: "category", label: "Category", type: "select", value: e.category || "Fuel", options: ["Fuel", "Lubricant", "Other"].map((v) => ({ value: v, label: v })) },
    { name: "unit", label: "Unit", type: "select", value: e.unit || "L", options: ["L", "Kg", "Piece"].map((v) => ({ value: v, label: v })) },
  ],
  pumps: (e = {}) => [
    { name: "name", label: "Pump / nozzle name", value: e.name, required: true, placeholder: "e.g. Pump 1 – Petrol" },
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
    if (entry && inUse(col, entry.id)) {
      const foot = document.querySelector(".overlay .sheet-foot");
      const b = document.createElement("button");
      b.type = "button"; b.className = "btn"; b.textContent = entry.archived ? "Reactivate" : "Make inactive";
      b.onclick = () => { store.update(col, entry.id, { archived: !entry.archived }); document.querySelector(".overlay")?.remove(); document.body.classList.remove("no-scroll"); redraw(); };
      foot.prepend(b);
    }
  };
  return { add: (_, r) => edit(null, r), edit: (id, r) => edit(store.get(col, id), r) };
}

const handlers = {
  products: masterHandlers("products"),
  pumps: masterHandlers("pumps"),
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
    set(productId, redraw) {
      const p = store.get("products", productId);
      openForm({
        title: `${p.name} price`,
        fields: [
          { name: "price", label: `Price per ${p.unit}`, type: "number", value: priceOn(productId, todayKey()), required: true },
          { name: "date", label: "Effective from", type: "date", value: todayKey(), required: true },
        ],
        onSubmit(v) {
          store.upsert("prices", (x) => x.productId === productId && x.date === v.date, { productId, date: v.date, price: num(v.price) });
          redraw();
        },
      });
    },
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
      const me = store.currentUser();
      openForm({
        title: u.name, fields: [
          { name: "name", label: "Name", value: u.name, required: true },
          { name: "role", label: "Role", type: "select", options: ROLES, value: u.role },
          { name: "password", label: "New password (leave blank to keep)", type: "password" },
          { name: "active", label: "Account", type: "select", value: u.active === false ? "no" : "yes", options: [{ value: "yes", label: "Active" }, { value: "no", label: "Disabled" }] },
        ],
        async onSubmit(v) {
          if (u.id === me.id && (v.role !== "owner" || v.active === "no")) throw new Error("You can't remove your own owner access.");
          const patch = { name: v.name, role: v.role, active: v.active === "yes" };
          if (v.password) { if (v.password.length < 6) throw new Error("Password must be at least 6 characters."); const c = await auth.credentials(u.username, v.password); patch.salt = c.salt; patch.hash = c.hash; }
          store.updateUser(id, patch); redraw();
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
