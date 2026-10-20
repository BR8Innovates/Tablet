import * as store from "../store.js";
import { html, render, $, $$, money, qty, num, round2, todayKey, shiftDate, fmtDate } from "../ui.js";
import { active, nameOf, priceOn, previousClosing, readingLitres, totals, liveNozzles, nozzleLabel } from "../calc.js";
import { creditForm, customerPaymentForm, saleOnlineForm, expenseForm, settleExpenseForm } from "../forms.js";

// Screen state survives re-renders (and navigating away and back within the session).
const state = { date: todayKey(), shiftId: null, tab: "sales" };

const TABS = [["sales", "Sales"], ["customers", "Customers"], ["expenses", "Expenses"], ["summary", "Summary"]];
const hhmm = (t) => t;

export function mount(root) {
  const shifts = active("shifts");
  if (!shifts.find((s) => s.id === state.shiftId)) state.shiftId = shifts[0]?.id;

  const redraw = () => draw(root);
  root.onclick = (e) => {
    const t = e.target.closest("[data-act]");
    if (!t) return;
    const { act, id } = t.dataset;
    const ctx = { date: state.date, shiftId: state.shiftId, done: redraw };
    const find = (col) => store.get(col, id);
    switch (act) {
      case "prev": state.date = shiftDate(state.date, -1); return redraw();
      case "next": state.date = shiftDate(state.date, 1); return redraw();
      case "today": state.date = todayKey(); return redraw();
      case "shift": state.shiftId = id; return redraw();
      case "tab": state.tab = id; return redraw();
      case "add-online": return saleOnlineForm(ctx);
      case "edit-online": return saleOnlineForm({ ...ctx, entry: find("payments") });
      case "add-credit": return creditForm(ctx);
      case "edit-credit": return creditForm({ ...ctx, entry: find("credits") });
      case "add-pay": return customerPaymentForm(ctx);
      case "edit-pay": return customerPaymentForm({ ...ctx, entry: find("payments") });
      case "add-exp": return expenseForm(ctx);
      case "edit-exp": return expenseForm({ ...ctx, entry: find("expenses") });
      case "settle": return settleExpenseForm({ entry: find("expenses"), done: redraw });
    }
  };
  root.onchange = (e) => {
    if (e.target.id === "datePick" && e.target.value) { state.date = e.target.value; redraw(); }
    else if (e.target.matches("[data-meter]")) saveReading(e.target.closest("[data-nozzle]"));
    else if (e.target.id === "cashCounted") saveClosing(e.target.value);
  };
  root.oninput = (e) => {
    if (e.target.matches("[data-meter]")) liveReading(e.target.closest("[data-nozzle]"));
  };
  draw(root);
}

// ---------- layout ----------
function draw(root) {
  const shifts = active("shifts");
  const isToday = state.date === todayKey();
  render(root, html`
    <div class="daybar">
      <button class="icon-btn" data-act="prev" aria-label="Previous day">‹</button>
      <label class="datepick"><span>${fmtDate(state.date, { weekday: "long", day: "numeric", month: "long" })}${isToday ? " · Today" : ""}</span>
        <input type="date" id="datePick" value="${state.date}"></label>
      <button class="icon-btn" data-act="next" aria-label="Next day">›</button>
      ${isToday ? "" : html`<button class="btn small" data-act="today">Today</button>`}
    </div>
    <div class="chips" role="tablist" aria-label="Shift">
      ${shifts.map((s) => html`<button class="chip ${s.id === state.shiftId ? "on" : ""}" data-act="shift" data-id="${s.id}">${s.name}<small>${hhmm(s.start)}–${hhmm(s.end)}</small></button>`)}
    </div>
    <div class="seg" role="tablist">
      ${TABS.map(([k, label]) => html`<button class="${state.tab === k ? "on" : ""}" data-act="tab" data-id="${k}">${label}</button>`)}
    </div>
    <div id="dailyBody">${body()}</div>`);
}

function body() {
  switch (state.tab) {
    case "sales": return salesTab();
    case "customers": return customersTab();
    case "expenses": return expensesTab();
    default: return summaryTab();
  }
}

const inShift = (r) => r.date === state.date && r.shiftId === state.shiftId;

// ---------- sales (meter readings + online collections) ----------
function salesTab() {
  const nozzles = liveNozzles();
  const online = store.list("payments").filter((p) => p.kind === "sale" && inShift(p));
  if (!nozzles.length) return html`<div class="empty">No nozzles yet. <a href="#/setup/pumps">Add a pump and its nozzles in Setup</a> to start recording meter readings.</div>`;
  return html`
    <h3 class="section">Meter readings</h3>
    <div class="stack">${nozzles.map(nozzleCard)}</div>
    <div class="section-row"><h3 class="section">Online collections</h3><button class="btn small" data-act="add-online">+ Add</button></div>
    <div class="list">${online.length ? online.map((p) => html`
      <button class="row" data-act="edit-online" data-id="${p.id}">
        <span class="row-main">${nameOf("sources", p.sourceId)}<small>${p.note || ""}</small></span><b>${money(p.amount)}</b></button>`)
      : html`<p class="muted pad">Nothing yet. Add UPI / card / fleet-card amounts collected this shift.</p>`}</div>
    <div id="shiftSummary">${shiftSummary()}</div>`;
}

function nozzleCard(pump) {
  const rec = store.list("readings").find((r) => r.nozzleId === pump.id && inShift(r));
  const prev = previousClosing(pump.id, state.date, state.shiftId);
  const opening = rec ? rec.opening : prev ?? "";
  const price = priceOn(pump.productId, state.date);
  return html`
    <div class="card pump" data-nozzle="${pump.id}" data-price="${price ?? ""}">
      <div class="pump-head"><b>${nozzleLabel(pump)}</b><span class="badge">${nameOf("products", pump.productId)}</span>
        <span class="muted">${price == null ? html`<a href="#/setup/prices">Set today's price</a>` : money(price) + "/" + (store.get("products", pump.productId)?.unit || "L")}</span></div>
      <div class="meters">
        <label class="field"><span>Opening</span><input data-meter name="opening" type="number" inputmode="decimal" step="any" min="0" value="${opening}"></label>
        <label class="field"><span>Closing</span><input data-meter name="closing" type="number" inputmode="decimal" step="any" min="0" value="${rec?.closing ?? ""}"></label>
      </div>
      <div class="pump-out"><span data-out="litres">${qty(rec ? readingLitres(rec) : 0)} L</span><b data-out="amount">${money(rec && price ? readingLitres(rec) * price : 0)}</b></div>
      <p class="warn" data-out="warn" hidden>Closing is lower than opening.</p>
    </div>`;
}

function liveReading(card) {
  const opening = num($("[name=opening]", card).value), closingEl = $("[name=closing]", card);
  const closing = num(closingEl.value), price = num(card.dataset.price);
  const litres = Math.max(0, closing - opening);
  $("[data-out=litres]", card).textContent = qty(litres) + " L";
  $("[data-out=amount]", card).textContent = money(litres * price);
  $("[data-out=warn]", card).hidden = !(closingEl.value !== "" && closing < opening);
}

function saveReading(card) {
  const nozzleId = card.dataset.nozzle;
  const o = $("[name=opening]", card).value, c = $("[name=closing]", card).value;
  const match = (r) => r.nozzleId === nozzleId && inShift(r);
  // Nothing to keep until a closing meter is entered.
  store.upsert("readings", match, c === "" ? null : { date: state.date, shiftId: state.shiftId, nozzleId, opening: num(o), closing: num(c) });
  liveReading(card);
  const s = $("#shiftSummary");
  if (s) render(s, shiftSummary());
}

function shiftSummary() {
  return summaryCard(`${nameOf("shifts", state.shiftId)} shift`, totals(state.date, state.shiftId));
}

function summaryCard(title, t) {
  const line = (label, v, cls = "") => html`<div class="kv ${cls}"><span>${label}</span><b>${money(v)}</b></div>`;
  return html`<div class="card summary"><h3>${title}</h3>
    ${line("Fuel sales", t.fuelSales)}${line("− Online received", t.online)}${line("− Credit given", t.creditGiven)}
    ${line("= Cash from sales", t.cashFromSales, "sub")}
    ${line("+ Cash from customers", t.custCash)}${line("− Cash expenses", t.expCash)}
    ${line("Expected cash in hand", t.expectedCash, "total")}</div>`;
}

// ---------- customers (credit + payments) ----------
function customersTab() {
  const credits = store.list("credits").filter(inShift);
  const pays = store.list("payments").filter((p) => p.kind === "customer" && inShift(p));
  const t = totals(state.date, state.shiftId);
  return html`
    <div class="two-btn"><button class="btn primary" data-act="add-credit">+ Credit sale</button><button class="btn" data-act="add-pay">+ Payment received</button></div>
    <h3 class="section">Credit given <span class="muted">${money(t.creditGiven)}</span></h3>
    <div class="list">${credits.length ? credits.map((c) => html`
      <button class="row" data-act="edit-credit" data-id="${c.id}">
        <span class="row-main">${nameOf("customers", c.customerId)}<small>${[c.litres ? qty(c.litres) + " L " + nameOf("products", c.productId, "") : "", c.vehicle].filter(Boolean).join(" · ")}</small></span>
        <b class="neg">${money(c.amount)}</b></button>`) : html`<p class="muted pad">No credit sales this shift.</p>`}</div>
    <h3 class="section">Payments received <span class="muted">${money(t.custCash + t.custOnline)}</span></h3>
    <div class="list">${pays.length ? pays.map((p) => html`
      <button class="row" data-act="edit-pay" data-id="${p.id}">
        <span class="row-main">${nameOf("customers", p.customerId)}<small>${p.method === "cash" ? "Cash" : "Online · " + nameOf("sources", p.sourceId)}${p.note ? " · " + p.note : ""}</small></span>
        <b class="pos">${money(p.amount)}</b></button>`) : html`<p class="muted pad">No customer payments this shift.</p>`}</div>`;
}

// ---------- expenses ----------
function expensesTab() {
  const exps = store.list("expenses").filter(inShift);
  const t = totals(state.date, state.shiftId);
  return html`
    <div class="two-btn"><button class="btn primary" data-act="add-exp">+ Add expense</button></div>
    <h3 class="section">Expenses <span class="muted">${money(t.expensesTotal)}</span></h3>
    <div class="list">${exps.length ? exps.map((e) => html`
      <div class="row-wrap">
        <button class="row" data-act="edit-exp" data-id="${e.id}">
          <span class="row-main">${nameOf("expenseTypes", e.typeId)}<small>${[e.payee, e.status === "credit" ? "On credit" : e.method === "cash" ? "Cash" : "Online · " + nameOf("sources", e.sourceId), e.note].filter(Boolean).join(" · ")}</small></span>
          <b class="neg">${money(e.amount)}</b></button>
        ${e.status === "credit" ? html`<button class="btn small" data-act="settle" data-id="${e.id}">Mark paid</button>` : ""}
      </div>`) : html`<p class="muted pad">No expenses this shift.</p>`}</div>`;
}

// ---------- day summary + cash reconciliation ----------
function saveClosing(v) {
  store.upsert("closings", (c) => c.date === state.date, v === "" ? null : { date: state.date, cashCounted: num(v) });
  draw($("#view"));
}

function summaryTab() {
  const day = totals(state.date);
  const closing = store.list("closings").find((c) => c.date === state.date);
  const diff = closing ? round2(closing.cashCounted - day.expectedCash) : null;
  return html`
    ${active("shifts").map((s) => {
      const t = totals(state.date, s.id);
      return html`<div class="card summary compact"><h3>${s.name}</h3>
        <div class="kv"><span>Sales</span><b>${money(t.fuelSales)}</b></div>
        <div class="kv"><span>Online / Credit</span><b>${money(t.online)} / ${money(t.creditGiven)}</b></div>
        <div class="kv"><span>Expected cash</span><b>${money(t.expectedCash)}</b></div></div>`;
    })}
    ${summaryCard("Whole day", day)}
    <div class="card"><label class="field"><span>Cash actually counted</span>
      <input id="cashCounted" type="number" inputmode="decimal" step="any" min="0" value="${closing?.cashCounted ?? ""}" placeholder="Enter closing cash"></label>
      ${diff === null ? "" : html`<div class="kv total ${diff === 0 ? "" : diff < 0 ? "neg" : "pos"}"><span>${diff === 0 ? "Cash matches" : diff < 0 ? "Short" : "Excess"}</span><b>${money(Math.abs(diff))}</b></div>`}
    </div>
    <div class="grid2">
      <div class="card stat"><span>Litres sold</span><b>${qty(day.litres)} L</b></div>
      <div class="card stat"><span>Expenses</span><b>${money(day.expensesTotal)}</b></div>
      <div class="card stat"><span>Customer payments</span><b>${money(day.custCash + day.custOnline)}</b></div>
      <div class="card stat"><span>Unpaid expenses</span><b>${money(day.expCredit)}</b></div>
    </div>`;
}
