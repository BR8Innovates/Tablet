// Business rules shared by every screen (and the future dashboards).
import { list, get } from "./store.js";
import { num, round2 } from "./ui.js";

export const active = (col) => list(col).filter((r) => !r.archived);
export const nameOf = (col, id, fallback = "—") => get(col, id)?.name || fallback;

const shiftIndex = (shiftId) => list("shifts").findIndex((s) => s.id === shiftId);

// Latest price for a product on or before `date`.
export function priceOn(productId, date) {
  let best = null;
  for (const p of list("prices")) {
    if (p.productId !== productId || p.date > date) continue;
    if (!best || p.date >= best.date) best = p;
  }
  return best ? best.price : null;
}

// Closing meter of the reading that immediately precedes (date, shift) for a pump.
export function previousClosing(pumpId, date, shiftId) {
  const cur = shiftIndex(shiftId);
  let best = null, bestKey = "";
  for (const r of list("readings")) {
    if (r.pumpId !== pumpId) continue;
    const idx = shiftIndex(r.shiftId);
    if (r.date > date || (r.date === date && idx >= cur)) continue;
    const key = r.date + String(idx).padStart(3, "0");
    if (key > bestKey) { best = r; bestKey = key; }
  }
  return best ? best.closing : null;
}

export function readingLitres(r) { return Math.max(0, num(r.closing) - num(r.opening)); }

export function readingAmount(r) {
  const pump = get("pumps", r.pumpId);
  const price = pump ? priceOn(pump.productId, r.date) : null;
  return round2(readingLitres(r) * (price || 0));
}

const sum = (arr, f) => round2(arr.reduce((t, x) => t + f(x), 0));

// Money position for a date, optionally for a single shift.
export function totals(date, shiftId = null) {
  const inScope = (r) => r.date === date && (!shiftId || r.shiftId === shiftId);
  const readings = list("readings").filter(inScope);
  const payments = list("payments").filter(inScope);
  const credits = list("credits").filter(inScope);
  const expenses = list("expenses").filter(inScope);
  // Cash/online leaves on the day it was actually paid (a credit expense settled later moves to that day).
  const paidScope = (e) => e.status !== "credit" && (e.paidOn
    ? e.paidOn === date && !shiftId
    : e.date === date && (!shiftId || e.shiftId === shiftId));
  const paidExpenses = list("expenses").filter(paidScope);

  const fuelSales = sum(readings, readingAmount);
  const litres = sum(readings, readingLitres);
  const online = sum(payments.filter((p) => p.kind === "sale"), (p) => p.amount);
  const creditGiven = sum(credits, (c) => c.amount);
  const custCash = sum(payments.filter((p) => p.kind === "customer" && p.method === "cash"), (p) => p.amount);
  const custOnline = sum(payments.filter((p) => p.kind === "customer" && p.method === "online"), (p) => p.amount);
  const expCash = sum(paidExpenses.filter((e) => e.method === "cash"), (e) => e.amount);
  const expOnline = sum(paidExpenses.filter((e) => e.method === "online"), (e) => e.amount);
  const expCredit = sum(expenses.filter((e) => e.status === "credit"), (e) => e.amount);
  const expensesAccrued = sum(expenses, (e) => e.amount);

  const cashFromSales = round2(fuelSales - online - creditGiven);
  return {
    fuelSales, litres, online, creditGiven, cashFromSales, custCash, custOnline,
    expCash, expOnline, expCredit, expensesTotal: expensesAccrued,
    expectedCash: round2(cashFromSales + custCash - expCash),
    totalCollected: round2(fuelSales - creditGiven + custCash + custOnline),
  };
}

export function litresByProduct(date) {
  const out = {};
  for (const r of list("readings").filter((x) => x.date === date)) {
    const pid = get("pumps", r.pumpId)?.productId;
    if (pid) out[pid] = round2((out[pid] || 0) + readingLitres(r));
  }
  return out;
}

export function customerBalance(customerId) {
  const credit = sum(list("credits").filter((c) => c.customerId === customerId), (c) => c.amount);
  const paid = sum(list("payments").filter((p) => p.kind === "customer" && p.customerId === customerId), (p) => p.amount);
  return round2(credit - paid);
}

export const outstandingTotal = () => round2(list("customers").reduce((t, c) => t + Math.max(0, customerBalance(c.id)), 0));

// ---------- range analytics (dashboards) ----------
import { shiftDate, parseKey } from "./ui.js";

export function daysBetween(from, to) {
  const out = [];
  for (let d = from; d <= to; d = shiftDate(d, 1)) out.push(d);
  return out;
}

// Litres and sales amount per product over [from, to].
export function productMix(from, to) {
  const out = {};
  for (const r of list("readings")) {
    if (r.date < from || r.date > to) continue;
    const pid = get("pumps", r.pumpId)?.productId;
    if (!pid) continue;
    const o = (out[pid] ||= { litres: 0, amount: 0 });
    o.litres = round2(o.litres + readingLitres(r));
    o.amount = round2(o.amount + readingAmount(r));
  }
  return out;
}

// Received money split by Cash / each online source / credit given.
export function paymentMix(from, to) {
  const out = {};
  const bump = (k, v) => { out[k] = round2((out[k] || 0) + v); };
  const inR = (r) => r.date >= from && r.date <= to;
  for (const p of list("payments").filter(inR)) bump(p.method === "cash" ? "Cash" : nameOf("sources", p.sourceId), p.amount);
  for (const d of daysBetween(from, to)) {
    const t = totals(d);
    bump("Cash", t.cashFromSales);
    bump("On credit", t.creditGiven);
  }
  // Online fuel collections were already counted as payments above.
  return out;
}

export function expenseMix(from, to) {
  const out = {};
  for (const e of list("expenses")) {
    if (e.date < from || e.date > to) continue;
    const k = nameOf("expenseTypes", e.typeId);
    out[k] = round2((out[k] || 0) + e.amount);
  }
  return out;
}

export function salesByShift(from, to) {
  const out = {};
  for (const r of list("readings")) {
    if (r.date < from || r.date > to) continue;
    out[r.shiftId] = round2((out[r.shiftId] || 0) + readingAmount(r));
  }
  return out;
}

// Outstanding credit by age. Each customer's payments are applied to their oldest credits first.
export const AGE_BUCKETS = [["0–30 days", 30], ["31–60 days", 60], ["61–90 days", 90], ["90+ days", Infinity]];
export function ageing(today) {
  const buckets = AGE_BUCKETS.map(([label]) => ({ label, amount: 0 }));
  const byCustomer = [];
  for (const c of list("customers")) {
    let paid = list("payments").filter((p) => p.kind === "customer" && p.customerId === c.id).reduce((t, p) => t + p.amount, 0);
    const credits = list("credits").filter((x) => x.customerId === c.id).sort((a, b) => a.date.localeCompare(b.date));
    let oldest = null, owed = 0;
    for (const cr of credits) {
      const applied = Math.min(paid, cr.amount);
      paid -= applied;
      const left = round2(cr.amount - applied);
      if (left <= 0) continue;
      const age = Math.round((parseKey(today) - parseKey(cr.date)) / 86400000);
      buckets[AGE_BUCKETS.findIndex(([, max]) => age <= max)].amount += left;
      owed += left;
      oldest ??= age;
    }
    if (owed > 0) byCustomer.push({ customer: c, owed: round2(owed), oldest });
  }
  buckets.forEach((b) => { b.amount = round2(b.amount); });
  return { buckets, byCustomer: byCustomer.sort((a, b) => b.oldest - a.oldest || b.owed - a.owed) };
}
