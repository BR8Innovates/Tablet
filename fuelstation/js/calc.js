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
