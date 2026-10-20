// Data layer. Everything the UI reads/writes goes through this module, scoped to the
// signed-in station (tenant). Two modes, picked at startup by init():
//   remote — the Node server in /server is reachable: accounts, roles and data live there.
//            The station's data is cached in memory (so the screens stay synchronous), writes apply
//            instantly and are sent through an offline-safe queue.
//   local  — no server (e.g. static hosting): everything stays in this browser's localStorage.

const KEY = "fsm:v1";
const SESSION_KEY = "fsm:session";

const COLLECTIONS = [
  "products", "pumps", "prices", "shifts", "readings", "customers",
  "credits", "payments", "expenses", "expenseTypes", "sources", "closings",
];

const TOKEN_KEY = "fsm:token", CACHE_KEY = "fsm:cache", QUEUE_KEY = "fsm:queue", MODE_KEY = "fsm:mode";
let mode = "local";
let db = load();
let session = loadSession();
let rem = { user: null, station: null, data: null, users: [] };   // remote-mode snapshot
let token = null;
let queue = [];

function fresh() { return { v: 1, stations: [], users: [], data: {} }; }
function load() {
  try { return JSON.parse(localStorage.getItem(KEY)) || fresh(); } catch { return fresh(); }
}
function persist() { localStorage.setItem(KEY, JSON.stringify(db)); }
function loadSession() {
  try { return JSON.parse(localStorage.getItem(SESSION_KEY)); } catch { return null; }
}

export function uid() {
  if (globalThis.crypto?.randomUUID) return crypto.randomUUID();
  return "id-" + Date.now().toString(36) + Math.random().toString(36).slice(2, 10);
}

// ---------- session / tenant ----------
export const isRemote = () => mode === "remote";
export const currentUser = () => isRemote() ? rem.user : session && db.users.find((u) => u.id === session.userId && u.active !== false) || null;
export const currentStation = () => isRemote() ? rem.station : session && db.stations.find((s) => s.id === session.stationId) || null;
export function startSession(user) {
  session = { userId: user.id, stationId: user.stationId };
  localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}
export function endSession() {
  session = null; localStorage.removeItem(SESSION_KEY);
  token = null; rem = { user: null, station: null, data: null, users: [] };
  for (const k of [TOKEN_KEY, CACHE_KEY]) localStorage.removeItem(k);
}

export const findUserByName = (username) => db.users.find((u) => u.username === username.trim().toLowerCase());
export const stationUsers = () => isRemote() ? rem.users : db.users.filter((u) => u.stationId === session.stationId);

export function createStation({ stationName, currency }, ownerFields) {
  const station = { id: uid(), name: stationName, currency: currency || "₹", createdAt: Date.now() };
  const owner = { id: uid(), stationId: station.id, role: "owner", active: true, createdAt: Date.now(), ...ownerFields };
  db.stations.push(station);
  db.users.push(owner);
  db.data[station.id] = Object.fromEntries(COLLECTIONS.map((c) => [c, []]));
  seedDefaults(station.id);
  persist();
  return owner;
}

function seedDefaults(stationId) {
  const d = db.data[stationId];
  const mk = (o) => ({ id: uid(), createdAt: Date.now(), ...o });
  d.products = [
    mk({ name: "Petrol", category: "Fuel", unit: "L" }),
    mk({ name: "Diesel", category: "Fuel", unit: "L" }),
  ];
  d.shifts = [
    mk({ name: "Morning", start: "06:00", end: "14:00" }),
    mk({ name: "Evening", start: "14:00", end: "22:00" }),
    mk({ name: "Night", start: "22:00", end: "06:00" }),
  ];
  d.expenseTypes = ["Salary", "Electricity", "Maintenance", "Transport", "Tea & Misc"].map((name) => mk({ name }));
  d.sources = ["UPI", "Card", "Bank Transfer", "Fleet Card"].map((name) => mk({ name }));
}

export function addUser(fields) {
  const u = { id: uid(), stationId: session.stationId, active: true, createdAt: Date.now(), ...fields };
  db.users.push(u);
  persist();
  return u;
}
export function updateUser(id, patch) {
  const u = db.users.find((x) => x.id === id && x.stationId === session.stationId);
  if (u) { Object.assign(u, patch); persist(); }
  return u;
}
export function updateStation(patch) {
  Object.assign(currentStation(), patch);
  if (isRemote()) { saveCache(); enqueue("PATCH", "station", { name: currentStation().name, currency: currentStation().currency }); } else persist();
}

// ---------- collections (scoped to current station) ----------
const bucket = () => isRemote() ? rem.data : db.data[session.stationId];
// Local mode writes the whole db; remote mode caches the snapshot and queues the change for the server.
function saved(col, id, rec) {
  if (!isRemote()) return persist();
  saveCache();
  enqueue(rec ? "PUT" : "DELETE", `c/${col}/${id}`, rec);
}

export const list = (col) => bucket()[col];
export const get = (col, id) => bucket()[col].find((r) => r.id === id);
export function add(col, obj) {
  const rec = { id: uid(), createdAt: Date.now(), ...obj };
  bucket()[col].push(rec);
  saved(col, rec.id, rec);
  return rec;
}
export function update(col, id, patch) {
  const rec = get(col, id);
  if (rec) { Object.assign(rec, patch, { updatedAt: Date.now() }); saved(col, id, rec); }
  return rec;
}
export function remove(col, id) {
  const arr = bucket()[col];
  const i = arr.findIndex((r) => r.id === id);
  if (i >= 0) { arr.splice(i, 1); saved(col, id, null); }
}
// Insert or update the single record matching `match`; delete it when `obj` is null.
export function upsert(col, match, obj) {
  const rec = bucket()[col].find(match);
  if (!obj) { if (rec) remove(col, rec.id); return null; }
  return rec ? update(col, rec.id, obj) : add(col, obj);
}

// ---------- remote mode: requests, offline queue, sync ----------
const api = (path) => new URL("api/" + path, document.baseURI).href;
const saveCache = () => { try { localStorage.setItem(CACHE_KEY, JSON.stringify(rem)); } catch { /* quota */ } };
const saveQueue = () => localStorage.setItem(QUEUE_KEY, JSON.stringify(queue));

async function request(method, path, body, authed = true) {
  let res;
  try {
    res = await fetch(api(path), {
      method, cache: "no-store",
      headers: { ...(body !== undefined ? { "Content-Type": "application/json" } : {}), ...(authed && token ? { Authorization: "Bearer " + token } : {}) },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch { const e = new Error("You're offline."); e.network = true; throw e; }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) { const e = new Error(data.error || `Request failed (${res.status})`); e.status = res.status; throw e; }
  return data;
}

const listeners = new Set();
let syncState = { offline: false, signedOut: false, flushing: false, error: "" };
export const onSync = (fn) => { listeners.add(fn); return () => listeners.delete(fn); };
export const syncStatus = () => ({ ...syncState, pending: queue.length });
const notify = () => listeners.forEach((fn) => fn(syncStatus()));

function enqueue(m, path, body) {
  queue.push({ m, path, body });
  saveQueue();
  flush();
}

let retryTimer = null;
export async function flush() {
  if (!isRemote() || !token || syncState.flushing) return;
  syncState.flushing = true; notify();
  try {
    while (queue.length) {
      const op = queue[0];
      try { await request(op.m, op.path, op.body); syncState.offline = false; }
      catch (e) {
        if (e.network || e.status >= 500) { syncState.offline = true; clearTimeout(retryTimer); retryTimer = setTimeout(flush, 15000); break; }
        if (e.status === 401) { syncState.signedOut = true; break; }
        syncState.error = e.message;           // rejected for good (e.g. role) — drop it; next refresh restores server truth
      }
      queue.shift(); saveQueue();
    }
  } finally { syncState.flushing = false; notify(); }
}
if (typeof window !== "undefined") window.addEventListener("online", () => flush());

function adopt(snap) {
  rem = { user: snap.user, station: snap.station, data: snap.data, users: snap.users || [] };
  saveCache();
}

// Pull the latest station data (only when nothing is waiting to be sent). True if a refresh happened.
export async function refresh() {
  if (!isRemote() || !token || queue.length || syncState.flushing) return false;
  try { adopt(await request("GET", "me")); syncState.offline = false; syncState.error = ""; notify(); return true; }
  catch (e) { if (e.status === 401) { syncState.signedOut = true; } else if (e.network) syncState.offline = true; notify(); return false; }
}

export async function remoteSignIn(kind, body) {
  const snap = await request("POST", kind, body, false);
  token = snap.token; localStorage.setItem(TOKEN_KEY, token);
  if (rem.user && rem.user.id !== snap.user.id) { queue = []; saveQueue(); }
  adopt(snap);
  syncState = { offline: false, signedOut: false, flushing: false, error: "" };
  flush(); notify();
}

export async function remoteUsers(method, path, body) {
  const out = await request(method, path, body);
  rem.users = out.users; saveCache();
}

// Decide the mode and restore any saved session. Call once before drawing anything.
export async function init() {
  let known = localStorage.getItem(MODE_KEY);
  try {
    const r = await fetch(api("health"), { cache: "no-store" });
    known = r.ok && (await r.json()).ok ? "remote" : "local";
    localStorage.setItem(MODE_KEY, known);
  } catch { /* offline: keep the last known mode */ }
  mode = known === "remote" ? "remote" : "local";
  if (mode !== "remote") return;

  token = localStorage.getItem(TOKEN_KEY);
  try { queue = JSON.parse(localStorage.getItem(QUEUE_KEY)) || []; } catch { queue = []; }
  if (!token) return;
  try {
    const cached = JSON.parse(localStorage.getItem(CACHE_KEY));
    if (cached?.user) rem = cached;
  } catch { /* ignore */ }
  await flush();
  if (!queue.length) {
    try { adopt(await request("GET", "me")); }
    catch (e) { if (e.status === 401) { token = null; localStorage.removeItem(TOKEN_KEY); rem = { user: null, station: null, data: null, users: [] }; } else syncState.offline = true; }
  }
  if (!rem.user) token = null;
}

// ---------- backup ----------
export function exportStation() {
  return JSON.stringify({ station: currentStation(), data: bucket(), exportedAt: new Date().toISOString() }, null, 2);
}
