import * as store from "../store.js";
import { html, render, money, qty, todayKey, shiftDate, fmtDate, parseKey, dateKey } from "../ui.js";
import { active, nameOf, totals, daysBetween, productMix, paymentMix, expenseMix, salesByShift, ageing } from "../calc.js";

const state = { range: "30" };
const RANGES = [["7", "7 days"], ["30", "30 days"], ["90", "90 days"], ["month", "This month"]];

function bounds() {
  const to = todayKey();
  if (state.range === "month") { const d = parseKey(to); d.setDate(1); return [dateKey(d), to]; }
  return [shiftDate(to, -(Number(state.range) - 1)), to];
}

// Horizontal bars from {label: value}.
function hbars(obj, fmt = money, cls = "") {
  const rows = Object.entries(obj).filter(([, v]) => v > 0).sort((a, b) => b[1] - a[1]);
  if (!rows.length) return html`<p class="muted pad">No data in this period.</p>`;
  const max = rows[0][1], total = rows.reduce((t, [, v]) => t + v, 0);
  return html`<div class="hbars">${rows.map(([k, v]) => html`
    <div class="hbar"><div class="hbar-top"><span>${k}</span><b>${fmt(v)} <small>${Math.round((v / total) * 100)}%</small></b></div>
      <div class="hbar-track"><i class="${cls}" style="width:${Math.max(2, Math.round((v / max) * 100))}%"></i></div></div>`)}</div>`;
}

export function mount(root) {
  root.onclick = (e) => {
    const t = e.target.closest("[data-range]");
    if (t) { state.range = t.dataset.range; mount(root); }
  };
  const [from, to] = bounds();
  const days = daysBetween(from, to).map((d) => ({ d, t: totals(d) }));
  const sum = (f) => days.reduce((a, x) => a + f(x.t), 0);
  const sales = sum((t) => t.fuelSales), exp = sum((t) => t.expensesTotal), litres = sum((t) => t.litres);
  const collected = sum((t) => t.totalCollected);
  const trackedDays = days.filter((x) => x.t.fuelSales > 0).length;

  const mix = productMix(from, to);
  const prodLitres = {}, prodSales = {};
  for (const [pid, v] of Object.entries(mix)) { prodLitres[nameOf("products", pid)] = v.litres; prodSales[nameOf("products", pid)] = v.amount; }
  const byShift = {};
  for (const [sid, v] of Object.entries(salesByShift(from, to))) byShift[nameOf("shifts", sid)] = v;
  const age = ageing(to);
  const ageTotal = age.buckets.reduce((t, b) => t + b.amount, 0);

  // Bar chart: thin to ~30 bars for long ranges by grouping into weeks.
  const grouped = days.length > 31
    ? Array.from({ length: Math.ceil(days.length / 7) }, (_, i) => {
        const chunk = days.slice(i * 7, i * 7 + 7);
        return { label: fmtDate(chunk[0].d, { day: "numeric", month: "short" }), v: chunk.reduce((a, x) => a + x.t.fuelSales, 0) };
      })
    : days.map((x) => ({ label: fmtDate(x.d, { day: "numeric" }), v: x.t.fuelSales }));
  const max = Math.max(1, ...grouped.map((g) => g.v));

  render(root, html`
    <h2>Dashboard</h2>
    <div class="chips">${RANGES.map(([k, l]) => html`<button class="chip slim ${state.range === k ? "on" : ""}" data-range="${k}">${l}</button>`)}</div>
    <div class="grid2">
      <div class="card stat hero"><span>Sales</span><b>${money(sales)}</b><small>${qty(litres)} L · avg ${money(trackedDays ? sales / trackedDays : 0)}/day</small></div>
      <div class="card stat"><span>Collected</span><b>${money(collected)}</b><small>cash + online</small></div>
      <div class="card stat"><span>Expenses</span><b>${money(exp)}</b></div>
      <div class="card stat"><span>Sales − expenses</span><b class="${sales - exp < 0 ? "neg" : "pos"}">${money(sales - exp)}</b></div>
    </div>

    <h3 class="section">Sales trend ${grouped.length > 31 || days.length > 31 ? html`<span class="muted">weekly</span>` : html`<span class="muted">daily</span>`}</h3>
    <div class="card"><div class="bars">${grouped.map((g) => html`
      <div class="bar" title="${g.label}: ${money(g.v)}"><i style="height:${Math.round((g.v / max) * 100)}%"></i>${grouped.length <= 14 ? html`<span>${g.label}</span>` : ""}</div>`)}</div>
      <div class="axis"><span>${fmtDate(from, { day: "numeric", month: "short" })}</span><span>peak ${money(max === 1 ? 0 : max)}</span><span>${fmtDate(to, { day: "numeric", month: "short" })}</span></div></div>

    <h3 class="section">Product mix · litres</h3>
    <div class="card">${hbars(prodLitres, (v) => qty(v) + " L")}</div>
    <h3 class="section">Product mix · sales</h3>
    <div class="card">${hbars(prodSales)}</div>
    <h3 class="section">Payment mix</h3>
    <div class="card">${hbars(paymentMix(from, to), money, "alt")}</div>
    <h3 class="section">Sales by shift</h3>
    <div class="card">${hbars(byShift)}</div>
    <h3 class="section">Expenses by type</h3>
    <div class="card">${hbars(expenseMix(from, to), money, "warnbar")}</div>

    <h3 class="section">Customer ageing <span class="muted">${money(ageTotal)} outstanding</span></h3>
    <div class="card"><div class="ageing">${age.buckets.map((b, i) => html`
      <div class="age-cell a${i}"><small>${b.label}</small><b>${money(b.amount)}</b></div>`)}</div></div>
    ${age.byCustomer.length ? html`<div class="list">${age.byCustomer.slice(0, 8).map((x) => html`
      <a class="row" href="#/customers/${x.customer.id}"><span class="row-main">${x.customer.name}<small>oldest unpaid ${x.oldest} day${x.oldest === 1 ? "" : "s"}</small></span>
        <b class="${x.oldest > 60 ? "neg" : ""}">${money(x.owed)}</b></a>`)}</div>` : ""}`);
}
