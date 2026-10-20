// Entry forms shared by the Daily, Customer and Payments screens.
import * as store from "./store.js";
import { openForm, opts, num, round2, todayKey, toast, money } from "./ui.js";
import { active, priceOn, customerBalance } from "./calc.js";

const METHODS = [{ value: "cash", label: "Cash" }, { value: "online", label: "Online" }];

const shiftField = (v) => ({ name: "shiftId", label: "Shift", type: "select", options: opts(active("shifts")), value: v });
const dateField = (v) => ({ name: "date", label: "Date", type: "date", value: v || todayKey(), required: true });
const methodFields = (e = {}) => [
  { name: "method", label: "Paid by", type: "select", options: METHODS, value: e.method || "cash" },
  { name: "sourceId", label: "Online source", type: "select", value: e.sourceId, required: true,
    options: opts(active("sources")), showIf: (v) => v.method === "online" },
];
const cleanSource = (v) => (v.method === "online" ? v.sourceId : null);

function needCustomers() {
  if (!active("customers").length) { toast("Add a customer first."); return true; }
  return false;
}

function save(col, entry, data) {
  if (entry) store.update(col, entry.id, data); else store.add(col, data);
}

export function creditForm({ date, shiftId, customerId, entry, done }) {
  if (needCustomers()) return;
  const fuels = active("products");
  const e = entry || {};
  const rateFor = (pid, d) => priceOn(pid, d) ?? "";
  const pid0 = e.productId || fuels[0]?.id;
  openForm({
    title: entry ? "Edit credit sale" : "Credit sale",
    note: "Fuel or goods given on credit — added to the customer's balance.",
    fields: [
      { name: "customerId", label: "Customer", type: "select", options: opts(active("customers")), value: e.customerId || customerId, required: true },
      dateField(e.date || date), shiftField(e.shiftId || shiftId),
      { name: "productId", label: "Product", type: "select", options: opts(fuels), value: pid0 },
      { name: "litres", label: "Quantity (litres)", type: "number", value: e.litres },
      { name: "rate", label: "Rate", type: "number", value: e.rate ?? rateFor(pid0, e.date || date) },
      { name: "amount", label: "Amount", type: "number", value: e.amount, required: true },
      { name: "vehicle", label: "Vehicle no.", value: e.vehicle },
      { name: "note", label: "Note", value: e.note },
    ],
    onChange(v, set, changed) {
      if (changed === "productId" || changed === "date") set("rate", rateFor(v.productId, v.date));
      if (["productId", "date", "litres", "rate"].includes(changed) && v.litres) {
        const rate = changed === "rate" || changed === "litres" ? v.rate : rateFor(v.productId, v.date);
        set("amount", round2(num(v.litres) * num(rate)));
      }
    },
    onSubmit(v) {
      const c = store.get("customers", v.customerId);
      const projected = customerBalance(v.customerId) - (entry && entry.customerId === v.customerId ? entry.amount : 0) + num(v.amount);
      save("credits", entry, { ...v, amount: num(v.amount) });
      if (c.creditLimit && projected > c.creditLimit) toast(`Over credit limit (${money(c.creditLimit)})`);
      done?.();
    },
    onDelete: entry && (() => { store.remove("credits", entry.id); done?.(); }),
  });
}

export function customerPaymentForm({ date, shiftId, customerId, entry, done }) {
  if (needCustomers()) return;
  const e = entry || {};
  openForm({
    title: entry ? "Edit payment" : "Payment received",
    note: "Money received from a customer — reduces their balance.",
    fields: [
      { name: "customerId", label: "Customer", type: "select", options: opts(active("customers")), value: e.customerId || customerId, required: true },
      dateField(e.date || date), shiftField(e.shiftId || shiftId),
      { name: "amount", label: "Amount", type: "number", value: e.amount, required: true },
      ...methodFields(e),
      { name: "note", label: "Reference / note", value: e.note },
    ],
    onSubmit(v) {
      save("payments", entry, { ...v, kind: "customer", amount: num(v.amount), sourceId: cleanSource(v) });
      done?.();
    },
    onDelete: entry && (() => { store.remove("payments", entry.id); done?.(); }),
  });
}

export function saleOnlineForm({ date, shiftId, entry, done }) {
  const e = entry || {};
  openForm({
    title: entry ? "Edit online collection" : "Online collection",
    note: "Fuel sales paid digitally at the pump (UPI, card, fleet card…). Cash is worked out for you.",
    fields: [
      dateField(e.date || date), shiftField(e.shiftId || shiftId),
      { name: "sourceId", label: "Source", type: "select", options: opts(active("sources")), value: e.sourceId, required: true },
      { name: "amount", label: "Amount", type: "number", value: e.amount, required: true },
      { name: "note", label: "Note", value: e.note },
    ],
    onSubmit(v) { save("payments", entry, { ...v, kind: "sale", method: "online", amount: num(v.amount) }); done?.(); },
    onDelete: entry && (() => { store.remove("payments", entry.id); done?.(); }),
  });
}

export function expenseForm({ date, shiftId, entry, done }) {
  if (!active("expenseTypes").length) { toast("Add an expense type in Setup first."); return; }
  const e = entry || {};
  const [m, s] = methodFields(e);
  openForm({
    title: entry ? "Edit expense" : "Add expense",
    fields: [
      dateField(e.date || date), shiftField(e.shiftId || shiftId),
      { name: "typeId", label: "Expense type", type: "select", options: opts(active("expenseTypes")), value: e.typeId },
      { name: "amount", label: "Amount", type: "number", value: e.amount, required: true },
      { name: "status", label: "Status", type: "select", value: e.status || "paid",
        options: [{ value: "paid", label: "Paid" }, { value: "credit", label: "On credit (pay later)" }] },
      { name: "payee", label: "Paid to / vendor", value: e.payee },
      { ...m, showIf: (v) => v.status === "paid" },
      { ...s, showIf: (v) => v.status === "paid" && v.method === "online" },
      { name: "note", label: "Note", value: e.note },
    ],
    onSubmit(v) {
      const paid = v.status === "paid";
      save("expenses", entry, { ...v, amount: num(v.amount), method: paid ? v.method : null, sourceId: paid ? cleanSource(v) : null });
      done?.();
    },
    onDelete: entry && (() => { store.remove("expenses", entry.id); done?.(); }),
  });
}

export function settleExpenseForm({ entry, done }) {
  openForm({
    title: "Mark expense as paid",
    note: `${money(entry.amount)}${entry.payee ? " to " + entry.payee : ""}`,
    fields: [dateField(todayKey()), ...methodFields({})],
    onSubmit(v) {
      store.update("expenses", entry.id, { status: "paid", method: v.method, sourceId: cleanSource(v), paidOn: v.date });
      done?.();
    },
  });
}

export function customerForm({ entry, done }) {
  const e = entry || {};
  openForm({
    title: entry ? "Edit customer" : "New customer",
    fields: [
      { name: "name", label: "Name / company", value: e.name, required: true },
      { name: "phone", label: "Phone", type: "tel", value: e.phone },
      { name: "vehicles", label: "Vehicle numbers", value: e.vehicles, placeholder: "e.g. MH12 AB 1234, MH12 CD 5678" },
      { name: "creditLimit", label: "Credit limit (optional)", type: "number", value: e.creditLimit },
      { name: "note", label: "Note", value: e.note },
    ],
    onSubmit(v) { const rec = entry ? store.update("customers", entry.id, v) : store.add("customers", v); done?.(rec); },
  });
}
