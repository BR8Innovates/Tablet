// Data layer. Everything the UI reads/writes goes through this module, scoped to the
// signed-in station (tenant). Today it persists to localStorage; to go multi-device SaaS,
// replace the bodies of load/persist and the CRUD helpers with REST calls — every record
// is already partitioned by station and carries a uuid, so the shape does not change.

const KEY = "fsm:v1";
const SESSION_KEY = "fsm:session";

const COLLECTIONS = [
  "products", "pumps", "prices", "shifts", "readings", "customers",
  "credits", "payments", "expenses", "expenseTypes", "sources", "closings",
];

let db = load();
let session = loadSession();

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
export const currentUser = () => session && db.users.find((u) => u.id === session.userId && u.active !== false) || null;
export const currentStation = () => session && db.stations.find((s) => s.id === session.stationId) || null;
export function startSession(user) {
  session = { userId: user.id, stationId: user.stationId };
  localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}
export function endSession() { session = null; localStorage.removeItem(SESSION_KEY); }

export const findUserByName = (username) => db.users.find((u) => u.username === username.trim().toLowerCase());
export const stationUsers = () => db.users.filter((u) => u.stationId === session.stationId);

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
export function updateStation(patch) { Object.assign(currentStation(), patch); persist(); }

// ---------- collections (scoped to current station) ----------
const bucket = () => db.data[session.stationId];

export const list = (col) => bucket()[col];
export const get = (col, id) => bucket()[col].find((r) => r.id === id);
export function add(col, obj) {
  const rec = { id: uid(), createdAt: Date.now(), ...obj };
  bucket()[col].push(rec);
  persist();
  return rec;
}
export function update(col, id, patch) {
  const rec = get(col, id);
  if (rec) { Object.assign(rec, patch, { updatedAt: Date.now() }); persist(); }
  return rec;
}
export function remove(col, id) {
  const arr = bucket()[col];
  const i = arr.findIndex((r) => r.id === id);
  if (i >= 0) { arr.splice(i, 1); persist(); }
}
// Insert or update the single record matching `match`; delete it when `obj` is null.
export function upsert(col, match, obj) {
  const rec = bucket()[col].find(match);
  if (!obj) { if (rec) remove(col, rec.id); return null; }
  return rec ? update(col, rec.id, obj) : add(col, obj);
}

// ---------- backup ----------
export function exportStation() {
  return JSON.stringify({ station: currentStation(), data: bucket(), exportedAt: new Date().toISOString() }, null, 2);
}
