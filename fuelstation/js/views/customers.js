import * as store from "../store.js";
import { html, render, $, money, fmtDate, round2 } from "../ui.js";
import { active, nameOf, customerBalance, outstandingTotal } from "../calc.js";
import { creditForm, customerPaymentForm, customerForm } from "../forms.js";
import { todayKey } from "../ui.js";

let query = "";

export function mount(root, param) {
  const redraw = () => mount(root, param);
  root.onclick = (e) => {
    const t = e.target.closest("[data-act]");
    if (!t) return;
    const ctx = { date: todayKey(), shiftId: active("shifts")[0]?.id, customerId: param, done: redraw };
    switch (t.dataset.act) {
      case "new": return customerForm({ done: redraw });
      case "edit": return customerForm({ entry: store.get("customers", param), done: redraw });
      case "credit": return creditForm(ctx);
      case "pay": return customerPaymentForm(ctx);
      case "edit-credit": return creditForm({ ...ctx, entry: store.get("credits", t.dataset.id) });
      case "edit-pay": return customerPaymentForm({ ...ctx, entry: store.get("payments", t.dataset.id) });
      case "archive":
        store.update("customers", param, { archived: true }); location.hash = "#/customers"; return;
    }
  };
  root.oninput = null;
  param ? detail(root, param) : listView(root);
}

function listView(root) {
  const draw = () => {
    const rows = active("customers").filter((c) => c.name.toLowerCase().includes(query.toLowerCase()) || (c.vehicles || "").toLowerCase().includes(query.toLowerCase()))
      .map((c) => ({ c, bal: customerBalance(c.id) })).sort((a, b) => b.bal - a.bal);
    render($("#custList", root), html`${rows.length ? rows.map(({ c, bal }) => html`
      <a class="row" href="#/customers/${c.id}"><span class="row-main">${c.name}<small>${c.phone || c.vehicles || ""}</small></span>
        <b class="${bal > 0 ? "neg" : bal < 0 ? "pos" : ""}">${money(bal)}</b></a>`)
      : html`<p class="muted pad">${query ? "No match." : "No customers yet — add your first credit customer."}</p>`}`);
  };
  render(root, html`
    <div class="section-row"><h2>Customers</h2><button class="btn primary small" data-act="new">+ New</button></div>
    <div class="card stat warnbg"><span>Total outstanding</span><b>${money(outstandingTotal())}</b></div>
    <input class="search" id="search" type="search" placeholder="Search name or vehicle" value="${query}">
    <div class="list" id="custList"></div>`);
  draw();
  $("#search", root).oninput = (e) => { query = e.target.value; draw(); };
}

function detail(root, id) {
  const c = store.get("customers", id);
  if (!c) { render(root, html`<p class="empty">Customer not found. <a href="#/customers">Back</a></p>`); return; }
  const entries = [
    ...store.list("credits").filter((x) => x.customerId === id).map((x) => ({ ...x, type: "credit" })),
    ...store.list("payments").filter((x) => x.kind === "customer" && x.customerId === id).map((x) => ({ ...x, type: "pay" })),
  ].sort((a, b) => a.date.localeCompare(b.date) || a.createdAt - b.createdAt);
  let run = 0;
  const withBal = entries.map((x) => ({ ...x, bal: (run = round2(run + (x.type === "credit" ? x.amount : -x.amount))) })).reverse();
  const bal = customerBalance(id);
  render(root, html`
    <a class="back" href="#/customers">‹ Customers</a>
    <div class="card cust-head">
      <h2>${c.name}</h2><p class="muted">${[c.phone, c.vehicles].filter(Boolean).join(" · ")}</p>
      <div class="balance ${bal > 0 ? "neg" : "pos"}"><span>${bal > 0 ? "Owes you" : bal < 0 ? "Advance with you" : "Settled"}</span><b>${money(Math.abs(bal))}</b></div>
      ${c.creditLimit ? html`<small class="muted">Credit limit ${money(c.creditLimit)}${bal > c.creditLimit ? " — exceeded" : ""}</small>` : ""}
    </div>
    <div class="two-btn"><button class="btn primary" data-act="credit">+ Credit sale</button><button class="btn" data-act="pay">+ Payment</button></div>
    <h3 class="section">Statement</h3>
    <div class="list">${withBal.length ? withBal.map((x) => html`
      <button class="row" data-act="${x.type === "credit" ? "edit-credit" : "edit-pay"}" data-id="${x.id}">
        <span class="row-main">${x.type === "credit" ? "Credit" + (x.litres ? " · " + x.litres + " L " + nameOf("products", x.productId, "") : "") : "Payment · " + (x.method === "cash" ? "Cash" : nameOf("sources", x.sourceId))}
          <small>${fmtDate(x.date)}${x.vehicle ? " · " + x.vehicle : ""}${x.note ? " · " + x.note : ""}</small></span>
        <span class="amt"><b class="${x.type === "credit" ? "neg" : "pos"}">${x.type === "credit" ? "+" : "−"}${money(x.amount)}</b><small>bal ${money(x.bal)}</small></span></button>`)
      : html`<p class="muted pad">No transactions yet.</p>`}</div>
    <div class="two-btn"><button class="btn small" data-act="edit">Edit details</button>${bal === 0 ? html`<button class="btn small danger" data-act="archive">Archive</button>` : ""}</div>`);
}
