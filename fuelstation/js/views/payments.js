import * as store from "../store.js";
import { html, render, money, todayKey, shiftDate, fmtDate, round2, parseKey, dateKey } from "../ui.js";
import { nameOf } from "../calc.js";
import { customerPaymentForm, saleOnlineForm, expenseForm, settleExpenseForm } from "../forms.js";

const state = { range: "7", tab: "in", method: "all" };
const RANGES = [["1", "Today"], ["7", "7 days"], ["30", "30 days"], ["month", "This month"]];

function bounds() {
  const to = todayKey();
  if (state.range === "month") { const d = parseKey(to); d.setDate(1); return [dateKey(d), to]; }
  return [shiftDate(to, -(Number(state.range) - 1)), to];
}

export function mount(root) {
  const redraw = () => mount(root);
  root.onclick = (e) => {
    const t = e.target.closest("[data-act]");
    if (!t) return;
    const { act, id } = t.dataset;
    if (act === "range") state.range = id;
    else if (act === "tab") state.tab = id;
    else if (act === "method") state.method = id;
    else if (act === "edit-in") { const p = store.get("payments", id); return (p.kind === "sale" ? saleOnlineForm : customerPaymentForm)({ entry: p, done: redraw }); }
    else if (act === "edit-out") return expenseForm({ entry: store.get("expenses", id), done: redraw });
    else if (act === "settle") return settleExpenseForm({ entry: store.get("expenses", id), done: redraw });
    redraw();
  };
  const [from, to] = bounds();
  const inRange = (r) => r.date >= from && r.date <= to;
  const meth = (r) => state.method === "all" || r.method === state.method;

  const chip = (act, id, label, cur) => html`<button class="chip slim ${cur === id ? "on" : ""}" data-act="${act}" data-id="${id}">${label}</button>`;
  const rows = state.tab === "in"
    ? store.list("payments").filter((p) => inRange(p) && meth(p))
    : store.list("expenses").filter((e) => inRange(e) && (state.method === "all" || e.method === state.method || (state.method === "credit" && e.status === "credit")));
  rows.sort((a, b) => b.date.localeCompare(a.date) || b.createdAt - a.createdAt);

  // Totals by cash / each online source.
  const bySource = {};
  let total = 0;
  for (const r of rows) {
    if (r.status === "credit") continue;
    const k = r.method === "cash" ? "Cash" : nameOf("sources", r.sourceId);
    bySource[k] = round2((bySource[k] || 0) + r.amount);
    total = round2(total + r.amount);
  }
  const credit = state.tab === "out" ? round2(rows.filter((r) => r.status === "credit").reduce((t, r) => t + r.amount, 0)) : 0;

  render(root, html`
    <h2>Payment records</h2>
    <div class="seg"><button class="${state.tab === "in" ? "on" : ""}" data-act="tab" data-id="in">Received</button><button class="${state.tab === "out" ? "on" : ""}" data-act="tab" data-id="out">Expenses</button></div>
    <div class="chips">${RANGES.map(([k, l]) => chip("range", k, l, state.range))}</div>
    <div class="chips">${[["all", "All"], ["cash", "Cash"], ["online", "Online"], ...(state.tab === "out" ? [["credit", "On credit"]] : [])].map(([k, l]) => chip("method", k, l, state.method))}</div>
    <div class="card summary"><div class="kv total"><span>${state.tab === "in" ? "Total received" : "Total paid"}</span><b>${money(total)}</b></div>
      ${Object.entries(bySource).map(([k, v]) => html`<div class="kv"><span>${k}</span><b>${money(v)}</b></div>`)}
      ${credit ? html`<div class="kv"><span>Unpaid (on credit)</span><b class="neg">${money(credit)}</b></div>` : ""}</div>
    <div class="list">${rows.length ? rows.map((r) => state.tab === "in" ? html`
      <button class="row" data-act="edit-in" data-id="${r.id}">
        <span class="row-main">${r.kind === "sale" ? "Fuel sale" : nameOf("customers", r.customerId)}<small>${fmtDate(r.date)} · ${nameOf("shifts", r.shiftId)} · ${r.method === "cash" ? "Cash" : nameOf("sources", r.sourceId)}</small></span><b class="pos">${money(r.amount)}</b></button>` : html`
      <div class="row-wrap"><button class="row" data-act="edit-out" data-id="${r.id}">
        <span class="row-main">${nameOf("expenseTypes", r.typeId)}<small>${fmtDate(r.date)} · ${r.status === "credit" ? "On credit" : r.method === "cash" ? "Cash" : nameOf("sources", r.sourceId)}${r.payee ? " · " + r.payee : ""}</small></span><b class="neg">${money(r.amount)}</b></button>
        ${r.status === "credit" ? html`<button class="btn small" data-act="settle" data-id="${r.id}">Mark paid</button>` : ""}</div>`)
      : html`<p class="muted pad">No records for this filter.</p>`}</div>`);
}
