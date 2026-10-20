import * as store from "../store.js";
import { html, render, money, qty, todayKey, shiftDate, fmtDate } from "../ui.js";
import { active, nameOf, priceOn, totals, litresByProduct, customerBalance, outstandingTotal } from "../calc.js";

export function mount(root) {
  const today = todayKey();
  const t = totals(today);
  const litres = litresByProduct(today);
  const fuels = active("products").filter((p) => p.category === "Fuel" || p.category === "Gas" || litres[p.id]);
  const missing = fuels.filter((p) => priceOn(p.id, today) == null);
  const debtors = active("customers").map((c) => ({ c, bal: customerBalance(c.id) }))
    .filter((x) => x.bal > 0).sort((a, b) => b.bal - a.bal).slice(0, 5);
  const days = Array.from({ length: 7 }, (_, i) => shiftDate(today, i - 6)).map((d) => ({ d, v: totals(d).fuelSales }));
  const max = Math.max(1, ...days.map((x) => x.v));

  render(root, html`
    <p class="greet">Hello, ${store.currentUser().name.split(" ")[0]} 👋 <span class="muted">${fmtDate(today)}</span></p>
    ${missing.length ? html`<a class="alert" href="#/setup/prices">⚠ No price set today for ${missing.map((p) => p.name).join(", ")} — tap to set</a>` : ""}
    <div class="grid2">
      <div class="card stat hero"><span>Today's sales</span><b>${money(t.fuelSales)}</b><small>${qty(t.litres)} L sold</small></div>
      <div class="card stat"><span>Expected cash</span><b>${money(t.expectedCash)}</b><small>after expenses</small></div>
      <div class="card stat"><span>Online</span><b>${money(t.online + t.custOnline)}</b></div>
      <div class="card stat"><span>Credit given</span><b>${money(t.creditGiven)}</b></div>
      <div class="card stat"><span>Expenses</span><b>${money(t.expensesTotal)}</b></div>
      <div class="card stat warnbg"><span>Total outstanding</span><b>${money(outstandingTotal())}</b><small>owed by customers</small></div>
    </div>
    <div class="two-btn"><a class="btn primary" href="#/daily">Open today's entry</a><a class="btn" href="#/customers">Customers</a></div>

    <h3 class="section">Last 7 days · sales</h3>
    <div class="card"><div class="bars">${days.map((x) => html`
      <div class="bar"><i style="height:${Math.round((x.v / max) * 100)}%"></i><span>${fmtDate(x.d, { weekday: "narrow" })}</span><small>${x.v ? Math.round(x.v / 1000) + "k" : ""}</small></div>`)}</div></div>

    ${fuels.length ? html`<h3 class="section">Today's prices</h3>
    <div class="card"><div class="kvs">${fuels.map((p) => html`<div class="kv"><span>${p.name}</span><b>${priceOn(p.id, today) == null ? "—" : money(priceOn(p.id, today))}</b></div>`)}</div></div>` : ""}

    ${debtors.length ? html`<h3 class="section">Top outstanding</h3>
    <div class="list">${debtors.map((x) => html`<a class="row" href="#/customers/${x.c.id}"><span class="row-main">${x.c.name}</span><b class="neg">${money(x.bal)}</b></a>`)}</div>` : ""}`);
}
